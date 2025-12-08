"""Pydantic models for retail inventory data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Product(BaseModel):
    """Product catalog model."""

    sku: str = Field(..., description="Stock Keeping Unit (unique identifier)")
    name: str = Field(..., description="Product name")
    category: str = Field(..., description="Product category")
    price: float = Field(gt=0, description="Product price (must be positive)")
    current_stock: int = Field(ge=0, description="Current stock level")
    reorder_level: int = Field(ge=0, description="Minimum stock level before reordering")
    supplier: str = Field(..., description="Supplier name")
    description: str = Field(default="", description="Product description")
    image_url: str | None = Field(default=None, description="Product image URL (optional)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sku": "SKU-10001",
                    "name": "Wireless Mouse",
                    "category": "Electronics",
                    "price": 29.99,
                    "current_stock": 45,
                    "reorder_level": 20,
                    "supplier": "Tech Supplies Inc.",
                    "description": "Ergonomic wireless mouse with 6 buttons",
                    "image_url": "https://placeholder.co/400x400?text=Mouse",
                }
            ]
        }
    }


class Sale(BaseModel):
    """Sales transaction model."""

    sale_id: str = Field(..., description="Unique sale identifier")
    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(gt=0, description="Quantity sold (must be positive)")
    sale_price: float = Field(gt=0, description="Sale price per unit (must be positive)")
    timestamp: datetime = Field(..., description="Sale timestamp")
    channel: Literal["retail", "online", "wholesale"] = Field(..., description="Sales channel")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "sale_id": "SALE-20240101-001",
                    "sku": "SKU-10001",
                    "quantity": 2,
                    "sale_price": 29.99,
                    "timestamp": "2024-01-01T10:30:00",
                    "channel": "retail",
                }
            ]
        }
    }


class PurchaseOrder(BaseModel):
    """Purchase order model."""

    po_id: str = Field(..., description="Purchase order ID")
    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(gt=0, description="Order quantity (must be positive)")
    supplier: str = Field(..., description="Supplier name")
    order_date: datetime = Field(..., description="Order creation date")
    expected_delivery: datetime = Field(..., description="Expected delivery date")
    status: Literal["pending", "approved", "shipped", "received", "cancelled"] = Field(
        ..., description="Purchase order status"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "po_id": "PO-20240115-001",
                    "sku": "SKU-10001",
                    "quantity": 100,
                    "supplier": "Tech Supplies Inc.",
                    "order_date": "2024-01-15T09:00:00",
                    "expected_delivery": "2024-01-22T09:00:00",
                    "status": "approved",
                }
            ]
        }
    }


class InventoryQuery(BaseModel):
    """Model for inventory query parameters."""

    sku: str | None = Field(default=None, description="Filter by SKU")
    category: str | None = Field(default=None, description="Filter by category")
    low_stock: bool = Field(default=False, description="Filter for low stock items")
    threshold: int = Field(default=10, description="Low stock threshold")


class ReorderCalculation(BaseModel):
    """Model for reorder point calculation parameters."""

    sku: str = Field(..., description="Product SKU")
    lead_time_days: int = Field(default=7, ge=1, description="Supplier lead time in days")
    safety_stock_multiplier: float = Field(default=1.5, ge=1.0, description="Safety stock multiplier")


class PurchaseOrderCreate(BaseModel):
    """Model for creating a purchase order."""

    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(gt=0, description="Order quantity")
    expected_delivery_date: datetime | None = Field(default=None, description="Expected delivery date (optional)")
