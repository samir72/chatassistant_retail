"""Retriever for RAG-based context retrieval."""

import json
import logging
from pathlib import Path
from typing import Any

from chatassistant_retail.config import get_settings
from chatassistant_retail.data.models import Product
from chatassistant_retail.observability import trace

from .azure_search_client import AzureSearchClient
from .embeddings import EmbeddingsClient

logger = logging.getLogger(__name__)


class Retriever:
    """Retriever for fetching relevant context from product catalog."""

    def __init__(self, settings=None):
        """
        Initialize retriever.

        Args:
            settings: Optional Settings instance. If None, uses get_settings().
        """
        self.settings = settings or get_settings()
        self.embeddings_client = EmbeddingsClient(settings=self.settings)
        self.search_client = AzureSearchClient(settings=self.settings)

        # Fallback to local data if Azure Search not configured
        self.use_local_data = not self.search_client.enabled
        if self.use_local_data:
            logger.info("Using local product data for retrieval (Azure Search not configured)")
            self._load_local_products()

    def _load_local_products(self):
        """Load products from local JSON file as fallback."""
        try:
            data_dir = Path(__file__).parent.parent.parent.parent / "data"
            products_file = data_dir / "products.json"

            if products_file.exists():
                with open(products_file) as f:
                    products_data = json.load(f)
                    self.local_products = [Product(**p) for p in products_data]
                logger.info(f"Loaded {len(self.local_products)} products from local file")
            else:
                logger.warning(f"Local products file not found: {products_file}")
                self.local_products = []

        except Exception as e:
            logger.error(f"Error loading local products: {e}")
            self.local_products = []

    @trace(name="rag_retrieve", trace_type="rag")
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_vector_search: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant products based on query.

        Args:
            query: User query text
            top_k: Number of results to return
            use_vector_search: Whether to use vector search (requires embedding)

        Returns:
            List of relevant product dictionaries
        """
        if self.use_local_data:
            return await self._retrieve_local(query, top_k)

        try:
            # Generate query embedding for vector search
            query_vector = None
            if use_vector_search:
                query_vector = await self.embeddings_client.generate_embedding(query)

            # Perform hybrid search
            products = await self.search_client.search_products(
                query=query,
                query_vector=query_vector,
                top_k=top_k,
                use_semantic=True,
            )

            logger.info(f"Retrieved {len(products)} products for query: {query}")
            return products

        except Exception as e:
            logger.error(f"Error retrieving products: {e}")
            # Fallback to local data
            return await self._retrieve_local(query, top_k)

    async def _retrieve_local(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve from local products using simple keyword matching.

        Args:
            query: User query text
            top_k: Number of results to return

        Returns:
            List of relevant product dictionaries
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        # Score products based on keyword matches
        scored_products = []
        for product in self.local_products:
            score = 0

            # Check name
            if any(term in product.name.lower() for term in query_terms):
                score += 3

            # Check category
            if any(term in product.category.lower() for term in query_terms):
                score += 2

            # Check description
            if any(term in product.description.lower() for term in query_terms):
                score += 1

            # Check for specific keywords
            if "low stock" in query_lower or "running low" in query_lower:
                if product.current_stock <= product.reorder_level:
                    score += 5

            if score > 0:
                product_dict = product.model_dump()
                product_dict["search_score"] = score
                scored_products.append(product_dict)

        # Sort by score and return top_k
        scored_products.sort(key=lambda x: x["search_score"], reverse=True)
        results = scored_products[:top_k]

        logger.info(f"Retrieved {len(results)} products locally for query: {query}")
        return results

    async def get_low_stock_items(self, threshold: int = 10, top_k: int = 20) -> list[dict[str, Any]]:
        """
        Get products with low stock.

        Args:
            threshold: Stock threshold
            top_k: Maximum results

        Returns:
            List of low stock products
        """
        if self.use_local_data:
            low_stock = [p.model_dump() for p in self.local_products if p.current_stock <= threshold]
            return sorted(low_stock, key=lambda x: x["current_stock"])[:top_k]

        return await self.search_client.get_low_stock_items(threshold, top_k)

    async def get_products_by_category(self, category: str, top_k: int = 20) -> list[dict[str, Any]]:
        """
        Get products by category.

        Args:
            category: Product category
            top_k: Maximum results

        Returns:
            List of products in category
        """
        if self.use_local_data:
            category_products = [p.model_dump() for p in self.local_products if p.category.lower() == category.lower()]
            return category_products[:top_k]

        return await self.search_client.get_products_by_category(category, top_k)

    async def get_product_by_sku(self, sku: str) -> dict[str, Any] | None:
        """
        Get product by SKU.

        Args:
            sku: Product SKU

        Returns:
            Product dictionary or None
        """
        if self.use_local_data:
            for product in self.local_products:
                if product.sku == sku:
                    return product.model_dump()
            return None

        return await self.search_client.get_product_by_sku(sku)

    async def get_reorder_recommendations(self, top_k: int = 10) -> list[dict[str, Any]]:
        """
        Get products that need reordering.

        Args:
            top_k: Maximum results

        Returns:
            List of products needing reorder
        """
        if self.use_local_data:
            needs_reorder = [p.model_dump() for p in self.local_products if p.current_stock <= p.reorder_level]
            # Sort by urgency (lowest stock first)
            needs_reorder.sort(key=lambda x: x["current_stock"] - x["reorder_level"])
            return needs_reorder[:top_k]

        # Use Azure Search with filter
        filter_expr = "current_stock le reorder_level"
        return await self.search_client.search_products(
            query="*",
            top_k=top_k,
            filter_expression=filter_expr,
            use_semantic=False,
        )
