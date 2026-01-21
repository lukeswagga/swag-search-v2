"""
Simple script to check database contents
Run: python v2/check_database.py
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_database, create_tables
from sqlalchemy import select, text, func
from models import Listing
import database as db_module


async def check_database():
    """Check database contents"""
    print("🔧 Connecting to database...")
    init_database()
    await create_tables()
    
    async with db_module._session_factory() as session:
        # Total count
        result = await session.execute(text('SELECT COUNT(*) FROM listings'))
        total = result.scalar()
        print(f"\n✅ Total listings in database: {total}")
        
        if total == 0:
            print("\n⚠️  Database is empty - no listings saved yet")
            print("   Run the scraper to populate the database")
            return
        
        # Count by market
        result = await session.execute(
            text('SELECT market, COUNT(*) FROM listings GROUP BY market ORDER BY COUNT(*) DESC')
        )
        by_market = result.fetchall()
        print(f"\n📊 Listings by market:")
        for market, count in by_market:
            print(f"   {market}: {count}")
        
        # Count by brand (top 10)
        result = await session.execute(
            text("""
                SELECT brand, COUNT(*) 
                FROM listings 
                WHERE brand IS NOT NULL
                GROUP BY brand 
                ORDER BY COUNT(*) DESC 
                LIMIT 10
            """)
        )
        by_brand = result.fetchall()
        if by_brand:
            print(f"\n🏷️  Top 10 brands:")
            for brand, count in by_brand:
                print(f"   {brand}: {count}")
        
        # Newest listings
        result = await session.execute(
            select(Listing)
            .order_by(Listing.first_seen.desc())
            .limit(5)
        )
        newest = result.scalars().all()
        print(f"\n🆕 Newest 5 listings:")
        for listing in newest:
            print(f"   [{listing.market}] {listing.external_id}")
            print(f"      {listing.title[:60]}...")
            print(f"      ¥{listing.price_jpy:,} | Brand: {listing.brand or 'N/A'}")
            print(f"      First seen: {listing.first_seen}")
            print()
        
        # Oldest listings
        result = await session.execute(
            select(Listing)
            .order_by(Listing.first_seen.asc())
            .limit(5)
        )
        oldest = result.scalars().all()
        print(f"📅 Oldest 5 listings:")
        for listing in oldest:
            print(f"   [{listing.market}] {listing.external_id}")
            print(f"      {listing.title[:60]}...")
            print(f"      ¥{listing.price_jpy:,} | Brand: {listing.brand or 'N/A'}")
            print(f"      First seen: {listing.first_seen}")
            print()
        
        # Recent activity (listings seen in last hour)
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM listings 
                WHERE last_seen > NOW() - INTERVAL '1 hour'
            """)
        )
        recent = result.scalar()
        print(f"🕐 Listings seen in last hour: {recent}")
    
    from database import close_database
    await close_database()
    print("\n✅ Database check complete")


if __name__ == "__main__":
    asyncio.run(check_database())

