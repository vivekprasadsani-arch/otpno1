# Telegram OTP Bot

A Telegram bot for OTP number collection, live OTP monitoring, and channel forwarding with user approval and Supabase persistence.

## What this bot does

- User approval workflow (`pending` -> `approved` / `rejected`)
- Number collection by service and country
- Range-based flow (`/rangechkr`) with "Change Numbers"
- Direct range input support (example: `24491501XXX` or `24491501`)
- Multi-number monitoring in background (15 minute timeout)
- OTP forwarding to a Telegram channel with masked number format
- Per-user daily OTP stats (BD timezone)
- Duplicate protection for used numbers (24 hour check via `used_numbers` table)
- Console stream monitoring (`/mdashboard/console`) for WhatsApp and Telegram OTP-like messages

## Main commands

- `/start` - Register user (if needed), show menu for approved users
- `/rangechkr` - Browse services, countries, and ranges
- `/users` - Admin only, list users
- `/add <user_id>` - Admin only, add and approve user directly
- `/remove <user_id>` - Admin only, remove user and session
- `/pending` - Admin only, list pending users
- `/broadcast <message>` - Admin only, send message to all approved users

## User flow summary

1. User runs `/start`
2. If user is not approved, admin receives approve/reject buttons
3. Approved users get menu buttons:
   - `Get Number`
   - `Set Number Count` (1 to 5)
   - `My Stats`
4. User selects service and country (or range from `/rangechkr`, or direct range text)
5. Bot returns numbers with tap-to-copy buttons and starts OTP monitor
6. On OTP arrival:
   - User gets OTP message with copy button
   - Channel gets masked-number message and range deep-link button
7. Monitor stops when all numbers receive OTP or after 15 minutes timeout

## Tech stack

- Python 3.12
- `python-telegram-bot` (async, job queue)
- Supabase (Postgres + API)
- `requests` / `curl-cffi` / `cloudscraper` for upstream API
- Flask (health endpoint for Render web service)

## Project files

- `telegram_bot.py` - Main bot logic
- `supabase_schema.sql` - Required DB schema and indexes
- `render.yaml` - Render service blueprint
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python runtime version
- `analyze_login.py`, `parse_har.py`, `test_login.py` - Local debugging helpers for upstream login/API behavior

## Database setup (Supabase)

1. Open Supabase SQL Editor
2. Run [`supabase_schema.sql`](./supabase_schema.sql)
3. Confirm these tables exist:
   - `users`
   - `user_sessions`
   - `used_numbers`

## Environment variables

Set all of these in your deployment environment (Render or local `.env`):

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram bot token |
| `ADMIN_USER_ID` | Yes | Telegram user ID of admin |
| `OTP_CHANNEL_ID` | Yes | Telegram channel ID for OTP forwarding |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_KEY` | Yes | Supabase key (service role recommended for backend use) |
| `API_EMAIL` | Yes | Upstream API login email |
| `API_PASSWORD` | Yes | Upstream API login password |
| `PORT` | No | Flask health check port (default `10000`) |
| `API_IO_WORKERS` | No | Thread pool size for blocking API I/O (default `120`) |

Security note: always set explicit environment variables and do not rely on in-code fallback values. Rotate any exposed credentials.

## Run locally

```bash
pip install -r requirements.txt
python telegram_bot.py
```

Example `.env`:

```env
BOT_TOKEN=your_bot_token
ADMIN_USER_ID=123456789
OTP_CHANNEL_ID=-1001234567890
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
API_EMAIL=your_email@example.com
API_PASSWORD=your_password
PORT=10000
API_IO_WORKERS=120
```

## Deploy to Render

This repo includes [`render.yaml`](./render.yaml) with:

- Build command: `pip install -r requirements.txt`
- Start command: `python telegram_bot.py`
- Python version: `3.12.8`

After creating the service, set the environment variables listed above.

## Notes

- Bot runs in polling mode (`run_polling`) and also starts a Flask server for Render health checks.
- OTP monitoring jobs and console monitor run via job queue.
- Numbers that already received OTP are tracked in `used_numbers` and skipped for 24 hours.

## License

Private project.
