#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lowest Price Scraper - Finds cheapest auction listings under ¥4,000
Sends to #lowest-price channel (Instant tier only)
All embeds use GREEN color (0x00FF00) - these are steals by definition
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

class LowestPriceScraper(YahooScraperBase):
    def __init__(self):
        super().__init__("lowest_price_scraper")
        self.target_channel = "💚-lowest-price"
        self.max_price_jpy = 4000  # Only items under ¥4,000
        self.max_price_usd = 4000 / 156.25  # Hardcoded exchange rate: ¥100 = $0.64
        self.cycle_count = 0
        self.last_run_time = None

        # Override exchange rate to hardcoded value (¥100 = $0.64 USD)
        # 1 USD = 156.25 JPY (100 / 0.64)
        self.current_usd_jpy_rate = 156.25
        print(f"💱 Using hardcoded exchange rate: 1 USD = {self.current_usd_jpy_rate:.2f} JPY")
        print(f"💰 Max price filter: ¥{self.max_price_jpy:,} (${self.max_price_usd:.2f})")

    async def scrape_lowest_price_page_async(self, keyword, page, brand_info):
        """Async version: Scrape a single page for lowest price auction listings"""
        try:
            # Build URL for auctions only, sorted by price ascending (lowest first)
            url = self.build_search_url(
                keyword=keyword,
                page=page,
                fixed_type=2,  # Auctions only
                sort_type="price",
                sort_order="a",  # Ascending (lowest price first)
            )

            # Use async fetch
            html, success = await self.fetch_page_async(url)
            if not success or not html:
                return [], True

            soup = BeautifulSoup(html, "html.parser")
            items = soup.select("li.Product")

            if not items:
                print(f"🔚 No items found on page {page} for '{keyword}'")
                return [], False

            listings = []
            should_continue = True

            for item in items:
                auction_data = self.extract_auction_data(item)
                if not auction_data:
                    continue

                # Check if auction_id already seen
                if auction_data['auction_id'] in self.seen_ids:
                    continue

                # Price filter: Only items under ¥4,000
                if auction_data['price_jpy'] > self.max_price_jpy:
                    # Since we're sorting by price ascending, if we hit a price over the limit,
                    # we can stop scraping this keyword entirely
                    print(f"🛑 Price exceeded ¥{self.max_price_jpy:,} (found ¥{auction_data['price_jpy']:,})")
                    print(f"   Stopping pagination for '{keyword}' - all remaining items will be too expensive")
                    should_continue = False
                    break

                # Add to listings
                listings.append(auction_data)
                self.seen_ids.add(auction_data['auction_id'])

            print(f"📄 Page {page} for '{keyword}': Found {len(listings)} items under ¥{self.max_price_jpy:,}")
            return listings, should_continue and len(items) >= 90  # Continue if page is full AND price limit not exceeded

        except Exception as e:
            print(f"❌ Error scraping page {page} for '{keyword}': {e}")
            return [], False

    def scrape_lowest_price_page(self, keyword, page, brand_info):
        """Sync version: Scrape a single page for lowest price auction listings (backward compatibility)"""
        try:
            # Build URL for auctions only, sorted by price ascending (lowest first)
            url = self.build_search_url(
                keyword=keyword,
                page=page,
                fixed_type=2,  # Auctions only
                sort_type="price",
                sort_order="a",  # Ascending (lowest price first)
            )

            headers = self.get_request_headers()
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code} for {keyword} page {page}")
                return [], True

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("li.Product")

            if not items:
                print(f"🔚 No items found on page {page} for '{keyword}'")
                return [], False

            listings = []
            should_continue = True

            for item in items:
                auction_data = self.extract_auction_data(item)
                if not auction_data:
                    continue

                # Check if auction_id already seen
                if auction_data['auction_id'] in self.seen_ids:
                    continue

                # Price filter: Only items under ¥4,000
                if auction_data['price_jpy'] > self.max_price_jpy:
                    # Since we're sorting by price ascending, if we hit a price over the limit,
                    # we can stop scraping this keyword entirely
                    print(f"🛑 Price exceeded ¥{self.max_price_jpy:,} (found ¥{auction_data['price_jpy']:,})")
                    print(f"   Stopping pagination for '{keyword}' - all remaining items will be too expensive")
                    should_continue = False
                    break

                # Add to listings
                listings.append(auction_data)
                self.seen_ids.add(auction_data['auction_id'])

            print(f"📄 Page {page} for '{keyword}': Found {len(listings)} items under ¥{self.max_price_jpy:,}")
            return listings, should_continue and len(items) >= 90  # Continue if page is full AND price limit not exceeded

        except Exception as e:
            print(f"❌ Error scraping page {page} for '{keyword}': {e}")
            return [], False

    async def scrape_brand_lowest_prices_async(self, brand, brand_info):
        """Async version: Scrape all lowest price listings for a specific brand"""
        all_listings = []
        max_pages = 10  # Reasonable limit since we stop at ¥4,000

        # Use primary variant as keyword
        primary_variant = brand_info['variants'][0]

        print(f"🔍 Scanning {brand} for lowest price items (up to {max_pages} pages, max ¥{self.max_price_jpy:,})")

        # Process pages sequentially to avoid rate limiting
        for page in range(1, max_pages + 1):
            listings, should_continue = await self.scrape_lowest_price_page_async(
                primary_variant, page, brand_info
            )

            all_listings.extend(listings)

            # Stop if we hit the price limit or page isn't full
            if not should_continue:
                print(f"🛑 Stopping pagination for {brand} at page {page}")
                break

            # Polite delay between pages (2-3 seconds to avoid rate limiting)
            if page < max_pages:
                await asyncio.sleep(2.5)

        return all_listings

    def scrape_brand_lowest_prices(self, brand, brand_info):
        """Sync version: Scrape all lowest price listings for a specific brand (backward compatibility)"""
        all_listings = []
        max_pages = 10  # Reasonable limit since we stop at ¥4,000

        # Use primary variant as keyword
        primary_variant = brand_info['variants'][0]

        print(f"🔍 Scanning {brand} for lowest price items (up to {max_pages} pages, max ¥{self.max_price_jpy:,})")

        for page in range(1, max_pages + 1):
            listings, should_continue = self.scrape_lowest_price_page(
                primary_variant, page, brand_info
            )

            all_listings.extend(listings)

            # Stop if we hit the price limit or page isn't full
            if not should_continue:
                print(f"🛑 Stopping pagination for {brand} at page {page}")
                break

            # Rate limiting
            if page < max_pages:
                time.sleep(1)

        return all_listings

    async def run_lowest_price_cycle_async(self):
        """Async version: Run a complete lowest price scraping cycle"""
        cycle_start = time.time()
        self.cycle_count += 1
        current_time = datetime.now(timezone.utc)

        print(f"\n💚 Starting lowest price cycle #{self.cycle_count} (ASYNC)")
        print(f"🕐 Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"💰 Max price: ¥{self.max_price_jpy:,} (${self.max_price_usd:.2f})")

        total_found = 0
        total_sent = 0

        # Process brands sequentially to avoid overwhelming Yahoo
        all_brand_listings = []

        for brand, brand_info in self.brand_data.items():
            try:
                print(f"\n{'='*60}")
                print(f"Processing brand: {brand}")
                print(f"{'='*60}")

                listings = await self.scrape_brand_lowest_prices_async(brand, brand_info)
                all_brand_listings.append((brand, listings))

                # Polite delay between brands (3 seconds to be respectful)
                await asyncio.sleep(3)

            except Exception as e:
                print(f"❌ Error processing {brand}: {e}")
                continue

        # Process all listings with rate limiting for Discord API
        for brand, listings in all_brand_listings:
            try:
                for listing in listings:
                    # Add scraper-specific metadata
                    listing['is_lowest_price'] = True
                    listing['scraper_source'] = 'lowest_price_scraper'
                    listing['listing_type'] = 'lowest_price'
                    listing['embed_color'] = 0x00FF00  # GREEN - these are steals!

                    # Enhanced logging for debugging
                    print(f"🔍 Processing lowest price listing: {listing['title'][:50]}...")
                    print(f"   💰 Price: ${listing['price_usd']:.2f} (¥{listing['price_jpy']:,})")
                    print(f"   🏷️ Brand: {listing['brand']}")
                    print(f"   📊 Quality Score: {listing.get('deal_quality', 0):.2f}")
                    print(f"   💚 LOWEST PRICE - GREEN EMBED")

                    # Send to Discord bot (let it handle channel routing)
                    if self.send_to_discord(listing):
                        total_sent += 1
                        print(f"✅ Sent lowest price listing to Discord bot: {listing['title'][:50]}...")

                        # CRITICAL: Rate limit 1 post per 2 seconds to respect Discord API
                        await asyncio.sleep(2.0)

                    total_found += 1

            except Exception as e:
                print(f"❌ Error processing {brand}: {e}")
                continue

        # Close async session
        await self.close_session()

        # Save seen items
        self.save_seen_items()

        # ANALYTICS: Show filtering statistics
        self.analyze_filtering()

        # Cleanup seen_ids if needed
        self.cleanup_old_seen_ids()

        # Update last run time
        self.last_run_time = current_time

        cycle_duration = time.time() - cycle_start
        print(f"\n📊 Lowest Price Cycle #{self.cycle_count} Complete (ASYNC):")
        print(f"   ⏱️ Duration: {cycle_duration:.1f}s")
        print(f"   🔍 Found: {total_found} items under ¥{self.max_price_jpy:,}")
        print(f"   📤 Sent: {total_sent} items")
        print(f"   💾 Tracking: {len(self.seen_ids)} seen items")
        print(f"   🚫 Enhanced spam filtering applied")
        print(f"   🎯 Target: {self.target_channel}")
        print(f"   💚 All embeds: GREEN (0x00FF00)")
        print(f"   ⏱️ Rate limit: 1 post per 2 seconds")
        print(f"   ⚡ Async mode: 3-5x faster with concurrent requests")

    def run_lowest_price_cycle(self):
        """Sync wrapper: Run a complete lowest price scraping cycle (for Railway deployment)"""
        asyncio.run(self.run_lowest_price_cycle_async())

    def start_scheduler(self):
        """Start the scheduler for lowest price scraping"""
        print(f"🚀 Starting Lowest Price Scraper")
        print(f"💚 Target Channel: {self.target_channel}")
        print(f"📅 Schedule: Every 15 minutes")
        print(f"🔄 Sort Order: Price ascending (lowest first)")
        print(f"💰 Max Price: ¥{self.max_price_jpy:,} (${self.max_price_usd:.2f})")
        print(f"💱 Exchange Rate: ¥100 = $0.64 (hardcoded)")

        # Schedule every 15 minutes
        schedule.every(15).minutes.do(self.run_lowest_price_cycle)

        # Run immediately
        self.run_lowest_price_cycle()

        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)

def main():
    scraper = LowestPriceScraper()

    # Start health server in background
    health_thread = threading.Thread(target=scraper.run_health_server, daemon=True)
    health_thread.start()
    print(f"🌐 Health server started on port {os.environ.get('PORT', 8000)}")

    # Start scraping
    try:
        scraper.start_scheduler()
    except KeyboardInterrupt:
        print("\n🛑 Lowest Price Scraper stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
