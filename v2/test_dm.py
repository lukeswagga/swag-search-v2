"""
Test script for Discord bot DM functionality

Usage:
1. Set DISCORD_BOT_TOKEN environment variable
2. Get your Discord user ID:
   - Discord settings → Advanced → Enable Developer Mode
   - Right-click your name → Copy User ID
3. Update YOUR_DISCORD_USER_ID below
4. Run: python test_dm.py
"""
import asyncio
import logging
import os
import sys

# Add parent directory to path for imports
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from v2.discord_bot import SwagSearchBot
    from v2.config import get_discord_bot_token
    from v2.models import Listing
except ImportError:
    from discord_bot import SwagSearchBot
    from config import get_discord_bot_token
    from models import Listing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ⚠️ UPDATE THIS WITH YOUR DISCORD USER ID (NOT YOUR USERNAME!)
# Your Discord User ID is a numerical string, NOT your username like "lukeswagga"
# To get your Discord User ID:
# 1. Discord settings → Advanced → Enable Developer Mode
# 2. Right-click your name (or your profile picture) → Copy User ID
# 3. Paste the numerical ID here (e.g., "184675305369792512")
YOUR_DISCORD_USER_ID = "1361239061117010090"  # Your Discord User ID


async def create_test_listing() -> Listing:
    """Create a test listing for DM testing"""
    listing = Listing(
        id=1,
        market="yahoo",
        external_id="test123456",
        title="Test Listing - Rick Owens DRKSHDW Bauhaus Carpenters",
        price_jpy=25000,
        brand="Rick Owens",
        url="https://auctions.yahoo.co.jp/closedsearch/closedsearch?auccat=0&tab_ex=commerce&ei=utf-8&fr=auc_top&va=test",
        image_url="https://example.com/test-image.jpg",
        listing_type="auction",
        seller_id="test_seller",
    )
    return listing


async def test_dm():
    """Test sending a DM via Discord bot"""
    # Get bot token
    token = get_discord_bot_token()
    if not token:
        logger.error("❌ DISCORD_BOT_TOKEN not set in environment")
        logger.error("   Set it in .env file or environment variables")
        return
    
    # Check user ID
    if YOUR_DISCORD_USER_ID == "YOUR_USER_ID_HERE":
        logger.error("❌ Please update YOUR_DISCORD_USER_ID in this script")
        logger.error("   Get your Discord User ID (NOT username!):")
        logger.error("   1. Discord settings → Advanced → Enable Developer Mode")
        logger.error("   2. Right-click your name → Copy User ID")
        logger.error("   3. Paste the numerical ID (e.g., '184675305369792512')")
        return
    
    # Validate that it's a numerical ID, not a username
    if not YOUR_DISCORD_USER_ID.isdigit():
        logger.error(f"❌ Invalid Discord User ID: '{YOUR_DISCORD_USER_ID}'")
        logger.error("   Discord User IDs are numerical strings (e.g., '184675305369792512')")
        logger.error("   You entered what looks like a username. Please get your User ID:")
        logger.error("   1. Discord settings → Advanced → Enable Developer Mode")
        logger.error("   2. Right-click your name → Copy User ID")
        return
    
    # Initialize bot
    logger.info("🤖 Initializing Discord bot...")
    bot = SwagSearchBot(token)
    
    try:
        # Start bot
        logger.info("🚀 Starting Discord bot...")
        await bot.start_bot()
        
        # Wait for bot to be ready
        logger.info("⏳ Waiting for bot to connect...")
        for i in range(100):  # Wait up to 10 seconds
            if bot.is_ready():
                logger.info("✅ Bot is ready!")
                break
            await asyncio.sleep(0.1)
        
        if not bot.is_ready():
            logger.error("❌ Bot failed to connect within 10 seconds")
            return
        
        # Create test listing
        logger.info("📦 Creating test listing...")
        test_listing = await create_test_listing()
        
        # Send test DM
        logger.info(f"📤 Sending test DM to user {YOUR_DISCORD_USER_ID}...")
        success = await bot.send_alert(
            YOUR_DISCORD_USER_ID,
            test_listing,
            "Test Filter"
        )
        
        if success:
            logger.info("✅ Test DM sent successfully!")
            logger.info("   Check your Discord DMs to verify")
        else:
            logger.error("❌ Failed to send test DM")
            logger.error("   Check logs above for error details")
            logger.error("   Common issues:")
            logger.error("   - User has DMs disabled")
            logger.error("   - User has blocked the bot")
            logger.error("   - Invalid user ID")
        
        # Show bot stats
        stats = bot.get_stats()
        logger.info(f"\n📊 Bot Statistics:")
        logger.info(f"   Total sent: {stats['total_sent']}")
        logger.info(f"   Total errors: {stats['total_errors']}")
        logger.info(f"   DMs disabled: {stats['dm_disabled']}")
        logger.info(f"   Blocked: {stats['blocked']}")
        logger.info(f"   Is ready: {stats['is_ready']}")
        
        # Wait a bit before closing
        logger.info("\n⏳ Waiting 2 seconds before closing...")
        await asyncio.sleep(2)
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}", exc_info=True)
    finally:
        # Close bot
        logger.info("🔌 Closing Discord bot...")
        await bot.close()
        logger.info("✅ Test complete")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("Discord Bot DM Test")
    print(f"{'='*60}")
    print("⚠️  Make sure to:")
    print("   1. Set DISCORD_BOT_TOKEN in environment")
    print("   2. Update YOUR_DISCORD_USER_ID in this script")
    print("   3. Enable Developer Mode in Discord to get your User ID")
    print(f"{'='*60}\n")
    
    asyncio.run(test_dm())

