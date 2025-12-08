"""
Deployment entry point for HuggingFace Spaces.

This file is used when deploying to HuggingFace Spaces.
For local deployment, use: python -m chatassistant_retail
"""

import logging
import os
import sys
from pathlib import Path

# Add src directory to Python path for HuggingFace Spaces deployment
# This allows imports to work without installing the package
src_path = Path(__file__).parent / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Set deployment mode for HF Spaces
os.environ["DEPLOYMENT_MODE"] = "hf_spaces"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

logger.info("Starting Retail Inventory Assistant on HuggingFace Spaces")

# from chatassistant_retail.ui import create_gradio_interface
from chatassistant_retail.ui import gradio_app

# Create and launch interface
#demo = create_gradio_interface()
demo = gradio_app.create_gradio_interface()

if __name__ == "__main__":
    # For HF Spaces, use 0.0.0.0 to accept external connections
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
