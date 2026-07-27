from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

from app.enums.sort_order import SortOrder
from app.repositories.pagination import PageResult


T = TypeVar("T")

# Upper bound so a client can never request an unbounded page.
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class PaginationParams:
    """Shared query parameters for paginated endpoints.

    Used as a FastAPI dependency so routers declare pagination uniformly and do
    no validation themselves -- ``page >= 1`` and ``1 <= page_size <= 100`` are
    enforced here by FastAPI's ``Query`` constraints.
    """

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="1-based page number"),
        page_size: int = Query(
            default=DEFAULT_PAGE_SIZE,
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Items per page",
        ),
        order: SortOrder = Query(
            default=SortOrder.DESC,
            description="newest-first (desc) or oldest-first (asc)",
        ),
    ):
        self.page = page
        self.page_size = page_size
        self.order = order


class PageMeta(BaseModel):
    total_items: int
    total_pages: int
    page: int
    page_size: int


class Page(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T]
    meta: PageMeta

    @classmethod
    def build(
        cls,
        result: PageResult,
        page: int,
        page_size: int,
    ) -> "Page[T]":
        """Map a repository ``PageResult`` onto the API envelope.

        Deriving ``total_pages`` here (not in routers) keeps the mapping in one
        place; it is presentation math, not business logic.
        """

        total_pages = ceil(result.total / page_size) if page_size else 0

        return cls(
            items=result.items,
            meta=PageMeta(
                total_items=result.total,
                total_pages=total_pages,
                page=page,
                page_size=page_size,
            ),
        )
