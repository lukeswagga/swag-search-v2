"""
Test script for Discord bot alerts (channel + DM)

Tests:
- Sending alerts to #v2 channel
- Sending personalized DMs to users
- Batch processing with rate limiting
"""
import asyncio
import logging
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from discord_bot import SwagSearchBot
    from config import get_discord_bot_token, get_discord_channel_id
    from models import Listing
except ImportError:
    from discord_bot import SwagSearchBot
    from config import get_discord_bot_token, get_discord_channel_id
    from models import Listing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_bot_alerts():
    """Test Discord bot alerts (channel + DM)"""
    
    # Get bot token and channel ID
    bot_token = get_discord_bot_token()
    channel_id = get_discord_channel_id()
    
    if not bot_token:
        logger.error("❌ DISCORD_BOT_TOKEN not set - cannot test bot")
        logger.error("   Set DISCORD_BOT_TOKEN environment variable to test")
        return
    
    if not channel_id:
        logger.warning("⚠️  DISCORD_CHANNEL_ID not set - channel alerts will be skipped")
        logger.warning("   Set DISCORD_CHANNEL_ID environment variable to test channel alerts")
        logger.warning("   To get channel ID: Enable Developer Mode → Right-click #v2 → Copy Channel ID")
    
    # Create test listing
    test_listing = Listing(
        title="Test Listing - Rick Owens Geobasket Sneakers",
        brand="Rick Owens",
        price_jpy=35000,
        market="yahoo",
        listing_type="buy_it_now",
        external_id="test12345",
        url="https://page.auctions.yahoo.co.jp/jp/auction/test12345",
        image_url="https://example.com/image.jpg"
    )
    
    # Initialize bot
    logger.info("🚀 Initializing Discord bot...")
    bot = SwagSearchBot(bot_token)
    
    try:
        # Start bot
        await bot.start_bot()
        
        if not bot.is_ready():
            logger.error("❌ Bot failed to start - cannot test")
            return
        
        logger.info("✅ Bot is ready!")
        
        # Test 1: Send to channel
        if channel_id:
            logger.info(f"\n{'='*60}")
            logger.info("TEST 1: Sending to channel")
            logger.info(f"{'='*60}")
            logger.info(f"Channel ID: {channel_id}")
            logger.info(f"Listing: {test_listing.title[:50]}...")
            
            channel_result = await bot.send_alert(
                listing=test_listing,
                channel_id=channel_id
            )
            
            if channel_result['channel_sent']:
                logger.info("✅ Channel alert sent successfully!")
            else:
                logger.error("❌ Failed to send channel alert")
                logger.error("   Check bot permissions and channel access")
        else:
            logger.info(f"\n{'='*60}")
            logger.info("TEST 1: SKIPPED - Channel ID not set")
            logger.info(f"{'='*60}")
            logger.info("   Set DISCORD_CHANNEL_ID environment variable to test channel alerts")
        
        # Test 2: Send DM to a user (replace with actual user ID for testing)
        test_user_id = os.getenv('TEST_USER_ID')  # Set TEST_USER_ID in env for testing
        if test_user_id:
            logger.info(f"\n{'='*60}")
            logger.info("TEST 2: Sending DM to user")
            logger.info(f"{'='*60}")
            logger.info(f"User ID: {test_user_id}")
            logger.info(f"Listing: {test_listing.title[:50]}...")
            
            dm_result = await bot.send_alert(
                listing=test_listing,
                user_ids=[test_user_id],
                filter_names={test_user_id: "Rick Owens Steals"}
            )
            
            if dm_result['dms_sent'] > 0:
                logger.info(f"✅ DM sent successfully to user {test_user_id}!")
            else:
                logger.error(f"❌ Failed to send DM to user {test_user_id}")
                logger.error("   User may have DMs disabled or blocked the bot")
        else:
            logger.info(f"\n{'='*60}")
            logger.info("TEST 2: SKIPPED - User ID not set")
            logger.info(f"{'='*60}")
            logger.info("   Set TEST_USER_ID environment variable to test DM alerts")
        
        # Test 3: Send batch of alerts
        logger.info(f"\n{'='*60}")
        logger.info("TEST 3: Batch sending")
        logger.info(f"{'='*60}")
        logger.info(f"Creating 3 test listings...")
        if channel_id:
            logger.info(f"  - Will send to channel: {channel_id}")
        else:
            logger.info(f"  - Channel ID not set (will skip channel sends)")
        if test_user_id:
            logger.info(f"  - Will send DMs to user: {test_user_id}")
        else:
            logger.info(f"  - User ID not set (will skip DM sends)")
        
        batch_alerts = []
        for i in range(3):
            listing = Listing(
                title=f"Test Listing {i+1} - Sample Item",
                brand="Test Brand",
                price_jpy=20000 + (i * 5000),
                market="yahoo",
                listing_type="buy_it_now",
                external_id=f"test{i+1}",
                url=f"https://page.auctions.yahoo.co.jp/jp/auction/test{i+1}",
                image_url="https://example.com/image.jpg"
            )
            
            alert_dict = {
                'listing': listing,
                'channel_id': channel_id if channel_id else None
            }
            
            if test_user_id:
                alert_dict['user_ids'] = [test_user_id]
                alert_dict['filter_names'] = {test_user_id: f"Test Filter {i+1}"}
            
            batch_alerts.append(alert_dict)
        
        logger.info(f"Processing batch of {len(batch_alerts)} alerts...")
        batch_result = await bot.send_batch(batch_alerts)
        
        logger.info(f"\n📊 Batch results:")
        logger.info(f"   Channel sent: {batch_result['channel_sent']}")
        logger.info(f"   Channel failed: {batch_result['channel_failed']}")
        logger.info(f"   DMs sent: {batch_result['dms_sent']}")
        logger.info(f"   DMs failed: {batch_result['dms_failed']}")
        
        if batch_result['channel_sent'] == 0 and batch_result['dms_sent'] == 0:
            logger.warning("\n⚠️  No alerts were sent!")
            logger.warning("   This is expected if:")
            logger.warning("   - DISCORD_CHANNEL_ID is not set (for channel alerts)")
            logger.warning("   - TEST_USER_ID is not set (for DM alerts)")
            logger.warning("\n   Set at least one of these to see actual alerts being sent")
        
        # Get final stats
        stats = bot.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info("Bot Statistics")
        logger.info(f"{'='*60}")
        logger.info(f"Channel messages sent: {stats['channel_sent']}")
        logger.info(f"DMs sent: {stats['dms_sent']}")
        logger.info(f"Total sent: {stats['total_sent']}")
        logger.info(f"Total errors: {stats['total_errors']}")
        logger.info(f"DMs disabled: {stats['dm_disabled']}")
        logger.info(f"Blocked users: {stats['blocked']}")
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
    finally:
        # Close bot
        await bot.close()
        logger.info("🔌 Bot closed")


if __name__ == "__main__":
    logger.info("🧪 Starting Discord bot alerts test...")
    logger.info("")
    logger.info("📋 Requirements:")
    logger.info("  ✅ DISCORD_BOT_TOKEN must be set (required)")
    logger.info("  ⚠️  DISCORD_CHANNEL_ID should be set (for channel test)")
    logger.info("  ⚠️  TEST_USER_ID should be set (for DM test)")
    logger.info("")
    logger.info("📝 To get channel ID:")
    logger.info("  1. Enable Developer Mode (User Settings → Advanced → Developer Mode)")
    logger.info("  2. Right-click your #v2 channel → Copy Channel ID")
    logger.info("  3. Set DISCORD_CHANNEL_ID environment variable")
    logger.info("")
    
    asyncio.run(test_bot_alerts())

