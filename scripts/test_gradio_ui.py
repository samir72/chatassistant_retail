#!/usr/bin/env python3
"""Test script for Gradio UI components."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_ui_components():
    """Test UI component functions."""
    print("\n" + "=" * 60)
    print("TEST 1: UI Components")
    print("=" * 60)

    try:
        from chatassistant_retail.ui.chat_interface import (
            create_example_queries,
            format_chat_history,
            format_context_display,
            format_error_message,
            get_welcome_message,
        )

        print("\n✓ Testing chat interface functions...")

        # Test welcome message
        welcome = get_welcome_message()
        print(f"  - Welcome message: {len(welcome)} characters")
        assert len(welcome) > 0

        # Test example queries
        examples = create_example_queries()
        print(f"  - Example queries: {len(examples)} examples")
        assert len(examples) > 0

        # Test chat history formatting
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        formatted = format_chat_history(messages)
        print(f"  - Chat history formatting: {len(formatted)} pairs")
        assert len(formatted) == 1

        # Test context display
        context = {"products": [{"name": "Test", "sku": "SKU-123", "price": 99.99, "current_stock": 10}]}
        context_str = format_context_display(context)
        print(f"  - Context display: {len(context_str)} characters")
        assert len(context_str) > 0

        # Test error formatting
        error_msg = format_error_message("Test error")
        print(f"  - Error formatting: {len(error_msg)} characters")
        assert "Error" in error_msg

        print("\n✅ UI Components Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ UI Components Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_metrics_dashboard():
    """Test metrics dashboard functions."""
    print("\n" + "=" * 60)
    print("TEST 2: Metrics Dashboard")
    print("=" * 60)

    try:
        from chatassistant_retail.ui.metrics_dashboard import (
            format_activity_log,
            format_metrics_for_display,
            get_empty_metrics,
        )

        print("\n✓ Testing metrics dashboard functions...")

        # Test empty metrics
        empty = get_empty_metrics()
        print(f"  - Empty metrics: {len(empty)} fields")
        assert empty["total_queries"] == 0

        # Test metrics formatting
        metrics = {
            "total_queries": 10,
            "avg_response_time": 1.5,
            "tool_calls_count": 3,
            "success_rate": 95.0,
        }
        total, avg, tools, success = format_metrics_for_display(metrics)
        print(f"  - Metrics formatting: total={total}, avg={avg}, tools={tools}, success={success}")
        assert total == 10

        # Test activity log formatting
        metrics_with_activity = {
            "recent_activity": [
                {"timestamp": "2025-12-05T20:00:00", "name": "test", "type": "function", "status": "success"}
            ]
        }
        activity = format_activity_log(metrics_with_activity)
        print(f"  - Activity log: {len(activity)} rows")
        assert len(activity) > 0

        print("\n✅ Metrics Dashboard Test: PASSED")
        return True

    except Exception as e:
        print(f"\n❌ Metrics Dashboard Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_gradio_interface():
    """Test Gradio interface creation."""
    print("\n" + "=" * 60)
    print("TEST 3: Gradio Interface")
    print("=" * 60)

    try:
        from chatassistant_retail.ui import create_gradio_interface

        print("\n✓ Creating Gradio interface...")
        demo = create_gradio_interface()

        print("  - Interface created successfully")
        print(f"  - Type: {type(demo).__name__}")

        # Check that demo has expected attributes
        assert hasattr(demo, "launch")
        print("  - Has launch method: ✓")

        print("\n✅ Gradio Interface Test: PASSED")
        print("\nNote: To fully test the UI, run: python -m chatassistant_retail")
        return True

    except Exception as e:
        print(f"\n❌ Gradio Interface Test: FAILED - {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHASE 5 GRADIO UI TESTING")
    print("=" * 60)

    results = {
        "UI Components": await test_ui_components(),
        "Metrics Dashboard": await test_metrics_dashboard(),
        "Gradio Interface": await test_gradio_interface(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")

    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
