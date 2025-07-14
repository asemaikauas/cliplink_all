#!/usr/bin/env python3
"""
Migration Script: Fix video_status enum to lowercase values

This script runs the migration to fix the video_status enum values
to match the schema.sql file (lowercase values).
"""

import asyncio
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def run_migration():
    """Run the migration to fix video_status enum values"""
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    # Create database engine
    engine = create_async_engine(database_url)
    
    try:
        # Read migration file
        migration_file = Path(__file__).parent / "migrations" / "002_fix_video_status_enum.sql"
        
        if not migration_file.exists():
            print(f"❌ Migration file not found: {migration_file}")
            return False
        
        migration_sql = migration_file.read_text()
        
        print("🔄 Running migration: Fix video_status enum to lowercase values...")
        
        # Run the migration
        async with engine.begin() as conn:
            await conn.execute(text(migration_sql))
            print("✅ Migration completed successfully!")
            
            # Verify the migration worked
            result = await conn.execute(text("SELECT unnest(enum_range(NULL::video_status)) AS enum_value"))
            enum_values = result.fetchall()
            
            print("📊 Current enum values after migration:")
            for row in enum_values:
                print(f"  - {row[0]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("✅ Your database now uses lowercase enum values that match your schema.sql")
        print("✅ You can now test the comprehensive workflow without enum errors")
    else:
        print("\n💥 Migration failed. Please check the errors above.")
        exit(1) 