"""Azure AI Search client for product catalog and sales data."""

import logging
import time
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery

from chatassistant_retail.config import get_settings
from chatassistant_retail.data.models import Product

logger = logging.getLogger(__name__)


class AzureSearchClient:
    """Client for Azure AI Search with hybrid (vector + keyword) search."""

    def __init__(self, settings=None):
        """
        Initialize Azure Search client.

        Args:
            settings: Optional Settings instance. If None, uses get_settings().
        """
        self.settings = settings or get_settings()

        # Only initialize if Azure Search is configured
        if not self.settings.AZURE_COGNITIVE_SEARCH_ENDPOINT or not self.settings.AZURE_COGNITIVE_SEARCH_API_KEY:
            logger.warning("Azure Search not configured. RAG features will be limited.")
            self.enabled = False
            return

        self.enabled = True
        self.credential = AzureKeyCredential(self.settings.AZURE_COGNITIVE_SEARCH_API_KEY)

        # Initialize clients
        self.index_client = SearchIndexClient(
            endpoint=self.settings.AZURE_COGNITIVE_SEARCH_ENDPOINT,
            credential=self.credential,
        )

        self.search_client = SearchClient(
            endpoint=self.settings.AZURE_COGNITIVE_SEARCH_ENDPOINT,
            index_name=self.settings.azure_search_index_name,
            credential=self.credential,
        )

        logger.info(f"Initialized Azure Search client for index: {self.settings.azure_search_index_name}")

        # Track whether semantic search is available (will be set to True if semantic search errors occur)
        self._semantic_search_disabled = False

        # Check if index exists and warn if missing
        if not self.index_exists():
            logger.warning(
                f"Azure Search index '{self.settings.azure_search_index_name}' does not exist. "
                f"Run 'python scripts/setup_azure_search.py' to create it. "
                f"The application will fall back to local product data until the index is created."
            )

    def create_index(self, embedding_dimensions: int = 1536):
        """
        Create search index with vector and keyword search capabilities.

        Args:
            embedding_dimensions: Dimension of embedding vectors (default: 1536 for text-embedding-ada-002)
        """
        if not self.enabled:
            logger.warning("Azure Search not enabled. Cannot create index.")
            return

        fields = [
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True,
            ),
            SearchField(
                name="sku",
                type=SearchFieldDataType.String,
                filterable=True,
                searchable=True,
            ),
            SearchField(
                name="name",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=False,
            ),
            SearchField(
                name="category",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True,
                searchable=True,
            ),
            SearchField(
                name="description",
                type=SearchFieldDataType.String,
                searchable=True,
            ),
            SearchField(
                name="price",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True,
            ),
            SearchField(
                name="current_stock",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
            ),
            SearchField(
                name="reorder_level",
                type=SearchFieldDataType.Int32,
                filterable=True,
            ),
            SearchField(
                name="supplier",
                type=SearchFieldDataType.String,
                filterable=True,
                searchable=True,
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=embedding_dimensions,
                vector_search_profile_name="vector-profile",
            ),
        ]

        # Configure vector search
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="hnsw-algorithm"),
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-algorithm",
                ),
            ],
        )

        # Configure semantic search
        semantic_search = SemanticSearch(
            configurations=[
                SemanticConfiguration(
                    name="semantic-config",
                    prioritized_fields=SemanticPrioritizedFields(
                        title_field=SemanticField(field_name="name"),
                        keywords_fields=[SemanticField(field_name="category")],
                        content_fields=[
                            SemanticField(field_name="description"),
                            SemanticField(field_name="supplier"),
                        ],
                    ),
                )
            ]
        )

        # Create index
        index = SearchIndex(
            name=self.settings.azure_search_index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

        try:
            self.index_client.create_or_update_index(index)
            logger.info(f"Created/updated search index: {self.settings.azure_search_index_name}")
        except Exception as e:
            logger.error(f"Error creating search index: {e}")
            raise

    async def index_products(self, products: list[Product], embeddings: list[list[float]]):
        """
        Index products with their embeddings to Azure Search.

        Args:
            products: List of Product instances
            embeddings: List of embedding vectors (same length as products)
        """
        if not self.enabled:
            logger.warning("Azure Search not enabled. Cannot index products.")
            return

        if len(products) != len(embeddings):
            raise ValueError("Number of products must match number of embeddings")

        documents = []
        for product, embedding in zip(products, embeddings):
            doc = {
                "id": product.sku,
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "description": product.description,
                "price": product.price,
                "current_stock": product.current_stock,
                "reorder_level": product.reorder_level,
                "supplier": product.supplier,
                "content_vector": embedding,
            }
            documents.append(doc)

        try:
            # Upload in batches of 100
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch = documents[i : i + batch_size]
                result = self.search_client.upload_documents(documents=batch)
                logger.info(f"Indexed batch {i // batch_size + 1}: {len(batch)} products")

            logger.info(f"Successfully indexed {len(products)} products")

        except Exception as e:
            logger.error(f"Error indexing products: {e}")
            raise

    async def search_products(
        self,
        query: str | None = None,
        query_vector: list[float] | None = None,
        top_k: int = 5,
        filter_expression: str | None = None,
        use_semantic: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search products using hybrid (vector + keyword) search.

        Args:
            query: Text query for keyword search
            query_vector: Embedding vector for semantic search
            top_k: Number of results to return
            filter_expression: OData filter expression
            use_semantic: Whether to use semantic ranking

        Returns:
            List of product dictionaries with scores
        """
        if not self.enabled:
            logger.warning("Azure Search not enabled. Returning empty results.")
            return []

        try:
            search_kwargs = {
                "top": top_k,
                "select": [
                    "sku",
                    "name",
                    "category",
                    "description",
                    "price",
                    "current_stock",
                    "reorder_level",
                    "supplier",
                ],
            }

            if filter_expression:
                search_kwargs["filter"] = filter_expression

            if use_semantic and query and not self._semantic_search_disabled:
                search_kwargs["query_type"] = "semantic"
                search_kwargs["semantic_configuration_name"] = "semantic-config"

            if query_vector:
                search_kwargs["vector_queries"] = [
                    VectorizedQuery(
                        vector=query_vector,
                        k_nearest_neighbors=top_k,
                        fields="content_vector",
                    )
                ]

            results = self.search_client.search(
                search_text=query or "*",
                **search_kwargs,
            )

            products = []
            for result in results:
                product = dict(result)
                product["search_score"] = result.get("@search.score", 0)
                products.append(product)

            logger.info(f"Found {len(products)} products for query: {query}")
            return products

        except ResourceNotFoundError:
            logger.error(
                f"Index '{self.settings.azure_search_index_name}' not found. "
                f"Run 'python scripts/setup_azure_search.py' to create it."
            )
            return []

        except HttpResponseError as e:
            # Check if error is related to semantic search not being available
            if "SemanticQueriesNotAvailable" in str(e) or "FeatureNotSupportedInService" in str(e):
                logger.warning(
                    "Semantic search not available on this Azure Search service. "
                    "To enable: Azure Portal → Search Service → Semantic ranker → Set to 'Free'. "
                    "Falling back to keyword + vector search."
                )
                self._semantic_search_disabled = True

                # Retry without semantic search
                search_kwargs.pop("query_type", None)
                search_kwargs.pop("semantic_configuration_name", None)

                results = self.search_client.search(
                    search_text=query or "*",
                    **search_kwargs,
                )

                products = []
                for result in results:
                    product = dict(result)
                    product["search_score"] = result.get("@search.score", 0)
                    products.append(product)

                logger.info(f"Found {len(products)} products for query: {query} (without semantic search)")
                return products
            else:
                # Re-raise if it's a different HTTP error
                raise
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []

    async def get_low_stock_items(self, threshold: int = 10, top_k: int = 20) -> list[dict[str, Any]]:
        """
        Get products with low stock levels.

        Args:
            threshold: Stock level threshold
            top_k: Maximum number of results

        Returns:
            List of low stock products
        """
        filter_expr = f"current_stock le {threshold}"
        return await self.search_products(
            query="*",
            top_k=top_k,
            filter_expression=filter_expr,
            use_semantic=False,
        )

    async def get_products_by_category(self, category: str, top_k: int = 20) -> list[dict[str, Any]]:
        """
        Get products by category.

        Args:
            category: Product category
            top_k: Maximum number of results

        Returns:
            List of products in category
        """
        filter_expr = f"category eq '{category}'"
        return await self.search_products(
            query="*",
            top_k=top_k,
            filter_expression=filter_expr,
            use_semantic=False,
        )

    async def get_product_by_sku(self, sku: str) -> dict[str, Any] | None:
        """
        Get a specific product by SKU.

        Args:
            sku: Product SKU

        Returns:
            Product dictionary or None if not found
        """
        if not self.enabled:
            return None

        try:
            result = self.search_client.get_document(key=sku)
            return dict(result)
        except Exception as e:
            logger.warning(f"Product not found: {sku} - {e}")
            return None

    def index_exists(self) -> bool:
        """
        Check if the search index exists.

        Returns:
            True if index exists, False otherwise
        """
        if not self.enabled:
            return False

        try:
            self.index_client.get_index(self.settings.azure_search_index_name)
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking if index exists: {e}")
            return False

    def get_index_stats(self) -> dict[str, Any]:
        """
        Get index statistics including document count and storage size.

        Returns:
            Dictionary with index statistics, or empty dict if unavailable
        """
        if not self.enabled:
            return {}

        try:
            stats = self.index_client.get_index_statistics(self.settings.azure_search_index_name)
            return {
                "document_count": stats.document_count,
                "storage_size_bytes": stats.storage_size,
            }
        except ResourceNotFoundError:
            logger.warning(f"Index not found: {self.settings.azure_search_index_name}")
            return {}
        except Exception as e:
            logger.error(f"Error getting index statistics: {e}")
            return {}

    def get_index_schema(self) -> dict[str, Any] | None:
        """
        Retrieve the current index schema including fields and search configurations.

        Returns:
            Dictionary with schema details, or None if index doesn't exist
        """
        if not self.enabled:
            return None

        try:
            index = self.index_client.get_index(self.settings.azure_search_index_name)

            # Extract field information
            fields = []
            for field in index.fields:
                field_info = {
                    "name": field.name,
                    "type": str(field.type),
                    "key": field.key or False,
                    "searchable": field.searchable or False,
                    "filterable": field.filterable or False,
                    "sortable": field.sortable or False,
                    "facetable": field.facetable or False,
                }
                # Add vector-specific properties if applicable
                if field.vector_search_dimensions:
                    field_info["vector_search_dimensions"] = field.vector_search_dimensions
                    field_info["vector_search_profile_name"] = field.vector_search_profile_name
                fields.append(field_info)

            # Extract vector search configuration
            vector_search_config = None
            if index.vector_search:
                algorithms = [{"name": algo.name, "kind": algo.kind} for algo in (index.vector_search.algorithms or [])]
                profiles = [
                    {"name": profile.name, "algorithm": profile.algorithm_configuration_name}
                    for profile in (index.vector_search.profiles or [])
                ]
                vector_search_config = {"algorithms": algorithms, "profiles": profiles}

            # Extract semantic search configuration
            semantic_search_config = None
            if index.semantic_search:
                configurations = []
                for config in index.semantic_search.configurations or []:
                    config_info = {
                        "name": config.name,
                        "title_field": config.prioritized_fields.title_field.field_name
                        if config.prioritized_fields.title_field
                        else None,
                        "keywords_fields": [f.field_name for f in (config.prioritized_fields.keywords_fields or [])],
                        "content_fields": [f.field_name for f in (config.prioritized_fields.content_fields or [])],
                    }
                    configurations.append(config_info)
                semantic_search_config = {"configurations": configurations}

            return {
                "name": index.name,
                "fields": fields,
                "vector_search": vector_search_config,
                "semantic_search": semantic_search_config,
            }

        except ResourceNotFoundError:
            logger.warning(f"Index not found: {self.settings.azure_search_index_name}")
            return None
        except Exception as e:
            logger.error(f"Error getting index schema: {e}")
            return None

    def validate_index_schema(self, expected_embedding_dimensions: int = 1536) -> dict[str, Any]:
        """
        Validate that the actual index schema matches the expected schema.

        Args:
            expected_embedding_dimensions: Expected dimension of embedding vectors (default: 1536)

        Returns:
            Validation report with differences and overall status
        """
        # Get actual schema
        actual_schema = self.get_index_schema()
        if actual_schema is None:
            return {"valid": False, "error": "Index not found"}

        # Define expected fields based on create_index() logic
        expected_fields = {
            "id": {"type": "Edm.String", "key": True, "filterable": True},
            "sku": {"type": "Edm.String", "searchable": True, "filterable": True},
            "name": {"type": "Edm.String", "searchable": True},
            "category": {"type": "Edm.String", "searchable": True, "filterable": True, "facetable": True},
            "description": {"type": "Edm.String", "searchable": True},
            "price": {"type": "Edm.Double", "filterable": True, "sortable": True},
            "current_stock": {"type": "Edm.Int32", "filterable": True, "sortable": True},
            "reorder_level": {"type": "Edm.Int32", "filterable": True},
            "supplier": {"type": "Edm.String", "searchable": True, "filterable": True},
            "content_vector": {
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "vector_search_dimensions": expected_embedding_dimensions,
                "vector_search_profile_name": "vector-profile",
            },
        }

        # Compare fields
        field_differences = []
        missing_fields = []
        actual_fields_dict = {f["name"]: f for f in actual_schema["fields"]}

        for field_name, expected_props in expected_fields.items():
            if field_name not in actual_fields_dict:
                missing_fields.append(field_name)
                continue

            actual_field = actual_fields_dict[field_name]

            # Check type
            if actual_field["type"] != expected_props["type"]:
                field_differences.append(
                    f"Field '{field_name}': expected type {expected_props['type']}, got {actual_field['type']}"
                )

            # Check vector dimensions
            if "vector_search_dimensions" in expected_props:
                actual_dims = actual_field.get("vector_search_dimensions")
                expected_dims = expected_props["vector_search_dimensions"]
                if actual_dims != expected_dims:
                    field_differences.append(
                        f"Field '{field_name}': expected {expected_dims} dimensions, got {actual_dims}"
                    )

        # Check for extra fields (not critical, just informational)
        extra_fields = [f for f in actual_fields_dict.keys() if f not in expected_fields]

        # Validate vector search configuration
        vector_search_valid = False
        if actual_schema["vector_search"]:
            profiles = actual_schema["vector_search"]["profiles"]
            vector_search_valid = any(p["name"] == "vector-profile" for p in profiles)
            if not vector_search_valid:
                field_differences.append("Vector search profile 'vector-profile' not found")
        else:
            field_differences.append("Vector search configuration missing")

        # Validate semantic search configuration
        semantic_search_valid = False
        if actual_schema["semantic_search"]:
            configs = actual_schema["semantic_search"]["configurations"]
            semantic_search_valid = any(c["name"] == "semantic-config" for c in configs)
            if not semantic_search_valid:
                field_differences.append("Semantic search configuration 'semantic-config' not found")
        else:
            field_differences.append("Semantic search configuration missing")

        return {
            "valid": len(field_differences) == 0 and len(missing_fields) == 0,
            "field_differences": field_differences,
            "vector_search_valid": vector_search_valid,
            "semantic_search_valid": semantic_search_valid,
            "missing_fields": missing_fields,
            "extra_fields": extra_fields,
        }

    def check_index_health(self) -> dict[str, Any]:
        """
        Perform comprehensive health check on the search index.

        Returns:
            Health report including existence, stats, schema validation, and connectivity
        """
        health_report = {
            "enabled": self.enabled,
            "exists": False,
            "index_name": self.settings.azure_search_index_name if self.enabled else None,
            "overall_status": "unavailable",
        }

        if not self.enabled:
            return health_report

        # Check if index exists
        try:
            exists = self.index_exists()
            health_report["exists"] = exists

            if not exists:
                health_report["overall_status"] = "unavailable"
                return health_report

            # Get statistics
            stats = self.get_index_stats()
            health_report["stats"] = stats

            # Validate schema
            schema_validation = self.validate_index_schema()
            health_report["schema_validation"] = schema_validation

            # Test connectivity with sample query
            connectivity = True
            query_test = {}
            try:
                start_time = time.time()
                results = self.search_client.search(search_text="*", top=1)
                result_list = list(results)
                response_time = (time.time() - start_time) * 1000  # ms

                query_test = {
                    "success": True,
                    "response_time_ms": round(response_time, 2),
                    "results_count": len(result_list),
                }
            except Exception as e:
                connectivity = False
                query_test = {"success": False, "error": str(e)}
                logger.error(f"Query test failed: {e}")

            health_report["connectivity"] = connectivity
            health_report["query_test"] = query_test

            # Determine overall status
            if connectivity and schema_validation.get("valid", False):
                health_report["overall_status"] = "healthy"
            elif connectivity:
                health_report["overall_status"] = "degraded"  # works but has schema issues
            else:
                health_report["overall_status"] = "unavailable"

        except Exception as e:
            logger.error(f"Error during health check: {e}")
            health_report["error"] = str(e)
            health_report["overall_status"] = "unavailable"

        return health_report
