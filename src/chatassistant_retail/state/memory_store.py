"""In-memory session storage for HuggingFace Spaces deployment."""

import logging
from typing import Any

from chatassistant_retail.state.session_store import SessionStore

logger = logging.getLogger(__name__)


class MemorySessionStore(SessionStore):
    """
    In-memory session storage implementation.

    Suitable for HuggingFace Spaces deployment where sessions persist
    only while the space is running. State is lost on restart/cold start.
    """

    def __init__(self):
        """Initialize in-memory storage."""
        self._sessions: dict[str, dict[str, Any]] = {}
        logger.info("Initialized in-memory session store")

    async def save_state(self, session_id: str, state: dict[str, Any]) -> bool:
        """
        Save conversation state for a session.

        Args:
            session_id: Unique session identifier
            state: State dictionary to save

        Returns:
            True if successful, False otherwise
        """
        try:
            self._sessions[session_id] = state.copy()
            logger.debug(f"Saved state for session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving state for session {session_id}: {e}")
            return False

    async def load_state(self, session_id: str) -> dict[str, Any] | None:
        """
        Load conversation state for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            State dictionary if found, None otherwise
        """
        try:
            state = self._sessions.get(session_id)
            if state:
                logger.debug(f"Loaded state for session: {session_id}")
                return state.copy()
            logger.debug(f"No state found for session: {session_id}")
            return None
        except Exception as e:
            logger.error(f"Error loading state for session {session_id}: {e}")
            return None

    async def delete_state(self, session_id: str) -> bool:
        """
        Delete conversation state for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug(f"Deleted state for session: {session_id}")
                return True
            logger.debug(f"No state to delete for session: {session_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting state for session {session_id}: {e}")
            return False

    async def list_sessions(self) -> list[str]:
        """
        List all active session IDs.

        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

    async def clear_all(self) -> bool:
        """
        Clear all sessions.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._sessions.clear()
            logger.info("Cleared all sessions")
            return True
        except Exception as e:
            logger.error(f"Error clearing all sessions: {e}")
            return False

    def get_session_count(self) -> int:
        """
        Get current number of active sessions.

        Returns:
            Number of sessions
        """
        return len(self._sessions)
