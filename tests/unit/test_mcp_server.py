"""Unit tests for MCP server tool executor."""

import pytest

from chatassistant_retail.tools.mcp_server import ToolExecutor


class TestToolExecutor:
    """Test tool executor functionality."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_empty_name(self):
        """Test that empty tool name returns proper error."""
        executor = ToolExecutor()
        result = await executor.execute_tool("", {})

        assert result["success"] is False
        assert "Tool name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_none_name(self):
        """Test that None tool name returns proper error."""
        executor = ToolExecutor()
        result = await executor.execute_tool(None, {})

        assert result["success"] is False
        assert "Tool name is required" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_tool_with_unknown_name(self):
        """Test that unknown tool name returns proper error."""
        executor = ToolExecutor()
        result = await executor.execute_tool("nonexistent_tool", {})

        assert result["success"] is False
        assert "Unknown tool: nonexistent_tool" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_query_inventory_tool(self):
        """Test executing query_inventory tool."""
        executor = ToolExecutor()
        result = await executor.execute_tool("query_inventory", {"low_stock": True, "threshold": 10})

        assert result["success"] is True
        assert "summary" in result
        assert "products" in result

    @pytest.mark.asyncio
    async def test_execute_calculate_reorder_point_tool(self):
        """Test executing calculate_reorder_point tool."""
        executor = ToolExecutor()
        result = await executor.execute_tool("calculate_reorder_point", {"sku": "SKU-10000"})

        assert result["success"] is True
        assert "product" in result or "error" in result  # May fail if SKU doesn't exist

    @pytest.mark.asyncio
    async def test_execute_create_purchase_order_tool(self):
        """Test executing create_purchase_order tool."""
        executor = ToolExecutor()
        result = await executor.execute_tool(
            "create_purchase_order", {"sku": "SKU-10000", "quantity": 100}
        )

        assert result["success"] is True
        # Check for either purchase order creation or error response
        assert "purchase_order" in result or "error" in result or "message" in result

    @pytest.mark.asyncio
    async def test_tool_executor_initializes_all_tools(self):
        """Test that tool executor initializes with all expected tools."""
        executor = ToolExecutor()

        assert len(executor.tools) == 3
        assert "query_inventory" in executor.tools
        assert "calculate_reorder_point" in executor.tools
        assert "create_purchase_order" in executor.tools
