"""Langgraph dialog state machine for conversation flow."""

import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, ConfigDict, Field

from chatassistant_retail.tools.context_utils import update_products_cache

logger = logging.getLogger(__name__)


class ConversationState(BaseModel):
    """State model for conversation flow."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: list[BaseMessage] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str = ""
    current_intent: Literal["greeting", "rag", "tool", "direct", "unknown"] = "unknown"
    needs_rag: bool = False
    needs_tool: bool = False
    error: str | None = None


class LanggraphManager:
    """
    Manages conversation flow using Langgraph state machine.

    State machine nodes:
    - greeting_node: Initialize conversation
    - classify_intent_node: Determine if user needs RAG, tool, or direct response
    - rag_retrieval_node: Retrieve product/sales context
    - tool_execution_node: Execute MCP tools
    - generate_response_node: LLM generates final response
    """

    def __init__(self, llm_client, rag_retriever, tool_executor):
        """
        Initialize Langgraph manager.

        Args:
            llm_client: Azure OpenAI client instance
            rag_retriever: RAG retriever instance
            tool_executor: MCP tool executor instance
        """
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever
        self.tool_executor = tool_executor
        self.workflow = self._build_workflow()
        logger.info("Initialized Langgraph state machine")

    def _build_workflow(self) -> StateGraph:
        """
        Build the conversation workflow graph.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(ConversationState)

        # Add nodes
        workflow.add_node("greeting", self._greeting_node)
        workflow.add_node("classify_intent", self._classify_intent_node)
        workflow.add_node("rag_retrieval", self._rag_retrieval_node)
        workflow.add_node("tool_execution", self._tool_execution_node)
        workflow.add_node("generate_response", self._generate_response_node)

        # Set entry point
        workflow.set_entry_point("classify_intent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_after_classification,
            {
                "greeting": "greeting",
                "rag": "rag_retrieval",
                "tool": "tool_execution",
                "direct": "generate_response",
            },
        )

        workflow.add_edge("greeting", "generate_response")
        workflow.add_edge("rag_retrieval", "generate_response")
        workflow.add_edge("tool_execution", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile()

    async def _greeting_node(self, state: ConversationState) -> dict[str, Any]:
        """
        Handle greeting and conversation initialization.

        Args:
            state: Current conversation state

        Returns:
            Updated state fields
        """
        logger.debug("Executing greeting_node")
        return {"current_intent": "greeting"}

    async def _classify_intent_node(self, state: ConversationState) -> dict[str, Any]:
        """
        Classify user intent to determine next action.

        Args:
            state: Current conversation state

        Returns:
            Updated state fields with classified intent
        """
        logger.debug("Executing classify_intent_node")

        if not state.messages:
            return {"current_intent": "direct"}

        # Get last user message
        last_message = state.messages[-1]
        if not isinstance(last_message, HumanMessage):
            return {"current_intent": "direct"}

        user_text = last_message.content.lower() if isinstance(last_message.content, str) else ""

        # Check for greeting
        greeting_keywords = ["hello", "hi", "hey", "good morning", "good afternoon"]
        if any(keyword in user_text for keyword in greeting_keywords) and len(user_text.split()) <= 5:
            return {"current_intent": "greeting"}

        # Check for tool-related queries
        tool_keywords = [
            "create order",
            "purchase order",
            "reorder point",
            "calculate reorder",
            "low stock",
            "inventory status",
            "stock level",
        ]
        if any(keyword in user_text for keyword in tool_keywords):
            return {"current_intent": "tool", "needs_tool": True}

        # Check for RAG-related queries (product search, information)
        rag_keywords = [
            "product",
            "find",
            "search",
            "category",
            "price",
            "electronics",
            "clothing",
            "supplier",
            "sku",
            "jacket",
            "laptop",
            "headphones",
            "smartphone",
        ]
        if any(keyword in user_text for keyword in rag_keywords):
            return {"current_intent": "rag", "needs_rag": True}

        # Default to direct response
        return {"current_intent": "direct"}

    async def _rag_retrieval_node(self, state: ConversationState) -> dict[str, Any]:
        """
        Retrieve relevant context from RAG system.

        Args:
            state: Current conversation state

        Returns:
            Updated state fields with retrieved context
        """
        logger.debug("Executing rag_retrieval_node")

        try:
            # Get last user message
            last_message = state.messages[-1]
            query = last_message.content if isinstance(last_message.content, str) else ""

            # Retrieve products
            products = await self.rag_retriever.retrieve(query, top_k=5)

            # Store in context (for backward compatibility)
            context = dict(state.context) if state.context else {}
            context["products"] = products
            context["rag_query"] = query
            logger.info(f"Retrieved {len(products)} products for query: {query}")

            # Also populate products_cache for tool reuse
            if products:
                # Create a temporary state object to pass to update function
                temp_state = ConversationState(
                    messages=state.messages,
                    context=context,
                    tool_calls=state.tool_calls,
                    session_id=state.session_id,
                )
                update_products_cache(
                    temp_state,
                    products=products,
                    source="rag",
                    filter_applied={"query": query},
                )
                # Update context with the cache
                context = temp_state.context

            return {"context": context}

        except Exception as e:
            logger.error(f"Error in RAG retrieval: {e}")
            context = dict(state.context) if state.context else {}
            context["products"] = []
            return {"error": f"RAG retrieval failed: {str(e)}", "context": context}

    async def _tool_execution_node(self, state: ConversationState) -> dict[str, Any]:
        """
        Execute MCP tools based on user request.

        Args:
            state: Current conversation state

        Returns:
            Updated state fields with tool execution results
        """
        logger.debug("Executing tool_execution_node")

        try:
            # Get last user message
            last_message = state.messages[-1]
            user_text = last_message.content if isinstance(last_message.content, str) else ""

            # Call LLM with tools to determine which tool to use
            from chatassistant_retail.tools.mcp_server import get_tool_definitions

            tools = get_tool_definitions()

            # Use LLM to determine tool call
            response = await self.llm_client.call_llm(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful retail assistant. Use the appropriate tool to answer the user's question.",
                    },
                    {"role": "user", "content": user_text},
                ],
                tools=tools,
            )

            # Check if LLM requested tool calls
            tool_calls_data = []
            tool_calls = await self.llm_client.extract_tool_calls(response)

            if tool_calls:
                logger.debug(f"Extracted {len(tool_calls)} tool calls from LLM response")

            for tool_call in tool_calls:
                tool_name = tool_call.get("function", {}).get("name", "")
                tool_args = tool_call.get("function", {}).get("arguments", {})

                logger.debug(f"Processing tool call: {tool_name} with args type: {type(tool_args)}")

                # Parse arguments if they're a string
                import json

                if isinstance(tool_args, str):
                    tool_args = json.loads(tool_args)

                # Execute tool with conversation state for context-aware data access
                logger.info(f"Executing tool: {tool_name}")
                tool_result = await self.tool_executor.execute_tool(tool_name, tool_args, state=state)

                tool_calls_data.append(
                    {
                        "tool": tool_name,
                        "args": tool_args,
                        "result": tool_result,
                    }
                )

            context = dict(state.context) if state.context else {}
            context["tool_results"] = tool_calls_data
            logger.info(f"Executed {len(tool_calls_data)} tool calls")

            return {"tool_calls": tool_calls_data, "context": context}

        except Exception as e:
            logger.error(f"Error in tool execution: {e}")
            return {"error": f"Tool execution failed: {str(e)}", "tool_calls": []}

    async def _generate_response_node(self, state: ConversationState) -> dict[str, Any]:
        """
        Generate final response using LLM.

        Args:
            state: Current conversation state

        Returns:
            Updated state fields with LLM response
        """
        logger.debug("Executing generate_response_node")

        try:
            # Build context for LLM
            context_parts = []

            # Add RAG context
            if "products" in state.context and state.context["products"]:
                products = state.context["products"]
                context_parts.append(f"Found {len(products)} relevant products:")
                for p in products[:3]:  # Top 3
                    context_parts.append(
                        f"- {p.get('name')} (SKU: {p.get('sku')}) - ${p.get('price')} - Stock: {p.get('current_stock')}"
                    )

            # Add tool results
            if "tool_results" in state.context and state.context["tool_results"]:
                context_parts.append("\nTool execution results:")
                for tool_call in state.context["tool_results"]:
                    context_parts.append(f"- {tool_call['tool']}: {tool_call['result']}")

            # Build messages for LLM
            llm_messages = []

            # Add system message
            system_prompt = "You are a helpful retail inventory assistant. Use the provided context to answer the user's questions accurately."
            if context_parts:
                system_prompt += f"\n\nContext:\n{chr(10).join(context_parts)}"
            llm_messages.append({"role": "system", "content": system_prompt})

            # Add conversation history
            for msg in state.messages:
                if isinstance(msg, HumanMessage):
                    llm_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    llm_messages.append({"role": "assistant", "content": msg.content})

            # Call LLM
            response = await self.llm_client.call_llm(messages=llm_messages)

            # Extract response text
            response_text = await self.llm_client.extract_response_content(response)

            # Add AI response to messages
            updated_messages = list(state.messages)
            updated_messages.append(AIMessage(content=response_text))
            logger.info("Generated LLM response")

            return {"messages": updated_messages}

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            updated_messages = list(state.messages)
            updated_messages.append(AIMessage(content=error_msg))
            return {"messages": updated_messages, "error": str(e)}

    def _route_after_classification(self, state: ConversationState) -> Literal["greeting", "rag", "tool", "direct"]:
        """
        Route to appropriate node after intent classification.

        Args:
            state: Current conversation state

        Returns:
            Next node name
        """
        return state.current_intent if state.current_intent in ["greeting", "rag", "tool"] else "direct"

    async def process(self, state: ConversationState) -> ConversationState:
        """
        Process a conversation state through the workflow.

        Args:
            state: Initial conversation state

        Returns:
            Final conversation state after processing
        """
        logger.debug(f"Processing conversation for session: {state.session_id}")
        try:
            # Langgraph returns dict, convert back to ConversationState
            result = await self.workflow.ainvoke(state)
            if isinstance(result, dict):
                return ConversationState(**result)
            return result
        except Exception as e:
            logger.error(f"Error processing workflow: {e}")
            state.error = str(e)
            return state
