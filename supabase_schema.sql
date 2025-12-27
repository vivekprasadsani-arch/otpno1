-- Supabase Database Schema for Telegram Bot
-- Run this SQL in Supabase SQL Editor to create tables

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

-- User sessions table (for active OTP monitoring and preferences)
CREATE TABLE IF NOT EXISTS user_sessions (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    selected_service TEXT,
    selected_country TEXT,
    range_id TEXT,
    number TEXT,
    monitoring INTEGER DEFAULT 0,
    number_count INTEGER DEFAULT 2,
    otp_count INTEGER DEFAULT 0,
    otp_date TEXT,
    last_check TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Used numbers table (to prevent reuse within 24 hours)
CREATE TABLE IF NOT EXISTS used_numbers (
    number TEXT PRIMARY KEY,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_user_sessions_monitoring ON user_sessions(monitoring);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_used_numbers_used_at ON used_numbers(used_at);

-- Apply Row Level Security (Good practice even if policies are permissive initially)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create policies (safe to run multiple times, they will just error or be ignored if exist, but 'DO' block is cleaner for idempotency)
-- However, for simple SQL editor usage, simple CREATE POLICY IF NOT EXISTS is not standard Postgres < 14/15 depending on version.
-- Best to drop and recreate for policies if needed, or wrap in DO block.
-- For simplicity here, we assume if tables exist, policies might too.
-- Let's use a safe format for policies:

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow all operations on users') THEN
        CREATE POLICY "Allow all operations on users" ON users FOR ALL USING (true) WITH CHECK (true);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow all operations on user_sessions') THEN
        CREATE POLICY "Allow all operations on user_sessions" ON user_sessions FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;
