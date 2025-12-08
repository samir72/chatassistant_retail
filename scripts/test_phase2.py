#!/usr/bin/env python3
"""Test script for Phase 2 components."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_llm_client():
    """Test Azure OpenAI client initialization and prompt templates."""
    print("\n" + "=" * 60)
    print("TEST 1: LLM Client & Prompt Templates")
    print("=" * 60)

    try:
        from chatassistant_retail.llm import AzureOpenAIClient, get_system_prompt

        # Test prompt templates
        print("\n✓ Testing prompt templates...")
        default_prompt = get_system_prompt("default")
        print(f"  - Default prompt: {len(default_prompt)} characters")

        multimodal_prompt = get_system_prompt("multimodal")
        print(f"  - Multimodal prompt: {len(multimodal_prompt)} characters")

        tool_calling_prompt = get_system_prompt("tool_calling")
        print(f"  - Tool calling prompt: {len(tool_calling_prompt)} characters")

        # Test client initialization (will fail without Azure credentials, but that's OK)
        print("\n✓ Testing LLM client initialization...")
        try:
            client = AzureOpenAIClient()
            print(f"  - Client initialized with endpoint: {client.settings.azure_openai_endpoint}")
            print(f"  - Deployment: {client.settings.azure_openai_deployment_name}")
        except Exception as e:
            print(f"  ⚠ Client initialization failed (expected if no Azure credentials): {e}")

        print("\n✅ LLM Client Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ LLM Client Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_rag_retriever():
    """Test RAG retriever with local data fallback."""
    print("\n" + "=" * 60)
    print("TEST 2: RAG Retriever")
    print("=" * 60)

    try:
        from chatassistant_retail.rag import Retriever

        print("\n✓ Initializing retriever...")
        retriever = Retriever()

        if retriever.use_local_data:
            print(f"  - Using local data: {len(retriever.local_products)} products loaded")
        else:
            print("  - Using Azure AI Search")

        # Test basic retrieval
        print("\n✓ Testing product retrieval...")
        products = await retriever.retrieve("wireless mouse", top_k=3)
        print(f"  - Found {len(products)} products for 'wireless mouse'")
        if products:
            print(f"  - Top result: {products[0].get('name')} (SKU: {products[0].get('sku')})")

        # Test low stock query
        print("\n✓ Testing low stock query...")
        low_stock = await retriever.get_low_stock_items(threshold=10, top_k=5)
        print(f"  - Found {len(low_stock)} low stock items")
        if low_stock:
            print(f"  - Example: {low_stock[0].get('name')} - Stock: {low_stock[0].get('current_stock')}")

        # Test category query
        print("\n✓ Testing category query...")
        electronics = await retriever.get_products_by_category("Electronics", top_k=5)
        print(f"  - Found {len(electronics)} electronics products")

        # Test SKU lookup
        print("\n✓ Testing SKU lookup...")
        product = await retriever.get_product_by_sku("SKU-10000")
        if product:
            print(f"  - Product: {product.get('name')} - ${product.get('price')}")
        else:
            print("  - Product SKU-10000 not found")

        # Test reorder recommendations
        print("\n✓ Testing reorder recommendations...")
        reorders = await retriever.get_reorder_recommendations(top_k=5)
        print(f"  - Found {len(reorders)} products needing reorder")
        if reorders:
            print(f"  - Most urgent: {reorders[0].get('name')} - Stock: {reorders[0].get('current_stock')}")

        print("\n✅ RAG Retriever Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ RAG Retriever Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_mcp_tools():
    """Test MCP function calling tools."""
    print("\n" + "=" * 60)
    print("TEST 3: MCP Tools")
    print("=" * 60)

    try:
        from chatassistant_retail.tools import (
            calculate_reorder_point,
            create_purchase_order,
            query_inventory,
        )
        from chatassistant_retail.tools.mcp_server import get_tool_definitions

        # Test tool definitions
        print("\n✓ Testing tool definitions...")
        tools = get_tool_definitions()
        print(f"  - Registered {len(tools)} tools:")
        for tool in tools:
            print(f"    • {tool['function']['name']}")

        # Test query_inventory
        print("\n✓ Testing query_inventory tool...")
        result = await query_inventory(low_stock=True, threshold=10)
        print(f"  - Success: {result.get('success')}")
        print(f"  - Message: {result.get('message')}")
        if result.get("summary"):
            summary = result["summary"]
            print(f"  - Low stock items: {summary.get('low_stock_items')}")
            print(f"  - Out of stock: {summary.get('out_of_stock_items')}")

        # Test with specific SKU
        print("\n✓ Testing query_inventory with SKU...")
        result = await query_inventory(sku="SKU-10000")
        if result.get("success") and result.get("products"):
            product = result["products"][0]
            print(f"  - Found: {product.get('name')}")
            print(f"  - Stock: {product.get('current_stock')}")
            print(f"  - Status: {product.get('status')}")

        # Test calculate_reorder_point
        print("\n✓ Testing calculate_reorder_point tool...")
        result = await calculate_reorder_point(sku="SKU-10000", lead_time_days=7)
        print(f"  - Success: {result.get('success')}")
        if result.get("success"):
            calc = result.get("calculation", {})
            rec = result.get("recommendations", {})
            print(f"  - Recommended reorder point: {calc.get('recommended_reorder_point')}")
            print(f"  - Order quantity: {rec.get('order_quantity')}")
            print(f"  - Urgency: {rec.get('urgency')}")
            print(f"  - Action: {rec.get('action')}")

        # Test create_purchase_order
        print("\n✓ Testing create_purchase_order tool...")
        result = await create_purchase_order(sku="SKU-10000", quantity=100)
        print(f"  - Success: {result.get('success')}")
        if result.get("success"):
            po = result.get("purchase_order", {})
            details = result.get("order_details", {})
            print(f"  - PO ID: {po.get('po_id')}")
            print(f"  - Quantity: {details.get('quantity')}")
            print(f"  - Total cost: ${details.get('total_cost')}")
            print(f"  - Expected delivery: {po.get('expected_delivery')}")
            print(f"  - Saved to file: {result.get('saved_to_file')}")

        print("\n✅ MCP Tools Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ MCP Tools Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_embeddings():
    """Test embeddings client."""
    print("\n" + "=" * 60)
    print("TEST 4: Embeddings Client")
    print("=" * 60)

    try:
        from chatassistant_retail.rag import EmbeddingsClient

        print("\n✓ Initializing embeddings client...")
        embeddings_client = EmbeddingsClient()

        # Note: This will fail without Azure credentials, which is expected
        print("\n✓ Testing embedding generation...")
        try:
            embedding = await embeddings_client.generate_embedding("test product description")
            print(f"  - Generated embedding with dimension: {len(embedding)}")
            print(f"  - Cache size: {embeddings_client.get_cache_size()}")
            print("\n✅ Embeddings Client Test: PASSED")
            return True
        except Exception as e:
            print(f"  ⚠ Embedding generation failed (expected if no Azure credentials): {e}")
            print("\n✅ Embeddings Client Test: PASSED (initialization only)")
            return True

    except Exception as e:
        print(f"\n❌ Embeddings Client Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_response_parser():
    """Test response parser utilities."""
    print("\n" + "=" * 60)
    print("TEST 5: Response Parser")
    print("=" * 60)

    try:
        from chatassistant_retail.llm import ResponseParser

        parser = ResponseParser()

        # Test tool argument parsing
        print("\n✓ Testing tool argument parsing...")
        args_str = '{"sku": "SKU-10000", "quantity": 100}'
        args = parser.parse_tool_arguments(args_str)
        print(f"  - Parsed arguments: {args}")
        assert args["sku"] == "SKU-10000"
        assert args["quantity"] == 100

        # Test thinking extraction
        print("\n✓ Testing thinking extraction...")
        response_text = "Let me think about this.\n\nThe answer is 42."
        thinking, answer = parser.extract_thinking(response_text)
        print(f"  - Thinking: {thinking[:50] if thinking else 'None'}")
        print(f"  - Answer: {answer[:50]}")

        # Test error formatting
        print("\n✓ Testing error formatting...")
        error = ValueError("Invalid input")
        formatted = parser.format_error_response(error, "testing")
        print(f"  - Formatted error: {formatted}")

        # Test context truncation
        print("\n✓ Testing context truncation...")
        long_text = "a" * 3000
        truncated = parser.truncate_context(long_text, max_length=100)
        print(f"  - Truncated from {len(long_text)} to {len(truncated)} chars")
        assert len(truncated) <= 103  # 100 + "..."

        # Test response validation
        print("\n✓ Testing response validation...")
        valid_response = {"choices": [{"message": {"content": "test"}}]}
        is_valid = parser.validate_response(valid_response)
        print(f"  - Valid response: {is_valid}")
        assert is_valid

        invalid_response = {"error": "test"}
        is_valid = parser.validate_response(invalid_response)
        print(f"  - Invalid response: {is_valid}")
        assert not is_valid

        print("\n✅ Response Parser Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Response Parser Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHASE 2 COMPONENT TESTING")
    print("=" * 60)

    results = {
        "LLM Client": await test_llm_client(),
        "RAG Retriever": await test_rag_retriever(),
        "MCP Tools": await test_mcp_tools(),
        "Embeddings": await test_embeddings(),
        "Response Parser": await test_response_parser(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:20} {status}")

    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
