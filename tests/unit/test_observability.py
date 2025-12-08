"""Unit tests for observability module."""

from unittest.mock import MagicMock, patch

import pytest


class TestLangFuseClient:
    """Test LangFuse client wrapper."""

    @patch("chatassistant_retail.config.settings.Settings")
    def test_get_langfuse_client_disabled(self, mock_settings):
        """Test getting LangFuse client when disabled."""
        # Reset global client
        import chatassistant_retail.observability.langfuse_client as lf_module

        lf_module._langfuse_client = None

        # Mock settings with disabled LangFuse
        settings_instance = MagicMock()
        settings_instance.langfuse_enabled = False
        mock_settings.return_value = settings_instance

        from chatassistant_retail.observability import get_langfuse_client

        client = get_langfuse_client()

        assert client is None

        # Reset global
        lf_module._langfuse_client = None


class TestTraceDecorator:
    """Test tracing decorator."""

    @pytest.mark.asyncio
    async def test_trace_decorator_async_function(self):
        """Test trace decorator on async function."""
        from chatassistant_retail.observability import trace

        @trace(name="test_function", trace_type="function")
        async def test_func(x, y):
            return x + y

        result = await test_func(2, 3)
        assert result == 5

    def test_trace_decorator_sync_function(self):
        """Test trace decorator on sync function."""
        from chatassistant_retail.observability import trace

        @trace(name="test_sync", trace_type="function")
        def test_func(x, y):
            return x * y

        result = test_func(4, 5)
        assert result == 20

    @pytest.mark.asyncio
    async def test_trace_decorator_with_error(self):
        """Test trace decorator when function raises error."""
        from chatassistant_retail.observability import trace

        @trace(name="failing_function", trace_type="function")
        async def failing_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await failing_func()


class TestMetricsCollector:
    """Test metrics collector."""

    def test_metrics_collector_no_client(self):
        """Test metrics collector without LangFuse client."""
        from chatassistant_retail.observability import MetricsCollector

        collector = MetricsCollector(langfuse_client=None)
        metrics = collector.get_dashboard_data()

        assert metrics["total_queries"] == 0
        assert metrics["avg_response_time"] == 0.0
        assert metrics["tool_calls_count"] == 0
        assert metrics["error_count"] == 0
        assert metrics["success_rate"] == 100.0
        assert metrics["recent_activity"] == []

    def test_metrics_collector_with_client(self):
        """Test metrics collector with mocked client."""
        from chatassistant_retail.observability import MetricsCollector

        mock_client = MagicMock()
        collector = MetricsCollector(langfuse_client=mock_client)
        metrics = collector.get_dashboard_data()

        # Should return empty metrics since we don't have real traces
        assert isinstance(metrics, dict)
        assert "total_queries" in metrics
        assert "avg_response_time" in metrics
        assert "tool_calls_count" in metrics

    def test_get_empty_metrics_structure(self):
        """Test empty metrics structure."""
        from chatassistant_retail.observability import MetricsCollector

        collector = MetricsCollector()
        metrics = collector._get_empty_metrics()

        assert metrics == {
            "total_queries": 0,
            "avg_response_time": 0.0,
            "tool_calls_count": 0,
            "recent_activity": [],
            "error_count": 0,
            "success_rate": 100.0,
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
