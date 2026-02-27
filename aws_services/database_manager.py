"""Database Manager for PostgreSQL RDS"""
import logging
import time
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2 import pool, OperationalError, DatabaseError
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections with pooling and retry logic"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        Initialize database manager with connection pooling
        
        Args:
            db_config: Database configuration (can be dict with connection params or database_url)
        """
        self.db_config = db_config
        self.connection_pool = None
        
        try:
            # Parse database URL if provided
            if 'database_url' in db_config:
                self._init_from_url(db_config['database_url'])
            else:
                self._init_from_params(db_config)
                
            logger.info("Database connection pool initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {str(e)}")
            raise
    
    def _init_from_url(self, database_url: str):
        """Initialize connection pool from database URL"""
        self.connection_pool = pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=database_url
        )
    
    def _init_from_params(self, db_config: Dict[str, Any]):
        """Initialize connection pool from connection parameters"""
        self.connection_pool = pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 5432),
            database=db_config.get('database', 'seva_arogya'),
            user=db_config.get('username', 'postgres'),
            password=db_config.get('password', '')
        )
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        
        Yields:
            Database connection from pool
        """
        conn = None
        try:
            conn = self.connection_pool.getconn()
            yield conn
        finally:
            if conn:
                self.connection_pool.putconn(conn)
    
    def execute_with_retry(self, query: str, params: tuple = None, max_retries: int = 3) -> Optional[List]:
        """
        Execute query with exponential backoff retry logic
        
        Args:
            query: SQL query to execute
            params: Query parameters
            max_retries: Maximum number of retry attempts
            
        Returns:
            Query results or None
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(query, params)
                        
                        # Commit if it's a write operation
                        if query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                            conn.commit()
                            return None
                        
                        # Fetch results for SELECT queries
                        return cursor.fetchall()
                        
            except (OperationalError, DatabaseError) as e:
                retry_count += 1
                last_error = e
                
                if retry_count < max_retries:
                    # Exponential backoff: 0.5s, 1s, 2s
                    wait_time = 0.5 * (2 ** (retry_count - 1))
                    logger.warning(f"Database query failed (attempt {retry_count}/{max_retries}), retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Database query failed after {max_retries} attempts: {str(e)}")
                    raise last_error
            
            except Exception as e:
                logger.error(f"Unexpected database error: {str(e)}")
                raise
        
        return None
    
    def health_check(self) -> bool:
        """
        Check database connection health
        
        Returns:
            True if database is accessible, False otherwise
        """
        try:
            result = self.execute_with_retry("SELECT 1", max_retries=1)
            return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def close_all_connections(self):
        """Close all connections in the pool gracefully"""
        if self.connection_pool:
            try:
                self.connection_pool.closeall()
                logger.info("All database connections closed successfully")
            except Exception as e:
                logger.error(f"Error closing database connections: {str(e)}")
