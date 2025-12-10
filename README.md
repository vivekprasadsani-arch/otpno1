# Telegram OTP Bot

<<<<<<< HEAD
Production-ready Telegram bot for OTP number management and monitoring.

## Features

- OTP number fetching and monitoring
- Multi-service support (WhatsApp, Facebook, Others)
- Range-based number selection
- Real-time OTP detection and forwarding
- User approval system
- Supabase database integration
=======
A production-ready Telegram bot for OTP service management with multi-user support, admin approval system, and real-time OTP monitoring.

## Features

- 🔐 Admin approval system for user registration
- 📱 Support for WhatsApp, Telegram, and Facebook OTP services
- 🌍 199+ countries with flag emojis
- 🔄 Real-time OTP monitoring and instant delivery
- 💾 Supabase PostgreSQL database for production
- 🔒 Cloudflare bypass using curl_cffi
- 🚀 Deployed on Render
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

## Setup Instructions

### 1. Database Setup (Supabase)

1. Go to your Supabase project SQL Editor
<<<<<<< HEAD
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
=======
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

#### Option A: Using render.yaml (Recommended)
1. Connect your GitHub repository to Render
2. Render will automatically detect `render.yaml` and use the configuration
3. Add all environment variables from step 2 in Render dashboard
4. Deploy!

#### Option B: Manual Setup
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 1 -b 0.0.0.0:$PORT telegram_bot:flask_app`
   - **Environment**: Python 3
4. Add all environment variables from step 2:
   - `USE_WEBHOOK=true`
   - `WEBHOOK_URL` (will be auto-set, or use your Render service URL)
   - All other variables from step 2
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
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
