"""
Compatibility shim — re-exports database primitives from app.db.session and app.db.base
so that code referencing app.models.database continues to work.
"""
from app.db.base import Base
from app.db.session import engine, SessionLocal, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
