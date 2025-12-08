"""LangFuse client wrapper for observability."""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Global LangFuse client instance
_langfuse_client = None


def get_langfuse_client():
    """
    Get singleton LangFuse client instance.

    Returns:
        Langfuse client instance or None if not configured

    Raises:
        ImportError: If langfuse package is not installed
    """
    global _langfuse_client

    if _langfuse_client is not None:
        return _langfuse_client

    try:
        from langfuse import Langfuse

        from chatassistant_retail.config.settings import Settings

        settings = Settings()

        if not settings.langfuse_enabled:
            logger.info("LangFuse is disabled in settings")
            return None

        # Initialize LangFuse client
        _langfuse_client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )

        logger.info(f"Initialized LangFuse client with host: {settings.langfuse_host}")
        return _langfuse_client

    except ImportError:
        logger.warning("langfuse package not installed. Install with: pip install langfuse")
        return None
    except Exception as e:
        logger.error(f"Error initializing LangFuse client: {e}")
        return None


def create_span(name: str, input_data: Any = None, metadata: dict | None = None):
    """
    Create a new LangFuse span.

    Note: The returned span must be explicitly ended by calling span.end() when done.

    Args:
        name: Span name
        input_data: Input data for the span
        metadata: Additional metadata

    Returns:
        LangfuseSpan object or None if LangFuse not available.
        Must call .end() on the returned span when operation completes.

    Example:
        span = create_span(name="my_operation", input_data={"key": "value"})
        try:
            # Do work
            span.update(output={"result": "success"})
        finally:
            span.end()
    """
    client = get_langfuse_client()
    if not client:
        return None

    try:
        span = client.start_span(name=name, input=input_data, metadata=metadata)
        return span
    except Exception as e:
        logger.error(f"Error creating span: {e}")
        return None


def log_event(
    name: str,
    level: str = "INFO",
    input_data: Any = None,
    output_data: Any = None,
    metadata: dict | None = None,
):
    """
    Log an event to LangFuse.

    The event will be associated with the current span in the context.
    If no active span exists, the event will be created as a standalone event.

    Args:
        name: Event name
        level: Log level (INFO, WARNING, ERROR)
        input_data: Input data
        output_data: Output data
        metadata: Additional metadata

    Example:
        log_event(
            name="user_action",
            level="INFO",
            input_data={"action": "click"},
            metadata={"user_id": "123"}
        )
    """
    client = get_langfuse_client()
    if not client:
        return

    try:
        client.create_event(
            name=name,
            level=level,
            input=input_data,
            output=output_data,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Error logging event: {e}")


def flush_langfuse():
    """Flush LangFuse client to ensure all traces are sent."""
    client = get_langfuse_client()
    if client:
        try:
            client.flush()
            logger.debug("Flushed LangFuse client")
        except Exception as e:
            logger.error(f"Error flushing LangFuse client: {e}")
