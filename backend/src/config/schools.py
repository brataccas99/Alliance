"""School configuration loader from JSON."""
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class School:
    """Represents a school configuration."""

    id: str
    name: str
    base_url: str
    pnrr_url: str
    city: str = "Salerno"
    active: bool = True


def load_schools_from_json() -> List[School]:
    """Load schools from JSON configuration file.

    Returns:
        List of School objects.
    """
    config_path = Path(__file__).parent.parent.parent / "config" / "schools.json"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        schools = []
        for school_data in data.get("schools", []):
            school = School(
                id=school_data["id"],
                name=school_data["name"],
                base_url=school_data["base_url"],
                pnrr_url=school_data["pnrr_url"],
                city=school_data.get("city", "Salerno"),
                active=school_data.get("active", True),
            )
            schools.append(school)

        logging.info(f"Loaded {len(schools)} schools from configuration")
        return schools

    except FileNotFoundError:
        logging.error(f"Schools configuration file not found: {config_path}")
        return []
    except json.JSONDecodeError as exc:
        logging.error(f"Invalid JSON in schools configuration: {exc}")
        return []
    except Exception as exc:
        logging.error(f"Error loading schools configuration: {exc}")
        return []


def get_active_schools() -> List[School]:
    """Get list of active schools.

    Returns:
        List of active School objects.
    """
    schools = load_schools_from_json()
    return [school for school in schools if school.active]


def get_school_by_id(school_id: str) -> School | None:
    """Get school by ID.

    Args:
        school_id: School identifier.

    Returns:
        School object or None if not found.
    """
    schools = load_schools_from_json()
    return next((school for school in schools if school.id == school_id), None)
