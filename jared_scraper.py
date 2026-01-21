#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Jared Custom Scraper - Customer-specific scraper for #jared channel
Posts only to #jared channel, uses jared_brands.json for brand list
Price limit: £80 = $108.12 USD = ¥16,850 JPY
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

class JaredScraper(YahooScraperBase):
    def __init__(self):
        super().__init__("jared_scraper")
        self.target_channel = "jared"  # Exact Discord channel name (no emoji)

        # Price limit: £80 = $108.12 USD = ¥16,849.96 JPY (rounded to ¥16,850)
        self.max_price_usd = 108.12
        self.max_price_jpy = 16850

        # Rotating pagination settings
        self.pages_per_cycle = 3  # Scrape 3 pages per cycle
        self.max_total_pages = 20  # Total pages to cycle through
        self.page_offset = self.load_page_offset()  # Load persisted offset

        self.cycle_count = 0
        self.last_run_time = None

        print(f"💰 Jared price limit: £80 (${self.max_price_usd:.2f} USD / ¥{self.max_price_jpy:,} JPY)")

    def load_page_offset(self):
        """Load the current page offset from database (persists across Railway redeploys)"""
        offset = self.load_scraper_state('page_offset', default=0)
        print(f"📖 Jared page offset loaded: {offset}")
        return offset

    def save_page_offset(self):
        """Save the current page offset to database (persists across Railway redeploys)"""
        self.save_scraper_state('page_offset', self.page_offset)
        print(f"💾 Jared page offset saved: {self.page_offset}")

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
        """Override to load jared_brands.json instead of brands.json"""
        try:
            jared_brands_file = "jared_brands.json"
            if os.path.exists(jared_brands_file):
                with open(jared_brands_file, 'r', encoding='utf-8') as f:
                    print(f"✅ Loading Jared brands from {jared_brands_file}")
                    return json.load(f)
            else:
                print(f"❌ {jared_brands_file} not found!")
                return {}
        except Exception as e:
            print(f"⚠️ Could not load Jared brand data: {e}")
            return {}

    async def scrape_jared_page_async(self, keyword, page, brand_info):
        """Scrape a single page for Jared custom listings"""
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
            price_filtered = 0

            for item in items:
                auction_data = self.extract_auction_data(item)
                if auction_data:
                    # Check if already seen
                    if auction_data['auction_id'] in self.seen_ids:
                        duplicates_skipped += 1
                        continue

                    # PRICE FILTER: Only items under £80 ($108.12 USD / ¥16,850 JPY)
                    if auction_data['price_jpy'] > self.max_price_jpy:
                        price_filtered += 1
                        print(f"   💸 Filtered out (over £80): ¥{auction_data['price_jpy']:,} (${auction_data['price_usd']:.2f})")
                        continue

                    listings.append(auction_data)
                    self.seen_ids.add(auction_data['auction_id'])

            print(f"📄 Page {page} for '{keyword}': Found {len(listings)} new items ({duplicates_skipped} duplicates, {price_filtered} over price limit)")
            if duplicates_skipped > 0:
                print(f"✅ Database working! Skipped {duplicates_skipped} already-seen items")
            return listings, len(items) >= 45  # Continue if page has enough items

        except Exception as e:
            print(f"❌ Error scraping page {page} for '{keyword}': {e}")
            return [], False

    async def scrape_brand_jared_async(self, brand, brand_info):
        """Scrape all listings for a specific Jared brand"""
        all_listings = []

        # Get current page range from rotating pagination
        start_page, end_page = self.get_current_page_range()

        # Use primary variant as keyword
        primary_variant = brand_info['variants'][0]

        print(f"🔍 Scanning {brand} for Jared channel (pages {start_page}-{end_page}, max £80)")

        # Process pages sequentially to avoid rate limiting
        for page in range(start_page, end_page + 1):
            listings, should_continue = await self.scrape_jared_page_async(
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

    async def run_jared_cycle_async(self):
        """Run a complete Jared scraping cycle"""
        cycle_start = time.time()
        self.cycle_count += 1
        current_time = datetime.now(timezone.utc)

        print(f"\n👤 Starting Jared cycle #{self.cycle_count} (ASYNC)")
        print(f"🎯 Target Channel: {self.target_channel}")
        print(f"💰 Price Limit: £80 (${self.max_price_usd:.2f} USD / ¥{self.max_price_jpy:,} JPY)")
        print(f"🕐 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        total_found = 0
        total_sent = 0

        # Process brands sequentially to avoid overwhelming Yahoo
        all_brand_listings = []

        for brand, brand_info in self.brand_data.items():
            try:
                print(f"\n{'='*60}")
                print(f"Processing Jared brand: {brand}")
                print(f"{'='*60}")

                listings = await self.scrape_brand_jared_async(brand, brand_info)
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
                    # Add Jared-specific metadata
                    listing['is_new_listing'] = True
                    listing['scraper_source'] = 'jared_scraper'  # Critical for routing
                    listing['listing_type'] = 'jared_custom'
                    listing['target_channel'] = 'jared'  # Force to jared channel

                    # Enhanced logging
                    print(f"🔍 Processing Jared listing: {listing['title'][:50]}...")
                    print(f"   💰 Price: ${listing['price_usd']:.2f} (¥{listing['price_jpy']:,})")
                    print(f"   🏷️ Brand: {listing['brand']}")
                    print(f"   📊 Quality Score: {listing.get('deal_quality', 0):.2f}")
                    print(f"   👤 Target: #{self.target_channel}")

                    # Send to Discord bot (will be routed to #jared only)
                    if self.send_to_discord(listing):
                        total_sent += 1
                        print(f"✅ Sent Jared listing to Discord bot: {listing['title'][:50]}...")

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
        print(f"\n📊 Jared Cycle #{self.cycle_count} Complete (ASYNC):")
        print(f"   ⏱️ Duration: {cycle_duration:.1f}s")
        print(f"   🔍 Found: {total_found} items")
        print(f"   📤 Sent: {total_sent} items")
        print(f"   💾 Tracking: {len(self.seen_ids)} seen items")
        print(f"   🎯 Target: #{self.target_channel}")
        print(f"   👤 Customer: Jared")
        print(f"   📦 Brands: {len(self.brand_data)}")
        print(f"   💰 Price Limit: £80 (${self.max_price_usd:.2f} / ¥{self.max_price_jpy:,})")

        return total_sent  # Return count for smart retry logic

    def run_jared_cycle(self):
        """Sync wrapper for Railway deployment with smart retry logic"""
        max_retries = 3  # Max retry cycles if insufficient results found
        retry_count = 0

        while retry_count <= max_retries:
            total_sent = asyncio.run(self.run_jared_cycle_async())

            # If we sent 4+ listings, we're done
            if total_sent >= 4:
                print(f"✅ Successfully sent {total_sent} listings, waiting for next scheduled run")
                break

            # If we got 1-3 listings, retry to find more
            if total_sent > 0:
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"⚠️ Only sent {total_sent} listing(s). Retry {retry_count}/{max_retries} - running another cycle to find more...")
                    time.sleep(5)  # Brief pause before retry
                else:
                    print(f"✅ Sent {total_sent} listing(s) after {max_retries} retries, accepting and waiting for next scheduled run")
                    break
            else:
                # No results - retry if we haven't hit max retries
                retry_count += 1
                if retry_count <= max_retries:
                    print(f"⚠️ No listings sent. Retry {retry_count}/{max_retries} - running another cycle immediately...")
                    time.sleep(5)  # Brief pause before retry
                else:
                    print(f"❌ No results after {max_retries} retries. Will wait for next scheduled run.")

    def start_scheduler(self):
        """Start the scheduler for Jared scraping"""
        start_page, end_page = self.get_current_page_range()
        print(f"🚀 Starting Jared Custom Scraper")
        print(f"👤 Customer: Jared")
        print(f"🎯 Target Channel: #{self.target_channel}")
        print(f"📦 Brands: {len(self.brand_data)}")
        print(f"💰 Price Limit: £80 (${self.max_price_usd:.2f} USD / ¥{self.max_price_jpy:,} JPY)")
        print(f"📅 Schedule: Every 15 minutes")
        print(f"🔄 Sort Order: Newest first")
        print(f"📄 Pagination: Rotating through pages {start_page}-{end_page} (cycles through 1-{self.max_total_pages})")
        print(f"⚠️ ISOLATED: Does not interfere with main brand routing")

        # List loaded brands
        print(f"\n📋 Jared Brands Loaded:")
        for brand in self.brand_data.keys():
            print(f"   - {brand}")

        # Schedule every 15 minutes
        schedule.every(15).minutes.do(self.run_jared_cycle)

        # Run immediately
        self.run_jared_cycle()

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)

def main():
    scraper = JaredScraper()

    # Start health server in background
    health_thread = threading.Thread(target=scraper.run_health_server, daemon=True)
    health_thread.start()
    print(f"🌐 Health server started on port {os.environ.get('PORT', 8000)}")

    # Start scraping
    try:
        scraper.start_scheduler()
    except KeyboardInterrupt:
        print("\n🛑 Jared Scraper stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
