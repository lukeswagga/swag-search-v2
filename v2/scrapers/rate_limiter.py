"""
Smart rate limiter with per-domain limits, exponential backoff, and rotating user agents
"""
import asyncio
import time
import random
from typing import Dict, Optional, List
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Smart rate limiter with per-domain limits, exponential backoff, and rotating user agents
    
    Features:
    - Per-domain rate limiting (e.g., Yahoo: 100 requests/minute)
    - Exponential backoff on 429/500 errors
    - Rotating user agents (10+ different agents)
    - Request queue with delays
    """
    
    # Rotating user agents pool
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]
    
    def __init__(self, domain: str, max_requests_per_minute: int = 100):
        """
        Initialize rate limiter for a domain
        
        Args:
            domain: Domain name (e.g., 'auctions.yahoo.co.jp')
            max_requests_per_minute: Maximum requests per minute for this domain
        """
        self.domain = domain
        self.max_requests_per_minute = max_requests_per_minute
        self.request_times: deque = deque()  # Track request timestamps
        self.current_user_agent_index = 0
        self.backoff_until: Optional[datetime] = None  # Backoff expiration time
        self.backoff_multiplier = 1  # Current backoff multiplier
        self.lock = asyncio.Lock()
        logger.info(f"🚀 Rate limiter initialized for {domain}: {max_requests_per_minute} req/min")
        
    def get_user_agent(self) -> str:
        """Get next user agent from rotating pool"""
        user_agent = self.USER_AGENTS[self.current_user_agent_index]
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.USER_AGENTS)
        return user_agent
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with rotating user agent (matches original working scraper)"""
        return {
            'User-Agent': self.get_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            # Note: No Referer header - original scraper didn't use it
        }
    
    async def wait_if_needed(self, min_delay: float = 1.0):
        """
        Wait if rate limit would be exceeded or if in backoff period
        Ensures minimum spacing between requests to prevent bursts
        
        Args:
            min_delay: Minimum delay since last request (seconds)
        """
        async with self.lock:
            now = datetime.now()
            
            # Check if we're in backoff period
            if self.backoff_until and now < self.backoff_until:
                wait_seconds = (self.backoff_until - now).total_seconds()
                logger.warning(f"⏸️  Rate limiter in backoff for {self.domain}: waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)
                now = datetime.now()
            
            # Clean old request times (older than 1 minute)
            one_minute_ago = now - timedelta(minutes=1)
            while self.request_times and self.request_times[0] < one_minute_ago:
                self.request_times.popleft()
            
            # Check if we've hit the rate limit
            if len(self.request_times) >= self.max_requests_per_minute:
                # Calculate wait time until oldest request expires
                oldest_request = self.request_times[0]
                wait_until = oldest_request + timedelta(minutes=1)
                wait_seconds = (wait_until - now).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"⏸️  Rate limit reached for {self.domain}: waiting {wait_seconds:.1f}s")
                    await asyncio.sleep(wait_seconds)
                    # Clean up again after waiting
                    now = datetime.now()
                    one_minute_ago = now - timedelta(minutes=1)
                    while self.request_times and self.request_times[0] < one_minute_ago:
                        self.request_times.popleft()
            
            # Ensure minimum delay since last request (prevents bursts)
            if self.request_times and min_delay > 0:
                last_request = self.request_times[-1]
                time_since_last = (now - last_request).total_seconds()
                if time_since_last < min_delay:
                    wait_needed = min_delay - time_since_last
                    if wait_needed > 0.1:  # Only log if significant wait
                        logger.debug(f"⏸️  Enforcing min delay for {self.domain}: waiting {wait_needed:.2f}s")
                    await asyncio.sleep(wait_needed)
                    now = datetime.now()
            
            # Record this request (BEFORE releasing lock to prevent race conditions)
            self.request_times.append(now)
            
            # Log current rate
            requests_in_last_min = len(self.request_times)
            if requests_in_last_min > 0:
                logger.debug(
                    f"📊 Rate limiter: {requests_in_last_min}/{self.max_requests_per_minute} "
                    f"requests in last minute for {self.domain}"
                )
    
    def record_success(self):
        """Record successful request - gradually reset backoff"""
        async def _reset():
            async with self.lock:
                # Gradually reduce backoff multiplier on success (not immediate reset)
                if self.backoff_multiplier > 1:
                    self.backoff_multiplier = max(1, self.backoff_multiplier - 1)
                    logger.info(
                        f"✅ Rate limiter success for {self.domain}: "
                        f"reduced backoff multiplier to {self.backoff_multiplier}"
                    )
                # Only clear backoff if we're not currently in one
                if self.backoff_until and datetime.now() >= self.backoff_until:
                    self.backoff_until = None
                    logger.info(f"✅ Rate limiter backoff cleared for {self.domain}")
        
        # Schedule reset (non-blocking)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_reset())
        except RuntimeError:
            # No event loop, skip (will be handled on next async call)
            pass
    
    def record_error(self, status_code: int, base_backoff: float = 2.0):
        """
        Record error and apply exponential backoff for 429/500 errors
        
        Args:
            status_code: HTTP status code
            base_backoff: Base backoff time in seconds
        """
        async def _apply_backoff():
            async with self.lock:
                if status_code in (429, 500, 502, 503, 504):
                    # Exponential backoff: base_backoff * (2 ^ multiplier)
                    backoff_seconds = base_backoff * (2 ** self.backoff_multiplier)
                    self.backoff_until = datetime.now() + timedelta(seconds=backoff_seconds)
                    self.backoff_multiplier = min(self.backoff_multiplier + 1, 6)  # Cap at 6
                    logger.warning(
                        f"⚠️  Rate limiter backoff for {self.domain}: "
                        f"HTTP {status_code}, waiting {backoff_seconds:.1f}s "
                        f"(multiplier: {self.backoff_multiplier})"
                    )
                else:
                    # Non-critical error - don't backoff
                    pass
        
        # Schedule backoff (non-blocking)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_apply_backoff())
        except RuntimeError:
            # No event loop, skip (will be handled on next async call)
            pass
    
    async def acquire(self, min_delay: float = 1.0):
        """
        Acquire permission to make a request (waits if needed)
        Call this before making any HTTP request
        
        Args:
            min_delay: Minimum delay since last request (seconds)
        """
        await self.wait_if_needed(min_delay=min_delay)
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get current rate limiter statistics (synchronous, thread-safe for reads)
        
        Note: This method reads without locking for performance.
        For accurate stats during concurrent access, use get_stats_async().
        """
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)
        
        # Count recent requests (approximate, without lock)
        recent_requests = sum(1 for req_time in self.request_times if req_time >= one_minute_ago)
        
        return {
            'domain': self.domain,
            'requests_last_minute': recent_requests,
            'max_requests_per_minute': self.max_requests_per_minute,
            'in_backoff': self.backoff_until is not None and now < self.backoff_until,
            'backoff_until': self.backoff_until.isoformat() if self.backoff_until else None,
            'backoff_multiplier': self.backoff_multiplier,
        }
    
    async def get_stats_async(self) -> Dict[str, any]:
        """Get current rate limiter statistics (async, fully thread-safe)"""
        async with self.lock:
            now = datetime.now()
            one_minute_ago = now - timedelta(minutes=1)
            
            # Clean old requests
            while self.request_times and self.request_times[0] < one_minute_ago:
                self.request_times.popleft()
            
            return {
                'domain': self.domain,
                'requests_last_minute': len(self.request_times),
                'max_requests_per_minute': self.max_requests_per_minute,
                'in_backoff': self.backoff_until is not None and now < self.backoff_until,
                'backoff_until': self.backoff_until.isoformat() if self.backoff_until else None,
                'backoff_multiplier': self.backoff_multiplier,
            }


class RateLimiterManager:
    """
    Manager for multiple domain rate limiters
    """
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
    
    def get_limiter(self, domain: str, max_requests_per_minute: int = 100) -> RateLimiter:
        """
        Get or create rate limiter for a domain
        
        Args:
            domain: Domain name
            max_requests_per_minute: Max requests per minute for this domain
        
        Returns:
            RateLimiter instance for this domain
        """
        if domain not in self.limiters:
            self.limiters[domain] = RateLimiter(domain, max_requests_per_minute)
        return self.limiters[domain]
    
    def get_all_stats(self) -> Dict[str, Dict[str, any]]:
        """Get statistics for all rate limiters"""
        return {domain: limiter.get_stats() for domain, limiter in self.limiters.items()}

