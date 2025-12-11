-- Supabase Database Schema for Telegram Bot
-- Run this SQL in Supabase SQL Editor to create tables

-- Drop existing tables if they exist (to recreate with correct schema)
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

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
    number_count INTEGER DEFAULT 5,
    last_check TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_user_sessions_monitoring ON user_sessions(monitoring);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);

-- Enable Row Level Security (RLS) if needed
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;

-- Create policies to allow all operations (adjust as needed for security)
CREATE POLICY "Allow all operations on users" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations on user_sessions" ON user_sessions FOR ALL USING (true) WITH CHECK (true);

