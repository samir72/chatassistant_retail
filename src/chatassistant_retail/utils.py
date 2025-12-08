"""Utility functions for retail chatbot."""

import re
from typing import Any


def sanitize_user_input(text: str, max_length: int = 5000) -> str:
    """
    Sanitize user input for security.

    Removes potentially dangerous patterns:
    - SQL injection attempts
    - Script injection attempts
    - Excessive whitespace

    Args:
        text: User input text
        max_length: Maximum allowed length (default: 5000)

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Limit length
    text = text[:max_length]

    # Remove potential SQL injection patterns
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bUNION\b.*\bSELECT\b)",
    ]

    for pattern in sql_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove script tags and JavaScript
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"javascript:", "", text, flags=re.IGNORECASE)

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()


def format_product_context(products: list[dict[str, Any]]) -> str:
    """
    Format product list for LLM context.

    Args:
        products: List of product dictionaries

    Returns:
        Formatted string with product information
    """
    if not products:
        return "No products found."

    lines = []
    for i, product in enumerate(products, 1):
        sku = product.get("sku", "N/A")
        name = product.get("name", "Unknown")
        category = product.get("category", "N/A")
        price = product.get("price", 0)
        stock = product.get("current_stock", 0)
        reorder = product.get("reorder_level", 0)

        status = "OK"
        if stock == 0:
            status = "OUT OF STOCK"
        elif stock <= reorder:
            status = "LOW STOCK"

        lines.append(
            f"{i}. {name} (SKU: {sku})\n"
            f"   Category: {category} | Price: ${price:.2f}\n"
            f"   Stock: {stock} units | Reorder Level: {reorder} | Status: {status}"
        )

    return "\n".join(lines)


def format_sales_summary(sales: list[dict[str, Any]]) -> str:
    """
    Format sales data summary for LLM context.

    Args:
        sales: List of sale dictionaries

    Returns:
        Formatted string with sales summary
    """
    if not sales:
        return "No sales data available."

    total_quantity = sum(sale.get("quantity", 0) for sale in sales)
    total_revenue = sum(sale.get("sale_price", 0) * sale.get("quantity", 0) for sale in sales)

    lines = [
        f"Sales Summary ({len(sales)} transactions):",
        f"- Total Units Sold: {total_quantity}",
        f"- Total Revenue: ${total_revenue:.2f}",
        f"- Average Transaction: ${total_revenue / len(sales):.2f}",
    ]

    return "\n".join(lines)


def parse_tool_response(tool_output: dict[str, Any]) -> str:
    """
    Parse MCP tool output into human-readable text.

    Args:
        tool_output: Tool execution result dictionary

    Returns:
        Human-readable description of the result
    """
    if not tool_output:
        return "No result from tool."

    if not tool_output.get("success", False):
        return f"Error: {tool_output.get('message', 'Unknown error')}"

    message = tool_output.get("message", "")

    # Add summary if available
    if "summary" in tool_output:
        summary = tool_output["summary"]
        message += "\n\nSummary:\n"
        message += f"- Total Items: {summary.get('total_items', 0)}\n"
        message += f"- Low Stock Items: {summary.get('low_stock_items', 0)}\n"
        message += f"- Out of Stock: {summary.get('out_of_stock_items', 0)}\n"
        message += f"- Total Inventory Value: ${summary.get('total_inventory_value', 0):.2f}"

    # Add calculation if available
    if "calculation" in tool_output:
        calc = tool_output["calculation"]
        message += "\n\nCalculation:\n"
        message += f"- Recommended Reorder Point: {calc.get('recommended_reorder_point', 0)} units\n"
        message += f"- Lead Time: {calc.get('lead_time_days', 0)} days\n"
        message += f"- Safety Stock: {calc.get('safety_stock', 0)} units"

    # Add purchase order details if available
    if "purchase_order" in tool_output:
        po = tool_output["purchase_order"]
        message += "\n\nPurchase Order:\n"
        message += f"- PO ID: {po.get('po_id', 'N/A')}\n"
        message += f"- Status: {po.get('status', 'N/A')}\n"
        message += f"- Expected Delivery: {po.get('expected_delivery', 'N/A')}"

    return message


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def extract_sku_from_text(text: str) -> str | None:
    """
    Extract SKU pattern from text.

    Args:
        text: Input text

    Returns:
        Extracted SKU or None if not found
    """
    # Pattern: SKU-XXXXX (5 digits)
    match = re.search(r"SKU-\d{5}", text, re.IGNORECASE)
    if match:
        return match.group(0).upper()

    return None


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session identifier

    Returns:
        True if valid, False otherwise
    """
    if not session_id:
        return False

    # Allow UUIDs and alphanumeric strings
    if re.match(r"^[a-zA-Z0-9\-]+$", session_id):
        return True

    return False
