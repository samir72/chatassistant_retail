"""Response parser for LLM outputs."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResponseParser:
    """Parse and process LLM responses."""

    @staticmethod
    def parse_tool_arguments(arguments_str: str) -> dict[str, Any]:
        """
        Parse tool function arguments from JSON string.

        Args:
            arguments_str: JSON string of function arguments

        Returns:
            Dictionary of parsed arguments
        """
        try:
            if isinstance(arguments_str, dict):
                return arguments_str

            return json.loads(arguments_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tool arguments: {e}")
            logger.debug(f"Arguments string: {arguments_str}")
            return {}

    @staticmethod
    def extract_thinking(response_text: str) -> tuple[str, str]:
        """
        Extract thinking/reasoning section from response.

        Some responses may include internal reasoning that should be
        separated from the final answer.

        Args:
            response_text: Full response text

        Returns:
            Tuple of (thinking, answer)
        """
        # Look for common thinking patterns
        thinking_markers = [
            "Let me think",
            "First, I'll",
            "To answer this",
            "Here's my approach:",
        ]

        thinking = ""
        answer = response_text

        for marker in thinking_markers:
            if marker in response_text:
                parts = response_text.split("\n\n", 1)
                if len(parts) == 2 and marker in parts[0]:
                    thinking = parts[0]
                    answer = parts[1]
                    break

        return thinking, answer

    @staticmethod
    def format_error_response(error: Exception, context: str = "") -> str:
        """
        Format error into user-friendly response.

        Args:
            error: Exception that occurred
            context: Additional context about what was being attempted

        Returns:
            User-friendly error message
        """
        error_messages = {
            "ConnectionError": "I'm having trouble connecting to the service. Please try again in a moment.",
            "TimeoutError": "The request took too long. Please try again.",
            "ValueError": "I encountered an issue processing your request. Could you rephrase that?",
            "KeyError": "Some required information is missing. Please provide more details.",
        }

        error_type = type(error).__name__
        user_message = error_messages.get(error_type, "I encountered an unexpected error.")

        if context:
            user_message += f" (Context: {context})"

        logger.error(f"Error in {context}: {error_type} - {str(error)}")

        return user_message

    @staticmethod
    def truncate_context(text: str, max_length: int = 2000) -> str:
        """
        Truncate context text to fit within token limits.

        Args:
            text: Text to truncate
            max_length: Maximum character length

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text

        truncated = text[: max_length - 3]
        # Try to truncate at a sentence boundary
        last_period = truncated.rfind(".")
        if last_period > max_length * 0.8:  # Only if we're not losing too much
            truncated = truncated[: last_period + 1]

        return truncated + "..."

    @staticmethod
    def validate_response(response: dict[str, Any]) -> bool:
        """
        Validate that response has expected structure.

        Args:
            response: Response dictionary from LLM

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(response, dict):
                logger.warning(f"Response is not a dictionary: {type(response)}")
                return False

            if "choices" not in response:
                logger.warning("Response missing 'choices' field")
                return False

            choices = response.get("choices", [])
            if not choices:
                logger.warning("Response has empty choices")
                return False

            first_choice = choices[0]
            if "message" not in first_choice:
                logger.warning("First choice missing 'message' field")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating response: {e}")
            return False

    @staticmethod
    def extract_metadata(response: dict[str, Any]) -> dict[str, Any]:
        """
        Extract metadata from LLM response.

        Args:
            response: Response dictionary from LLM

        Returns:
            Dictionary of metadata (tokens, model, finish_reason, etc.)
        """
        metadata = {}

        try:
            # Usage information
            usage = response.get("usage", {})
            metadata["prompt_tokens"] = usage.get("prompt_tokens", 0)
            metadata["completion_tokens"] = usage.get("completion_tokens", 0)
            metadata["total_tokens"] = usage.get("total_tokens", 0)

            # Model information
            metadata["model"] = response.get("model", "unknown")

            # Finish reason
            choices = response.get("choices", [])
            if choices:
                metadata["finish_reason"] = choices[0].get("finish_reason", "unknown")

            # Response ID
            metadata["response_id"] = response.get("id", "")

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")

        return metadata
