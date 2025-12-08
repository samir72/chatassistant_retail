"""Main Gradio application for retail chatbot."""

import logging
import uuid

import gradio as gr

from chatassistant_retail.chatbot import get_chatbot
from chatassistant_retail.ui.chat_interface import (
    create_example_queries,
    format_context_display,
    format_error_message,
    get_welcome_message,
)
from chatassistant_retail.ui.metrics_dashboard import (
    format_activity_log,
    format_metrics_for_display,
    get_empty_metrics,
)

logger = logging.getLogger(__name__)


def create_gradio_interface():
    """
    Create and configure the Gradio interface.

    Returns:
        Gradio Blocks interface
    """
    # Initialize chatbot
    chatbot_instance = get_chatbot()

    # Session storage (in Gradio state)
    def get_session_id(session_id):
        """Get or create session ID."""
        if not session_id:
            return str(uuid.uuid4())
        return session_id

    async def send_message(message, chat_history, session_id, image=None):
        """
        Process user message and update chat.

        Args:
            message: User message text
            chat_history: Current chat history
            session_id: Session identifier
            image: Optional uploaded image

        Returns:
            Tuple of (empty_message, updated_chat, session_id, context)
        """
        if not message and not image:
            return "", chat_history, session_id, "No message provided"

        try:
            # Ensure session ID exists
            session_id = get_session_id(session_id)

            # Process message through chatbot
            response = await chatbot_instance.process_message(
                text=message or "Analyze this image",
                image=image,
                session_id=session_id,
            )

            # Extract response
            response_text = response.get("response", "Sorry, I couldn't generate a response.")

            # Handle errors
            if response.get("error"):
                response_text = format_error_message(response["error"])

            # Update chat history
            chat_history.append({"role": "user", "content": message or "[Image uploaded]"})
            chat_history.append({"role": "assistant", "content": response_text})

            # Format context for display
            context = format_context_display(response.get("context", {}))

            return "", chat_history, session_id, context

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            error_msg = format_error_message(str(e))
            chat_history.append({"role": "user", "content": message or "[Image uploaded]"})
            chat_history.append({"role": "assistant", "content": error_msg})
            return "", chat_history, session_id, "Error occurred"

    async def clear_chat(session_id):
        """Clear chat history."""
        if session_id:
            try:
                await chatbot_instance.clear_session(session_id)
            except Exception as e:
                logger.error(f"Error clearing session: {e}")

        # Generate new session ID
        new_session_id = str(uuid.uuid4())
        return [], new_session_id, "Chat cleared"

    def refresh_metrics():
        """Refresh metrics dashboard."""
        try:
            metrics = chatbot_instance.get_metrics()
            total, avg_time, tools, success = format_metrics_for_display(metrics)
            activity = format_activity_log(metrics)
            return total, avg_time, tools, success, activity
        except Exception as e:
            logger.error(f"Error refreshing metrics: {e}")
            empty = get_empty_metrics()
            total, avg_time, tools, success = format_metrics_for_display(empty)
            activity = [["Error loading metrics", "", ""]]
            return total, avg_time, tools, success, activity

    def use_example(example):
        """Use example query."""
        return example

    # Create Gradio interface
    with gr.Blocks(title="Retail Inventory Assistant") as demo:
        gr.Markdown("# 🛒 Retail Inventory Assistant")
        gr.Markdown("AI-powered chatbot for retail inventory management with multi-modal support")

        # Session state
        session_id_state = gr.State(value=None)

        with gr.Row():
            # Left column: Chat interface
            with gr.Column(scale=2):
                gr.Markdown("## 💬 Chat")

                chatbot = gr.Chatbot(
                    value=[],
                    height=500,
                    label="Conversation",
                    show_label=False,
                )

                with gr.Row():
                    message_input = gr.Textbox(
                        placeholder="Ask about inventory, products, or stock levels...",
                        label="Message",
                        scale=4,
                        lines=2,
                    )
                    image_input = gr.Image(
                        type="filepath",
                        label="Upload Image (Optional)",
                        scale=1,
                    )

                with gr.Row():
                    send_btn = gr.Button("Send", variant="primary", scale=2)
                    clear_btn = gr.Button("Clear Chat", scale=1)

                # Context display
                context_display = gr.Textbox(
                    label="📋 Context Used",
                    lines=5,
                    interactive=False,
                )

                # Example queries
                gr.Markdown("### 💡 Example Queries")
                examples = create_example_queries()
                example_buttons = []
                with gr.Row():
                    for example in examples[:3]:
                        btn = gr.Button(example, size="sm")
                        example_buttons.append((btn, example))
                with gr.Row():
                    for example in examples[3:]:
                        btn = gr.Button(example, size="sm")
                        example_buttons.append((btn, example))

            # Right column: Metrics dashboard
            with gr.Column(scale=1):
                gr.Markdown("## 📊 Metrics")

                with gr.Row():
                    total_queries = gr.Number(
                        label="Total Queries",
                        value=0,
                        interactive=False,
                    )
                    avg_response_time = gr.Number(
                        label="Avg Response (s)",
                        value=0.0,
                        precision=3,
                        interactive=False,
                    )

                with gr.Row():
                    tool_calls = gr.Number(
                        label="Tool Calls",
                        value=0,
                        interactive=False,
                    )
                    success_rate = gr.Number(
                        label="Success Rate (%)",
                        value=100.0,
                        precision=1,
                        interactive=False,
                    )

                gr.Markdown("### 📝 Recent Activity")
                activity_log = gr.Dataframe(
                    headers=["Time", "Action", "Status"],
                    value=[["No activity yet", "", ""]],
                    interactive=False,
                )

                refresh_btn = gr.Button("🔄 Refresh Metrics", size="sm")

        # Event handlers
        send_btn.click(
            fn=send_message,
            inputs=[message_input, chatbot, session_id_state, image_input],
            outputs=[message_input, chatbot, session_id_state, context_display],
        )

        message_input.submit(
            fn=send_message,
            inputs=[message_input, chatbot, session_id_state, image_input],
            outputs=[message_input, chatbot, session_id_state, context_display],
        )

        clear_btn.click(
            fn=clear_chat,
            inputs=[session_id_state],
            outputs=[chatbot, session_id_state, context_display],
        )

        refresh_btn.click(
            fn=refresh_metrics,
            outputs=[total_queries, avg_response_time, tool_calls, success_rate, activity_log],
        )

        # Example buttons
        for btn, example in example_buttons:
            btn.click(
                fn=use_example,
                inputs=[gr.State(example)],
                outputs=[message_input],
            )

        # Show welcome message and initial metrics on load
        demo.load(
            fn=lambda: [{"role": "assistant", "content": get_welcome_message()}],
            outputs=[chatbot],
        )

        # Initial metrics load
        demo.load(
            fn=refresh_metrics,
            outputs=[total_queries, avg_response_time, tool_calls, success_rate, activity_log],
        )

    return demo


def launch_app(server_name="127.0.0.1", server_port=7860, share=False):
    """
    Launch the Gradio app.

    Args:
        server_name: Server host (default: 127.0.0.1)
        server_port: Server port (default: 7860)
        share: Whether to create public share link
    """
    logger.info(f"Launching Gradio app on {server_name}:{server_port}")

    demo = create_gradio_interface()
    demo.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        show_error=True,
    )
