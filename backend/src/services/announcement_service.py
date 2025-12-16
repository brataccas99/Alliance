"""Announcement service - fetches and manages announcements from schools."""
import logging
import os
import re
import time
import random
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ..config.schools import School, get_active_schools
from ..utils import JSONStorage
from .notification_service import NotificationService
from .subscriber_service import SubscriberService

CACHE_TTL = timedelta(minutes=30)
STALE_AFTER = timedelta(days=180)

# Anti-CAPTCHA settings
MIN_REQUEST_DELAY = float(os.getenv("MIN_REQUEST_DELAY", "2.0"))  # seconds
MAX_REQUEST_DELAY = float(os.getenv("MAX_REQUEST_DELAY", "5.0"))  # seconds
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))  # seconds


class AnnouncementService:
    """Service for fetching and managing announcements from multiple schools."""

    _BASE_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/119.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(self):
        """Initialize the service."""
        self.storage = JSONStorage("announcements.json")
        self._memory_cache: Dict[str, object] = {"data": None, "timestamp": None}
        self.session = requests.Session()
        self.session.headers.update(self._BASE_HEADERS)
        self._progress: Dict[str, object] = {
            "status": "idle",
            "total": 0,
            "current": 0,
            "school": None,
        }
        self._last_fetch_stats: Dict[str, object] = {
            "last_run": None,
            "total_count": 0,
            "new_count": 0,
            "emails_sent": 0,
        }
        self._last_request_time = 0.0
        self._request_count = 0

    def _smart_delay(self):
        """Add intelligent delay between requests to avoid rate limiting."""
        elapsed = time.time() - self._last_request_time

        # Calculate delay based on request count (increases with more requests)
        base_delay = MIN_REQUEST_DELAY
        if self._request_count > 10:
            base_delay = MIN_REQUEST_DELAY * 1.5
        if self._request_count > 20:
            base_delay = MIN_REQUEST_DELAY * 2

        delay = random.uniform(base_delay, MAX_REQUEST_DELAY)

        # Only delay if needed
        if elapsed < delay:
            sleep_time = delay - elapsed
            logging.debug(f"Delaying {sleep_time:.2f}s to avoid rate limiting (request #{self._request_count})")
            time.sleep(sleep_time)

        self._last_request_time = time.time()
        self._request_count += 1

    def _normalize_host(self, url: str) -> str:
        """Normalize host, removing scheme and www for comparisons."""
        return urlparse(url).netloc.replace("www.", "").lower()

    def _generate_url_variants(self, url: str) -> List[str]:
        """Generate host/scheme variants to bypass simple 403 blocks."""
        parsed = urlparse(url)
        hosts = {parsed.netloc}
        if parsed.netloc.startswith("www."):
            hosts.add(parsed.netloc[len("www.") :])
        else:
            hosts.add(f"www.{parsed.netloc}")

        schemes = ["https", "http"]
        variants = []
        for scheme in schemes:
            for host in hosts:
                variant = parsed._replace(scheme=scheme, netloc=host).geturl()
                variants.append(variant)
        # Preserve order and uniqueness
        seen = set()
        ordered = []
        for v in variants:
            if v not in seen:
                ordered.append(v)
                seen.add(v)
        return ordered

    def _fetch_with_playwright(self, url: str, referer: str | None = None) -> str:
        """Fetch page HTML using Playwright as a fallback for captcha/403."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            logging.error("Playwright not installed; cannot bypass captcha for %s", url)
            return ""

        headless = os.getenv("PLAYWRIGHT_HEADFUL", "").lower() not in ("1", "true", "yes")
        wait_ms = int(os.getenv("PLAYWRIGHT_WAIT_MS", "5000"))
        user_data_dir = os.getenv("PLAYWRIGHT_USER_DATA_DIR", ".playwright-profile")
        extra_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

        with sync_playwright() as p:  # pragma: no cover - network/UI dependent
            browser = p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=headless,
                args=extra_args,
                viewport={"width": 1400, "height": 900},
                bypass_csp=True,
            )
            context = browser
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
            )
            page = context.new_page()
            headers = dict(self._BASE_HEADERS)
            if referer:
                headers["Referer"] = referer
            page.set_extra_http_headers(headers)

            logging.info("Playwright fetch%s: %s", " (headful)" if not headless else "", url)
            page.goto(url, wait_until="networkidle", timeout=45000)

            if not headless:
                logging.info("If a captcha is shown, solve it in the browser window, then press Enter to continue.")
                try:
                    input()
                except EOFError:
                    pass

            page.wait_for_timeout(wait_ms)
            content = page.content()
            page.close()
            # keep persistent context open only if headless; headful should still close
            context.close()
            return content

    def _get(self, url: str, referer: str | None = None, retry_count: int = 0) -> requests.Response:
        """Perform a GET request with browser-like headers, referer, and host/scheme fallbacks."""
        # Add smart delay to avoid rate limiting
        self._smart_delay()

        errors = []
        for candidate in self._generate_url_variants(url):
            headers = {}
            if referer:
                headers["Referer"] = referer
            try:
                resp = self.session.get(candidate, timeout=REQUEST_TIMEOUT, headers=headers)
                resp.raise_for_status()
                return resp
            except requests.HTTPError as exc:  # pragma: no cover - network dependent
                status_code = exc.response.status_code if hasattr(exc, 'response') else None

                # Exponential backoff for rate limiting (429) or server errors (5xx)
                if status_code in [429, 503] and retry_count < 3:
                    backoff_time = (2 ** retry_count) * MIN_REQUEST_DELAY
                    logging.warning(f"Rate limited ({status_code}), backing off for {backoff_time:.1f}s")
                    time.sleep(backoff_time)
                    return self._get(url, referer, retry_count + 1)

                errors.append(f"{candidate} -> {exc}")
                # Try next variant on 403/404/other HTTP errors
                continue
            except Exception as exc:  # pragma: no cover - network dependent
                errors.append(f"{candidate} -> {exc}")
                continue

        raise requests.HTTPError(f"All variants failed for {url}: {errors}")

    def _fetch_listing_html(self, school: School) -> str:
        """Fetch listing page HTML with fallback to Playwright."""
        try:
            resp = self._get(school.pnrr_url, referer=school.base_url)
            return resp.text
        except requests.HTTPError as exc:
            logging.warning(f"Listing request failed for {school.name}: {exc}. Trying Playwright fallback.")
            html = self._fetch_with_playwright(school.pnrr_url, referer=school.base_url)
            if not html:
                logging.error(f"Playwright fallback failed for {school.name}")
            return html
        except Exception as exc:
            logging.error(f"Unexpected error fetching listing for {school.name}: {exc}")
            return ""

    def _parse_date(self, value: str) -> date:
        """Parse date string to date object."""
        try:
            return dateparser.parse(value).date()
        except Exception:
            return date.min

    def _extract_date_from_text(self, text: str) -> Optional[date]:
        """Extract date from Italian text using multiple patterns.

        Tries patterns in order of specificity:
        1. Dates with context keywords (scadenza, pubblicato, etc.)
        2. Italian text dates (24 gennaio 2024)
        3. Numeric formats (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)

        Args:
            text: Text to search for dates

        Returns:
            Extracted date or None if no valid date found
        """
        if not text:
            return None

        # Define Italian month names mapping
        italian_months = {
            'gennaio': '01', 'gen': '01',
            'febbraio': '02', 'feb': '02',
            'marzo': '03', 'mar': '03',
            'aprile': '04', 'apr': '04',
            'maggio': '05', 'mag': '05',
            'giugno': '06', 'giu': '06',
            'luglio': '07', 'lug': '07',
            'agosto': '08', 'ago': '08',
            'settembre': '09', 'set': '09',
            'ottobre': '10', 'ott': '10',
            'novembre': '11', 'nov': '11',
            'dicembre': '12', 'dic': '12'
        }

        # Create pattern fragments
        month_names = '|'.join(italian_months.keys())

        # Pattern 1: Contextual dates (highest priority)
        contextual_patterns = [
            rf'(?:scadenza|pubblicat[oa]|data)[\s:]+(\d{{1,2}})\s+({month_names})\s+(\d{{4}})',
            rf'(?:scadenza|pubblicat[oa]|data)[\s:]+(\d{{1,2}})[/-](\d{{1,2}})[/-](\d{{4}})',
            rf'(?:scadenza|pubblicat[oa]|data)[\s:]+(\d{{4}})[/-](\d{{1,2}})[/-](\d{{1,2}})',
        ]

        # Pattern 2: Italian text dates
        italian_date_pattern = rf'(\d{{1,2}})\s+({month_names})\s+(\d{{4}})'

        # Pattern 3: Numeric dates
        numeric_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})',  # DD/MM/YYYY or DD-MM-YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',  # YYYY-MM-DD
        ]

        candidates = []

        # Try contextual patterns first
        for pattern in contextual_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Check if it's Italian month format
                        if groups[1].lower() in italian_months:
                            day = int(groups[0])
                            month = int(italian_months[groups[1].lower()])
                            year = int(groups[2])
                        elif groups[0].isdigit() and len(groups[0]) == 4:  # YYYY-MM-DD
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # DD-MM-YYYY
                            day, month, year = int(groups[0]), int(groups[1]), int(groups[2])

                        # Validate ranges
                        if 1900 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                            parsed_date = date(year, month, day)
                            candidates.append((parsed_date, 10))  # High priority
                except (ValueError, TypeError, KeyError):
                    continue

        # Try Italian text dates
        matches = re.finditer(italian_date_pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                year = int(match.group(3))
                month = int(italian_months[month_name])

                if 1900 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                    parsed_date = date(year, month, day)
                    candidates.append((parsed_date, 8))  # Medium-high priority
            except (ValueError, TypeError, KeyError):
                continue

        # Try numeric patterns
        for pattern in numeric_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    groups = match.groups()
                    if len(groups[0]) == 4:  # YYYY-MM-DD format
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # DD/MM/YYYY format
                        day, month, year = int(groups[0]), int(groups[1]), int(groups[2])

                    # Validate ranges
                    if 1900 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
                        parsed_date = date(year, month, day)
                        candidates.append((parsed_date, 5))  # Lower priority
                except (ValueError, TypeError):
                    continue

        # Return highest priority candidate that's reasonable
        if candidates:
            # Filter future dates beyond 1 year (likely errors)
            max_future = date.today() + timedelta(days=365)
            valid_candidates = [
                (d, p) for d, p in candidates
                if d <= max_future
            ]

            if valid_candidates:
                # Sort by priority (descending) then by date (descending for most recent)
                valid_candidates.sort(key=lambda x: (x[1], x[0]), reverse=True)
                return valid_candidates[0][0]

        return None

    def _extract_text(self, element) -> str:
        """Extract text from BeautifulSoup element."""
        return element.get_text(strip=True) if element else ""

    def _parse_iso_datetime(self, value: str | None) -> Optional[datetime]:
        """Parse ISO datetime string safely."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    def _extract_pdf_text(self, pdf_url: str) -> tuple[str, Optional[date]]:
        """Extract text content and date from PDF file.

        Args:
            pdf_url: URL of PDF to extract from

        Returns:
            Tuple of (text_content, extracted_date)
            - text_content: First 5000 chars from first 5 pages
            - extracted_date: Date found in PDF text, or None
        """
        try:
            import io
            from PyPDF2 import PdfReader

            logging.info(f"Extracting text from PDF: {pdf_url}")
            resp = self._get(pdf_url)
            pdf_file = io.BytesIO(resp.content)
            reader = PdfReader(pdf_file)

            text_parts = []
            max_pages = min(5, len(reader.pages))  # Limit to first 5 pages
            for page_num in range(max_pages):
                page = reader.pages[page_num]
                text_parts.append(page.extract_text())

            full_text = "\n\n".join(text_parts)
            limited_text = full_text[:5000]  # Limit to 5000 chars

            # Extract date from first 2000 chars of PDF
            extracted_date = self._extract_date_from_text(full_text[:2000])

            return limited_text, extracted_date

        except ImportError:
            logging.warning("PyPDF2 not installed, cannot extract PDF text")
            return "", None
        except Exception as exc:
            logging.warning(f"Failed to extract PDF text from {pdf_url}: {exc}")
            return "", None

    def _extract_attachments(self, soup: BeautifulSoup, base_url: str) -> tuple[List[Dict], Optional[date]]:
        """Extract attachment links and earliest PDF date from announcement page.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            Tuple of (attachments_list, earliest_pdf_date)
            - attachments_list: List of attachment dicts with metadata
            - earliest_pdf_date: Earliest date found in PDFs, or None
        """
        attachments = []
        pdf_dates = []  # Collect dates from PDFs
        seen_urls = set()

        # Common attachment file extensions
        attachment_extensions = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar')

        # Find all links that might be attachments
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)

            # Skip if already seen or not an attachment
            if absolute_url in seen_urls:
                continue

            # Check if it's an attachment by extension or by link text/aria-label
            is_attachment = False
            if any(absolute_url.lower().endswith(ext) for ext in attachment_extensions):
                is_attachment = True
            elif any(keyword in link.get_text().lower() for keyword in ['scarica', 'download', 'allegat', 'document']):
                is_attachment = True

            if is_attachment:
                seen_urls.add(absolute_url)

                # Determine attachment type
                file_ext = None
                for ext in attachment_extensions:
                    if absolute_url.lower().endswith(ext):
                        file_ext = ext.lstrip('.')
                        break

                attachment = {
                    'url': absolute_url,
                    'label': link.get_text(strip=True) or f"Allegato {len(attachments) + 1}",
                    'type': file_ext or 'unknown'
                }

                # For PDFs, try to extract text content and date
                if file_ext == 'pdf':
                    pdf_text, pdf_date = self._extract_pdf_text(absolute_url)  # Unpack tuple
                    if pdf_text:
                        attachment['text_content'] = pdf_text
                    if pdf_date:
                        pdf_dates.append(pdf_date)
                        logging.info(f"Extracted date from PDF {absolute_url}: {pdf_date}")

                attachments.append(attachment)

                # Limit to 10 attachments per announcement
                if len(attachments) >= 10:
                    break

        # Return earliest PDF date (publication date)
        earliest_pdf_date = min(pdf_dates) if pdf_dates else None
        return attachments, earliest_pdf_date

    def _scrape_detail(self, url: str, school: School) -> Dict:
        """Scrape announcement details from URL."""
        html = ""
        content_type = ""

        try:
            resp = self._get(url, referer=school.pnrr_url)
            html = resp.text
            content_type = resp.headers.get("Content-Type", "").lower()
        except requests.HTTPError as exc:
            logging.warning(f"Detail request failed for {url}: {exc}. Trying Playwright fallback.")
            html = self._fetch_with_playwright(url, referer=school.pnrr_url)
            content_type = "text/html" if html else ""

        if "pdf" in content_type:
            # Minimal metadata for non-HTML resources (e.g., PDF notices)
            parsed_url = urlparse(url)
            source_domain = parsed_url.netloc
            return {
                "title": url.split("/")[-1] or url,
                "summary": "Documento scaricabile",
                "body": "",
                "link": url,
                "category": "PNRR Futura",
                "source": source_domain,
                "school_id": school.id,
                "school_name": school.name,
                "city": school.city,
                "date": date.min,
                "status": "Published",
                "tags": [],
                "highlight": False,
            }

        if not html:
            raise requests.HTTPError(f"Failed to fetch detail page after fallbacks: {url}")

        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = ""
        if (meta := soup.find("meta", property="og:title")) and meta.get("content"):
            title = meta["content"]
        elif soup.title:
            title = soup.title.get_text(strip=True)

        # Extract summary
        summary = ""
        if (meta := soup.find("meta", property="og:description")) and meta.get("content"):
            summary = meta["content"]
        else:
            first_p = soup.find("p")
            summary = self._extract_text(first_p)

        # Extract date with priority: PDF > Meta tags > Detail page text
        date_value = None

        # Priority 1: Meta tags (existing logic)
        if (meta := soup.find("meta", property="article:published_time")) and meta.get("content"):
            date_value = meta["content"]
        elif (meta := soup.find("meta", attrs={"itemprop": "datePublished"})) and meta.get("content"):
            date_value = meta["content"]
        elif (time_el := soup.find("time")) and time_el.get("datetime"):
            date_value = time_el["datetime"]

        published = self._parse_date(date_value) if date_value else date.min

        # Extract body (moved before attachments to get page text)
        paragraphs = [
            self._extract_text(p)
            for p in soup.find_all("p")
            if self._extract_text(p)
        ]
        body = " \n\n".join(paragraphs[:6])

        # Extract attachments (returns dates too now)
        attachments, pdf_date = self._extract_attachments(soup, url)

        # Priority 2: PDF dates (if meta tags failed)
        if published == date.min and pdf_date:
            published = pdf_date
            logging.info(f"Using PDF date for {url}: {pdf_date}")

        # Priority 3: Detail page text (if both meta and PDF failed)
        if published == date.min:
            # Extract strategic text sections
            page_text = ""

            # Check metadata sections
            for selector_params in [
                {'name': ['div', 'section'], 'class_': re.compile(r'(meta|header|info|data|pubblicat)', re.I)},
                {'name': ['article', 'main'], 'class_': re.compile(r'(content|article|post)', re.I)},
            ]:
                if container := soup.find(**selector_params):
                    page_text += self._extract_text(container) + " "

            # Fallback: use body paragraphs
            if len(page_text) < 100:
                page_text = body

            page_text = page_text[:2000]  # Limit search

            text_date = self._extract_date_from_text(page_text)
            if text_date:
                published = text_date
                logging.info(f"Using detail page text date for {url}: {text_date}")

        # Determine status and highlight
        highlight_keywords = ("avviso", "selezione", "tutor", "bando", "assunzione", "progetto", "incarico")
        highlight = any(k in title.lower() for k in highlight_keywords)
        status = "Open" if any(k in title.lower() for k in ("selezione", "avviso", "bando")) else "Published"

        # Extract domain
        parsed_url = urlparse(url)
        source_domain = parsed_url.netloc

        return {
            "title": title or url,
            "summary": summary,
            "body": body or summary,
            "link": url,
            "category": "PNRR Futura",
            "source": source_domain,
            "school_id": school.id,
            "school_name": school.name,
            "city": school.city,
            "date": published,
            "status": status,
            "tags": [],
            "highlight": highlight,
            "attachments": attachments,
        }

    def _scrape_school_announcements(self, school: School) -> List[Dict]:
        """Scrape announcements from a single school."""
        try:
            logging.info(f"Scraping announcements from {school.name}...")
            listing_html = self._fetch_listing_html(school)
            if not listing_html:
                logging.error(f"No listing HTML available for {school.name}")
                return []

            soup = BeautifulSoup(listing_html, "html.parser")

            links = []
            base_host = self._normalize_host(school.base_url)
            pnrr_host = self._normalize_host(school.pnrr_url)
            allowed_keywords = ("pnrr", "pon", "futura")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"].split("#")[0]
                absolute_url = urljoin(school.base_url.rstrip("/") + "/", href)
                parsed_url = urlparse(absolute_url)
                path_segment = parsed_url.path.strip("/")

                normalized = self._normalize_host(absolute_url)
                if (
                    normalized in (base_host, pnrr_host)
                    and path_segment  # avoid base URL root
                    and absolute_url.rstrip("/") != school.pnrr_url.rstrip("/")
                    and any(keyword in absolute_url.lower() for keyword in allowed_keywords)
                    and absolute_url not in links
                ):
                    links.append(absolute_url)

            items: List[Dict] = []
            for href in links[:10]:  # Limit per school
                try:
                    detail = self._scrape_detail(href, school)
                    items.append(detail)
                except Exception as exc:
                    logging.warning(f"Skipping {href} from {school.name}: {exc}")

            logging.info(f"Scraped {len(items)} announcements from {school.name}")
            return items

        except Exception as exc:
            logging.error(f"Failed to scrape from {school.name}: {exc}")
            return []

    def get_progress(self) -> Dict[str, object]:
        """Return current fetch progress."""
        return self._progress

    def _set_progress(self, status: str, total: int, current: int, school: Optional[str]) -> None:
        """Update progress state."""
        self._progress = {
            "status": status,
            "total": total,
            "current": current,
            "school": school,
        }

    def fetch_and_save(self) -> int:
        """Fetch announcements from all schools and save to JSON.

        Returns:
            Number of announcements fetched.
        """
        schools = get_active_schools()
        self._set_progress("running", len(schools), 0, None)
        scraped_items: List[Dict] = []

        for idx, school in enumerate(schools, start=1):
            self._set_progress("running", len(schools), idx - 1, school.name)
            school_items = self._scrape_school_announcements(school)
            scraped_items.extend(school_items)

        # Load existing data to merge and preserve older entries
        existing = self.storage.load_announcements()
        existing_by_key: Dict[tuple, Dict] = {}
        for ann in existing:
            key = (ann.get("school_id"), ann.get("link"))
            if key[0] and key[1]:
                existing_by_key[key] = ann

        now = datetime.utcnow()
        now_iso = now.isoformat()
        merged: List[Dict] = []
        newly_seen: List[Dict] = []

        for item in scraped_items:
            key = (item.get("school_id"), item.get("link"))
            if not key[0] or not key[1]:
                continue
            existing_ann = existing_by_key.pop(key, None)
            if existing_ann:
                merged_item = {**existing_ann, **item}
                merged_item["id"] = existing_ann.get("id")
                merged_item["first_seen"] = existing_ann.get("first_seen", now_iso)
            else:
                merged_item = dict(item)
                merged_item["first_seen"] = now_iso
                newly_seen.append(merged_item)
            merged_item["last_seen"] = now_iso
            merged.append(merged_item)

        # Keep existing items that were not scraped this run
        merged.extend(existing_by_key.values())

        # Drop stale items (last_seen older than 6 months)
        cutoff = now - STALE_AFTER
        pruned: List[Dict] = []
        for ann in merged:
            last_seen = self._parse_iso_datetime(ann.get("last_seen"))
            if last_seen and last_seen < cutoff:
                continue
            pruned.append(ann)

        # Assign IDs: keep existing ids, assign new ones for missing
        max_id = max((a.get("id", 0) or 0) for a in pruned) if pruned else 0
        next_id = max_id + 1
        # Sort by date desc then title for stable order
        pruned.sort(key=lambda a: (a.get("date") or date.min, a.get("title", "")), reverse=True)
        for ann in pruned:
            if not ann.get("id"):
                ann["id"] = next_id
                next_id += 1

        # Save to JSON
        self.storage.save_announcements(pruned)

        # Update memory cache
        self._memory_cache = {
            "data": pruned,
            "timestamp": datetime.utcnow()
        }

        self._set_progress("idle", 0, 0, None)
        logging.info(f"Saved {len(pruned)} total announcements from {len(schools)} schools (merged, pruned)")

        # Notify subscribers about newly seen announcements (best-effort).
        emails_sent = 0
        try:
            emails_sent = NotificationService().notify(SubscriberService().list_active(), newly_seen)
            if emails_sent:
                logging.info("Sent %s notification email(s) for %s new announcement(s)", emails_sent, len(newly_seen))
        except Exception as exc:  # noqa: BLE001
            logging.warning("Subscriber notification failed: %s", exc)

        self._last_fetch_stats = {
            "last_run": datetime.utcnow().isoformat(),
            "total_count": len(pruned),
            "new_count": len(newly_seen),
            "emails_sent": emails_sent,
        }
        return len(pruned)

    def get_last_fetch_stats(self) -> Dict[str, object]:
        """Get stats from the last fetch run."""
        return dict(self._last_fetch_stats)

    def get_all_announcements(self, use_cache: bool = True) -> List[Dict]:
        """Get all announcements.

        Args:
            use_cache: Use memory cache if available.

        Returns:
            List of all announcements.
        """
        # Check memory cache first
        if use_cache:
            cached = self._memory_cache.get("data")
            ts = self._memory_cache.get("timestamp")
            if cached and ts and datetime.utcnow() - ts < CACHE_TTL:
                return cached

        # Load from JSON
        announcements = self.storage.load_announcements()

        # Update memory cache
        self._memory_cache = {
            "data": announcements,
            "timestamp": datetime.utcnow()
        }

        return announcements

    def get_announcement_by_id(self, ann_id: int) -> Optional[Dict]:
        """Get specific announcement by ID.

        Args:
            ann_id: Announcement ID.

        Returns:
            Announcement dict or None.
        """
        announcements = self.get_all_announcements()
        return next((a for a in announcements if a.get("id") == ann_id), None)

    def get_announcements_by_school(self, school_id: str) -> List[Dict]:
        """Get announcements filtered by school.

        Args:
            school_id: School identifier.

        Returns:
            List of announcements from specified school.
        """
        announcements = self.get_all_announcements()
        return [a for a in announcements if a.get("school_id") == school_id]

    def get_last_updated(self) -> Optional[datetime]:
        """Get last update timestamp.

        Returns:
            Last update datetime or None.
        """
        return self.storage.get_last_updated()
