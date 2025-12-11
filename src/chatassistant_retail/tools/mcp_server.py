"""FastMCP server setup for inventory management tools."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastmcp import FastMCP

from .inventory_tools import calculate_reorder_point_impl, query_inventory_impl
from .purchase_order_tools import create_purchase_order_impl

if TYPE_CHECKING:
    from chatassistant_retail.state.langgraph_manager import ConversationState

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Retail Inventory Assistant")


@mcp.tool()
async def query_inventory(
    sku: str | None = None,
    category: str | None = None,
    low_stock: bool = False,
    threshold: int = 10,
) -> dict:
    """
    Query current inventory levels for products.

    Args:
        sku: Optional product SKU to query specific product
        category: Optional category filter
        low_stock: If True, return only low stock items
        threshold: Stock threshold for low stock filter (default: 10)

    Returns:
        Dictionary with inventory information
    """
    logger.info(f"Tool call: query_inventory(sku={sku}, category={category}, low_stock={low_stock})")
    return await query_inventory_impl(sku=sku, category=category, low_stock=low_stock, threshold=threshold)


@mcp.tool()
async def calculate_reorder_point(
    sku: str,
    lead_time_days: int = 7,
    safety_stock_multiplier: float = 1.5,
) -> dict:
    """
    Calculate optimal reorder point for a product based on sales history.

    Args:
        sku: Product SKU
        lead_time_days: Supplier lead time in days (default: 7)
        safety_stock_multiplier: Safety stock multiplier (default: 1.5)

    Returns:
        Dictionary with reorder point calculation
    """
    logger.info(f"Tool call: calculate_reorder_point(sku={sku}, lead_time={lead_time_days})")
    return await calculate_reorder_point_impl(
        sku=sku,
        lead_time_days=lead_time_days,
        safety_stock_multiplier=safety_stock_multiplier,
    )


@mcp.tool()
async def create_purchase_order(
    sku: str,
    quantity: int,
    expected_delivery_date: str | None = None,
) -> dict:
    """
    Create a purchase order for restocking inventory.

    Args:
        sku: Product SKU to order
        quantity: Quantity to order
        expected_delivery_date: Optional expected delivery date (ISO format)

    Returns:
        Dictionary with purchase order confirmation
    """
    logger.info(f"Tool call: create_purchase_order(sku={sku}, quantity={quantity})")
    return await create_purchase_order_impl(
        sku=sku,
        quantity=quantity,
        expected_delivery_date=expected_delivery_date,
    )


class ToolExecutor:
    """Execute MCP tools by name."""

    def __init__(self):
        """Initialize tool executor."""
        # Use implementation functions directly instead of decorated MCP tools
        self.tools = {
            "query_inventory": query_inventory_impl,
            "calculate_reorder_point": calculate_reorder_point_impl,
            "create_purchase_order": create_purchase_order_impl,
        }
        logger.info(f"Initialized ToolExecutor with {len(self.tools)} tools")

    async def execute_tool(self, tool_name: str, args: dict, state: ConversationState | None = None) -> dict:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments
            state: Conversation state for context-aware data access

        Returns:
            Tool execution result
        """
        if not tool_name:
            logger.error("Tool name is empty or None")
            return {"success": False, "message": "Tool name is required"}

        if tool_name not in self.tools:
            logger.error(f"Unknown tool: {tool_name}")
            return {"success": False, "message": f"Unknown tool: {tool_name}"}

        try:
            tool_func = self.tools[tool_name]
            # Pass state parameter to tool function
            result = await tool_func(**args, state=state)
            logger.info(f"Successfully executed tool: {tool_name}")
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"success": False, "message": f"Error executing tool: {str(e)}"}


def get_tool_definitions() -> list[dict]:
    """
    Get OpenAI-compatible tool definitions for function calling.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "query_inventory",
                "description": "Query current inventory levels for products. Can filter by SKU, category, or low stock status.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sku": {
                            "type": "string",
                            "description": "Product SKU to query specific product",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by product category",
                        },
                        "low_stock": {
                            "type": "boolean",
                            "description": "If true, return only low stock items",
                        },
                        "threshold": {
                            "type": "integer",
                            "description": "Stock threshold for low stock filter",
                            "default": 10,
                        },
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "calculate_reorder_point",
                "description": "Calculate optimal reorder point for a product based on historical sales data and lead time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sku": {
                            "type": "string",
                            "description": "Product SKU",
                        },
                        "lead_time_days": {
                            "type": "integer",
                            "description": "Supplier lead time in days",
                            "default": 7,
                        },
                        "safety_stock_multiplier": {
                            "type": "number",
                            "description": "Safety stock multiplier (e.g., 1.5 for 50% buffer)",
                            "default": 1.5,
                        },
                    },
                    "required": ["sku"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_purchase_order",
                "description": "Create a purchase order for restocking inventory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sku": {
                            "type": "string",
                            "description": "Product SKU to order",
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Quantity to order",
                        },
                        "expected_delivery_date": {
                            "type": "string",
                            "description": "Expected delivery date in ISO format (YYYY-MM-DD)",
                        },
                    },
                    "required": ["sku", "quantity"],
                },
            },
        },
    ]
