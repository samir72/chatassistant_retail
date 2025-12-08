"""Integration tests for Langgraph state manager."""

from unittest.mock import MagicMock

import pytest
from langchain_core.messages import HumanMessage

from chatassistant_retail.state import ConversationState, LanggraphManager


class MockLLMClient:
    """Mock LLM client for testing."""

    async def call_llm(self, messages, tools=None):
        """Mock LLM call - returns dictionary format."""
        return {
            "choices": [
                {
                    "message": {
                        "content": "This is a test response.",
                        "role": "assistant",
                        "tool_calls": None,
                    }
                }
            ]
        }

    async def extract_response_content(self, response):
        """Extract response content from dictionary."""
        if isinstance(response, dict) and "choices" in response:
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
        return ""

    async def extract_tool_calls(self, response):
        """Extract tool calls from dictionary."""
        if isinstance(response, dict) and "choices" in response:
            choices = response.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                tool_calls = message.get("tool_calls", [])
                if tool_calls:
                    return [
                        {
                            "name": tc.get("function", {}).get("name", ""),
                            "arguments": tc.get("function", {}).get("arguments", {}),
                        }
                        for tc in tool_calls
                    ]
        return []


class MockRAGRetriever:
    """Mock RAG retriever for testing."""

    async def retrieve(self, query, top_k=5):
        """Mock retrieval."""
        return [
            {
                "sku": "SKU-10000",
                "name": "Test Product",
                "category": "Electronics",
                "price": 99.99,
                "current_stock": 5,
                "reorder_level": 10,
            }
        ]


class MockToolExecutor:
    """Mock tool executor for testing."""

    async def execute_tool(self, tool_name, args):
        """Mock tool execution."""
        return {
            "success": True,
            "message": f"Executed {tool_name} with args {args}",
        }


class TestLanggraphManager:
    """Test Langgraph state management."""

    @pytest.mark.asyncio
    async def test_greeting_classification(self):
        """Test that greetings are classified correctly."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Hello")],
        )

        # Classify intent
        state = await manager._classify_intent_node(state)
        assert state.current_intent == "greeting"

    @pytest.mark.asyncio
    async def test_rag_classification(self):
        """Test that product queries are classified as RAG."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Find me a wireless mouse")],
        )

        # Classify intent
        state = await manager._classify_intent_node(state)
        assert state.current_intent == "rag"
        assert state.needs_rag is True

    @pytest.mark.asyncio
    async def test_tool_classification(self):
        """Test that tool-related queries are classified correctly."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Check low stock items")],
        )

        # Classify intent
        state = await manager._classify_intent_node(state)
        assert state.current_intent == "tool"
        assert state.needs_tool is True

    @pytest.mark.asyncio
    async def test_rag_retrieval_node(self):
        """Test RAG retrieval node."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Find wireless mouse")],
        )

        # Execute retrieval
        state = await manager._rag_retrieval_node(state)

        assert "products" in state.context
        assert len(state.context["products"]) > 0
        assert state.context["products"][0]["name"] == "Test Product"

    @pytest.mark.asyncio
    async def test_generate_response_node(self):
        """Test response generation node."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Hello")],
            context={"products": []},
        )

        # Generate response
        state = await manager._generate_response_node(state)

        # Should have added an AI message
        assert len(state.messages) == 2
        assert state.messages[1].content == "This is a test response."

    @pytest.mark.asyncio
    async def test_full_workflow_greeting(self):
        """Test full workflow for greeting."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Hi there")],
        )

        # Process through workflow
        final_state = await manager.process(state)

        # Should have response
        assert len(final_state.messages) == 2
        assert final_state.current_intent == "greeting"
        assert final_state.error is None

    @pytest.mark.asyncio
    async def test_full_workflow_rag(self):
        """Test full workflow for RAG query."""
        llm_client = MockLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Find electronics products")],
        )

        # Process through workflow
        final_state = await manager.process(state)

        # Should have retrieved products and generated response
        assert "products" in final_state.context
        assert len(final_state.messages) == 2
        assert final_state.current_intent == "rag"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in workflow."""

        class FailingLLMClient:
            async def call_llm(self, messages, tools=None):
                raise Exception("LLM error")

        llm_client = FailingLLMClient()
        rag_retriever = MockRAGRetriever()
        tool_executor = MockToolExecutor()

        manager = LanggraphManager(llm_client, rag_retriever, tool_executor)

        state = ConversationState(
            session_id="test-session",
            messages=[HumanMessage(content="Hello")],
        )

        # Process through workflow (should handle error gracefully)
        final_state = await manager.process(state)

        # Should have error set
        assert final_state.error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
