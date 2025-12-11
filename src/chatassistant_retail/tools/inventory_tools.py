"""Inventory management tools implementation."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chatassistant_retail.data.models import Product, Sale
from chatassistant_retail.observability import trace
from chatassistant_retail.tools.context_utils import (
    get_products_from_context,
    get_sales_from_context,
    update_products_cache,
    update_sales_cache,
)

if TYPE_CHECKING:
    from chatassistant_retail.state.langgraph_manager import ConversationState

logger = logging.getLogger(__name__)


def _products_to_dicts(products: list[Product]) -> list[dict]:
    """Convert Product models to dictionaries for caching."""
    return [
        {
            "sku": p.sku,
            "name": p.name,
            "category": p.category,
            "price": p.price,
            "current_stock": p.current_stock,
            "reorder_level": p.reorder_level,
            "supplier": p.supplier,
            "description": p.description,
        }
        for p in products
    ]


def _dicts_to_products(product_dicts: list[dict]) -> list[Product]:
    """Convert dictionaries back to Product models."""
    return [Product(**p) for p in product_dicts]


def _load_local_data() -> tuple[list[Product], list[Sale]]:
    """
    Load products and sales from local JSON files.

    Returns:
        Tuple of (products, sales)
    """
    try:
        data_dir = Path(__file__).parent.parent.parent.parent / "data"

        # Load products
        products_file = data_dir / "products.json"
        products = []
        if products_file.exists():
            with open(products_file) as f:
                products_data = json.load(f)
                products = [Product(**p) for p in products_data]

        # Load sales
        sales_file = data_dir / "sales_history.json"
        sales = []
        if sales_file.exists():
            with open(sales_file) as f:
                sales_data = json.load(f)
                sales = [Sale(**s) for s in sales_data]

        logger.info(f"Loaded {len(products)} products and {len(sales)} sales")
        return products, sales

    except Exception as e:
        logger.error(f"Error loading local data: {e}")
        return [], []


@trace(name="tool_query_inventory", trace_type="tool")
async def query_inventory_impl(
    sku: str | None = None,
    category: str | None = None,
    low_stock: bool = False,
    threshold: int = 10,
    state: ConversationState | None = None,
) -> dict[str, Any]:
    """
    Implementation of query_inventory tool.

    Args:
        sku: Optional product SKU
        category: Optional category filter
        low_stock: Filter for low stock items
        threshold: Low stock threshold
        state: Conversation state for context-aware data access

    Returns:
        Dictionary with inventory results
    """
    # Try to get products from context first
    product_dicts = get_products_from_context(state, sku, category, low_stock, threshold)

    if product_dicts is not None:
        logger.info(f"Using {len(product_dicts)} products from context cache")
        products = _dicts_to_products(product_dicts)
    else:
        # Fallback to loading fresh data
        logger.info("Loading fresh product data from JSON")
        products, _ = _load_local_data()

        # Cache the loaded products for future use
        if state and products:
            update_products_cache(
                state,
                _products_to_dicts(products),
                source="tool",
                filter_applied={"sku": sku, "category": category, "low_stock": low_stock, "threshold": threshold},
            )

    if not products:
        return {
            "success": False,
            "message": "No products found in inventory",
            "products": [],
        }

    # Filter products based on criteria
    filtered_products = products

    if sku:
        filtered_products = [p for p in filtered_products if p.sku == sku]

    if category:
        filtered_products = [p for p in filtered_products if p.category.lower() == category.lower()]

    if low_stock:
        filtered_products = [p for p in filtered_products if p.current_stock <= threshold]

    # Format results
    result_products = []
    for product in filtered_products[:20]:  # Limit to 20 results
        result_products.append(
            {
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "current_stock": product.current_stock,
                "reorder_level": product.reorder_level,
                "supplier": product.supplier,
                "status": "LOW STOCK" if product.current_stock <= product.reorder_level else "OK",
            }
        )

    # Calculate summary statistics
    total_items = len(filtered_products)
    low_stock_count = sum(1 for p in filtered_products if p.current_stock <= p.reorder_level)
    out_of_stock_count = sum(1 for p in filtered_products if p.current_stock == 0)
    total_value = sum(p.price * p.current_stock for p in filtered_products)

    return {
        "success": True,
        "message": f"Found {total_items} products",
        "summary": {
            "total_items": total_items,
            "low_stock_items": low_stock_count,
            "out_of_stock_items": out_of_stock_count,
            "total_inventory_value": round(total_value, 2),
        },
        "products": result_products,
    }


@trace(name="tool_calculate_reorder_point", trace_type="tool")
async def calculate_reorder_point_impl(
    sku: str,
    lead_time_days: int = 7,
    safety_stock_multiplier: float = 1.5,
    state: ConversationState | None = None,
) -> dict[str, Any]:
    """
    Implementation of calculate_reorder_point tool.

    Args:
        sku: Product SKU
        lead_time_days: Supplier lead time
        safety_stock_multiplier: Safety stock multiplier
        state: Conversation state for context-aware data access

    Returns:
        Dictionary with reorder point calculation
    """
    # Try to get products from context first
    product_dicts = get_products_from_context(state, sku=sku)

    if product_dicts is not None:
        logger.info(f"Using {len(product_dicts)} products from context cache")
        products = _dicts_to_products(product_dicts)
    else:
        # Fallback to loading fresh data
        logger.info("Loading fresh product data from JSON")
        products, sales_data = _load_local_data()

        # Cache the loaded products for future use
        if state and products:
            update_products_cache(
                state,
                _products_to_dicts(products),
                source="tool",
                filter_applied={"sku": sku},
            )

    # Find the product
    product = next((p for p in products if p.sku == sku), None)
    if not product:
        return {
            "success": False,
            "message": f"Product not found: {sku}",
        }

    # Try to get sales from context
    sales_dicts = get_sales_from_context(state, sku=sku)

    if sales_dicts is not None:
        logger.info(f"Using {len(sales_dicts)} sales records from context cache")
        sales = [Sale(**s) for s in sales_dicts]
    else:
        # Fallback to loading fresh sales data
        logger.info("Loading fresh sales data from JSON")
        if "sales_data" not in locals():
            _, sales_data = _load_local_data()
        sales = sales_data

        # Cache the loaded sales for future use
        if state and sales:
            sales_dicts_for_cache = [
                {
                    "sale_id": s.sale_id,
                    "sku": s.sku,
                    "quantity": s.quantity,
                    "sale_price": s.sale_price,
                    "timestamp": s.timestamp.isoformat(),
                    "channel": s.channel,
                }
                for s in sales
            ]
            update_sales_cache(state, sales_dicts_for_cache, sku_filter=sku)

    # Filter sales for this product
    product_sales = [s for s in sales if s.sku == sku]

    if not product_sales:
        return {
            "success": False,
            "message": f"No sales history found for {sku}. Using default reorder point.",
            "product": {
                "sku": product.sku,
                "name": product.name,
                "current_stock": product.current_stock,
                "current_reorder_level": product.reorder_level,
            },
        }

    # Calculate sales statistics
    total_quantity_sold = sum(s.quantity for s in product_sales)
    days_of_history = (max(s.timestamp for s in product_sales) - min(s.timestamp for s in product_sales)).days + 1

    average_daily_sales = total_quantity_sold / max(days_of_history, 1)

    # Calculate reorder point
    # Reorder Point = (Average Daily Sales * Lead Time) + Safety Stock
    lead_time_demand = average_daily_sales * lead_time_days
    safety_stock = lead_time_demand * (safety_stock_multiplier - 1)
    reorder_point = int(lead_time_demand + safety_stock)

    # Calculate recommended order quantity (1 month supply)
    recommended_order_quantity = int(average_daily_sales * 30)

    # Calculate days until stockout at current rate
    days_until_stockout = int(product.current_stock / max(average_daily_sales, 0.1))

    # Determine urgency
    if product.current_stock <= reorder_point:
        urgency = "HIGH"
        recommendation = "Order immediately to avoid stockout"
    elif product.current_stock <= reorder_point * 1.5:
        urgency = "MEDIUM"
        recommendation = "Consider ordering soon"
    else:
        urgency = "LOW"
        recommendation = "Stock level is adequate"

    return {
        "success": True,
        "message": f"Reorder point calculated for {product.name}",
        "product": {
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier,
        },
        "current_status": {
            "current_stock": product.current_stock,
            "current_reorder_level": product.reorder_level,
        },
        "sales_analysis": {
            "total_sales": len(product_sales),
            "total_quantity_sold": total_quantity_sold,
            "days_of_history": days_of_history,
            "average_daily_sales": round(average_daily_sales, 2),
        },
        "calculation": {
            "lead_time_days": lead_time_days,
            "safety_stock_multiplier": safety_stock_multiplier,
            "recommended_reorder_point": reorder_point,
            "safety_stock": int(safety_stock),
        },
        "recommendations": {
            "reorder_point": reorder_point,
            "order_quantity": recommended_order_quantity,
            "days_until_stockout": days_until_stockout,
            "urgency": urgency,
            "action": recommendation,
        },
    }


# Re-export for backward compatibility
query_inventory = query_inventory_impl
calculate_reorder_point = calculate_reorder_point_impl
