"""Image-based product lookup and inventory management processor.

This module provides the ImageProductProcessor class for orchestrating complete
image-based product workflows, from vision analysis to inventory recommendations.
"""

import json
import logging
from pathlib import Path
from typing import Any

from chatassistant_retail.llm import AzureOpenAIClient
from chatassistant_retail.rag import Retriever
from chatassistant_retail.tools.mcp_server import ToolExecutor

logger = logging.getLogger(__name__)


class ImageProductProcessor:
    """Orchestrates image-based product identification and inventory management.

    The ImageProductProcessor combines computer vision (Azure OpenAI GPT-4o Vision),
    semantic search (RAG), and inventory management tools to provide intelligent
    product identification and stock analysis from uploaded images.

    Workflow Steps:
        1. Vision Extraction
           - Analyze uploaded image using GPT-4o Vision
           - Extract: product_name, category, description, color, keywords
           - Return confidence score (0.0 to 1.0)
           - Minimum confidence threshold: 0.3

        2. Catalog Search
           - Build search query from extracted keywords
           - Use RAG retriever for hybrid search (vector + keyword + semantic)
           - Return top 5 matching products with scores

        3. Inventory Status Check
           - Query inventory for each matched product (SKU)
           - Check stock levels against reorder thresholds
           - Identify low-stock items

        4. Reorder Recommendations
           - For low-stock items, calculate reorder quantities
           - Estimate days until stockout based on sales velocity
           - Assign urgency level (LOW/MEDIUM/HIGH)

        5. Response Generation
           - Format results with inventory status
           - Include reorder recommendations for low-stock items
           - Provide actionable next steps

    Attributes:
        MIN_CONFIDENCE_THRESHOLD (float): Minimum vision confidence score (default: 0.3)
        MAX_MATCHES_TO_SHOW (int): Maximum products to return (default: 5)

    Usage Example:
        >>> from chatassistant_retail.workflow import ImageProductProcessor
        >>> from chatassistant_retail.llm import AzureOpenAIClient
        >>> from chatassistant_retail.rag import Retriever
        >>> from chatassistant_retail.tools.mcp_server import ToolExecutor
        >>>
        >>> processor = ImageProductProcessor()
        >>> llm_client = AzureOpenAIClient()
        >>> rag_retriever = Retriever()
        >>> tool_executor = ToolExecutor()
        >>>
        >>> result = await processor.process_image_query(
        ...     image_path="/path/to/product.jpg",
        ...     user_text="Check inventory for this item",
        ...     llm_client=llm_client,
        ...     rag_retriever=rag_retriever,
        ...     tool_executor=tool_executor
        ... )
        >>>
        >>> print(result["response"])
        🔍 Product Identification Results
        I identified: Wireless Mouse
        Category: Electronics

        📦 Matching Products in Inventory:
        1. Wireless Optical Mouse (SKU-10001)
           - Current Stock: 50 units ✅
        2. Ergonomic Wireless Mouse (SKU-10002)
           - Current Stock: 8 units ⚠️

        💡 Recommendations:
        ⚠️  SKU-10002 is running low:
           - Days until stockout: 5
           - Suggested order quantity: 50 units
           - Urgency: HIGH

    Error Handling:
        The processor includes comprehensive error handling:
        - Image analysis failures return user-friendly error messages
        - No matches found provides alternative actions
        - Individual product errors logged but don't fail entire workflow
        - All exceptions caught and returned in standardized error format

    Architecture:
        Image Upload → Vision Extraction → Catalog Search → Inventory Check → Response
             ↓              ↓                    ↓                 ↓             ↓
         User Photo    Product Info        RAG Retriever      Tool Calls    Formatted
          (PNG/JPG)   (name, category)   (hybrid search)   (check_stock)   Response
                       (confidence)         (top 5 SKUs)    (reorder calc)  (with recs)

    Returns:
        Dict with keys:
            - response (str): Formatted response text for user
            - context (dict): Structured data (vision_result, matched_products)
            - tool_calls (list): Tools executed during workflow
            - error (str | None): Error message if workflow failed
    """

    # Confidence threshold for product matching
    MIN_CONFIDENCE_THRESHOLD = 0.3
    MAX_MATCHES_TO_SHOW = 5

    async def process_image_query(
        self,
        image_path: str | Path,
        user_text: str,
        llm_client: AzureOpenAIClient,
        rag_retriever: Retriever,
        tool_executor: ToolExecutor,
    ) -> dict[str, Any]:
        """
        Process an image query to identify product and check inventory.

        Args:
            image_path: Path to the uploaded product image
            user_text: User's text message (may be empty)
            llm_client: Azure OpenAI client for vision processing
            rag_retriever: RAG retriever for product catalog search
            tool_executor: Tool executor for inventory operations

        Returns:
            Dictionary with:
                - response: Formatted response text
                - context: Product and inventory context
                - tool_calls: List of tools executed
                - error: Error message if any
        """
        logger.info(f"Processing image query: {image_path}")

        try:
            # Step 1: Extract product information from image
            vision_result = await self._extract_product_from_image(
                image_path=image_path,
                user_text=user_text,
                llm_client=llm_client,
            )

            if not vision_result:
                return self._build_error_response(
                    "I had trouble analyzing the image. Please ensure the image is clear and try again."
                )

            logger.info(f"Vision extraction: {vision_result.get('product_name')} ({vision_result.get('category')})")

            # Step 2: Search product catalog
            matching_products = await self._search_catalog(
                vision_result=vision_result,
                rag_retriever=rag_retriever,
            )

            if not matching_products:
                return self._handle_no_matches(vision_result)

            logger.info(f"Found {len(matching_products)} matching products")

            # Step 3: Check inventory status for matched products
            inventory_results, tool_calls_data = await self._check_inventory_status(
                products=matching_products,
                tool_executor=tool_executor,
            )

            # Step 4: Generate formatted response
            response_text = await self._generate_response(
                vision_result=vision_result,
                inventory_results=inventory_results,
                llm_client=llm_client,
            )

            return {
                "response": response_text,
                "context": {
                    "vision_result": vision_result,
                    "matched_products": inventory_results,
                    "match_count": len(matching_products),
                },
                "tool_calls": tool_calls_data,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Error processing image query: {e}", exc_info=True)
            return self._build_error_response(f"I encountered an error while processing the image: {str(e)}")

    async def _extract_product_from_image(
        self,
        image_path: str | Path,
        user_text: str,
        llm_client: AzureOpenAIClient,
    ) -> dict[str, Any] | None:
        """
        Extract product information from image using vision model.

        Args:
            image_path: Path to the product image
            user_text: User's accompanying text
            llm_client: Azure OpenAI client

        Returns:
            Dictionary with product attributes or None if extraction fails
        """
        try:
            # Use the new specialized method (to be added to llm_client)
            if hasattr(llm_client, "identify_product_from_image"):
                return await llm_client.identify_product_from_image(
                    image_path=image_path,
                    context=user_text,
                )

            # Fallback to generic multimodal processing
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

            response = await llm_client.process_multimodal(
                text=user_text or "Identify this product",
                image_path=image_path,
                system_prompt=system_prompt,
            )

            response_text = await llm_client.extract_response_content(response)

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

            return vision_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            return None
        except Exception as e:
            logger.error(f"Error extracting product from image: {e}", exc_info=True)
            return None

    async def _search_catalog(
        self,
        vision_result: dict[str, Any],
        rag_retriever: Retriever,
    ) -> list[dict[str, Any]]:
        """
        Search product catalog for matches based on vision extraction.

        Args:
            vision_result: Product information extracted from image
            rag_retriever: RAG retriever instance

        Returns:
            List of matching products with scores
        """
        try:
            # Build search query from vision results
            product_name = vision_result.get("product_name", "")
            category = vision_result.get("category", "")
            color = vision_result.get("color", "")

            # Combine into search query
            query_parts = [product_name, category, color]
            search_query = " ".join([p for p in query_parts if p]).strip()

            logger.info(f"Searching catalog with query: {search_query}")

            # Search using RAG retriever (supports hybrid search)
            results = await rag_retriever.retrieve(
                query=search_query,
                top_k=self.MAX_MATCHES_TO_SHOW,
            )

            # Filter by confidence threshold
            confidence = vision_result.get("confidence", 1.0)
            if confidence < self.MIN_CONFIDENCE_THRESHOLD:
                logger.warning(f"Low confidence ({confidence}) - showing results but flagging uncertainty")

            return results

        except Exception as e:
            logger.error(f"Error searching catalog: {e}", exc_info=True)
            return []

    async def _check_inventory_status(
        self,
        products: list[dict[str, Any]],
        tool_executor: ToolExecutor,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Check inventory status for matched products.

        Args:
            products: List of matched products from catalog search
            tool_executor: Tool executor for inventory operations

        Returns:
            Tuple of (inventory_results, tool_calls_data):
                - inventory_results: List of products with inventory status and reorder recommendations
                - tool_calls_data: List of tool calls executed (for state tracking)
        """
        inventory_results = []
        tool_calls_data = []

        for product in products:
            try:
                sku = product.get("sku")
                if not sku:
                    continue

                # Query inventory for this SKU
                tool_args = {"sku": sku}
                inventory_data = await tool_executor.execute_tool(
                    "query_inventory",
                    tool_args,
                )

                # Record tool call for state tracking
                tool_calls_data.append(
                    {
                        "tool": "query_inventory",
                        "args": tool_args,
                        "result": inventory_data,
                    }
                )

                # Extract product info from inventory response
                if inventory_data and inventory_data.get("products"):
                    product_info = inventory_data["products"][0]

                    current_stock = product_info.get("current_stock", 0)
                    reorder_level = product_info.get("reorder_level", 0)

                    # Check if low stock
                    is_low_stock = current_stock <= reorder_level

                    result = {
                        "sku": sku,
                        "name": product_info.get("name"),
                        "category": product_info.get("category"),
                        "price": product_info.get("price"),
                        "current_stock": current_stock,
                        "reorder_level": reorder_level,
                        "supplier": product_info.get("supplier"),
                        "status": "LOW STOCK" if is_low_stock else "OK",
                        "is_low_stock": is_low_stock,
                        "search_score": product.get("search_score", 0),
                    }

                    # If low stock, calculate reorder recommendation
                    if is_low_stock:
                        try:
                            reorder_args = {"sku": sku}
                            reorder_calc = await tool_executor.execute_tool(
                                "calculate_reorder_point",
                                reorder_args,
                            )

                            # Record reorder tool call
                            tool_calls_data.append(
                                {
                                    "tool": "calculate_reorder_point",
                                    "args": reorder_args,
                                    "result": reorder_calc,
                                }
                            )

                            if reorder_calc and "recommendations" in reorder_calc:
                                result["reorder_recommendation"] = {
                                    "order_quantity": reorder_calc["recommendations"].get("order_quantity"),
                                    "days_until_stockout": reorder_calc["recommendations"].get("days_until_stockout"),
                                    "urgency": reorder_calc["recommendations"].get("urgency"),
                                }
                        except Exception as e:
                            logger.warning(f"Could not calculate reorder point for {sku}: {e}")

                    inventory_results.append(result)

            except Exception as e:
                logger.error(f"Error checking inventory for product: {e}", exc_info=True)
                continue

        return inventory_results, tool_calls_data

    async def _generate_response(
        self,
        vision_result: dict[str, Any],
        inventory_results: list[dict[str, Any]],
        llm_client: AzureOpenAIClient,
    ) -> str:
        """
        Generate formatted response with inventory status and recommendations.

        Args:
            vision_result: Product identification from vision
            inventory_results: Inventory status for matched products
            llm_client: LLM client for natural language generation

        Returns:
            Formatted response text
        """
        # Build response sections
        response_parts = []

        # Header
        product_name = vision_result.get("product_name", "Unknown Product")
        category = vision_result.get("category", "")
        response_parts.append("🔍 Product Identification Results\n")
        response_parts.append(f"I identified: {product_name}")
        if category:
            response_parts.append(f"Category: {category}")
        response_parts.append("")

        # Matching products section
        if len(inventory_results) == 0:
            return self._handle_no_matches(vision_result)["response"]

        response_parts.append("📦 Matching Products in Inventory:\n")

        low_stock_items = []

        for idx, product in enumerate(inventory_results, 1):
            response_parts.append(f"{idx}. {product['name']} (SKU: {product['sku']})")
            response_parts.append(f"   - Price: ${product['price']:.2f}")
            response_parts.append(f"   - Current Stock: {product['current_stock']} units")
            response_parts.append(f"   - Reorder Level: {product['reorder_level']} units")
            response_parts.append(f"   - Status: {product['status']}")
            response_parts.append(f"   - Supplier: {product['supplier']}")

            if product.get("is_low_stock"):
                low_stock_items.append(product)

            response_parts.append("")

        # Recommendations section
        if low_stock_items:
            response_parts.append("💡 Recommendations:\n")

            for product in low_stock_items:
                reorder = product.get("reorder_recommendation", {})

                if reorder:
                    response_parts.append(f"⚠️  {product['name']} (SKU: {product['sku']}) is running low:")
                    response_parts.append(f"   - Days until stockout: {reorder.get('days_until_stockout', 'unknown')}")
                    response_parts.append(f"   - Suggested order quantity: {reorder.get('order_quantity', 0)} units")
                    response_parts.append(f"   - Urgency: {reorder.get('urgency', 'MEDIUM')}")
                    response_parts.append("")
                else:
                    response_parts.append(f"⚠️  {product['name']} (SKU: {product['sku']}) is below reorder level")
                    response_parts.append("")

            response_parts.append("Would you like me to create a purchase order for any of these items?")
        else:
            response_parts.append("✅ All matched products have adequate stock levels.")

        return "\n".join(response_parts)

    def _handle_no_matches(self, vision_result: dict[str, Any]) -> dict[str, Any]:
        """
        Handle case where no products match the image.

        Args:
            vision_result: Product information from vision

        Returns:
            Response dictionary
        """
        product_name = vision_result.get("product_name", "Unknown")
        category = vision_result.get("category", "")
        description = vision_result.get("description", "")

        response_parts = [
            "🔍 Product Identified\n",
            "I can see this product in the image:",
            f"- Product: {product_name}",
        ]

        if category:
            response_parts.append(f"- Category: {category}")
        if description:
            response_parts.append(f"- Description: {description}")

        response_parts.extend(
            [
                "",
                "❌ Not Found in Inventory Catalog",
                "",
                "This product doesn't match anything in our current inventory.",
                "",
                "Options:",
                "1. Try searching with different keywords?",
            ]
        )

        if category:
            response_parts.append(f"2. Show similar products in {category}?")

        response_parts.append("3. Add as new product to track?")
        response_parts.append("")
        response_parts.append("What would you like to do?")

        return {
            "response": "\n".join(response_parts),
            "context": {
                "vision_result": vision_result,
                "match_found": False,
            },
            "tool_calls": [],
            "error": None,
        }

    def _build_error_response(self, error_message: str) -> dict[str, Any]:
        """
        Build error response dictionary.

        Args:
            error_message: Error message to include

        Returns:
            Error response dictionary
        """
        return {
            "response": error_message,
            "context": {},
            "tool_calls": [],
            "error": error_message,
        }
