#!/usr/bin/env python3
"""
Quick script to run the category column migration
Run this on your production server (Railway, etc.) where DATABASE_URL is set
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from migrations.add_category_column import add_category_column

if __name__ == "__main__":
    print("🚀 Running category column migration...")
    print(f"📊 DATABASE_URL is {'set' if os.getenv('DATABASE_URL') else 'NOT SET'}")
    print()
    
    try:
        asyncio.run(add_category_column())
        print("\n✅ Migration completed successfully!")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

