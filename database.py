"""
Async database operations for v2 scrapers.
Uses SQLAlchemy async with asyncpg (PostgreSQL) or aiosqlite (SQLite for testing).

This module provides persistent storage and deduplication for listings across scraper cycles.
"""
import logging
import os
from typing import List, Optional, Dict
from datetime import datetime, timezone
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

# Import models
try:
    from .models import Base, Listing, UserFilter, AlertSent
except ImportError:
    from models import Base, Listing, UserFilter, AlertSent

# Global engine and session factory (will be initialized by init_database)
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None

# Cache for category column existence
_category_column_exists: Optional[bool] = None


def init_database(database_url: Optional[str] = None) -> None:
    """
    Initialize async database connection and create tables.
    
    Args:
        database_url: Database URL (e.g., postgresql+asyncpg://user:pass@host/db)
                     For SQLite: sqlite+aiosqlite:///./test.db
                     If None, uses models.py's init_database function
    """
    global _engine, _session_factory
    
    if database_url is None:
        # Use the existing models.py initialization
        from config import get_database_url
        database_url = get_database_url()
        
        if not database_url:
            # Default to SQLite for local testing (relative to current working directory)
            # Use absolute path to avoid directory issues
            db_path = os.path.abspath("./test.db")
            database_url = f"sqlite+aiosqlite:///{db_path}"
            logger.warning(f"⚠️  No DATABASE_URL found in environment, using SQLite: {database_url}")
        else:
            logger.info(f"✅ Using database URL from environment")
    
    # Convert postgresql:// to postgresql+asyncpg:// if needed
    if database_url.startswith("postgresql://") and "+asyncpg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        logger.info(f"   Converted to asyncpg URL: {database_url.split('@')[0]}@...")
    
    # Convert sqlite:// to sqlite+aiosqlite:// if needed
    if database_url.startswith("sqlite:///") and "+aiosqlite" not in database_url:
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        logger.info(f"   Converted to aiosqlite URL")
    
    logger.info(f"🔧 Initializing database connection...")
    
    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL query logging
        future=True,
        # SQLite-specific settings
        connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
    )
    
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    logger.info("✅ Database connection initialized")


async def create_tables() -> None:
    """Create all tables if they don't exist"""
    if _engine is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created/verified")


async def drop_tables() -> None:
    """Drop all tables (use with caution!)"""
    if _engine is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("✅ Database tables dropped")


async def listing_exists(external_id: str, market: str) -> bool:
    """
    Check if a listing with the given external_id and market already exists in the database.
    
    Args:
        external_id: External ID of the listing (auction ID, item ID, etc.)
        market: Market name (e.g., "yahoo", "mercari")
    
    Returns:
        True if listing exists, False otherwise
    
    Notes:
        This function is async to support database queries. For backward compatibility
        with existing code, it can be called without await if using an in-memory cache
        (not recommended for production).
    """
    if not external_id or not market:
        return False
    
    if _session_factory is None:
        # Database not initialized - return False (no listings exist)
        logger.debug(f"Database not initialized, listing_exists({external_id}, {market}) = False")
        return False
    
    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(Listing).where(
                    and_(
                        Listing.external_id == external_id,
                        Listing.market == market
                    )
                )
            )
            listing = result.scalar_one_or_none()
            exists = listing is not None
            if exists:
                logger.debug(f"listing_exists: {market}:{external_id} already exists in database")
            return exists
    except Exception as e:
        logger.error(f"❌ Error checking listing existence: {e}", exc_info=True)
        return False


async def save_listing(listing: Listing) -> bool:
    """
    Save a single listing to the database.
    If the listing already exists (by market+external_id), update last_seen timestamp.
    
    Args:
        listing: Listing object to save
    
    Returns:
        True if listing was saved (new), False if it was already a duplicate
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        async with _session_factory() as session:
            # Check if listing already exists
            result = await session.execute(
                select(Listing).where(
                    and_(
                        Listing.external_id == listing.external_id,
                        Listing.market == listing.market
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update last_seen timestamp
                await session.execute(
                    update(Listing)
                    .where(Listing.id == existing.id)
                    .values(last_seen=datetime.now(timezone.utc))
                )
                await session.commit()
                logger.debug(f"Updated existing listing: {listing.market}:{listing.external_id}")
                return False  # Duplicate
            else:
                # Insert new listing
                session.add(listing)
                await session.commit()
                logger.debug(f"Saved new listing: {listing.market}:{listing.external_id}")
                return True  # New listing
                
    except Exception as e:
        logger.error(f"❌ Error saving listing: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        return False


async def _check_category_column_exists(session) -> bool:
    """Check if category column exists in listings table"""
    global _category_column_exists
    if _category_column_exists is not None:
        return _category_column_exists
    
    try:
        from sqlalchemy import text
        from config import get_database_url
        
        db_url = get_database_url() or ""
        if "postgresql" in db_url.lower():
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns
                    WHERE table_name = 'listings'
                    AND column_name = 'category'
                )
            """))
            _category_column_exists = result.scalar()
        elif "sqlite" in db_url.lower():
            result = await session.execute(text("PRAGMA table_info(listings)"))
            columns = [row[1] for row in result.fetchall()]
            _category_column_exists = 'category' in columns
        else:
            _category_column_exists = False
    except Exception as e:
        logger.debug(f"Error checking category column: {e}")
        _category_column_exists = False
    
    return _category_column_exists

async def save_listings_batch(listings: List[Listing]) -> Dict[str, int]:
    """
    Save multiple listings to the database in a batch.
    Uses PostgreSQL's ON CONFLICT for efficient upserts.
    
    Args:
        listings: List of Listing objects to save
    
    Returns:
        Dictionary with stats:
        - saved: Number of new listings saved
        - duplicates: Number of duplicates (existing listings)
        - errors: Number of errors
        - total: Total listings processed
    """
    if not listings:
        return {"saved": 0, "duplicates": 0, "errors": 0, "total": 0}
    
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    stats = {"saved": 0, "duplicates": 0, "errors": 0, "total": len(listings)}
    
    try:
        async with _session_factory() as session:
            # Check if category column exists - if not, remove category from listings
            has_category_column = await _check_category_column_exists(session)
            if not has_category_column:
                # Remove category attribute to avoid SQL errors
                for listing in listings:
                    if hasattr(listing, 'category') and listing.category is not None:
                        # Use object.__setattr__ to bypass SQLAlchemy's attribute system
                        object.__setattr__(listing, 'category', None)
            # Build lookup map: (market, external_id) -> listing
            lookup_map = {(listing.market, listing.external_id): listing for listing in listings}
            
            # Single bulk query to check which listings exist
            # Use OR conditions - PostgreSQL handles this efficiently with indexes
            if lookup_map:
                from sqlalchemy import or_
                conditions = [
                    and_(Listing.market == market, Listing.external_id == external_id)
                    for market, external_id in lookup_map.keys()
                ]
                
                result = await session.execute(
                    select(Listing.market, Listing.external_id, Listing.id).where(
                        or_(*conditions)
                    )
                )
                # Build map of existing listings: (market, external_id) -> id
                existing_map = {(row[0], row[1]): row[2] for row in result.fetchall()}
            else:
                existing_map = {}
            
            # Separate new and existing listings
            new_listings = []
            existing_ids_to_update = []
            now = datetime.now(timezone.utc)
            
            for (market, external_id), listing in lookup_map.items():
                if (market, external_id) in existing_map:
                    existing_ids_to_update.append(existing_map[(market, external_id)])
                    stats["duplicates"] += 1
                else:
                    new_listings.append(listing)
                    stats["saved"] += 1
            
            # Bulk insert new listings
            if new_listings:
                session.add_all(new_listings)
            
            # Bulk update existing listings' last_seen timestamp
            if existing_ids_to_update:
                await session.execute(
                    update(Listing)
                    .where(Listing.id.in_(existing_ids_to_update))
                    .values(last_seen=now)
                )
            
            # Commit all changes at once
            await session.commit()
            logger.debug(
                f"Batch save: {stats['saved']} new, {stats['duplicates']} dups, {stats['errors']} errors"
            )
            
    except Exception as e:
        error_str = str(e)
        # Check if error is about missing category column
        if "category" in error_str.lower() and ("does not exist" in error_str or "UndefinedColumnError" in error_str):
            logger.error("❌ Category column missing in database!")
            logger.error("   Run migration on your production server:")
            logger.error("   python3 migrations/add_category_column.py")
            logger.error("   Or manually: ALTER TABLE listings ADD COLUMN category VARCHAR(200);")
        
        logger.error(f"❌ Error in batch save: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        stats["errors"] = stats["total"]
    
    return stats


async def get_listings_since(timestamp: datetime) -> List[Listing]:
    """
    Get all listings that were first_seen after the given timestamp.
    
    Args:
        timestamp: Get listings first_seen after this time
    
    Returns:
        List of Listing objects
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(Listing).where(Listing.first_seen >= timestamp)
                .order_by(Listing.first_seen.desc())
            )
            listings = result.scalars().all()
            logger.debug(f"Found {len(listings)} listings since {timestamp}")
            return list(listings)
    except Exception as e:
        logger.error(f"❌ Error querying listings: {e}", exc_info=True)
        return []


async def close_database() -> None:
    """
    Close database connections and clean up resources.
    Call this when shutting down the application.
    """
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("✅ Database connections closed")
    else:
        logger.debug("Database already closed or never initialized")


async def save_user_filter(user_filter: UserFilter) -> int:
    """
    Save a user filter to the database.
    
    Args:
        user_filter: UserFilter object to save
    
    Returns:
        Filter ID (primary key)
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        async with _session_factory() as session:
            session.add(user_filter)
            await session.commit()
            await session.refresh(user_filter)  # Refresh to get the ID
            filter_id = user_filter.id
            logger.debug(f"Saved filter: {user_filter.name} (ID: {filter_id})")
            return filter_id
    except Exception as e:
        logger.error(f"❌ Error saving user filter: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        raise


async def get_active_filters() -> List[UserFilter]:
    """
    Get all active user filters from the database.

    Returns:
        List of UserFilter objects where active=True
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(UserFilter).where(UserFilter.active == True)
            )
            filters = result.scalars().all()
            logger.debug(f"Found {len(filters)} active user filters")
            return list(filters)
    except Exception as e:
        logger.error(f"❌ Error getting active filters: {e}", exc_info=True)
        return []


async def get_user_filters(discord_id: str) -> List[UserFilter]:
    """
    Get all filters for a specific user (by Discord ID).

    Args:
        discord_id: Discord user ID (string)

    Returns:
        List of UserFilter objects for this user
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(UserFilter).where(UserFilter.user_id == discord_id)
                .order_by(UserFilter.created_at.desc())
            )
            filters = result.scalars().all()
            logger.debug(f"Found {len(filters)} filters for user {discord_id}")
            return list(filters)
    except Exception as e:
        logger.error(f"❌ Error getting user filters: {e}", exc_info=True)
        return []


async def get_filter_by_id(filter_id: int) -> Optional[UserFilter]:
    """
    Get a specific filter by ID.

    Args:
        filter_id: Filter ID

    Returns:
        UserFilter object or None if not found
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(UserFilter).where(UserFilter.id == filter_id)
            )
            filter_obj = result.scalar_one_or_none()
            return filter_obj
    except Exception as e:
        logger.error(f"❌ Error getting filter by ID: {e}", exc_info=True)
        return None


async def update_user_filter(filter_id: int, updates: dict) -> Optional[UserFilter]:
    """
    Update a user filter.

    Args:
        filter_id: Filter ID to update
        updates: Dictionary of fields to update

    Returns:
        Updated UserFilter object or None if not found
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            # Get existing filter
            result = await session.execute(
                select(UserFilter).where(UserFilter.id == filter_id)
            )
            filter_obj = result.scalar_one_or_none()

            if not filter_obj:
                logger.warning(f"⚠️  Filter {filter_id} not found")
                return None

            # Update fields
            for key, value in updates.items():
                if hasattr(filter_obj, key):
                    setattr(filter_obj, key, value)

            # Update timestamp
            filter_obj.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(filter_obj)

            logger.debug(f"Updated filter: {filter_id}")
            return filter_obj
    except Exception as e:
        logger.error(f"❌ Error updating filter: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        return None


async def delete_user_filter(filter_id: int) -> bool:
    """
    Delete a user filter.

    Args:
        filter_id: Filter ID to delete

    Returns:
        True if deleted, False if not found or error
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            # Get existing filter
            result = await session.execute(
                select(UserFilter).where(UserFilter.id == filter_id)
            )
            filter_obj = result.scalar_one_or_none()

            if not filter_obj:
                logger.warning(f"⚠️  Filter {filter_id} not found")
                return False

            # Delete filter
            await session.delete(filter_obj)
            await session.commit()

            logger.debug(f"Deleted filter: {filter_id}")
            return True
    except Exception as e:
        logger.error(f"❌ Error deleting filter: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()
        return False


async def get_listings_by_filter(filter_id: Optional[int] = None, discord_id: Optional[str] = None, limit: int = 50) -> List[Listing]:
    """
    Get listings that match a specific filter or all filters for a user.

    Args:
        filter_id: Specific filter ID (optional)
        discord_id: Discord user ID - get listings matching ANY of user's filters (optional)
        limit: Maximum number of listings to return

    Returns:
        List of Listing objects sorted by first_seen DESC

    Note:
        This is a simplified implementation that returns recent listings.
        For production, you'd want to implement proper filter matching logic.
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            # For now, return recent listings
            # TODO: Implement proper filter matching using filter_matcher.py
            result = await session.execute(
                select(Listing)
                .order_by(Listing.first_seen.desc())
                .limit(limit)
            )
            listings = result.scalars().all()
            logger.debug(f"Found {len(listings)} listings")
            return list(listings)
    except Exception as e:
        logger.error(f"❌ Error getting listings by filter: {e}", exc_info=True)
        return []


async def record_alert_sent(listing_id: int, user_id: str, filter_id: int) -> None:
    """
    Record that an alert was sent to a user for a listing.
    This prevents duplicate alerts.
    
    Args:
        listing_id: Listing ID
        user_id: User ID (Discord user ID string)
        filter_id: Filter ID that matched
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        async with _session_factory() as session:
            # Check if alert already exists (shouldn't happen due to unique constraint, but check anyway)
            result = await session.execute(
                select(AlertSent).where(
                    and_(
                        AlertSent.listing_id == listing_id,
                        AlertSent.user_id == user_id
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                logger.debug(f"Alert already recorded for listing {listing_id} and user {user_id}")
                return
            
            # Create new alert record
            alert = AlertSent(
                listing_id=listing_id,
                user_id=user_id,
                filter_id=filter_id
            )
            session.add(alert)
            await session.commit()
            logger.debug(f"✅ Recorded alert sent: listing {listing_id} -> user {user_id} (filter {filter_id})")
    except Exception as e:
        logger.error(f"❌ Error recording alert sent: {e}", exc_info=True)
        if _session_factory:
            async with _session_factory() as session:
                await session.rollback()


async def was_alert_sent(listing_id: int, user_id: str) -> bool:
    """
    Check if an alert was already sent to a user for a listing.
    
    Args:
        listing_id: Listing ID
        user_id: User ID (Discord user ID string)
    
    Returns:
        True if alert was already sent, False otherwise
    """
    if _session_factory is None:
        return False
    
    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(AlertSent).where(
                    and_(
                        AlertSent.listing_id == listing_id,
                        AlertSent.user_id == user_id
                    )
                )
            )
            exists = result.scalar_one_or_none() is not None
            return exists
    except Exception as e:
        logger.error(f"❌ Error checking if alert was sent: {e}", exc_info=True)
        return False


# Backward compatibility: synchronous wrapper for listing_exists
# Note: This only works if database is initialized and will log a warning
# For new code, use await listing_exists() directly
def listing_exists_sync(external_id: str, market: str) -> bool:
    """
    Synchronous wrapper for listing_exists (for backward compatibility).
    ⚠️  WARNING: This is not truly async-safe. Use async listing_exists() in new code.

    For now, this returns False if database isn't ready, which is safe for
    the smart pagination use case (assumes listings don't exist until proven otherwise).
    """
    if _session_factory is None:
        return False

    # Create a new event loop or use existing one
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use run() in a running loop - return False (safe default)
            logger.warning(
                f"⚠️  listing_exists_sync called in async context - use await listing_exists() instead"
            )
            return False
        else:
            return loop.run_until_complete(listing_exists(external_id, market))
    except RuntimeError:
        # No event loop - create one
        return asyncio.run(listing_exists(external_id, market))


async def search_listings_paginated(
    brand: Optional[str] = None,
    min_price_jpy: Optional[int] = None,
    max_price_jpy: Optional[int] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    sort: str = "newest",
    page: int = 1,
    per_page: int = 100
) -> tuple[List[Listing], int]:
    """
    Search all listings with pagination and filtering.

    Args:
        brand: Brand name to search (case-insensitive, partial match)
        min_price_jpy: Minimum price in JPY
        max_price_jpy: Maximum price in JPY
        market: Market filter ("yahoo", "mercari", or None for all)
        category: Category filter ("Jackets", "Tops", "Pants", "Shoes", "Bags", "Accessories", or None for all)
        sort: Sort order ("newest", "oldest", "price_low", "price_high")
        page: Page number (1-indexed)
        per_page: Items per page (max 200)

    Returns:
        Tuple of (listings, total_count)
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            # Build base query
            from sqlalchemy import func
            query = select(Listing)

            # Apply filters
            conditions = []

            if brand:
                # If brand parameter provided (could be single or multiple)
                brands = [b.strip() for b in brand.split('|') if b.strip()]  # Frontend sends "Rick Owens|Raf Simons"
                if brands:  # Only add filter if we have valid brands
                    # OR logic: match any of the selected brands
                    from sqlalchemy import or_
                    brand_filters = [Listing.brand.ilike(f'%{b}%') for b in brands]
                    conditions.append(or_(*brand_filters))

            if min_price_jpy is not None:
                conditions.append(Listing.price_jpy >= min_price_jpy)

            if max_price_jpy is not None:
                conditions.append(Listing.price_jpy <= max_price_jpy)

            if market and market != "all":
                conditions.append(Listing.market == market)

            if category and category != "All":
                conditions.append(Listing.category == category)

            # Apply all conditions
            if conditions:
                query = query.where(and_(*conditions))

            # Apply sorting
            if sort == "newest":
                query = query.order_by(Listing.first_seen.desc())
            elif sort == "oldest":
                query = query.order_by(Listing.first_seen.asc())
            elif sort == "price_low":
                query = query.order_by(Listing.price_jpy.asc())
            elif sort == "price_high":
                query = query.order_by(Listing.price_jpy.desc())
            else:
                # Default to newest
                query = query.order_by(Listing.first_seen.desc())

            # Get total count
            from sqlalchemy import func as sql_func
            count_query = select(sql_func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()

            # Apply pagination
            offset = (page - 1) * per_page
            query = query.offset(offset).limit(per_page)

            # Execute query - handle missing category column gracefully
            try:
                result = await session.execute(query)
                listings = result.scalars().all()
            except Exception as e:
                error_str = str(e)
                if "category" in error_str.lower() and ("does not exist" in error_str or "UndefinedColumnError" in error_str):
                    # Category column doesn't exist - use defer to exclude it
                    logger.warning("⚠️  Category column missing - using workaround")
                    from sqlalchemy.orm import defer
                    # Defer category column so SQLAlchemy doesn't try to load it
                    query = query.options(defer(Listing.category))
                    result = await session.execute(query)
                    listings = result.scalars().all()
                    # Set category to None for all listings
                    for listing in listings:
                        object.__setattr__(listing, 'category', None)
                else:
                    raise

            logger.debug(
                f"Search: brand={brand}, price={min_price_jpy}-{max_price_jpy}, "
                f"market={market}, category={category}, sort={sort}, page={page}/{per_page} -> "
                f"{len(listings)}/{total_count}"
            )

            return list(listings), total_count

    except Exception as e:
        logger.error(f"❌ Error searching listings: {e}", exc_info=True)
        return [], 0


async def get_recent_listings(
    since: datetime,
    brand: Optional[str] = None,
    min_price_jpy: Optional[int] = None,
    max_price_jpy: Optional[int] = None,
    market: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50
) -> List[Listing]:
    """
    Get listings that appeared after a given timestamp, with optional filtering.
    Used for real-time updates in the frontend.

    Args:
        since: Get listings with first_seen after this timestamp
        brand: Brand name to filter (case-insensitive, partial match)
        min_price_jpy: Minimum price in JPY
        max_price_jpy: Maximum price in JPY
        market: Market filter ("yahoo", "mercari", or None for all)
        category: Category filter ("Jackets", "Tops", etc., or None for all)
        limit: Maximum number of listings to return

    Returns:
        List of Listing objects sorted by first_seen DESC (newest first)
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            from sqlalchemy import func

            # Build query
            query = select(Listing).where(Listing.first_seen > since)

            # Apply optional filters
            conditions = []

            if brand:
                # If brand parameter provided (could be single or multiple)
                brands = [b.strip() for b in brand.split('|') if b.strip()]  # Frontend sends "Rick Owens|Raf Simons"
                if brands:  # Only add filter if we have valid brands
                    # OR logic: match any of the selected brands
                    from sqlalchemy import or_
                    brand_filters = [Listing.brand.ilike(f'%{b}%') for b in brands]
                    conditions.append(or_(*brand_filters))

            if min_price_jpy is not None:
                conditions.append(Listing.price_jpy >= min_price_jpy)

            if max_price_jpy is not None:
                conditions.append(Listing.price_jpy <= max_price_jpy)

            if market and market != "all":
                conditions.append(Listing.market == market)

            if category and category != "All":
                conditions.append(Listing.category == category)

            if conditions:
                query = query.where(and_(*conditions))

            # Sort by newest first and limit
            query = query.order_by(Listing.first_seen.desc()).limit(limit)

            # Execute query
            result = await session.execute(query)
            listings = result.scalars().all()

            logger.debug(
                f"Recent listings: since={since}, filters={bool(conditions)} -> {len(listings)} new"
            )

            return list(listings)

    except Exception as e:
        logger.error(f"❌ Error getting recent listings: {e}", exc_info=True)
        return []


async def get_listing_by_id(listing_id: int) -> Optional[Listing]:
    """
    Get a single listing by ID.

    Args:
        listing_id: Listing ID

    Returns:
        Listing object or None if not found
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")

    try:
        async with _session_factory() as session:
            result = await session.execute(
                select(Listing).where(Listing.id == listing_id)
            )
            listing = result.scalar_one_or_none()

            if listing:
                logger.debug(f"Found listing {listing_id}: {listing.title}")
            else:
                logger.debug(f"Listing {listing_id} not found")

            return listing

    except Exception as e:
        logger.error(f"❌ Error getting listing by ID: {e}", exc_info=True)
        return None


async def get_brands_with_counts(limit: int = 30, min_count: int = 5) -> List[Dict[str, any]]:
    """
    Get curated brands with their listing counts, filtered by whitelist.
    Only returns brands from the curated brand list defined in config.
    
    Args:
        limit: Maximum number of brands to return (default: 30, ignored if whitelist is smaller)
        min_count: Minimum listing count to include (default: 5)
    
    Returns:
        List of dictionaries with 'name' and 'count' keys, sorted by count descending
    """
    if _session_factory is None:
        raise ValueError("Database not initialized. Call init_database() first.")
    
    try:
        # Import curated brands from config
        try:
            from config import CURATED_BRANDS
        except ImportError:
            # Fallback if config not available
            CURATED_BRANDS = []
        
        if not CURATED_BRANDS:
            logger.warning("⚠️  No curated brands found in config, returning empty list")
            return []
        
        async with _session_factory() as session:
            from sqlalchemy import func, case
            
            # For each curated brand, count how many listings match it
            # Match if database brand contains curated brand name (case-insensitive)
            brands_with_counts = []
            
            for curated_brand in CURATED_BRANDS:
                curated_lower = curated_brand.lower()
                
                # Count listings where brand field contains the curated brand name
                count_query = (
                    select(func.count(Listing.id))
                    .where(Listing.brand.isnot(None))
                    .where(Listing.brand != '')
                    .where(func.lower(Listing.brand).like(f"%{curated_lower}%"))
                )
                
                result = await session.execute(count_query)
                count = result.scalar() or 0
                
                # Only include if count meets minimum threshold
                if count >= min_count:
                    brands_with_counts.append({
                        "name": curated_brand,
                        "count": count
                    })
            
            # Sort by count descending
            brands_with_counts.sort(key=lambda x: x["count"], reverse=True)
            
            # Apply limit
            if limit:
                brands_with_counts = brands_with_counts[:limit]
            
            logger.debug(f"Brands: {len(brands_with_counts)} (from {len(CURATED_BRANDS)} whitelist)")
            return brands_with_counts
    
    except Exception as e:
        logger.error(f"❌ Error getting brands: {e}", exc_info=True)
        return []
