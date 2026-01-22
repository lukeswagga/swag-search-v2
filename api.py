"""
FastAPI Web Server for SwagSearch v2
Exposes HTTP endpoints for the Next.js dashboard
"""

from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging
import json

# Import existing database functions
from database import (
    init_database,
    create_tables,
    get_user_filters,
    save_user_filter,
    delete_user_filter,
    get_listings_since,
    search_listings_paginated,
    get_recent_listings,
    get_listing_by_id,
)
from models import UserFilter, Listing
from config import get_database_url
from currency import usd_to_jpy, jpy_to_usd

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="SwagSearch API", version="2.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",  # Matches all Vercel domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Pydantic models for request/response
class FilterCreate(BaseModel):
    discord_id: str
    name: str
    brands: List[str]
    price_min_usd: Optional[float] = None  # Accept USD prices (NEW)
    price_max_usd: Optional[float] = None  # Accept USD prices (NEW)
    markets: List[str]

class FilterResponse(BaseModel):
    id: int
    user_id: str
    name: str
    brands: List[str]
    price_min: int  # JPY (stored in database)
    price_max: int  # JPY (stored in database)
    price_min_usd: float  # USD (for display)
    price_max_usd: float  # USD (for display)
    markets: List[str]
    active: bool

class ListingResponse(BaseModel):
    id: int
    external_id: str
    market: str
    title: str
    brand: str
    price_jpy: int
    price_usd: float
    image_url: Optional[str]
    listing_url: str
    first_seen: datetime

class PaginationMetadata(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool

class SearchParams(BaseModel):
    brand: Optional[str] = None
    min_price_usd: Optional[float] = None
    max_price_usd: Optional[float] = None
    market: Optional[str] = None

class SearchResponse(BaseModel):
    listings: List[ListingResponse]
    pagination: PaginationMetadata
    search_params: SearchParams

class RecentListingsResponse(BaseModel):
    listings: List[ListingResponse]
    count: int
    latest_timestamp: Optional[str] = None

# Startup event - initialize database
@app.on_event("startup")
async def startup():
    """Initialize database connection on startup"""
    try:
        db_url = get_database_url()
        if not db_url:
            logger.warning("⚠️  No DATABASE_URL found, using SQLite for testing")
            db_url = "sqlite+aiosqlite:///./test.db"
        
        logger.info(f"🔧 Initializing database...")
        init_database(db_url)
        await create_tables()
        logger.info("✅ FastAPI started, database ready")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Check if API is running"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "SwagSearch API v2"
    }

# Get user's filters
@app.get("/api/filters")
async def get_filters(discord_id: str = Query(..., description="Discord user ID")):
    """Get all filters for a user"""
    try:
        filters = await get_user_filters(discord_id)
        
        # Convert to response format
        response = []
        for f in filters:
            # Convert brands from JSON string to list
            brands = json.loads(f.brands) if f.brands else []
            # Convert markets from comma-separated string to list
            markets = f.markets.split(',') if f.markets else []
            markets = [m.strip() for m in markets if m.strip()]  # Clean up whitespace
            
            response.append({
                "id": f.id,
                "user_id": f.user_id,
                "name": f.name,
                "brands": brands,
                "price_min": f.price_min,  # JPY
                "price_max": f.price_max,  # JPY
                "price_min_usd": jpy_to_usd(f.price_min) if f.price_min else 0.0,  # USD
                "price_max_usd": jpy_to_usd(f.price_max) if f.price_max else jpy_to_usd(999999),  # USD
                "markets": markets,
                "active": f.active
            })
        
        logger.info(f"✅ Retrieved {len(response)} filters for user {discord_id}")
        return response
    
    except Exception as e:
        logger.error(f"❌ Error getting filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Create new filter
@app.post("/api/filters")
async def create_filter(filter_data: FilterCreate):
    """Create a new filter for a user"""
    try:
        # Validate
        if not filter_data.name:
            raise HTTPException(status_code=400, detail="Filter name is required")
        if not filter_data.markets:
            raise HTTPException(status_code=400, detail="At least one market is required")
        
        # Create UserFilter object
        # Convert brands list to JSON string
        brands_json = json.dumps(filter_data.brands) if filter_data.brands else None
        # Convert markets list to comma-separated string
        markets_str = ','.join(filter_data.markets) if filter_data.markets else None

        # Convert USD prices to JPY for storage
        price_min_jpy = usd_to_jpy(filter_data.price_min_usd) if filter_data.price_min_usd is not None else 0
        price_max_jpy = usd_to_jpy(filter_data.price_max_usd) if filter_data.price_max_usd is not None else 999999

        user_filter = UserFilter(
            user_id=filter_data.discord_id,
            name=filter_data.name,
            brands=brands_json,
            price_min=price_min_jpy,
            price_max=price_max_jpy,
            markets=markets_str,
            active=True
        )
        
        # Save to database
        filter_id = await save_user_filter(user_filter)
        
        # Return created filter (convert back to lists for API response)
        brands = json.loads(user_filter.brands) if user_filter.brands else []
        markets = user_filter.markets.split(',') if user_filter.markets else []
        markets = [m.strip() for m in markets if m.strip()]

        response = {
            "id": filter_id,
            "user_id": user_filter.user_id,
            "name": user_filter.name,
            "brands": brands,
            "price_min": user_filter.price_min,  # JPY
            "price_max": user_filter.price_max,  # JPY
            "price_min_usd": jpy_to_usd(user_filter.price_min),  # USD
            "price_max_usd": jpy_to_usd(user_filter.price_max),  # USD
            "markets": markets,
            "active": user_filter.active
        }
        
        logger.info(f"✅ Created filter '{filter_data.name}' (ID: {filter_id}) for user {filter_data.discord_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Update filter
@app.put("/api/filters/{filter_id}")
async def update_filter(filter_id: int, filter_data: FilterCreate):
    """Update an existing filter"""
    try:
        # Get existing filter to verify ownership
        filters = await get_user_filters(filter_data.discord_id)
        existing = next((f for f in filters if f.id == filter_id), None)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Filter not found or doesn't belong to user")
        
        # Update fields
        # Convert brands list to JSON string
        brands_json = json.dumps(filter_data.brands) if filter_data.brands else None
        # Convert markets list to comma-separated string
        markets_str = ','.join(filter_data.markets) if filter_data.markets else None

        # Convert USD prices to JPY for storage
        price_min_jpy = usd_to_jpy(filter_data.price_min_usd) if filter_data.price_min_usd is not None else 0
        price_max_jpy = usd_to_jpy(filter_data.price_max_usd) if filter_data.price_max_usd is not None else 999999

        existing.name = filter_data.name
        existing.brands = brands_json
        existing.price_min = price_min_jpy
        existing.price_max = price_max_jpy
        existing.markets = markets_str
        
        # Save
        await save_user_filter(existing)
        
        # Convert back to lists for API response
        brands = json.loads(existing.brands) if existing.brands else []
        markets = existing.markets.split(',') if existing.markets else []
        markets = [m.strip() for m in markets if m.strip()]

        response = {
            "id": existing.id,
            "user_id": existing.user_id,
            "name": existing.name,
            "brands": brands,
            "price_min": existing.price_min,  # JPY
            "price_max": existing.price_max,  # JPY
            "price_min_usd": jpy_to_usd(existing.price_min),  # USD
            "price_max_usd": jpy_to_usd(existing.price_max),  # USD
            "markets": markets,
            "active": existing.active
        }
        
        logger.info(f"✅ Updated filter {filter_id} for user {filter_data.discord_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Delete filter
@app.delete("/api/filters/{filter_id}")
async def delete_filter(filter_id: int, discord_id: str = Query(...)):
    """Delete a filter"""
    try:
        # Verify ownership
        filters = await get_user_filters(discord_id)
        existing = next((f for f in filters if f.id == filter_id), None)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Filter not found or doesn't belong to user")
        
        # Delete
        await delete_user_filter(filter_id)
        
        logger.info(f"✅ Deleted filter {filter_id} for user {discord_id}")
        return {"success": True, "deleted_id": filter_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Get feed (listings matched to user's filters)
@app.get("/api/feed")
async def get_feed(
    discord_id: str = Query(...),
    filter_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    """Get listings that match user's filters"""
    try:
        # Get user's filters
        filters = await get_user_filters(discord_id)
        
        if not filters:
            return []
        
        # If specific filter requested, use only that one
        if filter_id:
            filters = [f for f in filters if f.id == filter_id]
            if not filters:
                raise HTTPException(status_code=404, detail="Filter not found")
        
        # Get recent listings (last 24 hours for now)
        from datetime import timedelta
        since = datetime.utcnow() - timedelta(days=1)
        all_listings = await get_listings_since(since)
        
        # Filter listings that match user's filter criteria
        matched_listings = []
        for listing in all_listings:
            for user_filter in filters:
                # Parse brands from JSON string
                brands = json.loads(user_filter.brands) if user_filter.brands else []
                
                # Check brand match
                brand_match = False
                if "*" in brands:
                    brand_match = True
                else:
                    for brand in brands:
                        if brand.lower() in listing.brand.lower() if listing.brand else False:
                            brand_match = True
                            break
                
                # Check price range (handle None values)
                price_min = user_filter.price_min if user_filter.price_min is not None else 0
                price_max = user_filter.price_max if user_filter.price_max is not None else 999999
                price_match = (price_min <= listing.price_jpy <= price_max)
                
                # Parse markets from comma-separated string and check match
                markets = user_filter.markets.split(',') if user_filter.markets else []
                markets = [m.strip().lower() for m in markets if m.strip()]
                market_match = listing.market.lower() in markets if listing.market else False
                
                # If all match, include this listing
                if brand_match and price_match and market_match:
                    matched_listings.append(listing)
                    break  # Don't add same listing twice if it matches multiple filters
        
        # Sort by newest first and limit
        matched_listings.sort(key=lambda x: x.first_seen, reverse=True)
        matched_listings = matched_listings[:limit]
        
        # Convert to response format
        # Rough JPY to USD conversion rate (1 USD ≈ 147 JPY)
        JPY_TO_USD_RATE = 147.0
        response = []
        for listing in matched_listings:
            response.append({
                "id": listing.id,
                "external_id": listing.external_id,
                "market": listing.market,
                "title": listing.title,
                "brand": listing.brand,
                "price_jpy": listing.price_jpy,
                "price_usd": listing.price_jpy / JPY_TO_USD_RATE if listing.price_jpy else 0.0,
                "image_url": listing.image_url,
                "listing_url": listing.url,
                "first_seen": listing.first_seen.isoformat()
            })
        
        logger.info(f"✅ Retrieved {len(response)} listings for user {discord_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Search all listings with pagination (NEW - historical search)
@app.get("/api/feed/search")
async def search_feed(
    discord_id: str = Query(..., description="Discord user ID for context"),
    brand: Optional[str] = Query(None, description="Brand name to search (case-insensitive)"),
    min_price_usd: Optional[float] = Query(None, ge=0, description="Minimum price in USD"),
    max_price_usd: Optional[float] = Query(None, ge=0, description="Maximum price in USD"),
    market: str = Query("all", description="Market filter: 'all', 'yahoo', or 'mercari'"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=200, description="Items per page (max 200)"),
    sort: str = Query("newest", description="Sort order: 'newest', 'oldest', 'price_low', 'price_high'")
):
    """
    Search ALL historical listings with advanced filtering and pagination.
    This is the main search endpoint that replaces the limited /api/feed.
    """
    try:
        # Convert USD prices to JPY for database query
        min_price_jpy = usd_to_jpy(min_price_usd) if min_price_usd is not None else None
        max_price_jpy = usd_to_jpy(max_price_usd) if max_price_usd is not None else None

        # Validate sort parameter
        valid_sorts = ["newest", "oldest", "price_low", "price_high"]
        if sort not in valid_sorts:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort parameter. Must be one of: {', '.join(valid_sorts)}"
            )

        # Validate market parameter
        valid_markets = ["all", "yahoo", "mercari"]
        if market not in valid_markets:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid market parameter. Must be one of: {', '.join(valid_markets)}"
            )

        # Query database
        listings, total_count = await search_listings_paginated(
            brand=brand,
            min_price_jpy=min_price_jpy,
            max_price_jpy=max_price_jpy,
            market=market if market != "all" else None,
            sort=sort,
            page=page,
            per_page=per_page
        )

        # Calculate pagination metadata
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        has_next = page < total_pages
        has_prev = page > 1

        # Convert to response format
        listing_responses = []
        for listing in listings:
            listing_responses.append({
                "id": listing.id,
                "external_id": listing.external_id,
                "market": listing.market,
                "title": listing.title,
                "brand": listing.brand or "",
                "price_jpy": listing.price_jpy,
                "price_usd": jpy_to_usd(listing.price_jpy),
                "image_url": listing.image_url,
                "listing_url": listing.url,
                "first_seen": listing.first_seen.isoformat()
            })

        # Build response
        response = {
            "listings": listing_responses,
            "pagination": {
                "total": total_count,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "search_params": {
                "brand": brand,
                "min_price_usd": min_price_usd,
                "max_price_usd": max_price_usd,
                "market": market
            }
        }

        logger.info(
            f"✅ Search completed for user {discord_id}: "
            f"{len(listing_responses)} of {total_count} results "
            f"(page {page}/{total_pages})"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in search endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Get recent listings for real-time updates (NEW - polling endpoint)
@app.get("/api/feed/recent")
async def get_recent_feed(
    discord_id: str = Query(..., description="Discord user ID"),
    since: str = Query(..., description="ISO timestamp - only return listings after this"),
    brand: Optional[str] = Query(None, description="Brand name filter"),
    min_price_usd: Optional[float] = Query(None, ge=0, description="Minimum price in USD"),
    max_price_usd: Optional[float] = Query(None, ge=0, description="Maximum price in USD"),
    market: Optional[str] = Query("all", description="Market filter"),
    limit: int = Query(50, ge=1, le=200, description="Maximum items to return")
):
    """
    Get listings that appeared after a given timestamp.
    Frontend polls this endpoint every 30 seconds to get new listings.
    """
    try:
        # Parse timestamp
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid timestamp format. Use ISO 8601 format (e.g., '2026-01-22T10:30:00Z')"
            )

        # Convert USD prices to JPY
        min_price_jpy = usd_to_jpy(min_price_usd) if min_price_usd is not None else None
        max_price_jpy = usd_to_jpy(max_price_usd) if max_price_usd is not None else None

        # Query database for recent listings
        listings = await get_recent_listings(
            since=since_dt,
            brand=brand,
            min_price_jpy=min_price_jpy,
            max_price_jpy=max_price_jpy,
            market=market if market != "all" else None,
            limit=limit
        )

        # Convert to response format
        listing_responses = []
        latest_timestamp = None

        for listing in listings:
            listing_responses.append({
                "id": listing.id,
                "external_id": listing.external_id,
                "market": listing.market,
                "title": listing.title,
                "brand": listing.brand or "",
                "price_jpy": listing.price_jpy,
                "price_usd": jpy_to_usd(listing.price_jpy),
                "image_url": listing.image_url,
                "listing_url": listing.url,
                "first_seen": listing.first_seen.isoformat()
            })

            # Track latest timestamp
            if latest_timestamp is None or listing.first_seen > latest_timestamp:
                latest_timestamp = listing.first_seen

        response = {
            "listings": listing_responses,
            "count": len(listing_responses),
            "latest_timestamp": latest_timestamp.isoformat() if latest_timestamp else None
        }

        logger.info(
            f"✅ Recent listings for user {discord_id}: "
            f"{len(listing_responses)} new listings since {since}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in recent feed endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Get single listing detail (NEW - detail view)
@app.get("/api/listings/{listing_id}")
async def get_listing_detail(
    listing_id: int = Path(..., description="Listing ID")
):
    """
    Get detailed information for a single listing.
    Used for detail modal/page view.
    """
    try:
        # Query database
        listing = await get_listing_by_id(listing_id)

        if not listing:
            raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")

        # Convert to response format
        response = {
            "id": listing.id,
            "external_id": listing.external_id,
            "market": listing.market,
            "title": listing.title,
            "brand": listing.brand or "",
            "price_jpy": listing.price_jpy,
            "price_usd": jpy_to_usd(listing.price_jpy),
            "image_url": listing.image_url,
            "listing_url": listing.url,
            "first_seen": listing.first_seen.isoformat(),
            "last_seen": listing.last_seen.isoformat(),
            "seller_id": listing.seller_id,
            "listing_type": listing.listing_type
        }

        logger.info(f"✅ Retrieved listing {listing_id}: {listing.title}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting listing detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Root endpoint
@app.get("/")
async def root():
    """API root"""
    return {
        "service": "SwagSearch API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "filters": "/api/filters",
            "feed": "/api/feed",
            "search": "/api/feed/search",
            "recent": "/api/feed/recent",
            "listing_detail": "/api/listings/{id}"
        }
    }
