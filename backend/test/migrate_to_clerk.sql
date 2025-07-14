-- Migration: Update users table for Clerk authentication
-- This script migrates from password-based auth to Clerk JWT auth

-- Step 1: Add new columns for Clerk authentication
ALTER TABLE users ADD COLUMN clerk_id VARCHAR(255);
ALTER TABLE users ADD COLUMN first_name VARCHAR(255);
ALTER TABLE users ADD COLUMN last_name VARCHAR(255);
ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Step 2: Create a function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Step 3: Create trigger for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Step 4: For existing users, you have a few options:
-- Option A: Clear the table (if you don't have important data)
-- TRUNCATE users CASCADE;

-- Option B: Create placeholder clerk_ids for existing users (if you have existing data)
-- UPDATE users SET clerk_id = 'legacy_' || id::text WHERE clerk_id IS NULL;

-- Step 5: Make clerk_id NOT NULL and UNIQUE after handling existing data
-- Uncomment these lines after you've handled existing users:
-- ALTER TABLE users ALTER COLUMN clerk_id SET NOT NULL;
-- ALTER TABLE users ADD CONSTRAINT users_clerk_id_unique UNIQUE (clerk_id);

-- Step 6: Drop the old password_hash column (after confirming everything works)
-- ALTER TABLE users DROP COLUMN password_hash;

-- Step 7: Add index for performance
CREATE INDEX idx_users_clerk_id ON users(clerk_id);

-- Step 8: Update comments
COMMENT ON COLUMN users.clerk_id IS 'Clerk user ID from JWT sub claim';
COMMENT ON COLUMN users.first_name IS 'User first name from Clerk';
COMMENT ON COLUMN users.last_name IS 'User last name from Clerk';
COMMENT ON COLUMN users.updated_at IS 'Timestamp when user data was last updated';

-- Step 9: Update table comment
COMMENT ON TABLE users IS 'Registered users authenticated via Clerk';

-- Note: After running this migration, you'll need to:
-- 1. Set environment variables: CLERK_DOMAIN, JWKS_URL
-- 2. Install new dependencies: pip install PyJWT cryptography
-- 3. Update your application code to use the new auth system 