"""Subscriber service - stores and manages email subscribers."""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import Iterable, List, Optional

from pymongo import ASCENDING

from ..utils import get_subscribers_collection
from ..utils.blob_json_store import BlobJsonStore


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Subscriber:
    """Email subscriber with optional school filters."""

    email: str
    school_ids: Optional[List[str]] = None  # None => all schools


class SubscriberService:
    """Manage subscribers (MongoDB if configured, else local JSON file)."""

    def __init__(self) -> None:
        self._collection = get_subscribers_collection()
        self._file_path = Path(__file__).parent.parent.parent / "data" / "subscribers.json"
        self._store = BlobJsonStore(local_path=self._file_path, object_name="subscribers.json")
        self._ensure_storage()

        if self._collection is not None:
            self._collection.create_index([("email", ASCENDING)], unique=True)
            self._collection.create_index([("active", ASCENDING)])

    def _ensure_storage(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._write_file({"subscribers": []})

    def _read_file(self) -> dict:
        return self._store.load({"subscribers": []})

    def _write_file(self, data: dict) -> None:
        self._store.save(data)

    def _update_file_atomic(self, updater, *, retries: int = 8) -> Any:
        """Read-modify-write with optimistic concurrency (GCS) and retries."""
        for attempt in range(retries):
            loaded = self._store.load_with_generation({"subscribers": []})
            data = loaded.data
            generation = loaded.generation
            result = updater(data)
            try:
                self._store.save_with_generation(data, generation=generation)
                return result
            except Exception as exc:  # noqa: BLE001
                if attempt >= retries - 1:
                    raise
                logging.warning("Subscriber JSON update retry (%s): %s", attempt + 1, exc)
                time.sleep(0.2 * (attempt + 1))

    def _normalize_school_ids(self, school_ids: Optional[Iterable[str]]) -> Optional[List[str]]:
        if school_ids is None:
            return None
        normalized = sorted({s.strip() for s in school_ids if (s or "").strip()})
        return normalized or None

    def _validate_email(self, email: str) -> str:
        value = (email or "").strip().lower()
        if not value or not _EMAIL_RE.match(value):
            raise ValueError("Invalid email")
        return value

    def subscribe(self, email: str, school_ids: Optional[Iterable[str]] = None) -> Subscriber:
        """Create or update a subscriber (idempotent).

        Args:
            email: Subscriber email.
            school_ids: Optional list of school ids to filter on; None => all.

        Returns:
            Subscriber.
        """
        email_norm = self._validate_email(email)
        school_ids_norm = self._normalize_school_ids(school_ids)
        now = datetime.utcnow().isoformat()

        if self._collection is not None:
            self._collection.update_one(
                {"email": email_norm},
                {
                    "$set": {
                        "email": email_norm,
                        "school_ids": school_ids_norm,
                        "active": True,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now, "last_notified_at": None},
                },
                upsert=True,
            )
            return Subscriber(email=email_norm, school_ids=school_ids_norm)

        def updater(data: dict):
            subs = data.get("subscribers", [])
            updated = False
            for s in subs:
                if (s.get("email") or "").lower() == email_norm:
                    s["email"] = email_norm
                    s["school_ids"] = school_ids_norm
                    s["active"] = True
                    s["updated_at"] = now
                    s.setdefault("created_at", now)
                    s.setdefault("last_notified_at", None)
                    updated = True
                    break
            if not updated:
                subs.append(
                    {
                        "email": email_norm,
                        "school_ids": school_ids_norm,
                        "active": True,
                        "created_at": now,
                        "updated_at": now,
                        "last_notified_at": None,
                    }
                )
            data["subscribers"] = subs
            return Subscriber(email=email_norm, school_ids=school_ids_norm)

        return self._update_file_atomic(updater)

    def unsubscribe(self, email: str) -> bool:
        """Deactivate a subscriber.

        Returns:
            True if a subscriber was found and deactivated.
        """
        email_norm = self._validate_email(email)
        now = datetime.utcnow().isoformat()

        if self._collection is not None:
            result = self._collection.update_one(
                {"email": email_norm},
                {"$set": {"active": False, "updated_at": now}},
            )
            return bool(result.matched_count)

        def updater(data: dict):
            subs = data.get("subscribers", [])
            changed = False
            for s in subs:
                if (s.get("email") or "").lower() == email_norm:
                    s["active"] = False
                    s["updated_at"] = now
                    changed = True
                    break
            data["subscribers"] = subs
            return changed

        return bool(self._update_file_atomic(updater))

    def list_active(self) -> List[Subscriber]:
        """List active subscribers."""
        if self._collection is not None:
            docs = list(self._collection.find({"active": True}, {"_id": 0, "email": 1, "school_ids": 1}))
            return [Subscriber(email=d["email"], school_ids=d.get("school_ids")) for d in docs]

        data = self._read_file()
        subs = data.get("subscribers", [])
        active = [s for s in subs if s.get("active") is True]
        return [Subscriber(email=s.get("email", ""), school_ids=s.get("school_ids")) for s in active]
