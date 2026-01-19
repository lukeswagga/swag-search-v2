#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pubert Custom Scraper - Customer-specific scraper for #pubert channel
Posts only to #pubert channel, uses pubert_brands.json for brand list
Does NOT interfere with main brand routing or channels
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core_scraper_base import YahooScraperBase
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime, timezone, timedelta
import threading
import schedule
import asyncio
import json

class PubertScraper(YahooScraperBase):
    def __init__(self):
        super().__init__("pubert_scraper")
        self.target_channel = "pubert"  # Exact Discord channel name (no emoji)

        # Rotating pagination settings
        self.pages_per_cycle = 3  # Scrape 3 pages per cycle
        self.max_total_pages = 10  # Reduced from 20 - pages 10-20 rarely have good results
        self.page_offset = self.load_page_offset()  # Load persisted offset

        self.cycle_count = 0
        self.last_run_time = None

    def load_page_offset(self):
        """Load the current page offset from database (persists across Railway redeploys)"""
        offset = self.load_scraper_state('page_offset', default=0)
        print(f"📖 Pubert page offset loaded: {offset}")
        return offset

    def save_page_offset(self):
        """Save the current page offset to database (persists across Railway redeploys)"""
        self.save_scraper_state('page_offset', self.page_offset)
        print(f"💾 Pubert page offset saved: {self.page_offset}")

    def get_current_page_range(self):
        """Get the current page range to scrape (start_page, end_page)"""
        start_page = self.page_offset + 1
        end_page = min(self.page_offset + self.pages_per_cycle, self.max_total_pages)
        return start_page, end_page

    def advance_page_offset(self):
        """Advance to the next page range, reset if at the end"""
        self.page_offset += self.pages_per_cycle
        if self.page_offset >= self.max_total_pages:
            self.page_offset = 0
            print(f"🔄 Completed all {self.max_total_pages} pages, resetting to page 1")
        self.save_page_offset()

    def load_brand_data(self):
        """Override to load pubert_brands.json instead of brands.json"""
        try:
            pubert_brands_file = "pubert_brands.json"
            if os.path.exists(pubert_brands_file):
                with open(pubert_brands_file, 'r', encoding='utf-8') as f:
                    print(f"✅ Loading Pubert brands from {pubert_brands_file}")
                    return json.load(f)
            else:
                print(f"❌ {pubert_brands_file} not found!")
                return {}
        except Exception as e:
            print(f"⚠️ Could not load Pubert brand data: {e}")
            return {}

    async def scrape_pubert_page_async(self, keyword, page, brand_info):
        """Scrape a single page for Pubert custom listings"""
        try:
            # Build URL for both auctions and fixed price, sorted by newest
            url = self.build_search_url(
                keyword=keyword,
                page=page,
                fixed_type=3,  # Both auction and fixed price
                sort_type="new",
                sort_order="d",  # Descending (newest first)
                
            )

            # Use async fetch with retry logic
            html, success = await self.fetch_page_async(url)
            if not success or not html:
                return [], True

            soup = BeautifulSoup(html, "html.parser")
            items = soup.select("li.Product")

            if not items:
                print(f"🔚 No items found on page {page} for '{keyword}'")
                return [], False

            listings = []
            duplicates_skipped = 0

            for item in items:
                auction_data = self.extract_auction_data(item)
                if auction_data:
                    if auction_data['auction_id'] not in self.seen_ids:
                        listings.append(auction_data)
                        self.seen_ids.add(auction_data['auction_id'])
                    else:
                        duplicates_skipped += 1

            print(f"📄 Page {page} for '{keyword}': Found {len(listings)} new items ({duplicates_skipped} duplicates skipped)")
            if duplicates_skipped > 0:
                print(f"✅ Database working! Skipped {duplicates_skipped} already-seen items")
            return listings, len(items) >= 45  # Continue if page has enough items

        except Exception as e:
            print(f"❌ Error scraping page {page} for '{keyword}': {e}")
            return [], False

    async def scrape_brand_pubert_async(self, brand, brand_info):
        """Scrape all listings for a specific Pubert brand"""
        all_listings = []

        # Get current page range from rotating pagination
        start_page, end_page = self.get_current_page_range()

        # Use primary variant as keyword
        primary_variant = brand_info['variants'][0]

        print(f"🔍 Scanning {brand} for Pubert channel (pages {start_page}-{end_page})")

        # Process pages sequentially to avoid rate limiting
        for page in range(start_page, end_page + 1):
            listings, should_continue = await self.scrape_pubert_page_async(
                primary_variant, page, brand_info
            )

            all_listings.extend(listings)

            # Stop if page isn't full (but we'll still continue rotating through all pages)
            if not should_continue:
                print(f"🛑 Page {page} not full for {brand}, but will continue pagination rotation")
                # Don't break - we want to check all pages in the range even if one isn't full
                # This ensures we systematically cover all 20 pages over time

            # Polite delay between pages
            if page < end_page:
                await asyncio.sleep(2.5)

        return all_listings

    async def run_pubert_cycle_async(self):
        """Run a complete Pubert scraping cycle"""
        cycle_start = time.time()
        self.cycle_count += 1
        current_time = datetime.now(timezone.utc)

        print(f"\n👤 Starting Pubert cycle #{self.cycle_count} (ASYNC)")
        print(f"🎯 Target Channel: {self.target_channel}")
        print(f"🕐 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        total_found = 0
        total_sent = 0

        # Process brands sequentially to avoid overwhelming Yahoo
        all_brand_listings = []

        for brand, brand_info in self.brand_data.items():
            try:
                print(f"\n{'='*60}")
                print(f"Processing Pubert brand: {brand}")
                print(f"{'='*60}")

                listings = await self.scrape_brand_pubert_async(brand, brand_info)
                all_brand_listings.append((brand, listings))

                # Polite delay between brands
                await asyncio.sleep(3)

            except Exception as e:
                print(f"❌ Error processing {brand}: {e}")
                continue

        # Process all listings
        for brand, listings in all_brand_listings:
            try:
                for listing in listings:
                    # Add Pubert-specific metadata
                    listing['is_new_listing'] = True
                    listing['scraper_source'] = 'pubert_scraper'  # Critical for routing
                    listing['listing_type'] = 'pubert_custom'
                    listing['target_channel'] = 'pubert'  # Force to pubert channel

                    # Enhanced logging
                    print(f"🔍 Processing Pubert listing: {listing['title'][:50]}...")
                    print(f"   💰 Price: ${listing['price_usd']:.2f} (¥{listing['price_jpy']:,})")
                    print(f"   🏷️ Brand: {listing['brand']}")
                    print(f"   📊 Quality Score: {listing.get('deal_quality', 0):.2f}")
                    print(f"   👤 Target: #{self.target_channel}")

                    # Send to Discord bot (will be routed to #pubert only)
                    if self.send_to_discord(listing):
                        total_sent += 1
                        print(f"✅ Sent Pubert listing to Discord bot: {listing['title'][:50]}...")

                    total_found += 1

                    # Small delay to avoid overwhelming Discord
                    await asyncio.sleep(0.1)

            except Exception as e:
                print(f"❌ Error processing {brand}: {e}")
                continue

        # Close async session
        await self.close_session()

        # Save seen items
        self.save_seen_items()

        # Show filtering statistics
        self.analyze_filtering()

        # Cleanup seen_ids if needed
        self.cleanup_old_seen_ids()

        # Advance to next page range for next cycle
        start_page, end_page = self.get_current_page_range()
        print(f"📄 Completed pages {start_page}-{end_page}")
        self.advance_page_offset()
        next_start, next_end = self.get_current_page_range()
        print(f"📅 Next cycle will scrape pages {next_start}-{next_end}")

        # Update last run time
        self.last_run_time = current_time

        cycle_duration = time.time() - cycle_start
        print(f"\n📊 Pubert Cycle #{self.cycle_count} Complete (ASYNC):")
        print(f"   ⏱️ Duration: {cycle_duration:.1f}s")
        print(f"   🔍 Found: {total_found} items")
        print(f"   📤 Sent: {total_sent} items")
        print(f"   💾 Tracking: {len(self.seen_ids)} seen items")
        print(f"   🎯 Target: #{self.target_channel}")
        print(f"   👤 Customer: Pubert")
        print(f"   📦 Brands: {len(self.brand_data)}")

        return total_sent  # Return count for smart retry logic

    def run_pubert_cycle(self):
        """Sync wrapper for Railway deployment with smart retry logic"""
        max_retries = 3  # Max retry cycles if no results found
        retry_count = 0

        while retry_count <= max_retries:
            total_sent = asyncio.run(self.run_pubert_cycle_async())

            # If we sent at least 2 listings, we're done
            if total_sent >= 2:
                print(f"✅ Successfully sent {total_sent} listings, waiting for next scheduled run")
                break

            # If we got some results but not many, still accept it
            if total_sent > 0:
                print(f"✅ Sent {total_sent} listing(s), accepting and waiting for next scheduled run")
                break

            # No results - retry if we haven't hit max retries
            retry_count += 1
            if retry_count <= max_retries:
                print(f"⚠️ No listings sent. Retry {retry_count}/{max_retries} - running another cycle immediately...")
                time.sleep(5)  # Brief pause before retry
            else:
                print(f"❌ No results after {max_retries} retries. Will wait for next scheduled run.")

    def start_scheduler(self):
        """Start the scheduler for Pubert scraping"""
        start_page, end_page = self.get_current_page_range()
        print(f"🚀 Starting Pubert Custom Scraper")
        print(f"👤 Customer: Pubert")
        print(f"🎯 Target Channel: #{self.target_channel}")
        print(f"📦 Brands: {len(self.brand_data)}")
        print(f"📅 Schedule: Every 15 minutes")
        print(f"🔄 Sort Order: Newest first")
        print(f"📄 Pagination: Rotating through pages {start_page}-{end_page} (cycles through 1-{self.max_total_pages})")
        print(f"🔁 Smart Retry: Auto-retries up to 3 times if no listings found")
        print(f"⚠️ ISOLATED: Does not interfere with main brand routing")

        # List loaded brands
        print(f"\n📋 Pubert Brands Loaded:")
        for brand in self.brand_data.keys():
            print(f"   - {brand}")

        # Schedule every 15 minutes (less frequent to reduce load)
        schedule.every(15).minutes.do(self.run_pubert_cycle)

        # Run immediately
        self.run_pubert_cycle()

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)

def main():
    scraper = PubertScraper()

    # Start health server in background
    health_thread = threading.Thread(target=scraper.run_health_server, daemon=True)
    health_thread.start()
    print(f"🌐 Health server started on port {os.environ.get('PORT', 8000)}")

    # Start scraping
    try:
        scraper.start_scheduler()
    except KeyboardInterrupt:
        print("\n🛑 Pubert Scraper stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
