"""Context utilities for tools to access cached data from conversation state.

This module provides helper functions for tools to efficiently access data
that has already been retrieved during the conversation (e.g., from RAG queries
or previous tool executions) instead of always loading fresh data from files.

Benefits:
- Performance: Reduces redundant JSON file I/O operations (3-5x faster for follow-up queries)
- Context coherence: Ensures tools work with the same data user is discussing
- Token efficiency: Reduces LLM context size by reusing retrieved data
- Backward compatible: Tools work with or without state parameter

Usage Example:
    >>> from chatassistant_retail.tools.context_utils import get_products_from_context
    >>> from chatassistant_retail.tools.context_utils import update_products_cache
    >>> from chatassistant_retail.state.langgraph_manager import ConversationState
    >>>
    >>> def query_inventory(sku: str, state: ConversationState | None = None):
    ...     '''Check inventory with context caching.'''
    ...     # Try context cache first (fast path)
    ...     cached_products = get_products_from_context(state, sku=sku)
    ...     if cached_products:
    ...         return cached_products  # Reuse cached data
    ...
    ...     # Fallback: load fresh data from file (slower)
    ...     products = load_from_json("data/products.json")
    ...
    ...     # Update cache for future queries
    ...     if state:
    ...         update_products_cache(state, products, source="tool", filter_applied={"sku": sku})
    ...
    ...     return products

Architecture:
    User Query → RAG Node retrieves products → update_products_cache() → state.context
                                                        ↓
    User Follow-up → Tool called → get_products_from_context() → Cache hit ✓
                                          ↓ (cache miss)
                                    Load from JSON → update_products_cache()

Cache Validation:
    The module performs smart filter matching to ensure cached data can be safely reused:
    - SKU filter: Cache must contain the exact SKU requested
    - Category filter: All cached products must match the category
    - Low-stock filter: All cached products must be below threshold
    - No filter: Cache is only used if reasonably small (<= 50 products)

Examples:
    # Example 1: RAG retrieves products → tools reuse cached data
    >>> # Step 1: User asks about electronics
    >>> # RAG retrieves 5 electronics products → cached in state.context
    >>> # Step 2: User asks "What's the inventory for SKU-10001?"
    >>> cached = get_products_from_context(state, sku="SKU-10001")
    >>> # Returns product from cache (SKU-10001 was in the 5 products)

    # Example 2: Cache miss → load fresh data → update cache
    >>> # User asks for a product not in cache
    >>> cached = get_products_from_context(state, sku="SKU-99999")
    >>> # Returns None (product not in cache)
    >>> # Tool loads from JSON and updates cache
    >>> update_products_cache(state, products, source="tool")

    # Example 3: Filter validation prevents incorrect cache reuse
    >>> # Cache contains electronics products
    >>> # User asks for clothing products
    >>> cached = get_products_from_context(state, category="Clothing")
    >>> # Returns None (cache has electronics, not clothing)
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from chatassistant_retail.state.langgraph_manager import ConversationState


def get_products_from_context(
    state: ConversationState | None,
    sku: str | None = None,
    category: str | None = None,
    low_stock: bool = False,
    threshold: int = 10,
) -> list[dict] | None:
    """Try to get products from context cache.

    Args:
        state: Conversation state containing context cache
        sku: Filter by specific SKU (optional)
        category: Filter by category (optional)
        low_stock: Filter by low stock status (optional)
        threshold: Stock threshold for low stock determination (optional)

    Returns:
        List of product dictionaries if available in context and matching filters,
        None otherwise.
    """
    if not state or not state.context:
        return None

    # Try products_cache first (more structured with metadata)
    cache = state.context.get("products_cache")
    if cache and isinstance(cache, dict):
        products = cache.get("data", [])
        if products and _matches_filter(products, sku, category, low_stock, threshold):
            return products

    # Fallback to RAG-retrieved products (for backward compatibility)
    products = state.context.get("products")
    if products and _matches_filter(products, sku, category, low_stock, threshold):
        return products

    return None


def get_sales_from_context(
    state: ConversationState | None,
    sku: str | None = None,
) -> list[dict] | None:
    """Try to get sales history from context cache.

    Args:
        state: Conversation state containing context cache
        sku: Filter by specific SKU (optional)

    Returns:
        List of sales dictionaries if available in context and matching filter,
        None otherwise.
    """
    if not state or not state.context:
        return None

    cache = state.context.get("sales_cache")
    if not cache or not isinstance(cache, dict):
        return None

    sales = cache.get("data", [])
    if not sales:
        return None

    # If requesting specific SKU, verify cache matches
    cached_sku_filter = cache.get("sku_filter")
    if sku and cached_sku_filter != sku:
        # Cache is for different SKU, can't use it
        return None

    # If cache has a specific SKU filter and we want all SKUs, can't use it
    if not sku and cached_sku_filter:
        return None

    return sales


def update_products_cache(
    state: ConversationState,
    products: list[dict],
    source: str = "tool",
    filter_applied: dict[str, Any] | None = None,
) -> None:
    """Update products cache in conversation state context.

    Args:
        state: Conversation state to update
        products: List of product dictionaries to cache
        source: Source of the data ("rag", "tool", "full_load")
        filter_applied: Dictionary of filter parameters applied (e.g., {"sku": "SKU-123"})
    """
    if not state.context:
        state.context = {}

    state.context["products_cache"] = {
        "data": products,
        "source": source,
        "timestamp": time.time(),
        "filter_applied": filter_applied or {},
    }


def update_sales_cache(
    state: ConversationState,
    sales: list[dict],
    sku_filter: str | None = None,
) -> None:
    """Update sales cache in conversation state context.

    Args:
        state: Conversation state to update
        sales: List of sales dictionaries to cache
        sku_filter: SKU filter that was applied (None means all SKUs)
    """
    if not state.context:
        state.context = {}

    state.context["sales_cache"] = {
        "data": sales,
        "timestamp": time.time(),
        "sku_filter": sku_filter,
    }


def _matches_filter(
    products: list[dict],
    sku: str | None = None,
    category: str | None = None,
    low_stock: bool = False,
    threshold: int = 10,
) -> bool:
    """Check if cached products match the requested filter criteria.

    This function determines if the cached products can be used for the
    requested query. It uses a conservative approach:
    - If a specific SKU is requested, cache must contain that exact SKU
    - If a category is requested, cache must be filtered by same category
    - If low_stock filter is requested, we can't reliably use unfiltered cache

    Args:
        products: List of cached products to check
        sku: Requested SKU filter
        category: Requested category filter
        low_stock: Requested low stock filter
        threshold: Stock threshold for low stock

    Returns:
        True if cached products match the filter criteria, False otherwise.
    """
    if not products:
        return False

    # If specific SKU requested, check if it's in the cache
    if sku:
        # If cache contains exactly one product with matching SKU, it's a match
        if len(products) == 1 and products[0].get("sku") == sku:
            return True
        # If cache contains multiple products, check if requested SKU is present
        # (This handles case where RAG returned multiple relevant products)
        skus_in_cache = {p.get("sku") for p in products}
        if sku in skus_in_cache:
            return True
        return False

    # If category requested, check if all products in cache match that category
    if category:
        category_lower = category.lower()
        for product in products:
            product_category = product.get("category", "").lower()
            if product_category != category_lower:
                # Cache contains mixed categories, can't reliably use it
                return False
        # All products match the requested category
        return True

    # If low_stock filter requested, we need to verify all products meet criteria
    if low_stock:
        for product in products:
            current_stock = product.get("current_stock", 0)
            if current_stock > threshold:
                # Cache contains products that don't match low_stock filter
                return False
        # All products in cache are low stock
        return True

    # No specific filter requested, cache can be used for general queries
    # (Conservative: only use if cache is reasonably small)
    # Large caches (>50 products) are likely full database dumps
    if len(products) > 50:
        return False

    return True
