"""Unit tests for inventory tools."""

import pytest

from chatassistant_retail.tools.inventory_tools import (
    calculate_reorder_point_impl,
    query_inventory_impl,
)


class TestInventoryTools:
    """Test inventory management tools."""

    @pytest.mark.asyncio
    async def test_query_inventory_low_stock(self):
        """Test querying low stock items."""
        result = await query_inventory_impl(low_stock=True, threshold=10)

        assert result["success"] is True
        assert "summary" in result
        assert "products" in result
        assert result["summary"]["low_stock_items"] > 0

    @pytest.mark.asyncio
    async def test_query_inventory_by_sku(self):
        """Test querying specific product by SKU."""
        result = await query_inventory_impl(sku="SKU-10000")

        assert result["success"] is True
        assert len(result["products"]) <= 1
        if result["products"]:
            assert result["products"][0]["sku"] == "SKU-10000"

    @pytest.mark.asyncio
    async def test_query_inventory_by_category(self):
        """Test querying products by category."""
        result = await query_inventory_impl(category="Electronics")

        assert result["success"] is True
        for product in result["products"]:
            assert product["category"] == "Electronics"

    @pytest.mark.asyncio
    async def test_calculate_reorder_point_valid_sku(self):
        """Test calculating reorder point for valid product."""
        result = await calculate_reorder_point_impl(sku="SKU-10000", lead_time_days=7)

        assert result["success"] is True
        assert "product" in result
        assert "sales_analysis" in result
        assert "calculation" in result
        assert "recommendations" in result

        # Check that calculations are present
        calc = result["calculation"]
        assert calc["lead_time_days"] == 7
        assert calc["recommended_reorder_point"] >= 0

    @pytest.mark.asyncio
    async def test_calculate_reorder_point_invalid_sku(self):
        """Test calculating reorder point for non-existent product."""
        result = await calculate_reorder_point_impl(sku="INVALID-SKU")

        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_reorder_point_urgency_levels(self):
        """Test that urgency levels are calculated correctly."""
        # Test with a low stock SKU
        result = await calculate_reorder_point_impl(sku="SKU-10001", lead_time_days=7)

        if result["success"]:
            assert "recommendations" in result
            assert "urgency" in result["recommendations"]
            assert result["recommendations"]["urgency"] in ["HIGH", "MEDIUM", "LOW"]


class TestQueryInventoryResults:
    """Test query inventory result formatting."""

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Test that results have proper structure."""
        result = await query_inventory_impl()

        assert "success" in result
        assert "message" in result
        assert "summary" in result
        assert "products" in result

    @pytest.mark.asyncio
    async def test_summary_statistics(self):
        """Test summary statistics calculation."""
        result = await query_inventory_impl()

        summary = result["summary"]
        assert "total_items" in summary
        assert "low_stock_items" in summary
        assert "out_of_stock_items" in summary
        assert "total_inventory_value" in summary

        # Values should be non-negative
        assert summary["total_items"] >= 0
        assert summary["low_stock_items"] >= 0
        assert summary["out_of_stock_items"] >= 0
        assert summary["total_inventory_value"] >= 0

    @pytest.mark.asyncio
    async def test_product_fields(self):
        """Test that product records have all required fields."""
        result = await query_inventory_impl(sku="SKU-10000")

        if result["products"]:
            product = result["products"][0]
            required_fields = [
                "sku",
                "name",
                "category",
                "price",
                "current_stock",
                "reorder_level",
                "supplier",
                "status",
            ]

            for field in required_fields:
                assert field in product


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
