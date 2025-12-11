# History

## 0.2.0 (2025-12-10) - Context Caching & Image Workflows

### Major Features

#### Context Caching System (NEW)
**Added intelligent context caching for improved performance**:
- New `context_utils.py` module for smart data reuse across conversation
- `get_products_from_context()` and `get_sales_from_context()` retrieve cached data
- `update_products_cache()` and `update_sales_cache()` manage cache with metadata
- Filter validation ensures cached data matches requested queries
- Reduces redundant JSON file I/O operations
- Improves response times for follow-up questions

**Modified all tools to support context awareness**:
- `inventory_tools.py` - Now checks context cache before loading files
- `purchase_order_tools.py` - Reuses cached product data when available
- `mcp_server.py` - ToolExecutor passes conversation state to tools
- Backward compatible: tools work with or without state parameter

**Enhanced state management**:
- `langgraph_manager.py` RAG node now populates `context["products_cache"]`
- Cache includes metadata: source, timestamp, filters applied
- Tool node passes state to ToolExecutor for context-aware execution

#### Image-Based Product Workflow (NEW)
**Added complete image processing workflow**:
- New `workflow/` module for orchestrating multi-step operations
- `ImageProductProcessor` class implements end-to-end image workflow:
  1. Vision extraction (GPT-4o Vision product identification)
  2. Catalog search (RAG-based hybrid search)
  3. Inventory checking (automated stock level queries)
  4. Reorder recommendations (low-stock alerts with calculations)
- Confidence thresholds (MIN_CONFIDENCE_THRESHOLD = 0.3)
- Limits results to top 5 matches (MAX_MATCHES_TO_SHOW = 5)
- Comprehensive error handling and logging

**Enhanced vision capabilities**:
- Added `identify_product_from_image()` method to `azure_openai_client.py`
- Specialized product identification with structured JSON output
- Extracts: product_name, category, description, color, keywords, confidence
- Validates required fields before returning results
- Handles JSON parsing from markdown code blocks

**Updated chatbot for image processing**:
- `chatbot.py` now uses `ImageProductProcessor` for image queries
- Automatic workflow execution: vision → search → inventory → response
- Formatted responses with inventory status and recommendations
- Tool call tracking for state management

### Test Coverage

**Added comprehensive test suites**:
- `tests/unit/test_context_utils.py` - 419 lines, context caching validation
- `tests/unit/test_image_processor.py` - 467 lines, image workflow tests
- `tests/integration/test_tool_context_integration.py` - 164 lines, end-to-end integration
- All tests passing across Python 3.10, 3.11, 3.12, 3.13

### Architecture Improvements

**Benefits of Context Caching:**
- ✅ **Performance:** Reduced file I/O operations (3-5x faster for follow-up queries)
- ✅ **Consistency:** Tools work with same data user is discussing
- ✅ **Efficiency:** Reuses RAG-retrieved products without redundant retrieval
- ✅ **Backward Compatible:** Optional state parameter doesn't break existing code

**Benefits of Image Workflow:**
- ✅ **Multi-Modal Support:** Users can upload product images for identification
- ✅ **Automated Processing:** Complete workflow from image to purchase order
- ✅ **Smart Matching:** Hybrid search combines vision extraction with RAG retrieval
- ✅ **Proactive Alerts:** Automatic low-stock detection and reorder suggestions

### Data Flow Architecture

**Before (0.1.x):**
```
User Query → LLM → Tool Call → Load JSON → Process → Response
User Follow-up → LLM → Tool Call → Load JSON → Process → Response  [redundant load]
```

**After (0.2.0):**
```
User Query → RAG → Cache Products → Tool Call → Use Cache → Response
User Follow-up → Tool Call → Check Cache → Reuse Data → Response  [no reload ✓]
```

### Developer Notes

When adding new tools or modifying existing ones:
- Add optional `state: ConversationState | None = None` parameter
- Use `get_products_from_context()` / `get_sales_from_context()` before loading files
- Call `update_products_cache()` / `update_sales_cache()` after fresh loads
- Maintain backward compatibility (state parameter should be optional)

## 0.1.1 (2025-12-08) - HuggingFace Spaces Deployment & Data Inclusion

### HuggingFace Spaces Deployment Fixes

**Fixed Docker build error on HuggingFace Spaces** (commits 45ae942, bdd0940):
- Removed `.` package self-installation from requirements.txt that caused "Directory '.' is not installable" error
- Added sys.path manipulation in app.py to make src-layout imports work without formal package installation
- Added [build-system] section to pyproject.toml with hatchling backend
- Updated MANIFEST.in to explicitly include src/chatassistant_retail/

**Technical Details:**
HuggingFace Spaces' auto-generated Dockerfile mounts requirements.txt before copying the repository, preventing standard package installation. The workaround adds the src/ directory to Python's import path at runtime.

### Sample Data Files Now Included

**Added sample data files to repository** (commit 224a842):
- Updated .gitignore to track data/ directory (previously excluded)
- Added products.json (220 KB) - 500+ sample products across 8 categories
- Added sales_history.json (3.6 MB) - 6 months of transaction history
- Added purchase_orders.json (1.3 KB) - Sample purchase orders
- Total size: ~3.7 MB

**Rationale:** Provides convenient setup for new developers without requiring data generation script execution.

### GitHub Actions Workflow Updates

**Updated HuggingFace Spaces sync workflow** (commits 3e95887, 106d1ac, 7c6b46e):
- Migrated from manual git push to JacobLinCool/huggingface-sync@v1 action
- Added proper checkout step with actions/checkout@v4
- Improved configuration with explicit user/space parameters

### UI Module Reorganization

**Updated Gradio interface import** (commit 6600d9e):
- Changed from direct import to module-based import: `gradio_app.create_gradio_interface()`
- Improved module organization in chatassistant_retail.ui package

### Metrics Dashboard UI Disabled

**Temporarily disabled Gradio metrics dashboard UI** (commit TBD):
- Commented out metrics dashboard imports in gradio_app.py (lines 15-20)
- Disabled metrics UI components (lines 179-217)
- Removed metrics refresh event handlers (lines 238-242, 258-262)

**Backend Status:** The observability infrastructure remains fully functional:
- ✅ LangFuse tracing active
- ✅ MetricsCollector class operational
- ✅ @trace decorator working
- ✅ Programmatic metrics access available

**Rationale:** Streamlined UI to focus on core chat functionality. Metrics remain accessible via LangFuse web dashboard and programmatic API.

**Future Plans:** Dashboard may be re-enabled in a future release with enhanced features.

## 0.1.0 (2025-12-05)

* First release on PyPI.
