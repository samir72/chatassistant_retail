# Troubleshooting Guide

## HuggingFace Spaces Issues

### "Directory '.' is not installable" Error

**Error message:**
```
ERROR: Directory '.' is not installable. Neither 'setup.py' nor 'pyproject.toml' found.
```

**Cause:**
This error occurs when `requirements.txt` contains `.` (package self-installation) but `pyproject.toml` isn't available during Docker build.

**Solution:**
Ensure `requirements.txt` does NOT contain `.` entry. The current version uses sys.path manipulation instead.

**Correct requirements.txt:**
```txt
gradio>=4.0.0
openai>=1.10.0
# ... other dependencies
# NO "." entry
```

### ModuleNotFoundError: No module named 'chatassistant_retail'

**Error message:**
```
ModuleNotFoundError: No module named 'chatassistant_retail'
```

**Cause:**
The package isn't installed or the sys.path manipulation in `app.py` isn't working.

**Solution for HF Spaces:**
Verify `app.py` contains sys.path manipulation (lines 13-17):

```python
src_path = Path(__file__).parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
```

**Solution for Local:**
Install the package in editable mode:

```bash
pip install -e .
```

### HF Spaces Build Succeeds But App Doesn't Start

**Symptoms:**
- Docker build completes successfully
- App fails to start or import errors occur

**Check:**
1. Verify all required environment variables are set in HF Spaces settings
2. Check HF Spaces logs for specific error messages
3. Ensure `DEPLOYMENT_MODE` environment variable is set to "hf_spaces"

**Environment variables needed:**
- `AZURE_COGNITIVE_SEARCH_ENDPOINT` (optional - falls back to local JSON if missing)
- `AZURE_COGNITIVE_SEARCH_API_KEY` (optional)
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`

## Local Development Issues

### "data" Module Not Found

**Error:**
```python
from chatassistant_retail.data.models import Product
ModuleNotFoundError: No module named 'chatassistant_retail.data'
```

**Cause:**
Package not installed or file permissions issue.

**Solution:**
1. Install in editable mode: `pip install -e .`
2. Verify src/chatassistant_retail/data/ has `__init__.py`
3. Check file permissions: `chmod 644 src/chatassistant_retail/data/*.py`

### Sample Data Files Missing

**Symptom:**
Application can't find products.json or sales_history.json

**Solution:**
As of version 0.1.1, sample data is included in the repository. If missing:

1. Pull latest from git: `git pull origin main`
2. Or regenerate: `python scripts/generate_sample_data.py`

## Azure Integration Issues

### Azure Search Index Not Found

**Error:**
```
Index 'products' not found
```

**Solution:**
Create the index using the setup script:

```bash
python scripts/setup_azure_search.py
```

This creates the index with proper schema and optionally loads sample data.

### Semantic Search Not Enabled

**Error:**
```
(FeatureNotSupportedInService) Semantic search is not enabled for this service.
```

**Solution:**
1. Navigate to Azure AI Search service in Azure Portal
2. Click "Semantic ranker" in left menu
3. Change setting from "Disabled" to "Free"
4. Save and wait 1-2 minutes

The application automatically falls back to non-semantic search if unavailable.
