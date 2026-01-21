"""
Lightweight database abstraction for v2 scrapers.

For now, this uses an in-memory set to track seen listing IDs so that
scrapers can implement smart pagination (stop when they hit already-seen
listings while sorting by newest first).

Tomorrow, this module will be updated to check a real PostgreSQL database.
The public API (`listing_exists`) should remain stable so scrapers don't
need to change.
"""

from typing import Set

import logging

logger = logging.getLogger(__name__)

# In-memory set of seen listing external IDs (Yahoo auction IDs, Mercari item IDs, etc.)
_seen_listing_ids: Set[str] = set()


def listing_exists(external_id: str) -> bool:
    """
    Check if a listing with the given external_id has already been seen.

    Args:
        external_id: External ID of the listing (auction ID, item ID, etc.)

    Returns:
        True if we've already seen this ID in the current process, False otherwise.

    Notes:
        - This is intentionally very lightweight: an in-memory set only.
        - In production with PostgreSQL, this will become a real database lookup.
    """
    if not external_id:
        return False

    exists = external_id in _seen_listing_ids
    if exists and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"listing_exists: external_id={external_id} already seen")
    return exists


def mark_listing_seen(external_id: str) -> None:
    """
    Mark a single listing as seen in the in-memory set.

    This is a convenience for any code path that wants to eagerly register
    listings as seen (e.g., after persisting to the real database).
    """
    if not external_id:
        return
    _seen_listing_ids.add(external_id)


def mark_listings_seen(external_ids) -> None:
    """
    Mark multiple listings as seen.

    Args:
        external_ids: Iterable of external ID strings.
    """
    for external_id in external_ids:
        mark_listing_seen(external_id)


