"""Metrics dashboard components for Gradio UI."""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def format_metrics_for_display(metrics: dict[str, Any]) -> tuple[int, float, int, float]:
    """
    Format metrics for Gradio Number components.

    Args:
        metrics: Metrics dictionary from MetricsCollector

    Returns:
        Tuple of (total_queries, avg_response_time, tool_calls, success_rate)
    """
    total_queries = metrics.get("total_queries", 0)
    avg_response_time = metrics.get("avg_response_time", 0.0)
    tool_calls = metrics.get("tool_calls_count", 0)
    success_rate = metrics.get("success_rate", 100.0)

    return total_queries, avg_response_time, tool_calls, success_rate


def format_activity_log(metrics: dict[str, Any]) -> list[list[str]]:
    """
    Format recent activity for Gradio Dataframe.

    Args:
        metrics: Metrics dictionary from MetricsCollector

    Returns:
        List of rows for dataframe [timestamp, action, status]
    """
    recent_activity = metrics.get("recent_activity", [])

    if not recent_activity:
        return [["No recent activity", "", ""]]

    rows = []
    for activity in recent_activity[:10]:  # Show last 10
        timestamp = activity.get("timestamp", "")
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            formatted_time = dt.strftime("%H:%M:%S")
        except Exception:
            formatted_time = timestamp[:19] if len(timestamp) > 19 else timestamp

        name = activity.get("name", "Unknown")
        action_type = activity.get("type", "function")
        status = activity.get("status", "success")

        # Format status with emoji
        status_emoji = "✅" if status == "success" else "❌"
        action_label = f"{action_type}: {name}"

        rows.append([formatted_time, action_label, f"{status_emoji} {status}"])

    return rows


def create_metrics_summary(metrics: dict[str, Any]) -> str:
    """
    Create summary text for metrics.

    Args:
        metrics: Metrics dictionary from MetricsCollector

    Returns:
        Formatted summary string
    """
    total_queries = metrics.get("total_queries", 0)
    avg_response_time = metrics.get("avg_response_time", 0.0)
    tool_calls = metrics.get("tool_calls_count", 0)
    error_count = metrics.get("error_count", 0)
    success_rate = metrics.get("success_rate", 100.0)

    summary = f"""📊 **System Metrics Summary**

**Performance:**
- Total Queries: {total_queries}
- Avg Response Time: {avg_response_time:.3f}s
- Tool Calls: {tool_calls}

**Reliability:**
- Success Rate: {success_rate:.1f}%
- Error Count: {error_count}

Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    return summary


def get_empty_metrics() -> dict[str, Any]:
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


def format_metric_change(current: float, previous: float) -> str:
    """
    Format metric change with trend indicator.

    Args:
        current: Current metric value
        previous: Previous metric value

    Returns:
        Formatted change string with arrow
    """
    if previous == 0:
        return "—"

    change = current - previous
    percent_change = (change / previous) * 100

    if change > 0:
        return f"↑ {abs(percent_change):.1f}%"
    elif change < 0:
        return f"↓ {abs(percent_change):.1f}%"
    else:
        return "→ 0%"
