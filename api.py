"""
FastAPI web server for SwagSearch v2 Dashboard

Exposes HTTP endpoints for the dashboard to interact with the database.
Provides CRUD operations for user filters and retrieves listings.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import json

# Import database functions
from database import (
    get_user_filters,
    save_user_filter,
    delete_user_filter,
    get_listings_by_filter,
    listing_exists,
    init_database,
    create_tables,
    get_filter_by_id,
    update_user_filter,
)

# Import models
from models import UserFilter, Listing

# Import config
from config import get_database_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="SwagSearch v2 API",
    description="Fashion arbitrage dashboard API",
    version="2.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


# Pydantic models for request/response validation
class HealthResponse(BaseModel):
    status: str
    timestamp: str


class FilterCreate(BaseModel):
    discord_id: str = Field(..., min_length=1, description="Discord user ID")
    name: str = Field(..., min_length=1, max_length=100, description="Filter name")
    brands: Optional[List[str]] = Field(default=None, description="List of brand names")
    keywords: Optional[List[str]] = Field(default=None, description="List of keywords")
    min_price: Optional[float] = Field(default=None, ge=0, description="Minimum price in JPY")
    max_price: Optional[float] = Field(default=None, ge=0, description="Maximum price in JPY")
    markets: List[str] = Field(..., min_items=1, description="List of markets (yahoo, mercari)")
    active: bool = Field(default=True, description="Whether filter is active")

    @field_validator('markets')
    @classmethod
    def validate_markets(cls, v):
        valid_markets = ['yahoo', 'mercari']
        for market in v:
            if market.lower() not in valid_markets:
                raise ValueError(f"Invalid market: {market}. Must be one of {valid_markets}")
        return [m.lower() for m in v]

    @field_validator('max_price')
    @classmethod
    def validate_price_range(cls, v, info):
        if v is not None and info.data.get('min_price') is not None:
            if v < info.data['min_price']:
                raise ValueError("max_price must be greater than or equal to min_price")
        return v


class FilterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    brands: Optional[List[str]] = Field(default=None)
    keywords: Optional[List[str]] = Field(default=None)
    min_price: Optional[float] = Field(default=None, ge=0)
    max_price: Optional[float] = Field(default=None, ge=0)
    markets: Optional[List[str]] = Field(default=None, min_items=1)
    active: Optional[bool] = Field(default=None)

    @field_validator('markets')
    @classmethod
    def validate_markets(cls, v):
        if v is not None:
            valid_markets = ['yahoo', 'mercari']
            for market in v:
                if market.lower() not in valid_markets:
                    raise ValueError(f"Invalid market: {market}. Must be one of {valid_markets}")
            return [m.lower() for m in v]
        return v


class FilterResponse(BaseModel):
    id: int
    discord_id: str
    name: str
    brands: Optional[List[str]]
    keywords: Optional[List[str]]
    min_price: Optional[float]
    max_price: Optional[float]
    markets: List[str]
    active: bool
    created_at: str
    updated_at: str

    @classmethod
    def from_orm(cls, filter_obj: UserFilter) -> "FilterResponse":
        """Convert SQLAlchemy UserFilter to Pydantic model"""
        # Parse JSON fields
        brands = json.loads(filter_obj.brands) if filter_obj.brands else None
        keywords = json.loads(filter_obj.keywords) if filter_obj.keywords else None
        markets = filter_obj.markets.split(',') if filter_obj.markets else []

        return cls(
            id=filter_obj.id,
            discord_id=filter_obj.user_id,
            name=filter_obj.name,
            brands=brands,
            keywords=keywords,
            min_price=filter_obj.price_min,
            max_price=filter_obj.price_max,
            markets=markets,
            active=filter_obj.active,
            created_at=filter_obj.created_at.isoformat(),
            updated_at=filter_obj.updated_at.isoformat(),
        )


class ListingResponse(BaseModel):
    id: int
    market: str
    external_id: str
    title: str
    price_jpy: int
    brand: Optional[str]
    url: str
    image_url: Optional[str]
    listing_type: str
    seller_id: Optional[str]
    first_seen: str
    last_seen: str

    @classmethod
    def from_orm(cls, listing: Listing) -> "ListingResponse":
        """Convert SQLAlchemy Listing to Pydantic model"""
        return cls(
            id=listing.id,
            market=listing.market,
            external_id=listing.external_id,
            title=listing.title,
            price_jpy=listing.price_jpy,
            brand=listing.brand,
            url=listing.url,
            image_url=listing.image_url,
            listing_type=listing.listing_type,
            seller_id=listing.seller_id,
            first_seen=listing.first_seen.isoformat(),
            last_seen=listing.last_seen.isoformat(),
        )


class DeleteResponse(BaseModel):
    success: bool
    deleted_id: int


# Startup event
@app.on_event("startup")
async def startup():
    """Initialize database connection on startup"""
    try:
        database_url = get_database_url()
        if not database_url:
            logger.warning("⚠️  No DATABASE_URL found, using SQLite for testing")

        logger.info("🚀 Initializing database connection...")
        init_database(database_url)
        await create_tables()
        logger.info("✅ FastAPI started, database ready")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}", exc_info=True)
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown"""
    logger.info("👋 FastAPI shutting down...")


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        Status and timestamp
    """
    logger.info("GET /api/health")
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@app.get("/api/filters", response_model=List[FilterResponse])
async def get_filters(
    discord_id: str = Query(..., description="Discord user ID")
):
    """
    Get all filters for a specific user

    Args:
        discord_id: Discord user ID (required query param)

    Returns:
        List of user filters
    """
    logger.info(f"GET /api/filters?discord_id={discord_id}")

    try:
        filters = await get_user_filters(discord_id)
        return [FilterResponse.from_orm(f) for f in filters]
    except Exception as e:
        logger.error(f"❌ Error getting filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/filters", response_model=FilterResponse, status_code=201)
async def create_filter(filter_data: FilterCreate):
    """
    Create a new user filter

    Args:
        filter_data: Filter creation data

    Returns:
        Created filter with ID
    """
    logger.info(f"POST /api/filters - Creating filter for user {filter_data.discord_id}")

    try:
        # Convert Pydantic model to SQLAlchemy model
        user_filter = UserFilter(
            user_id=filter_data.discord_id,
            name=filter_data.name,
            brands=json.dumps(filter_data.brands) if filter_data.brands else None,
            keywords=json.dumps(filter_data.keywords) if filter_data.keywords else None,
            price_min=filter_data.min_price,
            price_max=filter_data.max_price,
            markets=','.join(filter_data.markets),
            active=filter_data.active,
        )

        # Save to database
        filter_id = await save_user_filter(user_filter)

        # Retrieve the saved filter to return full object
        saved_filter = await get_filter_by_id(filter_id)
        if not saved_filter:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved filter")

        logger.info(f"✅ Created filter {filter_id} for user {filter_data.discord_id}")
        return FilterResponse.from_orm(saved_filter)

    except ValueError as e:
        logger.warning(f"⚠️  Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Error creating filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.put("/api/filters/{filter_id}", response_model=FilterResponse)
async def update_filter(
    filter_id: int,
    filter_data: FilterUpdate,
    discord_id: str = Query(..., description="Discord user ID for ownership verification")
):
    """
    Update an existing filter

    Args:
        filter_id: Filter ID to update
        filter_data: Fields to update
        discord_id: Discord user ID for ownership verification

    Returns:
        Updated filter object
    """
    logger.info(f"PUT /api/filters/{filter_id} - User {discord_id}")

    try:
        # Check if filter exists and belongs to user
        existing_filter = await get_filter_by_id(filter_id)
        if not existing_filter:
            raise HTTPException(status_code=404, detail=f"Filter {filter_id} not found")

        if existing_filter.user_id != discord_id:
            logger.warning(f"⚠️  User {discord_id} attempted to update filter {filter_id} owned by {existing_filter.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to update this filter")

        # Build updates dict (only include non-None fields)
        updates = {}
        if filter_data.name is not None:
            updates['name'] = filter_data.name
        if filter_data.brands is not None:
            updates['brands'] = json.dumps(filter_data.brands)
        if filter_data.keywords is not None:
            updates['keywords'] = json.dumps(filter_data.keywords)
        if filter_data.min_price is not None:
            updates['price_min'] = filter_data.min_price
        if filter_data.max_price is not None:
            updates['price_max'] = filter_data.max_price
        if filter_data.markets is not None:
            updates['markets'] = ','.join(filter_data.markets)
        if filter_data.active is not None:
            updates['active'] = filter_data.active

        # Update filter
        updated_filter = await update_user_filter(filter_id, updates)
        if not updated_filter:
            raise HTTPException(status_code=500, detail="Failed to update filter")

        logger.info(f"✅ Updated filter {filter_id}")
        return FilterResponse.from_orm(updated_filter)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/api/filters/{filter_id}", response_model=DeleteResponse)
async def delete_filter(
    filter_id: int,
    discord_id: str = Query(..., description="Discord user ID for ownership verification")
):
    """
    Delete a filter

    Args:
        filter_id: Filter ID to delete
        discord_id: Discord user ID for ownership verification

    Returns:
        Success status and deleted ID
    """
    logger.info(f"DELETE /api/filters/{filter_id} - User {discord_id}")

    try:
        # Check if filter exists and belongs to user
        existing_filter = await get_filter_by_id(filter_id)
        if not existing_filter:
            raise HTTPException(status_code=404, detail=f"Filter {filter_id} not found")

        if existing_filter.user_id != discord_id:
            logger.warning(f"⚠️  User {discord_id} attempted to delete filter {filter_id} owned by {existing_filter.user_id}")
            raise HTTPException(status_code=403, detail="You don't have permission to delete this filter")

        # Delete filter
        success = await delete_user_filter(filter_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete filter")

        logger.info(f"✅ Deleted filter {filter_id}")
        return DeleteResponse(success=True, deleted_id=filter_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting filter: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/feed", response_model=List[ListingResponse])
async def get_feed(
    discord_id: str = Query(..., description="Discord user ID"),
    filter_id: Optional[int] = Query(None, description="Specific filter ID (optional)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of listings to return")
):
    """
    Get listings feed for a user

    If filter_id is provided, returns listings matching that specific filter.
    If no filter_id, returns listings matching ANY of the user's filters.

    Args:
        discord_id: Discord user ID (required)
        filter_id: Specific filter ID (optional)
        limit: Maximum number of listings (default 50, max 500)

    Returns:
        List of listings sorted by first_seen DESC
    """
    logger.info(f"GET /api/feed?discord_id={discord_id}&filter_id={filter_id}&limit={limit}")

    try:
        # Get listings
        listings = await get_listings_by_filter(
            filter_id=filter_id,
            discord_id=discord_id,
            limit=limit
        )

        logger.info(f"✅ Returning {len(listings)} listings")
        return [ListingResponse.from_orm(listing) for listing in listings]

    except Exception as e:
        logger.error(f"❌ Error getting feed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "SwagSearch v2 API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "filters": "/api/filters",
            "feed": "/api/feed",
        },
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
