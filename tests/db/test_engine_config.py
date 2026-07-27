"""SQLAlchemy engine configuration (pooling)."""

from types import SimpleNamespace

from app.db.database import build_engine_kwargs


def _config(**overrides):
    base = dict(
        DB_ECHO=False,
        DB_POOL_PRE_PING=True,
        DB_POOL_RECYCLE=1800,
        DB_POOL_SIZE=5,
        DB_MAX_OVERFLOW=10,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_postgres_gets_full_pool_configuration():
    kwargs = build_engine_kwargs("postgresql://localhost/db", config=_config())

    assert kwargs["pool_pre_ping"] is True
    assert kwargs["pool_recycle"] == 1800
    assert kwargs["pool_size"] == 5
    assert kwargs["max_overflow"] == 10
    assert kwargs["echo"] is False


def test_pool_values_are_configurable():
    kwargs = build_engine_kwargs(
        "postgresql://localhost/db",
        config=_config(DB_POOL_SIZE=20, DB_MAX_OVERFLOW=40, DB_POOL_RECYCLE=900, DB_ECHO=True),
    )

    assert kwargs["pool_size"] == 20
    assert kwargs["max_overflow"] == 40
    assert kwargs["pool_recycle"] == 900
    assert kwargs["echo"] is True


def test_sqlite_omits_server_pool_settings():
    kwargs = build_engine_kwargs("sqlite://", config=_config())

    # SQLite uses a different pool that rejects these arguments.
    assert "pool_size" not in kwargs
    assert "max_overflow" not in kwargs
    assert "pool_recycle" not in kwargs
    assert kwargs["echo"] is False
