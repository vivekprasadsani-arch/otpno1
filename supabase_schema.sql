-- Supabase Database Schema for Telegram Bot
-- Run this SQL in Supabase SQL Editor to create tables

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    last_check TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_user_sessions_monitoring ON user_sessions(monitoring);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);

