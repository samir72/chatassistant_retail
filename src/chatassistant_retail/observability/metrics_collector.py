"""Metrics collection for dashboard display."""

import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects metrics from LangFuse for dashboard display.

    Queries LangFuse API for recent traces and aggregates metrics.
    """

    def __init__(self, langfuse_client=None):
        """
        Initialize metrics collector.

        Args:
            langfuse_client: LangFuse client instance (optional)
        """
        self.client = langfuse_client

    def get_dashboard_data(self, hours: int = 24) -> dict[str, Any]:
        """
        Get aggregated metrics for dashboard display.

        Args:
            hours: Number of hours to look back (default: 24)

        Returns:
            Dictionary with dashboard metrics:
            {
                "total_queries": int,
                "avg_response_time": float,
                "tool_calls_count": int,
                "recent_activity": list[dict],
                "error_count": int,
                "success_rate": float,
            }
        """
        if not self.client:
            return self._get_empty_metrics()

        try:
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            # Fetch traces from LangFuse
            traces = self._fetch_traces(start_time, end_time)

            # Aggregate metrics
            metrics = self._aggregate_metrics(traces)

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return self._get_empty_metrics()

    def _fetch_traces(self, start_time: datetime, end_time: datetime) -> list:
        """
        Fetch traces from LangFuse API.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of trace objects
        """
        try:
            # Note: LangFuse Python SDK doesn't have a direct query method
            # In production, you would use the LangFuse REST API
            # For now, return empty list
            logger.warning("Trace fetching not fully implemented - would use LangFuse REST API")
            return []

        except Exception as e:
            logger.error(f"Error fetching traces: {e}")
            return []

    def _aggregate_metrics(self, traces: list) -> dict[str, Any]:
        """
        Aggregate metrics from traces.

        Args:
            traces: List of trace objects

        Returns:
            Aggregated metrics dictionary
        """
        total_queries = len(traces)
        total_duration = 0.0
        tool_calls = 0
        errors = 0
        recent_activity = []

        for trace in traces:
            # Extract duration
            if hasattr(trace, "metadata") and "duration_seconds" in trace.metadata:
                total_duration += trace.metadata["duration_seconds"]

            # Count tool calls
            if hasattr(trace, "metadata") and trace.metadata.get("type") == "tool":
                tool_calls += 1

            # Count errors
            if hasattr(trace, "metadata") and trace.metadata.get("error"):
                errors += 1

            # Add to recent activity
            if len(recent_activity) < 10:
                recent_activity.append(
                    {
                        "timestamp": getattr(trace, "timestamp", datetime.now()).isoformat(),
                        "name": getattr(trace, "name", "Unknown"),
                        "type": getattr(trace, "metadata", {}).get("type", "function"),
                        "status": "error" if hasattr(trace, "metadata") and trace.metadata.get("error") else "success",
                    }
                )

        # Calculate averages
        avg_response_time = total_duration / total_queries if total_queries > 0 else 0.0
        success_rate = (total_queries - errors) / total_queries * 100 if total_queries > 0 else 100.0

        return {
            "total_queries": total_queries,
            "avg_response_time": round(avg_response_time, 3),
            "tool_calls_count": tool_calls,
            "recent_activity": recent_activity,
            "error_count": errors,
            "success_rate": round(success_rate, 1),
        }

    def _get_empty_metrics(self) -> dict[str, Any]:
        """
        Get empty metrics structure.

        Returns:
            Empty metrics dictionary
        """
        return {
            "total_queries": 0,
            "avg_response_time": 0.0,
            "tool_calls_count": 0,
            "recent_activity": [],
            "error_count": 0,
            "success_rate": 100.0,
        }

    def get_trace_details(self, trace_id: str) -> dict[str, Any] | None:
        """
        Get detailed information for a specific trace.

        Args:
            trace_id: Trace identifier

        Returns:
            Trace details or None if not found
        """
        if not self.client:
            return None

        try:
            # In production, fetch from LangFuse API
            logger.warning("Trace details fetching not fully implemented")
            return None
        except Exception as e:
            logger.error(f"Error fetching trace details: {e}")
            return None
