"""
Quick test script to verify Discord webhook is working
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from discord_notifier import DiscordNotifier
    from config import get_discord_webhook_url
    from models import Listing
except ImportError:
    from discord_notifier import DiscordNotifier
    from config import get_discord_webhook_url
    from models import Listing

from datetime import datetime, timezone


async def test_discord():
    """Test Discord webhook with a sample listing"""
    webhook_url = get_discord_webhook_url()
    
    if not webhook_url:
        print("❌ DISCORD_WEBHOOK_URL not set in .env file")
        return False
    
    print(f"✅ Discord webhook URL loaded")
    print(f"   Testing webhook connection...")
    
    # Create a test listing
    test_listing = Listing(
        market="yahoo",
        external_id="test123",
        title="🧪 TEST LISTING - Discord Integration Test",
        price_jpy=15000,  # Should show as green (< ¥20,000)
        brand="Test Brand",
        url="https://auctions.yahoo.co.jp",
        image_url=None,
        listing_type="auction",
        seller_id="test_seller",
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    # Create notifier and send test message
    notifier = DiscordNotifier(webhook_url)
    
    try:
        print(f"📤 Sending test message to Discord...")
        success = await notifier.send_listing(test_listing)
        
        if success:
            print(f"✅ Test message sent successfully!")
            print(f"   Check your Discord channel to see the embed")
            return True
        else:
            print(f"❌ Failed to send test message")
            return False
    finally:
        await notifier.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Discord Webhook Test")
    print("=" * 60)
    result = asyncio.run(test_discord())
    print("=" * 60)
    sys.exit(0 if result else 1)

