"""
FastAPI Web Server for SwagSearch v2
Exposes HTTP endpoints for the Next.js dashboard
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

# Import existing database functions
from database import (
    init_database,
    create_tables,
    get_user_filters,
    save_user_filter,
    delete_user_filter,
    get_listings_since,
)
from models import UserFilter, Listing
from config import get_database_url

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
    min_price: int = 0
    max_price: int = 999999
    markets: List[str]

class FilterResponse(BaseModel):
    id: int
    user_id: str
    name: str
    brands: List[str]
    min_price: int
    max_price: int
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
            response.append({
                "id": f.id,
                "user_id": f.user_id,
                "name": f.name,
                "brands": f.brands,
                "min_price": f.min_price,
                "max_price": f.max_price,
                "markets": f.markets,
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
        user_filter = UserFilter(
            user_id=filter_data.discord_id,
            name=filter_data.name,
            brands=filter_data.brands,
            min_price=filter_data.min_price,
            max_price=filter_data.max_price,
            markets=filter_data.markets,
            active=True
        )
        
        # Save to database
        filter_id = await save_user_filter(user_filter)
        
        # Return created filter
        response = {
            "id": filter_id,
            "user_id": user_filter.user_id,
            "name": user_filter.name,
            "brands": user_filter.brands,
            "min_price": user_filter.min_price,
            "max_price": user_filter.max_price,
            "markets": user_filter.markets,
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
        existing.name = filter_data.name
        existing.brands = filter_data.brands
        existing.min_price = filter_data.min_price
        existing.max_price = filter_data.max_price
        existing.markets = filter_data.markets
        
        # Save
        await save_user_filter(existing)
        
        response = {
            "id": existing.id,
            "user_id": existing.user_id,
            "name": existing.name,
            "brands": existing.brands,
            "min_price": existing.min_price,
            "max_price": existing.max_price,
            "markets": existing.markets,
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
                # Check brand match
                brand_match = False
                if "*" in user_filter.brands:
                    brand_match = True
                else:
                    for brand in user_filter.brands:
                        if brand.lower() in listing.brand.lower():
                            brand_match = True
                            break
                
                # Check price range
                price_match = (
                    user_filter.min_price <= listing.price_jpy <= user_filter.max_price
                )
                
                # Check market
                market_match = listing.market in user_filter.markets
                
                # If all match, include this listing
                if brand_match and price_match and market_match:
                    matched_listings.append(listing)
                    break  # Don't add same listing twice if it matches multiple filters
        
        # Sort by newest first and limit
        matched_listings.sort(key=lambda x: x.first_seen, reverse=True)
        matched_listings = matched_listings[:limit]
        
        # Convert to response format
        response = []
        for listing in matched_listings:
            response.append({
                "id": listing.id,
                "external_id": listing.external_id,
                "market": listing.market,
                "title": listing.title,
                "brand": listing.brand,
                "price_jpy": listing.price_jpy,
                "price_usd": listing.price_usd,
                "image_url": listing.image_url,
                "listing_url": listing.listing_url,
                "first_seen": listing.first_seen.isoformat()
            })
        
        logger.info(f"✅ Retrieved {len(response)} listings for user {discord_id}")
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting feed: {e}", exc_info=True)
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
            "feed": "/api/feed"
        }
    }
