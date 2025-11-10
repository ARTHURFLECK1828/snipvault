"""
Connection pooling for PostgreSQL.

Provides efficient connection management with health checks,
automatic reconnection, and monitoring.
"""

import time
from contextlib import contextmanager
from typing import Optional, Dict, Any
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from utils.logger import get_logger
from utils.exceptions import ConnectionError, DatabaseError

logger = get_logger(__name__)


class ConnectionPool:
    """PostgreSQL connection pool manager."""

    def __init__(
        self,
        host: str,
        port: int,
        database: str,
        user: str,
        password: str,
        min_connections: int = 1,
        max_connections: int = 10,
        max_overflow: int = 20,
        connection_timeout: int = 30
    ):
        """
        Initialize connection pool.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
            min_connections: Minimum pool size
            max_connections: Maximum pool size
            max_overflow: Maximum overflow connections
            connection_timeout: Connection timeout in seconds
        """
        self.config = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }

        self.min_connections = min_connections
        self.max_connections = max_connections
        self.max_overflow = max_overflow
        self.connection_timeout = connection_timeout

        self._pool: Optional[pg_pool.ThreadedConnectionPool] = None
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'total_requests': 0,
            'failed_requests': 0,
            'total_wait_time': 0.0,
            'max_wait_time': 0.0
        }

        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self._pool = pg_pool.ThreadedConnectionPool(
                minconn=self.min_connections,
                maxconn=self.max_connections + self.max_overflow,
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password'],
                connect_timeout=self.connection_timeout,
                cursor_factory=RealDictCursor
            )

            logger.info(
                f"Connection pool initialized: "
                f"min={self.min_connections}, max={self.max_connections}, "
                f"overflow={self.max_overflow}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise ConnectionError(f"Failed to initialize connection pool: {e}")

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.

        Yields:
            Database connection

        Raises:
            ConnectionError: If connection cannot be acquired
        """
        connection = None
        start_time = time.time()

        try:
            self._stats['total_requests'] += 1

            # Get connection from pool
            connection = self._pool.getconn()

            wait_time = time.time() - start_time
            self._stats['total_wait_time'] += wait_time
            self._stats['max_wait_time'] = max(self._stats['max_wait_time'], wait_time)
            self._stats['active_connections'] += 1

            if wait_time > 1.0:
                logger.warning(f"High connection wait time: {wait_time:.2f}s")

            # Verify connection is alive
            if not self._is_connection_alive(connection):
                logger.warning("Stale connection detected, reconnecting...")
                self._pool.putconn(connection, close=True)
                connection = self._pool.getconn()

            yield connection

        except Exception as e:
            self._stats['failed_requests'] += 1
            logger.error(f"Error getting connection from pool: {e}")
            raise ConnectionError(f"Failed to get database connection: {e}")

        finally:
            if connection:
                self._stats['active_connections'] -= 1

                # Return connection to pool
                try:
                    self._pool.putconn(connection)
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")

    @contextmanager
    def get_cursor(self, commit: bool = True):
        """
        Get a cursor from a pooled connection.

        Args:
            commit: Whether to auto-commit on success

        Yields:
            Database cursor

        Raises:
            DatabaseError: If cursor operation fails
        """
        with self.get_connection() as conn:
            cursor = None
            try:
                cursor = conn.cursor()
                yield cursor

                if commit:
                    conn.commit()

            except Exception as e:
                if commit:
                    conn.rollback()
                logger.error(f"Cursor operation failed: {e}")
                raise DatabaseError(f"Database operation failed: {e}")

            finally:
                if cursor:
                    cursor.close()

    def _is_connection_alive(self, connection) -> bool:
        """
        Check if connection is alive.

        Args:
            connection: Database connection

        Returns:
            True if connection is alive
        """
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False

    def health_check(self) -> bool:
        """
        Perform health check on the connection pool.

        Returns:
            True if pool is healthy
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                cursor.close()

                return result is not None

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def close_all_connections(self):
        """Close all connections in the pool."""
        if self._pool:
            try:
                self._pool.closeall()
                logger.info("All connections closed")
            except Exception as e:
                logger.error(f"Error closing connections: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics.

        Returns:
            Dictionary with pool stats
        """
        avg_wait_time = (
            self._stats['total_wait_time'] / self._stats['total_requests']
            if self._stats['total_requests'] > 0
            else 0.0
        )

        return {
            'total_requests': self._stats['total_requests'],
            'failed_requests': self._stats['failed_requests'],
            'active_connections': self._stats['active_connections'],
            'avg_wait_time_ms': round(avg_wait_time * 1000, 2),
            'max_wait_time_ms': round(self._stats['max_wait_time'] * 1000, 2),
            'success_rate': (
                (self._stats['total_requests'] - self._stats['failed_requests'])
                / self._stats['total_requests'] * 100
                if self._stats['total_requests'] > 0
                else 0.0
            ),
            'pool_config': {
                'min_connections': self.min_connections,
                'max_connections': self.max_connections,
                'max_overflow': self.max_overflow
            }
        }

    def reset_stats(self):
        """Reset pool statistics."""
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'idle_connections': 0,
            'total_requests': 0,
            'failed_requests': 0,
            'total_wait_time': 0.0,
            'max_wait_time': 0.0
        }

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all_connections()


# Global connection pool instance
_pool_instance: Optional[ConnectionPool] = None


def get_connection_pool() -> ConnectionPool:
    """
    Get global connection pool instance.

    Returns:
        ConnectionPool instance
    """
    global _pool_instance

    if _pool_instance is None:
        from config import get_config

        config = get_config()

        _pool_instance = ConnectionPool(
            host=config.require('database.postgres.host'),
            port=config.get('database.postgres.port', 5432),
            database=config.require('database.postgres.database'),
            user=config.require('database.postgres.user'),
            password=config.require('database.postgres.password'),
            min_connections=1,
            max_connections=config.get('database.postgres.pool_size', 10),
            max_overflow=config.get('database.postgres.max_overflow', 20),
            connection_timeout=30
        )

    return _pool_instance


def close_pool():
    """Close global connection pool."""
    global _pool_instance

    if _pool_instance:
        _pool_instance.close_all_connections()
        _pool_instance = None
