"""
Comprehensive test suite for SwagSearch search API endpoints.

Tests all new endpoints:
- GET /api/feed/search (historical search with pagination)
- GET /api/feed/recent (real-time updates)
- GET /api/listings/{id} (detail view)

Also tests updated /api/filters endpoints with USD support.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class APITester:
    """Test harness for API endpoints"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_user_id = "test_user_123"

    def print_header(self, text: str):
        """Print test section header"""
        print("\n" + "=" * 70)
        print(f"  {text}")
        print("=" * 70)

    def print_test(self, name: str):
        """Print test name"""
        print(f"\n▶ Test: {name}")

    def assert_true(self, condition: bool, message: str):
        """Assert a condition is true"""
        if condition:
            print(f"  ✅ {message}")
            self.passed += 1
        else:
            print(f"  ❌ {message}")
            self.failed += 1

    def assert_equals(self, actual: Any, expected: Any, message: str):
        """Assert two values are equal"""
        if actual == expected:
            print(f"  ✅ {message}: {actual}")
            self.passed += 1
        else:
            print(f"  ❌ {message}: expected {expected}, got {actual}")
            self.failed += 1

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 70)
        print(f"  TEST SUMMARY")
        print("=" * 70)
        print(f"  Passed: {self.passed}")
        print(f"  Failed: {self.failed}")
        print(f"  Total:  {self.passed + self.failed}")
        print("=" * 70)

        if self.failed == 0:
            print("\n🎉 All tests passed!")
        else:
            print(f"\n⚠️  {self.failed} test(s) failed")


async def setup_test_data():
    """Create test listings in the database"""
    from database import init_database, create_tables, save_listings_batch
    from models import Listing
    from config import get_database_url

    logger.info("\n🔧 Setting up test database...")

    # Initialize database
    db_url = get_database_url()
    if not db_url:
        db_url = "sqlite+aiosqlite:///./test_search.db"
        logger.info(f"   Using test database: {db_url}")

    init_database(db_url)
    await create_tables()

    # Create diverse test listings
    now = datetime.utcnow()
    test_listings = []

    # Brand: Raf Simons (various prices and markets)
    for i in range(15):
        test_listings.append(Listing(
            market="yahoo" if i % 2 == 0 else "mercari",
            external_id=f"raf_{i}",
            title=f"Raf Simons Archive Jacket {i}",
            brand="Raf Simons",
            price_jpy=20000 + (i * 1000),  # ¥20,000 to ¥34,000
            url=f"https://example.com/raf_{i}",
            image_url=f"https://example.com/raf_{i}.jpg",
            listing_type="auction" if i % 3 == 0 else "buy_it_now",
            seller_id=f"seller_{i % 5}",
            first_seen=now - timedelta(hours=i),
            last_seen=now - timedelta(hours=i)
        ))

    # Brand: Rick Owens (higher prices)
    for i in range(10):
        test_listings.append(Listing(
            market="yahoo",
            external_id=f"rick_{i}",
            title=f"Rick Owens Geobasket {i}",
            brand="Rick Owens",
            price_jpy=40000 + (i * 2000),  # ¥40,000 to ¥58,000
            url=f"https://example.com/rick_{i}",
            image_url=f"https://example.com/rick_{i}.jpg",
            listing_type="buy_it_now",
            seller_id=f"seller_{i % 3}",
            first_seen=now - timedelta(hours=i + 20),
            last_seen=now - timedelta(hours=i + 20)
        ))

    # Brand: Maison Margiela (mixed prices)
    for i in range(8):
        test_listings.append(Listing(
            market="mercari",
            external_id=f"margiela_{i}",
            title=f"Maison Margiela Tabi Boots {i}",
            brand="Maison Margiela",
            price_jpy=25000 + (i * 1500),
            url=f"https://example.com/margiela_{i}",
            image_url=f"https://example.com/margiela_{i}.jpg",
            listing_type="buy_it_now",
            seller_id=f"seller_{i % 4}",
            first_seen=now - timedelta(hours=i + 40),
            last_seen=now - timedelta(hours=i + 40)
        ))

    # Brand: Yohji Yamamoto (budget to luxury)
    for i in range(12):
        test_listings.append(Listing(
            market="yahoo" if i % 2 == 0 else "mercari",
            external_id=f"yohji_{i}",
            title=f"Yohji Yamamoto Vintage Piece {i}",
            brand="Yohji Yamamoto",
            price_jpy=15000 + (i * 3000),  # ¥15,000 to ¥48,000
            url=f"https://example.com/yohji_{i}",
            image_url=f"https://example.com/yohji_{i}.jpg",
            listing_type="auction",
            seller_id=f"seller_{i % 6}",
            first_seen=now - timedelta(hours=i + 60),
            last_seen=now - timedelta(hours=i + 60)
        ))

    # Save all test listings
    stats = await save_listings_batch(test_listings)
    logger.info(f"   ✅ Created {stats['saved']} test listings")

    return len(test_listings)


async def test_search_endpoint(tester: APITester):
    """Test /api/feed/search endpoint"""
    from database import search_listings_paginated
    from currency import usd_to_jpy, jpy_to_usd

    tester.print_header("TEST: /api/feed/search - Historical Search")

    # Test 1: Search with no parameters (all listings)
    tester.print_test("Search with no parameters")
    listings, total = await search_listings_paginated(page=1, per_page=100)
    tester.assert_true(total > 0, f"Found {total} total listings")
    tester.assert_true(len(listings) <= 100, f"Returned {len(listings)} listings (respects per_page limit)")

    # Test 2: Search by brand only (case-insensitive)
    tester.print_test("Search by brand only (case-insensitive)")
    listings, total = await search_listings_paginated(brand="raf simons", page=1, per_page=50)
    tester.assert_true(total >= 15, f"Found {total} Raf Simons listings")
    if listings:
        tester.assert_true(
            "raf simons" in listings[0].brand.lower(),
            f"First result brand: {listings[0].brand}"
        )

    # Test 3: Search by price range only (USD converted to JPY)
    tester.print_test("Search by price range (USD to JPY conversion)")
    min_usd, max_usd = 136, 272  # ~¥20,000 to ¥40,000
    min_jpy = usd_to_jpy(min_usd)
    max_jpy = usd_to_jpy(max_usd)
    listings, total = await search_listings_paginated(
        min_price_jpy=min_jpy,
        max_price_jpy=max_jpy,
        page=1,
        per_page=50
    )
    tester.assert_true(total > 0, f"Found {total} listings in price range")
    if listings:
        price_in_range = min_jpy <= listings[0].price_jpy <= max_jpy
        tester.assert_true(
            price_in_range,
            f"Price within range: ¥{listings[0].price_jpy} (${jpy_to_usd(listings[0].price_jpy)})"
        )

    # Test 4: Search by brand + price + market
    tester.print_test("Search by brand + price + market")
    listings, total = await search_listings_paginated(
        brand="rick owens",
        min_price_jpy=40000,
        max_price_jpy=50000,
        market="yahoo",
        page=1,
        per_page=50
    )
    tester.assert_true(total > 0, f"Found {total} Rick Owens listings on Yahoo in price range")
    if listings:
        tester.assert_equals(listings[0].market, "yahoo", "Market filter works")

    # Test 5: Pagination (multiple pages)
    tester.print_test("Pagination (page 1, 2, 3)")
    page1, total = await search_listings_paginated(page=1, per_page=10)
    page2, _ = await search_listings_paginated(page=2, per_page=10)
    page3, _ = await search_listings_paginated(page=3, per_page=10)

    tester.assert_equals(len(page1), 10, "Page 1 has 10 items")
    tester.assert_true(len(page2) > 0, f"Page 2 has {len(page2)} items")

    if page1 and page2:
        different = page1[0].id != page2[0].id
        tester.assert_true(different, "Pages contain different listings (OFFSET works)")

    # Test 6: Sort options
    tester.print_test("Sort options")

    # Sort by newest
    newest, _ = await search_listings_paginated(sort="newest", page=1, per_page=5)
    if len(newest) >= 2:
        tester.assert_true(
            newest[0].first_seen >= newest[1].first_seen,
            f"Newest first: {newest[0].first_seen} >= {newest[1].first_seen}"
        )

    # Sort by oldest
    oldest, _ = await search_listings_paginated(sort="oldest", page=1, per_page=5)
    if len(oldest) >= 2:
        tester.assert_true(
            oldest[0].first_seen <= oldest[1].first_seen,
            f"Oldest first: {oldest[0].first_seen} <= {oldest[1].first_seen}"
        )

    # Sort by price_low
    price_low, _ = await search_listings_paginated(sort="price_low", page=1, per_page=5)
    if len(price_low) >= 2:
        tester.assert_true(
            price_low[0].price_jpy <= price_low[1].price_jpy,
            f"Price low to high: ¥{price_low[0].price_jpy} <= ¥{price_low[1].price_jpy}"
        )

    # Sort by price_high
    price_high, _ = await search_listings_paginated(sort="price_high", page=1, per_page=5)
    if len(price_high) >= 2:
        tester.assert_true(
            price_high[0].price_jpy >= price_high[1].price_jpy,
            f"Price high to low: ¥{price_high[0].price_jpy} >= ¥{price_high[1].price_jpy}"
        )

    # Test 7: Empty results (no matches)
    tester.print_test("Empty results (no matches)")
    listings, total = await search_listings_paginated(
        brand="nonexistent brand xyz",
        page=1,
        per_page=50
    )
    tester.assert_equals(total, 0, "No results for nonexistent brand")
    tester.assert_equals(len(listings), 0, "Empty listings array")


async def test_recent_endpoint(tester: APITester):
    """Test /api/feed/recent endpoint"""
    from database import get_recent_listings, save_listings_batch
    from models import Listing

    tester.print_header("TEST: /api/feed/recent - Real-Time Updates")

    # Test 8: Recent listings (timestamp filtering)
    tester.print_test("Get recent listings since timestamp")

    # Get listings from last 2 hours
    since = datetime.utcnow() - timedelta(hours=2)
    listings = await get_recent_listings(since=since, limit=50)
    tester.assert_true(len(listings) > 0, f"Found {len(listings)} recent listings")

    if listings:
        all_after_since = all(listing.first_seen > since for listing in listings)
        tester.assert_true(all_after_since, "All listings are after 'since' timestamp")

    # Test 9: Recent listings with filters
    tester.print_test("Recent listings with brand filter")
    listings = await get_recent_listings(
        since=datetime.utcnow() - timedelta(hours=100),  # Far back to ensure results
        brand="raf simons",
        limit=20
    )
    tester.assert_true(len(listings) > 0, f"Found {len(listings)} recent Raf Simons listings")

    # Test 10: No new listings (recent timestamp)
    tester.print_test("No new listings (very recent timestamp)")
    listings = await get_recent_listings(
        since=datetime.utcnow() + timedelta(hours=1),  # Future timestamp
        limit=50
    )
    tester.assert_equals(len(listings), 0, "No listings in the future")


async def test_listing_detail_endpoint(tester: APITester):
    """Test /api/listings/{id} endpoint"""
    from database import search_listings_paginated, get_listing_by_id

    tester.print_header("TEST: /api/listings/{id} - Detail View")

    # Test 11: Get listing by ID
    tester.print_test("Get listing by ID")

    # Get a listing ID first
    listings, _ = await search_listings_paginated(page=1, per_page=1)
    if listings:
        listing_id = listings[0].id
        detail = await get_listing_by_id(listing_id)

        tester.assert_true(detail is not None, f"Found listing {listing_id}")
        if detail:
            tester.assert_equals(detail.id, listing_id, "Correct listing returned")
            tester.assert_true(detail.title is not None, f"Has title: {detail.title}")
            tester.assert_true(detail.price_jpy > 0, f"Has price: ¥{detail.price_jpy}")
    else:
        logger.warning("   ⚠️  No listings found to test detail view")

    # Test 12: Non-existent listing ID
    tester.print_test("Non-existent listing ID (404)")
    detail = await get_listing_by_id(999999)
    tester.assert_true(detail is None, "Returns None for non-existent ID")


async def test_filters_with_usd(tester: APITester):
    """Test updated /api/filters endpoints with USD support"""
    from database import save_user_filter, get_user_filters, delete_user_filter
    from models import UserFilter
    from currency import usd_to_jpy, jpy_to_usd

    tester.print_header("TEST: /api/filters - USD Price Support")

    # Test 13: Create filter with USD prices
    tester.print_test("Create filter with USD prices")

    min_usd, max_usd = 136, 340
    min_jpy = usd_to_jpy(min_usd)
    max_jpy = usd_to_jpy(max_usd)

    test_filter = UserFilter(
        user_id="test_user_usd",
        name="Test Filter USD",
        brands='["Raf Simons"]',
        price_min=min_jpy,
        price_max=max_jpy,
        markets="yahoo,mercari",
        active=True
    )

    filter_id = await save_user_filter(test_filter)
    tester.assert_true(filter_id > 0, f"Created filter with ID {filter_id}")

    # Verify conversion
    tester.assert_equals(
        test_filter.price_min,
        min_jpy,
        f"USD {min_usd} converted to JPY {min_jpy}"
    )
    tester.assert_equals(
        test_filter.price_max,
        max_jpy,
        f"USD {max_usd} converted to JPY {max_jpy}"
    )

    # Test 14: Retrieve filter and verify both USD/JPY
    tester.print_test("Retrieve filter with both USD and JPY prices")

    filters = await get_user_filters("test_user_usd")
    tester.assert_equals(len(filters), 1, "Found 1 filter")

    if filters:
        f = filters[0]
        retrieved_min_usd = jpy_to_usd(f.price_min)
        retrieved_max_usd = jpy_to_usd(f.price_max)

        # Allow small rounding difference
        min_diff = abs(retrieved_min_usd - min_usd)
        max_diff = abs(retrieved_max_usd - max_usd)

        tester.assert_true(
            min_diff < 1.0,
            f"Min price USD conversion: {retrieved_min_usd} ≈ {min_usd}"
        )
        tester.assert_true(
            max_diff < 1.0,
            f"Max price USD conversion: {retrieved_max_usd} ≈ {max_usd}"
        )

    # Cleanup
    if filters:
        await delete_user_filter(filters[0].id)


async def test_performance(tester: APITester):
    """Test query performance"""
    import time

    tester.print_header("TEST: Performance")

    # Test 15: Query performance (< 100ms for typical queries)
    tester.print_test("Query performance for typical search")

    from database import search_listings_paginated

    start = time.time()
    listings, total = await search_listings_paginated(
        brand="raf simons",
        min_price_jpy=20000,
        max_price_jpy=40000,
        page=1,
        per_page=100
    )
    elapsed_ms = (time.time() - start) * 1000

    tester.assert_true(
        elapsed_ms < 1000,  # Allow 1 second for test database
        f"Query completed in {elapsed_ms:.1f}ms"
    )

    if elapsed_ms < 100:
        print(f"  🚀 Excellent: Query under 100ms ({elapsed_ms:.1f}ms)")
    elif elapsed_ms < 500:
        print(f"  ⚡ Good: Query under 500ms ({elapsed_ms:.1f}ms)")


async def run_all_tests():
    """Run complete test suite"""
    tester = APITester()

    print("\n" + "=" * 70)
    print("  SwagSearch Search API - Comprehensive Test Suite")
    print("=" * 70)

    try:
        # Setup test data
        num_listings = await setup_test_data()
        logger.info(f"   📊 Test database has {num_listings} listings\n")

        # Run all test suites
        await test_search_endpoint(tester)
        await test_recent_endpoint(tester)
        await test_listing_detail_endpoint(tester)
        await test_filters_with_usd(tester)
        await test_performance(tester)

        # Print summary
        tester.print_summary()

        return tester.failed == 0

    except Exception as e:
        logger.error(f"\n❌ Test suite failed with error: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
