"""
Test script for Yahoo scraper
Tests scraping 3 brands and verifies performance and deduplication
"""
import asyncio
import time
from scrapers.yahoo_scraper import YahooScraper


async def test_yahoo_scraper():
    """Test the Yahoo scraper with 3 brands"""
    
    # Test brands
    test_brands = ["Rick Owens", "Raf Simons", "Comme des Garcons"]
    
    print("=" * 60)
    print("🚀 Testing Yahoo Scraper (v2)")
    print("=" * 60)
    print(f"📋 Brands to scrape: {', '.join(test_brands)}")
    print(f"⚡ Processing up to 100 listings in parallel")
    print()
    
    # Start timing
    start_time = time.time()
    
    # Create scraper and run
    async with YahooScraper() as scraper:
        print("🔍 Starting scrape...")
        listings = await scraper.scrape(brands=test_brands, max_price=None)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Print results
    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(f"⏱️  Duration: {duration:.2f} seconds")
    print(f"📦 Total listings found: {len(listings)}")
    print()
    
    # Group by brand
    brand_counts = {}
    for listing in listings:
        brand = listing.brand or "Unknown"
        brand_counts[brand] = brand_counts.get(brand, 0) + 1
    
    print("📈 Listings by brand:")
    for brand, count in sorted(brand_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   {brand}: {count} listings")
    print()
    
    # Check for duplicates
    urls = [listing.url for listing in listings]
    unique_urls = set(urls)
    duplicates = len(urls) - len(unique_urls)
    
    print(f"🔍 Duplicate check:")
    print(f"   Total URLs: {len(urls)}")
    print(f"   Unique URLs: {len(unique_urls)}")
    print(f"   Duplicates: {duplicates}")
    
    if duplicates > 0:
        print(f"   ⚠️  WARNING: Found {duplicates} duplicate listings!")
    else:
        print(f"   ✅ No duplicates found")
    print()
    
    # Show sample listings
    print("=" * 60)
    print("📋 SAMPLE LISTINGS (first 10)")
    print("=" * 60)
    
    for i, listing in enumerate(listings[:10], 1):
        print(f"\n{i}. {listing.title[:60]}...")
        print(f"   Brand: {listing.brand or 'Unknown'}")
        print(f"   Price: ¥{listing.price_jpy:,} ({listing.price_jpy / 147:.2f} USD)")
        print(f"   Type: {listing.listing_type}")
        print(f"   URL: {listing.url[:80]}...")
        if listing.image_url:
            print(f"   Image: {listing.image_url[:60]}...")
    
    if len(listings) > 10:
        print(f"\n... and {len(listings) - 10} more listings")
    
    print()
    print("=" * 60)
    print("✅ Test complete!")
    print("=" * 60)
    
    return listings


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_yahoo_scraper())

