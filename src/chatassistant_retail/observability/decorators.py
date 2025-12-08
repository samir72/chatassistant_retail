"""Tracing decorators for automatic observability."""

import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


def trace(name: str | None = None, trace_type: str = "function"):
    """
    Decorator to trace function execution with LangFuse.

    Args:
        name: Optional custom name for the trace (defaults to function name)
        trace_type: Type of trace (function, llm, rag, tool)

    Usage:
        @trace(name="custom_name", trace_type="llm")
        async def my_function(arg1, arg2):
            ...
    """

    def decorator(func: Callable) -> Callable:
        trace_name = name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            error = None
            result = None

            # Try to get LangFuse client
            try:
                from chatassistant_retail.observability.langfuse_client import (
                    get_langfuse_client,
                )

                client = get_langfuse_client()
            except Exception as e:
                logger.debug(f"LangFuse not available: {e}")
                client = None

            # Create span if client available
            span_obj = None
            if client:
                try:
                    span_obj = client.start_span(
                        name=trace_name,
                        metadata={
                            "type": trace_type,
                            "function": func.__name__,
                            "module": func.__module__,
                        },
                    )
                except Exception as e:
                    logger.debug(f"Error creating span: {e}")

            # Execute function
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                error = e
                raise
            finally:
                # Update and end span
                if span_obj:
                    try:
                        duration = time.time() - start_time
                        span_obj.update(
                            output={"result": str(result)[:1000] if result else None},
                            metadata={
                                "duration_seconds": duration,
                                "error": str(error) if error else None,
                            },
                        )
                        span_obj.end()  # End the span
                    except Exception as e:
                        logger.debug(f"Error updating/ending span: {e}")

            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            error = None
            result = None

            # Try to get LangFuse client
            try:
                from chatassistant_retail.observability.langfuse_client import (
                    get_langfuse_client,
                )

                client = get_langfuse_client()
            except Exception as e:
                logger.debug(f"LangFuse not available: {e}")
                client = None

            # Create span if client available
            span_obj = None
            if client:
                try:
                    span_obj = client.start_span(
                        name=trace_name,
                        metadata={
                            "type": trace_type,
                            "function": func.__name__,
                            "module": func.__module__,
                        },
                    )
                except Exception as e:
                    logger.debug(f"Error creating span: {e}")

            # Execute function
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                error = e
                raise
            finally:
                # Update and end span
                if span_obj:
                    try:
                        duration = time.time() - start_time
                        span_obj.update(
                            output={"result": str(result)[:1000] if result else None},
                            metadata={
                                "duration_seconds": duration,
                                "error": str(error) if error else None,
                            },
                        )
                        span_obj.end()  # End the span
                    except Exception as e:
                        logger.debug(f"Error updating/ending span: {e}")

            return result

        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
