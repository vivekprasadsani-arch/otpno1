# Telegram OTP Bot

A production-ready Telegram bot for OTP service management with multi-user support, admin approval system, and real-time OTP monitoring.

## Features

- 🔐 Admin approval system for user registration
- 📱 Support for WhatsApp, Telegram, and Facebook OTP services
- 🌍 199+ countries with flag emojis
- 🔄 Real-time OTP monitoring and instant delivery
- 💾 Supabase PostgreSQL database for production
- 🔒 Cloudflare bypass using curl_cffi
- 🚀 Deployed on Render

## Setup Instructions

### 1. Database Setup (Supabase)

1. Go to your Supabase project SQL Editor
2. Run the SQL script from `supabase_schema.sql` to create the required tables:
   ```sql
   -- Copy and paste the contents of supabase_schema.sql
   ```

### 2. Environment Variables

Set the following environment variables in Render (or your hosting platform):

```
BOT_TOKEN=your_telegram_bot_token
ADMIN_USER_ID=your_admin_user_id
API_BASE_URL=https://v2.mnitnetwork.com
API_EMAIL=your_api_email
API_PASSWORD=your_api_password
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_DB_HOST=db.your-project.supabase.co
SUPABASE_DB_PORT=5432
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.your-project
SUPABASE_DB_PASSWORD=your_database_password
```

### 3. Deploy to Render

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python telegram_bot.py`
   - **Environment**: Python 3
4. Add all environment variables from step 2
5. Deploy!

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set environment variables (or use .env file):
   ```bash
   export BOT_TOKEN=your_token
   export ADMIN_USER_ID=your_id
   # ... other variables
   ```

3. Run the bot:
   ```bash
   python telegram_bot.py
   ```

## Database Schema

- **users**: Stores user information and approval status
- **user_sessions**: Stores active user sessions and OTP monitoring state

## Admin Commands

- `/users` - List all users
- `/pending` - List pending approval requests
- `/remove <user_id>` - Remove a user

## License

Private project - All rights reserved
