"""Purchase order creation tools implementation."""

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from chatassistant_retail.data.models import Product, PurchaseOrder
from chatassistant_retail.observability import trace

logger = logging.getLogger(__name__)


def _load_products() -> list[Product]:
    """Load products from local JSON file."""
    try:
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        products_file = data_dir / "products.json"

        if products_file.exists():
            with open(products_file) as f:
                products_data = json.load(f)
                return [Product(**p) for p in products_data]

        return []

    except Exception as e:
        logger.error(f"Error loading products: {e}")
        return []


def _save_purchase_order(po: PurchaseOrder) -> bool:
    """
    Save purchase order to local file.

    Args:
        po: PurchaseOrder instance

    Returns:
        True if successful, False otherwise
    """
    try:
        data_dir = Path(__file__).parent.parent.parent.parent / "data"
        data_dir.mkdir(exist_ok=True)

        po_file = data_dir / "purchase_orders.json"

        # Load existing POs
        existing_pos = []
        if po_file.exists():
            with open(po_file) as f:
                existing_pos = json.load(f)

        # Add new PO
        existing_pos.append(po.model_dump(mode="json"))

        # Save
        with open(po_file, "w") as f:
            json.dump(existing_pos, f, indent=2, default=str)

        logger.info(f"Saved purchase order: {po.po_id}")
        return True

    except Exception as e:
        logger.error(f"Error saving purchase order: {e}")
        return False


@trace(name="tool_create_purchase_order", trace_type="tool")
async def create_purchase_order_impl(
    sku: str,
    quantity: int,
    expected_delivery_date: str | None = None,
) -> dict[str, Any]:
    """
    Implementation of create_purchase_order tool.

    Args:
        sku: Product SKU
        quantity: Order quantity
        expected_delivery_date: Optional delivery date (ISO format)

    Returns:
        Dictionary with purchase order confirmation
    """
    products = _load_products()

    # Find the product
    product = next((p for p in products if p.sku == sku), None)
    if not product:
        return {
            "success": False,
            "message": f"Product not found: {sku}",
        }

    # Validate quantity
    if quantity <= 0:
        return {
            "success": False,
            "message": "Quantity must be positive",
        }

    # Generate PO ID
    po_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

    # Calculate delivery date
    order_date = datetime.now()
    if expected_delivery_date:
        try:
            delivery_date = datetime.fromisoformat(expected_delivery_date)
        except ValueError:
            logger.warning(f"Invalid delivery date format: {expected_delivery_date}")
            delivery_date = order_date + timedelta(days=7)  # Default 7 days
    else:
        delivery_date = order_date + timedelta(days=7)  # Default 7 days

    # Create purchase order
    po = PurchaseOrder(
        po_id=po_id,
        sku=sku,
        quantity=quantity,
        supplier=product.supplier,
        order_date=order_date,
        expected_delivery=delivery_date,
        status="pending",
    )

    # Save PO
    saved = _save_purchase_order(po)

    # Calculate totals
    unit_cost = product.price * 0.6  # Assume 40% margin
    total_cost = unit_cost * quantity

    # Calculate stock after delivery
    stock_after_delivery = product.current_stock + quantity

    return {
        "success": True,
        "message": "Purchase order created successfully",
        "purchase_order": {
            "po_id": po_id,
            "status": "pending",
            "order_date": order_date.isoformat(),
            "expected_delivery": delivery_date.isoformat(),
        },
        "product": {
            "sku": product.sku,
            "name": product.name,
            "category": product.category,
            "supplier": product.supplier,
        },
        "order_details": {
            "quantity": quantity,
            "unit_cost": round(unit_cost, 2),
            "total_cost": round(total_cost, 2),
        },
        "inventory_impact": {
            "current_stock": product.current_stock,
            "stock_after_delivery": stock_after_delivery,
            "reorder_level": product.reorder_level,
            "status_after_delivery": "OK" if stock_after_delivery > product.reorder_level else "LOW",
        },
        "next_steps": [
            "PO submitted to supplier for approval",
            f"Expected delivery: {delivery_date.strftime('%Y-%m-%d')}",
            "You will receive notification when order is shipped",
        ],
        "saved_to_file": saved,
    }


# Re-export for backward compatibility
create_purchase_order = create_purchase_order_impl
