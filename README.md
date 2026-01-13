# Telegram OTP Bot

Production-ready Telegram bot for OTP number management and monitoring.

## Features

- OTP number fetching and monitoring
- Multi-service support (WhatsApp, Facebook, Others)
- Range-based number selection
- Real-time OTP detection and forwarding
- User approval system
- Supabase database integration

## Setup Instructions

### 1. Database Setup (Supabase)

1. Go to your Supabase project SQL Editor
2. Run the SQL commands from `database.sql` to create tables:
   - `users` table
   - `user_sessions` table

### 2. Environment Variables

Set these environment variables in Render:

- `BOT_TOKEN` - Your Telegram bot token
- `ADMIN_USER_ID` - Your Telegram user ID (admin)
- `OTP_CHANNEL_ID` - Channel ID for OTP forwarding
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon key
- `API_EMAIL` - API login email
- `API_PASSWORD` - API login password

### 3. Deploy to Render

1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Use the following settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python telegram_bot.py`
   - Add all environment variables from step 2

### 4. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
BOT_TOKEN=your_bot_token
ADMIN_USER_ID=your_user_id
OTP_CHANNEL_ID=your_channel_id
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
API_EMAIL=your_api_email
API_PASSWORD=your_api_password

# Run bot
python telegram_bot.py
```

## Database Schema

### users
- `user_id` (BIGINT PRIMARY KEY)
- `username` (TEXT)
- `status` (TEXT DEFAULT 'pending')
- `created_at` (TIMESTAMP)
- `approved_at` (TIMESTAMP)

### user_sessions
- `user_id` (BIGINT PRIMARY KEY)
- `selected_service` (TEXT)
- `selected_country` (TEXT)
- `range_id` (TEXT)
- `number` (TEXT)
- `monitoring` (INTEGER DEFAULT 0)
- `last_check` (TIMESTAMP)

## Commands

- `/start` - Start the bot
- `/rangechkr` - Check available ranges
- Admin commands: `/users`, `/approve`, `/reject`, `/remove`

## License

Private project
