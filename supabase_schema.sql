-- Supabase Database Schema for Telegram Bot
-- Run this SQL in Supabase SQL Editor to create tables

-- Drop existing tables if they exist (to recreate with correct schema)
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS used_numbers CASCADE;

-- Users table
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

-- User sessions table (for active OTP monitoring)
CREATE TABLE user_sessions (
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
CREATE TABLE used_numbers (
    number TEXT PRIMARY KEY,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_user_sessions_monitoring ON user_sessions(monitoring);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_used_numbers_used_at ON used_numbers(used_at);

-- Enable Row Level Security (RLS) if needed
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE used_numbers ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (adjust as needed for security)
CREATE POLICY "Allow all operations on users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on user_sessions" ON user_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on used_numbers" ON used_numbers FOR ALL USING (true) WITH CHECK (true);
