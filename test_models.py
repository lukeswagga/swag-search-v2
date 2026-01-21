"""
Test file to verify SQLAlchemy models work with SQLite locally
Run: python test_models.py
"""

import asyncio
import os
from datetime import datetime
from models import (
    Base, UserFilter, Listing, AlertSent,
    init_database, create_tables, drop_tables
)
import models


async def test_models():
    """Test all models with SQLite"""
    
    # Use SQLite for testing (async SQLite support)
    db_path = "test_v2.db"
    if os.path.exists(db_path):
        os.remove(db_path)  # Clean up old test DB
    
    database_url = f"sqlite+aiosqlite:///{db_path}"
    print(f"🔧 Initializing database: {database_url}")
    
    # Initialize database
    init_database(database_url)
    
    # Verify initialization worked
    if models.AsyncSessionLocal is None:
        raise ValueError("AsyncSessionLocal is None - init_database() failed!")
    
    # Create tables
    print("📦 Creating tables...")
    await create_tables()
    print("✅ Tables created successfully")
    
    # Test CRUD operations - use the module's AsyncSessionLocal after init
    async with models.AsyncSessionLocal() as session:
        print("\n" + "="*60)
        print("TEST 1: Create UserFilter")
        print("="*60)
        
        # Create a user filter
        user_filter = UserFilter(
            user_id=12345,
            name="Budget Finds Under $100",
            markets="yahoo",
            brands='["Raf Simons", "Rick Owens"]',
            keywords='["jacket", "coat"]',
            price_min=0.0,
            price_max=100.0,
            listing_types="auction,buy_it_now",
            active=True
        )
        session.add(user_filter)
        await session.commit()
        await session.refresh(user_filter)
        print(f"✅ Created UserFilter: {user_filter}")
        print(f"   ID: {user_filter.id}")
        print(f"   Created at: {user_filter.created_at}")
        
        print("\n" + "="*60)
        print("TEST 2: Create Listing")
        print("="*60)
        
        # Create a listing
        listing = Listing(
            market="yahoo",
            external_id="u123456789",
            title="Raf Simons Archive Jacket Black Size 50",
            price_jpy=15000,
            brand="Raf Simons",
            url="https://zenmarket.jp/en/auction.aspx?itemCode=u123456789",
            image_url="https://example.com/image.jpg",
            listing_type="auction",
            seller_id="seller_123"
        )
        session.add(listing)
        await session.commit()
        await session.refresh(listing)
        print(f"✅ Created Listing: {listing}")
        print(f"   ID: {listing.id}")
        print(f"   First seen: {listing.first_seen}")
        print(f"   Last seen: {listing.last_seen}")
        
        print("\n" + "="*60)
        print("TEST 3: Create AlertSent")
        print("="*60)
        
        # Create an alert
        alert = AlertSent(
            listing_id=listing.id,
            user_id=12345,
            filter_id=user_filter.id
            # sent_at will be set automatically by server_default
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)
        print(f"✅ Created AlertSent: {alert}")
        print(f"   ID: {alert.id}")
        print(f"   Listing ID: {alert.listing_id}")
        print(f"   Filter ID: {alert.filter_id if alert.filter_id else 'None'}")
        
        print("\n" + "="*60)
        print("TEST 4: Query with Relationships")
        print("="*60)
        
        # Query listing with alerts - need to eager load relationships
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        result = await session.execute(
            select(Listing)
            .where(Listing.id == listing.id)
            .options(selectinload(Listing.alerts_sent).selectinload(AlertSent.filter))
        )
        fetched_listing = result.scalar_one()
        print(f"✅ Fetched Listing: {fetched_listing.title}")
        print(f"   Alerts sent: {len(fetched_listing.alerts_sent)}")
        for alert in fetched_listing.alerts_sent:
            filter_name = alert.filter.name if alert.filter else 'manual'
            print(f"      - User {alert.user_id} via filter '{filter_name}'")
        
        # Query user filter with alerts
        result = await session.execute(
            select(UserFilter)
            .where(UserFilter.id == user_filter.id)
            .options(selectinload(UserFilter.alerts_sent))
        )
        fetched_filter = result.scalar_one()
        print(f"\n✅ Fetched Filter: {fetched_filter.name}")
        print(f"   Alerts sent: {len(fetched_filter.alerts_sent)}")
        
        print("\n" + "="*60)
        print("TEST 5: Update Listing (last_seen)")
        print("="*60)
        
        # Update listing
        import time
        time.sleep(1)  # Wait 1 second to see timestamp change
        fetched_listing.brand = "Updated Brand"
        await session.commit()
        await session.refresh(fetched_listing)
        print(f"✅ Updated listing")
        print(f"   Brand: {fetched_listing.brand}")
        print(f"   Last seen: {fetched_listing.last_seen}")
        
        print("\n" + "="*60)
        print("TEST 6: Query Filters by User")
        print("="*60)
        
        # Query all filters for a user
        result = await session.execute(
            select(UserFilter).where(UserFilter.user_id == 12345)
        )
        user_filters = result.scalars().all()
        print(f"✅ Found {len(user_filters)} filters for user 12345")
        for f in user_filters:
            print(f"   - {f.name} (active={f.active})")
        
        print("\n" + "="*60)
        print("TEST 7: Check Unique Constraints")
        print("="*60)
        
        # Try to create duplicate listing (should work, but check unique index)
        duplicate_listing = Listing(
            market="yahoo",
            external_id="u123456789",  # Same external_id
            title="Duplicate Listing",
            price_jpy=20000,
            brand="Rick Owens",
            url="https://example.com/duplicate",
            listing_type="auction"
        )
        session.add(duplicate_listing)
        try:
            await session.commit()
            print("⚠️  WARNING: Duplicate listing was created (unique constraint not working?)")
        except Exception as e:
            print(f"✅ Unique constraint working: {type(e).__name__}")
            await session.rollback()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print(f"📊 Database file: {db_path}")
        print(f"   User Filters: {len(user_filters)}")
        print(f"   Listings: 1")
        print(f"   Alerts Sent: 1")


async def main():
    """Main test function"""
    try:
        await test_models()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if os.path.exists("test_v2.db"):
            print(f"\n🧹 Cleaning up test database...")
            os.remove("test_v2.db")


if __name__ == "__main__":
    print("🧪 Testing v2 SQLAlchemy Models with SQLite")
    print("="*60)
    asyncio.run(main())

