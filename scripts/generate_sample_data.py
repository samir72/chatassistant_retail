#!/usr/bin/env python3
"""Generate sample data for retail inventory system."""

import json
import logging
from pathlib import Path

from chatassistant_retail.config import get_settings
from chatassistant_retail.data import SampleDataGenerator
from chatassistant_retail.data.models import Product, Sale

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_and_save_sample_data(
    count: int | None = None,
    months: int | None = None,
    save_to_disk: bool = True,
    data_dir: Path | None = None,
) -> tuple[list[Product], list[Sale]]:
    """
    Generate sample products and sales data.

    Args:
        count: Number of products to generate (defaults to settings.sample_data_products_count)
        months: Number of months of sales history (defaults to settings.sample_data_sales_months)
        save_to_disk: Whether to save JSON files to disk (default: True)
        data_dir: Directory to save files (defaults to project root/data/)

    Returns:
        Tuple of (products, sales) as lists of Product and Sale instances

    Raises:
        OSError: If save_to_disk=True and file writing fails
    """
    settings = get_settings()

    # Use defaults from settings if not provided
    if count is None:
        count = settings.sample_data_products_count
    if months is None:
        months = settings.sample_data_sales_months
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data"

    logger.info("Initializing sample data generator...")
    generator = SampleDataGenerator(seed=42)

    # Generate products
    logger.info(f"Generating {count} products...")
    products = generator.generate_products(count=count)
    logger.info(f"Generated {len(products)} products")

    # Generate sales history
    logger.info(f"Generating sales history for {months} months...")
    sales = generator.generate_sales_history(products=products, months=months)
    logger.info(f"Generated {len(sales)} sales transactions")

    # Save to disk if requested
    if save_to_disk:
        data_dir.mkdir(exist_ok=True)
        products_file = data_dir / "products.json"
        sales_file = data_dir / "sales_history.json"

        logger.info(f"Saving products to {products_file}...")
        try:
            with open(products_file, "w") as f:
                json.dump([p.model_dump() for p in products], f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Failed to save products: {e}")
            raise

        logger.info(f"Saving sales history to {sales_file}...")
        try:
            with open(sales_file, "w") as f:
                json.dump([s.model_dump() for s in sales], f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Failed to save sales history: {e}")
            raise

    return products, sales


def main():
    """Generate and save sample data with summary output."""
    try:
        # Generate and save data
        products, sales = generate_and_save_sample_data()

        # Get file paths for summary
        data_dir = Path(__file__).parent.parent / "data"
        products_file = data_dir / "products.json"
        sales_file = data_dir / "sales_history.json"

        # Print summary statistics
        print("\n" + "=" * 60)
        print("SAMPLE DATA GENERATION SUMMARY")
        print("=" * 60)
        print(f"Total Products: {len(products)}")
        print(f"Total Sales: {len(sales)}")
        print("\nProducts by Category:")
        category_counts = {}
        for product in products:
            category_counts[product.category] = category_counts.get(product.category, 0) + 1
        for category, count in sorted(category_counts.items()):
            print(f"  {category}: {count}")

        print("\nStock Distribution:")
        out_of_stock = sum(1 for p in products if p.current_stock == 0)
        low_stock = sum(1 for p in products if 0 < p.current_stock <= p.reorder_level)
        normal_stock = sum(1 for p in products if p.current_stock > p.reorder_level)
        print(f"  Out of Stock: {out_of_stock}")
        print(f"  Low Stock: {low_stock}")
        print(f"  Normal Stock: {normal_stock}")

        print("\nSales by Channel:")
        channel_counts = {}
        for sale in sales:
            channel_counts[sale.channel] = channel_counts.get(sale.channel, 0) + 1
        for channel, count in sorted(channel_counts.items()):
            print(f"  {channel.capitalize()}: {count}")

        print("\nFiles saved:")
        print(f"  {products_file}")
        print(f"  {sales_file}")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Failed to generate sample data: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
