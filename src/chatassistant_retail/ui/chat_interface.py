"""Chat interface components for Gradio UI."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def format_message_for_display(role: str, content: str) -> tuple[str, str]:
    """
    Format message for Gradio chatbot display.

    Args:
        role: Message role (user or assistant)
        content: Message content

    Returns:
        Tuple of (role_label, content)
    """
    if role == "user":
        return ("👤 You", content)
    else:
        return ("🤖 Assistant", content)


def format_chat_history(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Format chat history for Gradio chatbot widget.

    Args:
        messages: List of message dictionaries with role and content

    Returns:
        List of dictionaries with 'role' and 'content' keys for Gradio (messages format)
    """
    # Messages are already in the correct format for Gradio 4.0+
    # Just return as-is
    return messages


def format_context_display(context: dict[str, Any]) -> str:
    """
    Format context information for display.

    Args:
        context: Context dictionary from chatbot response

    Returns:
        Formatted string for display
    """
    if not context:
        return "No context available"

    parts = []

    # Products context
    if "products" in context and context["products"]:
        products = context["products"]
        parts.append(f"📦 **Retrieved {len(products)} products:**")
        for i, product in enumerate(products[:3], 1):  # Show top 3
            name = product.get("name", "Unknown")
            sku = product.get("sku", "N/A")
            price = product.get("price", 0)
            stock = product.get("current_stock", 0)
            parts.append(f"{i}. {name} (SKU: {sku}) - ${price:.2f} - Stock: {stock}")

    # Tool results context
    if "tool_results" in context and context["tool_results"]:
        tool_results = context["tool_results"]
        parts.append(f"\n🔧 **Executed {len(tool_results)} tool(s):**")
        for tool_call in tool_results:
            tool_name = tool_call.get("tool", "unknown")
            parts.append(f"- {tool_name}")

    return "\n".join(parts) if parts else "No context available"


def create_example_queries() -> list[str]:
    """
    Create example queries for users.

    Returns:
        List of example query strings
    """
    return [
        "Show me low stock items",
        "Find wireless headphones",
        "What products are in the Electronics category?",
        "Calculate reorder point for SKU-10000",
        "Create a purchase order for 100 units of SKU-10001",
        "Show me products that need reordering",
    ]


def get_welcome_message() -> str:
    """
    Get welcome message for chat interface.

    Returns:
        Welcome message string
    """
    return """👋 **Welcome to the Retail Inventory Assistant!**

I can help you with:
- 📦 Checking inventory levels
- 🔍 Finding products by name or category
- ⚠️ Identifying low stock items
- 📊 Calculating optimal reorder points
- 🛒 Creating purchase orders
- 📈 Analyzing sales trends

Try asking me something like:
- "Show me low stock items"
- "Find wireless headphones"
- "Calculate reorder point for SKU-10000"

How can I assist you today?"""


def format_error_message(error: str) -> str:
    """
    Format error message for display.

    Args:
        error: Error message

    Returns:
        Formatted error message
    """
    return f"❌ **Error:** {error}\n\nPlease try rephrasing your question or contact support if the issue persists."
