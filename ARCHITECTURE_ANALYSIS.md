# Architecture Analysis - Current System

## 1. How Does Scraping Work Currently?

### Core Flow
1. **Base Class (`YahooScraperBase`)**:
   - Handles HTTP requests (sync `requests` + async `aiohttp`)
   - Parses HTML with BeautifulSoup
   - Builds Yahoo Auctions search URLs with pagination
   - Extracts auction data (title, price, brand, URLs)
   - Filters spam/clothing/price/quality
   - Tracks "seen" auction IDs to prevent duplicates

2. **Scraper Implementation (`NewListingsScraper`)**:
   - Extends `YahooScraperBase`
   - Runs on schedule (every 10 minutes)
   - Processes brands **sequentially** (one at a time)
   - For each brand:
     - Uses primary variant as search keyword
     - Pages through results **sequentially** (one page at a time)
     - Extracts listings and checks if they're new
   - Sends filtered listings to Discord via webhook

3. **Data Flow**:
   ```
   Yahoo Auctions → HTTP Request → BeautifulSoup Parse → 
   Extract Auction Data → Filter (Spam/Clothing/Price) → 
   Check Seen IDs → Send to Discord Bot → Save to DB
   ```

### Key Components
- **HTTP Layer**: `aiohttp` (async) with connection pooling, retries, exponential backoff
- **Parsing**: BeautifulSoup for HTML extraction
- **Filtering**: `EnhancedSpamDetector` + `QualityChecker` from `enhancedfiltering.py`
- **Rate Limiting**: 2.5s delay between pages, 3s delay between brands
- **Deduplication**: In-memory `seen_ids` set + SQLite/PostgreSQL persistence

---

## 2. Where's the Bottleneck?

### Primary Bottlenecks:

1. **Sequential Brand Processing** (Line 202 in `new_listings_scraper.py`):
   - Brands processed one-by-one, not in parallel
   - Comment: "REDUCED CONCURRENCY: Process brands sequentially to avoid overwhelming Yahoo"
   - **Impact**: With 20+ brands, this adds significant latency

2. **Sequential Page Requests** (Line 138):
   - Pages processed one-by-one within each brand
   - 2.5 second delay between pages
   - **Impact**: 5 pages × 2.5s = 12.5s per brand minimum

3. **Yahoo Rate Limiting**:
   - HTTP 500 errors when hit too hard
   - Forces conservative rate limiting
   - **Impact**: Cannot parallelize effectively without errors

4. **In-Memory Seen IDs**:
   - Large set loaded into memory on startup
   - Checked for every listing (O(1) but memory-intensive)
   - **Impact**: Memory bloat (30k+ items), slow startup

5. **Database Writes**:
   - Seen IDs saved after each cycle (batch write)
   - Listings saved individually via Discord bot webhook
   - **Impact**: Potential write contention

### Estimated Timing:
- Per brand: ~15-30 seconds (5 pages × 3s/page)
- 20 brands: ~5-10 minutes per cycle
- With rate limiting: **Cannot parallelize without Yahoo 500 errors**

---

## 3. How Are Brands/Keywords Being Matched?

### Brand Data Structure:
- Loaded from `brands.json` (JSON file)
- Format:
  ```json
  {
    "Brand Name": {
      "variants": ["primary variant", "alternative", "japanese name"],
      "subcategories": ["jacket", "coat", ...],
      "tier": 1-5
    }
  }
  ```

### Matching Algorithm (Line 765-774):
```python
def detect_brand_in_title(self, title):
    title_lower = title.lower()
    for brand, brand_info in self.brand_data.items():
        for variant in brand_info.get('variants', []):
            if variant.lower() in title_lower:
                return brand
    return "Unknown"
```

### Search Strategy:
- Uses **primary variant** (first in variants array) for Yahoo search
- Example: "Raf Simons" → searches for "raf simons"
- **Problem**: Simple substring matching can create false positives
- No fuzzy matching, no exact word boundaries

### Current Limitations:
- No multi-keyword search (only primary variant)
- Simple substring match (e.g., "raf" matches "graffiti")
- No brand disambiguation
- Japanese variants used for search but may not be optimal

---

## 4. What's the Database Schema?

### Current Tables (from `database_manager.py`):

#### **listings**
```sql
- id (PK, auto)
- auction_id (UNIQUE, VARCHAR)
- title (TEXT)
- brand (VARCHAR)
- price_jpy (INTEGER)
- price_usd (REAL)
- seller_id (VARCHAR)
- zenmarket_url (TEXT)
- yahoo_url (TEXT)
- image_url (TEXT)
- deal_quality (REAL, default 0.5)
- priority_score (REAL, default 0.0)
- created_at (TIMESTAMP)
- message_id (BIGINT)
- auction_end_time (TIMESTAMP)
- reminder_1h_sent (BOOLEAN)
- reminder_5m_sent (BOOLEAN)
```

#### **reactions**
```sql
- id (PK)
- user_id (BIGINT)
- auction_id (VARCHAR)
- reaction_type (VARCHAR)
- created_at (TIMESTAMP)
```

#### **user_preferences**
```sql
- user_id (PK, BIGINT)
- proxy_service (VARCHAR, default 'zenmarket')
- setup_complete (BOOLEAN)
- notifications_enabled (BOOLEAN)
- min_quality_threshold (REAL)
- max_price_alert (REAL)
- bookmark_method (VARCHAR)
- auto_bookmark_likes (BOOLEAN)
- preferred_sizes (TEXT)
- size_alerts_enabled (BOOLEAN)
- created_at, updated_at (TIMESTAMP)
```

#### **user_bookmarks**
```sql
- id (PK)
- user_id (BIGINT)
- auction_id (VARCHAR)
- bookmark_message_id (BIGINT)
- bookmark_channel_id (BIGINT)
- auction_end_time (TIMESTAMP)
- reminder_sent_1h, reminder_sent_5m (BOOLEAN)
- created_at (TIMESTAMP)
- UNIQUE(user_id, auction_id)
```

#### **scraper_stats**
```sql
- id (PK)
- timestamp (TIMESTAMP)
- total_found (INTEGER)
- quality_filtered (INTEGER)
- sent_to_discord (INTEGER)
- errors_count (INTEGER)
- keywords_searched (INTEGER)
```

#### **user_subscriptions**
```sql
- id (PK)
- user_id (UNIQUE, BIGINT)
- tier (VARCHAR, default 'free')
- upgraded_at, expires_at (TIMESTAMP)
- payment_provider (VARCHAR)
- subscription_id (VARCHAR)
- status (VARCHAR)
- created_at, updated_at (TIMESTAMP)
```

### Additional Tracking (in `core_scraper_base.py`):

#### **seen_items** (SQLite/PostgreSQL)
```sql
- scraper_name (TEXT)
- auction_id (TEXT)
- first_seen (TIMESTAMP)
- PRIMARY KEY (scraper_name, auction_id)
```

#### **scraper_state**
```sql
- scraper_name (TEXT, PK)
- page_offset (INTEGER)
- last_updated (TIMESTAMP)
```

### Database Usage:
- **PostgreSQL**: Production (Railway), with `psycopg2`
- **SQLite**: Local development fallback
- **Dual-mode**: Auto-detects based on `DATABASE_URL` env var

---

## Key Insights for V2:

1. **Need for Async Database Operations**: Current DB operations are blocking
2. **Better User Filtering**: Current system filters at scraper level, not per-user
3. **Improved Brand Matching**: Need fuzzy matching and exact word boundaries
4. **Optimized Deduplication**: Current seen_ids in-memory is not scalable
5. **User-Centric Architecture**: V2 should support per-user filters instead of global filters

