import os

# Force the testing environment BEFORE any app module (and thus Settings) is
# imported below. This keeps a plain ``pytest`` invocation deterministic:
# APP_ENV=testing disables the background scheduler and rate limiting so the
# suite never starts threads or throttles its own auth calls. Using setdefault
# means an explicitly-exported APP_ENV/JWT_SECRET_KEY still wins.
os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-sandbox-only")

import pytest

from app.db.session import SessionLocal


@pytest.fixture
def db_session():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()