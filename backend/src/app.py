"""Main Flask application factory and entry point."""
import logging
import os
from pathlib import Path
from typing import Optional

from flask import Flask

from .config import get_config
from .controllers import announcement_bp, subscriber_bp
from .services import AnnouncementService

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except Exception:  # pragma: no cover - optional dependency at runtime
    BackgroundScheduler = None  # type: ignore
    CronTrigger = None  # type: ignore


def create_app(config_name: str = "default") -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: Name of the configuration to use.

    Returns:
        Configured Flask application.
    """
    # Determine template and static folder paths
    # Templates and static files are served from frontend during development
    # In production, they should be built and copied to backend/templates and backend/static
    backend_dir = Path(__file__).parent.parent
    template_folder = backend_dir / "templates"
    static_folder = backend_dir / "static"

    app = Flask(
        __name__,
        template_folder=str(template_folder),
        static_folder=str(static_folder),
    )

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Register blueprints
    app.register_blueprint(announcement_bp)
    app.register_blueprint(subscriber_bp)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    return app


def _start_scheduler(service: AnnouncementService) -> Optional[BackgroundScheduler]:
    """Start a daily fetch scheduler if APScheduler is available."""
    if not BackgroundScheduler or not CronTrigger:
        logging.warning("APScheduler not installed; background fetch scheduler disabled.")
        return None

    scheduler = BackgroundScheduler(daemon=True)

    def job():
        try:
            count = service.fetch_and_save()
            logging.info("Scheduled fetch completed: %s announcements", count)
        except Exception as exc:  # noqa: BLE001
            logging.error("Scheduled fetch failed: %s", exc)

    # Run daily at 02:00 UTC
    scheduler.add_job(job, CronTrigger(hour=2, minute=0))
    scheduler.start()
    logging.info("Background scheduler started (daily fetch at 02:00 UTC)")
    return scheduler


def main() -> None:
    """Run the Flask application."""
    config_name = os.getenv("FLASK_ENV", "development")
    app = create_app(config_name)
    config = get_config(config_name)

    # Avoid double-start under the Werkzeug reloader
    is_reloader = os.getenv("WERKZEUG_RUN_MAIN") == "true"
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() in ("1", "true", "yes")
    initial_fetch = os.getenv("INITIAL_FETCH", "true").lower() in ("1", "true", "yes")
    scheduler = None
    service = AnnouncementService()

    # Run initial fetch once on startup in non-debug, non-reloader mode if enabled
    if initial_fetch and not config.DEBUG and not is_reloader:
        try:
            count = service.fetch_and_save()
            logging.info("Initial fetch completed at startup: %s announcements", count)
        except Exception as exc:  # noqa: BLE001
            logging.error("Initial fetch failed at startup: %s", exc)

    if scheduler_enabled and not is_reloader:
        scheduler = _start_scheduler(service)

    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
    )

    if scheduler:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
