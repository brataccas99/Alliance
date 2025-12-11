"""Announcement service - fetches and manages announcements from schools."""
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from ..config.schools import School, get_active_schools
from ..utils import JSONStorage

CACHE_TTL = timedelta(minutes=30)


class AnnouncementService:
    """Service for fetching and managing announcements from multiple schools."""

    def __init__(self):
        """Initialize the service."""
        self.storage = JSONStorage("announcements.json")
        self._memory_cache: Dict[str, object] = {"data": None, "timestamp": None}

    def _parse_date(self, value: str) -> date:
        """Parse date string to date object."""
        try:
            return dateparser.parse(value).date()
        except Exception:
            return date.min

    def _extract_text(self, element) -> str:
        """Extract text from BeautifulSoup element."""
        return element.get_text(strip=True) if element else ""

    def _scrape_detail(self, url: str, school: School) -> Dict:
        """Scrape announcement details from URL."""
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

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
            "date": published,
            "status": status,
            "tags": [],
            "highlight": highlight,
        }

    def _scrape_school_announcements(self, school: School) -> List[Dict]:
        """Scrape announcements from a single school."""
        try:
            logging.info(f"Scraping announcements from {school.name}...")
            listing = requests.get(school.pnrr_url, timeout=10)
            listing.raise_for_status()
            soup = BeautifulSoup(listing.text, "html.parser")

            links = []
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"].split("#")[0]
                absolute_url = urljoin(school.base_url, href)

                if absolute_url.startswith(school.base_url) and absolute_url != school.pnrr_url and absolute_url not in links:
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
        all_items: List[Dict] = []

        for school in schools:
            school_items = self._scrape_school_announcements(school)
            all_items.extend(school_items)

        # Assign unique IDs
        for idx, item in enumerate(all_items, start=1):
            item["id"] = idx

        # Save to JSON
        self.storage.save_announcements(all_items)

        # Update memory cache
        self._memory_cache = {
            "data": all_items,
            "timestamp": datetime.utcnow()
        }

        logging.info(f"Saved {len(all_items)} total announcements from {len(schools)} schools")
        return len(all_items)

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
