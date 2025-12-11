"""Main Flask application factory and entry point."""
import logging
import os
from pathlib import Path

from flask import Flask

from .config import get_config
from .controllers import announcement_bp


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

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    return app


def main() -> None:
    """Run the Flask application."""
    config_name = os.getenv("FLASK_ENV", "development")
    app = create_app(config_name)
    config = get_config(config_name)

    app.run(
        debug=config.DEBUG,
        host=config.HOST,
        port=config.PORT,
    )


if __name__ == "__main__":
    main()
