"""Abstract session storage interface."""

from abc import ABC, abstractmethod
from typing import Any


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    async def save_state(self, session_id: str, state: dict[str, Any]) -> bool:
        """
        Save conversation state for a session.

        Args:
            session_id: Unique session identifier
            state: State dictionary to save

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def load_state(self, session_id: str) -> dict[str, Any] | None:
        """
        Load conversation state for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            State dictionary if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_state(self, session_id: str) -> bool:
        """
        Delete conversation state for a session.

        Args:
            session_id: Unique session identifier

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def list_sessions(self) -> list[str]:
        """
        List all active session IDs.

        Returns:
            List of session IDs
        """
        pass

    @abstractmethod
    async def clear_all(self) -> bool:
        """
        Clear all sessions.

        Returns:
            True if successful, False otherwise
        """
        pass
