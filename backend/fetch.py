#!/usr/bin/env python3
"""CLI script to fetch announcements from all schools and save to JSON."""
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.services import AnnouncementService


def main():
    """Fetch and save announcements."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    print("Starting announcement fetch...")
    service = AnnouncementService()

    try:
        count = service.fetch_and_save()
        print(f"\n✅ Successfully fetched and saved {count} announcements")
        print(f"📁 Data saved to: backend/data/announcements.json")

        last_updated = service.get_last_updated()
        if last_updated:
            print(f"🕐 Last updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    except Exception as exc:
        print(f"\n❌ Error: {exc}")
        logging.exception("Fetch failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
