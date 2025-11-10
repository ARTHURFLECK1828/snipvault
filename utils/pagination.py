"""
Pagination utilities for SnipVault.

Provides pagination for search results and snippet listings.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from math import ceil


@dataclass
class Page:
    """Page of results with metadata."""

    items: List[Any]
    page_number: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @property
    def start_index(self) -> int:
        """Get start index (1-based)."""
        return (self.page_number - 1) * self.page_size + 1

    @property
    def end_index(self) -> int:
        """Get end index (1-based)."""
        return min(self.page_number * self.page_size, self.total_items)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'items': self.items,
            'page': self.page_number,
            'page_size': self.page_size,
            'total_items': self.total_items,
            'total_pages': self.total_pages,
            'has_next': self.has_next,
            'has_previous': self.has_previous,
            'start_index': self.start_index,
            'end_index': self.end_index
        }


class Paginator:
    """Paginator for offsetting and limiting results."""

    def __init__(self, page_size: int = 10):
        """
        Initialize paginator.

        Args:
            page_size: Number of items per page
        """
        self.page_size = page_size

    def paginate(
        self,
        items: List[Any],
        page: int = 1,
        total_count: Optional[int] = None
    ) -> Page:
        """
        Paginate a list of items.

        Args:
            items: List of items to paginate
            page: Page number (1-based)
            total_count: Total count (if known), otherwise len(items) used

        Returns:
            Page object
        """
        page = max(1, page)  # Ensure page >= 1
        total_items = total_count if total_count is not None else len(items)
        total_pages = ceil(total_items / self.page_size) if total_items > 0 else 1

        # Ensure page doesn't exceed total pages
        page = min(page, total_pages)

        # Calculate offset
        offset = (page - 1) * self.page_size

        # Slice items if not already sliced
        if total_count is None:
            page_items = items[offset:offset + self.page_size]
        else:
            page_items = items

        return Page(
            items=page_items,
            page_number=page,
            page_size=self.page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )

    def get_offset_limit(self, page: int) -> Tuple[int, int]:
        """
        Get SQL offset and limit for a page.

        Args:
            page: Page number (1-based)

        Returns:
            Tuple of (offset, limit)
        """
        page = max(1, page)
        offset = (page - 1) * self.page_size
        return offset, self.page_size


@dataclass
class CursorPage:
    """Cursor-based page for streaming results."""

    items: List[Any]
    next_cursor: Optional[str]
    has_more: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'items': self.items,
            'next_cursor': self.next_cursor,
            'has_more': self.has_more
        }


class CursorPaginator:
    """Cursor-based paginator for streaming results."""

    def __init__(self, page_size: int = 10):
        """
        Initialize cursor paginator.

        Args:
            page_size: Number of items per page
        """
        self.page_size = page_size

    def paginate(
        self,
        items: List[Any],
        cursor_key: str = 'id',
        after: Optional[str] = None
    ) -> CursorPage:
        """
        Paginate items using cursor.

        Args:
            items: List of items (should be pre-sorted)
            cursor_key: Key to use for cursor (default: 'id')
            after: Cursor to start after

        Returns:
            CursorPage object
        """
        # Filter items after cursor
        if after:
            filtered_items = []
            found_cursor = False

            for item in items:
                if found_cursor:
                    filtered_items.append(item)
                elif str(self._get_cursor_value(item, cursor_key)) == after:
                    found_cursor = True

            items = filtered_items

        # Take page_size + 1 to check if there are more items
        page_items = items[:self.page_size + 1]
        has_more = len(page_items) > self.page_size

        # Remove extra item if present
        if has_more:
            page_items = page_items[:self.page_size]

        # Get next cursor
        next_cursor = None
        if has_more and page_items:
            next_cursor = str(self._get_cursor_value(page_items[-1], cursor_key))

        return CursorPage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more
        )

    def _get_cursor_value(self, item: Any, key: str) -> Any:
        """
        Get cursor value from item.

        Args:
            item: Item (dict or object)
            key: Key to extract

        Returns:
            Cursor value
        """
        if isinstance(item, dict):
            return item.get(key)
        else:
            return getattr(item, key, None)


def format_pagination_info(page: Page) -> str:
    """
    Format pagination info for display.

    Args:
        page: Page object

    Returns:
        Formatted string
    """
    return (
        f"Page {page.page_number}/{page.total_pages} "
        f"(showing {page.start_index}-{page.end_index} of {page.total_items})"
    )


def get_page_navigation(page: Page) -> str:
    """
    Get navigation instructions for CLI.

    Args:
        page: Page object

    Returns:
        Navigation string
    """
    nav_parts = []

    if page.has_previous:
        nav_parts.append(f"Previous: --page {page.page_number - 1}")

    if page.has_next:
        nav_parts.append(f"Next: --page {page.page_number + 1}")

    if nav_parts:
        return " | ".join(nav_parts)
    return ""
