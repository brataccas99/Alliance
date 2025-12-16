"""Notification service - dedupe and send announcement emails."""
from __future__ import annotations

import logging
import os
import time
import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote

from pymongo import ASCENDING

from ..utils import get_notifications_collection
from ..utils.blob_json_store import BlobJsonStore
from .email_service import EmailService
from .subscriber_service import Subscriber


class NotificationService:
    """Send announcement notifications to subscribers."""

    def __init__(self) -> None:
        self._collection = get_notifications_collection()
        if self._collection is not None:
            self._collection.create_index([("email", ASCENDING), ("key", ASCENDING)], unique=True)
            self._collection.create_index([("created_at", ASCENDING)])
        self._email = EmailService()
        self._gcs_bucket = (os.getenv("GCS_BUCKET", "") or "").strip()

    @staticmethod
    def _announcement_key(ann: Dict) -> Optional[str]:
        school_id = ann.get("school_id")
        link = ann.get("link")
        if not school_id or not link:
            return None
        return f"{school_id}|{link}"

    @staticmethod
    def _fmt_date(value) -> str:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            return value
        return ""

    def _filter_by_subscriber(self, subscriber: Subscriber, announcements: Iterable[Dict]) -> List[Dict]:
        if not subscriber.school_ids:
            return list(announcements)
        allowed = set(subscriber.school_ids)
        return [a for a in announcements if a.get("school_id") in allowed]

    def _filter_unsent(self, email: str, announcements: List[Dict]) -> List[Dict]:
        if self._collection is None:
            return self._filter_unsent_json(email, announcements)

        keys = [self._announcement_key(a) for a in announcements]
        keys = [k for k in keys if k]
        if not keys:
            return []

        existing = set(
            d["key"]
            for d in self._collection.find({"email": email, "key": {"$in": keys}}, {"_id": 0, "key": 1})
        )
        return [a for a in announcements if (self._announcement_key(a) not in existing)]

    def _notification_store(self, email: str) -> BlobJsonStore:
        digest = hashlib.sha256(email.encode("utf-8")).hexdigest()
        base_dir = Path(__file__).parent.parent.parent
        local_path = base_dir / "data" / "notifications" / f"{digest}.json"
        return BlobJsonStore(local_path=local_path, object_name=f"notifications/{digest}.json")

    def _filter_unsent_json(self, email: str, announcements: List[Dict]) -> List[Dict]:
        keys = [self._announcement_key(a) for a in announcements]
        keys = [k for k in keys if k]
        if not keys:
            return []

        store = self._notification_store(email)
        loaded = store.load({"sent_keys": []})
        existing = set(loaded.get("sent_keys", []) or [])
        return [a for a in announcements if (self._announcement_key(a) not in existing)]

    def _record_sent(self, email: str, announcements: List[Dict]) -> None:
        if self._collection is None:
            self._record_sent_json(email, announcements)
            return
        now = datetime.utcnow().isoformat()
        docs = []
        for a in announcements:
            key = self._announcement_key(a)
            if not key:
                continue
            docs.append({"email": email, "key": key, "created_at": now})
        if not docs:
            return
        try:
            self._collection.insert_many(docs, ordered=False)
        except Exception:  # noqa: BLE001
            pass

    def _record_sent_json(self, email: str, announcements: List[Dict]) -> None:
        keys = [self._announcement_key(a) for a in announcements]
        keys = [k for k in keys if k]
        if not keys:
            return

        store = self._notification_store(email)
        for attempt in range(8):
            loaded = store.load_with_generation({"sent_keys": []})
            data = loaded.data
            generation = loaded.generation
            sent_keys = set(data.get("sent_keys", []) or [])
            before = len(sent_keys)
            sent_keys.update(keys)
            if len(sent_keys) == before:
                return
            data["sent_keys"] = sorted(sent_keys)
            data["updated_at"] = datetime.utcnow().isoformat()
            try:
                store.save_with_generation(data, generation=generation)
                return
            except Exception as exc:  # noqa: BLE001
                if attempt >= 7:
                    logging.warning("Notification dedupe JSON update failed for %s: %s", email, exc)
                    return
                time.sleep(0.2 * (attempt + 1))

    def _build_email_body(self, announcements: List[Dict], recipient_email: str) -> str:
        lines = ["New announcements are available:", ""]
        for a in announcements[:50]:
            title = (a.get("title") or "").strip()
            school = (a.get("school_name") or a.get("school_id") or "").strip()
            when = self._fmt_date(a.get("date"))
            link = (a.get("link") or "").strip()
            lines.append(f"- {title} ({school}) {when}")
            if link:
                lines.append(f"  {link}")
        lines.append("")
        base_url = (os.getenv("APP_BASE_URL", "") or "").rstrip("/")
        if base_url:
            lines.append(f"Unsubscribe: {base_url}/unsubscribe?email={quote(recipient_email)}")
        else:
            lines.append("Unsubscribe: open the app and use /api/unsubscribe with your email.")
        return "\n".join(lines)

    def notify(self, subscribers: Iterable[Subscriber], new_announcements: Iterable[Dict]) -> int:
        """Send notifications for new announcements.

        Returns:
            Number of emails sent.
        """
        new_list = list(new_announcements)
        if not new_list:
            return 0

        sent = 0
        for subscriber in subscribers:
            subset = self._filter_by_subscriber(subscriber, new_list)
            subset = self._filter_unsent(subscriber.email, subset)
            if not subset:
                continue
            try:
                subject = f"{len(subset)} new announcement(s)"
                body = self._build_email_body(subset, subscriber.email)
                self._email.send_text(subscriber.email, subject, body)
                self._record_sent(subscriber.email, subset)
                sent += 1
            except Exception as exc:  # noqa: BLE001
                logging.warning("Failed to send email to %s: %s", subscriber.email, exc)
        return sent
