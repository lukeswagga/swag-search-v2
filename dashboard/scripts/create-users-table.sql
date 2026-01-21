-- Create users table for SwagSearch dashboard
-- Run this manually in your PostgreSQL database (Railway)

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  discord_id VARCHAR(255) UNIQUE NOT NULL,
  discord_username VARCHAR(255),
  discord_avatar VARCHAR(255),
  email VARCHAR(255),
  subscription_tier VARCHAR(50) DEFAULT 'free',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Create index on discord_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id);

-- Add comment
COMMENT ON TABLE users IS 'Stores Discord OAuth user information for SwagSearch dashboard';

