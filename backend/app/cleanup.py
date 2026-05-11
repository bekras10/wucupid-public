import atexit
from . import db  # assumes db = SQLAlchemy() is defined in app/__init__.py

@atexit.register
def close_db_sessions():
    try:
        db.session.remove()
    except Exception:
        pass