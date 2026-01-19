"""
Quick test - runs 1 cycle and sends top listings to Discord
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from scrapers.yahoo_scraper import YahooScraper
    from config import get_discord_webhook_url, MAX_ALERTS_PER_CYCLE
    from discord_notifier import DiscordNotifier
except ImportError:
    from v2.scrapers.yahoo_scraper import YahooScraper
    from v2.config import get_discord_webhook_url, MAX_ALERTS_PER_CYCLE
    from v2.discord_notifier import DiscordNotifier

async def quick_test():
    """Run one scraper cycle and send top listings to Discord"""
    print("=" * 60)
    print("Quick Discord Test - Single Cycle")
    print("=" * 60)
    
    # Check Discord webhook
    webhook_url = get_discord_webhook_url()
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set in .env file")
        return
    
    print(f"✅ Discord webhook configured")
    print(f"📦 Scraping brands: Supreme, Bape, Nike")
    print(f"📤 Will send top {MAX_ALERTS_PER_CYCLE} listings to Discord\n")
    
    notifier = DiscordNotifier(webhook_url)
    
    try:
        async with YahooScraper() as scraper:
            listings = await scraper.scrape(
                brands=["Supreme", "Bape", "Nike"],
                max_price=None
            )
            
            print(f"✅ Found {len(listings)} listings")
            
            if listings:
                # Sort by price (lowest first) and take top N
                sorted_listings = sorted(listings, key=lambda x: x.price_jpy)
                top_listings = sorted_listings[:MAX_ALERTS_PER_CYCLE]
                
                print(f"📤 Sending top {len(top_listings)} listings to Discord...")
                stats = await notifier.send_listings(top_listings)
                
                print(f"\n✅ Complete!")
                print(f"   Sent: {stats['sent']} alerts")
                print(f"   Failed: {stats['failed']} alerts")
                print(f"   Check your Discord channel!")
            else:
                print("⚠️  No listings found to send")
    finally:
        await notifier.close()

if __name__ == "__main__":
    asyncio.run(quick_test())

