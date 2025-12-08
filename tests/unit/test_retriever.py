"""Unit tests for RAG retriever."""

import pytest

from chatassistant_retail.rag import Retriever


class TestRetriever:
    """Test RAG retriever functionality."""

    @pytest.mark.asyncio
    async def test_retriever_initialization(self):
        """Test retriever initialization."""
        retriever = Retriever()

        assert retriever is not None
        if retriever.use_local_data:
            assert len(retriever.local_products) > 0

    @pytest.mark.asyncio
    async def test_basic_retrieval(self):
        """Test basic product retrieval."""
        retriever = Retriever()
        products = await retriever.retrieve("wireless mouse", top_k=5)

        assert isinstance(products, list)
        assert len(products) <= 5

    @pytest.mark.asyncio
    async def test_retrieve_empty_query(self):
        """Test retrieval with empty query."""
        retriever = Retriever()
        products = await retriever.retrieve("", top_k=5)

        assert isinstance(products, list)

    @pytest.mark.asyncio
    async def test_get_low_stock_items(self):
        """Test getting low stock items."""
        retriever = Retriever()
        low_stock = await retriever.get_low_stock_items(threshold=10, top_k=10)

        assert isinstance(low_stock, list)
        for product in low_stock:
            assert product.get("current_stock", 0) <= 10

    @pytest.mark.asyncio
    async def test_get_products_by_category(self):
        """Test getting products by category."""
        retriever = Retriever()
        products = await retriever.get_products_by_category("Electronics", top_k=10)

        assert isinstance(products, list)
        for product in products:
            assert product.get("category") == "Electronics"

    @pytest.mark.asyncio
    async def test_get_product_by_sku(self):
        """Test getting specific product by SKU."""
        retriever = Retriever()
        product = await retriever.get_product_by_sku("SKU-10000")

        if product:
            assert product.get("sku") == "SKU-10000"
            assert "name" in product
            assert "price" in product

    @pytest.mark.asyncio
    async def test_get_product_invalid_sku(self):
        """Test getting product with invalid SKU."""
        retriever = Retriever()
        product = await retriever.get_product_by_sku("INVALID-SKU-999999")

        assert product is None

    @pytest.mark.asyncio
    async def test_get_reorder_recommendations(self):
        """Test getting reorder recommendations."""
        retriever = Retriever()
        recommendations = await retriever.get_reorder_recommendations(top_k=10)

        assert isinstance(recommendations, list)
        # All recommended products should have stock <= reorder level
        for product in recommendations:
            assert product.get("current_stock", float("inf")) <= product.get("reorder_level", 0)

    @pytest.mark.asyncio
    async def test_retrieve_with_different_top_k(self):
        """Test retrieval with different top_k values."""
        retriever = Retriever()

        for k in [1, 3, 5, 10]:
            products = await retriever.retrieve("product", top_k=k)
            assert len(products) <= k


class TestLocalDataRetrieval:
    """Test local data fallback retrieval."""

    @pytest.mark.asyncio
    async def test_local_keyword_matching(self):
        """Test keyword matching in local retrieval."""
        retriever = Retriever()

        # Search for specific category
        products = await retriever._retrieve_local("electronics", top_k=5)

        # Should find electronics products
        if products:
            assert any("electronic" in p.get("name", "").lower() for p in products) or any(
                p.get("category", "").lower() == "electronics" for p in products
            )

    @pytest.mark.asyncio
    async def test_local_low_stock_boost(self):
        """Test that low stock items get boosted in search."""
        retriever = Retriever()

        products = await retriever._retrieve_local("low stock", top_k=5)

        # Results should include low stock items
        if products:
            assert any(p.get("current_stock", float("inf")) <= p.get("reorder_level", 0) for p in products)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
