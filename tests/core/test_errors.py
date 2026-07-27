"""Standardized error envelope produced by the exception handlers."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    register_exception_handlers,
    AppError,
    NotFoundError,
    UnauthorizedError,
    ErrorCode,
)


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    class Body(BaseModel):
        value: int

    @app.get("/notfound")
    def _notfound():
        raise NotFoundError("Missing.", code=ErrorCode.CONTRACT_NOT_FOUND)

    @app.get("/unauthorized")
    def _unauthorized():
        raise UnauthorizedError("Nope.")

    @app.get("/generic")
    def _generic():
        raise AppError("Bad input.")

    @app.get("/boom")
    def _boom():
        raise RuntimeError("kaboom")

    @app.post("/validate")
    def _validate(body: Body):
        return {"ok": body.value}

    return app


def test_app_error_envelope():
    client = TestClient(_app())

    response = client.get("/notfound")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "CONTRACT_NOT_FOUND", "message": "Missing."}
    }


def test_unauthorized_defaults_to_unauthorized_code():
    client = TestClient(_app())

    response = client.get("/unauthorized")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_generic_app_error_is_validation_error_400():
    client = TestClient(_app())

    response = client.get("/generic")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unexpected_exception_is_masked_as_500():
    client = TestClient(_app(), raise_server_exceptions=False)

    response = client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Internal details must never leak.
    assert "kaboom" not in response.text


def test_request_validation_error_envelope():
    client = TestClient(_app())

    response = client.post("/validate", json={"value": "not-an-int"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
