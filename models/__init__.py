"""
models/__init__.py — Database instance and model imports
"""

from flask_sqlalchemy import SQLAlchemy

# Single shared db instance used across all models
db = SQLAlchemy()

from .user import User
from .profile import Profile
from .application import Application

__all__ = ["db", "User", "Profile", "Application"]
