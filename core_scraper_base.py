#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core infrastructure for specialized Yahoo Japan scrapers
Shared functionality for all 4 scraper services
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
import urllib.parse
from datetime import datetime, timezone, timedelta
import re
import sqlite3
from flask import Flask
import threading
import random
import asyncio
import aiohttp

# Import enhanced filtering system
from enhancedfiltering import EnhancedSpamDetector, QualityChecker

# Yahoo Auctions category codes
# Fashion & Accessories (parent category - includes Men's, Women's, all fashion)
# https://auctions.yahoo.co.jp/category/list/2084005438/
FASHION_CATEGORY = "2084005438"
MENS_FASHION_CATEGORY = "2084005009"  # Kept for reference

# Database configuration - auto-detect PostgreSQL vs SQLite
# Try DATABASE_PUBLIC_URL first (for Railway), fallback to DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_PUBLIC_URL') or os.getenv('DATABASE_URL')
USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    print(f"🐘 PostgreSQL detected: {DATABASE_URL[:50]}...")  # Show first 50 chars
else:
    print("💾 Using SQLite (DATABASE_URL not set)")

class YahooScraperBase:
    def __init__(self, scraper_name):
        self.scraper_name = scraper_name
        self.seen_file = f"seen_{scraper_name}.json"
        self.scraper_db = "auction_tracking.db"

        # Discord Bot Integration
        self.discord_bot_url = os.getenv('DISCORD_BOT_URL', 'https://motivated-stillness-production.up.railway.app')
        if self.discord_bot_url and not self.discord_bot_url.startswith(('http://', 'https://')):
            self.discord_bot_url = f"https://{self.discord_bot_url}"

        # Exchange rate
        self.current_usd_jpy_rate = 147.0

        # Initialize SQLite database for persistent seen_ids tracking
        self.init_database()
        self.seen_ids = self.load_seen_items()

        # Brand data
        self.brand_data = self.load_brand_data()

        # Enhanced filtering system (integrated from enhancedfiltering.py)
        self.spam_detector = EnhancedSpamDetector()
        self.quality_checker = QualityChecker()

        # Filtering statistics for analytics
        self.stats = {
            'total_processed': 0,
            'spam_blocked': 0,
            'clothing_blocked': 0,
            'price_blocked': 0,
            'quality_blocked': 0,
            'sent': 0
        }

        # Flask health server
        self.app = Flask(__name__)
        self.setup_health_routes()

        # Async HTTP session (will be created when needed)
        self._session = None

        # Category filter disabled - caused 404 errors with Yahoo Auctions
        self.default_category = None

        print(f"🚀 {scraper_name} initialized")
        if USE_POSTGRES:
            print(f"💾 Using PostgreSQL database (Railway) for persistent tracking")
        else:
            print(f"💾 Using SQLite database for persistent tracking")
        print(f"🛡️ Enhanced spam detector loaded")
        print(f"📊 Quality checker initialized")
        print(f"⚡ Async HTTP support enabled")
    
    def setup_health_routes(self):
        @self.app.route('/health', methods=['GET'])
        def health():
            return {"status": "healthy", "service": self.scraper_name}, 200
            
        @self.app.route('/', methods=['GET'])
        def root():
            return {"service": f"Yahoo {self.scraper_name}", "status": "running"}, 200
    
    def run_health_server(self):
        port = int(os.environ.get('PORT', 8000))
        self.app.run(host='0.0.0.0', port=port, debug=False)

    def init_database(self):
        """Initialize database for persistent seen_ids tracking (PostgreSQL or SQLite)"""
        try:
            if USE_POSTGRES:
                # Lazy import for Railway deployment
                try:
                    import psycopg2
                    print("🐘 psycopg2 imported successfully")
                except ImportError as ie:
                    print(f"❌ Failed to import psycopg2: {ie}")
                    print("⚠️ Falling back to SQLite")
                    # Fall through to SQLite
                    self._init_sqlite()
                    return

                # PostgreSQL initialization
                print(f"🔌 Connecting to PostgreSQL for {self.scraper_name}...")
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                print("✅ PostgreSQL connection successful")

                # Create seen_items table if it doesn't exist (PostgreSQL syntax)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS seen_items (
                        scraper_name TEXT NOT NULL,
                        auction_id TEXT NOT NULL,
                        first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (scraper_name, auction_id)
                    )
                ''')

                # Create index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_scraper_name
                    ON seen_items(scraper_name)
                ''')

                # Create scraper_state table for persisting scraper state (page offsets, etc.)
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS scraper_state (
                        scraper_name TEXT PRIMARY KEY,
                        page_offset INTEGER DEFAULT 0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                conn.commit()
                conn.close()
                print(f"💾 PostgreSQL initialized for {self.scraper_name}")
            else:
                self._init_sqlite()
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")

    def _init_sqlite(self):
        """Initialize SQLite database (fallback)"""
        try:
            # SQLite initialization (fallback for local development)
            conn = sqlite3.connect(self.scraper_db)
            cursor = conn.cursor()

            # Create seen_items table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seen_items (
                    scraper_name TEXT NOT NULL,
                    auction_id TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (scraper_name, auction_id)
                )
            ''')

            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_scraper_name
                ON seen_items(scraper_name)
            ''')

            # Create scraper_state table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scraper_state (
                    scraper_name TEXT PRIMARY KEY,
                    page_offset INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.commit()
            conn.close()
            print(f"💾 SQLite initialized: {self.scraper_db}")
        except Exception as e:
            print(f"❌ SQLite initialization error: {e}")

    def load_seen_items(self):
        """Load seen auction IDs from database (PostgreSQL or SQLite)"""
        try:
            print(f"📥 Loading seen items for {self.scraper_name}...")
            if USE_POSTGRES:
                # Lazy import
                try:
                    import psycopg2
                except ImportError:
                    print("❌ psycopg2 not available, using SQLite")
                    return self._load_seen_items_sqlite()

                # PostgreSQL
                print(f"🔌 Connecting to PostgreSQL to load seen items...")
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT auction_id FROM seen_items
                    WHERE scraper_name = %s
                ''', (self.scraper_name,))

                seen_ids = set(row[0] for row in cursor.fetchall())
                conn.close()
                print(f"✅ PostgreSQL: Loaded {len(seen_ids)} seen items for {self.scraper_name}")
            else:
                seen_ids = self._load_seen_items_sqlite()

            # Show sample of seen IDs for debugging
            if len(seen_ids) > 0:
                sample = list(seen_ids)[:3]
                print(f"📋 Sample seen IDs: {sample}")
            else:
                print(f"⚠️ WARNING: No seen items loaded! This may cause duplicate posts.")

            return seen_ids
        except Exception as e:
            print(f"❌ Could not load seen items from database: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            return set()

    def _load_seen_items_sqlite(self):
        """Load seen items from SQLite"""
        try:
            conn = sqlite3.connect(self.scraper_db)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT auction_id FROM seen_items
                WHERE scraper_name = ?
            ''', (self.scraper_name,))

            seen_ids = set(row[0] for row in cursor.fetchall())
            conn.close()
            print(f"💾 SQLite: Loaded {len(seen_ids)} seen items for {self.scraper_name}")
            return seen_ids
        except Exception as e:
            print(f"❌ SQLite load error: {e}")
            return set()

    def _load_sqlite(self):
        """Load from SQLite (helper method)"""
        conn = sqlite3.connect(self.scraper_db)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT auction_id FROM seen_items
            WHERE scraper_name = ?
        ''', (self.scraper_name,))

        seen_ids = set(row[0] for row in cursor.fetchall())
        conn.close()
        return seen_ids

    def save_seen_items(self):
        """Save seen auction IDs to database (PostgreSQL or SQLite)"""
        try:
            if USE_POSTGRES:
                # Lazy import
                try:
                    import psycopg2
                except ImportError:
                    print("❌ psycopg2 not available, using SQLite")
                    return self._save_seen_items_sqlite()

                # PostgreSQL - batch insert is more efficient
                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()

                # Insert new auction IDs (ON CONFLICT DO NOTHING = ignore if exists)
                for auction_id in self.seen_ids:
                    cursor.execute('''
                        INSERT INTO seen_items (scraper_name, auction_id)
                        VALUES (%s, %s)
                        ON CONFLICT (scraper_name, auction_id) DO NOTHING
                    ''', (self.scraper_name, auction_id))

                conn.commit()
                conn.close()
                print(f"💾 Saved {len(self.seen_ids)} total seen items to PostgreSQL")
            else:
                self._save_seen_items_sqlite()
        except Exception as e:
            print(f"❌ Could not save seen items to database: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")

    def _save_seen_items_sqlite(self):
        """Save seen items to SQLite"""
        try:
            conn = sqlite3.connect(self.scraper_db)
            cursor = conn.cursor()

            # Insert new auction IDs (ignore if already exists)
            for auction_id in self.seen_ids:
                cursor.execute('''
                    INSERT OR IGNORE INTO seen_items (scraper_name, auction_id)
                    VALUES (?, ?)
                ''', (self.scraper_name, auction_id))

            conn.commit()
            conn.close()
            print(f"💾 Saved {len(self.seen_ids)} total seen items to SQLite")
        except Exception as e:
            print(f"❌ SQLite save error: {e}")

    def load_scraper_state(self, key, default=0):
        """Load scraper state from database (for page offset, etc.)"""
        try:
            if USE_POSTGRES:
                try:
                    import psycopg2
                except ImportError:
                    return default

                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT page_offset FROM scraper_state
                    WHERE scraper_name = %s
                ''', (self.scraper_name,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    print(f"📖 Loaded {key}={result[0]} from PostgreSQL for {self.scraper_name}")
                    return result[0]
                else:
                    print(f"📖 No saved state found, using default {key}={default}")
                    return default
            else:
                conn = sqlite3.connect(self.scraper_db)
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT page_offset FROM scraper_state
                    WHERE scraper_name = ?
                ''', (self.scraper_name,))
                result = cursor.fetchone()
                conn.close()

                if result:
                    print(f"📖 Loaded {key}={result[0]} from SQLite for {self.scraper_name}")
                    return result[0]
                else:
                    return default
        except Exception as e:
            print(f"⚠️ Could not load scraper state: {e}")
            return default

    def save_scraper_state(self, key, value):
        """Save scraper state to database (for page offset, etc.)"""
        try:
            if USE_POSTGRES:
                try:
                    import psycopg2
                except ImportError:
                    return

                conn = psycopg2.connect(DATABASE_URL)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scraper_state (scraper_name, page_offset, last_updated)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (scraper_name)
                    DO UPDATE SET page_offset = EXCLUDED.page_offset, last_updated = CURRENT_TIMESTAMP
                ''', (self.scraper_name, value))
                conn.commit()
                conn.close()
                print(f"💾 Saved {key}={value} to PostgreSQL for {self.scraper_name}")
            else:
                conn = sqlite3.connect(self.scraper_db)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO scraper_state (scraper_name, page_offset, last_updated)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (self.scraper_name, value))
                conn.commit()
                conn.close()
                print(f"💾 Saved {key}={value} to SQLite for {self.scraper_name}")
        except Exception as e:
            print(f"⚠️ Could not save scraper state: {e}")
    
    def load_brand_data(self):
        try:
            if os.path.exists("brands.json"):
                with open("brands.json", 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self.get_default_brands()
        except Exception as e:
            print(f"⚠️ Could not load brand data, using defaults: {e}")
            return self.get_default_brands()
    
    def get_default_brands(self):
        return {
            "Raf Simons": {"variants": ["raf simons", "raf", "ラフシモンズ"], "tier": 1},
            "Rick Owens": {"variants": ["rick owens", "rick", "リックオウエンス"], "tier": 1},
            "Maison Margiela": {"variants": ["margiela", "maison margiela", "メゾンマルジェラ"], "tier": 1},
            "Jean Paul Gaultier": {"variants": ["jean paul gaultier", "gaultier", "jpg", "ジャンポールゴルチエ"], "tier": 1},
            "Yohji Yamamoto": {"variants": ["yohji yamamoto", "yohji", "ヨウジヤマモト"], "tier": 2},
            "Junya Watanabe": {"variants": ["junya watanabe", "junya", "ジュンヤワタナベ"], "tier": 2},
            "Undercover": {"variants": ["undercover", "アンダーカバー"], "tier": 2},
            "Vetements": {"variants": ["vetements", "ヴェトモン"], "tier": 2},
            "Comme des Garcons": {"variants": ["comme des garcons", "cdg", "コムデギャルソン"], "tier": 3},
            "Martine Rose": {"variants": ["martine rose", "マルティーヌローズ"], "tier": 3},
            "Balenciaga": {"variants": ["balenciaga", "バレンシアガ"], "tier": 3},
            "Alyx": {"variants": ["alyx", "1017 alyx", "アリクス"], "tier": 3},
            "Celine": {"variants": ["celine", "セリーヌ"], "tier": 4},
            "Bottega Veneta": {"variants": ["bottega veneta", "bottega", "ボッテガヴェネタ"], "tier": 4},
            "Kiko Kostadinov": {"variants": ["kiko kostadinov", "kiko", "キコ"], "tier": 4},
            "Prada": {"variants": ["prada", "プラダ"], "tier": 5},
            "Miu Miu": {"variants": ["miu miu", "ミュウミュウ"], "tier": 5},
            "Chrome Hearts": {"variants": ["chrome hearts", "クロムハーツ"], "tier": 5}
        }
    
    def get_usd_jpy_rate(self):
        """Get current USD to JPY exchange rate"""
        try:
            response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.current_usd_jpy_rate = data['rates']['JPY']
                print(f"💱 Updated exchange rate: 1 USD = {self.current_usd_jpy_rate:.2f} JPY")
                return self.current_usd_jpy_rate
        except Exception as e:
            print(f"⚠️ Could not fetch exchange rate: {e}")
        
        return self.current_usd_jpy_rate
    
    def convert_jpy_to_usd(self, jpy_amount):
        """Convert JPY to USD using current exchange rate"""
        return jpy_amount / self.current_usd_jpy_rate
    
    def convert_usd_to_jpy(self, usd_amount):
        """Convert USD to JPY using current exchange rate"""
        return usd_amount * self.current_usd_jpy_rate
    
    def extract_auction_id_from_url(self, url):
        """Extract clean auction ID from Yahoo Japan URL"""
        try:
            auction_id = None
            
            # Method 1: Extract from /auction/ path
            if "/auction/" in url:
                auction_id = url.split("/auction/")[-1].split("?")[0]
            
            # Method 2: Extract from aID parameter
            elif "aID=" in url:
                auction_id = url.split("aID=")[-1].split("&")[0]
            
            # Method 3: Extract from URL segments
            else:
                url_parts = url.split("/")
                for part in reversed(url_parts):
                    if part and not part.startswith("?") and len(part) > 5:
                        auction_id = part.split("?")[0]
                        break
            
            if auction_id:
                # Clean up the auction ID - keep the 'u' prefix for ZenMarket
                auction_id = auction_id.strip()
                
                # Ensure the auction ID has the 'u' prefix for ZenMarket
                if not auction_id.startswith('u') and auction_id.isdigit():
                    auction_id = f"u{auction_id}"
                
                return auction_id
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting auction ID from {url}: {e}")
            return None
    
    def build_search_url(self, keyword, page=1, fixed_type=3, sort_type="end", sort_order="a", page_size=50, category=None):
        """
        Build Yahoo Japan search URL with all parameters

        Args:
            keyword: Search term
            page: Page number (1-based)
            fixed_type: 1=fixed price only, 2=auction only, 3=both
            sort_type: "end"=ending soon, "new"=newest, "price"=price
            sort_order: "a"=ascending, "d"=descending
            page_size: Items per page (default 50, max recommended 100)
            category: Yahoo category code (e.g., "2084005438" for Fashion & Accessories)
        """
        base_url = "https://auctions.yahoo.co.jp/search/search"

        # Calculate starting position (Yahoo uses 1-based indexing)
        start_position = (page - 1) * page_size + 1

        # Minimal parameters matching known working URLs
        params = {
            'p': keyword,
            'va': keyword,  # Verified auction parameter
            'fixed': str(fixed_type),
            'is_postage_mode': '1',
            'dest_pref_code': '13',  # Tokyo prefecture for shipping
            'b': str(start_position),
            'n': str(page_size)  # items per page (reduced from 100 to 50)
        }

        # Add category filter if specified (CRITICAL for filtering out non-fashion items)
        if category:
            params['auccat'] = str(category)

        # Add sorting parameters
        if sort_type == "end":
            params['s1'] = 'end'
            params['o1'] = sort_order
        elif sort_type == "new":
            params['s1'] = 'new'
            params['o1'] = sort_order
        elif sort_type == "price":
            params['s1'] = 'cbids'
            params['o1'] = sort_order

        # Use urlencode with quote_plus to ensure spaces become '+' (Yahoo preference)
        # Removed: ei=utf-8, price filters (these may trigger 500 errors)
        param_string = urllib.parse.urlencode(params, quote_via=urllib.parse.quote_plus)
        return f"{base_url}?{param_string}"
    
    def extract_auction_data(self, item):
        """Extract auction data from BeautifulSoup item"""
        try:
            self.stats['total_processed'] += 1

            # Get auction link and ID
            link_tag = item.select_one("a.Product__titleLink")
            if not link_tag:
                return None

            link = link_tag.get('href', '')
            if not link.startswith("http"):
                link = "https://auctions.yahoo.co.jp" + link

            # Get auction ID using improved extraction
            auction_id = self.extract_auction_id_from_url(link)
            if not auction_id or auction_id in self.seen_ids:
                return None

            # Debug: Print the auction ID and URL for troubleshooting
            print(f"🔍 Extracted auction ID: '{auction_id}' from URL: {link}")

            # Get title
            title = link_tag.get_text(strip=True)
            if not title:
                return None

            # Detect brand early for spam detection
            brand = self.detect_brand_in_title(title)

            # ENHANCED spam filtering using EnhancedSpamDetector
            is_spam, spam_type = self.spam_detector.is_spam(title, brand, item, "", link)
            if is_spam:
                self.stats['spam_blocked'] += 1
                print(f"🚫 Spam blocked ({spam_type}): {title[:50]}...")
                return None

            # Clothing check (less aggressive now)
            if not self.is_clothing_item(title):
                self.stats['clothing_blocked'] += 1
                print(f"🚫 Clothing filter blocked: {title[:50]}...")
                return None
            
            # Get price
            price_tag = item.select_one(".Product__priceValue")
            if not price_tag:
                return None
                
            price_text = price_tag.get_text(strip=True)
            price_jpy = self.extract_price_from_text(price_text)
            if not price_jpy:
                return None
            
            price_usd = price_jpy / self.current_usd_jpy_rate
            
            # Get image
            img_tag = item.select_one("img")
            image_url = img_tag.get('src', '') if img_tag else ''
            
            # Get end time (for auctions only)
            end_time = None
            end_tag = item.select_one(".Product__time")
            if end_tag:
                end_time = self.parse_end_time(end_tag.get_text(strip=True))
            
            # Detect brand
            brand = self.detect_brand_in_title(title)
            
            # Get seller info
            seller_id = self.extract_seller_info(item)
            
            # Calculate deal quality (keep for scoring but don't filter)
            deal_quality = self.calculate_deal_quality(price_usd, brand, title)
            
            # Build correct ZenMarket URL
            # ZenMarket format: https://zenmarket.jp/en/auction.aspx?itemCode=u[auction_id]
            # The auction_id now includes the 'u' prefix
            zenmarket_url = f"https://zenmarket.jp/en/auction.aspx?itemCode={auction_id}"
            
            # Debug: Print the ZenMarket URL for verification
            print(f"🔗 ZenMarket URL: {zenmarket_url}")
            
            return {
                'auction_id': auction_id,
                'title': title,
                'brand': brand,
                'price_jpy': price_jpy,
                'price_usd': round(price_usd, 2),
                'deal_quality': deal_quality,
                'yahoo_url': link,
                'zenmarket_url': zenmarket_url,
                'image_url': image_url,
                'seller_id': seller_id,
                'end_time': end_time,
                'found_at': datetime.now(timezone.utc).isoformat(),
                'scraper_source': self.scraper_name
            }
            
        except Exception as e:
            print(f"❌ Error extracting auction data: {e}")
            return None
    
    def is_enhanced_spam(self, title, brand=None):
        """Enhanced spam detection with new exclusions and JDirectItems filtering"""
        title_lower = title.lower()
        
        # NEW HIGH PRIORITY EXCLUSIONS
        new_excluded_keywords = {
            "LEGO", "レゴ",  # LEGO blocks
            "Water Tank", "ウォータータンク", "水タンク",  # Water tanks
            "BMW Touring E91", "BMW E91", "E91",  # BMW car parts
            "Mazda", "マツダ",  # Mazda car parts
            "Band of Outsiders", "バンドオブアウトサイダーズ"  # Unwanted brand
        }
        
        for excluded in new_excluded_keywords:
            if excluded.lower() in title_lower:
                print(f"🚫 NEW EXCLUSION BLOCKED: {excluded}")
                return True
        
        # STRICT JDirectItems FILTERING
        if "jdirectitems" in title_lower:
            # Extract category using regex pattern
            import re
            pattern = r'jdirectitems auction.*?→\s*([^,\n]+)'
            match = re.search(pattern, title_lower)
            if match:
                category = match.group(1).strip().lower()
                
                # Only allow fashion-related categories
                allowed_categories = {
                    "fashion", "clothing", "apparel", 
                    "ファッション", "衣類", "服", "洋服"
                }
                
                if not any(allowed in category for allowed in allowed_categories):
                    print(f"🚫 JDirectItems NON-FASHION BLOCKED: {category}")
                    return True
                else:
                    print(f"✅ JDirectItems FASHION ALLOWED: {category}")
        
        # EXISTING EXCLUSIONS (enhanced)
        existing_excluded_items = {
            "perfume", "cologne", "fragrance", "香水", "watch", "時計", 
            "motorcycle", "engine", "エンジン", "cb400", "vtr250",
            "server", "raid", "pci", "computer", "食品", "food", "snack",
            "財布", "バッグ", "鞄", "カバン", "poster", "ポスター", 
            "sticker", "ステッカー", "magazine", "雑誌", "dvd", "book",
            "本", "figure", "フィギュア", "toy", "おもちゃ"
        }
        
        for excluded in existing_excluded_items:
            if excluded in title_lower:
                print(f"🚫 EXISTING EXCLUSION BLOCKED: {excluded}")
                return True
        
        return False
    
    def is_clothing_item(self, title):
        """Less restrictive clothing detection - allow more items through"""
        title_lower = title.lower()

        # Expanded clothing keywords for better coverage
        clothing_keywords = {
            # English keywords
            "shirt", "tee", "tshirt", "t-shirt", "jacket", "blazer", "coat", "parka",
            "pants", "trousers", "jeans", "denim", "hoodie", "sweatshirt", "sweater",
            "dress", "skirt", "shorts", "vest", "cardigan", "pullover", "knit",
            "top", "bottom", "wear", "outerwear", "innerwear", "clothing", "apparel",
            "suit", "blazer", "overcoat", "windbreaker", "bomber", "leather",
            "cargo", "chino", "jogger", "sweatpants", "tracksuit", "jersey",
            "polo", "henley", "tank", "sleeveless", "longsleeve", "crewneck",
            "boots", "shoes", "sneakers", "sandals", "loafers", "oxfords",

            # Japanese keywords (comprehensive)
            "シャツ", "Tシャツ", "ジャケット", "コート", "パンツ", "ジーンズ",
            "パーカー", "スウェット", "セーター", "ワンピース", "スカート",
            "ベスト", "カーディガン", "プルオーバー", "アウター", "インナー",
            "トップス", "ボトムス", "ウェア", "服", "衣類", "洋服",
            "デニム", "ニット", "スーツ", "ブレザー", "オーバーコート",
            "ボンバー", "レザー", "カーゴ", "チノ", "ジョガー",
            "ポロ", "タンクトップ", "長袖", "半袖", "クルーネック",
            "ブーツ", "シューズ", "スニーカー", "サンダル", "ローファー"
        }

        # Check for any clothing keyword
        for keyword in clothing_keywords:
            if keyword in title_lower:
                return True

        # LESS RESTRICTIVE: Allow items from known fashion brands even without keywords
        # If it's from a recognized brand, assume it's clothing
        brand = self.detect_brand_in_title(title)
        if brand != "Unknown":
            print(f"✅ Allowing brand item without clothing keyword: {brand}")
            return True

        # Default to ALLOWING (changed from blocking) - trust spam filter to catch non-fashion
        return True
    
    def extract_price_from_text(self, price_text):
        """Extract numeric price from price text"""
        price_match = re.search(r'([\d,]+)', price_text.replace(',', ''))
        if price_match:
            try:
                return int(price_match.group(1).replace(',', ''))
            except ValueError:
                return None
        return None
    
    def parse_end_time(self, time_text):
        """Parse auction end time from Japanese text"""
        try:
            # This would need proper Japanese time parsing
            # For now, return a placeholder
            return time_text
        except Exception:
            return None
    
    def detect_brand_in_title(self, title):
        """Detect brand in title"""
        title_lower = title.lower()
        
        for brand, brand_info in self.brand_data.items():
            for variant in brand_info.get('variants', []):
                if variant.lower() in title_lower:
                    return brand
        
        return "Unknown"
    
    def extract_seller_info(self, item):
        """Extract seller information"""
        try:
            seller_link = item.select_one("a[href*='sellerID']")
            if seller_link:
                href = seller_link.get('href', '')
                seller_match = re.search(r'sellerID=([^&]+)', href)
                if seller_match:
                    return seller_match.group(1)
            return "unknown"
        except Exception:
            return "unknown"
    
    def calculate_deal_quality(self, price_usd, brand, title):
        """Enhanced deal quality scoring with more generous thresholds"""
        title_lower = title.lower()
        quality = 0.2  # Higher base quality (was 0.1)
        
        # Enhanced brand quality boost (more generous)
        premium_brands = ["Raf Simons", "Rick Owens", "Maison Margiela", "Jean Paul Gaultier"]
        high_tier_brands = ["Yohji Yamamoto", "Junya Watanabe", "Undercover", "Vetements"]
        mid_tier_brands = ["Comme des Garcons", "Martine Rose", "Balenciaga", "Alyx"]
        
        if brand in premium_brands:
            quality += 0.4  # Increased from 0.3
        elif brand in high_tier_brands:
            quality += 0.3  # Increased from 0.2
        elif brand in mid_tier_brands:
            quality += 0.25  # New tier
        else:
            quality += 0.15  # Increased from 0.1
        
        # More generous price quality boost
        if price_usd <= 80:  # Lowered from 100
            quality += 0.35  # Increased from 0.3
        elif price_usd <= 150:  # Lowered from 200
            quality += 0.25  # Increased from 0.2
        elif price_usd <= 250:  # Lowered from 300
            quality += 0.15  # Increased from 0.1
        elif price_usd <= 400:  # New tier
            quality += 0.1
        
        # Archive/rare keywords (enhanced)
        archive_keywords = ["archive", "rare", "fw", "ss", "limited", "vintage", "deadstock", "sample"]
        if any(word in title_lower for word in archive_keywords):
            quality += 0.25  # Increased from 0.2
        
        # Size bonus (common sizes get slight boost)
        size_keywords = ["m", "l", "medium", "large", "28", "30", "32", "34", "36"]
        if any(word in title_lower for word in size_keywords):
            quality += 0.05
        
        return min(quality, 1.0)
    
    def send_to_discord(self, auction_data):
        """Send auction data to Discord via webhook"""
        try:
            webhook_url = f"{self.discord_bot_url}/webhook/listing"

            # Debug logging
            print(f"🔗 Attempting to send to: {webhook_url}")
            print(f"📦 Data includes scraper_source: {auction_data.get('scraper_source', 'NOT SET')}")

            # Ensure scraper_source is set for proper Discord bot routing
            if 'scraper_source' not in auction_data:
                auction_data['scraper_source'] = self.scraper_name

            response = requests.post(webhook_url, json=auction_data, timeout=10)

            print(f"📡 Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"📄 Response content: {response.text[:200]}...")

            if response.status_code in [200, 204]:
                self.stats['sent'] += 1  # Track successful sends
                print(f"✅ Sent to Discord bot: {auction_data['title'][:50]}...")
                return True
            else:
                print(f"❌ Discord webhook failed: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Discord webhook error: {e}")
            return False
    
    def determine_target_channels(self, auction_data, primary_channel):
        """Determine which channels to send the listing to"""
        channels = [primary_channel]
        
        price_usd = auction_data['price_usd']
        brand = auction_data['brand']
        
        # Always send to main auction alerts
        if primary_channel != '🎯-auction-alerts':
            channels.append('🎯-auction-alerts')
        
        # Send to budget steals if ≤ $60
        if price_usd <= 60 and primary_channel != '💰-budget-steals':
            channels.append('💰-budget-steals')
        
        # Send to brand channel if brand detected
        if brand != "Unknown":
            brand_channel = f"🏷️-{brand.lower().replace(' ', '-')}"
            if brand_channel not in channels:
                channels.append(brand_channel)
        
        return channels
    
    def get_request_headers(self):
        """Get random headers for requests"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def get_session(self):
        """Get or create async HTTP session with connection pooling"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            timeout = aiohttp.ClientTimeout(total=15, connect=5)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.get_request_headers()
            )
        return self._session
    
    async def close_session(self):
        """Close async HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def fetch_page_async(self, url, max_retries=4):
        """
        Async version of fetch_page using aiohttp with retry logic

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts for 5xx errors

        Returns:
            tuple: (html_content, success) or (None, False) on error
        """
        for attempt in range(1, max_retries + 1):
            try:
                session = await self.get_session()
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return html, True
                    elif response.status >= 500:
                        # Server error - retry with exponential backoff
                        if attempt < max_retries:
                            delay = 2 ** attempt  # 2s, 4s, 8s, 16s
                            print(f"❌ HTTP {response.status} for {url}")
                            print(f"   ⏳ Retry {attempt}/{max_retries} after {delay}s...")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            print(f"❌ HTTP {response.status} for {url} (all retries exhausted)")
                            return None, False
                    else:
                        # Client error or other - don't retry
                        print(f"❌ HTTP {response.status} for {url}")
                        return None, False
            except asyncio.TimeoutError:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    print(f"⏱️ Timeout fetching {url} (attempt {attempt}/{max_retries})")
                    print(f"   ⏳ Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"⏱️ Timeout fetching {url} (all retries exhausted)")
                    return None, False
            except Exception as e:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    print(f"❌ Error fetching {url}: {e} (attempt {attempt}/{max_retries})")
                    print(f"   ⏳ Retrying after {delay}s...")
                    await asyncio.sleep(delay)
                    continue
                else:
                    print(f"❌ Error fetching {url}: {e} (all retries exhausted)")
                    return None, False

        return None, False
    
    def fetch_page(self, url, max_retries=4):
        """
        Synchronous version of fetch_page with retry logic

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts for 5xx errors

        Returns:
            tuple: (html_content, success) or (None, False) on error
        """
        for attempt in range(1, max_retries + 1):
            try:
                headers = self.get_request_headers()
                response = requests.get(url, headers=headers, timeout=15)

                if response.status_code == 200:
                    return response.text, True
                elif response.status_code >= 500:
                    # Server error - retry with exponential backoff
                    if attempt < max_retries:
                        delay = 2 ** attempt  # 2s, 4s, 8s, 16s
                        print(f"❌ HTTP {response.status_code} for {url}")
                        print(f"   ⏳ Retry {attempt}/{max_retries} after {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        print(f"❌ HTTP {response.status_code} for {url} (all retries exhausted)")
                        return None, False
                else:
                    # Client error or other - don't retry
                    print(f"❌ HTTP {response.status_code} for {url}")
                    return None, False
            except requests.Timeout:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    print(f"⏱️ Timeout fetching {url} (attempt {attempt}/{max_retries})")
                    print(f"   ⏳ Retrying after {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"⏱️ Timeout fetching {url} (all retries exhausted)")
                    return None, False
            except Exception as e:
                if attempt < max_retries:
                    delay = 2 ** attempt
                    print(f"❌ Error fetching {url}: {e} (attempt {attempt}/{max_retries})")
                    print(f"   ⏳ Retrying after {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"❌ Error fetching {url}: {e} (all retries exhausted)")
                    return None, False

        return None, False

    def analyze_filtering(self):
        """Log filtering statistics for debugging and optimization"""
        print(f"\n📊 ===== {self.scraper_name.upper()} FILTERING STATISTICS =====")
        print(f"   Total items processed:    {self.stats['total_processed']}")
        print(f"   🚫 Blocked by spam:       {self.stats['spam_blocked']}")
        print(f"   🚫 Blocked by clothing:   {self.stats['clothing_blocked']}")
        print(f"   🚫 Blocked by price:      {self.stats['price_blocked']}")
        print(f"   🚫 Blocked by quality:    {self.stats['quality_blocked']}")
        print(f"   ✅ Sent to Discord:       {self.stats['sent']}")
        print(f"   📦 Seen IDs tracked:      {len(self.seen_ids)}")

        # Calculate percentages
        if self.stats['total_processed'] > 0:
            sent_rate = (self.stats['sent'] / self.stats['total_processed']) * 100
            spam_rate = (self.stats['spam_blocked'] / self.stats['total_processed']) * 100
            print(f"\n   📈 Send rate:             {sent_rate:.1f}%")
            print(f"   📉 Spam block rate:       {spam_rate:.1f}%")

        print(f"========================================\n")

    def cleanup_old_seen_ids(self):
        """Remove seen IDs older than retention period to prevent memory bloat"""
        try:
            current_size = len(self.seen_ids)

            # Aggressive cleanup if we're over 50,000 items
            if current_size > 50000:
                print(f"🧹 AGGRESSIVE CLEANUP: {current_size} seen_ids (>50,000 limit)")
                # Keep only most recent 10,000 items
                self.seen_ids = set(list(self.seen_ids)[-10000:])
                self.save_seen_items()
                new_size = len(self.seen_ids)
                print(f"✅ Cleaned from {current_size} to {new_size} items")

            # Normal cleanup if we're over 30,000 items
            elif current_size > 30000:
                print(f"🧹 NORMAL CLEANUP: {current_size} seen_ids (>30,000)")
                # Keep most recent 20,000 items
                self.seen_ids = set(list(self.seen_ids)[-20000:])
                self.save_seen_items()
                new_size = len(self.seen_ids)
                print(f"✅ Cleaned from {current_size} to {new_size} items")

        except Exception as e:
            print(f"⚠️ Error during seen_ids cleanup: {e}")
