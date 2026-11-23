import pytest

from app.config import Settings


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Neon's copy-paste connection string
        (
            "postgresql://alex:p%40ss@ep-cool-1.aws.neon.tech/neondb"
            "?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://alex:p%40ss@ep-cool-1.aws.neon.tech/neondb?ssl=require",
        ),
        # Heroku/Render style scheme
        ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
        # Already in the right form: unchanged
        (
            "postgresql+asyncpg://u:p@localhost:5432/docqa",
            "postgresql+asyncpg://u:p@localhost:5432/docqa",
        ),
    ],
)
def test_database_url_is_normalized_for_asyncpg(given, expected):
    assert Settings(database_url=given).database_url == expected
