"""
Discord bot for sending personalized DMs to users based on their filters
"""
import asyncio
import logging
from typing import Optional, Tuple
import discord
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

try:
    from .models import Listing
except ImportError:
    from models import Listing


class SwagSearchBot:
    """
    Discord bot that sends personalized DMs to users
    
    Features:
    - Sends DMs based on user filters
    - Rate limiting (1 msg/sec)
    - Handles DMs disabled, user blocked, etc.
    - Graceful error handling
    """
    
    # JPY to USD conversion rate (¥147 = $1)
    JPY_TO_USD_RATE = 147.0
    
    # Price thresholds for color coding
    PRICE_LOW = 20000  # Green: Under ¥20,000
    PRICE_MEDIUM = 50000  # Yellow: ¥20,000-50,000
    
    # Discord embed color constants (decimal RGB)
    COLOR_GREEN = 5763719   # 0x57E307
    COLOR_YELLOW = 16776960  # 0xFFFF00
    COLOR_RED = 15548997     # 0xED4245
    
    def __init__(self, token: str):
        """
        Initialize Discord bot
        
        Args:
            token: Discord bot token
        """
        intents = discord.Intents.default()
        intents.message_content = False  # Don't need to read messages
        self.bot = discord.Client(intents=intents)
        self.token = token
        self._ready = False
        self._start_task: Optional[asyncio.Task] = None
        self._last_send_time = 0.0
        self._min_delay = 1.0  # 1 second between messages
        self._send_count = 0
        self._error_count = 0
        self._dm_disabled_count = 0
        self._blocked_count = 0
        
        # Set up bot event handlers
        @self.bot.event
        async def on_ready():
            self._ready = True
            logger.info(f"✅ Discord bot logged in as {self.bot.user} (ID: {self.bot.user.id})")
        
        @self.bot.event
        async def on_error(event, *args, **kwargs):
            logger.error(f"❌ Discord bot error in {event}: {args}, {kwargs}")
    
    async def start_bot(self):
        """
        Start bot in background without blocking
        """
        if self._start_task is None or self._start_task.done():
            logger.info("🚀 Starting Discord bot...")
            self._start_task = asyncio.create_task(self.bot.start(self.token))
            # Wait a bit for bot to connect
            for _ in range(50):  # Wait up to 5 seconds
                if self._ready:
                    break
                await asyncio.sleep(0.1)
            
            if not self._ready:
                logger.warning("⚠️  Discord bot not ready after 5 seconds, continuing anyway...")
        else:
            logger.info("ℹ️  Discord bot already starting...")
    
    async def close(self):
        """Close the bot connection"""
        if self.bot and not self.bot.is_closed():
            logger.info("🔌 Closing Discord bot connection...")
            await self.bot.close()
            self._ready = False
            if self._start_task:
                try:
                    await self._start_task
                except Exception as e:
                    logger.error(f"Error waiting for bot task: {e}")
    
    def is_ready(self) -> bool:
        """Check if bot is ready"""
        return self._ready and self.bot and not self.bot.is_closed()
    
    def _get_color_for_price(self, price_jpy: int) -> int:
        """Get Discord embed color based on price range"""
        if price_jpy < self.PRICE_LOW:
            return self.COLOR_GREEN
        elif price_jpy < self.PRICE_MEDIUM:
            return self.COLOR_YELLOW
        else:
            return self.COLOR_RED
    
    def _format_price(self, price_jpy: int) -> str:
        """Format price in JPY and USD"""
        price_usd = price_jpy / self.JPY_TO_USD_RATE
        return f"¥{price_jpy:,} (${price_usd:.2f})"
    
    def _truncate_title(self, title: str, max_length: int = 100) -> str:
        """Truncate title to max length"""
        if len(title) <= max_length:
            return title
        return title[:max_length - 3] + "..."
    
    def _get_source_name(self, market: str) -> str:
        """Get source name for display"""
        if market.lower() == "yahoo":
            return "Yahoo Japan"
        elif market.lower() == "mercari":
            return "Mercari"
        return market.title()
    
    def _get_source_display(self, listing_type: str) -> str:
        """Get source display text based on listing type"""
        if listing_type == "buy_it_now":
            return "Buy It Now"
        elif listing_type == "auction":
            return "Auction"
        else:
            return "Fixed Price"
    
    def _get_proxy_links(self, listing: Listing) -> Tuple[str, str]:
        """Get Buyee and ZenMarket proxy links for a listing"""
        raw_id = listing.external_id
        if raw_id.startswith('u') and raw_id[1:].isdigit():
            raw_id = raw_id[1:]
        
        if listing.market.lower() == "yahoo":
            buyee_url = f"https://buyee.jp/item/jdirectitems/auction/{raw_id}"
            zenmarket_url = f"https://zenmarket.jp/en/auction.aspx?itemCode={listing.external_id}"
        elif listing.market.lower() == "mercari":
            buyee_url = f"https://buyee.jp/mercari/item/{raw_id}"
            zenmarket_url = f"https://zenmarket.jp/en/mercariproduct.aspx?itemCode={raw_id}"
        else:
            buyee_url = listing.url
            zenmarket_url = listing.url
        
        return buyee_url, zenmarket_url
    
    def _get_reverse_image_search_url(self, image_url: str) -> str:
        """Get Google Lens reverse image search URL"""
        if not image_url:
            return ""
        encoded_url = quote(image_url, safe='')
        return f"https://lens.google.com/uploadbyurl?url={encoded_url}"
    
    def _format_timestamp(self, dt: datetime) -> str:
        """Format timestamp for footer display"""
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.days == 0:
            return dt.strftime("Today at %I:%M %p")
        elif diff.days == 1:
            return dt.strftime("Yesterday at %I:%M %p")
        elif diff.days < 7:
            return dt.strftime("%A at %I:%M %p")
        else:
            return dt.strftime("%B %d, %Y at %I:%M %p")
    
    def _create_embed(self, listing: Listing, filter_name: str) -> discord.Embed:
        """
        Create Discord embed for a listing (same format as webhook embeds)
        
        Args:
            listing: Listing object
            filter_name: Filter name that matched
            
        Returns:
            Discord Embed object
        """
        # Truncate title
        title = self._truncate_title(listing.title, 100)
        
        # Create embed
        embed = discord.Embed(
            title=title,
            color=self._get_color_for_price(listing.price_jpy),
            timestamp=datetime.utcnow()
        )
        
        # Add fields
        embed.add_field(name="Brand", value=listing.brand or "Unknown", inline=False)
        embed.add_field(name="Price", value=self._format_price(listing.price_jpy), inline=False)
        embed.add_field(name="Quality", value="70.0%", inline=False)
        embed.add_field(name="Priority", value="0.66", inline=False)
        embed.add_field(name="Source", value=self._get_source_display(listing.listing_type), inline=False)
        
        # Get proxy links
        buyee_url, zenmarket_url = self._get_proxy_links(listing)
        source_name = self._get_source_name(listing.market)
        
        # Build links
        links_parts = [
            f"🇯🇵 [{source_name}]({listing.url})",
            f"[📦 Buyee]({buyee_url})",
            f"[🛒 ZenMarket]({zenmarket_url})"
        ]
        
        # Add reverse image search if available
        if listing.image_url:
            reverse_image_url = self._get_reverse_image_search_url(listing.image_url)
            links_parts.append(f"[🔍 Check Retail/Resale]({reverse_image_url})")
        
        links_value = " | ".join(links_parts)
        embed.add_field(name="🔗 Links", value=links_value, inline=False)
        
        # Add thumbnail
        if listing.image_url:
            embed.set_thumbnail(url=listing.image_url)
        
        # Add footer
        timestamp_str = self._format_timestamp(datetime.utcnow())
        footer_text = f"Auction ID: {listing.external_id} • {timestamp_str}\nMatched filter: {filter_name}"
        embed.set_footer(text=footer_text)
        
        return embed
    
    async def _enforce_rate_limit(self):
        """Enforce 1 message per second rate limit"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_send = current_time - self._last_send_time
        
        if time_since_last_send < self._min_delay:
            wait_time = self._min_delay - time_since_last_send
            await asyncio.sleep(wait_time)
        
        self._last_send_time = asyncio.get_event_loop().time()
    
    async def send_dm(self, user_id: str, embed: discord.Embed) -> bool:
        """
        Send a DM to a user with an embed
        
        Args:
            user_id: Discord user ID (as string, e.g., "184675305369792512")
            embed: Discord Embed object
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_ready():
            logger.error("❌ Bot is not ready - cannot send DM")
            return False
        
        try:
            # Enforce rate limit
            await self._enforce_rate_limit()
            
            # Get user by ID
            try:
                user = await self.bot.fetch_user(int(user_id))
            except discord.NotFound:
                logger.error(f"❌ User not found: {user_id}")
                return False
            except discord.HTTPException as e:
                logger.error(f"❌ Error fetching user {user_id}: {e}")
                return False
            
            # Try to send DM
            try:
                await user.send(embed=embed)
                self._send_count += 1
                logger.info(f"✅ DM sent to user {user_id} ({user.name})")
                return True
            except discord.Forbidden:
                # User has DMs disabled or blocked bot
                # Try to determine which one
                try:
                    # If we can't send, try creating a DM channel (this will fail if blocked)
                    await user.create_dm()
                    # If we get here, DM channel was created but we still got Forbidden
                    # This means DMs are disabled
                    self._dm_disabled_count += 1
                    logger.warning(f"⚠️  User {user_id} ({user.name}) has DMs disabled")
                except discord.Forbidden:
                    # Can't create DM channel = user blocked bot
                    self._blocked_count += 1
                    logger.warning(f"⚠️  User {user_id} ({user.name}) has blocked the bot")
                self._error_count += 1
                return False
            except discord.HTTPException as e:
                logger.error(f"❌ Error sending DM to user {user_id}: {e}")
                self._error_count += 1
                return False
                
        except Exception as e:
            logger.error(f"❌ Unexpected error sending DM to user {user_id}: {e}", exc_info=True)
            self._error_count += 1
            return False
    
    async def send_alert(self, user_id: str, listing: Listing, filter_name: str) -> bool:
        """
        Send a personalized alert DM to a user
        
        Args:
            user_id: Discord user ID (as string)
            listing: Listing object
            filter_name: Filter name that matched
            
        Returns:
            True if successful, False otherwise
        """
        embed = self._create_embed(listing, filter_name)
        return await self.send_dm(user_id, embed)
    
    def get_stats(self) -> dict:
        """
        Get bot statistics
        
        Returns:
            Dictionary with stats
        """
        return {
            'total_sent': self._send_count,
            'total_errors': self._error_count,
            'dm_disabled': self._dm_disabled_count,
            'blocked': self._blocked_count,
            'is_ready': self.is_ready()
        }

