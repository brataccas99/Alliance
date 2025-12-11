"""Configuration package."""
import os


class Config:
    """Base configuration."""

    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    PORT = int(os.getenv("PORT", "5000"))
    HOST = os.getenv("HOST", "0.0.0.0")
    MONGO_URI = os.getenv("MONGO_URI", "")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str = "default") -> Config:
    """Get configuration by name.

    Args:
        config_name: Name of the configuration.

    Returns:
        Configuration class.
    """
    return config_by_name.get(config_name, DevelopmentConfig)
