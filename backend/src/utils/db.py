"""Database utilities for MongoDB connection."""
import logging
import os
from functools import lru_cache
from typing import Optional

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import PyMongoError


@lru_cache
def get_client() -> Optional[MongoClient]:
    """Get MongoDB client instance.

    Returns:
        MongoClient instance if connection successful, None otherwise.
    """
    uri = os.getenv("MONGO_URI")
    if not uri:
        logging.info("MONGO_URI not set, using in-memory data only.")
        return None
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        return client
    except PyMongoError as exc:
        logging.warning("Mongo connection failed, using fallback: %s", exc)
        return None


def get_collection() -> Optional[Collection]:
    """Get announcements collection from MongoDB.

    Returns:
        MongoDB collection instance if available, None otherwise.
    """
    client = get_client()
    if not client:
        return None
    try:
        db = client.get_default_database()
        return db.get_collection("announcements")
    except Exception as exc:  # noqa: BLE001
        logging.warning("Mongo collection unavailable: %s", exc)
        return None
