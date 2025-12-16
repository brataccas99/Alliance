"""JSON file storage utilities."""
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional

from .blob_json_store import BlobJsonStore


class JSONStorage:
    """Handle JSON file storage for announcements."""

    def __init__(self, data_file: str = "announcements.json"):
        """Initialize JSON storage.

        Args:
            data_file: Name of the JSON data file.
        """
        self.data_path = Path(__file__).parent.parent.parent / "data" / data_file
        self._store = BlobJsonStore(local_path=self.data_path, object_name=data_file)
        self._ensure_data_file()

    def _ensure_data_file(self) -> None:
        """Ensure data file and directory exist."""
        if os.getenv("GCS_BUCKET"):
            # For GCS, don't pre-create on disk; just attempt a load on first use.
            return
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            self._write_data({"last_updated": None, "announcements": []})

    def _serialize_date(self, obj):
        """Serialize date objects to ISO format.

        Args:
            obj: Object to serialize.

        Returns:
            ISO format string for dates, original object otherwise.
        """
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return obj

    def _deserialize_date(self, date_str: str) -> Optional[date]:
        """Deserialize ISO date string to date object.

        Args:
            date_str: ISO format date string.

        Returns:
            date object or None if parsing fails.
        """
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None

    def _read_data(self) -> Dict:
        """Read data from JSON file.

        Returns:
            Dictionary with announcements data.
        """
        default = {"last_updated": None, "announcements": []}
        try:
            return self._store.load(default)
        except json.JSONDecodeError as exc:
            logging.error(f"Invalid JSON in data file: {exc}")
            return default

    def _write_data(self, data: Dict) -> None:
        """Write data to JSON file.

        Args:
            data: Dictionary to write.
        """
        try:
            text = json.dumps(data, indent=2, ensure_ascii=False, default=self._serialize_date)
            # BlobJsonStore expects dict; keep same serialization output.
            self._store.save(json.loads(text))
            logging.info("Data written to %s", self.data_path)
        except Exception as exc:
            logging.error(f"Failed to write data file: {exc}")

    def save_announcements(self, announcements: List[Dict]) -> None:
        """Save announcements to JSON file.

        Args:
            announcements: List of announcement dictionaries.
        """
        # Serialize dates
        serialized = []
        for ann in announcements:
            ann_copy = dict(ann)
            if isinstance(ann_copy.get("date"), date):
                ann_copy["date"] = ann_copy["date"].isoformat()
            serialized.append(ann_copy)

        data = {
            "last_updated": datetime.utcnow().isoformat(),
            "announcements": serialized
        }
        self._write_data(data)

    def load_announcements(self) -> List[Dict]:
        """Load announcements from JSON file.

        Returns:
            List of announcement dictionaries with deserialized dates.
        """
        data = self._read_data()
        announcements = data.get("announcements", [])

        # Deserialize dates
        for ann in announcements:
            if "date" in ann and isinstance(ann["date"], str):
                ann["date"] = self._deserialize_date(ann["date"])

        return announcements

    def get_last_updated(self) -> Optional[datetime]:
        """Get last update timestamp.

        Returns:
            Last update datetime or None.
        """
        data = self._read_data()
        last_updated = data.get("last_updated")
        if last_updated:
            try:
                return datetime.fromisoformat(last_updated)
            except (ValueError, TypeError):
                return None
        return None

    def clear_announcements(self) -> None:
        """Clear all announcements from storage."""
        self._write_data({"last_updated": None, "announcements": []})
        logging.info("Cleared all announcements from storage")
