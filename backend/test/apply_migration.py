#!/usr/bin/env python3
"""
Apply Azure Blob Storage migration to the database
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from dotenv import load_dotenv 

load_dotenv()

async def apply_migration():
    """Apply the Azure Blob Storage migration"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
        
    # Convert to async URL if needed
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    try:
        async with async_session() as session:
            print("🔄 Applying Azure Blob Storage migration...")
            
            # Execute each SQL statement separately
            migration_statements = [
                "ALTER TABLE clips RENAME COLUMN s3_url TO blob_url;",
                "ALTER TABLE clips ADD COLUMN thumbnail_url TEXT;",
                "ALTER TABLE clips ADD COLUMN file_size FLOAT;",
                "COMMENT ON COLUMN clips.blob_url IS 'Azure Blob Storage URL where the processed clip is stored';",
                "COMMENT ON COLUMN clips.thumbnail_url IS 'Azure Blob Storage URL for the clip thumbnail image';",
                "COMMENT ON COLUMN clips.file_size IS 'File size in bytes';",
                "CREATE INDEX idx_clips_blob_url ON clips(blob_url);",
                "CREATE INDEX idx_clips_thumbnail_url ON clips(thumbnail_url);",
                "COMMENT ON TABLE clips IS 'Individual short video clips generated from YouTube videos, stored in Azure Blob Storage';"
            ]
            
            for i, statement in enumerate(migration_statements, 1):
                try:
                    print(f"  {i}/{len(migration_statements)}: Executing {statement.split()[0]} command...")
                    await session.execute(text(statement))
                    await session.commit()
                except Exception as e:
                    if "already exists" in str(e) or "does not exist" in str(e):
                        print(f"    ⚠️  Skipping (already applied): {e}")
                        continue
                    else:
                        raise e
            
            print("✅ Migration applied successfully!")
            
            # Verify the changes
            result = await session.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'clips' 
                ORDER BY ordinal_position;
            """))
            
            print("\n📋 Updated clips table structure:")
            for row in result:
                print(f"  - {row.column_name} ({row.data_type})")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(apply_migration())
    if success:
        print("\n🎉 Database migration completed! You can now run the integration test.")
    else:
        print("\n💥 Migration failed. Please check the errors above.") 