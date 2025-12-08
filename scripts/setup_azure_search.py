"""Setup Azure Cognitive Search index for chatassistant_retail."""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for importing sibling scripts
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatassistant_retail.config import get_settings
from chatassistant_retail.rag import AzureSearchClient, EmbeddingsClient
from scripts.generate_sample_data import generate_and_save_sample_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Set up Azure Search index and optionally load sample data."""
    try:
        settings = get_settings()

        # Initialize clients
        logger.info("Initializing Azure Search client...")
        search_client = AzureSearchClient(settings)

        if not search_client.enabled:
            logger.error("Azure Search not configured. Please set environment variables:")
            logger.error("  - AZURE_COGNITIVE_SEARCH_ENDPOINT")
            logger.error("  - AZURE_COGNITIVE_SEARCH_API_KEY")
            logger.error("  - AZURE_SEARCH_INDEX_NAME (optional, defaults to 'products')")
            return 1

        # Check if index already exists
        index_name = settings.azure_search_index_name
        if search_client.index_exists():
            logger.warning(f"Index '{index_name}' already exists.")
            response = input("Do you want to recreate it? This will delete all existing data. (yes/no): ")
            if response.lower() != "yes":
                logger.info("Setup cancelled.")
                return 0

            logger.info(f"Deleting existing index '{index_name}'...")
            try:
                search_client.index_client.delete_index(index_name)
                logger.info(f"Index '{index_name}' deleted successfully.")
                # Wait a moment for deletion to complete
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Failed to delete index: {e}")
                return 1

        # Create index
        logger.info(f"Creating index '{index_name}'...")
        search_client.create_index(embedding_dimensions=1536)

        # Wait a moment for index creation to complete
        await asyncio.sleep(2)

        # Verify creation
        if not search_client.index_exists():
            logger.error("Failed to create index.")
            return 1

        logger.info(f"Index '{index_name}' created successfully!")

        # Get index schema info
        schema = search_client.get_index_schema()
        if schema:
            logger.info(f"Index has {len(schema.get('fields', []))} fields")
            logger.info(f"Vector search configured: {bool(schema.get('vector_search'))}")
            logger.info(f"Semantic search configured: {bool(schema.get('semantic_search'))}")

        # Ask if user wants to load sample data
        response = input("\nDo you want to load sample product data (500 products)? (yes/no): ")
        if response.lower() == "yes":
            try:
                logger.info("Generating sample products and sales history...")
                products, sales = generate_and_save_sample_data(
                    count=500,
                    months=6,
                    save_to_disk=True,  # Overwrite data/products.json and data/sales_history.json
                )
                logger.info(f"Generated {len(products)} products and {len(sales)} sales transactions")
                logger.info("Sample data saved to data/products.json and data/sales_history.json")
            except Exception as e:
                logger.error(f"Failed to generate sample data: {e}")
                logger.error("Cannot continue without sample data")
                return 1

            logger.info("Generating embeddings (this may take a few minutes)...")
            embeddings_client = EmbeddingsClient(settings)

            # Create text for embeddings
            texts = [f"{p.name} {p.category} {p.description}" for p in products]

            # Generate embeddings in batches
            embeddings = await embeddings_client.generate_embeddings_batch(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")

            logger.info("Uploading products to index (batches of 100)...")
            await search_client.index_products(products, embeddings)

            # Wait for indexing to complete
            await asyncio.sleep(3)

            stats = search_client.get_index_stats()
            doc_count = stats.get("document_count", 0)
            logger.info(f"Successfully indexed {doc_count} products")

            if doc_count != len(products):
                logger.warning(f"Expected {len(products)} products but index shows {doc_count}")

        # Show health check
        logger.info("\nPerforming health check...")
        health = search_client.check_index_health()
        logger.info(f"Index health: {health['overall_status']}")
        logger.info(f"Document count: {health.get('stats', {}).get('document_count', 0)}")
        logger.info(f"Storage size: {health.get('stats', {}).get('storage_size_bytes', 0)} bytes")

        if health.get("schema_validation", {}).get("valid"):
            logger.info("Schema validation: PASSED")
        else:
            logger.warning("Schema validation: FAILED")
            for diff in health.get("schema_validation", {}).get("field_differences", []):
                logger.warning(f"  - {diff}")

        logger.info("\nSetup complete!")
        logger.info(f"Your Azure Search index '{index_name}' is ready to use.")
        return 0

    except KeyboardInterrupt:
        logger.info("\nSetup interrupted by user.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during setup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
