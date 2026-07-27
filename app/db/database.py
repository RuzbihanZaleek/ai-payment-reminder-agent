from sqlalchemy import create_engine

from app.core.config import settings


def build_engine_kwargs(database_url: str, config=settings) -> dict:
    """Assemble SQLAlchemy engine kwargs from configuration.

    Factored out (and pure) so the pooling configuration can be unit-tested
    without opening a real connection. Connection-pool tuning is only applied to
    server databases -- SQLite (used by tests) uses a different pool that would
    reject these arguments.
    """

    kwargs: dict = {"echo": config.DB_ECHO}

    if not database_url.startswith("sqlite"):
        kwargs.update(
            pool_pre_ping=config.DB_POOL_PRE_PING,  # detect dropped connections
            pool_recycle=config.DB_POOL_RECYCLE,    # avoid stale server-side timeouts
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
        )

    return kwargs


engine = create_engine(
    settings.DATABASE_URL,
    **build_engine_kwargs(settings.DATABASE_URL),
)
