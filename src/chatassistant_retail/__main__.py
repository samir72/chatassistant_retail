"""Main entry point for Retail Inventory Assistant."""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    """Launch the Gradio UI."""
    from chatassistant_retail.ui import create_gradio_interface

    print("\n" + "=" * 60)
    print("🛒 Retail Inventory Assistant")
    print("=" * 60)
    print("\nStarting Gradio interface...")
    print("Access the UI at: http://127.0.0.1:7860")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    demo = create_gradio_interface()
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
