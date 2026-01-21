# Production Implementation Plan - Multi-User Discord Bot

## Overview
Transform the current webhook-based system into a production-ready Discord bot that supports 1000+ users with individual channels.

## Phase 1: Core Infrastructure (Week 1-2)

### 1.1 Add UserChannel Model
**File:** `v2/models.py`

```python
class UserChannel(Base):
    """User's preferred channel for receiving alerts"""
    __tablename__ = "user_channels"
    
    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)  # None = DMs
    dm_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=lambda: datetime.utcnow())
```

### 1.2 Create Discord Bot Module
**File:** `v2/discord_bot.py`

```python
import discord
from discord.ext import commands
from typing import Optional

class SwagSearchBot:
    def __init__(self, token: str):
        intents = discord.Intents.default()
        intents.message_content = True
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.token = token
        
    async def send_listing_alert(self, channel_id: int, listing: Listing, filter_name: str, user_id: str):
        """Send listing alert to specific channel"""
        channel = self.bot.get_channel(channel_id)
        if channel:
            embed = self._create_embed(listing, filter_name, user_id)
            await channel.send(embed=embed)
    
    async def send_dm_alert(self, user_id: int, listing: Listing, filter_name: str):
        """Send listing alert via DM"""
        user = await self.bot.fetch_user(user_id)
        if user:
            embed = self._create_embed(listing, filter_name, str(user_id))
            await user.send(embed=embed)
```

### 1.3 Database Functions
**File:** `v2/database.py`

```python
async def get_user_channel(user_id: str) -> Optional[UserChannel]:
    """Get user's channel configuration"""
    
async def set_user_channel(user_id: str, channel_id: Optional[int], dm_enabled: bool = False) -> None:
    """Set user's channel for alerts"""
```

## Phase 2: Bot Commands (Week 2-3)

### 2.1 Filter Management Commands

```python
@bot.command(name='filter')
async def filter_command(ctx, action: str, *args):
    """Manage your filters"""
    user_id = str(ctx.author.id)
    
    if action == 'create':
        # /filter create name:"Budget Finds" brands:"rick owens" max_price:50000
        await create_filter(ctx, user_id, *args)
    elif action == 'list':
        await list_filters(ctx, user_id)
    elif action == 'edit':
        await edit_filter(ctx, user_id, *args)
    elif action == 'delete':
        await delete_filter(ctx, user_id, *args)
```

### 2.2 Channel Configuration Commands

```python
@bot.command(name='alertchannel')
async def alert_channel_command(ctx, channel: Optional[discord.TextChannel] = None):
    """Set where you receive alerts"""
    user_id = str(ctx.author.id)
    
    if channel:
        # Set to specific channel
        await set_user_channel(user_id, channel.id, dm_enabled=False)
        await ctx.send(f"✅ Alerts will be sent to {channel.mention}")
    else:
        # Set to DMs
        await set_user_channel(user_id, None, dm_enabled=True)
        await ctx.send("✅ Alerts will be sent via DM")
```

## Phase 3: Scheduler Updates (Week 3-4)

### 3.1 Update Alert Routing

```python
# In scheduler.py
async def send_personalized_alert(listing, filter_obj, user_id):
    """Send alert to user's preferred channel"""
    user_channel = await get_user_channel(user_id)
    
    if not user_channel:
        # Default: send to user's DMs
        await discord_bot.send_dm_alert(int(user_id), listing, filter_obj.name)
    elif user_channel.dm_enabled:
        await discord_bot.send_dm_alert(int(user_id), listing, filter_obj.name)
    elif user_channel.channel_id:
        await discord_bot.send_listing_alert(
            user_channel.channel_id, 
            listing, 
            filter_obj.name, 
            user_id
        )
```

### 3.2 Batch Alerts

```python
# Group alerts by channel to reduce API calls
alerts_by_channel = defaultdict(list)
for listing_id, matched_filters in matches.items():
    for filter_obj in matched_filters:
        user_channel = await get_user_channel(filter_obj.user_id)
        channel_key = user_channel.channel_id if user_channel else f"dm_{filter_obj.user_id}"
        alerts_by_channel[channel_key].append((listing, filter_obj))

# Send batched alerts (up to 10 embeds per message)
for channel_key, alerts in alerts_by_channel.items():
    await send_batched_alerts(channel_key, alerts[:10])  # Discord limit: 10 embeds
```

## Phase 4: Performance Optimizations (Week 4-5)

### 4.1 Filter Caching

```python
class FilterCache:
    def __init__(self):
        self._cache = None
        self._cache_time = None
        self._cache_ttl = 300  # 5 minutes
    
    async def get_active_filters(self):
        if self._cache is None or time.time() - self._cache_time > self._cache_ttl:
            self._cache = await get_active_filters()
            self._cache_time = time.time()
        return self._cache
```

### 4.2 Database Query Optimization

```python
# Instead of matching in Python, use SQL
async def find_matching_filters(listing: Listing) -> List[UserFilter]:
    """Use database query for efficient matching"""
    # This is much faster than Python loops
    query = select(UserFilter).where(
        and_(
            UserFilter.active == True,
            # Brand matching (case-insensitive)
            func.lower(UserFilter.brands).contains(func.lower(listing.brand)),
            # Price range
            UserFilter.price_min <= listing.price_jpy,
            UserFilter.price_max >= listing.price_jpy,
            # Market
            UserFilter.markets.contains(listing.market)
        )
    )
    return await session.execute(query)
```

## Phase 5: Rate Limiting & Queue (Week 5-6)

### 5.1 Alert Queue System

```python
class AlertQueue:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.rate_limiter = RateLimiter(max_per_second=50)
    
    async def add_alert(self, listing, filter_obj, user_id):
        await self.queue.put((listing, filter_obj, user_id))
    
    async def process_queue(self):
        """Process queue with rate limiting"""
        while True:
            listing, filter_obj, user_id = await self.queue.get()
            await self.rate_limiter.wait()
            await send_personalized_alert(listing, filter_obj, user_id)
            self.queue.task_done()
```

## Testing Plan

### Phase 1 Testing (10 users)
- Create 10 test filters
- Verify alerts go to correct channels
- Test filter commands

### Phase 2 Testing (100 users)
- Load test with 100 filters
- Verify performance
- Test rate limiting

### Phase 3 Testing (1000 users)
- Full production test
- Monitor performance
- Verify scalability

## Deployment Checklist

- [ ] Discord bot token configured
- [ ] Database migrations run
- [ ] Bot has necessary permissions
- [ ] Rate limiting tested
- [ ] Error handling tested
- [ ] Monitoring/logging set up
- [ ] Backup strategy in place
- [ ] Documentation complete

## Rollout Strategy

1. **Beta (10 users):** Test with trusted users
2. **Limited (100 users):** Invite more users, monitor closely
3. **Full (1000 users):** Open to all users

## Success Metrics

- Alert delivery rate > 99%
- Average alert latency < 5 seconds
- Zero rate limit errors
- User satisfaction > 4/5



