from enum import Enum


class SortOrder(str, Enum):
    """Ordering for collection endpoints.

    ``DESC`` is "newest first" (the default everywhere), ``ASC`` is "oldest
    first". Repositories translate this against each table's chronological
    column (``id`` / ``created_at`` / ``started_at``).
    """

    ASC = "asc"
    DESC = "desc"
