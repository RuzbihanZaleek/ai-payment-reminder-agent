from app.repositories.pagination import PageResult
from app.schemas.pagination import Page, PaginationParams, MAX_PAGE_SIZE


def test_page_build_computes_total_pages_with_remainder():
    result = PageResult(items=[1, 2, 3], total=25)

    page = Page.build(result, page=1, page_size=10)

    assert page.meta.total_items == 25
    assert page.meta.total_pages == 3  # ceil(25 / 10)
    assert page.meta.page == 1
    assert page.meta.page_size == 10
    assert page.items == [1, 2, 3]


def test_page_build_exact_multiple():
    page = Page.build(PageResult(items=[], total=20), page=2, page_size=10)

    assert page.meta.total_pages == 2


def test_page_build_empty():
    page = Page.build(PageResult(items=[], total=0), page=1, page_size=10)

    assert page.meta.total_pages == 0
    assert page.meta.total_items == 0
    assert page.items == []


def test_pagination_params_explicit_values():
    from app.enums.sort_order import SortOrder

    params = PaginationParams(page=2, page_size=5, order=SortOrder.ASC)

    assert params.page == 2
    assert params.page_size == 5
    assert params.order == SortOrder.ASC


def test_max_page_size_is_bounded():
    assert MAX_PAGE_SIZE == 100
