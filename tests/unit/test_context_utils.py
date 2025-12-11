"""Unit tests for context utilities module."""

from __future__ import annotations

import time
from typing import Any

from chatassistant_retail.state.langgraph_manager import ConversationState
from chatassistant_retail.tools.context_utils import (
    get_products_from_context,
    get_sales_from_context,
    update_products_cache,
    update_sales_cache,
)

# Sample test data
SAMPLE_PRODUCTS = [
    {
        "sku": "SKU-10000",
        "name": "Laptop Pro",
        "category": "Electronics",
        "price": 1299.99,
        "current_stock": 5,
        "reorder_level": 10,
    },
    {
        "sku": "SKU-10001",
        "name": "Wireless Mouse",
        "category": "Electronics",
        "price": 29.99,
        "current_stock": 15,
        "reorder_level": 20,
    },
    {
        "sku": "SKU-20000",
        "name": "Office Chair",
        "category": "Furniture",
        "price": 249.99,
        "current_stock": 3,
        "reorder_level": 5,
    },
]

SAMPLE_SALES = [
    {
        "sale_id": "SALE-001",
        "sku": "SKU-10000",
        "quantity": 2,
        "sale_price": 1299.99,
        "timestamp": "2025-01-01T10:00:00",
    },
    {
        "sale_id": "SALE-002",
        "sku": "SKU-10000",
        "quantity": 1,
        "sale_price": 1299.99,
        "timestamp": "2025-01-02T14:30:00",
    },
]


def create_state_with_context(context: dict[str, Any]) -> ConversationState:
    """Helper to create a ConversationState with specific context."""
    return ConversationState(
        messages=[],
        context=context,
        tool_calls=[],
        session_id="test-session",
        current_intent="tool",
        needs_rag=False,
        needs_tool=True,
    )


class TestGetProductsFromContext:
    """Tests for get_products_from_context function."""

    def test_get_products_from_rag_data(self):
        """Test retrieving products from RAG-populated context."""
        state = create_state_with_context({"products": SAMPLE_PRODUCTS[:2]})
        result = get_products_from_context(state)
        assert result is not None
        assert len(result) == 2
        assert result[0]["sku"] == "SKU-10000"

    def test_get_products_from_cache(self):
        """Test retrieving products from structured products_cache."""
        cache = {
            "data": SAMPLE_PRODUCTS[:2],
            "source": "tool",
            "timestamp": time.time(),
            "filter_applied": {},
        }
        state = create_state_with_context({"products_cache": cache})
        result = get_products_from_context(state)
        assert result is not None
        assert len(result) == 2

    def test_get_products_with_sku_filter_exact_match(self):
        """Test retrieving single product by SKU."""
        state = create_state_with_context({"products": [SAMPLE_PRODUCTS[0]]})
        result = get_products_from_context(state, sku="SKU-10000")
        assert result is not None
        assert len(result) == 1
        assert result[0]["sku"] == "SKU-10000"

    def test_get_products_with_sku_filter_in_multiple(self):
        """Test retrieving product by SKU from multi-product cache."""
        state = create_state_with_context({"products": SAMPLE_PRODUCTS})
        result = get_products_from_context(state, sku="SKU-20000")
        assert result is not None
        assert any(p["sku"] == "SKU-20000" for p in result)

    def test_get_products_with_sku_filter_not_found(self):
        """Test SKU filter returns None when SKU not in cache."""
        state = create_state_with_context({"products": SAMPLE_PRODUCTS[:2]})
        result = get_products_from_context(state, sku="SKU-99999")
        assert result is None

    def test_get_products_with_category_filter_match(self):
        """Test retrieving products by category."""
        electronics = [p for p in SAMPLE_PRODUCTS if p["category"] == "Electronics"]
        state = create_state_with_context({"products": electronics})
        result = get_products_from_context(state, category="Electronics")
        assert result is not None
        assert all(p["category"] == "Electronics" for p in result)

    def test_get_products_with_category_filter_mixed_cache(self):
        """Test category filter returns None when cache has mixed categories."""
        state = create_state_with_context({"products": SAMPLE_PRODUCTS})  # Mixed categories
        result = get_products_from_context(state, category="Electronics")
        assert result is None  # Can't reliably use mixed cache

    def test_get_products_with_low_stock_filter_match(self):
        """Test retrieving low stock products."""
        low_stock_products = [p for p in SAMPLE_PRODUCTS if p["current_stock"] <= 10]
        state = create_state_with_context({"products": low_stock_products})
        result = get_products_from_context(state, low_stock=True, threshold=10)
        assert result is not None
        assert all(p["current_stock"] <= 10 for p in result)

    def test_get_products_with_low_stock_filter_mixed_cache(self):
        """Test low stock filter returns None when cache has mixed stock levels."""
        state = create_state_with_context({"products": SAMPLE_PRODUCTS})  # Mixed stock
        result = get_products_from_context(state, low_stock=True, threshold=10)
        assert result is None  # Can't use cache with products above threshold

    def test_get_products_with_none_state(self):
        """Test function handles None state gracefully."""
        result = get_products_from_context(None)
        assert result is None

    def test_get_products_with_empty_context(self):
        """Test function handles empty context gracefully."""
        state = create_state_with_context({})
        result = get_products_from_context(state)
        assert result is None

    def test_get_products_large_cache_rejected(self):
        """Test that very large caches (>50 products) are not used for unfiltered queries."""
        large_cache = [
            {"sku": f"SKU-{i}", "name": f"Product {i}", "category": "Test", "current_stock": 10} for i in range(100)
        ]
        state = create_state_with_context({"products": large_cache})
        result = get_products_from_context(state)  # No filter
        assert result is None  # Large cache should be rejected

    def test_get_products_cache_priority_over_rag(self):
        """Test that products_cache takes priority over RAG products."""
        cache_products = [SAMPLE_PRODUCTS[0]]
        rag_products = [SAMPLE_PRODUCTS[1]]
        state = create_state_with_context(
            {
                "products": rag_products,
                "products_cache": {
                    "data": cache_products,
                    "source": "tool",
                    "timestamp": time.time(),
                },
            }
        )
        result = get_products_from_context(state)
        assert result is not None
        assert result[0]["sku"] == "SKU-10000"  # From cache, not RAG


class TestGetSalesFromContext:
    """Tests for get_sales_from_context function."""

    def test_get_sales_without_filter(self):
        """Test retrieving all sales from context."""
        cache = {
            "data": SAMPLE_SALES,
            "timestamp": time.time(),
            "sku_filter": None,
        }
        state = create_state_with_context({"sales_cache": cache})
        result = get_sales_from_context(state)
        assert result is not None
        assert len(result) == 2

    def test_get_sales_with_matching_sku_filter(self):
        """Test retrieving sales with matching SKU filter."""
        cache = {
            "data": SAMPLE_SALES,
            "timestamp": time.time(),
            "sku_filter": "SKU-10000",
        }
        state = create_state_with_context({"sales_cache": cache})
        result = get_sales_from_context(state, sku="SKU-10000")
        assert result is not None
        assert len(result) == 2

    def test_get_sales_with_mismatched_sku_filter(self):
        """Test that mismatched SKU filter returns None."""
        cache = {
            "data": SAMPLE_SALES,
            "timestamp": time.time(),
            "sku_filter": "SKU-10000",
        }
        state = create_state_with_context({"sales_cache": cache})
        result = get_sales_from_context(state, sku="SKU-99999")
        assert result is None

    def test_get_sales_requesting_all_with_filtered_cache(self):
        """Test that requesting all sales fails when cache is SKU-filtered."""
        cache = {
            "data": SAMPLE_SALES,
            "timestamp": time.time(),
            "sku_filter": "SKU-10000",
        }
        state = create_state_with_context({"sales_cache": cache})
        result = get_sales_from_context(state, sku=None)
        assert result is None  # Can't use SKU-filtered cache for all sales

    def test_get_sales_with_none_state(self):
        """Test function handles None state gracefully."""
        result = get_sales_from_context(None)
        assert result is None

    def test_get_sales_with_empty_context(self):
        """Test function handles empty context gracefully."""
        state = create_state_with_context({})
        result = get_sales_from_context(state)
        assert result is None

    def test_get_sales_with_no_cache(self):
        """Test function handles missing sales_cache gracefully."""
        state = create_state_with_context({"products": SAMPLE_PRODUCTS})
        result = get_sales_from_context(state)
        assert result is None

    def test_get_sales_with_empty_data(self):
        """Test function handles empty sales data gracefully."""
        cache = {
            "data": [],
            "timestamp": time.time(),
            "sku_filter": None,
        }
        state = create_state_with_context({"sales_cache": cache})
        result = get_sales_from_context(state)
        assert result is None


class TestUpdateProductsCache:
    """Tests for update_products_cache function."""

    def test_update_products_cache_basic(self):
        """Test updating products cache with basic data."""
        state = create_state_with_context({})
        update_products_cache(state, SAMPLE_PRODUCTS[:2], source="tool")

        assert "products_cache" in state.context
        cache = state.context["products_cache"]
        assert cache["data"] == SAMPLE_PRODUCTS[:2]
        assert cache["source"] == "tool"
        assert "timestamp" in cache
        assert cache["filter_applied"] == {}

    def test_update_products_cache_with_filter(self):
        """Test updating cache with filter metadata."""
        state = create_state_with_context({})
        filter_applied = {"sku": "SKU-10000"}
        update_products_cache(state, [SAMPLE_PRODUCTS[0]], source="rag", filter_applied=filter_applied)

        cache = state.context["products_cache"]
        assert cache["filter_applied"] == filter_applied
        assert cache["source"] == "rag"

    def test_update_products_cache_overwrites_existing(self):
        """Test that updating cache overwrites previous cache."""
        state = create_state_with_context(
            {
                "products_cache": {
                    "data": [SAMPLE_PRODUCTS[0]],
                    "source": "old",
                    "timestamp": time.time() - 100,
                },
            }
        )

        update_products_cache(state, SAMPLE_PRODUCTS[:2], source="new")

        cache = state.context["products_cache"]
        assert len(cache["data"]) == 2
        assert cache["source"] == "new"

    def test_update_products_cache_initializes_context(self):
        """Test that update works with fresh ConversationState."""
        state = ConversationState(
            messages=[],
            tool_calls=[],
            session_id="test",
        )
        # Context is initialized as empty dict by default
        assert state.context == {}

        update_products_cache(state, SAMPLE_PRODUCTS[:1])
        assert "products_cache" in state.context


class TestUpdateSalesCache:
    """Tests for update_sales_cache function."""

    def test_update_sales_cache_basic(self):
        """Test updating sales cache with basic data."""
        state = create_state_with_context({})
        update_sales_cache(state, SAMPLE_SALES)

        assert "sales_cache" in state.context
        cache = state.context["sales_cache"]
        assert cache["data"] == SAMPLE_SALES
        assert "timestamp" in cache
        assert cache["sku_filter"] is None

    def test_update_sales_cache_with_sku_filter(self):
        """Test updating sales cache with SKU filter."""
        state = create_state_with_context({})
        update_sales_cache(state, SAMPLE_SALES, sku_filter="SKU-10000")

        cache = state.context["sales_cache"]
        assert cache["sku_filter"] == "SKU-10000"

    def test_update_sales_cache_overwrites_existing(self):
        """Test that updating cache overwrites previous cache."""
        state = create_state_with_context(
            {
                "sales_cache": {
                    "data": [],
                    "timestamp": time.time() - 100,
                    "sku_filter": "OLD",
                },
            }
        )

        update_sales_cache(state, SAMPLE_SALES, sku_filter="NEW")

        cache = state.context["sales_cache"]
        assert len(cache["data"]) == 2
        assert cache["sku_filter"] == "NEW"

    def test_update_sales_cache_initializes_context(self):
        """Test that update works with fresh ConversationState."""
        state = ConversationState(
            messages=[],
            tool_calls=[],
            session_id="test",
        )
        # Context is initialized as empty dict by default
        assert state.context == {}

        update_sales_cache(state, SAMPLE_SALES)
        assert "sales_cache" in state.context


class TestIntegratedScenarios:
    """Integration tests for realistic usage scenarios."""

    def test_rag_then_tool_workflow(self):
        """Test workflow: RAG retrieves products, then tool uses cached data."""
        # Step 1: RAG retrieves products
        state = create_state_with_context({})
        update_products_cache(state, SAMPLE_PRODUCTS[:2], source="rag")

        # Step 2: Tool tries to get products
        result = get_products_from_context(state)
        assert result is not None
        assert len(result) == 2

    def test_tool_loads_then_reuses(self):
        """Test workflow: Tool loads data, caches it, then reuses on next call."""
        state = create_state_with_context({})

        # First tool call: loads fresh data
        products_from_load = SAMPLE_PRODUCTS.copy()
        update_products_cache(state, products_from_load, source="tool")

        # Second tool call: reuses cached data
        result = get_products_from_context(state)
        assert result is not None
        assert result == products_from_load

    def test_multiple_tools_share_cache(self):
        """Test workflow: Multiple tools access same cached data."""
        state = create_state_with_context({})

        # Tool 1 caches products and sales
        update_products_cache(state, SAMPLE_PRODUCTS, source="tool")
        update_sales_cache(state, SAMPLE_SALES, sku_filter="SKU-10000")

        # Tool 2 retrieves products
        products = get_products_from_context(state, sku="SKU-10000")
        assert products is not None

        # Tool 3 retrieves sales
        sales = get_sales_from_context(state, sku="SKU-10000")
        assert sales is not None
        assert len(sales) == 2
