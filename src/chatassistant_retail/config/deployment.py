"""Deployment mode configuration and factory patterns."""

import logging
from typing import TYPE_CHECKING

from .settings import Settings, get_settings

if TYPE_CHECKING:
    from chatassistant_retail.state.session_store import SessionStore

logger = logging.getLogger(__name__)


def get_session_store(settings: Settings | None = None) -> "SessionStore":
    """
    Factory function to get the appropriate session store based on deployment mode.

    Args:
        settings: Optional Settings instance. If None, will use get_settings().

    Returns:
        SessionStore: Appropriate session store implementation

    Raises:
        ValueError: If deployment mode is invalid or required dependencies are missing
    """
    if settings is None:
        settings = get_settings()

    if settings.deployment_mode == "hf_spaces":
        logger.info("Using in-memory session store for HuggingFace Spaces deployment")
        from chatassistant_retail.state.memory_store import MemorySessionStore

        return MemorySessionStore()

    elif settings.deployment_mode == "local":
        # Try Redis first, then PostgreSQL, fallback to in-memory
        if settings.redis_url:
            logger.info(f"Using Redis session store at {settings.redis_url}")
            try:
                from chatassistant_retail.state.persistent_store import RedisSessionStore

                return RedisSessionStore(redis_url=settings.redis_url)
            except ImportError as e:
                logger.error(f"Redis dependencies not available: {e}. Falling back to in-memory store.")
                from chatassistant_retail.state.memory_store import MemorySessionStore

                return MemorySessionStore()

        elif settings.postgres_url:
            logger.info(f"Using PostgreSQL session store at {settings.postgres_url}")
            try:
                from chatassistant_retail.state.persistent_store import PostgreSQLSessionStore

                return PostgreSQLSessionStore(db_url=settings.postgres_url)
            except ImportError as e:
                logger.error(f"PostgreSQL dependencies not available: {e}. Falling back to in-memory store.")
                from chatassistant_retail.state.memory_store import MemorySessionStore

                return MemorySessionStore()

        else:
            logger.warning("Local deployment mode but no Redis/PostgreSQL URL provided. Using in-memory session store.")
            from chatassistant_retail.state.memory_store import MemorySessionStore

            return MemorySessionStore()

    else:
        raise ValueError(f"Invalid deployment mode: {settings.deployment_mode}")


def configure_logging(settings: Settings | None = None) -> None:
    """
    Configure logging based on deployment mode.

    Args:
        settings: Optional Settings instance. If None, will use get_settings().
    """
    if settings is None:
        settings = get_settings()

    if settings.deployment_mode == "hf_spaces":
        # HuggingFace Spaces: Less verbose logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        # Local development: More verbose logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        )

    logger.info(f"Logging configured for deployment mode: {settings.deployment_mode}")


def get_gradio_server_config(settings: Settings | None = None) -> dict:
    """
    Get Gradio server configuration based on deployment mode.

    Args:
        settings: Optional Settings instance. If None, will use get_settings().

    Returns:
        dict: Gradio server configuration
    """
    if settings is None:
        settings = get_settings()

    if settings.deployment_mode == "hf_spaces":
        return {
            "server_name": "0.0.0.0",  # Listen on all interfaces for HF Spaces
            "server_port": 7860,  # HF Spaces standard port
            "share": False,  # No need for share link on HF Spaces
            "show_error": True,  # Show errors to users
        }
    else:
        return {
            "server_name": "127.0.0.1",  # Localhost only for local dev
            "server_port": 7860,
            "share": False,  # Can enable for tunneling during development
            "show_error": True,
            "debug": True,  # Enable debug mode for local development
        }
