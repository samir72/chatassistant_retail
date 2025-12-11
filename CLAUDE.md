# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**chatassistant_retail** is a Web API chatbot for the retail industry, designed to assist with retail inventory management.

**Important**: This project is in early development (v0.1.0). The current codebase contains template scaffolding from cookiecutter-pypackage with Typer (CLI framework) dependencies, but the final implementation will be a Web API (REST) chatbot, not a command-line application.

- **Python Version**: >= 3.10 (tested on 3.12 and 3.13)
- **Package Manager**: uv (Rust-based Python package manager)
- **Task Runner**: just (command runner using justfile)
- **Planned Interface**: Web API (REST) using FastAPI, Flask, or similar
- **Current Dependencies**: Typer (template artifact, will be replaced), Rich (for terminal output during development)

## Development Commands

All development tasks are managed via the `justfile`. Use `just list` to see all available commands.

### Primary Commands

**Quality Assurance & Testing:**
- `just qa` - Run full QA pipeline: format with ruff → lint with ruff → fix imports (isort) → type-check with ty → run tests
- `just test [ARGS]` - Run tests with pytest (pass optional arguments)
- `just testall` - Run tests on Python 3.10, 3.11, 3.12, and 3.13
- `just pdb [ARGS]` - Run tests with IPython debugger on failure (max 10 failures)
- `just coverage` - Generate coverage report and HTML output

**Building & Versioning:**
- `just build` - Build distribution package (removes old build/dist first)
- `just version` - Print current version from pyproject.toml
- `just tag` - Create and push git tag for current version

**Cleaning:**
- `just clean` - Remove all build, test, coverage, and Python artifacts
- `just clean-build` - Remove build artifacts only
- `just clean-pyc` - Remove Python bytecode files
- `just clean-test` - Remove test and coverage artifacts

### Running Single Tests

To run a specific test file or test function:
```sh
just test tests/test_chatassistant_retail.py
just test tests/test_chatassistant_retail.py::test_specific_function
```

### Using the Debugger

When a test fails, use `just pdb` to drop into an interactive debugger:
```sh
just pdb tests/test_chatassistant_retail.py
```

## Code Architecture

### Current State (Early Development)

The codebase is currently scaffolding from the cookiecutter-pypackage template. The existing files contain placeholder code:

**Current Files:**
- `src/chatassistant_retail/__main__.py` - Template entry point (will be refactored)
- `src/chatassistant_retail/cli.py` - Typer CLI scaffold (will be replaced with API endpoints)
- `src/chatassistant_retail/utils.py` - Placeholder utility functions
- `src/chatassistant_retail/__init__.py` - Package initialization

### Planned Architecture (Web API Chatbot)

The chatbot will follow a Web API architecture pattern:

```
HTTP API Layer (FastAPI/Flask)
    ↓
Chat Request Handler
    ↓
Business Logic (Retail Inventory)
    ↓
Data/Response Layer
```

When implementing the chatbot, consider:
- RESTful API endpoints for chat interactions
- Request/response handling for chat messages
- Integration with retail inventory systems
- Appropriate authentication/authorization for API access

### Current Architecture - Context-Aware System

The chatbot now implements a context-aware architecture that reduces redundant data loading and improves performance:

#### Context Caching System

**Location:** `src/chatassistant_retail/tools/context_utils.py`

The context caching system allows tools to reuse data that has already been retrieved during the conversation, rather than reloading it from JSON files every time.

**Key Functions:**
- `get_products_from_context()` - Retrieves cached product data with smart filtering
- `get_sales_from_context()` - Retrieves cached sales history data
- `update_products_cache()` - Updates product cache with metadata
- `update_sales_cache()` - Updates sales cache with metadata

**How It Works:**

```python
# Example: Tool checks context before loading fresh data
from chatassistant_retail.tools.context_utils import get_products_from_context

def query_inventory(sku: str, state: ConversationState | None = None):
    # Try context cache first
    cached = get_products_from_context(state, sku=sku)
    if cached:
        return cached  # Reuse data already in conversation

    # Fallback: load from JSON
    products = load_products_from_file()

    # Cache for future use
    if state:
        update_products_cache(state, products, source="tool")

    return products
```

**Data Flow:**

```
User Query → RAG Retrieves Products → Cached in state.context
                                              ↓
User Follow-up → Tool Checks Cache → Reuses Cached Data ✓
                       ↓ (if not found)
                 Load from JSON → Cache → Return
```

**Benefits:**
- **Performance:** Reduces redundant JSON file I/O operations
- **Context Coherence:** Ensures tools work with same data user is discussing
- **Token Efficiency:** Reduces LLM context size by reusing retrieved data
- **Backward Compatible:** Tools work with or without state parameter

#### Image-Based Product Workflow

**Location:** `src/chatassistant_retail/workflow/image_processor.py`

The `ImageProductProcessor` class orchestrates a complete workflow for visual product queries:

**Workflow Steps:**

1. **Vision Extraction** - Identify product from image using GPT-4o Vision
   - Extracts: product_name, category, description, color, keywords
   - Returns confidence score (0.0 to 1.0)
   - Minimum confidence threshold: 0.3

2. **Catalog Search** - Search product database using RAG
   - Uses extracted keywords for hybrid search
   - Returns top 5 matching products
   - Filters by confidence threshold

3. **Inventory Check** - Query inventory status for matches
   - Checks stock levels for each matched product
   - Compares against reorder levels
   - Flags low-stock items

4. **Reorder Recommendations** - Calculate purchase orders for low stock
   - Determines order quantity based on sales velocity
   - Estimates days until stockout
   - Assigns urgency level (LOW/MEDIUM/HIGH)

**Architecture Diagram:**

```
Image Upload → Vision Extraction → Catalog Search → Inventory Check → Response
     ↓              ↓                    ↓                 ↓             ↓
 User Photo    Product Info        RAG Retriever      Tool Calls    Formatted
  (PNG/JPG)   (name, category)   (hybrid search)   (check_stock)   Response
               (confidence)         (top 5 SKUs)    (reorder calc)  (with recs)
```

**Example Use Case:**

User uploads photo of wireless mouse → AI identifies "Wireless Optical Mouse, Electronics" → Searches catalog → Finds 2 matches → Checks inventory → SKU-10001: 50 units (OK), SKU-10002: 8 units (LOW) → Recommends ordering 50 units of SKU-10002

#### Context-Aware Tools

All tools in `src/chatassistant_retail/tools/` now support an optional `state: ConversationState | None = None` parameter:

**Modified Files:**
- `inventory_tools.py` - Query inventory, calculate reorder points
- `purchase_order_tools.py` - Create and manage purchase orders
- `mcp_server.py` - ToolExecutor passes state to tool functions

**Backward Compatibility:** Tools function normally without the state parameter, falling back to loading fresh data from files.

**Integration Point:** The LangGraph state manager's tool node passes conversation state to ToolExecutor, which forwards it to tool implementations.

## Tools Configuration

### Ruff (Linting & Formatting)

Configuration in `pyproject.toml`:
- Line length: 120 characters
- Enabled rules:
  - `E` - pycodestyle errors
  - `W` - pycodestyle warnings
  - `F` - Pyflakes
  - `I` - isort (import sorting)
  - `B` - flake8-bugbear
  - `UP` - pyupgrade (Python syntax modernization)

### ty (Type Checking)

All rules are enabled as "error" by default. Override specific rules in `pyproject.toml` if needed:
```toml
[tool.ty]
# rules.TY015 = "warn"  # Example: relax invalid-argument-type to warning
```

### pytest (Testing)

Run with coverage using: `just coverage`

Test files are located in `tests/` directory following the pattern `test_*.py`.

## Multi-Version Python Testing

This project supports Python 3.10, 3.11, 3.12, and 3.13. The `justfile` uses `uv run --python=X.Y` to test across versions:

- Local development defaults to Python 3.13
- `just testall` runs tests on all four supported versions
- GitHub Actions CI tests on Python 3.12 and 3.13

When adding new features, ensure compatibility across all supported Python versions.

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/test.yml`) runs on push to main/master and pull requests:

1. Install dependencies from `requirements_dev.txt`
2. Lint with ruff (syntax errors first, then full check)
3. Install package with pip
4. Run tests with pytest

**Matrix**: Python 3.12 and 3.13 on Ubuntu Latest

## Package Structure

This project uses the **src-layout** pattern:

```
chatassistant_retail/
├── src/chatassistant_retail/  # Source code (importable package)
├── tests/                     # Test files
├── docs/                      # Documentation
├── pyproject.toml            # Project metadata and dependencies
└── justfile                  # Task automation
```

Benefits: Prevents accidental imports from the source directory during testing, ensuring tests run against the installed package.

## Setting Up Azure Search Index

Before using Azure Search features, you must create the index using the setup script:

```bash
python scripts/setup_azure_search.py
```

This script:
- Checks if Azure Search is configured (requires `AZURE_COGNITIVE_SEARCH_ENDPOINT` and `AZURE_COGNITIVE_SEARCH_API_KEY` environment variables)
- Creates the 'products' index with proper schema (vector search + semantic search)
- Optionally loads sample product data (500 products)
- Generates embeddings using Azure OpenAI (text-embedding-ada-002, 1536 dimensions)
- Uploads products in batches of 100
- Performs health check and displays index statistics

**Important:** If Azure Search is not set up or the index doesn't exist, the application gracefully falls back to local JSON-based product search without vector capabilities. You'll see a warning message in the logs when the application starts if the index is missing.

## Enabling Semantic Search on Free Tier

Azure Search Free tier includes **1,000 semantic ranker requests per month**, but semantic search must be **manually enabled** in the Azure Portal before it can be used.

### Symptoms of Disabled Semantic Search

If you see this error in your logs:
```
(FeatureNotSupportedInService) Semantic search is not enabled for this service.
Parameter name: queryType
```

This means semantic search is configured in your index but not enabled at the service level.

### Solution: Enable Semantic Search in Azure Portal

Follow these steps to enable semantic search:

1. Navigate to your **Azure AI Search service** in the Azure Portal
2. In the left menu, click **"Semantic ranker"**
3. Change the setting from **"Disabled"** to **"Free"**
4. Click **"Save"**
5. Wait 1-2 minutes for the change to take effect

### Automatic Fallback Behavior

The application automatically detects when semantic search is unavailable and falls back to keyword + vector search without semantic ranking. When this happens, you'll see a warning in the logs:

```
Semantic search not available on this Azure Search service.
To enable: Azure Portal → Search Service → Semantic ranker → Set to 'Free'.
Falling back to keyword + vector search.
```

The application will continue to work normally, but without the enhanced relevance ranking that semantic search provides.

### Free Tier Quota

- **1,000 semantic ranker requests per month** included in Free tier
- Requests exceeding the monthly quota will automatically fall back to non-semantic search
- Quota counter resets at the beginning of each month
- The application caches the semantic search availability status to avoid repeated errors

### What is Semantic Search?

Semantic search uses AI-powered language understanding to improve search relevance:
- **Without semantic search**: Results ranked by keyword matching and vector similarity
- **With semantic search**: Results additionally ranked by semantic meaning and context
- **Best for**: Natural language queries, questions, and complex searches

Example: Searching for "red shoes for running" will return better results with semantic search because it understands the relationship between "running" and "athletic footwear" beyond just keyword matching.

## RAG Index Management

The `AzureSearchClient` class provides programmatic methods for checking the health and status of the Azure AI Search index used for RAG (Retrieval-Augmented Generation).

### Available Methods

```python
from chatassistant_retail.rag.azure_search_client import AzureSearchClient
from chatassistant_retail.config import get_settings

client = AzureSearchClient(get_settings())

# Check if index exists
exists = client.index_exists()
print(f"Index exists: {exists}")

# Get index statistics
stats = client.get_index_stats()
print(f"Documents: {stats.get('document_count')}")
print(f"Storage: {stats.get('storage_size_bytes')} bytes")

# Get detailed index schema
schema = client.get_index_schema()
if schema:
    print(f"Index name: {schema['name']}")
    print(f"Fields: {len(schema['fields'])}")
    print(f"Vector search: {schema['vector_search']}")
    print(f"Semantic search: {schema['semantic_search']}")

# Validate schema matches expected configuration
validation = client.validate_index_schema()
if not validation['valid']:
    print(f"Schema issues found:")
    for diff in validation['field_differences']:
        print(f"  - {diff}")
    for field in validation['missing_fields']:
        print(f"  - Missing field: {field}")

# Comprehensive health check
health = client.check_index_health()
print(f"Overall status: {health['overall_status']}")
print(f"Index enabled: {health['enabled']}")
print(f"Index exists: {health['exists']}")
print(f"Connectivity: {health.get('connectivity', False)}")

if health.get('query_test'):
    qt = health['query_test']
    print(f"Query test: {qt['success']} ({qt.get('response_time_ms', 0)}ms)")
```

### Health Check Response Format

The `check_index_health()` method returns a comprehensive health report:

**Healthy Index:**
```python
{
    "enabled": True,
    "exists": True,
    "index_name": "products",
    "stats": {
        "document_count": 500,
        "storage_size_bytes": 2457600
    },
    "schema_validation": {
        "valid": True,
        "field_differences": [],
        "vector_search_valid": True,
        "semantic_search_valid": True,
        "missing_fields": [],
        "extra_fields": []
    },
    "connectivity": True,
    "query_test": {
        "success": True,
        "response_time_ms": 234,
        "results_count": 1
    },
    "overall_status": "healthy"
}
```

**Status Values:**
- `"healthy"` - Index exists, schema is valid, connectivity confirmed
- `"degraded"` - Index exists and is accessible, but has schema issues
- `"unavailable"` - Index doesn't exist or Azure Search not configured

### Use Cases

**1. Pre-deployment Checks:**
```python
health = client.check_index_health()
if health['overall_status'] != 'healthy':
    raise RuntimeError(f"Index not ready: {health}")
```

**2. Monitoring & Alerting:**
```python
stats = client.get_index_stats()
if stats.get('document_count', 0) == 0:
    logger.warning("Index is empty - no products indexed")
```

**3. Schema Migration Validation:**
```python
validation = client.validate_index_schema(expected_embedding_dimensions=1536)
if not validation['valid']:
    logger.error(f"Schema mismatch: {validation['field_differences']}")
```

## HuggingFace Spaces Deployment

### sys.path Workaround for Src-Layout

The project uses a **sys.path manipulation workaround** in `app.py` for HuggingFace Spaces deployment:

```python
# Add src directory to Python path for HuggingFace Spaces deployment
src_path = Path(__file__).parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
```

**Why this is needed:**

1. HuggingFace Spaces uses an auto-generated Dockerfile for Gradio SDK apps
2. The Dockerfile mounts `requirements.txt` during the pip install step
3. At that point, `pyproject.toml` is not yet copied into the container
4. Standard package installation (`pip install .`) fails with "Directory '.' is not installable"

**Solution:**

- Remove `.` from `requirements.txt` (no package self-installation)
- Add `src/` directory to Python path at runtime in `app.py`
- Imports work without formal package installation

**Trade-offs:**

✅ Works with HF Spaces' Docker build process
✅ Doesn't break local development (path added conditionally)
⚠️ Less "proper" than formal package installation
⚠️ Package metadata not available at runtime

**For local development:**

Continue using the standard approach:

```bash
pip install -e .
```

The sys.path workaround is harmless when the package is already installed.

### Automatic Sync from GitHub

The project automatically syncs to HuggingFace Spaces via GitHub Actions:

**Workflow:** `.github/workflows/syn-to-hf.yml`
- Uses `JacobLinCool/huggingface-sync@v1` action
- Triggered on push to main branch or manual workflow_dispatch
- Requires `HF_TOKEN` secret configured in GitHub repository settings

## Sample Data Now Tracked

As of December 8, 2025, sample data files are **tracked in version control**:

| File | Size | Status |
|------|------|--------|
| `data/products.json` | 220 KB | Tracked |
| `data/sales_history.json` | 3.6 MB | Tracked |
| `data/purchase_orders.json` | 1.3 KB | Tracked |

**Previous behavior:** Data folder was excluded via `.gitignore` to keep repository lean.

**Current behavior:** Sample data included for convenient setup. Users can still regenerate data using:

```bash
python scripts/generate_sample_data.py
```

**Rationale:** New developers can clone and run immediately without data generation step.
