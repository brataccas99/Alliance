"""Announcement controller for handling HTTP requests."""
import logging
from datetime import date

from flask import Blueprint, abort, render_template, request, jsonify

from ..services import AnnouncementService

announcement_bp = Blueprint("announcement", __name__)
service = AnnouncementService()


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

    return render_template(
        "index.html",
        announcements=data,
        query=query,
        sort=sort,
        order=order,
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


@announcement_bp.route("/api/fetch", methods=["POST"])
def fetch_announcements():
    """API endpoint to trigger fetching announcements from all schools."""
    try:
        count = service.fetch_and_save()
        return jsonify({
            "success": True,
            "message": f"Fetched {count} announcements",
            "count": count
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
