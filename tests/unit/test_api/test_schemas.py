"""Unit tests for API schemas."""

from __future__ import annotations

from datetime import UTC, datetime

from src.api.schemas import (
    ApiResponse,
    ErrorDetail,
    PaginationMeta,
    PortfolioCreateRequest,
    UserResponse,
)


class TestApiResponse:
    def test_data_response(self) -> None:
        resp = ApiResponse(data={"key": "value"})
        assert resp.data == {"key": "value"}
        assert resp.error is None
        assert resp.meta is None

    def test_error_response(self) -> None:
        resp = ApiResponse(error=ErrorDetail(code="NOT_FOUND", message="Not found"))
        assert resp.data is None
        assert resp.error is not None
        assert resp.error.code == "NOT_FOUND"

    def test_paginated_response(self) -> None:
        resp = ApiResponse(
            data=[1, 2, 3],
            meta=PaginationMeta(total=100, page=1, limit=20),
        )
        assert resp.meta is not None
        assert resp.meta.total == 100


class TestUserResponse:
    def test_from_attributes(self) -> None:
        class FakeUser:
            id = "00000000-0000-0000-0000-000000000002"
            username = "test"
            email = "test@example.com"
            persona_type = "trader"
            preferences = {}
            created_at = datetime(2025, 1, 1, tzinfo=UTC)

        user_resp = UserResponse.model_validate(FakeUser())
        assert str(user_resp.id) == "00000000-0000-0000-0000-000000000002"
        assert user_resp.username == "test"


class TestPortfolioCreateRequest:
    def test_valid(self) -> None:
        req = PortfolioCreateRequest(symbol="BTC", quantity=1.5, entry_price=50000.0)
        assert req.symbol == "BTC"

    def test_invalid_quantity(self) -> None:
        import pydantic

        with __import__("pytest").raises(pydantic.ValidationError):
            PortfolioCreateRequest(symbol="BTC", quantity=-1, entry_price=50000.0)
