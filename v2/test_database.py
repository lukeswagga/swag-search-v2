"""
Test database operations for v2 scrapers.
Tests saving listings, deduplication, and querying recent listings.
Uses SQLite locally for testing.
"""
import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    init_database,
    create_tables,
    drop_tables,
    listing_exists,
    save_listing,
    save_listings_batch,
    get_listings_since,
    close_database
)
from models import Listing

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_listing_exists():
    """Test listing_exists function"""
    print("\n" + "="*80)
    print("🧪 Test 1: listing_exists")
    print("="*80)
    
    # Check non-existent listing
    exists = await listing_exists("test_id_123", "yahoo")
    assert not exists, f"Expected False, got {exists}"
    print("✅ listing_exists('test_id_123', 'yahoo') = False (correct)")
    
    # Create a listing
    listing = Listing(
        market="yahoo",
        external_id="test_id_123",
        title="Test Listing",
        price_jpy=10000,
        brand="Test Brand",
        url="https://test.com/123",
        listing_type="auction",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    # Save it
    saved = await save_listing(listing)
    assert saved, "Expected to save new listing"
    print("✅ Saved new listing")
    
    # Check it exists now
    exists = await listing_exists("test_id_123", "yahoo")
    assert exists, f"Expected True, got {exists}"
    print("✅ listing_exists('test_id_123', 'yahoo') = True (correct)")
    
    # Check with different market (should not exist)
    exists = await listing_exists("test_id_123", "mercari")
    assert not exists, f"Expected False (different market), got {exists}"
    print("✅ listing_exists('test_id_123', 'mercari') = False (correct - different market)")
    
    print("✅ Test 1 passed!\n")


async def test_save_listing():
    """Test save_listing function"""
    print("\n" + "="*80)
    print("🧪 Test 2: save_listing (new vs duplicate)")
    print("="*80)
    
    # Save new listing
    listing1 = Listing(
        market="yahoo",
        external_id="test_id_456",
        title="New Listing",
        price_jpy=20000,
        brand="Supreme",
        url="https://test.com/456",
        listing_type="auction",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    saved = await save_listing(listing1)
    assert saved, "Expected to save new listing"
    print("✅ Saved new listing (returned True)")
    
    # Try to save same listing again (should return False - duplicate)
    listing2 = Listing(
        market="yahoo",
        external_id="test_id_456",
        title="Same Listing",  # Different title, but same external_id
        price_jpy=25000,  # Different price
        brand="Supreme",
        url="https://test.com/456",
        listing_type="auction",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    saved = await save_listing(listing2)
    assert not saved, "Expected duplicate (return False)"
    print("✅ Attempted to save duplicate (returned False - correct)")
    
    # Verify listing still exists
    exists = await listing_exists("test_id_456", "yahoo")
    assert exists, "Listing should still exist"
    print("✅ Duplicate listing still exists in database (last_seen updated)")
    
    print("✅ Test 2 passed!\n")


async def test_save_listings_batch():
    """Test save_listings_batch function"""
    print("\n" + "="*80)
    print("🧪 Test 3: save_listings_batch")
    print("="*80)
    
    # Create a batch of listings (some new, some duplicates)
    listings = [
        Listing(
            market="mercari",
            external_id=f"batch_new_{i}",
            title=f"New Listing {i}",
            price_jpy=10000 + i * 1000,
            brand="Bape",
            url=f"https://mercari.com/item/{i}",
            listing_type="fixed",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc)
        )
        for i in range(5)
    ]
    
    # Add one duplicate (use existing test_id_123 from Test 1)
    duplicate = Listing(
        market="yahoo",
        external_id="test_id_123",  # Already exists
        title="Duplicate Listing",
        price_jpy=15000,
        brand="Test Brand",
        url="https://test.com/123",
        listing_type="auction",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    listings.append(duplicate)
    
    # Save batch
    stats = await save_listings_batch(listings)
    
    print(f"📊 Batch save stats:")
    print(f"   Total processed: {stats['total']}")
    print(f"   New saved: {stats['saved']}")
    print(f"   Duplicates: {stats['duplicates']}")
    print(f"   Errors: {stats['errors']}")
    
    assert stats['total'] == 6, f"Expected 6 total, got {stats['total']}"
    assert stats['saved'] == 5, f"Expected 5 new, got {stats['saved']}"
    assert stats['duplicates'] == 1, f"Expected 1 duplicate, got {stats['duplicates']}"
    assert stats['errors'] == 0, f"Expected 0 errors, got {stats['errors']}"
    
    print("✅ Test 3 passed!\n")


async def test_get_listings_since():
    """Test get_listings_since function"""
    print("\n" + "="*80)
    print("🧪 Test 4: get_listings_since")
    print("="*80)
    
    # Get current time
    now = datetime.now(timezone.utc)
    past_time = now - timedelta(minutes=1)
    
    # Query listings since past_time (should include all test listings)
    recent_listings = await get_listings_since(past_time)
    
    print(f"📊 Found {len(recent_listings)} listings since {past_time}")
    
    # Should have at least the listings we created in tests
    assert len(recent_listings) >= 6, f"Expected at least 6 listings, got {len(recent_listings)}"
    
    # Verify they're sorted by first_seen desc (newest first)
    if len(recent_listings) > 1:
        for i in range(len(recent_listings) - 1):
            assert recent_listings[i].first_seen >= recent_listings[i+1].first_seen, \
                "Listings should be sorted by first_seen descending"
    
    print("✅ Test 4 passed!\n")


async def test_deduplication_across_markets():
    """Test that same external_id can exist for different markets"""
    print("\n" + "="*80)
    print("🧪 Test 5: Deduplication across markets")
    print("="*80)
    
    # Create listing for Yahoo
    yahoo_listing = Listing(
        market="yahoo",
        external_id="same_id_789",
        title="Yahoo Listing",
        price_jpy=30000,
        brand="Nike",
        url="https://yahoo.com/item/789",
        listing_type="auction",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    # Create listing for Mercari with same external_id
    mercari_listing = Listing(
        market="mercari",
        external_id="same_id_789",
        title="Mercari Listing",
        price_jpy=30000,
        brand="Nike",
        url="https://mercari.com/item/789",
        listing_type="fixed",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    # Save both - they should both be saved (different markets)
    saved_yahoo = await save_listing(yahoo_listing)
    saved_mercari = await save_listing(mercari_listing)
    
    assert saved_yahoo, "Yahoo listing should be saved"
    assert saved_mercari, "Mercari listing should be saved (different market)"
    
    print("✅ Saved Yahoo listing")
    print("✅ Saved Mercari listing with same external_id (different market)")
    
    # Verify both exist
    yahoo_exists = await listing_exists("same_id_789", "yahoo")
    mercari_exists = await listing_exists("same_id_789", "mercari")
    
    assert yahoo_exists, "Yahoo listing should exist"
    assert mercari_exists, "Mercari listing should exist"
    
    print("✅ Both listings exist in database (different markets)")
    print("✅ Test 5 passed!\n")


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("🧪 Database Operations Test Suite")
    print("="*80)
    print("\nUsing SQLite for local testing...")
    print("Database: sqlite+aiosqlite:///./test.db\n")
    
    # Clean up old test database if it exists
    db_path = "./test.db"
    if os.path.exists(db_path):
        print("🧹 Cleaning up old test database...")
        os.remove(db_path)
    
    try:
        # Initialize database with SQLite (synchronous)
        init_database("sqlite+aiosqlite:///./test.db")
        # Create tables (async)
        await create_tables()
        print("✅ Database initialized\n")
        
        # Run tests
        await test_listing_exists()
        await test_save_listing()
        await test_save_listings_batch()
        await test_get_listings_since()
        await test_deduplication_across_markets()
        
        print("="*80)
        print("✅ All tests passed!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up - drop tables first, then close connection
        try:
            await drop_tables()
            await close_database()
            print("\n✅ Database connections closed")
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
            await close_database()
        
        # Optionally delete test database
        if os.path.exists("./test.db"):
            response = input("\nDelete test database (test.db)? [y/N]: ")
            if response.lower() == 'y':
                os.remove("./test.db")
                print("✅ Test database deleted")


if __name__ == "__main__":
    asyncio.run(main())

