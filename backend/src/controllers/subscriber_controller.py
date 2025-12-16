"""Subscriber controller for managing email subscriptions."""
import logging

from flask import Blueprint, jsonify, request

from ..services import SubscriberService

subscriber_bp = Blueprint("subscriber", __name__)
subscriber_service = SubscriberService()


@subscriber_bp.route("/api/subscribe", methods=["POST"])
def subscribe():
    """Subscribe an email address to announcement notifications."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    school_ids = payload.get("school_ids")
    try:
        subscriber = subscriber_service.subscribe(email=email, school_ids=school_ids)
        return jsonify(
            {
                "success": True,
                "subscriber": {"email": subscriber.email, "school_ids": subscriber.school_ids},
            }
        )
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logging.error("Subscribe failed: %s", exc)
        return jsonify({"success": False, "error": "Subscription failed"}), 500


@subscriber_bp.route("/api/unsubscribe", methods=["POST"])
def unsubscribe():
    """Unsubscribe an email address from announcement notifications."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    try:
        removed = subscriber_service.unsubscribe(email=email)
        return jsonify({"success": True, "unsubscribed": removed})
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:  # noqa: BLE001
        logging.error("Unsubscribe failed: %s", exc)
        return jsonify({"success": False, "error": "Unsubscribe failed"}), 500


@subscriber_bp.route("/unsubscribe", methods=["GET"])
def unsubscribe_link():
    """Simple unsubscribe link for emails."""
    email = (request.args.get("email") or "").strip()
    try:
        removed = subscriber_service.unsubscribe(email=email)
        if removed:
            return "You have been unsubscribed.", 200
        return "No active subscription found for this email.", 404
    except ValueError:
        return "Invalid email.", 400
