"""Main chatbot class for retail inventory assistant."""

import logging
import uuid
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from chatassistant_retail.config.settings import Settings
from chatassistant_retail.llm import AzureOpenAIClient
from chatassistant_retail.rag import Retriever
from chatassistant_retail.state import ConversationState, LanggraphManager, MemorySessionStore
from chatassistant_retail.tools.mcp_server import ToolExecutor

logger = logging.getLogger(__name__)


class RetailChatBot:
    """
    Main chatbot class for retail inventory management.

    Integrates:
    - Azure OpenAI multi-modal LLM
    - RAG retrieval from Azure AI Search
    - MCP tools for inventory operations
    - Langgraph state management
    - Session persistence
    - LangFuse observability (optional)
    """

    def __init__(
        self,
        settings: Settings | None = None,
        session_store=None,
    ):
        """
        Initialize retail chatbot.

        Args:
            settings: Configuration settings (uses default if not provided)
            session_store: Session storage implementation (uses MemorySessionStore if not provided)
        """
        self.settings = settings or Settings()

        # Initialize LLM client
        self.llm_client = AzureOpenAIClient(settings=self.settings)
        logger.info("Initialized Azure OpenAI client")

        # Initialize RAG retriever
        self.rag_retriever = Retriever(settings=self.settings)
        logger.info("Initialized RAG retriever")

        # Initialize MCP tool executor
        self.tool_executor = ToolExecutor()
        logger.info("Initialized MCP tool executor")

        # Initialize session store
        self.session_store = session_store or MemorySessionStore()
        logger.info(f"Initialized session store: {type(self.session_store).__name__}")

        # Initialize Langgraph state machine
        self.state_manager = LanggraphManager(
            llm_client=self.llm_client,
            rag_retriever=self.rag_retriever,
            tool_executor=self.tool_executor,
        )
        logger.info("Initialized Langgraph state manager")

        # Initialize LangFuse observability
        self.langfuse_client = None
        if self.settings.langfuse_enabled:
            try:
                from chatassistant_retail.observability import get_langfuse_client

                self.langfuse_client = get_langfuse_client()
                logger.info("Initialized LangFuse observability")
            except Exception as e:
                logger.warning(f"Failed to initialize LangFuse: {e}")

    async def process_message(
        self,
        text: str,
        image: str | Path | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process user message and generate response.

        Args:
            text: User message text
            image: Optional image path for multi-modal input
            session_id: Session identifier (generates new if not provided)

        Returns:
            Dictionary with response and metadata:
            {
                "response": str,
                "session_id": str,
                "intent": str,
                "context": dict,
                "tool_calls": list,
                "error": str | None
            }
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.info(f"Processing message for session: {session_id}")

        try:
            # Load existing state or create new
            state_dict = await self.session_store.load_state(session_id)
            if state_dict:
                state = ConversationState(**state_dict)
                logger.debug(f"Loaded existing state with {len(state.messages)} messages")
            else:
                state = ConversationState(session_id=session_id)
                logger.debug("Created new conversation state")

            # Handle multi-modal input
            if image:
                # Use multi-modal LLM for image + text
                response = await self.llm_client.process_multimodal(
                    text=text,
                    image_path=image,
                    system_prompt="You are a helpful retail inventory assistant with vision capabilities.",
                )

                # Extract response text
                response_text = await self.llm_client.extract_response_content(response)

                # Create simple state for multi-modal
                from langchain_core.messages import AIMessage

                state.messages.append(HumanMessage(content=f"{text} [with image]"))
                state.messages.append(AIMessage(content=response_text))
                state.current_intent = "direct"

            else:
                # Add user message to state
                state.messages.append(HumanMessage(content=text))

                # Trim conversation history if too long
                max_history = self.settings.max_conversation_history
                if len(state.messages) > max_history * 2:  # *2 for user+assistant pairs
                    state.messages = state.messages[-(max_history * 2) :]
                    logger.debug(f"Trimmed conversation history to {len(state.messages)} messages")

                # Process through Langgraph state machine
                state = await self.state_manager.process(state)

            # Save state
            state_dict = state.model_dump(mode="json")
            await self.session_store.save_state(session_id, state_dict)

            # Extract response
            response_text = ""
            if state.messages:
                last_message = state.messages[-1]
                response_text = last_message.content if hasattr(last_message, "content") else ""

            # Build response
            result = {
                "response": response_text,
                "session_id": session_id,
                "intent": state.current_intent,
                "context": state.context,
                "tool_calls": state.tool_calls,
                "error": state.error,
            }

            logger.info(f"Successfully processed message for session: {session_id}")
            return result

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "session_id": session_id,
                "intent": "unknown",
                "context": {},
                "tool_calls": [],
                "error": str(e),
            }

    async def clear_session(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Clearing session: {session_id}")
        return await self.session_store.delete_state(session_id)

    async def get_session_history(self, session_id: str) -> list[dict[str, str]]:
        """
        Get conversation history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of messages with role and content
        """
        state_dict = await self.session_store.load_state(session_id)
        if not state_dict:
            return []

        state = ConversationState(**state_dict)
        history = []
        for msg in state.messages:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            content = msg.content if hasattr(msg, "content") else ""
            history.append({"role": role, "content": content})

        return history

    def get_metrics(self) -> dict[str, Any]:
        """
        Get chatbot metrics.

        Returns:
            Dictionary with metrics data
        """
        if self.langfuse_client:
            try:
                from chatassistant_retail.observability import MetricsCollector

                collector = MetricsCollector(self.langfuse_client)
                return collector.get_dashboard_data()
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

        # Return basic metrics if LangFuse not available
        return {
            "total_queries": 0,
            "avg_response_time": 0.0,
            "tool_calls_count": 0,
            "recent_activity": [],
        }


# Create singleton instance
_chatbot_instance: RetailChatBot | None = None


def get_chatbot() -> RetailChatBot:
    """
    Get singleton chatbot instance.

    Returns:
        RetailChatBot instance
    """
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = RetailChatBot()
    return _chatbot_instance
