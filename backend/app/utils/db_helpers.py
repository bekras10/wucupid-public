"""Database helper utilities."""
import time
import functools
import logging
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from psycopg2.errors import OperationalError as Psycopg2OpError
from flask import current_app
from .. import db

logger = logging.getLogger(__name__)

def retry_on_db_error(max_retries=3, delay=1):
    """
    Decorator to retry database operations on transient errors.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        delay (int): Delay in seconds between retries
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (OperationalError, Psycopg2OpError) as e:
                    last_error = e
                    if attempt < max_retries - 1:  # Don't sleep on last attempt
                        logger.warning(
                            f"Database error on attempt {attempt + 1}/{max_retries}, "
                            f"retrying in {delay}s: {str(e)}"
                        )
                        time.sleep(delay)
                        # Ensure connection is fresh
                        db.session.remove()
                        db.engine.dispose()
                    else:
                        logger.error(
                            f"Database operation failed after {max_retries} attempts: {str(e)}"
                        )
                except SQLAlchemyError as e:
                    # Don't retry on non-operational errors
                    logger.error(f"Database error (non-retryable): {str(e)}")
                    raise
            raise last_error
        return wrapper
    return decorator

def ensure_fresh_connection():
    """Ensure we have a fresh database connection."""
    try:
        # Test the connection
        db.session.execute("SELECT 1")
    except Exception:
        # If there's any error, cleanup and get fresh connection
        db.session.remove()
        db.engine.dispose() 