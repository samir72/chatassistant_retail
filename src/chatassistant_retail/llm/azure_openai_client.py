"""Azure OpenAI client for multi-modal LLM interactions."""

import base64
import logging
from pathlib import Path
from typing import Any

from openai import AsyncAzureOpenAI

from chatassistant_retail.config import get_settings
from chatassistant_retail.observability import trace

logger = logging.getLogger(__name__)


class AzureOpenAIClient:
    """Client for interacting with Azure OpenAI multi-modal models."""

    def __init__(self, settings=None):
        """
        Initialize Azure OpenAI client.

        Args:
            settings: Optional Settings instance. If None, uses get_settings().
        """
        self.settings = settings or get_settings()
        self.client = AsyncAzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            azure_endpoint=self.settings.azure_openai_endpoint,
        )
        logger.info(f"Initialized Azure OpenAI client with endpoint: {self.settings.azure_openai_endpoint}")

    @trace(name="azure_openai_call", trace_type="llm")
    async def call_llm(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
    ) -> dict[str, Any] | Any:
        """
        Call Azure OpenAI LLM with messages and optional function calling.

        Args:
            messages: List of message dictionaries with role and content
            tools: Optional list of tool definitions for function calling
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response

        Returns:
            Response from Azure OpenAI (dict if not streaming, generator if streaming)
        """
        try:
            request_params = {
                "model": self.settings.azure_openai_deployment_name,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if tools:
                request_params["tools"] = tools
                request_params["tool_choice"] = "auto"

            if stream:
                return await self.client.chat.completions.create(stream=True, **request_params)
            else:
                response = await self.client.chat.completions.create(**request_params)
                logger.debug(f"LLM response: {response.model_dump()}")
                return response.model_dump()

        except Exception as e:
            logger.error(f"Error calling Azure OpenAI: {e}")
            raise

    @trace(name="multimodal_process", trace_type="llm")
    async def process_multimodal(
        self,
        text: str,
        image_path: str | Path | None = None,
        system_prompt: str | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Process multi-modal input (text + optional image).

        Args:
            text: User text input
            image_path: Optional path to image file
            system_prompt: Optional system prompt
            tools: Optional list of tool definitions

        Returns:
            Response from Azure OpenAI
        """
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Build user message content
        user_content = []

        # Add text
        user_content.append({"type": "text", "text": text})

        # Add image if provided
        if image_path:
            image_data = self._encode_image(image_path)
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                }
            )
            logger.info(f"Processing multi-modal input with image: {image_path}")

        messages.append({"role": "user", "content": user_content})

        return await self.call_llm(messages=messages, tools=tools)

    @trace(name="identify_product_from_image", trace_type="llm")
    async def identify_product_from_image(
        self,
        image_path: str | Path,
        context: str = "",
    ) -> dict[str, Any] | None:
        """
        Identify product from image with structured output for inventory lookup.

        This specialized method extracts product attributes optimized for
        catalog search and inventory management.

        Args:
            image_path: Path to the product image
            context: Optional context from user (e.g., "check inventory for this")

        Returns:
            Dictionary with product attributes:
                - product_name: Product type and name
                - category: Product category
                - description: Detailed description
                - color: Primary color(s)
                - keywords: List of search keywords
                - confidence: Confidence score (0.0 to 1.0)
            Returns None if identification fails
        """
        import json

        system_prompt = """You are a retail product identification specialist. Analyze the image and extract product information.

Return ONLY a JSON object with these fields:
- product_name: The type and name of the product (e.g., "Wireless Mouse", "Running Shoes")
- category: One of: Electronics, Clothing, Groceries, Home & Garden, Sports & Outdoors, Books & Media, Toys & Games, Health & Beauty
- description: Detailed description of the product
- color: Primary color(s) of the product
- keywords: Array of search keywords (3-5 keywords)
- confidence: Your confidence level (0.0 to 1.0)

Example:
{
    "product_name": "Wireless Mouse",
    "category": "Electronics",
    "description": "Black wireless optical mouse with ergonomic design",
    "color": "black",
    "keywords": ["wireless mouse", "computer mouse", "black mouse", "optical mouse"],
    "confidence": 0.9
}"""

        try:
            response = await self.process_multimodal(
                text=context or "Identify this product for inventory lookup",
                image_path=image_path,
                system_prompt=system_prompt,
            )

            response_text = await self.extract_response_content(response)

            # Parse JSON response
            # Try to extract JSON from markdown code blocks if present
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()

            vision_data = json.loads(json_str)

            # Validate required fields
            required_fields = ["product_name", "category", "keywords"]
            if not all(field in vision_data for field in required_fields):
                logger.warning(f"Vision response missing required fields: {vision_data}")
                return None

            logger.info(
                f"Identified product: {vision_data.get('product_name')} "
                f"({vision_data.get('category')}) "
                f"confidence: {vision_data.get('confidence', 0)}"
            )

            return vision_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision response as JSON: {e}")
            logger.debug(f"Response text: {response_text if 'response_text' in locals() else 'N/A'}")
            return None
        except Exception as e:
            logger.error(f"Error identifying product from image: {e}", exc_info=True)
            return None

    def _encode_image(self, image_path: str | Path) -> str:
        """
        Encode image to base64 for API.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def extract_response_content(self, response: dict[str, Any]) -> str:
        """
        Extract text content from LLM response.

        Args:
            response: Response dictionary from call_llm()

        Returns:
            Extracted text content
        """
        try:
            choices = response.get("choices", [])
            if not choices:
                return ""

            message = choices[0].get("message", {})
            content = message.get("content", "")

            return content or ""

        except Exception as e:
            logger.error(f"Error extracting response content: {e}")
            return ""

    async def extract_tool_calls(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract tool calls from LLM response.

        Args:
            response: Response dictionary from call_llm()

        Returns:
            List of tool call dictionaries
        """
        try:
            choices = response.get("choices", [])
            if not choices:
                return []

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls") or []

            return [
                {
                    "id": tc.get("id"),
                    "type": tc.get("type"),
                    "function": {
                        "name": tc.get("function", {}).get("name"),
                        "arguments": tc.get("function", {}).get("arguments"),
                    },
                }
                for tc in tool_calls
            ]

        except Exception as e:
            logger.error(f"Error extracting tool calls: {e}")
            return []

    async def stream_response(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None):
        """
        Stream response from Azure OpenAI.

        Args:
            messages: List of message dictionaries
            tools: Optional list of tool definitions

        Yields:
            Chunks of the response
        """
        stream = await self.call_llm(messages=messages, tools=tools, stream=True)

        async for chunk in stream:
            chunk_dict = chunk.model_dump()
            choices = chunk_dict.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
