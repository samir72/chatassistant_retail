"""Unit tests for ImageProductProcessor."""

import json
from unittest.mock import AsyncMock

import pytest

from chatassistant_retail.workflow.image_processor import ImageProductProcessor


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = AsyncMock()
    client.identify_product_from_image = AsyncMock()
    client.process_multimodal = AsyncMock()
    client.extract_response_content = AsyncMock()
    return client


@pytest.fixture
def mock_rag_retriever():
    """Create mock RAG retriever."""
    retriever = AsyncMock()
    retriever.retrieve = AsyncMock()
    return retriever


@pytest.fixture
def mock_tool_executor():
    """Create mock tool executor."""
    executor = AsyncMock()
    executor.execute_tool = AsyncMock()
    return executor


@pytest.fixture
def sample_vision_result():
    """Sample vision extraction result."""
    return {
        "product_name": "Wireless Mouse",
        "category": "Electronics",
        "description": "Black wireless optical mouse with ergonomic design",
        "color": "black",
        "keywords": ["wireless mouse", "computer mouse", "black mouse"],
        "confidence": 0.9,
    }


@pytest.fixture
def sample_products():
    """Sample product catalog results."""
    return [
        {
            "sku": "SKU-10001",
            "name": "Wireless Optical Mouse",
            "category": "Electronics",
            "price": 29.99,
            "search_score": 0.95,
        },
        {
            "sku": "SKU-10002",
            "name": "Ergonomic Wireless Mouse",
            "category": "Electronics",
            "price": 39.99,
            "search_score": 0.88,
        },
    ]


class TestImageProductProcessor:
    """Test suite for ImageProductProcessor."""

    def test_init(self):
        """Test processor initialization."""
        processor = ImageProductProcessor()
        assert processor.MIN_CONFIDENCE_THRESHOLD == 0.3
        assert processor.MAX_MATCHES_TO_SHOW == 5

    @pytest.mark.asyncio
    async def test_process_image_query_success(
        self,
        mock_llm_client,
        mock_rag_retriever,
        mock_tool_executor,
        sample_vision_result,
        sample_products,
    ):
        """Test successful image query processing."""
        # Setup mocks
        mock_llm_client.identify_product_from_image.return_value = sample_vision_result
        mock_rag_retriever.retrieve.return_value = sample_products
        mock_tool_executor.execute_tool.return_value = {
            "products": [
                {
                    "sku": "SKU-10001",
                    "name": "Wireless Optical Mouse",
                    "category": "Electronics",
                    "price": 29.99,
                    "current_stock": 50,
                    "reorder_level": 20,
                    "supplier": "Tech Supplies Inc",
                }
            ]
        }

        processor = ImageProductProcessor()
        result = await processor.process_image_query(
            image_path="/tmp/test.jpg",
            user_text="Check inventory",
            llm_client=mock_llm_client,
            rag_retriever=mock_rag_retriever,
            tool_executor=mock_tool_executor,
        )

        assert result["response"]
        assert "Wireless Mouse" in result["response"]
        assert result["context"]["match_count"] == 2
        assert result["error"] is None
        # Validate tool_calls structure
        assert isinstance(result["tool_calls"], list)
        assert len(result["tool_calls"]) > 0
        assert all(isinstance(tc, dict) for tc in result["tool_calls"])
        assert all("tool" in tc and "args" in tc and "result" in tc for tc in result["tool_calls"])

    @pytest.mark.asyncio
    async def test_process_image_query_no_vision_result(self, mock_llm_client, mock_rag_retriever, mock_tool_executor):
        """Test handling when vision extraction fails."""
        mock_llm_client.identify_product_from_image.return_value = None

        processor = ImageProductProcessor()
        result = await processor.process_image_query(
            image_path="/tmp/test.jpg",
            user_text="What is this?",
            llm_client=mock_llm_client,
            rag_retriever=mock_rag_retriever,
            tool_executor=mock_tool_executor,
        )

        assert "trouble analyzing the image" in result["response"]
        assert result["error"]

    @pytest.mark.asyncio
    async def test_extract_product_from_image_with_specialized_method(self, mock_llm_client, sample_vision_result):
        """Test product extraction using specialized method."""
        mock_llm_client.identify_product_from_image.return_value = sample_vision_result

        processor = ImageProductProcessor()
        result = await processor._extract_product_from_image(
            image_path="/tmp/test.jpg",
            user_text="Check this",
            llm_client=mock_llm_client,
        )

        assert result == sample_vision_result
        mock_llm_client.identify_product_from_image.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_product_from_image_fallback(self, mock_llm_client, sample_vision_result):
        """Test product extraction with fallback to generic multimodal."""
        # Remove the specialized method
        delattr(mock_llm_client, "identify_product_from_image")

        # Mock the generic multimodal processing
        mock_llm_client.process_multimodal.return_value = {"choices": [{"message": {}}]}
        mock_llm_client.extract_response_content.return_value = json.dumps(sample_vision_result)

        processor = ImageProductProcessor()
        result = await processor._extract_product_from_image(
            image_path="/tmp/test.jpg",
            user_text="Check this",
            llm_client=mock_llm_client,
        )

        assert result["product_name"] == "Wireless Mouse"
        assert result["category"] == "Electronics"
        mock_llm_client.process_multimodal.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_product_from_image_json_with_markdown(self, mock_llm_client, sample_vision_result):
        """Test parsing JSON from markdown code blocks."""
        delattr(mock_llm_client, "identify_product_from_image")

        # Mock response with markdown code block
        mock_llm_client.process_multimodal.return_value = {"choices": [{"message": {}}]}
        mock_llm_client.extract_response_content.return_value = f"```json\n{json.dumps(sample_vision_result)}\n```"

        processor = ImageProductProcessor()
        result = await processor._extract_product_from_image(
            image_path="/tmp/test.jpg",
            user_text="",
            llm_client=mock_llm_client,
        )

        assert result["product_name"] == "Wireless Mouse"

    @pytest.mark.asyncio
    async def test_search_catalog(self, mock_rag_retriever, sample_vision_result, sample_products):
        """Test catalog search functionality."""
        mock_rag_retriever.retrieve.return_value = sample_products

        processor = ImageProductProcessor()
        results = await processor._search_catalog(
            vision_result=sample_vision_result,
            rag_retriever=mock_rag_retriever,
        )

        assert len(results) == 2
        assert results[0]["sku"] == "SKU-10001"
        mock_rag_retriever.retrieve.assert_called_once()
        call_args = mock_rag_retriever.retrieve.call_args
        assert "Wireless Mouse" in call_args.kwargs["query"]
        assert call_args.kwargs["top_k"] == 5

    @pytest.mark.asyncio
    async def test_check_inventory_status_ok_stock(self, mock_tool_executor, sample_products):
        """Test inventory check with adequate stock."""
        mock_tool_executor.execute_tool.return_value = {
            "products": [
                {
                    "sku": "SKU-10001",
                    "name": "Wireless Optical Mouse",
                    "category": "Electronics",
                    "price": 29.99,
                    "current_stock": 50,
                    "reorder_level": 20,
                    "supplier": "Tech Supplies Inc",
                }
            ]
        }

        processor = ImageProductProcessor()
        results, tool_calls = await processor._check_inventory_status(
            products=sample_products,
            tool_executor=mock_tool_executor,
        )

        assert len(results) > 0
        assert results[0]["status"] == "OK"
        assert results[0]["is_low_stock"] is False
        assert "reorder_recommendation" not in results[0]
        # Validate tool_calls structure
        assert isinstance(tool_calls, list)
        assert len(tool_calls) > 0
        assert tool_calls[0]["tool"] == "query_inventory"
        assert "args" in tool_calls[0]
        assert "result" in tool_calls[0]

    @pytest.mark.asyncio
    async def test_check_inventory_status_low_stock(self, mock_tool_executor, sample_products):
        """Test inventory check with low stock."""
        mock_tool_executor.execute_tool.side_effect = [
            # First call: query_inventory
            {
                "products": [
                    {
                        "sku": "SKU-10001",
                        "name": "Wireless Optical Mouse",
                        "category": "Electronics",
                        "price": 29.99,
                        "current_stock": 10,
                        "reorder_level": 20,
                        "supplier": "Tech Supplies Inc",
                    }
                ]
            },
            # Second call: calculate_reorder_point
            {
                "recommendations": {
                    "order_quantity": 50,
                    "days_until_stockout": 5,
                    "urgency": "HIGH",
                }
            },
        ]

        processor = ImageProductProcessor()
        results, tool_calls = await processor._check_inventory_status(
            products=sample_products[:1],
            tool_executor=mock_tool_executor,
        )

        assert len(results) > 0
        assert results[0]["status"] == "LOW STOCK"
        assert results[0]["is_low_stock"] is True
        assert "reorder_recommendation" in results[0]
        assert results[0]["reorder_recommendation"]["urgency"] == "HIGH"
        # Validate tool_calls - should have both query_inventory and calculate_reorder_point
        assert isinstance(tool_calls, list)
        assert len(tool_calls) == 2
        assert tool_calls[0]["tool"] == "query_inventory"
        assert tool_calls[1]["tool"] == "calculate_reorder_point"
        assert all("args" in tc and "result" in tc for tc in tool_calls)

    @pytest.mark.asyncio
    async def test_generate_response_with_low_stock(self, mock_llm_client, sample_vision_result):
        """Test response generation with low stock items."""
        inventory_results = [
            {
                "sku": "SKU-10001",
                "name": "Wireless Optical Mouse",
                "category": "Electronics",
                "price": 29.99,
                "current_stock": 10,
                "reorder_level": 20,
                "supplier": "Tech Supplies Inc",
                "status": "LOW STOCK",
                "is_low_stock": True,
                "reorder_recommendation": {
                    "order_quantity": 50,
                    "days_until_stockout": 5,
                    "urgency": "HIGH",
                },
            }
        ]

        processor = ImageProductProcessor()
        response = await processor._generate_response(
            vision_result=sample_vision_result,
            inventory_results=inventory_results,
            llm_client=mock_llm_client,
        )

        assert "Wireless Mouse" in response
        assert "LOW STOCK" in response
        assert "Recommendations" in response
        assert "purchase order" in response.lower()

    @pytest.mark.asyncio
    async def test_generate_response_adequate_stock(self, mock_llm_client, sample_vision_result):
        """Test response generation with adequate stock."""
        inventory_results = [
            {
                "sku": "SKU-10001",
                "name": "Wireless Optical Mouse",
                "category": "Electronics",
                "price": 29.99,
                "current_stock": 50,
                "reorder_level": 20,
                "supplier": "Tech Supplies Inc",
                "status": "OK",
                "is_low_stock": False,
            }
        ]

        processor = ImageProductProcessor()
        response = await processor._generate_response(
            vision_result=sample_vision_result,
            inventory_results=inventory_results,
            llm_client=mock_llm_client,
        )

        assert "adequate stock" in response.lower()
        assert "OK" in response

    def test_handle_no_matches(self, sample_vision_result):
        """Test handling when no products match."""
        processor = ImageProductProcessor()
        result = processor._handle_no_matches(sample_vision_result)

        assert "Not Found in Inventory" in result["response"]
        assert "Wireless Mouse" in result["response"]
        assert result["context"]["match_found"] is False
        assert result["error"] is None

    def test_build_error_response(self):
        """Test error response building."""
        processor = ImageProductProcessor()
        result = processor._build_error_response("Test error message")

        assert result["response"] == "Test error message"
        assert result["error"] == "Test error message"
        assert result["context"] == {}
        assert result["tool_calls"] == []

    @pytest.mark.asyncio
    async def test_process_image_query_exception_handling(
        self, mock_llm_client, mock_rag_retriever, mock_tool_executor
    ):
        """Test exception handling in process_image_query."""
        mock_llm_client.identify_product_from_image.side_effect = Exception("Vision API error")

        processor = ImageProductProcessor()
        result = await processor.process_image_query(
            image_path="/tmp/test.jpg",
            user_text="Check this",
            llm_client=mock_llm_client,
            rag_retriever=mock_rag_retriever,
            tool_executor=mock_tool_executor,
        )

        assert "trouble analyzing" in result["response"].lower()
        assert result["error"]

    @pytest.mark.asyncio
    async def test_search_catalog_exception_handling(self, mock_rag_retriever, sample_vision_result):
        """Test exception handling in search_catalog."""
        mock_rag_retriever.retrieve.side_effect = Exception("Search error")

        processor = ImageProductProcessor()
        results = await processor._search_catalog(
            vision_result=sample_vision_result,
            rag_retriever=mock_rag_retriever,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_tool_calls_format_validation(
        self,
        mock_llm_client,
        mock_rag_retriever,
        mock_tool_executor,
        sample_vision_result,
        sample_products,
    ):
        """
        Test that tool_calls are returned as list of dicts, not strings.

        This is a regression test for the validation error:
        "tool_calls.0 Input should be a valid dictionary [type=dict_type]"
        """
        # Setup mocks
        mock_llm_client.identify_product_from_image.return_value = sample_vision_result
        mock_rag_retriever.retrieve.return_value = sample_products
        mock_tool_executor.execute_tool.return_value = {
            "products": [
                {
                    "sku": "SKU-10001",
                    "name": "Wireless Optical Mouse",
                    "category": "Electronics",
                    "price": 29.99,
                    "current_stock": 50,
                    "reorder_level": 20,
                    "supplier": "Tech Supplies Inc",
                }
            ]
        }

        processor = ImageProductProcessor()
        result = await processor.process_image_query(
            image_path="/tmp/test.jpg",
            user_text="Check inventory",
            llm_client=mock_llm_client,
            rag_retriever=mock_rag_retriever,
            tool_executor=mock_tool_executor,
        )

        # Strict validation: tool_calls must be a list of dictionaries
        assert isinstance(result["tool_calls"], list), "tool_calls must be a list"

        for idx, tool_call in enumerate(result["tool_calls"]):
            assert isinstance(tool_call, dict), f"tool_calls[{idx}] must be a dict, got {type(tool_call)}"
            assert "tool" in tool_call, f"tool_calls[{idx}] must have 'tool' field"
            assert "args" in tool_call, f"tool_calls[{idx}] must have 'args' field"
            assert "result" in tool_call, f"tool_calls[{idx}] must have 'result' field"

            # Validate types
            assert isinstance(tool_call["tool"], str), f"tool_calls[{idx}]['tool'] must be a string"
            assert isinstance(tool_call["args"], dict), f"tool_calls[{idx}]['args'] must be a dict"

        # At least one tool should be called
        assert len(result["tool_calls"]) > 0, "At least one tool should be called"

        # The first tool should be query_inventory
        assert result["tool_calls"][0]["tool"] == "query_inventory"
