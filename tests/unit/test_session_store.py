"""Unit tests for session storage implementations."""

import pytest

from chatassistant_retail.state import MemorySessionStore


class TestMemorySessionStore:
    """Test in-memory session storage."""

    @pytest.mark.asyncio
    async def test_save_and_load_state(self):
        """Test saving and loading session state."""
        store = MemorySessionStore()

        session_id = "test-session-1"
        state = {"messages": ["hello", "world"], "context": {"key": "value"}}

        # Save state
        success = await store.save_state(session_id, state)
        assert success is True

        # Load state
        loaded_state = await store.load_state(session_id)
        assert loaded_state is not None
        assert loaded_state["messages"] == ["hello", "world"]
        assert loaded_state["context"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_load_nonexistent_state(self):
        """Test loading state that doesn't exist."""
        store = MemorySessionStore()

        loaded_state = await store.load_state("nonexistent-session")
        assert loaded_state is None

    @pytest.mark.asyncio
    async def test_delete_state(self):
        """Test deleting session state."""
        store = MemorySessionStore()

        session_id = "test-session-2"
        state = {"data": "test"}

        # Save and then delete
        await store.save_state(session_id, state)
        deleted = await store.delete_state(session_id)
        assert deleted is True

        # Verify deletion
        loaded_state = await store.load_state(session_id)
        assert loaded_state is None

        # Delete again should return False
        deleted_again = await store.delete_state(session_id)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        """Test listing all session IDs."""
        store = MemorySessionStore()

        # Save multiple sessions
        await store.save_state("session-1", {"data": "1"})
        await store.save_state("session-2", {"data": "2"})
        await store.save_state("session-3", {"data": "3"})

        # List sessions
        sessions = await store.list_sessions()
        assert len(sessions) == 3
        assert "session-1" in sessions
        assert "session-2" in sessions
        assert "session-3" in sessions

    @pytest.mark.asyncio
    async def test_clear_all(self):
        """Test clearing all sessions."""
        store = MemorySessionStore()

        # Save multiple sessions
        await store.save_state("session-1", {"data": "1"})
        await store.save_state("session-2", {"data": "2"})

        # Clear all
        success = await store.clear_all()
        assert success is True

        # Verify all cleared
        sessions = await store.list_sessions()
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_update_existing_state(self):
        """Test updating an existing session state."""
        store = MemorySessionStore()

        session_id = "test-session-3"

        # Save initial state
        await store.save_state(session_id, {"count": 1})

        # Update state
        await store.save_state(session_id, {"count": 2})

        # Load and verify
        loaded_state = await store.load_state(session_id)
        assert loaded_state["count"] == 2

    @pytest.mark.asyncio
    async def test_get_session_count(self):
        """Test getting session count."""
        store = MemorySessionStore()

        assert store.get_session_count() == 0

        await store.save_state("session-1", {"data": "1"})
        assert store.get_session_count() == 1

        await store.save_state("session-2", {"data": "2"})
        assert store.get_session_count() == 2

        await store.delete_state("session-1")
        assert store.get_session_count() == 1

    @pytest.mark.asyncio
    async def test_state_isolation(self):
        """Test that states are isolated between sessions."""
        store = MemorySessionStore()

        # Save different states for different sessions
        await store.save_state("session-a", {"value": "A"})
        await store.save_state("session-b", {"value": "B"})

        # Load and verify isolation
        state_a = await store.load_state("session-a")
        state_b = await store.load_state("session-b")

        assert state_a["value"] == "A"
        assert state_b["value"] == "B"

        # Modify one shouldn't affect the other
        state_a["value"] = "Modified"
        reloaded_b = await store.load_state("session-b")
        assert reloaded_b["value"] == "B"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
