# History

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

## 0.1.0 (2025-12-05)

* First release on PyPI.
