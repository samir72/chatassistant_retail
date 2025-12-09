# chatassistant_retail

![PyPI version](https://img.shields.io/pypi/v/chatassistant_retail.svg)
[![Documentation Status](https://readthedocs.org/projects/chatassistant_retail/badge/?version=latest)](https://chatassistant_retail.readthedocs.io/en/latest/?version=latest)

**chatassistant_retail** is a production-ready conversational AI chatbot designed specifically for the retail industry, providing intelligent assistance for retail inventory management. It features a multi-modal interface (text + images) powered by Azure OpenAI GPT-4o-mini, hybrid RAG search with Azure Cognitive Search, stateful conversation management via LangGraph, and flexible session persistence (Memory/Redis/PostgreSQL). The system includes a Gradio-based web UI, MCP tool integration, and comprehensive observability with LangFuse.

* PyPI package: https://pypi.org/project/chatassistant_retail/
* Free software: MIT License
* Documentation: https://chatassistant_retail.readthedocs.io
* Python Version: >= 3.10 (tested on 3.10, 3.11, 3.12, and 3.13)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Scripts Reference](#scripts-reference)
- [Session Management](#session-management)
- [Multi-Modal Processing](#multi-modal-processing)
- [Observability](#observability)
- [Deployment Options](#deployment-options)
- [Testing](#testing)
- [Contributing](#contributing)
- [Credits](#credits)

---

## Features

### Core Capabilities

- **Conversational Interface**: Gradio-based web UI for natural language interactions with retail inventory systems
- **Retail Inventory Management**: Specialized chatbot for handling inventory queries, stock levels, and purchase orders
- **Natural Language Understanding**: Powered by Azure OpenAI (GPT-4o-mini) for understanding and responding to retail-related questions
- **Agentic Workflow**: LangGraph-based state machine for complex multi-step conversations
- **Tool Integration**: MCP (Model Context Protocol) server for inventory and purchase order tools

### Technical Features

- **Multi-Modal Input Processing**: Handle both text and images (PNG, JPG, JPEG, WebP) for product analysis and visual queries
- **LangGraph Orchestration**: Stateful conversation management with persistent session storage
- **Hybrid RAG Search**: Vector + keyword + semantic search via Azure Cognitive Search with automatic fallback to local data
- **Flexible Session Persistence**: Three backend options - Memory (fast, ephemeral), Redis (distributed), or PostgreSQL (full persistence)
- **Semantic Search**: AI-powered relevance ranking with Free tier support (1,000 queries/month)
- **Observability**: Built-in LangFuse integration for tracing, monitoring, and analytics
- **Async Processing**: Asynchronous operations for high-performance request handling
- **Graceful Fallbacks**: Automatic degradation when Azure services unavailable (local data, keyword search)

### Retail-Specific Features

- **Inventory Queries**: Check stock levels, product availability, and warehouse information
- **Purchase Order Management**: Create, track, and manage purchase orders
- **Sample Data Generation**: Generate realistic product catalogs and sales history using Faker (500+ products, 6 months sales)
- **Product Search**: Semantic search across product catalog using Azure Cognitive Search with visual product matching

### Deployment & Development

- **Deployment Flexibility**: Local development, HuggingFace Spaces, or production deployment (Azure App Service, Docker, K8s)
- **Development Tools**: Comprehensive test suite, data generation scripts, Azure Search setup automation
- **Multi-Environment Configuration**: Environment-based settings with validation and graceful fallbacks

---

## Architecture

The chatbot follows an agentic architecture pattern using LangGraph for state management and orchestration:

```
┌─────────────────────────────────────────────────────────┐
│                  Gradio Web Interface                    │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Chat UI    │  │  Metrics     │  │  Session      │  │
│  │             │  │  Dashboard   │  │  Management   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              LangGraph State Manager                     │
│  ┌──────────────────┐  ┌──────────────────────────┐    │
│  │  State Graph     │  │  Session Store           │    │
│  │  (Workflow)      │  │  (Memory/PostgreSQL)     │    │
│  └──────────────────┘  └──────────────────────────┘    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Business Logic Layer                        │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │  Azure       │  │  Inventory  │  │  Purchase    │   │
│  │  OpenAI      │  │  Tools      │  │  Order Tools │   │
│  └──────────────┘  └─────────────┘  └──────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│              Data/Integration Layer                      │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │  PostgreSQL  │  │  Azure      │  │  Redis       │   │
│  │  (Sessions)  │  │  Search     │  │  (Cache)     │   │
│  └──────────────┘  └─────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                  Observability Layer                     │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐   │
│  │  LangFuse    │  │  Metrics    │  │  Python      │   │
│  │  Tracing     │  │  Collector  │  │  Logging     │   │
│  └──────────────┘  └─────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Components

- **Gradio UI** (`ui/`): Web-based chat interface with multi-modal input (text + images) and metrics dashboard
- **LangGraph State Manager** (`state/`): Conversation state management with Memory/Redis/PostgreSQL session stores
- **Azure OpenAI Client** (`llm/`): Multi-modal LLM integration (GPT-4o-mini) with prompt templates and response parsing
- **Tools** (`tools/`): Inventory and purchase order tools exposed via MCP (Model Context Protocol) server
- **RAG System** (`rag/`): Hybrid search with Azure Cognitive Search (vector + keyword + semantic) and local fallback
- **Observability** (`observability/`): LangFuse tracing and metrics collection across all components
- **Data Models** (`data/`): Pydantic models for products, sales, and purchase orders with sample data generation

### Design Principles

- **Separation of Concerns**: Clear separation between UI, orchestration, business logic, and data layers
- **Stateful Conversations**: LangGraph manages conversation state with checkpointing
- **Tool-Based Architecture**: LLM invokes tools (inventory queries, purchase orders) through structured outputs
- **Observable by Default**: All LLM calls and tool invocations traced with LangFuse
- **Error Resilience**: Graceful degradation and comprehensive error handling

---

## Project Structure

This project uses the **src-layout** pattern for better development and testing practices:

```
chatassistant_retail/
├── app.py                        # HuggingFace Spaces entry point
│
├── src/
│   └── chatassistant_retail/
│       ├── __init__.py           # Package initialization
│       ├── __main__.py           # Application entry point
│       ├── cli.py                # CLI entry point
│       ├── chatbot.py            # Main chatbot orchestrator (multi-modal)
│       │
│       ├── ui/                   # Gradio web interface
│       │   ├── __init__.py
│       │   ├── gradio_app.py     # Main Gradio application
│       │   ├── chat_interface.py # Chat UI components
│       │   └── metrics_dashboard.py  # Observability dashboard
│       │
│       ├── state/                # LangGraph state management
│       │   ├── __init__.py
│       │   ├── langgraph_manager.py  # State graph orchestration
│       │   ├── session_store.py      # Abstract session interface
│       │   ├── memory_store.py       # In-memory store (HF Spaces)
│       │   ├── redis_store.py        # Redis store (distributed)
│       │   └── postgresql_store.py   # PostgreSQL store (persistent)
│       │
│       ├── llm/                  # LLM integration
│       │   ├── __init__.py
│       │   ├── azure_openai_client.py  # Azure OpenAI client (GPT-4o-mini)
│       │   ├── prompt_templates.py     # System/user prompts
│       │   └── response_parser.py      # Response parsing
│       │
│       ├── tools/                # Inventory & PO tools
│       │   ├── __init__.py
│       │   ├── inventory_tools.py      # Inventory operations
│       │   ├── purchase_order_tools.py # PO operations
│       │   └── mcp_server.py           # MCP server setup
│       │
│       ├── rag/                  # Azure Cognitive Search RAG
│       │   ├── __init__.py
│       │   ├── azure_search_client.py  # Hybrid search client (vector+keyword+semantic)
│       │   ├── retriever.py            # Document retrieval with fallback
│       │   └── embeddings.py           # Embedding generation
│       │
│       ├── data/                 # Data models and generation
│       │   ├── __init__.py
│       │   ├── models.py         # Product, Sale, PurchaseOrder models
│       │   └── generator.py      # Sample data generator (Faker)
│       │
│       ├── observability/        # LangFuse observability
│       │   ├── __init__.py
│       │   ├── langfuse_client.py      # LangFuse wrapper
│       │   ├── decorators.py           # @trace decorator
│       │   └── metrics_collector.py    # Metrics aggregation
│       │
│       └── config/               # Configuration
│           ├── __init__.py
│           ├── settings.py       # Pydantic settings (env-based)
│           └── deployment.py     # Deployment configs
│
├── data/                         # Sample data files
│   ├── products.json             # 500+ sample products (216KB)
│   ├── sales_history.json        # 6 months sales data (3.5MB)
│   └── purchase_orders.json      # Sample purchase orders
│
├── scripts/                      # Utility scripts
│   ├── setup_azure_search.py     # Azure Search index setup
│   ├── generate_sample_data.py   # Generate sample product/sales data
│   ├── test_gradio_ui.py         # UI testing script
│   ├── test_phase2.py            # Integration testing
│   └── test_phase3.py            # E2E scenario testing
│
├── tests/
│   ├── __init__.py
│   ├── unit/                     # Unit tests
│   │   ├── test_observability.py
│   │   ├── test_inventory_tools.py
│   │   ├── test_session_store.py
│   │   ├── test_retriever.py
│   │   ├── test_azure_search_client.py
│   │   ├── test_azure_openai_client.py
│   │   └── test_data_generator.py
│   ├── integration/              # Integration tests
│   │   └── test_state_manager.py
│   └── test_chatassistant_retail.py  # Main tests
│
├── docs/                         # Sphinx documentation
│   ├── conf.py
│   ├── index.rst
│   └── usage.rst
│
├── .github/
│   └── workflows/
│       └── test.yml              # CI/CD pipeline
│
├── pyproject.toml                # Project metadata and dependencies
├── justfile                      # Task automation
├── CLAUDE.md                     # Claude Code guidance
├── README.md                     # This file
├── HISTORY.md                    # Changelog
└── LICENSE                       # MIT License
```

### Key Directories

- **app.py**: HuggingFace Spaces entry point (sets deployment mode and launches Gradio on 0.0.0.0:7860)
- **ui/**: Gradio-based web interface with multi-modal chat and metrics dashboard
- **state/**: LangGraph state machine with three session backends (Memory/Redis/PostgreSQL)
- **llm/**: Azure OpenAI integration (GPT-4o-mini) with prompt engineering and multi-modal support
- **tools/**: Inventory and purchase order tools with MCP server integration
- **rag/**: Hybrid search with Azure Cognitive Search (vector+keyword+semantic) and local fallback
- **data/**: Pydantic data models and Faker-based sample data generation
- **observability/**: LangFuse tracing, metrics collection, and monitoring
- **config/**: Pydantic settings with environment variable support and validation
- **scripts/**: Setup scripts (Azure Search index, data generation, testing)
- **data/ (root)**: Sample JSON files (products, sales history, purchase orders)
- **tests/**: Comprehensive PyTest suite (unit and integration tests)

---

## Installation

### Prerequisites

- Python >= 3.10
- [uv](https://github.com/astral-sh/uv) (Rust-based Python package manager) - **Required**
- [just](https://github.com/casey/just) (Command runner for task automation) - **Required for development**
- Azure OpenAI API access
- Azure Cognitive Search instance (optional, for RAG)
- PostgreSQL database (optional, for persistent sessions)
- Redis instance (optional, for caching)
- LangFuse account (optional, for observability)

#### Installing uv and just

Both `uv` and `just` need to be installed system-wide (not in a virtual environment):

**macOS:**
```bash
# Install with Homebrew (recommended)
brew install uv just

# Or install uv via curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# And install just separately
brew install just
```

**Linux:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install just
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash
```

**Windows:**
```powershell
# Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install just with cargo
cargo install just
```

After installation, verify both are available:
```bash
uv --version  # Should show: uv 0.9.x or later
just --version  # Should show: just 1.x.x or later
```

### Install from PyPI (when published)

```bash
pip install chatassistant_retail
```

### Development Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/samir72/chatassistant_retail.git
   cd chatassistant_retail
   ```

2. Install dependencies with uv:
   ```bash
   uv sync
   ```

3. Set up environment variables (create `.env` file):
   ```bash
   # Azure OpenAI (Required)
   AZURE_OPENAI_API_KEY=your-api-key
   AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini                      # GPT-4o-mini deployment
   AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002  # For RAG embeddings
   AZURE_OPENAI_API_VERSION=2024-02-15-preview

   # Azure Cognitive Search (Optional - fallback to local data if not configured)
   AZURE_COGNITIVE_SEARCH_ENDPOINT=https://your-search.search.windows.net
   AZURE_COGNITIVE_SEARCH_API_KEY=your-search-key
   AZURE_SEARCH_INDEX_NAME=products
   # Note: Semantic search must be enabled in Azure Portal (Search Service → Semantic ranker → Free)

   # Session Persistence (Optional - defaults to Memory store)
   SESSION_STORE_TYPE=memory                    # Options: memory, redis, postgresql
   REDIS_URL=redis://localhost:6379/0           # If using redis
   POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/chatbot  # If using postgresql

   # Deployment Configuration (Optional)
   DEPLOYMENT_MODE=local                        # Options: local, hf_spaces
   LOG_LEVEL=INFO                               # DEBUG, INFO, WARNING, ERROR

   # LangFuse Observability (Optional - recommended for production)
   LANGFUSE_PUBLIC_KEY=pk-lf-...
   LANGFUSE_SECRET_KEY=sk-lf-...
   LANGFUSE_HOST=https://cloud.langfuse.com
   LANGFUSE_ENABLED=true
   ```

4. Verify installation:
   ```bash
   just test
   ```

---

## Sample Data

The repository includes **sample data files** for immediate testing and development:

| File | Size | Description |
|------|------|-------------|
| `data/products.json` | 220 KB | 500+ sample products across 8 retail categories (Electronics, Clothing, Groceries, etc.) |
| `data/sales_history.json` | 3.6 MB | 6 months of sales transaction history with seasonal patterns |
| `data/purchase_orders.json` | 1.3 KB | Sample purchase orders (pending/fulfilled statuses) |

**Total size:** ~3.7 MB

### Why Sample Data is Included

Previously, the `data/` directory was excluded from version control to keep the repository lean. As of version 0.1.1, sample data is **included by default** for:

- ✅ Faster setup for new developers
- ✅ Consistent test data across environments
- ✅ No need to run data generation scripts initially

### Regenerating Sample Data (Optional)

If you want to regenerate or customize sample data:

```bash
python scripts/generate_sample_data.py
```

This will create fresh sample data with configurable parameters.

---

## Usage

### Setting Up Azure Cognitive Search

If you're using Azure Cognitive Search for RAG (Retrieval-Augmented Generation), you need to create the search index before running the chatbot.

#### Prerequisites
- Azure Cognitive Search service created
- Environment variables configured:
  - `AZURE_COGNITIVE_SEARCH_ENDPOINT`
  - `AZURE_COGNITIVE_SEARCH_API_KEY`
  - `AZURE_SEARCH_INDEX_NAME` (optional, defaults to "products")

#### Create the Index

Run the setup script:

```bash
python scripts/setup_azure_search.py
```

This will:
1. Create the "products" index with the proper schema
2. Configure vector search (1536-dimensional embeddings)
3. Set up semantic search capabilities
4. Optionally load 500 sample products with embeddings

#### Verify Setup

Check index health:

```python
from chatassistant_retail.rag import AzureSearchClient
from chatassistant_retail.config import get_settings

client = AzureSearchClient(get_settings())
health = client.check_index_health()
print(f"Status: {health['overall_status']}")
print(f"Document count: {health['stats']['document_count']}")
```

**Note:** If the index doesn't exist, the chatbot will still work but will fall back to local product data without vector search capabilities.

---

### Running the Chatbot

#### Start Gradio Web Interface

```bash
# Using Python module
python -m chatassistant_retail

# Or using the CLI entry point
chatassistant-retail

# With custom port
chatassistant-retail --port 7860
```

The web interface will be available at `http://localhost:7860` with:
- **Chat Interface**: Main conversational UI
- **Metrics Dashboard**: LangFuse observability metrics

#### Command-Line Usage

```bash
# Interactive CLI mode
chatassistant-retail --cli

# Single query
chatassistant-retail --query "What is the stock level for SKU-12345?"
```

### Example Conversations

#### Inventory Query
```
User: What is the current stock level for SKU-12345?
Assistant: Let me check the inventory for SKU-12345...
[Tool: inventory_tools.check_stock_level(sku="SKU-12345")]
The current stock level for SKU-12345 is 150 units across 3 warehouses.
```

#### Purchase Order Management
```
User: Create a purchase order for 500 units of SKU-67890 from Supplier ABC
Assistant: I'll create a purchase order for you...
[Tool: purchase_order_tools.create_po(sku="SKU-67890", quantity=500, supplier="ABC")]
Purchase order PO-2025-001 created successfully for 500 units of SKU-67890.
Expected delivery: 2025-01-15
```

#### Product Search with RAG
```
User: Tell me about our winter jacket inventory
Assistant: Let me search our product catalog...
[RAG: Azure Cognitive Search retrieval with semantic search]
We have 5 winter jacket styles in stock with a total of 1,250 units.
Most popular: "Alpine Puffer Jacket" (SKU-WJ-001) with 450 units available.
```

#### Multi-Modal Query (Image + Text)
```
User: [Uploads product image] Is this the same as SKU-12345? What's the stock level?
Assistant: Analyzing the product image...
[Multi-Modal: GPT-4o-mini processing]
[Tool: inventory_tools.check_stock_level(sku="SKU-12345")]
Yes, this appears to be the same product as SKU-12345 (Blue Athletic Sneaker).
Current stock: 85 units available across 2 warehouses.
```

---

## Development

This project uses `just` for task automation. All development commands are defined in the `justfile`.

### Quick Start

```bash
# List all available commands
just list

# Run full QA pipeline (format, lint, type-check, test)
just qa

# Run tests
just test

# Run tests with debugger on failure
just pdb

# Generate coverage report
just coverage
```

### Development Workflow

1. **Make changes** to the codebase
2. **Run QA**: `just qa` (formats, lints, type-checks, and tests)
3. **Debug failures**: `just pdb` if tests fail
4. **Check coverage**: `just coverage` to ensure adequate test coverage
5. **Build package**: `just build` when ready to release

### Code Quality Tools

- **Ruff**: Fast Python linter and formatter (line length: 120)
- **isort**: Import sorting (integrated with Ruff)
- **ty**: Type checking with all rules enabled
- **pytest**: Testing framework with async support and coverage reporting

### Local Development Setup

```bash
# Activate virtual environment (if not using uv)
source .venv/bin/activate

# Install pre-commit hooks (optional)
pre-commit install

# Run development server with auto-reload
python -m chatassistant_retail --reload

# Run tests in watch mode
pytest-watch
```

### Data Generation

The project includes tools for generating realistic sample data for development and testing.

#### Generating Sample Data

Use the `generate_sample_data.py` script to create sample products and sales history:

```bash
# Generate default data (500 products, 6 months sales history)
python scripts/generate_sample_data.py

# Custom data generation
python scripts/generate_sample_data.py --count 1000 --months 12
```

#### What Gets Generated

**Products (`data/products.json`):**
- 500+ realistic retail products (configurable)
- Categories: Electronics, Clothing, Home & Garden, Sports, Books
- Realistic pricing, descriptions, and metadata
- Auto-generated embeddings for Azure Search (1536 dimensions)

**Sales History (`data/sales_history.json`):**
- 6 months of transactional data (configurable)
- Realistic sales patterns (seasonality, trends)
- Multiple warehouses and channels
- Customer demographics

**Purchase Orders (`data/purchase_orders.json`):**
- Sample PO data for testing
- Various suppliers and statuses
- Delivery tracking information

#### Integration with Azure Search

The generated data includes pre-computed embeddings for immediate upload to Azure Search:

```bash
# 1. Generate sample data with embeddings
python scripts/generate_sample_data.py

# 2. Upload to Azure Search
python scripts/setup_azure_search.py --load-data
```

#### Customization

The data generator uses [Faker](https://faker.readthedocs.io/) for realistic data generation. Customize by modifying `src/chatassistant_retail/data/generator.py`.

---

## Scripts Reference

The `scripts/` directory contains utility scripts for setup, testing, and data management.

### setup_azure_search.py

**Purpose:** Create and configure Azure Cognitive Search index with proper schema for RAG.

**Usage:**
```bash
# Create index (prompts to load sample data)
python scripts/setup_azure_search.py

# Create index and auto-load data
python scripts/setup_azure_search.py --load-data

# Recreate existing index
python scripts/setup_azure_search.py --recreate
```

**What It Does:**
- Creates "products" index with hybrid search configuration
- Configures vector search (HNSW algorithm, 1536 dimensions)
- Sets up semantic search capabilities
- Optionally loads 500 sample products with embeddings
- Uploads in batches of 100 for efficiency
- Performs health check and displays statistics

**Requirements:**
- `AZURE_COGNITIVE_SEARCH_ENDPOINT` environment variable
- `AZURE_COGNITIVE_SEARCH_API_KEY` environment variable
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` for embedding generation

### generate_sample_data.py

**Purpose:** Generate realistic retail data for development and testing.

**Usage:**
```bash
# Default: 500 products, 6 months sales
python scripts/generate_sample_data.py

# Custom counts
python scripts/generate_sample_data.py --count 1000 --months 12

# Dry run (don't save files)
python scripts/generate_sample_data.py --dry-run
```

**Output:**
- `data/products.json` - Product catalog with embeddings
- `data/sales_history.json` - Sales transactions
- `data/purchase_orders.json` - PO data

### test_gradio_ui.py

**Purpose:** Interactive testing of Gradio UI components.

**Usage:**
```bash
python scripts/test_gradio_ui.py
```

Launches the Gradio interface for manual testing and validation.

### test_phase2.py / test_phase3.py

**Purpose:** Integration and end-to-end testing scripts.

**Usage:**
```bash
# Integration testing
python scripts/test_phase2.py

# E2E scenario testing
python scripts/test_phase3.py
```

Tests the complete chatbot workflow including LangGraph state management, tool execution, and RAG retrieval.

---

## Session Management

The chatbot supports three different session storage backends for conversation state persistence, allowing you to choose the right balance between simplicity, performance, and durability.

### Session Store Backends

#### Memory Store (Default)

The in-memory session store is the default and simplest option, ideal for development and HuggingFace Spaces deployment.

**Characteristics:**
- ✅ **Fast**: No network latency, instant access
- ✅ **Simple**: No external dependencies required
- ✅ **Auto-configured**: Default for HF Spaces deployment
- ❌ **Ephemeral**: Sessions lost on restart
- ❌ **Single-instance**: Not shared across multiple app instances

**Configuration:**
```bash
SESSION_STORE_TYPE=memory  # or omit (default)
```

**Use When:**
- Developing locally
- Deploying to HuggingFace Spaces
- Session persistence not critical
- Running single instance

#### Redis Store

Redis provides distributed session storage with persistence, ideal for production deployments with multiple instances.

**Characteristics:**
- ✅ **Fast**: In-memory with disk persistence
- ✅ **Distributed**: Shared across multiple app instances
- ✅ **Persistent**: Survives app restarts (with RDB/AOF)
- ✅ **TTL Support**: Automatic session expiration
- ⚠️ **Requires Redis**: External service dependency

**Configuration:**
```bash
SESSION_STORE_TYPE=redis
REDIS_URL=redis://localhost:6379/0
# Or for production with auth:
REDIS_URL=redis://:password@redis-host:6379/0
```

**Use When:**
- Running multiple app instances (load balanced)
- Need distributed session sharing
- Want automatic session expiration
- Production deployment with high availability

#### PostgreSQL Store

PostgreSQL provides full persistence with queryable session history, ideal for audit requirements and analytics.

**Characteristics:**
- ✅ **Fully Persistent**: Durable storage with ACID guarantees
- ✅ **Queryable**: SQL access to session data and history
- ✅ **Audit Trail**: Complete conversation history
- ✅ **Backup/Recovery**: Standard database backup tools
- ⚠️ **Slower**: Disk I/O overhead vs in-memory stores
- ⚠️ **Requires PostgreSQL**: External database dependency

**Configuration:**
```bash
SESSION_STORE_TYPE=postgresql
POSTGRES_CONNECTION_STRING=postgresql://user:password@localhost:5432/chatbot
```

**Use When:**
- Need complete audit trail
- Compliance/regulatory requirements
- Want to query conversation history
- Long-term session retention needed
- Analytics on conversation patterns

### Configuration Examples

**Local Development (Memory):**
```bash
# .env
SESSION_STORE_TYPE=memory  # Fast, simple, ephemeral
```

**HuggingFace Spaces (Memory):**
```bash
# Automatically configured via app.py
DEPLOYMENT_MODE=hf_spaces
SESSION_STORE_TYPE=memory  # Default for HF Spaces
```

**Production (Redis):**
```bash
# .env
SESSION_STORE_TYPE=redis
REDIS_URL=redis://:your-password@redis.example.com:6379/0
```

**Enterprise (PostgreSQL):**
```bash
# .env
SESSION_STORE_TYPE=postgresql
POSTGRES_CONNECTION_STRING=postgresql://chatbot:password@db.example.com:5432/chatbot
```

### Choosing a Backend

| Criteria | Memory | Redis | PostgreSQL |
|----------|--------|-------|------------|
| **Speed** | ⭐⭐⭐ Fastest | ⭐⭐ Very Fast | ⭐ Fast |
| **Persistence** | ❌ None | ⭐⭐ Configurable | ⭐⭐⭐ Full |
| **Multi-Instance** | ❌ No | ✅ Yes | ✅ Yes |
| **Setup Complexity** | ⭐⭐⭐ None | ⭐⭐ Moderate | ⭐ Complex |
| **Cost** | Free | $ Low | $$ Moderate |
| **Best For** | Dev, HF Spaces | Production | Enterprise, Audit |

---

## Multi-Modal Processing

The chatbot supports multi-modal input, allowing users to send both text and images for visual product analysis, comparison, and identification.

### Overview

Powered by Azure OpenAI GPT-4o-mini, the chatbot can:
- Analyze product images to identify items
- Compare products visually against catalog images
- Extract product details from photos (color, style, features)
- Verify product authenticity and condition
- Assist with visual inventory checks

### Supported Formats

**Image Formats:**
- PNG (.png)
- JPEG (.jpg, .jpeg)
- WebP (.webp)

**Size Limits:**
- Maximum file size: 20MB (Azure OpenAI limit)
- Recommended resolution: 2048x2048 pixels or less
- Images automatically resized if too large

### Usage Examples

#### Text-Only Query
```python
# Via Gradio UI: Type in chat box
User: "What is the stock level for SKU-12345?"
```

#### Image + Text Query
```python
# Via Gradio UI: Click image upload button, select image, then type query
User: [Uploads product photo] "Is this product in our catalog? Check inventory?"
```

Assistant analyzes the image using GPT-4o-mini, compares it against the catalog, and provides inventory information.

#### Product Image Analysis
```python
User: [Uploads warehouse photo showing multiple items] "Identify all products in this image and check stock levels"
```

The chatbot can identify multiple products in a single image and provide bulk inventory information.

### Best Practices

**Image Quality:**
- Use clear, well-lit photos
- Ensure products are centered and in focus
- Avoid excessive image compression

**Query Construction:**
- Combine images with specific questions for best results
- Reference SKUs or product names when known
- Ask focused questions (inventory, identification, comparison)

**Supported Use Cases:**
- ✅ Product identification from photos
- ✅ Visual comparison against catalog
- ✅ Quality/authenticity verification
- ✅ Bulk identification from warehouse photos
- ❌ Image generation or editing (not supported)

---

## Observability

The chatbot includes comprehensive observability using **LangFuse** for distributed tracing and monitoring.

### LangFuse Integration

LangFuse is integrated throughout the application for automatic tracing of:
- **LLM Calls**: All Azure OpenAI requests with prompts, completions, and token usage
- **Tool Invocations**: Inventory queries and purchase order operations
- **State Transitions**: LangGraph state changes and workflow steps
- **RAG Operations**: Document retrieval and embedding generation

### Configuration

Set up LangFuse in your `.env` file:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com  # or self-hosted
LANGFUSE_ENABLED=true
```

### Using the @trace Decorator

Automatically trace any function:

```python
from chatassistant_retail.observability import trace

@trace(name="inventory_check", trace_type="tool")
async def check_inventory(sku: str):
    # Function automatically traced in LangFuse
    return await inventory_service.get_stock(sku)
```

### Manual Tracing (Advanced Usage)

**Note:** For most use cases, the `@trace` decorator is recommended. Use manual tracing only when you need fine-grained control over span lifecycle.

```python
from chatassistant_retail.observability import create_span, log_event

# Create a span (must call .end() when done)
span = create_span(
    name="complex_workflow",
    input_data={"query": "user input"},
    metadata={"user_id": "123"}
)

try:
    # Do work
    result = perform_operation()

    # Log events within the span
    log_event(
        name="operation_milestone",
        level="INFO",
        input_data={"checkpoint": "halfway"}
    )

    # Update span with output
    span.update(output={"result": result})
finally:
    # Always end the span
    span.end()
```

**Important:** Spans created with `create_span()` must be explicitly ended with `.end()` to avoid memory leaks. Use the `@trace` decorator for automatic lifecycle management.

### Metrics Dashboard

The Gradio UI includes a real-time metrics dashboard showing:

- **Total Queries**: Number of chat interactions
- **Average Response Time**: Mean latency across all requests
- **Tool Calls**: Count of inventory/PO tool invocations
- **Error Rate**: Percentage of failed requests
- **Success Rate**: Percentage of successful completions
- **Recent Activity**: Timeline of recent conversations

Access the dashboard at: `http://localhost:7860` (Metrics tab)

### Metrics Collection

The `MetricsCollector` class aggregates data from LangFuse traces:

```python
from chatassistant_retail.observability import MetricsCollector

collector = MetricsCollector()
metrics = collector.get_dashboard_data()

print(f"Total queries: {metrics['total_queries']}")
print(f"Avg response time: {metrics['avg_response_time']:.2f}s")
print(f"Success rate: {metrics['success_rate']:.1f}%")
```

### Logging

Structured logging with Python's `logging` module:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Processing user query", extra={
    "session_id": session_id,
    "query_length": len(query)
})
```

Log levels are configurable via environment variables:
```bash
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Monitoring in Production

LangFuse provides:
- **Request Tracing**: End-to-end visibility of each conversation
- **Performance Metrics**: Latency, throughput, and error rates
- **Cost Tracking**: Token usage and API costs per request
- **User Analytics**: Session duration, query patterns, tool usage
- **Error Analysis**: Exception tracking and debugging

Access your LangFuse dashboard at https://cloud.langfuse.com to view:
- Real-time trace explorer
- Analytics dashboards
- Cost reports
- User session replays

---

## Deployment Options

The chatbot supports multiple deployment scenarios, from local development to production hosting on cloud platforms.

### Local Development

**Quick Start:**
```bash
# Clone repository
git clone https://github.com/samir72/chatassistant_retail.git
cd chatassistant_retail

# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your Azure credentials

# Run locally
python -m chatassistant_retail
```

**Features:**
- Hot reload with `--reload` flag
- Full debugging capabilities
- All features enabled (Azure Search, Redis, PostgreSQL, LangFuse)
- Access at `http://localhost:7860`

**Session Storage:** Any (Memory, Redis, PostgreSQL)

### HuggingFace Spaces

Deploy directly to HuggingFace Spaces for free hosting with automatic HTTPS and sharing.

#### Prerequisites

1. HuggingFace account (https://huggingface.co)
2. Azure OpenAI API credentials
3. (Optional) Azure Cognitive Search for RAG

#### Configuration

The `app.py` file is pre-configured for HF Spaces deployment:

```python
# app.py sets deployment mode automatically
os.environ["DEPLOYMENT_MODE"] = "hf_spaces"
```

**Important: src-layout Workaround**

Due to HuggingFace Spaces' Docker build process, this project uses a **sys.path manipulation workaround** instead of standard package installation:

- `requirements.txt` installs only dependencies (no package self-installation via `.`)
- `app.py` adds `src/` directory to Python path at startup
- Imports work without formal package installation

This is intentional and necessary because HF Spaces' auto-generated Dockerfile mounts `requirements.txt` before copying `pyproject.toml`, preventing standard `pip install .` from working. For local development, continue using `pip install -e .` as normal.

**Environment Variables (HF Spaces Secrets):**
```bash
# Required
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini

# Recommended
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
AZURE_COGNITIVE_SEARCH_ENDPOINT=...
AZURE_COGNITIVE_SEARCH_API_KEY=...

# Optional
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

#### Deployment Steps

1. **Create Space:**
   - Go to https://huggingface.co/new-space
   - Select "Gradio" as SDK
   - Choose "Public" or "Private"

2. **Upload Files:**
   ```bash
   git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
   cd YOUR_SPACE_NAME
   cp -r chatassistant_retail/* .
   git add .
   git commit -m "Initial deployment"
   git push
   ```

3. **Set Secrets:**
   - Go to Space Settings → Repository secrets
   - Add all required environment variables
   - Space will automatically rebuild and deploy

4. **Access:**
   - Your app will be live at: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`

**Limitations:**
- Uses Memory session store (sessions lost on restart)
- No Redis or PostgreSQL (Spaces compute limitations)
- Limited to 16GB RAM, 8 CPU cores (Free tier)
- Automatic sleep after 48 hours of inactivity

**Best For:**
- Demos and prototypes
- Sharing with stakeholders
- Testing without infrastructure setup
- Free tier hosting

### Production Deployment

Deploy to cloud platforms for scalable, production-grade hosting.

#### Azure App Service

**Requirements:**
- Azure subscription
- Azure App Service (B1 or higher)
- Azure OpenAI, Azure Cognitive Search, Azure Database for PostgreSQL

**Steps:**
```bash
# 1. Install Azure CLI
az login

# 2. Create App Service
az webapp create \
  --resource-group retail-chatbot-rg \
  --plan retail-chatbot-plan \
  --name retail-chatbot-app \
  --runtime "PYTHON:3.12"

# 3. Configure environment variables
az webapp config appsettings set \
  --resource-group retail-chatbot-rg \
  --name retail-chatbot-app \
  --settings \
    DEPLOYMENT_MODE=production \
    SESSION_STORE_TYPE=postgresql \
    POSTGRES_CONNECTION_STRING="..." \
    AZURE_OPENAI_API_KEY="..."

# 4. Deploy
az webapp up \
  --resource-group retail-chatbot-rg \
  --name retail-chatbot-app
```

**Recommended Configuration:**
- **Compute:** App Service B2 or higher (3.5GB RAM)
- **Session Store:** Azure Database for PostgreSQL
- **Cache:** Azure Cache for Redis (optional)
- **Monitoring:** Azure Application Insights + LangFuse

#### Docker Deployment

**Dockerfile Example:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY . /app

# Install dependencies
RUN uv sync

# Expose port
EXPOSE 7860

# Run application
CMD ["python", "-m", "chatassistant_retail"]
```

**Build and Run:**
```bash
# Build image
docker build -t retail-chatbot .

# Run container
docker run -p 7860:7860 \
  -e AZURE_OPENAI_API_KEY="..." \
  -e DEPLOYMENT_MODE=production \
  retail-chatbot
```

#### Kubernetes Deployment

For high-availability, multi-replica deployments:

**Key Considerations:**
- Use PostgreSQL or Redis for session storage (not Memory)
- Configure horizontal pod autoscaling (HPA)
- Set up ingress with TLS/SSL
- Use Azure Key Vault for secrets management
- Configure health checks and liveness probes

**Session Store:** Redis or PostgreSQL (required for multi-replica)

### Architecture Recommendations

| Deployment | Compute | Session Store | Cost | Best For |
|------------|---------|---------------|------|----------|
| **Local** | Developer machine | Memory | Free | Development |
| **HF Spaces** | Free tier (16GB) | Memory | Free | Demos, prototypes |
| **Azure App Service** | B2+ (3.5GB+) | PostgreSQL | $$ | Small-medium production |
| **Docker** | Custom | Redis/PostgreSQL | $ | Flexible hosting |
| **Kubernetes** | Multi-node cluster | Redis/PostgreSQL | $$$ | Enterprise, high-availability |

### Scaling Considerations

**Vertical Scaling (Single Instance):**
- Increase CPU/RAM allocation
- Use Memory or Redis session store
- Suitable for up to 1000 concurrent users

**Horizontal Scaling (Multiple Instances):**
- Deploy multiple replicas behind load balancer
- **Required:** Redis or PostgreSQL session store
- Configure sticky sessions (optional, for performance)
- Use Azure Front Door or Application Gateway
- Suitable for 1000+ concurrent users

**Performance Optimization:**
- Enable LangFuse for monitoring bottlenecks
- Use Redis for caching frequent queries
- Optimize Azure Search index (partition keys, replicas)
- Consider Azure OpenAI provisioned throughput for high volume

---

## Testing

The project uses **PyTest** for comprehensive testing with both unit and integration tests.

### Test Structure

```
tests/
├── unit/                           # Unit tests (isolated components)
│   ├── test_observability.py      # LangFuse client and metrics
│   ├── test_inventory_tools.py    # Inventory tool functions
│   ├── test_session_store.py      # Session persistence
│   ├── test_retriever.py          # RAG retrieval logic
│   └── test_data_generator.py     # Synthetic data generation
├── integration/                    # Integration tests (multiple components)
│   └── test_state_manager.py      # LangGraph state machine
└── test_chatassistant_retail.py   # Main chatbot tests
```

### Running Tests

```bash
# Run all tests
just test

# Run with verbose output
just test -v

# Run specific test file
just test tests/unit/test_observability.py

# Run specific test function
just test tests/unit/test_observability.py::TestLangFuseClient::test_get_langfuse_client_disabled

# Run with keyword filter
just test -k "inventory"

# Test on all Python versions (3.10, 3.11, 3.12, 3.13)
just testall
```

### Running Tests with Debugger

Use `ipdb` debugger on test failures:

```bash
# Drop into debugger on first failure
just pdb

# Debug specific test
just pdb tests/unit/test_inventory_tools.py

# Limit to first 10 failures
pytest --pdb --maxfail=10
```

### Coverage Reporting

```bash
# Run tests with coverage
just coverage

# View coverage report in terminal
coverage report

# Generate HTML coverage report
coverage html
# Open htmlcov/index.html in browser
```

Target coverage: **>= 90%**

### Test Fixtures

PyTest fixtures are used for common test setup:

```python
import pytest

@pytest.fixture
def mock_langfuse_client():
    """Provide mocked LangFuse client."""
    from unittest.mock import MagicMock
    return MagicMock()

@pytest.fixture
async def inventory_tool():
    """Provide inventory tool instance."""
    from chatassistant_retail.tools import InventoryTools
    return InventoryTools()

def test_inventory_query(inventory_tool):
    result = inventory_tool.check_stock("SKU-123")
    assert result["stock_level"] > 0
```

### Async Testing

Tests for async functions use `pytest-asyncio`:

```python
import pytest

@pytest.mark.asyncio
async def test_async_llm_call():
    from chatassistant_retail.llm import AzureOpenAIClient

    client = AzureOpenAIClient()
    response = await client.chat("Test query")
    assert response is not None
```

### Mocking External Services

Use `pytest-mock` for mocking Azure services:

```python
def test_azure_search(mocker):
    # Mock Azure Cognitive Search
    mock_search = mocker.patch("azure.search.documents.SearchClient")
    mock_search.return_value.search.return_value = [
        {"sku": "SKU-123", "name": "Test Product"}
    ]

    # Test retriever
    from chatassistant_retail.rag import Retriever
    retriever = Retriever()
    results = retriever.search("test query")
    assert len(results) == 1
```

### CI/CD Testing

GitHub Actions runs tests automatically:

```yaml
# .github/workflows/test.yml
- Run tests on Python 3.12 and 3.13
- Check code formatting with Ruff
- Verify type hints with ty
- Generate coverage report
```

View test results in GitHub Actions: https://github.com/samir72/chatassistant_retail/actions

---

## Contributing

Contributions are welcome! Please follow these guidelines:

### Getting Started

1. **Fork** the repository on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/your-username/chatassistant_retail.git
   cd chatassistant_retail
   ```
3. **Install dependencies**:
   ```bash
   uv sync
   ```
4. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Process

1. **Make your changes** following the code standards below
2. **Add tests** for new functionality (maintain >= 90% coverage)
3. **Run QA checks**:
   ```bash
   just qa  # Format, lint, type-check, and test
   ```
4. **Update documentation** if needed (README, docstrings, CLAUDE.md)
5. **Commit your changes**:
   ```bash
   git commit -m "Add feature: description"
   ```
6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Submit a pull request** to the main repository

### Code Standards

- **Style Guide**: PEP 8 (enforced by Ruff)
- **Line Length**: 120 characters maximum
- **Type Hints**: Required for all function signatures
- **Docstrings**: Required for all public functions and classes (Google style)
- **Test Coverage**: >= 90% for all new code
- **Import Sorting**: Automatic with Ruff (isort rules)

#### Example Code Style

```python
from typing import Optional

from chatassistant_retail.observability import trace


@trace(name="example_function", trace_type="function")
async def example_function(param1: str, param2: int = 0) -> Optional[dict]:
    """
    Brief description of function.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
    """
    if param2 < 0:
        raise ValueError("param2 must be non-negative")

    return {"param1": param1, "param2": param2}
```

### Pull Request Guidelines

- **Title**: Clear, concise description (e.g., "Add purchase order export feature")
- **Description**: Explain what changed and why
- **Tests**: Include test results showing all tests pass
- **Coverage**: Show coverage hasn't decreased
- **Documentation**: Update README/docs if needed
- **Breaking Changes**: Clearly mark any breaking changes

### Reporting Bugs

Use GitHub Issues: https://github.com/samir72/chatassistant_retail/issues

Include:
- Python version
- Environment (OS, dependencies)
- Steps to reproduce
- Expected vs actual behavior
- Error messages/stack traces
- Minimal code example

---

## Credits

This package was created with [Cookiecutter](https://github.com/audreyfeldroy/cookiecutter) and the [audreyfeldroy/cookiecutter-pypackage](https://github.com/audreyfeldroy/cookiecutter-pypackage) project template.

### Technologies Used

- **LangGraph**: Agentic workflow orchestration
- **LangChain**: LLM framework and integrations
- **Azure OpenAI**: GPT-4o-mini language model
- **Azure Cognitive Search**: Vector search and RAG
- **LangFuse**: Observability and tracing
- **Gradio**: Web UI framework
- **FastMCP**: Model Context Protocol server
- **PyTest**: Testing framework
- **Ruff**: Python linter and formatter
- **uv**: Fast Python package manager

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Support

- **Documentation**: https://chatassistant_retail.readthedocs.io
- **Issues**: https://github.com/samir72/chatassistant_retail/issues
- **Discussions**: https://github.com/samir72/chatassistant_retail/discussions
