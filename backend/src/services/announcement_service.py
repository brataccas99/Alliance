"""Announcement service - fetches and manages announcements from schools."""
import logging
import os
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

    def _extract_pdf_text(self, pdf_url: str) -> str:
        """Extract text content from PDF file."""
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
            return full_text[:5000]  # Limit to 5000 chars
        except ImportError:
            logging.warning("PyPDF2 not installed, cannot extract PDF text")
            return ""
        except Exception as exc:
            logging.warning(f"Failed to extract PDF text from {pdf_url}: {exc}")
            return ""

    def _extract_attachments(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract attachment links from announcement page."""
        attachments = []
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

                # For PDFs, try to extract text content
                if file_ext == 'pdf':
                    pdf_text = self._extract_pdf_text(absolute_url)
                    if pdf_text:
                        attachment['text_content'] = pdf_text

                attachments.append(attachment)

                # Limit to 10 attachments per announcement
                if len(attachments) >= 10:
                    break

        return attachments

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

        # Extract date
        date_value = None
        if (meta := soup.find("meta", property="article:published_time")) and meta.get("content"):
            date_value = meta["content"]
        elif (meta := soup.find("meta", attrs={"itemprop": "datePublished"})) and meta.get("content"):
            date_value = meta["content"]
        elif (time_el := soup.find("time")) and time_el.get("datetime"):
            date_value = time_el["datetime"]

        published = self._parse_date(date_value) if date_value else date.min

        # Extract body
        paragraphs = [
            self._extract_text(p)
            for p in soup.find_all("p")
            if self._extract_text(p)
        ]
        body = " \n\n".join(paragraphs[:6])

        # Extract attachments
        attachments = self._extract_attachments(soup, url)

        # Determine status and highlight
        highlight_keywords = ("avviso", "selezione", "tutor", "bando")
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

    def fetch_and_save(self) -> int:
        """Fetch announcements from all schools and save to JSON.

        Returns:
            Number of announcements fetched.
        """
        schools = get_active_schools()
        scraped_items: List[Dict] = []

        for school in schools:
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

        logging.info(f"Saved {len(pruned)} total announcements from {len(schools)} schools (merged, pruned)")
        return len(pruned)

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
