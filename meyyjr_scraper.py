#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meyyjr Custom Scraper - Customer-specific scraper for #meyyjr channel
Posts only to #meyyjr channel, uses meyyjr_brands.json for brand list
Price filter: Max 60 EUR = 11,000 JPY
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

class MeyyjrScraper(YahooScraperBase):
    def __init__(self):
        super().__init__("meyyjr_scraper")
        self.target_channel = "meyyjr"  # Exact Discord channel name (no emoji)
        self.max_pages_initial = 2  # Conservative page count
        self.max_pages_regular = 1  # Even more conservative for regular runs
        self.cycle_count = 0
        self.last_run_time = None

        # Price filter: 60 EUR = 11,000 JPY
        self.max_price_jpy = 11000
        self.max_price_eur = 60

        print(f"💰 Price filter enabled: Max ¥{self.max_price_jpy:,} ({self.max_price_eur} EUR)")

    def load_brand_data(self):
        """Override to load meyyjr_brands.json instead of brands.json"""
        try:
            meyyjr_brands_file = "meyyjr_brands.json"
            if os.path.exists(meyyjr_brands_file):
                with open(meyyjr_brands_file, 'r', encoding='utf-8') as f:
                    print(f"✅ Loading Meyyjr brands from {meyyjr_brands_file}")
                    return json.load(f)
            else:
                print(f"❌ {meyyjr_brands_file} not found!")
                return {}
        except Exception as e:
            print(f"⚠️ Could not load Meyyjr brand data: {e}")
            return {}

    def extract_auction_data_with_price_filter(self, item):
        """Extract auction data and apply price filter"""
        try:
            # Use parent class method to extract data
            auction_data = self.extract_auction_data(item)

            if not auction_data:
                return None

            # Apply price filter BEFORE adding to seen_ids
            price_jpy = auction_data.get('price_jpy', 0)

            if price_jpy > self.max_price_jpy:
                print(f"🚫 Price filter: ¥{price_jpy:,} exceeds ¥{self.max_price_jpy:,} limit ({self.max_price_eur} EUR)")
                print(f"   Item: {auction_data.get('title', '')[:50]}...")
                self.stats['price_blocked'] += 1
                return None
            else:
                print(f"✅ Price OK: ¥{price_jpy:,} (under ¥{self.max_price_jpy:,} limit)")

            return auction_data

        except Exception as e:
            print(f"❌ Error extracting auction data with price filter: {e}")
            return None

    async def scrape_meyyjr_page_async(self, keyword, page, brand_info):
        """Scrape a single page for Meyyjr custom listings"""
        try:
            # Build URL for both auctions and fixed price, sorted by newest
            url = self.build_search_url(
                keyword=keyword,
                page=page,
                fixed_type=3,  # Both auction and fixed price (CRITICAL)
                sort_type="new",  # CRITICAL: Sort by newest
                sort_order="d",  # CRITICAL: Descending (newest first)
                
            )

            print(f"🔍 Fetching URL: {url}")

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

            for item in items:
                # Use price filtering extraction method
                auction_data = self.extract_auction_data_with_price_filter(item)

                if auction_data and auction_data['auction_id'] not in self.seen_ids:
                    listings.append(auction_data)
                    self.seen_ids.add(auction_data['auction_id'])

            print(f"📄 Page {page} for '{keyword}': Found {len(listings)} new items (after price filter)")
            return listings, len(items) >= 45  # Continue if page has enough items

        except Exception as e:
            print(f"❌ Error scraping page {page} for '{keyword}': {e}")
            return [], False

    async def scrape_brand_meyyjr_async(self, brand, brand_info):
        """Scrape all listings for a specific Meyyjr brand"""
        all_listings = []

        # Determine max pages based on cycle count
        max_pages = self.max_pages_initial if self.cycle_count < 3 else self.max_pages_regular

        # Use primary variant as keyword
        primary_variant = brand_info['variants'][0]

        print(f"🔍 Scanning {brand} for Meyyjr channel (up to {max_pages} pages)")
        print(f"   💰 Max price: ¥{self.max_price_jpy:,} ({self.max_price_eur} EUR)")

        # Process pages sequentially to avoid rate limiting
        for page in range(1, max_pages + 1):
            listings, should_continue = await self.scrape_meyyjr_page_async(
                primary_variant, page, brand_info
            )

            all_listings.extend(listings)

            # Stop if page isn't full
            if not should_continue:
                print(f"🛑 Stopping pagination for {brand} at page {page}")
                break

            # Polite delay between pages
            if page < max_pages:
                await asyncio.sleep(2.5)

        return all_listings

    async def run_meyyjr_cycle_async(self):
        """Run a complete Meyyjr scraping cycle"""
        cycle_start = time.time()
        self.cycle_count += 1
        current_time = datetime.now(timezone.utc)

        print(f"\n👤 Starting Meyyjr cycle #{self.cycle_count} (ASYNC)")
        print(f"🎯 Target Channel: {self.target_channel}")
        print(f"💰 Price Filter: Max ¥{self.max_price_jpy:,} ({self.max_price_eur} EUR)")
        print(f"🔄 Sort: NEWEST FIRST (critical)")
        print(f"🕐 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        total_found = 0
        total_sent = 0

        # Process brands sequentially to avoid overwhelming Yahoo
        all_brand_listings = []

        for brand, brand_info in self.brand_data.items():
            try:
                print(f"\n{'='*60}")
                print(f"Processing Meyyjr brand: {brand}")
                print(f"{'='*60}")

                listings = await self.scrape_brand_meyyjr_async(brand, brand_info)
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
                    # Add Meyyjr-specific metadata
                    listing['is_new_listing'] = True
                    listing['scraper_source'] = 'meyyjr_scraper'  # Critical for routing
                    listing['listing_type'] = 'meyyjr_custom'
                    listing['target_channel'] = 'meyyjr'  # Force to meyyjr channel
                    listing['price_filter_applied'] = True
                    listing['max_price_jpy'] = self.max_price_jpy

                    # Enhanced logging
                    print(f"🔍 Processing Meyyjr listing: {listing['title'][:50]}...")
                    print(f"   💰 Price: ${listing['price_usd']:.2f} (¥{listing['price_jpy']:,}) - UNDER ¥{self.max_price_jpy:,} ✅")
                    print(f"   🏷️ Brand: {listing['brand']}")
                    print(f"   📊 Quality Score: {listing.get('deal_quality', 0):.2f}")
                    print(f"   👤 Target: #{self.target_channel}")

                    # Send to Discord bot (will be routed to #meyyjr only)
                    if self.send_to_discord(listing):
                        total_sent += 1
                        print(f"✅ Sent Meyyjr listing to Discord bot: {listing['title'][:50]}...")

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

        # Update last run time
        self.last_run_time = current_time

        cycle_duration = time.time() - cycle_start
        print(f"\n📊 Meyyjr Cycle #{self.cycle_count} Complete (ASYNC):")
        print(f"   ⏱️ Duration: {cycle_duration:.1f}s")
        print(f"   🔍 Found: {total_found} items (after price filter)")
        print(f"   📤 Sent: {total_sent} items")
        print(f"   💾 Tracking: {len(self.seen_ids)} seen items")
        print(f"   💰 Price blocked: {self.stats.get('price_blocked', 0)} items")
        print(f"   🎯 Target: #{self.target_channel}")
        print(f"   👤 Customer: Meyyjr")
        print(f"   📦 Brands: {len(self.brand_data)}")

    def run_meyyjr_cycle(self):
        """Sync wrapper for Railway deployment"""
        asyncio.run(self.run_meyyjr_cycle_async())

    def start_scheduler(self):
        """Start the scheduler for Meyyjr scraping"""
        print(f"🚀 Starting Meyyjr Custom Scraper")
        print(f"👤 Customer: Meyyjr")
        print(f"🎯 Target Channel: #{self.target_channel}")
        print(f"📦 Brands: {len(self.brand_data)}")
        print(f"💰 Price Filter: Max ¥{self.max_price_jpy:,} ({self.max_price_eur} EUR)")
        print(f"📅 Schedule: Every 15 minutes")
        print(f"🔄 Sort Order: NEWEST FIRST (critical)")
        print(f"⚠️ ISOLATED: Does not interfere with main brand routing")

        # List loaded brands
        print(f"\n📋 Meyyjr Brands Loaded:")
        for brand in self.brand_data.keys():
            print(f"   - {brand}")

        # Schedule every 15 minutes
        schedule.every(15).minutes.do(self.run_meyyjr_cycle)

        # Run immediately
        self.run_meyyjr_cycle()

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)

def main():
    scraper = MeyyjrScraper()

    # Start health server in background
    health_thread = threading.Thread(target=scraper.run_health_server, daemon=True)
    health_thread.start()
    print(f"🌐 Health server started on port {os.environ.get('PORT', 8000)}")

    # Start scraping
    try:
        scraper.start_scheduler()
    except KeyboardInterrupt:
        print("\n🛑 Meyyjr Scraper stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
