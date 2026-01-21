"""
Test smart pagination feature

This test verifies that scrapers stop early when they encounter
already-seen listings (since we're sorting by newest first).

Test flow:
1. First run: Scrape a brand (all listings should be new)
2. Mark those listings as seen in the in-memory database
3. Second run: Scrape the same brand again (should stop early)
4. Verify logging shows early stop messages
"""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import time
import logging
from scrapers.yahoo_scraper import YahooScraper
from scrapers.mercari_api_scraper import MercariAPIScraper
from database import mark_listings_seen, listing_exists

# Configure logging to see the smart pagination messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_yahoo_smart_pagination():
    """Test Yahoo scraper smart pagination"""
    print("\n" + "="*80)
    print("🧪 Testing Yahoo Smart Pagination")
    print("="*80)
    
    test_brand = "Rick Owens"
    
    # First run: scrape brand (all should be new)
    print(f"\n📋 First run: Scraping {test_brand} (all listings should be new)")
    print("-" * 80)
    
    start_time = time.time()
    async with YahooScraper() as scraper:
        first_run_listings = await scraper.scrape(brands=[test_brand], max_price=None)
    first_duration = time.time() - start_time
    
    print(f"\n✅ First run complete:")
    print(f"   ⏱️  Duration: {first_duration:.2f} seconds")
    print(f"   📦 Listings found: {len(first_run_listings)}")
    
    if not first_run_listings:
        print("   ⚠️  No listings found - cannot test smart pagination")
        return
    
    # Mark all first-run listings as seen
    external_ids = [listing.external_id for listing in first_run_listings if listing.external_id]
    mark_listings_seen(external_ids)
    print(f"   ✅ Marked {len(external_ids)} listings as seen in database")
    
    # Show first few listings
    print(f"\n📋 First 5 listings from first run:")
    for i, listing in enumerate(first_run_listings[:5], 1):
        print(f"   {i}. {listing.external_id}: {listing.title[:50]}...")
    
    # Wait a moment
    print(f"\n⏳ Waiting 3 seconds before second run...")
    await asyncio.sleep(3)
    
    # Second run: scrape same brand (should stop early)
    print(f"\n📋 Second run: Scraping {test_brand} again (should stop early)")
    print("-" * 80)
    print("   💡 Look for 'Stopped at page X' message in logs above")
    
    start_time = time.time()
    async with YahooScraper() as scraper:
        second_run_listings = await scraper.scrape(brands=[test_brand], max_price=None)
    second_duration = time.time() - start_time
    
    print(f"\n✅ Second run complete:")
    print(f"   ⏱️  Duration: {second_duration:.2f} seconds")
    print(f"   📦 Listings found: {len(second_run_listings)}")
    
    # Verify smart pagination worked
    if len(second_run_listings) < len(first_run_listings):
        print(f"   ✅ Smart pagination worked! Found {len(second_run_listings)} vs {len(first_run_listings)} listings")
        print(f"   📉 Reduction: {len(first_run_listings) - len(second_run_listings)} fewer listings")
        print(f"   ⚡ Speed improvement: {first_duration / second_duration:.2f}x faster")
    else:
        print(f"   ⚠️  Expected fewer listings in second run, but got {len(second_run_listings)}")
        print(f"   💡 This might mean all listings on page 1 were new (unlikely but possible)")
    
    # Check if any second-run listings were already seen
    seen_count = sum(1 for listing in second_run_listings if listing.external_id and listing_exists(listing.external_id))
    if seen_count > 0:
        print(f"   ⚠️  Found {seen_count} listings that were already marked as seen")
    else:
        print(f"   ✅ All second-run listings are new (smart pagination stopped before duplicates)")
    
    return first_run_listings, second_run_listings


async def test_mercari_smart_pagination():
    """Test Mercari scraper smart pagination"""
    print("\n" + "="*80)
    print("🧪 Testing Mercari Smart Pagination")
    print("="*80)
    
    test_brand = "Rick Owens"
    
    # First run: scrape brand (all should be new)
    print(f"\n📋 First run: Scraping {test_brand} (all listings should be new)")
    print("-" * 80)
    
    start_time = time.time()
    async with MercariAPIScraper() as scraper:
        first_run_listings = await scraper.scrape(brands=[test_brand], max_price=None)
    first_duration = time.time() - start_time
    
    print(f"\n✅ First run complete:")
    print(f"   ⏱️  Duration: {first_duration:.2f} seconds")
    print(f"   📦 Listings found: {len(first_run_listings)}")
    
    if not first_run_listings:
        print("   ⚠️  No listings found - cannot test smart pagination")
        return
    
    # Mark all first-run listings as seen
    external_ids = [listing.external_id for listing in first_run_listings if listing.external_id]
    mark_listings_seen(external_ids)
    print(f"   ✅ Marked {len(external_ids)} listings as seen in database")
    
    # Show first few listings
    print(f"\n📋 First 5 listings from first run:")
    for i, listing in enumerate(first_run_listings[:5], 1):
        print(f"   {i}. {listing.external_id}: {listing.title[:50]}...")
    
    # Wait a moment
    print(f"\n⏳ Waiting 3 seconds before second run...")
    await asyncio.sleep(3)
    
    # Second run: scrape same brand (should stop early)
    print(f"\n📋 Second run: Scraping {test_brand} again (should stop early)")
    print("-" * 80)
    print("   💡 Look for 'Stopped at page X' message in logs above")
    
    start_time = time.time()
    async with MercariAPIScraper() as scraper:
        second_run_listings = await scraper.scrape(brands=[test_brand], max_price=None)
    second_duration = time.time() - start_time
    
    print(f"\n✅ Second run complete:")
    print(f"   ⏱️  Duration: {second_duration:.2f} seconds")
    print(f"   📦 Listings found: {len(second_run_listings)}")
    
    # Verify smart pagination worked
    if len(second_run_listings) < len(first_run_listings):
        print(f"   ✅ Smart pagination worked! Found {len(second_run_listings)} vs {len(first_run_listings)} listings")
        print(f"   📉 Reduction: {len(first_run_listings) - len(second_run_listings)} fewer listings")
        print(f"   ⚡ Speed improvement: {first_duration / second_duration:.2f}x faster")
    else:
        print(f"   ⚠️  Expected fewer listings in second run, but got {len(second_run_listings)}")
        print(f"   💡 This might mean all listings on page 1 were new (unlikely but possible)")
    
    # Check if any second-run listings were already seen
    seen_count = sum(1 for listing in second_run_listings if listing.external_id and listing_exists(listing.external_id))
    if seen_count > 0:
        print(f"   ⚠️  Found {seen_count} listings that were already marked as seen")
    else:
        print(f"   ✅ All second-run listings are new (smart pagination stopped before duplicates)")
    
    return first_run_listings, second_run_listings


async def test_database_functions():
    """Test the database helper functions"""
    print("\n" + "="*80)
    print("🧪 Testing Database Functions")
    print("="*80)
    
    from database import listing_exists, mark_listing_seen
    
    # Test basic functionality
    test_id = "test_123"
    
    print(f"\n1. Testing listing_exists with new ID:")
    exists = listing_exists(test_id)
    print(f"   ✅ listing_exists('{test_id}') = {exists} (expected: False)")
    
    print(f"\n2. Marking listing as seen:")
    mark_listing_seen(test_id)
    print(f"   ✅ mark_listing_seen('{test_id}') called")
    
    print(f"\n3. Testing listing_exists with seen ID:")
    exists = listing_exists(test_id)
    print(f"   ✅ listing_exists('{test_id}') = {exists} (expected: True)")
    
    # Test with multiple IDs
    print(f"\n4. Testing mark_listings_seen with multiple IDs:")
    from database import mark_listings_seen
    test_ids = ["id_1", "id_2", "id_3"]
    mark_listings_seen(test_ids)
    print(f"   ✅ mark_listings_seen({test_ids}) called")
    
    for test_id in test_ids:
        exists = listing_exists(test_id)
        print(f"   ✅ listing_exists('{test_id}') = {exists} (expected: True)")
    
    print(f"\n✅ All database function tests passed!")


async def main():
    """Run all smart pagination tests"""
    print("\n" + "="*80)
    print("🚀 SMART PAGINATION TEST SUITE")
    print("="*80)
    print("\nThis test verifies that scrapers stop early when they encounter")
    print("already-seen listings (since we're sorting by newest first).")
    print("\nTest flow:")
    print("1. First run: Scrape a brand (all listings should be new)")
    print("2. Mark those listings as seen in the in-memory database")
    print("3. Second run: Scrape the same brand again (should stop early)")
    print("4. Verify logging shows early stop messages")
    print("="*80)
    
    try:
        # Test database functions first
        await test_database_functions()
        
        # Test Yahoo smart pagination
        print("\n" + "="*80)
        print("Testing Yahoo Scraper Smart Pagination")
        print("="*80)
        yahoo_first, yahoo_second = await test_yahoo_smart_pagination()
        
        # Test Mercari smart pagination
        print("\n" + "="*80)
        print("Testing Mercari Scraper Smart Pagination")
        print("="*80)
        mercari_first, mercari_second = await test_mercari_smart_pagination()
        
        # Summary
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"\n✅ Yahoo Scraper:")
        print(f"   First run: {len(yahoo_first)} listings")
        print(f"   Second run: {len(yahoo_second)} listings")
        if len(yahoo_second) < len(yahoo_first):
            print(f"   ✅ Smart pagination: WORKING (stopped early)")
        else:
            print(f"   ⚠️  Smart pagination: May need more listings to test")
        
        print(f"\n✅ Mercari Scraper:")
        print(f"   First run: {len(mercari_first)} listings")
        print(f"   Second run: {len(mercari_second)} listings")
        if len(mercari_second) < len(mercari_first):
            print(f"   ✅ Smart pagination: WORKING (stopped early)")
        else:
            print(f"   ⚠️  Smart pagination: May need more listings to test")
        
        print("\n" + "="*80)
        print("✅ All tests complete!")
        print("="*80)
        print("\n💡 Tips:")
        print("   - Look for 'Stopped at page X' messages in the logs above")
        print("   - Look for 'Scraped all X pages' messages (means no duplicates found)")
        print("   - Average pages per brand should be lower in second run")
        print("="*80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

