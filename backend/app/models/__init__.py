"""SQLAlchemy models package.

Ensure all model modules are imported so their tables
are registered in Base.metadata for migrations and create_all.
"""

# Import model modules to register tables
from .upload import Upload  # noqa: F401
from .task import Task  # noqa: F401
from .result import Result  # noqa: F401
