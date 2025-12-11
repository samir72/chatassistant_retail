"""Unit tests for Azure OpenAI client."""

import pytest

from chatassistant_retail.llm.azure_openai_client import AzureOpenAIClient


class TestAzureOpenAIClient:
    """Test Azure OpenAI client functionality."""

    @pytest.mark.asyncio
    async def test_extract_tool_calls_with_valid_response(self):
        """Test extracting tool calls from valid OpenAI response."""
        client = AzureOpenAIClient()

        # Simulate real OpenAI response structure with tool calls
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_abc123",
                                "type": "function",
                                "function": {
                                    "name": "query_inventory",
                                    "arguments": '{"low_stock": true, "threshold": 10}',
                                },
                            }
                        ],
                    }
                }
            ]
        }

        tool_calls = await client.extract_tool_calls(response)

        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_abc123"
        assert tool_calls[0]["type"] == "function"
        assert tool_calls[0]["function"]["name"] == "query_inventory"
        assert tool_calls[0]["function"]["arguments"] == '{"low_stock": true, "threshold": 10}'

    @pytest.mark.asyncio
    async def test_extract_tool_calls_with_multiple_tools(self):
        """Test extracting multiple tool calls from response."""
        client = AzureOpenAIClient()

        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "query_inventory",
                                    "arguments": '{"category": "Electronics"}',
                                },
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {
                                    "name": "calculate_reorder_point",
                                    "arguments": '{"sku": "SKU-10000"}',
                                },
                            },
                        ]
                    }
                }
            ]
        }

        tool_calls = await client.extract_tool_calls(response)

        assert len(tool_calls) == 2
        assert tool_calls[0]["function"]["name"] == "query_inventory"
        assert tool_calls[1]["function"]["name"] == "calculate_reorder_point"

    @pytest.mark.asyncio
    async def test_extract_tool_calls_with_no_tool_calls(self):
        """Test extracting tool calls when response has none."""
        client = AzureOpenAIClient()

        response = {"choices": [{"message": {"role": "assistant", "content": "Hello, how can I help you?"}}]}

        tool_calls = await client.extract_tool_calls(response)

        assert len(tool_calls) == 0

    @pytest.mark.asyncio
    async def test_extract_tool_calls_with_empty_response(self):
        """Test extracting tool calls from empty response."""
        client = AzureOpenAIClient()

        response = {"choices": []}

        tool_calls = await client.extract_tool_calls(response)

        assert len(tool_calls) == 0

    @pytest.mark.asyncio
    async def test_extract_tool_calls_with_malformed_response(self):
        """Test that malformed responses are handled gracefully."""
        client = AzureOpenAIClient()

        response = {}  # Missing 'choices' key

        tool_calls = await client.extract_tool_calls(response)

        assert len(tool_calls) == 0

    @pytest.mark.asyncio
    async def test_extract_tool_calls_with_null_tool_calls(self):
        """Test extraction when tool_calls is explicitly null (not missing)."""
        client = AzureOpenAIClient()

        # This can happen when Azure OpenAI returns tool_calls: null
        # instead of omitting the key or returning an empty array
        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I'll help with that.",
                        "tool_calls": None,  # Explicit null value
                    }
                }
            ]
        }

        tool_calls = await client.extract_tool_calls(response)

        assert tool_calls == []
        assert isinstance(tool_calls, list)

    @pytest.mark.asyncio
    async def test_extract_response_content_with_valid_response(self):
        """Test extracting text content from response."""
        client = AzureOpenAIClient()

        response = {"choices": [{"message": {"role": "assistant", "content": "Here are the products you requested."}}]}

        content = await client.extract_response_content(response)

        assert content == "Here are the products you requested."

    @pytest.mark.asyncio
    async def test_extract_response_content_with_empty_content(self):
        """Test extracting content when message has no content."""
        client = AzureOpenAIClient()

        response = {"choices": [{"message": {"role": "assistant", "content": None}}]}

        content = await client.extract_response_content(response)

        assert content == ""

    @pytest.mark.asyncio
    async def test_extract_response_content_with_tool_call_response(self):
        """Test extracting content from response with tool calls (no text content)."""
        client = AzureOpenAIClient()

        response = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {"name": "query_inventory", "arguments": "{}"},
                            }
                        ],
                    }
                }
            ]
        }

        content = await client.extract_response_content(response)

        assert content == ""
