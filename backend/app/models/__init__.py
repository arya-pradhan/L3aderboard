"""SQLModel models. Importing them here ensures they are registered on the
shared SQLModel metadata (used by Alembic autogenerate)."""
from app.models.follow import Follow
from app.models.game import Game
from app.models.library import LibraryEntry, LibraryStatus, LibrarySource
from app.models.user import User

__all__ = [
    "User",
    "Game",
    "LibraryEntry",
    "LibraryStatus",
    "LibrarySource",
    "Follow",
]
