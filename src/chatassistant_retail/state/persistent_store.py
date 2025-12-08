"""Persistent session storage implementations for local deployment."""

import json
import logging
from typing import Any

from chatassistant_retail.state.session_store import SessionStore

logger = logging.getLogger(__name__)


class RedisSessionStore(SessionStore):
    """
    Redis-based session storage implementation.

    Suitable for local deployment with Redis server.
    Requires: redis>=5.0.0
    """

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl: int = 3600):
        """
        Initialize Redis session store.

        Args:
            redis_url: Redis connection URL
            ttl: Session time-to-live in seconds (default: 1 hour)
        """
        try:
            import redis.asyncio as redis

            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.ttl = ttl
            self._prefix = "chatbot:session:"
            logger.info(f"Initialized Redis session store: {redis_url}")
        except ImportError:
            logger.error("redis package not installed. Install with: pip install redis")
            raise

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
            key = f"{self._prefix}{session_id}"
            serialized = json.dumps(state)
            await self.redis.setex(key, self.ttl, serialized)
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
            key = f"{self._prefix}{session_id}"
            serialized = await self.redis.get(key)
            if serialized:
                state = json.loads(serialized)
                logger.debug(f"Loaded state for session: {session_id}")
                return state
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
            key = f"{self._prefix}{session_id}"
            deleted = await self.redis.delete(key)
            if deleted:
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
        try:
            pattern = f"{self._prefix}*"
            keys = await self.redis.keys(pattern)
            session_ids = [key.replace(self._prefix, "") for key in keys]
            return session_ids
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    async def clear_all(self) -> bool:
        """
        Clear all sessions.

        Returns:
            True if successful, False otherwise
        """
        try:
            pattern = f"{self._prefix}*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
            logger.info(f"Cleared {len(keys)} sessions")
            return True
        except Exception as e:
            logger.error(f"Error clearing all sessions: {e}")
            return False

    async def close(self):
        """Close Redis connection."""
        await self.redis.close()


class PostgreSQLSessionStore(SessionStore):
    """
    PostgreSQL-based session storage implementation.

    Suitable for local deployment with PostgreSQL database.
    Requires: psycopg2-binary>=2.9.9, sqlalchemy>=2.0.0
    """

    def __init__(self, db_url: str = "postgresql://localhost/chatbot"):
        """
        Initialize PostgreSQL session store.

        Args:
            db_url: PostgreSQL connection URL
        """
        try:
            from sqlalchemy import JSON, Column, DateTime, String, create_engine, text
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            from sqlalchemy.orm import declarative_base, sessionmaker

            # Convert sync URL to async if needed
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

            self.engine = create_async_engine(db_url, echo=False)
            self.async_session_maker = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

            Base = declarative_base()

            class SessionState(Base):
                __tablename__ = "chatbot_sessions"
                session_id = Column(String, primary_key=True)
                state = Column(JSON, nullable=False)
                updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

            self.SessionState = SessionState
            logger.info(f"Initialized PostgreSQL session store: {db_url}")
        except ImportError:
            logger.error(
                "Required packages not installed. Install with: pip install psycopg2-binary sqlalchemy asyncpg"
            )
            raise

    async def _ensure_table(self):
        """Create table if not exists."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(self.SessionState.metadata.create_all)
        except Exception as e:
            logger.error(f"Error creating table: {e}")

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
            await self._ensure_table()
            from sqlalchemy.dialects.postgresql import insert

            async with self.async_session_maker() as session:
                stmt = insert(self.SessionState).values(session_id=session_id, state=state)
                stmt = stmt.on_conflict_do_update(index_elements=["session_id"], set_={"state": state})
                await session.execute(stmt)
                await session.commit()
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
            from sqlalchemy import select

            async with self.async_session_maker() as session:
                result = await session.execute(
                    select(self.SessionState).where(self.SessionState.session_id == session_id)
                )
                row = result.scalar_one_or_none()
                if row:
                    logger.debug(f"Loaded state for session: {session_id}")
                    return row.state
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
            from sqlalchemy import delete

            async with self.async_session_maker() as session:
                result = await session.execute(
                    delete(self.SessionState).where(self.SessionState.session_id == session_id)
                )
                await session.commit()
                deleted = result.rowcount > 0
                if deleted:
                    logger.debug(f"Deleted state for session: {session_id}")
                else:
                    logger.debug(f"No state to delete for session: {session_id}")
                return deleted
        except Exception as e:
            logger.error(f"Error deleting state for session {session_id}: {e}")
            return False

    async def list_sessions(self) -> list[str]:
        """
        List all active session IDs.

        Returns:
            List of session IDs
        """
        try:
            from sqlalchemy import select

            async with self.async_session_maker() as session:
                result = await session.execute(select(self.SessionState.session_id))
                session_ids = [row[0] for row in result.all()]
                return session_ids
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []

    async def clear_all(self) -> bool:
        """
        Clear all sessions.

        Returns:
            True if successful, False otherwise
        """
        try:
            from sqlalchemy import delete

            async with self.async_session_maker() as session:
                result = await session.execute(delete(self.SessionState))
                await session.commit()
                logger.info(f"Cleared {result.rowcount} sessions")
                return True
        except Exception as e:
            logger.error(f"Error clearing all sessions: {e}")
            return False

    async def close(self):
        """Close database connection."""
        await self.engine.dispose()
