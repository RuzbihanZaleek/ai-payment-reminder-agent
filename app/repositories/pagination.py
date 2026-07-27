"""Repository-layer pagination and ordering helpers.

Pagination, filtering and ordering are owned by the repositories. These helpers
keep the mechanics in one place so no repository re-implements offset math or
the newest/oldest-first ordering.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Query

from app.enums.sort_order import SortOrder


@dataclass
class PageResult:
    """A single page of rows plus the unpaginated total.

    Repositories return this; services/reporting services pass it through; the
    router maps it onto the API ``Page`` envelope.
    """

    items: list
    total: int


def apply_ordering(query: Query, column, order: SortOrder) -> Query:
    """Order ``query`` by ``column`` -- descending for newest-first."""

    if order == SortOrder.ASC:
        return query.order_by(column.asc())

    return query.order_by(column.desc())


def paginate(query: Query, page: int, page_size: int) -> PageResult:
    """Return the requested page of ``query`` together with its total count.

    ``total`` is computed before applying limit/offset so callers can derive the
    page count. Assumes ``page >= 1`` and ``page_size >= 1`` (validated at the
    API edge by ``PaginationParams``).
    """

    total = query.order_by(None).count()

    items = (
        query
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PageResult(items=items, total=total)
