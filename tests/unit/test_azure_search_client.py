"""Unit tests for AzureSearchClient index health check methods."""

from unittest.mock import Mock, patch

import pytest
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from chatassistant_retail.config import Settings
from chatassistant_retail.rag.azure_search_client import AzureSearchClient


@pytest.fixture
def mock_settings():
    """Create mock settings with Azure Search configured."""
    settings = Mock(spec=Settings)
    settings.AZURE_COGNITIVE_SEARCH_ENDPOINT = "https://test.search.windows.net"
    settings.AZURE_COGNITIVE_SEARCH_API_KEY = "test-key"
    settings.azure_search_index_name = "products"
    settings.azure_openai_endpoint = "https://test.openai.azure.com"
    settings.azure_openai_api_key = "test-openai-key"
    settings.azure_openai_embedding_deployment = "text-embedding-ada-002"
    settings.azure_openai_api_version = "2024-02-15-preview"
    return settings


@pytest.fixture
def mock_settings_disabled():
    """Create mock settings with Azure Search disabled."""
    settings = Mock(spec=Settings)
    settings.AZURE_COGNITIVE_SEARCH_ENDPOINT = None
    settings.AZURE_COGNITIVE_SEARCH_API_KEY = None
    settings.azure_search_index_name = "products"
    return settings


@pytest.fixture
def mock_index():
    """Create a mock search index."""
    index = Mock()
    index.name = "products"

    # Mock fields
    fields = []
    for field_data in [
        {"name": "id", "type": "Edm.String", "key": True, "filterable": True},
        {"name": "sku", "type": "Edm.String", "searchable": True, "filterable": True},
        {"name": "name", "type": "Edm.String", "searchable": True},
        {
            "name": "category",
            "type": "Edm.String",
            "searchable": True,
            "filterable": True,
            "facetable": True,
        },
        {"name": "description", "type": "Edm.String", "searchable": True},
        {"name": "price", "type": "Edm.Double", "filterable": True, "sortable": True},
        {"name": "current_stock", "type": "Edm.Int32", "filterable": True, "sortable": True},
        {"name": "reorder_level", "type": "Edm.Int32", "filterable": True},
        {"name": "supplier", "type": "Edm.String", "searchable": True, "filterable": True},
        {
            "name": "content_vector",
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "vector_search_dimensions": 1536,
            "vector_search_profile_name": "vector-profile",
        },
    ]:
        field = Mock()
        field.name = field_data["name"]
        field.type = field_data["type"]
        field.key = field_data.get("key", False)
        field.searchable = field_data.get("searchable", False)
        field.filterable = field_data.get("filterable", False)
        field.sortable = field_data.get("sortable", False)
        field.facetable = field_data.get("facetable", False)
        field.vector_search_dimensions = field_data.get("vector_search_dimensions")
        field.vector_search_profile_name = field_data.get("vector_search_profile_name")
        fields.append(field)
    index.fields = fields

    # Mock vector search
    vector_search = Mock()
    algorithm = Mock()
    algorithm.name = "hnsw-algorithm"
    algorithm.kind = "hnsw"
    vector_search.algorithms = [algorithm]
    profile = Mock()
    profile.name = "vector-profile"
    profile.algorithm_configuration_name = "hnsw-algorithm"
    vector_search.profiles = [profile]
    index.vector_search = vector_search

    # Mock semantic search
    semantic_search = Mock()
    config = Mock()
    config.name = "semantic-config"
    prioritized_fields = Mock()
    title_field = Mock()
    title_field.field_name = "name"
    prioritized_fields.title_field = title_field
    keyword_field = Mock()
    keyword_field.field_name = "category"
    prioritized_fields.keywords_fields = [keyword_field]
    content_field1 = Mock()
    content_field1.field_name = "description"
    content_field2 = Mock()
    content_field2.field_name = "supplier"
    prioritized_fields.content_fields = [content_field1, content_field2]
    config.prioritized_fields = prioritized_fields
    semantic_search.configurations = [config]
    index.semantic_search = semantic_search

    return index


@pytest.fixture
def mock_index_stats():
    """Create mock index statistics."""
    stats = Mock()
    stats.document_count = 500
    stats.storage_size = 2457600
    return stats


class TestIndexExists:
    """Tests for index_exists() method."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_index_exists_true(self, mock_index_client_class, mock_settings, mock_index):
        """Test index_exists returns True when index exists."""
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.index_exists()

        assert result is True
        # get_index is called twice: once during __init__ and once in this test
        assert mock_index_client.get_index.call_count == 2
        mock_index_client.get_index.assert_called_with("products")

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_index_exists_false(self, mock_index_client_class, mock_settings):
        """Test index_exists returns False when index not found."""
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = ResourceNotFoundError("Index not found")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.index_exists()

        assert result is False

    def test_index_exists_disabled(self, mock_settings_disabled):
        """Test index_exists returns False when Azure Search not configured."""
        client = AzureSearchClient(mock_settings_disabled)
        result = client.index_exists()

        assert result is False

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_index_exists_error(self, mock_index_client_class, mock_settings):
        """Test index_exists returns False on unexpected error."""
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = Exception("Network error")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.index_exists()

        assert result is False


class TestGetIndexStats:
    """Tests for get_index_stats() method."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_get_index_stats_success(self, mock_index_client_class, mock_settings, mock_index_stats):
        """Test get_index_stats returns statistics successfully."""
        mock_index_client = Mock()
        mock_index_client.get_index_statistics.return_value = mock_index_stats
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.get_index_stats()

        assert result == {"document_count": 500, "storage_size_bytes": 2457600}
        mock_index_client.get_index_statistics.assert_called_once_with("products")

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_get_index_stats_not_found(self, mock_index_client_class, mock_settings):
        """Test get_index_stats returns empty dict when index not found."""
        mock_index_client = Mock()
        mock_index_client.get_index_statistics.side_effect = ResourceNotFoundError("Index not found")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.get_index_stats()

        assert result == {}

    def test_get_index_stats_disabled(self, mock_settings_disabled):
        """Test get_index_stats returns empty dict when Azure Search not configured."""
        client = AzureSearchClient(mock_settings_disabled)
        result = client.get_index_stats()

        assert result == {}

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_get_index_stats_error(self, mock_index_client_class, mock_settings):
        """Test get_index_stats returns empty dict on error."""
        mock_index_client = Mock()
        mock_index_client.get_index_statistics.side_effect = Exception("Network error")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.get_index_stats()

        assert result == {}


class TestGetIndexSchema:
    """Tests for get_index_schema() method."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_get_index_schema_success(self, mock_index_client_class, mock_settings, mock_index):
        """Test get_index_schema returns schema successfully."""
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.get_index_schema()

        assert result is not None
        assert result["name"] == "products"
        assert len(result["fields"]) == 10
        assert result["vector_search"] is not None
        assert result["semantic_search"] is not None

        # Verify content_vector field has vector properties
        content_vector_field = next(f for f in result["fields"] if f["name"] == "content_vector")
        assert content_vector_field["vector_search_dimensions"] == 1536
        assert content_vector_field["vector_search_profile_name"] == "vector-profile"

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_get_index_schema_not_found(self, mock_index_client_class, mock_settings):
        """Test get_index_schema returns None when index not found."""
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = ResourceNotFoundError("Index not found")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.get_index_schema()

        assert result is None

    def test_get_index_schema_disabled(self, mock_settings_disabled):
        """Test get_index_schema returns None when Azure Search not configured."""
        client = AzureSearchClient(mock_settings_disabled)
        result = client.get_index_schema()

        assert result is None

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_get_index_schema_error(self, mock_index_client_class, mock_settings):
        """Test get_index_schema returns None on error."""
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = Exception("Network error")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.get_index_schema()

        assert result is None


class TestValidateIndexSchema:
    """Tests for validate_index_schema() method."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_valid(self, mock_index_client_class, mock_settings, mock_index):
        """Test validate_index_schema returns valid for matching schema."""
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema()

        assert result["valid"] is True
        assert len(result["field_differences"]) == 0
        assert len(result["missing_fields"]) == 0
        assert result["vector_search_valid"] is True
        assert result["semantic_search_valid"] is True

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_wrong_dimensions(self, mock_index_client_class, mock_settings, mock_index):
        """Test validate_index_schema detects wrong vector dimensions."""
        # Modify mock index to have wrong dimensions
        for field in mock_index.fields:
            if field.name == "content_vector":
                field.vector_search_dimensions = 768  # Wrong dimension

        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema(expected_embedding_dimensions=1536)

        assert result["valid"] is False
        assert any("1536 dimensions, got 768" in diff for diff in result["field_differences"])

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_missing_field(self, mock_index_client_class, mock_settings, mock_index):
        """Test validate_index_schema detects missing fields."""
        # Remove a field from mock index
        mock_index.fields = [f for f in mock_index.fields if f.name != "supplier"]

        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema()

        assert result["valid"] is False
        assert "supplier" in result["missing_fields"]

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_wrong_type(self, mock_index_client_class, mock_settings, mock_index):
        """Test validate_index_schema detects wrong field type."""
        # Change field type
        for field in mock_index.fields:
            if field.name == "price":
                field.type = "Edm.String"  # Wrong type, should be Double

        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema()

        assert result["valid"] is False
        assert any("price" in diff and "Edm.Double" in diff for diff in result["field_differences"])

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_no_vector_search(self, mock_index_client_class, mock_settings, mock_index):
        """Test validate_index_schema detects missing vector search config."""
        mock_index.vector_search = None

        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema()

        assert result["valid"] is False
        assert result["vector_search_valid"] is False
        assert any("Vector search configuration missing" in diff for diff in result["field_differences"])

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_no_semantic_search(self, mock_index_client_class, mock_settings, mock_index):
        """Test validate_index_schema detects missing semantic search config."""
        mock_index.semantic_search = None

        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema()

        assert result["valid"] is False
        assert result["semantic_search_valid"] is False
        assert any("Semantic search configuration missing" in diff for diff in result["field_differences"])

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_validate_index_schema_not_found(self, mock_index_client_class, mock_settings):
        """Test validate_index_schema when index doesn't exist."""
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = ResourceNotFoundError("Index not found")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.validate_index_schema()

        assert result["valid"] is False
        assert result["error"] == "Index not found"


class TestCheckIndexHealth:
    """Tests for check_index_health() method."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_check_index_health_healthy(
        self, mock_index_client_class, mock_search_client_class, mock_settings, mock_index, mock_index_stats
    ):
        """Test check_index_health returns healthy status."""
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client.get_index_statistics.return_value = mock_index_stats
        mock_index_client_class.return_value = mock_index_client

        mock_search_client = Mock()
        mock_result = Mock()
        mock_search_client.search.return_value = [mock_result]
        mock_search_client_class.return_value = mock_search_client

        client = AzureSearchClient(mock_settings)
        result = client.check_index_health()

        assert result["enabled"] is True
        assert result["exists"] is True
        assert result["index_name"] == "products"
        assert result["stats"]["document_count"] == 500
        assert result["schema_validation"]["valid"] is True
        assert result["connectivity"] is True
        assert result["query_test"]["success"] is True
        assert result["query_test"]["results_count"] == 1
        assert result["overall_status"] == "healthy"

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_check_index_health_degraded(
        self, mock_index_client_class, mock_search_client_class, mock_settings, mock_index, mock_index_stats
    ):
        """Test check_index_health returns degraded status with schema issues."""
        # Modify index to have wrong dimensions
        for field in mock_index.fields:
            if field.name == "content_vector":
                field.vector_search_dimensions = 768

        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client.get_index_statistics.return_value = mock_index_stats
        mock_index_client_class.return_value = mock_index_client

        mock_search_client = Mock()
        mock_result = Mock()
        mock_search_client.search.return_value = [mock_result]
        mock_search_client_class.return_value = mock_search_client

        client = AzureSearchClient(mock_settings)
        result = client.check_index_health()

        assert result["enabled"] is True
        assert result["exists"] is True
        assert result["connectivity"] is True
        assert result["schema_validation"]["valid"] is False
        assert result["overall_status"] == "degraded"

    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_check_index_health_unavailable_not_found(self, mock_index_client_class, mock_settings):
        """Test check_index_health returns unavailable when index doesn't exist."""
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = ResourceNotFoundError("Index not found")
        mock_index_client_class.return_value = mock_index_client

        client = AzureSearchClient(mock_settings)
        result = client.check_index_health()

        assert result["enabled"] is True
        assert result["exists"] is False
        assert result["overall_status"] == "unavailable"

    def test_check_index_health_disabled(self, mock_settings_disabled):
        """Test check_index_health when Azure Search not configured."""
        client = AzureSearchClient(mock_settings_disabled)
        result = client.check_index_health()

        assert result["enabled"] is False
        assert result["exists"] is False
        assert result["overall_status"] == "unavailable"

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_check_index_health_query_fails(
        self, mock_index_client_class, mock_search_client_class, mock_settings, mock_index, mock_index_stats
    ):
        """Test check_index_health when query test fails."""
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client.get_index_statistics.return_value = mock_index_stats
        mock_index_client_class.return_value = mock_index_client

        mock_search_client = Mock()
        mock_search_client.search.side_effect = HttpResponseError("Connection failed")
        mock_search_client_class.return_value = mock_search_client

        client = AzureSearchClient(mock_settings)
        result = client.check_index_health()

        assert result["enabled"] is True
        assert result["exists"] is True
        assert result["connectivity"] is False
        assert result["query_test"]["success"] is False
        assert "error" in result["query_test"]
        assert result["overall_status"] == "unavailable"


class TestInitWarnings:
    """Tests for initialization warnings."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_init_warns_if_index_missing(self, mock_index_client_class, mock_search_client_class, mock_settings):
        """Test that __init__ warns if index doesn't exist."""
        # Mock index_exists to return False
        mock_index_client = Mock()
        mock_index_client.get_index.side_effect = ResourceNotFoundError("Index not found")
        mock_index_client_class.return_value = mock_index_client

        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client

        # Capture log messages
        with patch("chatassistant_retail.rag.azure_search_client.logger") as mock_logger:
            client = AzureSearchClient(mock_settings)

            # Verify warning was logged
            warning_calls = [call for call in mock_logger.warning.call_args_list if call[0]]
            assert len(warning_calls) > 0

            # Check warning message content
            warning_message = warning_calls[0][0][0]
            assert "does not exist" in warning_message
            assert "setup_azure_search.py" in warning_message
            assert mock_settings.azure_search_index_name in warning_message

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_init_no_warning_if_index_exists(
        self, mock_index_client_class, mock_search_client_class, mock_settings, mock_index
    ):
        """Test that __init__ doesn't warn if index exists."""
        # Mock index_exists to return True
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        mock_search_client = Mock()
        mock_search_client_class.return_value = mock_search_client

        # Capture log messages
        with patch("chatassistant_retail.rag.azure_search_client.logger") as mock_logger:
            client = AzureSearchClient(mock_settings)

            # Verify no warning about missing index
            warning_calls = [call for call in mock_logger.warning.call_args_list if call[0]]
            for call in warning_calls:
                assert "does not exist" not in call[0][0]


class TestSearchProductsErrorHandling:
    """Tests for search_products error handling."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_search_products_handles_missing_index(
        self, mock_index_client_class, mock_search_client_class, mock_settings, mock_index
    ):
        """Test that search_products handles ResourceNotFoundError specifically."""
        # Setup mocks
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = mock_index
        mock_index_client_class.return_value = mock_index_client

        mock_search_client = Mock()
        mock_search_client.search.side_effect = ResourceNotFoundError("Index not found")
        mock_search_client_class.return_value = mock_search_client

        # Suppress initialization warning for this test
        with patch("chatassistant_retail.rag.azure_search_client.logger"):
            client = AzureSearchClient(mock_settings)

        # Capture search error log
        with patch("chatassistant_retail.rag.azure_search_client.logger") as mock_logger:
            import asyncio

            result = asyncio.run(client.search_products(query="test"))

            # Verify empty result
            assert result == []

            # Verify specific error message
            error_calls = [call for call in mock_logger.error.call_args_list if call[0]]
            assert len(error_calls) > 0

            error_message = error_calls[0][0][0]
            assert "not found" in error_message.lower()
            assert "setup_azure_search.py" in error_message


class TestSemanticSearchFallback:
    """Test semantic search fallback when feature is not available."""

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_semantic_search_disabled_fallback(self, mock_index_client_class, mock_search_client_class, mock_settings):
        """Test that semantic search errors trigger automatic fallback."""
        # Mock index client
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = Mock()
        mock_index_client_class.return_value = mock_index_client

        # Mock search client with semantic search error on first call, success on retry
        mock_search_client = Mock()

        # Create semantic search error
        semantic_error = HttpResponseError(
            message="(FeatureNotSupportedInService) Semantic search is not enabled for this service"
        )

        # Mock successful results for fallback search
        mock_result = {
            "sku": "TEST-001",
            "name": "Test Product",
            "@search.score": 0.95,
        }

        # First call raises error, second call (fallback) succeeds
        mock_search_client.search.side_effect = [semantic_error, [mock_result]]
        mock_search_client_class.return_value = mock_search_client

        # Suppress initialization warning
        with patch("chatassistant_retail.rag.azure_search_client.logger"):
            client = AzureSearchClient(mock_settings)

        # Perform search
        import asyncio

        result = asyncio.run(client.search_products(query="test product"))

        # Verify we got results from fallback
        assert len(result) == 1
        assert result[0]["sku"] == "TEST-001"
        assert result[0]["name"] == "Test Product"

        # Verify semantic search flag is now disabled
        assert client._semantic_search_disabled is True

        # Verify search was called twice (initial + fallback)
        assert mock_search_client.search.call_count == 2

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_semantic_search_disabled_cached(self, mock_index_client_class, mock_search_client_class, mock_settings):
        """Test that _semantic_search_disabled prevents future semantic search attempts."""
        # Mock index client
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = Mock()
        mock_index_client_class.return_value = mock_index_client

        # Mock search client
        mock_search_client = Mock()
        mock_result = Mock()
        mock_result.get.return_value = 0.95
        mock_result.__iter__ = lambda self: iter([("sku", "TEST-001"), ("name", "Test Product")])
        mock_search_client.search.return_value = [mock_result]
        mock_search_client_class.return_value = mock_search_client

        # Suppress initialization warning
        with patch("chatassistant_retail.rag.azure_search_client.logger"):
            client = AzureSearchClient(mock_settings)

        # Manually disable semantic search
        client._semantic_search_disabled = True

        # Perform search
        import asyncio

        asyncio.run(client.search_products(query="test product", use_semantic=True))

        # Verify search was called only once (no retry needed)
        assert mock_search_client.search.call_count == 1

        # Verify semantic search parameters were NOT passed
        call_kwargs = mock_search_client.search.call_args[1]
        assert "query_type" not in call_kwargs
        assert "semantic_configuration_name" not in call_kwargs

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_semantic_search_error_logged(self, mock_index_client_class, mock_search_client_class, mock_settings):
        """Test that semantic search errors are logged with helpful message."""
        # Mock index client
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = Mock()
        mock_index_client_class.return_value = mock_index_client

        # Mock search client with semantic search error
        mock_search_client = Mock()
        semantic_error = HttpResponseError(
            message="(SemanticQueriesNotAvailable) Semantic search is not enabled for this service"
        )

        # Mock successful fallback
        mock_result = {
            "sku": "TEST-001",
            "@search.score": 0.95,
        }
        mock_search_client.search.side_effect = [semantic_error, [mock_result]]
        mock_search_client_class.return_value = mock_search_client

        # Suppress initialization warning
        with patch("chatassistant_retail.rag.azure_search_client.logger"):
            client = AzureSearchClient(mock_settings)

        # Capture warning log
        with patch("chatassistant_retail.rag.azure_search_client.logger") as mock_logger:
            import asyncio

            asyncio.run(client.search_products(query="test"))

            # Verify warning was logged
            warning_calls = [call for call in mock_logger.warning.call_args_list if call[0]]
            assert len(warning_calls) > 0

            warning_message = warning_calls[0][0][0]
            assert "Semantic search not available" in warning_message
            assert "Azure Portal" in warning_message
            assert "Semantic ranker" in warning_message
            assert "Free" in warning_message

    @patch("chatassistant_retail.rag.azure_search_client.SearchClient")
    @patch("chatassistant_retail.rag.azure_search_client.SearchIndexClient")
    def test_other_http_errors_are_reraised(self, mock_index_client_class, mock_search_client_class, mock_settings):
        """Test that non-semantic HTTP errors are re-raised, not caught by fallback."""
        # Mock index client
        mock_index_client = Mock()
        mock_index_client.get_index.return_value = Mock()
        mock_index_client_class.return_value = mock_index_client

        # Mock search client with different HTTP error
        mock_search_client = Mock()
        other_error = HttpResponseError(message="(Unauthorized) Invalid credentials")
        mock_search_client.search.side_effect = other_error
        mock_search_client_class.return_value = mock_search_client

        # Suppress initialization warning
        with patch("chatassistant_retail.rag.azure_search_client.logger"):
            client = AzureSearchClient(mock_settings)

        # Perform search - should raise the error
        import asyncio

        with pytest.raises(HttpResponseError) as exc_info:
            asyncio.run(client.search_products(query="test"))

        # Verify it's the original error
        assert "Unauthorized" in str(exc_info.value)
