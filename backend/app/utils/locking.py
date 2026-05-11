"""Database locking utilities."""
from sqlalchemy import text
from .. import db

# Global constant lock keys (choose arbitrary, keep spaced to avoid clashes)
GLOBAL_INIT_LOCK_KEY = 9000000
GLOBAL_CYCLE_THREAD_LOCK_KEY = 42424242
GLOBAL_CYCLE_TRANSITION_LOCK_KEY = 8888888

def acquire_global_init_lock() -> bool:
    """Acquire global advisory lock for cycle initialization (one per deploy)."""
    return db.session.execute(
        text("SELECT pg_try_advisory_lock(:k)"),
        {"k": GLOBAL_INIT_LOCK_KEY}
    ).scalar()

def release_global_init_lock() -> None:
    """Release global advisory lock for cycle initialization."""
    db.session.execute(
        text("SELECT pg_advisory_unlock(:k)"),
        {"k": GLOBAL_INIT_LOCK_KEY}
    )

def try_acquire_global_cycle_thread():
    """
    Returns a live connection holding the advisory lock if acquired,
    or None if not acquired.
    Keep this connection open for lifetime of thread.
    """
    conn = db.engine.connect()
    try:
        acquired = conn.execute(text("SELECT pg_try_advisory_lock(:k)"),
                              {"k": GLOBAL_CYCLE_THREAD_LOCK_KEY}).scalar()
        if acquired:
            return conn
        conn.close()
        return None
    except Exception:
        conn.close()
        return None

def acquire_match_lock(cycle_id: int) -> bool:
    """
    Try to acquire an advisory lock for match generation.
    Returns True if lock acquired, False if not.
    """
    return db.session.execute(
        text("SELECT pg_try_advisory_lock(:k)"),
        {"k": cycle_id}
    ).scalar()

def release_match_lock(cycle_id: int) -> None:
    """Release the advisory lock for match generation."""
    db.session.execute(
        text("SELECT pg_advisory_unlock(:k)"),
        {"k": cycle_id}
    )

def acquire_email_lock(cycle_id: int) -> bool:
    """
    Try to acquire an advisory lock for email sending.
    Returns True if lock acquired, False if not.
    """
    return db.session.execute(
        text("SELECT pg_try_advisory_lock(:k)"),
        {"k": cycle_id + 1000000}  # Offset to avoid collision with match locks
    ).scalar()

def release_email_lock(cycle_id: int) -> None:
    """Release the advisory lock for email sending."""
    db.session.execute(
        text("SELECT pg_advisory_unlock(:k)"),
        {"k": cycle_id + 1000000}
    )

def acquire_cycle_lock(cycle_id: int) -> bool:
    """
    Try to acquire an advisory lock for cycle rollover.
    Returns True if lock acquired, False if not.
    """
    return db.session.execute(
        text("SELECT pg_try_advisory_lock(:k)"),
        {"k": GLOBAL_CYCLE_TRANSITION_LOCK_KEY}  # Use global key for cycle transitions
    ).scalar()

def release_cycle_lock(cycle_id: int) -> None:
    """Release the advisory lock for cycle rollover."""
    db.session.execute(
        text("SELECT pg_advisory_unlock(:k)"),
        {"k": GLOBAL_CYCLE_TRANSITION_LOCK_KEY}
    ) 