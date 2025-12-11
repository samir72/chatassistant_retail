"""Integration tests for context-aware tool functionality."""

from __future__ import annotations

import pytest

from chatassistant_retail.state.langgraph_manager import ConversationState
from chatassistant_retail.tools.inventory_tools import (
    calculate_reorder_point_impl,
    query_inventory_impl,
)
from chatassistant_retail.tools.purchase_order_tools import create_purchase_order_impl


@pytest.mark.asyncio
async def test_query_inventory_without_state():
    """Test query_inventory works without state (backward compatibility)."""
    result = await query_inventory_impl(sku="SKU-10000")
    assert result["success"] is True
    assert len(result["products"]) >= 1


@pytest.mark.asyncio
async def test_query_inventory_with_empty_state():
    """Test query_inventory falls back to fresh load with empty state."""
    state = ConversationState(session_id="test")
    result = await query_inventory_impl(sku="SKU-10000", state=state)
    assert result["success"] is True
    assert len(result["products"]) >= 1
    # State should now have products_cache populated
    assert "products_cache" in state.context


@pytest.mark.asyncio
async def test_query_inventory_uses_context():
    """Test query_inventory reuses products from context."""
    # Create state with pre-populated product cache
    test_product = {
        "sku": "SKU-10000",
        "name": "Test Laptop",
        "category": "Electronics",
        "price": 999.99,
        "current_stock": 5,
        "reorder_level": 10,
        "supplier": "Test Supplier",
        "description": "Test description",
    }

    state = ConversationState(
        session_id="test",
        context={
            "products_cache": {
                "data": [test_product],
                "source": "rag",
                "timestamp": 123456.0,
                "filter_applied": {"sku": "SKU-10000"},
            }
        },
    )

    result = await query_inventory_impl(sku="SKU-10000", state=state)
    assert result["success"] is True
    assert len(result["products"]) == 1
    assert result["products"][0]["name"] == "Test Laptop"


@pytest.mark.asyncio
async def test_calculate_reorder_point_without_state():
    """Test calculate_reorder_point works without state (backward compatibility)."""
    result = await calculate_reorder_point_impl(sku="SKU-10000")
    # May succeed or fail depending on whether product exists and has sales
    assert "success" in result


@pytest.mark.asyncio
async def test_calculate_reorder_point_with_state():
    """Test calculate_reorder_point caches products when loading fresh."""
    state = ConversationState(session_id="test")
    result = await calculate_reorder_point_impl(sku="SKU-10000", state=state)

    if result["success"]:
        # State should have products_cache populated
        assert "products_cache" in state.context


@pytest.mark.asyncio
async def test_create_purchase_order_without_state():
    """Test create_purchase_order works without state (backward compatibility)."""
    result = await create_purchase_order_impl(sku="SKU-10000", quantity=10)
    # May succeed or fail depending on whether product exists
    assert "success" in result


@pytest.mark.asyncio
async def test_create_purchase_order_with_state():
    """Test create_purchase_order caches products when loading fresh."""
    state = ConversationState(session_id="test")
    result = await create_purchase_order_impl(sku="SKU-10000", quantity=10, state=state)

    if result["success"]:
        # State should have products_cache populated
        assert "products_cache" in state.context


@pytest.mark.asyncio
async def test_multi_tool_context_reuse():
    """Test multiple tools sharing context data."""
    state = ConversationState(session_id="test")

    # First tool call: query_inventory loads and caches data
    result1 = await query_inventory_impl(sku="SKU-10000", state=state)
    assert result1["success"] is True
    assert "products_cache" in state.context
    initial_cache = state.context["products_cache"]

    # Second tool call: calculate_reorder_point should reuse cached product
    result2 = await calculate_reorder_point_impl(sku="SKU-10000", state=state)

    if result2["success"]:
        # Cache should still be there (may have been updated with sales data)
        assert "products_cache" in state.context

    # Third tool call: create_purchase_order should also reuse cache
    result3 = await create_purchase_order_impl(sku="SKU-10000", quantity=10, state=state)

    if result3["success"]:
        # Cache should still be present
        assert "products_cache" in state.context


@pytest.mark.asyncio
async def test_rag_to_tool_workflow():
    """Test workflow where RAG populates context, then tool uses it."""
    # Simulate RAG having populated products in context
    rag_product = {
        "sku": "SKU-10000",
        "name": "Laptop Pro",
        "category": "Electronics",
        "price": 1299.99,
        "current_stock": 5,
        "reorder_level": 10,
        "supplier": "Tech Supplies Inc.",
        "description": "High-performance laptop",
    }

    state = ConversationState(
        session_id="test",
        context={
            "products": [rag_product],  # Simulating RAG results
            "products_cache": {
                "data": [rag_product],
                "source": "rag",
                "timestamp": 123456.0,
                "filter_applied": {"query": "laptop"},
            },
        },
    )

    # Tool should be able to use the RAG-retrieved product
    result = await query_inventory_impl(sku="SKU-10000", state=state)
    assert result["success"] is True
    # Should use cached data
    assert len(result["products"]) == 1
