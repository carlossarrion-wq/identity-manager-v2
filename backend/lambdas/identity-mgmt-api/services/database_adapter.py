"""
Database Adapter for Local Development
Provides SQLite support while maintaining PostgreSQL interface compatibility
"""
import sqlite3
import os
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Any

logger = logging.getLogger()


class SQLiteAdapter:
    """SQLite adapter that mimics PostgreSQL interface for local development"""
    
    _connection = None
    
    @classmethod
    def get_connection(cls):
        """Get or create SQLite connection"""
        if cls._connection is None:
            db_path = os.environ.get('DB_PATH', 'identity_manager.db')
            logger.info(f"Creating SQLite connection to {db_path}")
            cls._connection = sqlite3.connect(db_path, check_same_thread=False)
            cls._connection.row_factory = sqlite3.Row
        return cls._connection
    
    @classmethod
    @contextmanager
    def get_cursor(cls):
        """Context manager for database cursor"""
        conn = cls.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    @classmethod
    def execute_query(cls, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query and return results as list of dicts"""
        with cls.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    @classmethod
    def execute_insert(cls, query: str, params: tuple = None) -> Optional[str]:
        """Execute INSERT query and return last inserted ID"""
        with cls.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return str(cursor.lastrowid)
    
    @classmethod
    def execute_update(cls, query: str, params: tuple = None) -> int:
        """Execute UPDATE/DELETE query and return affected rows"""
        with cls.get_cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.rowcount
    
    @classmethod
    def dict_row_factory(cls, cursor, row):
        """Convert row to dictionary"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def is_local_development() -> bool:
    """Check if running in local development mode"""
    return os.environ.get('ENVIRONMENT') == 'local-development' or os.environ.get('DB_TYPE') == 'sqlite'


# Monkey-patch the database service for local development
if is_local_development():
    logger.info("🔧 Local development mode detected - using SQLite adapter")
