-- Supabase Database Setup for Telegram Bot
-- Run this SQL in Supabase SQL Editor

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    approved_at TIMESTAMP
);

-- User sessions table (for active OTP monitoring)
CREATE TABLE IF NOT EXISTS user_sessions (
    user_id BIGINT PRIMARY KEY,
    selected_service TEXT,
    selected_country TEXT,
    range_id TEXT,
    number TEXT,
    monitoring INTEGER DEFAULT 0,
    last_check TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_user_sessions_monitoring ON user_sessions(monitoring);

