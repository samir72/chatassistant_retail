"""Setup Azure Cognitive Search index for chatassistant_retail."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for importing sibling scripts
sys.path.insert(0, str(Path(__file__).parent.parent))

from chatassistant_retail.config import get_settings
from chatassistant_retail.data.models import Product
from chatassistant_retail.rag import AzureSearchClient, EmbeddingsClient
from scripts.generate_sample_data import generate_and_save_sample_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Setup and manage Azure AI Search index for product catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Initial setup (default behavior)
  python scripts/setup_azure_search.py

  # Sync changes from local JSON to Azure index
  python scripts/setup_azure_search.py --sync

  # Full reindex (delete and recreate)
  python scripts/setup_azure_search.py --full-reindex

  # Sync without confirmation prompt (CI/CD usage)
  python scripts/setup_azure_search.py --sync --yes
        """,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--sync",
        action="store_true",
        help="Sync local products.json to Azure index (detect and apply inserts/updates/deletes)",
    )
    group.add_argument(
        "--full-reindex",
        action="store_true",
        help="Delete entire index and recreate from scratch",
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompts (auto-confirm)",
    )

    return parser.parse_args()


def load_local_products() -> list[Product]:
    """Load products from local JSON file."""
    data_dir = Path(__file__).parent.parent / "data"
    products_file = data_dir / "products.json"

    if not products_file.exists():
        raise FileNotFoundError(f"Products file not found: {products_file}")

    with open(products_file) as f:
        products_data = json.load(f)

    return [Product(**p) for p in products_data]


async def load_sample_data(search_client: AzureSearchClient, settings) -> int:
    """Load sample data into the index."""
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

    return 0


async def initial_setup_operation(search_client: AzureSearchClient, settings, args) -> int:
    """
    Initial setup: Create index and optionally load sample data.
    This is the default behavior (backward compatible).
    """
    index_name = settings.azure_search_index_name

    # Check if index already exists
    if search_client.index_exists():
        logger.warning(f"Index '{index_name}' already exists.")

        if args.yes:
            response = "yes"
        else:
            response = input("Do you want to recreate it? This will delete all existing data. (yes/no): ")

        if response.lower() != "yes":
            logger.info("Setup cancelled.")
            logger.info("Hint: Use --sync to update existing index without recreating it.")
            return 0

        logger.info(f"Deleting existing index '{index_name}'...")
        try:
            search_client.index_client.delete_index(index_name)
            logger.info(f"Index '{index_name}' deleted successfully.")
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
    if args.yes:
        load_data = True
    else:
        response = input("\nDo you want to load sample product data (500 products)? (yes/no): ")
        load_data = response.lower() == "yes"

    if load_data:
        result = await load_sample_data(search_client, settings)
        if result != 0:
            return result
    else:
        logger.info("Index created successfully. No data loaded.")
        logger.info("Hint: Use --sync to load products from data/products.json")

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


async def sync_operation(search_client: AzureSearchClient, settings, args) -> int:
    """
    Sync operation: Detect and apply changes from local JSON to Azure index.
    """
    from scripts.index_diff import calculate_diff

    index_name = settings.azure_search_index_name

    # Check if index exists
    if not search_client.index_exists():
        logger.error(f"Index '{index_name}' does not exist.")
        logger.error("Please run initial setup first:")
        logger.error("  python scripts/setup_azure_search.py")
        return 1

    # Load local products
    logger.info("Loading local products from data/products.json...")
    try:
        local_products = load_local_products()
        logger.info(f"Loaded {len(local_products)} products from local file")
    except Exception as e:
        logger.error(f"Failed to load local products: {e}")
        return 1

    # Fetch indexed documents
    logger.info("Fetching documents from Azure Search index...")
    try:
        indexed_documents = await search_client.get_all_documents()
        logger.info(f"Retrieved {len(indexed_documents)} documents from index")
    except Exception as e:
        logger.error(f"Failed to fetch indexed documents: {e}")
        return 1

    # Calculate diff
    logger.info("Calculating changes...")
    diff = calculate_diff(local_products, indexed_documents)

    # Display summary
    print("\n" + "=" * 60)
    print(diff.summary())
    print("=" * 60 + "\n")

    if diff.total_changes() == 0:
        logger.info("No changes detected. Index is up to date.")
        return 0

    # Confirm with user
    if not args.yes:
        response = input("Apply these changes to Azure Search index? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Sync cancelled.")
            return 0

    # Apply changes
    logger.info("Applying changes to Azure Search index...")

    # Step 1: Delete products
    if diff.deletes:
        logger.info(f"Deleting {len(diff.deletes)} products...")
        delete_result = await search_client.delete_products_by_sku(diff.deletes)
        logger.info(f"Deleted {delete_result['succeeded']} / {delete_result['total']} products")

        if delete_result["errors"]:
            logger.warning(f"Delete errors: {len(delete_result['errors'])}")
            for error in delete_result["errors"][:5]:  # Show first 5 errors
                logger.warning(f"  - {error}")

    # Step 2: Upsert (insert + update)
    products_to_upsert = diff.inserts + diff.updates
    if products_to_upsert:
        logger.info(f"Upserting {len(products_to_upsert)} products (inserts + updates)...")

        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings_client = EmbeddingsClient(settings)
        texts = [f"{p.name} {p.category} {p.description}" for p in products_to_upsert]
        embeddings = await embeddings_client.generate_embeddings_batch(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Upsert products
        upsert_result = await search_client.upsert_products(products_to_upsert, embeddings)
        logger.info(f"Upserted {upsert_result['succeeded']} / {upsert_result['total']} products")

        if upsert_result["errors"]:
            logger.warning(f"Upsert errors: {len(upsert_result['errors'])}")
            for error in upsert_result["errors"][:5]:
                logger.warning(f"  - {error}")

    # Wait for indexing
    await asyncio.sleep(3)

    # Verify final state
    logger.info("\nVerifying sync results...")
    stats = search_client.get_index_stats()
    doc_count = stats.get("document_count", 0)
    expected_count = len(local_products)

    logger.info(f"Index document count: {doc_count}")
    logger.info(f"Expected count: {expected_count}")

    if doc_count == expected_count:
        logger.info("✓ Sync completed successfully!")
    else:
        logger.warning(f"⚠ Document count mismatch (expected {expected_count}, got {doc_count})")

    return 0


async def full_reindex_operation(search_client: AzureSearchClient, settings, args) -> int:
    """
    Full reindex: Delete entire index and recreate from local JSON.
    """
    index_name = settings.azure_search_index_name

    # Confirm destructive operation
    if not args.yes:
        logger.warning(f"This will DELETE index '{index_name}' and recreate it from scratch.")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Full reindex cancelled.")
            return 0

    # Delete index if exists
    if search_client.index_exists():
        logger.info(f"Deleting index '{index_name}'...")
        try:
            search_client.index_client.delete_index(index_name)
            logger.info(f"Index '{index_name}' deleted.")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            return 1

    # Create index
    logger.info(f"Creating index '{index_name}'...")
    search_client.create_index(embedding_dimensions=1536)
    await asyncio.sleep(2)

    if not search_client.index_exists():
        logger.error("Failed to create index.")
        return 1

    logger.info(f"Index '{index_name}' created successfully!")

    # Load local products
    logger.info("Loading products from data/products.json...")
    try:
        local_products = load_local_products()
        logger.info(f"Loaded {len(local_products)} products from local file")
    except Exception as e:
        logger.error(f"Failed to load local products: {e}")
        return 1

    if not local_products:
        logger.warning("No products found in data/products.json. Index is empty.")
        return 0

    # Generate embeddings
    logger.info("Generating embeddings (this may take a few minutes)...")
    embeddings_client = EmbeddingsClient(settings)
    texts = [f"{p.name} {p.category} {p.description}" for p in local_products]
    embeddings = await embeddings_client.generate_embeddings_batch(texts)
    logger.info(f"Generated {len(embeddings)} embeddings")

    # Upload products
    logger.info(f"Uploading {len(local_products)} products to index...")
    upsert_result = await search_client.upsert_products(local_products, embeddings)
    logger.info(f"Uploaded {upsert_result['succeeded']} / {upsert_result['total']} products")

    if upsert_result["errors"]:
        logger.warning(f"Upload errors: {len(upsert_result['errors'])}")
        for error in upsert_result["errors"][:5]:
            logger.warning(f"  - {error}")

    # Wait for indexing
    await asyncio.sleep(3)

    # Health check
    logger.info("\nPerforming health check...")
    health = search_client.check_index_health()
    logger.info(f"Index health: {health['overall_status']}")
    logger.info(f"Document count: {health.get('stats', {}).get('document_count', 0)}")

    logger.info("\nFull reindex complete!")
    return 0


async def main():
    """Main entry point for Azure Search setup and management."""
    args = parse_args()

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

        # Route to appropriate operation
        if args.sync:
            return await sync_operation(search_client, settings, args)
        elif args.full_reindex:
            return await full_reindex_operation(search_client, settings, args)
        else:
            return await initial_setup_operation(search_client, settings, args)

    except KeyboardInterrupt:
        logger.info("\nOperation interrupted by user.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
