"""
Discord webhook notifier for listing alerts
Sends formatted embeds with rate limiting (1 msg/second max)
"""
import asyncio
import aiohttp
import logging
from typing import Optional, List, Tuple
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)

try:
    from .models import Listing
except ImportError:
    from models import Listing


class DiscordNotifier:
    """
    Discord webhook notifier with rate limiting
    
    Features:
    - Sends formatted embeds for listings
    - Rate limited to 1 message per second
    - Color-coded by price range
    - Handles errors gracefully
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
    
    def __init__(self, webhook_url: str):
        """
        Initialize Discord notifier
        
        Args:
            webhook_url: Discord webhook URL
        """
        self.webhook_url = webhook_url
        self._last_send_time = 0.0
        self._min_delay = 1.0  # 1 second between messages
        self._session: Optional[aiohttp.ClientSession] = None
        self._send_count = 0
        self._error_count = 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _get_color_for_price(self, price_jpy: int) -> int:
        """
        Get Discord embed color based on price range
        
        Args:
            price_jpy: Price in JPY
            
        Returns:
            Discord embed color (decimal RGB)
        """
        if price_jpy < self.PRICE_LOW:
            return self.COLOR_GREEN
        elif price_jpy < self.PRICE_MEDIUM:
            return self.COLOR_YELLOW
        else:
            return self.COLOR_RED
    
    def _format_price(self, price_jpy: int) -> str:
        """
        Format price in JPY and USD
        
        Args:
            price_jpy: Price in JPY
            
        Returns:
            Formatted price string (e.g., "¥15,000 ($102.04)")
        """
        price_usd = price_jpy / self.JPY_TO_USD_RATE
        return f"¥{price_jpy:,} (${price_usd:.2f})"
    
    def _truncate_title(self, title: str, max_length: int = 100) -> str:
        """
        Truncate title to max length
        
        Args:
            title: Listing title
            max_length: Maximum length
            
        Returns:
            Truncated title with ellipsis if needed
        """
        if len(title) <= max_length:
            return title
        return title[:max_length - 3] + "..."
    
    def _get_source_name(self, market: str) -> str:
        """
        Get source name for display
        
        Args:
            market: Market name ("yahoo" or "mercari")
            
        Returns:
            Source name ("Yahoo Japan" or "Mercari")
        """
        if market.lower() == "yahoo":
            return "Yahoo Japan"
        elif market.lower() == "mercari":
            return "Mercari"
        return market.title()
    
    def _get_source_display(self, listing_type: str) -> str:
        """
        Get source display text based on listing type
        
        Args:
            listing_type: Listing type ("auction", "buy_it_now", etc.)
            
        Returns:
            Source display text ("Buy It Now", "Auction", or "Fixed Price")
        """
        if listing_type == "buy_it_now":
            return "Buy It Now"
        elif listing_type == "auction":
            return "Auction"
        else:
            return "Fixed Price"
    
    def _get_proxy_links(self, listing: Listing) -> Tuple[str, str]:
        """
        Get Buyee and ZenMarket proxy links for a listing
        
        Args:
            listing: Listing object
            
        Returns:
            Tuple of (buyee_url, zenmarket_url)
        """
        # Extract raw ID (remove 'u' prefix if present for Buyee)
        raw_id = listing.external_id
        if raw_id.startswith('u') and raw_id[1:].isdigit():
            raw_id = raw_id[1:]
        
        # For ZenMarket Yahoo, we might need the 'u' prefix
        zenmarket_id = listing.external_id
        if listing.market.lower() == "yahoo" and not zenmarket_id.startswith('u') and zenmarket_id.isdigit():
            zenmarket_id = f"u{zenmarket_id}"
        
        if listing.market.lower() == "yahoo":
            buyee_url = f"https://buyee.jp/item/yahoo/auction/{raw_id}"
            zenmarket_url = f"https://zenmarket.jp/en/yahoo.aspx?itemCode={zenmarket_id}"
        elif listing.market.lower() == "mercari":
            buyee_url = f"https://buyee.jp/item/mercari/{raw_id}"
            zenmarket_url = f"https://zenmarket.jp/en/mercari.aspx?itemCode={raw_id}"
        else:
            # Fallback for unknown markets
            buyee_url = listing.url
            zenmarket_url = listing.url
        
        return buyee_url, zenmarket_url
    
    def _get_reverse_image_search_url(self, image_url: str) -> str:
        """
        Get Google Lens reverse image search URL (works on desktop and mobile)
        
        Uses Google Lens which works reliably on both desktop and mobile devices,
        unlike the searchbyimage endpoint which only works on desktop.
        
        Args:
            image_url: Image URL to search
            
        Returns:
            Google Lens reverse image search URL
        """
        if not image_url:
            return ""
        # Google Lens works on both desktop and mobile
        # URL format: https://lens.google.com/uploadbyurl?url={encoded_url}
        encoded_url = quote(image_url, safe='')
        return f"https://lens.google.com/uploadbyurl?url={encoded_url}"
    
    def _format_timestamp(self, dt: datetime) -> str:
        """
        Format timestamp for footer display
        
        Args:
            dt: Datetime object
            
        Returns:
            Formatted timestamp string (e.g., "Yesterday at 9:18 PM")
        """
        # Calculate relative time
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
    
    def _create_embed(self, listing: Listing) -> dict:
        """
        Create Discord embed for a listing matching production format
        
        Args:
            listing: Listing object
            
        Returns:
            Discord embed dictionary
        """
        # Truncate title to 100 chars (title is NOT a hyperlink)
        title = self._truncate_title(listing.title, 100)
        
        # Format price
        price_text = self._format_price(listing.price_jpy)
        
        # Get color based on price
        color = self._get_color_for_price(listing.price_jpy)
        
        # Get source name and display
        source_name = self._get_source_name(listing.market)
        source_display = self._get_source_display(listing.listing_type)
        
        # Get proxy links
        buyee_url, zenmarket_url = self._get_proxy_links(listing)
        
        # Get reverse image search URL (Google Lens)
        reverse_image_url = ""
        if listing.image_url:
            reverse_image_url = self._get_reverse_image_search_url(listing.image_url)
        
        # Build links field value
        links_parts = []
        
        # Source link (Yahoo Japan or Mercari)
        source_link = f"[{source_name}]({listing.url})"
        links_parts.append(f"🇯🇵 {source_link}")
        
        # Buyee link
        links_parts.append(f"[📦 Buyee]({buyee_url})")
        
        # ZenMarket link
        links_parts.append(f"[🛒 ZenMarket]({zenmarket_url})")
        
        # Reverse image search link (Google Lens)
        if reverse_image_url:
            links_parts.append(f"[🔍 Check Retail/Resale]({reverse_image_url})")
        
        links_value = " | ".join(links_parts)
        
        # Format timestamp for footer
        timestamp_str = self._format_timestamp(datetime.utcnow())
        
        # Build embed fields in order
        fields = [
            {
                "name": "Brand",
                "value": listing.brand or "Unknown",
                "inline": False
            },
            {
                "name": "Price",
                "value": price_text,
                "inline": False
            },
            {
                "name": "Quality",
                "value": "70.0%",
                "inline": False
            },
            {
                "name": "Priority",
                "value": "0.66",
                "inline": False
            },
            {
                "name": "Source",
                "value": source_display,
                "inline": False
            },
            {
                "name": "🔗 Links",
                "value": links_value,
                "inline": False
            }
        ]
        
        # Build embed
        embed = {
            "title": title,
            "color": color,
            "fields": fields,
            "footer": {
                "text": f"Auction ID: {listing.external_id} • {timestamp_str}"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add thumbnail if image URL exists (on right side)
        if listing.image_url:
            embed["thumbnail"] = {
                "url": listing.image_url
            }
        
        return embed
    
    async def _enforce_rate_limit(self):
        """Enforce 1 message per second rate limit"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_send = current_time - self._last_send_time
        
        if time_since_last_send < self._min_delay:
            wait_time = self._min_delay - time_since_last_send
            await asyncio.sleep(wait_time)
        
        self._last_send_time = asyncio.get_event_loop().time()
    
    async def send_listing(self, listing: Listing) -> bool:
        """
        Send a single listing to Discord webhook
        
        Args:
            listing: Listing object to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Enforce rate limit
            await self._enforce_rate_limit()
            
            # Create embed
            embed = self._create_embed(listing)
            
            # Prepare payload
            payload = {
                "embeds": [embed]
            }
            
            # Get session and send
            session = await self._get_session()
            async with session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    self._send_count += 1
                    logger.info(f"✅ Discord alert sent: {listing.title[:50]}... (¥{listing.price_jpy:,})")
                    return True
                elif response.status == 429:
                    # Rate limited by Discord
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"⚠️  Discord rate limited, waiting {retry_after}s...")
                    await asyncio.sleep(retry_after)
                    # Retry once
                    async with session.post(self.webhook_url, json=payload) as retry_response:
                        if retry_response.status == 204:
                            self._send_count += 1
                            logger.info(f"✅ Discord alert sent (retry): {listing.title[:50]}...")
                            return True
                        else:
                            error_text = await retry_response.text()
                            logger.error(f"❌ Discord webhook failed (retry): {retry_response.status} - {error_text[:100]}")
                            self._error_count += 1
                            return False
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Discord webhook failed: {response.status} - {error_text[:100]}")
                    self._error_count += 1
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error sending Discord alert: {e}", exc_info=True)
            self._error_count += 1
            return False
    
    async def send_listings(self, listings: List[Listing]) -> dict:
        """
        Send multiple listings to Discord (with rate limiting)
        
        Args:
            listings: List of Listing objects
            
        Returns:
            Dictionary with send statistics
        """
        if not listings:
            return {
                'total': 0,
                'sent': 0,
                'failed': 0
            }
        
        logger.info(f"📤 Sending {len(listings)} listings to Discord...")
        
        sent_count = 0
        failed_count = 0
        
        for listing in listings:
            success = await self.send_listing(listing)
            if success:
                sent_count += 1
            else:
                failed_count += 1
        
        logger.info(f"📊 Discord alerts: {sent_count} sent, {failed_count} failed out of {len(listings)} total")
        
        return {
            'total': len(listings),
            'sent': sent_count,
            'failed': failed_count
        }
    
    def get_stats(self) -> dict:
        """
        Get notifier statistics
        
        Returns:
            Dictionary with stats
        """
        return {
            'total_sent': self._send_count,
            'total_errors': self._error_count
        }

