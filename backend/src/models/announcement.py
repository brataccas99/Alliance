"""Announcement model definition."""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class Announcement:
    """Represents a school announcement."""

    id: int
    title: str
    category: str
    date: date
    status: str
    school_id: str = ""
    school_name: str = ""
    tags: List[str] = field(default_factory=list)
    source: str = ""
    link: str = ""
    highlight: bool = False
    summary: str = ""
    body: str = ""

    def to_dict(self) -> dict:
        """Convert announcement to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "date": self.date,
            "status": self.status,
            "school_id": self.school_id,
            "school_name": self.school_name,
            "tags": self.tags,
            "source": self.source,
            "link": self.link,
            "highlight": self.highlight,
            "summary": self.summary,
            "body": self.body,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Announcement":
        """Create announcement from dictionary."""
        return cls(
            id=data.get("id", 0),
            title=data.get("title", ""),
            category=data.get("category", ""),
            date=data.get("date", date.min),
            status=data.get("status", ""),
            school_id=data.get("school_id", ""),
            school_name=data.get("school_name", ""),
            tags=data.get("tags", []),
            source=data.get("source", ""),
            link=data.get("link", ""),
            highlight=data.get("highlight", False),
            summary=data.get("summary", ""),
            body=data.get("body", ""),
        )
