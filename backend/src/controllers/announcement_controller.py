"""Announcement controller for handling HTTP requests."""
import logging
from datetime import date

from flask import Blueprint, abort, render_template, request, jsonify, url_for

from ..services import AnnouncementService

announcement_bp = Blueprint("announcement", __name__)
service = AnnouncementService()

def _normalize_school_key(name: str) -> str:
    """Normalize school name to avoid duplicates caused by suffixes like ' - PNRR'."""
    base = (name or "").split(" - ")[0].strip()
    return base.lower()

# Minimal OpenAPI spec for exposed endpoints
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Alliance Announcements API",
        "version": "1.0.0",
        "description": "Endpoints for announcements, fetch status and triggers.",
    },
    "paths": {
        "/api/announcements": {
            "get": {
                "summary": "List announcements",
                "parameters": [
                    {
                        "in": "query",
                        "name": "school_id",
                        "schema": {"type": "string"},
                        "required": False,
                        "description": "Filter announcements by school id",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Announcements list",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "announcements": {
                                            "type": "array",
                                            "items": {"$ref": "#/components/schemas/Announcement"},
                                        },
                                        "count": {"type": "integer"},
                                        "last_updated": {"type": "string", "format": "date-time", "nullable": True},
                                    },
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/fetch": {
            "post": {
                "summary": "Trigger fetch of announcements",
                "responses": {
                    "200": {
                        "description": "Fetch started/completed",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/FetchResponse"}
                            }
                        },
                    },
                    "500": {
                        "description": "Fetch error",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
        "/api/fetch/status": {
            "get": {
                "summary": "Fetch progress",
                "responses": {
                    "200": {
                        "description": "Current progress",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Progress"}
                            }
                        },
                    }
                },
            }
        },
        "/api/subscribe": {
            "post": {
                "summary": "Subscribe to email notifications",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SubscribeRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Subscribed",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SubscribeResponse"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
        "/api/unsubscribe": {
            "post": {
                "summary": "Unsubscribe from email notifications",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/UnsubscribeRequest"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Unsubscribed",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UnsubscribeResponse"}
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid request",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        },
                    },
                },
            }
        },
    },
    "components": {
        "schemas": {
            "Announcement": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "body": {"type": "string"},
                    "link": {"type": "string"},
                    "category": {"type": "string"},
                    "source": {"type": "string"},
                    "school_id": {"type": "string"},
                    "school_name": {"type": "string"},
                    "city": {"type": "string", "nullable": True},
                    "date": {"type": "string", "format": "date-time"},
                    "status": {"type": "string", "example": "Open"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "highlight": {"type": "boolean"},
                    "attachments": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/Attachment"},
                    },
                },
                "required": ["id", "title", "link", "school_id", "school_name", "status", "highlight"],
            },
            "Attachment": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "label": {"type": "string"},
                    "type": {"type": "string", "example": "pdf"},
                },
            },
            "Progress": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "example": "running"},
                    "total": {"type": "integer"},
                    "current": {"type": "integer"},
                    "school": {"type": "string", "nullable": True},
                },
            },
            "FetchResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"},
                    "count": {"type": "integer"},
                    "stats": {"$ref": "#/components/schemas/FetchStats"},
                },
            },
            "FetchStats": {
                "type": "object",
                "properties": {
                    "last_run": {"type": "string", "format": "date-time", "nullable": True},
                    "total_count": {"type": "integer"},
                    "new_count": {"type": "integer"},
                    "emails_sent": {"type": "integer"},
                },
            },
            "SubscribeRequest": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "school_ids": {"type": "array", "items": {"type": "string"}, "nullable": True},
                },
                "required": ["email"],
            },
            "SubscribeResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "subscriber": {
                        "type": "object",
                        "properties": {
                            "email": {"type": "string"},
                            "school_ids": {"type": "array", "items": {"type": "string"}, "nullable": True},
                        },
                    },
                },
            },
            "UnsubscribeRequest": {
                "type": "object",
                "properties": {"email": {"type": "string"}},
                "required": ["email"],
            },
            "UnsubscribeResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "unsubscribed": {"type": "boolean"},
                },
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {"type": "string"},
                },
            },
        }
    },
}


@announcement_bp.route("/")
def index():
    """Render the main announcements page with filtering and sorting."""
    announcements = service.get_all_announcements()
    query = request.args.get("q", "").strip()
    sort = request.args.get("sort", "date")
    order = request.args.get("order", "desc")

    data = list(announcements)
    data.sort(key=lambda a: a.get("date", date.min), reverse=True)

    if query:
        lowered = query.lower()
        data = [
            a
            for a in data
            if lowered in a.get("title", "").lower()
            or lowered in a.get("summary", "").lower()
            or lowered in a.get("category", "").lower()
            or lowered in a.get("school_name", "").lower()
            or any(lowered in tag.lower() for tag in a.get("tags", []))
        ]

    sorters = {
        "title": lambda a: a.get("title", "").lower(),
        "school": lambda a: a.get("school_name", "").lower(),
        "city": lambda a: a.get("city", "").lower(),
        "category": lambda a: a.get("category", "").lower(),
        "date": lambda a: a.get("date", date.min),
        "status": lambda a: a.get("status", "").lower(),
    }

    sorter = sorters.get(sort, sorters["date"])
    reverse = order != "asc"
    data.sort(key=sorter, reverse=reverse)

    # Build unique schools list (normalize by stripping suffix after " - ")
    unique_schools = {}
    for ann in data:
        school_name = ann.get("school_name") or ""
        key = _normalize_school_key(school_name)
        if not key:
            continue
        if key not in unique_schools:
            base_name = (school_name.split(" - ")[0].strip()) or school_name
            unique_schools[key] = {
                "id": key,
                "name": base_name,
                "city": ann.get("city"),
            }

    return render_template(
        "index.html",
        announcements=data,
        query=query,
        sort=sort,
        order=order,
        unique_schools=list(unique_schools.values()),
    )


@announcement_bp.route("/announcement/<int:ann_id>")
def announcement_detail(ann_id: int):
    """Render the detail page for a specific announcement."""
    announcement = service.get_announcement_by_id(ann_id)
    if not announcement:
        abort(404)

    # Build navigation and derived metadata
    announcements = service.get_all_announcements()
    # Sort by date desc, fallback to id to keep stable order
    announcements.sort(key=lambda a: (a.get("date") or date.min, a.get("id") or 0), reverse=True)
    ids = [a.get("id") for a in announcements]
    try:
        idx = ids.index(ann_id)
    except ValueError:
        idx = -1

    prev_ann = announcements[idx - 1] if idx > 0 else None
    next_ann = announcements[idx + 1] if 0 <= idx < len(announcements) - 1 else None

    # Get attachments from announcement data
    attachments = announcement.get("attachments", [])

    # Also check if the main link is a PDF (backward compatibility)
    link = announcement.get("link", "")
    if isinstance(link, str) and link.lower().endswith(".pdf"):
        # Check if it's not already in attachments
        if not any(att.get("url") == link for att in attachments):
            attachments.insert(0, {
                "url": link,
                "label": "Documento PDF principale",
                "type": "pdf"
            })

    return render_template(
        "detail.html",
        announcement=announcement,
        prev_ann=prev_ann,
        next_ann=next_ann,
        attachments=attachments,
    )


@announcement_bp.route("/openapi.json")
def openapi_json():
    """Serve OpenAPI spec."""
    return jsonify(OPENAPI_SPEC)


@announcement_bp.route("/docs")
def swagger_ui():
    """Serve Swagger UI page."""
    return render_template("swagger.html", spec_url=url_for("announcement.openapi_json"))


@announcement_bp.route("/api/fetch", methods=["POST"])
def fetch_announcements():
    """API endpoint to trigger fetching announcements from all schools."""
    try:
        count = service.fetch_and_save()
        stats = service.get_last_fetch_stats()
        return jsonify({
            "success": True,
            "message": f"Fetched {count} announcements",
            "count": count,
            "stats": stats,
        })
    except Exception as exc:
        logging.error(f"Error fetching announcements: {exc}")
        return jsonify({
            "success": False,
            "error": str(exc)
        }), 500


@announcement_bp.route("/api/fetch/status")
def fetch_status():
    """API endpoint to get current fetch progress."""
    progress = service.get_progress()
    return jsonify(progress)


@announcement_bp.route("/api/announcements")
def api_get_announcements():
    """API endpoint to get all announcements as JSON."""
    school_id = request.args.get("school_id")

    if school_id:
        announcements = service.get_announcements_by_school(school_id)
    else:
        announcements = service.get_all_announcements()

    # Serialize dates for JSON
    serialized = []
    for ann in announcements:
        ann_copy = dict(ann)
        if isinstance(ann_copy.get("date"), date):
            ann_copy["date"] = ann_copy["date"].isoformat()
        serialized.append(ann_copy)

    return jsonify({
        "announcements": serialized,
        "count": len(serialized),
        "last_updated": service.get_last_updated().isoformat() if service.get_last_updated() else None
    })
