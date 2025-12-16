"""JSON storage to local filesystem or Google Cloud Storage (GCS)."""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class JsonLoadResult:
    data: Dict[str, Any]
    generation: int


class BlobJsonStore:
    """Read/write a single JSON document from local disk or GCS.

    If `GCS_BUCKET` is set and `google-cloud-storage` is installed, this store uses
    `gs://$GCS_BUCKET/$GCS_PREFIX/<object_name>`.
    """

    def __init__(self, *, local_path: Path, object_name: str):
        self._local_path = local_path
        self._object_name = object_name.lstrip("/")
        self._bucket = (os.getenv("GCS_BUCKET", "") or "").strip()
        self._prefix = (os.getenv("GCS_PREFIX", "data/") or "data/").lstrip("/")
        if self._prefix and not self._prefix.endswith("/"):
            self._prefix += "/"

    def _use_gcs(self) -> bool:
        return bool(self._bucket)

    def _gcs_object(self) -> str:
        return f"{self._prefix}{self._object_name}"

    def _get_client(self):
        try:
            from google.cloud import storage  # type: ignore
        except Exception:  # pragma: no cover - optional dependency
            return None
        try:
            return storage.Client()
        except Exception:  # pragma: no cover - environment dependent
            return None

    def load(self, default: Dict[str, Any]) -> Dict[str, Any]:
        return self.load_with_generation(default).data

    def load_with_generation(self, default: Dict[str, Any]) -> JsonLoadResult:
        """Load JSON, returning a generation for optimistic concurrency (GCS only)."""
        if self._use_gcs():
            client = self._get_client()
            if not client:
                logging.warning("GCS_BUCKET set but google-cloud-storage not available; using local JSON.")
            else:
                try:
                    bucket = client.bucket(self._bucket)
                    blob = bucket.blob(self._gcs_object())
                    if not blob.exists():
                        return JsonLoadResult(data=dict(default), generation=0)
                    text = blob.download_as_text(encoding="utf-8")
                    data = json.loads(text) if text else dict(default)
                    blob.reload()
                    generation = int(blob.generation or 0)
                    return JsonLoadResult(data=data, generation=generation)
                except Exception as exc:  # noqa: BLE001
                    logging.warning("GCS JSON load failed (%s); falling back to local: %s", self._gcs_object(), exc)

        try:
            if not self._local_path.exists():
                return JsonLoadResult(data=dict(default), generation=0)
            with open(self._local_path, "r", encoding="utf-8") as f:
                return JsonLoadResult(data=json.load(f), generation=0)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Local JSON load failed (%s): %s", self._local_path, exc)
            return JsonLoadResult(data=dict(default), generation=0)

    def save(self, data: Dict[str, Any]) -> None:
        self.save_with_generation(data, generation=None)

    def save_with_generation(self, data: Dict[str, Any], generation: int | None, *, retries: int = 5) -> None:
        """Save JSON, optionally using GCS generation match for safe updates."""
        text = json.dumps(data, indent=2, ensure_ascii=False)

        if self._use_gcs():
            client = self._get_client()
            if not client:
                logging.warning("GCS_BUCKET set but google-cloud-storage not available; using local JSON.")
            else:
                bucket = client.bucket(self._bucket)
                blob = bucket.blob(self._gcs_object())
                for attempt in range(retries):
                    try:
                        if generation is None:
                            blob.upload_from_string(text, content_type="application/json")
                        else:
                            blob.upload_from_string(
                                text,
                                content_type="application/json",
                                if_generation_match=int(generation),
                            )
                        return
                    except Exception as exc:  # noqa: BLE001
                        # Retry on precondition / transient errors.
                        if attempt >= retries - 1:
                            logging.error("GCS JSON save failed (%s): %s", self._gcs_object(), exc)
                            return
                        time.sleep(0.2 * (attempt + 1))
                        try:
                            # Refresh generation and retry.
                            blob.reload()
                            generation = int(blob.generation or 0)
                        except Exception:
                            generation = 0

        try:
            self._local_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._local_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as exc:  # noqa: BLE001
            logging.error("Local JSON save failed (%s): %s", self._local_path, exc)

