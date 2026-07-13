import os
import threading
import time
import asyncio
import concurrent.futures
from datetime import datetime, timedelta, timezone
from datetime import datetime, timedelta, timezone
import requests
import codec
import json
import re
import hashlib
import html
import unicodedata
import random
from functools import partial
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import Conflict
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
from flask import Flask

# Premium emoji helper - loads mappings from premium_emojis.json
_PREMIUM_EMOJI_MAP = None

def pe(emoji_char):
    """Return premium emoji HTML tag for a standard emoji character.
    Usage: pe('💬') -> '<tg-emoji emoji-id="5233376087777501917">💬</tg-emoji>'
    In f-strings: f"{pe('💬')} WhatsApp"
    """
    global _PREMIUM_EMOJI_MAP
    if _PREMIUM_EMOJI_MAP is None:
        try:
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'premium_emojis.json')
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _PREMIUM_EMOJI_MAP = {}
            for category in data.values():
                _PREMIUM_EMOJI_MAP.update(category)
        except Exception:
            _PREMIUM_EMOJI_MAP = {}
    eid = _PREMIUM_EMOJI_MAP.get(emoji_char)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{emoji_char}</tg-emoji>'
    return emoji_char



# Load environment variables
load_dotenv()

# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

# Try to import curl_cffi for Cloudflare bypass (better than cloudscraper)
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def normalize_range_token(value):
    """Normalize any range-like token, preserving letters and underscores for IDs like b_42."""
    if value is None:
        return ""
    return re.sub(r'[^A-Za-z0-9_\-]', '', str(value)).replace('x', 'X')


def _build_bengali_proverb_pool(target_size=1000):
    """Build a deterministic pool of Bengali proverb-style motivation lines."""
    starters = [
        "ধৈর্য ধরলে", "সততা রাখলে", "পরিশ্রম করলে", "সময়কে সম্মান করলে", "ছোট পদক্ষেপ নিলে",
        "লক্ষ্য ঠিক রাখলে", "মনোযোগ ধরে রাখলে", "নিয়মিত চেষ্টা করলে", "বিশ্বাস ধরে রাখলে", "ভুল থেকে শিখলে",
        "সকালে শুরু করলে", "দৃঢ় থাকলে", "শৃঙ্খলা মানলে", "নিজেকে গুছিয়ে নিলে", "হাল না ছাড়লে",
        "সমস্যাকে চ্যালেঞ্জ ভাবলে", "ভয়কে নিয়ন্ত্রণ করলে", "শুরুটা করে ফেললে", "অভ্যাস ঠিক করলে", "স্বপ্নে কাজ জুড়লে",
        "উদ্যম বজায় রাখলে", "চিন্তা পরিষ্কার রাখলে", "কথার চেয়ে কাজ বাড়ালে", "অগ্রাধিকার ঠিক করলে", "সাহস নিয়ে এগোলে"
    ]
    middles = [
        "সাফল্য একদিন দরজায় কড়া নাড়বেই", "ভাগ্যও পরিশ্রমীর পাশে দাঁড়ায়", "প্রতিদিনের অগ্রগতি বড় ফল আনে",
        "অসম্ভবও ধীরে ধীরে সম্ভব হয়", "কষ্টের পরেই স্বস্তি আসে", "ভালো ফল সময় নিয়ে আসে",
        "অন্ধকারের পরেই আলো আসে", "অভ্যাসই মানুষকে এগিয়ে দেয়", "চেষ্টা কখনো ব্যর্থ যায় না",
        "নিজের ওপর ভরসাই সবচেয়ে বড় শক্তি", "ধীর গতি হলেও পথ ঠিক থাকে", "পতনের ভেতরেই শেখা থাকে",
        "নিরবচ্ছিন্ন চেষ্টাই পার্থক্য গড়ে", "সময়মতো কাজই শান্তি দেয়", "সংগ্রামই চরিত্র গড়ে",
        "মাটিতে থাকা মানুষই উঁচুতে ওঠে", "ভুল মানা মানুষ দ্রুত শেখে", "সৎ পথে দেরি হলেও জয় আসে",
        "আজকের কষ্টই আগামীর সম্পদ", "এক ধাপ এগোলেই পথ ছোট হয়", "নীরব পরিশ্রম সবচেয়ে জোরে কথা বলে",
        "চাপের মাঝেই দক্ষতা তৈরি হয়", "আত্মবিশ্বাস থাকলে পথ বের হয়", "শুরু ছোট হলেও শেষ বড় হতে পারে",
        "যে থামে না, সে হারেও না"
    ]
    endings = [
        "তাই আজও এগিয়ে যাও", "তাই নিজের গতিতে চলতে থাকো", "তাই কাজটাই ধরে রাখো",
        "তাই মন খারাপ নয়, আবার শুরু করো", "তাই লক্ষ্য থেকে চোখ সরিও না", "তাই আজকের কাজ আজই শেষ করো",
        "তাই হাল না ছেড়ে সামনে তাকাও", "তাই তোমার সময় অবশ্যই আসবে", "তাই চেষ্টা চালিয়ে যাও",
        "তাই অল্প অল্প করে জিততে থাকো", "তাই নিজেকে আজই আরও ভালো করো", "তাই প্রতিদিন ১% উন্নতি করো",
        "তাই স্থির থাকো, ফল আসবেই", "তাই সংকল্প শক্ত রাখো", "তাই পরিশ্রমকে সঙ্গী বানাও",
        "তাই শৃঙ্খলাকেই শক্তি বানাও", "তাই বিশ্বাস রেখো, জয় হবে", "তাই কাজই তোমার পরিচয় হোক",
        "তাই নিজের যাত্রাকে সম্মান দাও", "তাই এগোনোর গল্পটা থামিও না"
    ]

    lines = []
    for a in starters:
        for b in middles:
            for c in endings:
                lines.append(f"{a}, {b} - {c}।")

    rng = random.Random(20260227)
    rng.shuffle(lines)
    return lines[:target_size]


BN_OTP_MOTIVATION_LINES = _build_bengali_proverb_pool(1000)


def get_random_bn_otp_motivation():
    if not BN_OTP_MOTIVATION_LINES:
        return "পরিশ্রমের ফল একদিন অবশ্যই আসে।"
    return random.choice(BN_OTP_MOTIVATION_LINES)

# Try to import cloudscraper for Cloudflare bypass
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

# Bot Configuration (from environment variables only - no default value)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required. Please set it in Render environment variables.")

BOT_CONFIG = {
    'poll_interval': 3,  # Seconds between OTP checks
}

ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "5742928021"))
OTP_CHANNEL_ID = int(os.getenv("OTP_CHANNEL_ID", "-1003403204287"))  # Channel ID for forwarding OTP messages

# API Configuration (from otp_tool.py)
BASE_URL = "https://stexsms.com"
API_EMAIL = os.getenv("API_EMAIL", "roni791158@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "53561106@Roni")
API_KEY = os.getenv("API_KEY", "MXS47FLFX0U")
BASE_API_URL = f"https://api.2oo9.cloud/{API_KEY}/tness"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sgnnqvfoajqsfdyulolm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNnbm5xdmZvYWpxc2ZkeXVsb2xtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNzE1MjcsImV4cCI6MjA3OTc0NzUyN30.dFniV0odaT-7bjs5iQVFQ-N23oqTGMAgQKjswhaHSP4")

# Supabase Database setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Service → appId mapping (known primary services)
SERVICE_APP_IDS = {
    "whatsapp": "WhatsApp",
    "facebook": "Facebook",
    "telegram": "Telegram",
}

def init_database():
    """Initialize Supabase database (tables should be created manually via SQL)"""
    try:
        # Test connection
        result = supabase.table('users').select('user_id').limit(1).execute()
        logger.info("pe('✅') Supabase connection successful")
    except Exception as e:
        logger.warning(f"⚠️ Supabase connection test failed (tables may not exist yet): {e}")

# Initialize database on import
init_database()

class BestEffortLock:
    """Non-blocking-ish lock to avoid freezing the event loop under contention."""
    def __init__(self, timeout=0.05):
        self._lock = threading.Lock()
        self._timeout = timeout
        self._acquired = False

    def __enter__(self):
        try:
            self._acquired = self._lock.acquire(timeout=self._timeout)
        except Exception:
            self._acquired = False
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._acquired:
            try:
                self._lock.release()
            except Exception:
                pass
        self._acquired = False
        return False

# Global locks for thread safety
db_lock = BestEffortLock(timeout=0.05)
user_jobs = {}  # Store latest monitoring job per user (older jobs may still run)
console_lock = threading.Lock()
console_bootstrapped = False
forwarded_console_ids = set()
forwarded_console_order = []
MAX_FORWARDED_CONSOLE_IDS = 5000
bot_username_cache = None
CONSOLE_MONITOR_INTERVAL = int(os.getenv("CONSOLE_MONITOR_INTERVAL", "3"))
CONSOLE_MAX_FORWARDS_PER_CYCLE = int(os.getenv("CONSOLE_MAX_FORWARDS_PER_CYCLE", "6"))
CONSOLE_CYCLE_BUDGET_SECONDS = float(os.getenv("CONSOLE_CYCLE_BUDGET_SECONDS", "2.2"))
# Console stream -> OTP channel forwarding is limited to these services for now.
CONSOLE_FORWARD_SERVICE_KEYS = {"whatsapp", "telegram"}

# Global API client - single session for all users
global_api_client = None
api_lock = threading.Lock()
API_IO_WORKERS = int(os.getenv("API_IO_WORKERS", "120"))
UPDATE_CONCURRENCY = int(os.getenv("UPDATE_CONCURRENCY", "128"))
api_io_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=max(16, API_IO_WORKERS),
    thread_name_prefix="api-io"
)

async def run_api_call(func, *args, **kwargs):
    """Run blocking API call in thread pool to keep event loop responsive."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(api_io_executor, partial(func, *args, **kwargs))

def get_global_api_client():
    """Get or create global API client (single session for all users)"""
    global global_api_client
    if global_api_client is None:
        global_api_client = APIClient()
        if not global_api_client.login():
            logger.error("Failed to login to API")
    return global_api_client

def refresh_global_token():
    """Refresh global API token if expired"""
    global global_api_client
    with api_lock:
        if global_api_client:
            if not global_api_client.login():
                logger.error("Failed to refresh API token")
                # Try to create new client
                global_api_client = APIClient()
                global_api_client.login()
        else:
            get_global_api_client()

# Helper for time parsing
def parse_time_ago(time_str):
    """Parse '7 mins ago', '1 hours ago' to minutes"""
    if not time_str:
        return 999999 # Treat missing as very old
        
    try:
        parts = str(time_str).lower().split()
        if len(parts) >= 2:
            val = int(parts[0])
            unit = parts[1]
            
            if 'sec' in unit:
                return val / 60
            elif 'min' in unit:
                return val
            elif 'hour' in unit:
                return val * 60
            elif 'day' in unit:
                return val * 1440
            elif 'week' in unit:
                return val * 10080
            elif 'month' in unit:
                return val * 43200
                
        return 999999
    except:
        return 999999

def get_user_status(user_id):
    """Get user approval status from database"""
    try:
        # Always approve admin
        if int(user_id) == ADMIN_USER_ID:
            return 'approved'
            
        with db_lock:
            # Use integer user_id (BIGINT in database)
            result = supabase.table('users').select('status').eq('user_id', int(user_id)).execute()
            if result.data and len(result.data) > 0:
                status = result.data[0].get('status')
                if status:
                    return status
        # Return 'pending' if user doesn't exist (not None)
        return 'pending'
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        # Return 'pending' on error to avoid approval loop
        return 'pending'

def add_user(user_id, username):
    """Add new user to database"""
    try:
        with db_lock:
            # Use integer user_id (BIGINT in database)
            supabase.table('users').upsert({
                'user_id': int(user_id),
                'username': username,
                'status': 'pending'
            }).execute()
    except Exception as e:
        logger.error(f"Error adding user: {e}")

def approve_user(user_id):
    """Approve user in database"""
    try:
        with db_lock:
            # Use integer user_id (BIGINT in database)
            supabase.table('users').update({
                'status': 'approved',
                'approved_at': datetime.now().isoformat()
            }).eq('user_id', int(user_id)).execute()
    except Exception as e:
        logger.error(f"Error approving user: {e}")

def reject_user(user_id):
    """Reject user in database"""
    try:
        with db_lock:
            # Use integer user_id (BIGINT in database)
            supabase.table('users').update({
                'status': 'rejected'
            }).eq('user_id', int(user_id)).execute()
    except Exception as e:
        logger.error(f"Error rejecting user: {e}")

def remove_user(user_id):
    """Remove user from database"""
    try:
        with db_lock:
            # Use integer user_id (BIGINT in database)
            supabase.table('users').delete().eq('user_id', int(user_id)).execute()
            supabase.table('user_sessions').delete().eq('user_id', int(user_id)).execute()
    except Exception as e:
        logger.error(f"Error removing user: {e}")

def get_pending_users():
    """Get list of pending users"""
    try:
        with db_lock:
            result = supabase.table('users').select('user_id, username').eq('status', 'pending').execute()
            return [(row['user_id'], row['username']) for row in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error getting pending users: {e}")
        return []

def get_all_users():
    """Get all users"""
    try:
        with db_lock:
            result = supabase.table('users').select('user_id, username, status').execute()
            return [(row['user_id'], row['username'], row['status']) for row in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []


def get_approved_user_ids():
    """Get list of approved user_ids."""
    try:
        with db_lock:
            result = supabase.table('users').select('user_id').eq('status', 'approved').execute()
            return [int(row['user_id']) for row in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error getting approved users: {e}")
        return []

def update_user_session(user_id, service=None, country=None, range_id=None, number=None, monitoring=0, number_count=None):
    """Update user session in database"""
    try:
        with db_lock:
            # Use integer user_id (BIGINT in database)
            data = {
                'user_id': int(user_id),
                'selected_service': service,
                'selected_country': country,
                'range_id': range_id,
                'number': number,
                'monitoring': monitoring,
                'last_check': datetime.now().isoformat()
            }
            # Only update number_count if provided
            if number_count is not None:
                data['number_count'] = number_count
            supabase.table('user_sessions').upsert(data).execute()
    except Exception as e:
        logger.error(f"Error updating user session: {e}")

def get_user_session(user_id):
    """Get user session from database"""
    try:
        with db_lock:
            # Use integer user_id (BIGINT in database)
            result = supabase.table('user_sessions').select('*').eq('user_id', int(user_id)).execute()
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return {
                    'user_id': row['user_id'],
                    'service': row.get('selected_service'),
                    'country': row.get('selected_country'),
                    'range_id': row.get('range_id'),
                    'number': row.get('number'),
                    'monitoring': row.get('monitoring', 0),
                    'number_count': row.get('number_count', 2)  # Default to 2 if not set
                }
        return {'number_count': 2}  # Return default if no session exists
    except Exception as e:
        logger.error(f"Error getting user session: {e}")
        return {'number_count': 2}  # Return default on error


def add_used_number(number):
    """Add a number to the used_numbers table to prevent reuse for 24 hours."""
    try:
        if not number:
            return
        # Normalize number (digits only for robust matching)
        normalized = ''.join(filter(str.isdigit, str(number)))
        if not normalized:
            return
            
        with db_lock:
            supabase.table('used_numbers').upsert({
                'number': normalized,
                'used_at': datetime.now(timezone.utc).isoformat()
            }).execute()
        logger.info(f"Number {normalized} added to used_numbers table.")
    except Exception as e:
        logger.error(f"Error adding used number {number}: {e}")


def is_number_used(number):
    """Check if a number has been used (received OTP) within the last 24 hours."""
    try:
        if not number:
            return False
        # Normalize number (digits only for robust matching)
        normalized = ''.join(filter(str.isdigit, str(number)))
        if not normalized:
            return False
            
        with db_lock:
            # Check for exact match
            result = supabase.table('used_numbers').select('*').eq('number', normalized).execute()
            if result.data and len(result.data) > 0:
                used_at_str = result.data[0].get('used_at')
                if used_at_str:
                    used_at = datetime.fromisoformat(used_at_str.replace('Z', '+00:00'))
                    # If used within last 24 hours
                    if datetime.now(timezone.utc) - used_at < timedelta(hours=24):
                        return True
        return False
    except Exception as e:
        logger.error(f"Error checking if number {number} is used: {e}")
        return False


def get_bd_today_str():
    """Return today's date string in Asia/Dhaka timezone (YYYY-MM-DD)."""
    # Asia/Dhaka is UTC+6 and has no DST currently
    bd_now = datetime.now(timezone.utc) + timedelta(hours=6)
    return bd_now.date().isoformat()


def get_bd_now():
    """Return current datetime in Asia/Dhaka timezone (UTC+6)."""
    # Using fixed offset to avoid extra deps (Asia/Dhaka has no DST currently)
    return datetime.now(timezone.utc) + timedelta(hours=6)


def increment_otp_count(user_id):
    """Increment today's OTP count for a user (per Bangladesh time)."""
    try:
        today_str = get_bd_today_str()
        with db_lock:
            result = supabase.table('user_sessions').select('otp_count, otp_date').eq('user_id', int(user_id)).execute()
            otp_count = 0
            otp_date = None
            if result.data and len(result.data) > 0:
                row = result.data[0]
                otp_count = row.get('otp_count', 0) or 0
                otp_date = row.get('otp_date')

            # Reset count if date changed
            if otp_date != today_str:
                new_count = 1
            else:
                new_count = otp_count + 1

            supabase.table('user_sessions').upsert({
                'user_id': int(user_id),
                'otp_count': new_count,
                'otp_date': today_str
            }).execute()
    except Exception as e:
        logger.error(f"Error incrementing OTP count for user {user_id}: {e}")


def get_today_otp_count(user_id):
    """Get how many OTPs user received today (per Bangladesh time)."""
    try:
        today_str = get_bd_today_str()
        with db_lock:
            result = supabase.table('user_sessions').select('otp_count, otp_date').eq('user_id', int(user_id)).execute()
            if result.data and len(result.data) > 0:
                row = result.data[0]
                otp_count = row.get('otp_count', 0) or 0
                otp_date = row.get('otp_date')
                if otp_date == today_str:
                    return otp_count
        return 0
    except Exception as e:
        logger.error(f"Error getting OTP stats for user {user_id}: {e}")
        return 0


def resolve_app_id(service_name, context):
    """Resolve app_id from known services or per-user custom services."""
    if service_name in SERVICE_APP_IDS:
        return SERVICE_APP_IDS[service_name]
    custom_services = context.user_data.get('custom_services', {}) if context else {}
    return custom_services.get(service_name) or service_name

# API Functions (from otp_tool.py)
class APIClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.base_api_url = BASE_API_URL
        # Use curl_cffi if available (best for Cloudflare bypass)
        if HAS_CURL_CFFI:
            self.session = curl_requests.Session(impersonate="chrome110")
            self.use_curl = True
            logger.info("Using curl_cffi for Cloudflare bypass")
        elif HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper()
            self.use_curl = False
            logger.info("Using cloudscraper for Cloudflare bypass")
        else:
            self.session = requests.Session()
            self.use_curl = False
            logger.warning("No Cloudflare bypass available, using standard requests")
        self.auth_token = None
        self.email = API_EMAIL
        self.password = API_PASSWORD
        # Browser-like headers to avoid session expiration and Cloudflare - EXACT same as otp_tool.py
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/dashboard/getnum",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty"
        }
        self._ranges_cache = {}  # Cache structure: {app_id: {'timestamp': time.time(), 'data': [...]}}
        self._cache_duration = int(os.getenv("RANGES_CACHE_SECONDS", "30"))
        
        # Internal lock for thread safety (login/token refresh)
        self._lock = threading.Lock()

        # Load bootstrap ranges
        self.bootstrap_ranges = []
        try:
            dir_path = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(dir_path, "har_ranges.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    self.bootstrap_ranges = json.load(f)
                logger.info(f"Loaded {len(self.bootstrap_ranges)} bootstrap ranges from har_ranges.json")
        except Exception as e:
            logger.error(f"Failed to load bootstrap ranges: {e}")


    def _get_decrypt_key(self):
        """Extract the sid from JWT token to use as AES key, or return fallback key."""
        if not self.auth_token:
            return "M0000000001"
        try:
            parts = self.auth_token.split('.')
            if len(parts) >= 2:
                import base64
                import json
                payload_b64 = parts[1]
                payload_b64 += '=' * (-len(payload_b64) % 4)
                payload_bytes = base64.urlsafe_b64decode(payload_b64)
                payload_dict = json.loads(payload_bytes.decode('utf-8'))
                sid = payload_dict.get("sid")
                if sid:
                    return sid
        except Exception as e:
            logger.error(f"Error extracting sid from token: {e}")
        return "M0000000001"
    
    def login(self):
        """Login to API - Thread-safe"""
        with self._lock:
            try:
                login_headers = {
                    **self.browser_headers,
                    "Content-Type": "text/plain; charset=utf-8",
                    "Referer": f"{self.base_url}/"
                }
                login_url = f"{self.base_api_url}/@auth/login"
                
                logger.info(f"Attempting login to {login_url}")
                payload = {"email": self.email, "password": self.password}
                
                encrypted_payload = codec.encrypt(payload, "M0000000001")
                
                login_resp = self.session.post(
                    login_url,
                    data=encrypted_payload,
                    headers=login_headers,
                    timeout=15
                )
                
                if login_resp.status_code in [200, 201]:
                    decrypted_text = codec.decrypt(login_resp.text.strip(), "M0000000001")
                    login_data = decrypted_text if isinstance(decrypted_text, dict) else json.loads(decrypted_text)
                    
                    token = None
                    if 'data' in login_data and 'session_token' in login_data['data']:
                        token = login_data['data']['session_token']
                    elif 'token' in login_data:
                        token = login_data['token']
                    elif 'session_token' in login_data:
                        token = login_data['session_token']
                    
                    if token:
                        self.auth_token = token
                        self.session.headers.update({"mauth": self.auth_token})
                        logger.info("Login successful")
                        return True
                    else:
                        logger.error(f"Login response missing token: {login_data}")
                else:
                    logger.error(f"Login failed with status {login_resp.status_code}: {login_resp.text[:200]}")
                return False
            except Exception as e:
                logger.error(f"Login error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return False
    
    def _normalize_country(self, raw_country, range_token="", number_token=""):
        """Prefer explicit country; fallback to number/range based detection."""
        country = str(raw_country or "").strip()
        generic_labels = {"unknown", "other", "postpaid", "prepaid"}
        if country and country.lower() not in generic_labels:
            return country

        detected = (
            detect_country_from_range(range_token)
            or detect_country_from_number(number_token)
            or detect_country_from_range(number_token)
        )
        return detected or "Unknown"

    def _build_ranges_from_console_logs(self, logs):
        """
        Build deduplicated range objects from console stream.
        This replaces old /mdashboard/access scraping.
        """
        # Convert bootstrap ranges to log item format
        bootstrap_logs = []
        if hasattr(self, 'bootstrap_ranges') and self.bootstrap_ranges:
            for b_idx, b_item in enumerate(self.bootstrap_ranges):
                bootstrap_logs.append({
                    "id": f"b_{b_idx}",
                    "time": "12:00:00",
                    "carrier": b_item.get("carrier", "Unknown"),
                    "operator": b_item.get("operator", "Unknown"),
                    "app_name": b_item.get("app_name", "Unknown"),
                    "sms": "",
                    "range": b_item.get("range", ""),
                    "country": b_item.get("country", "Unknown")
                })
        
        combined_logs = []
        if isinstance(logs, list):
            combined_logs.extend(logs)
        combined_logs.extend(bootstrap_logs)

        if not combined_logs:
            return []

        primary_services = {"whatsapp", "facebook", "telegram"}
        primary_labels = {
            "whatsapp": "WhatsApp",
            "facebook": "Facebook",
            "telegram": "Telegram",
        }

        range_map = {}

        for idx, item in enumerate(combined_logs):
            if not isinstance(item, dict):
                continue

            app_name_raw = str(item.get('app_name') or "").strip()
            if not app_name_raw:
                continue

            service_key = normalize_service_name(app_name_raw)
            service_label = primary_labels.get(service_key, app_name_raw)

            # Prioritize carrier as the most accurate base for ranges from this API
            raw_carrier = normalize_range_token(item.get('carrier'))
            raw_range = normalize_range_token(item.get('range'))
            raw_number = normalize_range_token(item.get('number'))

            if raw_carrier and raw_carrier.isdigit() and len(raw_carrier) >= 4:
                range_token = f"{raw_carrier}XXX"
            else:
                range_token = raw_range or raw_number
                if range_token and range_token.isdigit() and len(range_token) >= 7:
                    # If it's a full phone number, truncate last 3 digits to make it a range
                    range_token = f"{range_token[:-3]}XXX"

            if not range_token:
                continue

            # The new API might fail with 500 if XXX is missing. Ensure it has XXX suffix.
            range_for_api = range_token
            if range_for_api.isdigit() and not range_for_api.endswith('XXX'):
                range_for_api = f"{range_for_api}XXX"

            # Ignore clearly invalid short prefixes.
            if len(re.sub(r'[^0-9]', '', range_for_api)) < 4:
                continue

            country = self._normalize_country(item.get('country'), range_for_api, raw_number)
            carrier = str(item.get('carrier') or "Unknown").strip() or "Unknown"
            log_id = item.get('id')

            # Existing UI sort expects "X mins ago" style text.
            datetime_label = f"{idx} mins ago"

            obj = {
                'id': range_for_api,
                'numerical_id': str(log_id) if log_id is not None else "",
                'range_id': range_for_api,
                'name': range_for_api,
                'pattern': range_for_api,
                'country': country,
                'cantryName': country,
                'operator': carrier,
                'service': service_label,
                'datetime': datetime_label,
            }

            # Keep newest occurrence per (service, range).
            map_key = (service_label.lower(), range_for_api)
            if map_key not in range_map:
                range_map[map_key] = obj
            else:
                existing = range_map[map_key]
                if existing.get('country') in {"Unknown", "Other", "postpaid", "prepaid"} and country not in {"Unknown", "Other", "postpaid", "prepaid"}:
                    range_map[map_key] = obj

        # Keep deterministic ordering by freshness first.
        ranges = list(range_map.values())
        ranges.sort(key=lambda x: parse_time_ago(x.get('datetime', '')))

        # Drop exact duplicate range IDs to keep UI cleaner.
        seen_ids = set()
        unique_ranges = []
        for r in ranges:
            rid = str(r.get('range_id') or r.get('name') or "")
            sid = str(r.get('service') or "").lower()
            dedupe_key = (sid, rid)
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            unique_ranges.append(r)

        # Filter out blank service rows from "others" view stability perspective.
        return [r for r in unique_ranges if str(r.get('service') or "").strip()]

    def get_ranges(self, app_id, max_retries=3, keyword=""):
        """Get ranges using new getnum-era console stream metadata."""
        try:
            if not self.auth_token:
                if not self.login():
                    return []

            app_id_norm = str(app_id or "").strip().lower()
            cache_key = f"ranges_console::{app_id_norm}"
            now_ts = time.time()

            if cache_key in self._ranges_cache:
                entry = self._ranges_cache[cache_key]
                if now_ts - entry['timestamp'] < self._cache_duration:
                    return entry['data']

            logs = self.get_console_logs()
            all_ranges = self._build_ranges_from_console_logs(logs)
            if not all_ranges:
                logger.warning(f"No ranges available from console source for app_id={app_id}")
                self._ranges_cache[cache_key] = {'timestamp': now_ts, 'data': []}
                return []

            primary_services = {"whatsapp", "facebook", "telegram"}
            filtered = []

            for r in all_ranges:
                service_label = str(r.get('service') or "").strip()
                if not service_label:
                    continue

                service_norm = normalize_service_name(service_label)
                service_lower = service_label.lower()

                if app_id_norm in primary_services:
                    if service_norm == app_id_norm:
                        filtered.append(r)
                elif app_id_norm == "others":
                    if service_norm not in primary_services:
                        filtered.append(r)
                else:
                    if app_id_norm in service_lower or service_lower in app_id_norm:
                        filtered.append(r)

            self._ranges_cache[cache_key] = {'timestamp': now_ts, 'data': filtered}
            logger.info(f"Found {len(filtered)} ranges for {app_id} from new console source")
            return filtered

        except Exception as e:
            logger.error(f"Error getting ranges: {e}")
            return []

    def get_applications(self, max_retries=3):
        """Get available applications - Mapped from SERVICE_APP_IDS for compatibility"""
        apps = []
        for name, app_id in SERVICE_APP_IDS.items():
            apps.append({'id': app_id, 'name': app_id})
        return apps
    
    def get_number(self, range_id):
        """Request a number from a range"""
        try:
            if not self.auth_token:
                if not self.login():
                    return None

            normalized = normalize_range_token(range_id)
            if not normalized:
                return None

            candidates = []
            
            # Always try exactly what was provided first
            candidates.append(normalized)
            
            # Try variants based on 'X' presence
            if 'X' in normalized:
                no_x = normalized.replace('X', '')
                if no_x:
                    candidates.append(no_x)
            else:
                candidates.append(f"{normalized}XXX")

            # Keep order and remove duplicates.
            dedup_candidates = []
            seen = set()
            for c in candidates:
                if c not in seen:
                    seen.add(c)
                    dedup_candidates.append(c)

            for candidate_range in dedup_candidates:
                headers = {
                    **self.browser_headers,
                    "mauth": self.auth_token,
                    "Content-Type": "text/plain; charset=utf-8",
                    "Referer": f"{self.base_url}/"
                }

                payload = {
                    "range": candidate_range,
                    "is_national": False,
                    "remove_plus": False
                }

                logger.info(f"DEBUG getnum request: payload={payload}")

                key = self._get_decrypt_key()
                encrypted_payload = codec.encrypt(payload, key)

                url = f"{self.base_api_url}/@dashboard/dialer/getnum/request"
                resp = self.session.post(
                    url,
                    data=encrypted_payload,
                    headers=headers,
                    timeout=15
                )

                logger.info(f"DEBUG getnum response status: {resp.status_code}")

                if resp.status_code in [401, 403]:
                    self.auth_token = None
                    if self.login():
                        headers["mauth"] = self.auth_token
                        key = self._get_decrypt_key()
                        encrypted_payload = codec.encrypt(payload, key)
                        resp = self.session.post(
                            url,
                            data=encrypted_payload,
                            headers=headers,
                            timeout=15
                        )

                if resp.status_code == 200:
                    decrypted_text = codec.decrypt(resp.text.strip(), key)
                    logger.info(f"DEBUG getnum decrypted response: {str(decrypted_text)[:500]}")
                    data = decrypted_text if isinstance(decrypted_text, dict) else json.loads(decrypted_text)
                    if 'data' in data:
                        number_data = data['data']
                        if isinstance(number_data, dict):
                            if 'number' in number_data:
                                return number_data
                            if 'copy' in number_data:
                                number_data['number'] = number_data['copy']
                                return number_data
                    else:
                        logger.warning(f"DEBUG NO DATA FIELD: {data}")
                else:
                    err_msg = resp.text[:500]
                    try:
                        dec_err = codec.decrypt(resp.text.strip(), key)
                        err_msg = f"Decrypted: {str(dec_err)}"
                    except:
                        pass
                    logger.warning(f"DEBUG NOT 200: Status={resp.status_code}, Msg={err_msg}")

            logger.warning(f"get_number failed for range={range_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting number: {e}")
            return None
    
    def get_multiple_numbers(self, range_id, range_name=None, count=2, max_retries=10):
        """Request multiple numbers from a range - with filtering and dual range_id/range_name logic."""
        numbers = []
        total_attempts = 0
        max_total_attempts = count * 10  # Safety limit
        
        logger.info(f"Requesting {count} numbers from range {range_id} (name: {range_name})")
        
        while len(numbers) < count and total_attempts < max_total_attempts:
            total_attempts += 1
            try:
                # Try range_name first (this is the pattern like "9965579XXX")
                number_data = None
                if range_name:
                    logger.info(f"Attempting with range_name (pattern): {range_name}")
                    number_data = self.get_number(range_name)
                
                # Fallback to range_id only if range_name fails and they're different
                if not number_data and range_id != range_name:
                    logger.info(f"Fallback: attempting with range_id: {range_id}")
                    number_data = self.get_number(range_id)
                    
                if number_data:
                    num_val = number_data.get('number') or number_data.get('num')
                    if num_val:
                        # Check if number was used in last 24 hours
                        if not is_number_used(num_val):
                            numbers.append(number_data)
                            logger.info(f"Added fresh number: {num_val}")
                        else:
                            logger.info(f"Skipping recently used number: {num_val}")
                    else:
                        logger.warning(f"get_number returned data without number field: {number_data}")
                else:
                    # No more numbers available from API or temporary error
                    logger.warning(f"get_number returned None for range {range_id} (attempt {total_attempts})")
                    # If we already have some numbers, maybe return what we have after a few more tries
                    if len(numbers) > 0 and total_attempts > count + 2:
                        break
                    time.sleep(1)
            except Exception as e:
                logger.error(f"Error in get_multiple_numbers loop: {e}")
                time.sleep(1)
        
        if not numbers:
            logger.error(f"pe('❌') Failed to get any valid numbers from range {range_id} after {total_attempts} attempts.")
        else:
            logger.info(f"pe('✅') Successfully obtained {len(numbers)}/{count} numbers for range {range_id}.")
            
        return numbers
    
    def check_otp(self, number):
        """Check for OTP on a number - using NEW API /@dashboard/dialer/getnum/list"""
        try:
            if not self.auth_token:
                if not self.login():
                    return None
            
            headers = {
                **self.browser_headers,
                "mauth": self.auth_token,
                "Referer": f"{self.base_url}/"
            }
            
            url = f"{self.base_api_url}/@dashboard/dialer/getnum/list?page=1"
            resp = self.session.get(
                url,
                headers=headers,
                timeout=8
            )
            
            if resp.status_code == 401:
                logger.info("Token expired in check_otp, refreshing...")
                if self.login():
                    headers["mauth"] = self.auth_token
                    resp = self.session.get(
                        url,
                        headers=headers,
                        timeout=8
                    )
                else:
                    return None
            
            if resp.status_code == 200:
                key = self._get_decrypt_key()
                decrypted_text = codec.decrypt(resp.text.strip(), key)
                data = decrypted_text if isinstance(decrypted_text, dict) else json.loads(decrypted_text)
                if 'data' in data and data['data']:
                    numbers_list = data['data'].get('numbers', [])
                    if numbers_list:
                        target_normalized = number.replace('+', '').replace(' ', '').strip()
                        
                        for num_obj in numbers_list:
                            api_num = num_obj.get('number', '').replace('+', '').strip()
                            if api_num == target_normalized or (len(api_num) >= 9 and len(target_normalized) >= 9 and api_num[-9:] == target_normalized[-9:]):
                                msg = num_obj.get('message') or num_obj.get('otp', '')
                                if msg:
                                    num_obj['sms_content'] = msg
                                    num_obj['otp'] = None  # Clear to force extraction
                                    return num_obj
                                else:
                                    return num_obj 
            return None
        except Exception as e:
            logger.error(f"Error checking OTP: {e}")
            return None
    
    def check_otp_batch(self, numbers):
        """Check OTP for multiple numbers - using NEW API"""
        try:
            if not self.auth_token:
                if not self.login():
                    return {}
            
            headers = {
                **self.browser_headers,
                "mauth": self.auth_token,
                "Referer": f"{self.base_url}/"
            }
            
            url = f"{self.base_api_url}/@dashboard/dialer/getnum/list?page=1"
            resp = self.session.get(
                url,
                headers=headers,
                timeout=8
            )
            
            if resp.status_code == 401:
                if self.login():
                    headers["mauth"] = self.auth_token
                    resp = self.session.get(
                        url,
                        headers=headers,
                        timeout=8
                    )
                else:
                    return {}

            result = {}
            if resp.status_code == 200:
                key = self._get_decrypt_key()
                decrypted_text = codec.decrypt(resp.text.strip(), key)
                data = decrypted_text if isinstance(decrypted_text, dict) else json.loads(decrypted_text)
                if 'data' in data and data['data']:
                    numbers_list = data['data'].get('numbers', [])
                    if numbers_list:
                        target_map_exact = {n.replace('+', '').replace(' ', '').strip(): n for n in numbers}
                        target_map_last9 = {n.replace('+', '').replace(' ', '').strip()[-9:]: n for n in numbers if len(n.replace('+', '').replace(' ', '').strip()) >= 9}
                        
                        for num_obj in numbers_list:
                            api_num = num_obj.get('number', '').replace('+', '').strip()
                            
                            msg = num_obj.get('message') or num_obj.get('otp', '')
                            if msg:
                                num_obj['sms_content'] = msg
                                num_obj['otp'] = None

                            if api_num in target_map_exact:
                                origin = target_map_exact[api_num]
                                result[origin] = num_obj
                            elif len(api_num) >= 9 and api_num[-9:] in target_map_last9:
                                origin = target_map_last9[api_num[-9:]]
                                result[origin] = num_obj

            return result
        except Exception as e:
            logger.error(f"Error checking OTP batch: {e}")
            return {}

    def get_console_logs(self):
        """Get latest masked OTP logs from console endpoint."""
        try:
            if not self.auth_token:
                if not self.login():
                    return []

            headers = {
                **self.browser_headers,
                "mauth": self.auth_token,
                "Referer": f"{self.base_url}/"
            }

            url = f"{self.base_api_url}/@dashboard/dialer/console/info"
            resp = self.session.get(url, headers=headers, timeout=10)

            if resp.status_code in [401, 403]:
                logger.info("Token expired in get_console_logs, refreshing...")
                if self.login():
                    headers["mauth"] = self.auth_token
                    resp = self.session.get(url, headers=headers, timeout=10)
                else:
                    return []

            if resp.status_code != 200:
                logger.warning(f"get_console_logs failed: status={resp.status_code} body={resp.text[:200]}")
                return []

            key = self._get_decrypt_key()
            decrypted_text = codec.decrypt(resp.text.strip(), key)
            payload = decrypted_text if isinstance(decrypted_text, dict) else json.loads(decrypted_text)
            
            data = payload.get("data", {}) if isinstance(payload, dict) else {}
            logs = data.get("logs", []) if isinstance(data, dict) else []
            
            if isinstance(logs, list):
                for item in logs:
                    if isinstance(item, dict):
                        app_name = item.get('app_name')
                        if app_name and str(app_name).strip() == '******':
                            item['app_name'] = 'WhatsApp'
            
            return logs if isinstance(logs, list) else []
        except Exception as e:
            logger.error(f"Error getting console logs: {e}")
            return []

# Global API client - single session for all users
global_api_client = None
api_lock = threading.Lock()

def get_global_api_client():
    """Get or create global API client (single session for all users)"""
    global global_api_client
    if global_api_client is None:
        global_api_client = APIClient()
        # Try to login, but don't fail if it doesn't work - will retry on first API call
        if not global_api_client.login():
            logger.warning("Initial login failed, will retry on first API call")
    return global_api_client

def refresh_global_token():
    """Refresh global API token if expired"""
    global global_api_client
    with api_lock:
        if global_api_client:
            if not global_api_client.login():
                logger.error("Failed to refresh API token")
                # Try to create new client
                global_api_client = APIClient()
                global_api_client.login()
        else:
            get_global_api_client()

# Comprehensive Country calling codes mapping (199+ countries)
COUNTRY_CODES = {
    # 3-digit codes (check first - most specific)
    '264': 'Namibia', '265': 'Malawi', '266': 'Lesotho', '267': 'Botswana',
    '268': 'Swaziland', '269': 'Comoros', '290': 'Saint Helena', '291': 'Eritrea',
    '297': 'Aruba', '298': 'Faroe Islands', '299': 'Greenland', '350': 'Gibraltar',
    '351': 'Portugal', '352': 'Luxembourg', '353': 'Ireland', '354': 'Iceland',
    '355': 'Albania', '356': 'Malta', '357': 'Cyprus', '358': 'Finland',
    '359': 'Bulgaria', '370': 'Lithuania', '371': 'Latvia', '372': 'Estonia',
    '373': 'Moldova', '374': 'Armenia', '375': 'Belarus', '376': 'Andorra',
    '377': 'Monaco', '378': 'San Marino', '380': 'Ukraine', '381': 'Serbia',
    '382': 'Montenegro', '383': 'Kosovo', '385': 'Croatia', '386': 'Slovenia',
    '387': 'Bosnia', '389': 'Macedonia', '420': 'Czech Republic', '421': 'Slovakia',
    '423': 'Liechtenstein', '500': 'Falkland Islands', '501': 'Belize', '502': 'Guatemala',
    '503': 'El Salvador', '504': 'Honduras', '505': 'Nicaragua', '506': 'Costa Rica',
    '507': 'Panama', '508': 'Saint Pierre', '509': 'Haiti', '590': 'Guadeloupe',
    '591': 'Bolivia', '592': 'Guyana', '593': 'Ecuador', '594': 'French Guiana',
    '595': 'Paraguay', '596': 'Martinique', '597': 'Suriname', '598': 'Uruguay',
    '599': 'Netherlands Antilles', '670': 'East Timor', '672': 'Antarctica', '673': 'Brunei',
    '674': 'Nauru', '675': 'Papua New Guinea', '676': 'Tonga', '677': 'Solomon Islands',
    '678': 'Vanuatu', '679': 'Fiji', '680': 'Palau', '681': 'Wallis',
    '682': 'Cook Islands', '683': 'Niue', '685': 'Samoa', '686': 'Kiribati',
    '687': 'New Caledonia', '688': 'Tuvalu', '689': 'French Polynesia', '850': 'North Korea',
    '852': 'Hong Kong', '853': 'Macau', '855': 'Cambodia', '856': 'Laos',
    '880': 'Bangladesh', '886': 'Taiwan', '960': 'Maldives', '961': 'Lebanon',
    '962': 'Jordan', '963': 'Syria', '964': 'Iraq', '965': 'Kuwait',
    '966': 'Saudi Arabia', '967': 'Yemen', '968': 'Oman', '970': 'Palestine',
    '971': 'UAE', '972': 'Israel', '973': 'Bahrain', '974': 'Qatar',
    '975': 'Bhutan', '976': 'Mongolia', '977': 'Nepal', '992': 'Tajikistan',
    '993': 'Turkmenistan', '994': 'Azerbaijan', '995': 'Georgia', '996': 'Kyrgyzstan',
    '998': 'Uzbekistan', '240': 'Equatorial Guinea', '241': 'Gabon', '242': 'Congo',
    '243': 'DR Congo', '244': 'Angola', '245': 'Guinea-Bissau', '246': 'Diego Garcia',
    '247': 'Ascension', '248': 'Seychelles', '249': 'Sudan', '250': 'Rwanda',
    '251': 'Ethiopia', '252': 'Somalia', '253': 'Djibouti', '254': 'Kenya',
    '255': 'Tanzania', '256': 'Uganda', '257': 'Burundi', '258': 'Mozambique',
    '260': 'Zambia', '261': 'Madagascar', '262': 'Reunion', '263': 'Zimbabwe',
    '212': 'Morocco', '213': 'Algeria', '216': 'Tunisia', '218': 'Libya',
    '220': 'Gambia', '221': 'Senegal', '222': 'Mauritania', '223': 'Mali',
    '224': 'Guinea', '225': 'Ivory Coast', '226': 'Burkina Faso', '227': 'Niger',
    '228': 'Togo', '229': 'Benin', '230': 'Mauritius', '231': 'Liberia',
    '232': 'Sierra Leone', '233': 'Ghana',
    # Missing African codes (common)
    '234': 'Nigeria', '235': 'Chad', '236': 'Central African Republic', '237': 'Cameroon',
    '238': 'Cape Verde', '239': 'Sao Tome and Principe',
    # 2-digit codes
    '20': 'Egypt', '27': 'South Africa', '30': 'Greece', '31': 'Netherlands',
    '32': 'Belgium', '33': 'France', '34': 'Spain', '36': 'Hungary',
    '39': 'Italy', '40': 'Romania', '41': 'Switzerland', '43': 'Austria',
    '44': 'UK', '45': 'Denmark', '46': 'Sweden', '47': 'Norway',
    '48': 'Poland', '49': 'Germany', '51': 'Peru', '52': 'Mexico',
    '53': 'Cuba', '54': 'Argentina', '55': 'Brazil', '56': 'Chile',
    '57': 'Colombia', '58': 'Venezuela', '60': 'Malaysia', '61': 'Australia',
    '62': 'Indonesia', '63': 'Philippines', '64': 'New Zealand', '65': 'Singapore',
    '66': 'Thailand', '81': 'Japan', '82': 'South Korea', '84': 'Vietnam',
    '86': 'China', '90': 'Turkey', '91': 'India', '92': 'Pakistan',
    '93': 'Afghanistan', '94': 'Sri Lanka', '95': 'Myanmar', '98': 'Iran',
    # 1-digit codes (check last - least specific)
    '1': 'USA', '7': 'Russia'
}

# Comprehensive Country flags mapping (all countries)
COUNTRY_FLAGS = {
    'Angola': pe('🇦🇴'), 'Afghanistan': pe('🇦🇫'), 'Albania': pe('🇦🇱'), 'Algeria': pe('🇩🇿'),
    'Andorra': pe('🇦🇩'), 'Argentina': pe('🇦🇷'), 'Armenia': pe('🇦🇲'), 'Aruba': '🇦🇼',
    'Australia': pe('🇦🇺'), 'Austria': pe('🇦🇹'), 'Azerbaijan': pe('🇦🇿'), 'Bahrain': pe('🇧🇭'),
    'Bangladesh': pe('🇧🇩'), 'Belarus': pe('🇧🇾'), 'Belgium': pe('🇧🇪'), 'Belize': pe('🇧🇿'),
    'Benin': pe('🇧🇯'), 'Bhutan': pe('🇧🇹'), 'Bolivia': pe('🇧🇴'), 'Bosnia': pe('🇧🇦'),
    'Botswana': pe('🇧🇼'), 'Brazil': pe('🇧🇷'), 'Brunei': pe('🇧🇳'), 'Bulgaria': pe('🇧🇬'),
    'Burkina Faso': pe('🇧🇫'), 'Burundi': pe('🇧🇮'), 'Cameroon': pe('🇨🇲'), 'Cambodia': pe('🇰🇭'), 'Canada': pe('🇨🇦'),
    'Chile': pe('🇨🇱'), 'China': pe('🇨🇳'), 'Colombia': pe('🇨🇴'), 'Congo': pe('🇨🇬'),
    'Costa Rica': pe('🇨🇷'), 'Croatia': pe('🇭🇷'), 'Cuba': '🇨🇺', 'Cyprus': pe('🇨🇾'),
    'Central African Republic': pe('🇨🇫'), 'Chad': pe('🇹🇩'), 'Nigeria': pe('🇳🇬'), 'Cape Verde': pe('🇨🇻'), 'Sao Tome and Principe': pe('🇸🇹'),
    'Czech Republic': pe('🇨🇿'), 'DR Congo': pe('🇨🇩'), 'Denmark': pe('🇩🇰'), 'Djibouti': pe('🇩🇯'),
    'Ecuador': pe('🇪🇨'), 'Egypt': pe('🇪🇬'), 'El Salvador': '🇸🇻', 'Equatorial Guinea': pe('🇬🇶'),
    'Eritrea': '🇪🇷', 'Estonia': pe('🇪🇪'), 'Ethiopia': pe('🇪🇹'), 'Fiji': pe('🇫🇯'),
    'Finland': pe('🇫🇮'), 'France': pe('🇫🇷'), 'French Guiana': '🇬🇫', 'Gabon': pe('🇬🇦'),
    'Gambia': pe('🇬🇲'), 'Georgia': pe('🇬🇪'), 'Germany': pe('🇩🇪'), 'Ghana': pe('🇬🇭'),
    'Gibraltar': '🇬🇮', 'Greece': pe('🇬🇷'), 'Greenland': '🇬🇱', 'Guadeloupe': '🇬🇵',
    'Guatemala': pe('🇬🇹'), 'Guinea': pe('🇬🇳'), 'Guinea-Bissau': pe('🇬🇼'), 'Guyana': pe('🇬🇾'),
    'Haiti': pe('🇭🇹'), 'Honduras': pe('🇭🇳'), 'Hong Kong': '🇭🇰', 'Hungary': pe('🇭🇺'),
    'Iceland': pe('🇮🇸'), 'India': pe('🇮🇳'), 'Indonesia': pe('🇮🇩'), 'Iran': pe('🇮🇷'),
    'Iraq': pe('🇮🇶'), 'Ireland': pe('🇮🇪'), 'Israel': pe('🇮🇱'), 'Italy': pe('🇮🇹'),
    'Ivory Coast': '🇨🇮', 'Japan': pe('🇯🇵'), 'Jordan': pe('🇯🇴'), 'Kenya': pe('🇰🇪'),
    'Kiribati': pe('🇰🇮'), 'Kosovo': pe('🇽🇰'), 'Kuwait': pe('🇰🇼'), 'Kyrgyzstan': pe('🇰🇬'),
    'Laos': pe('🇱🇦'), 'Latvia': pe('🇱🇻'), 'Lebanon': pe('🇱🇧'), 'Lesotho': pe('🇱🇸'),
    'Liberia': pe('🇱🇷'), 'Libya': pe('🇱🇾'), 'Liechtenstein': '🇱🇮', 'Lithuania': pe('🇱🇹'),
    'Luxembourg': pe('🇱🇺'), 'Macau': '🇲🇴', 'Macedonia': pe('🇲🇰'), 'Madagascar': pe('🇲🇬'),
    'Malawi': '🇲🇼', 'Malaysia': pe('🇲🇾'), 'Maldives': pe('🇲🇻'), 'Mali': pe('🇲🇱'),
    'Malta': pe('🇲🇹'), 'Martinique': pe('🇲🇶'), 'Mauritania': '🇲🇷', 'Mauritius': pe('🇲🇺'),
    'Mexico': pe('🇲🇽'), 'Moldova': pe('🇲🇩'), 'Monaco': pe('🇲🇨'), 'Mongolia': pe('🇲🇳'),
    'Montenegro': pe('🇲🇪'), 'Morocco': pe('🇲🇦'), 'Mozambique': pe('🇲🇿'), 'Myanmar': '🇲🇲',
    'Namibia': pe('🇳🇦'), 'Nauru': '🇳🇷', 'Nepal': pe('🇳🇵'), 'Netherlands': pe('🇳🇱'),
    'New Caledonia': '🇳🇨', 'New Zealand': pe('🇳🇿'), 'Nicaragua': '🇳🇮', 'Niger': pe('🇳🇪'),
    'Nigeria': pe('🇳🇬'), 'North Korea': '🇰🇵', 'Norway': pe('🇳🇴'), 'Oman': pe('🇴🇲'),
    'Pakistan': pe('🇵🇰'), 'Palau': '🇵🇼', 'Palestine': pe('🇵🇸'), 'Panama': pe('🇵🇦'),
    'Papua New Guinea': pe('🇵🇬'), 'Paraguay': pe('🇵🇾'), 'Peru': pe('🇵🇪'), 'Philippines': pe('🇵🇭'),
    'Poland': pe('🇵🇱'), 'Portugal': pe('🇵🇹'), 'Qatar': pe('🇶🇦'), 'Reunion': '🇷🇪',
    'Romania': pe('🇷🇴'), 'Russia': pe('🇷🇺'), 'Rwanda': pe('🇷🇼'), 'Saudi Arabia': pe('🇸🇦'),
    'Senegal': pe('🇸🇳'), 'Serbia': pe('🇷🇸'), 'Seychelles': pe('🇸🇨'), 'Sierra Leone': pe('🇸🇱'),
    'Singapore': pe('🇸🇬'), 'Slovakia': pe('🇸🇰'), 'Slovenia': pe('🇸🇮'), 'Solomon Islands': pe('🇸🇧'),
    'Somalia': pe('🇸🇴'), 'South Africa': pe('🇿🇦'), 'South Korea': pe('🇰🇷'), 'Spain': pe('🇪🇸'),
    'Sri Lanka': pe('🇱🇰'), 'Sudan': pe('🇸🇩'), 'Suriname': pe('🇸🇷'), 'Swaziland': pe('🇸🇿'),
    'Sweden': pe('🇸🇪'), 'Switzerland': pe('🇨🇭'), 'Syria': '🇸🇾', 'Taiwan': '🇹🇼',
    'Tajikistan': pe('🇹🇯'), 'Tanzania': pe('🇹🇿'), 'Thailand': pe('🇹🇭'), 'Togo': pe('🇹🇬'),
    'Tonga': '🇹🇴', 'Tunisia': pe('🇹🇳'), 'Turkey': pe('🇹🇷'), 'Turkmenistan': pe('🇹🇲'),
    'Tuvalu': '🇹🇻', 'UAE': pe('🇦🇪'), 'Uganda': pe('🇺🇬'), 'UK': pe('🇬🇧'),
    'Ukraine': pe('🇺🇦'), 'Uruguay': pe('🇺🇾'), 'USA': pe('🇺🇸'), 'Uzbekistan': pe('🇺🇿'),
    'Vanuatu': pe('🇻🇺'), 'Venezuela': '🇻🇪', 'Vietnam': pe('🇻🇳'), 'Yemen': pe('🇾🇪'),
    'Zambia': pe('🇿🇲'), 'Zimbabwe': pe('🇿🇼'), 'Comoros': pe('🇰🇲'), 'East Timor': pe('🇹🇱'),
    'Falkland Islands': '🇫🇰', 'Faroe Islands': pe('🇫🇴'), 'French Polynesia': '🇵🇫',
    'Guinea-Bissau': pe('🇬🇼'), 'Saint Helena': '🇸🇭', 'Saint Pierre': '🇵🇲',
    'Wallis': '🇼🇫', 'Cook Islands': '🇨🇰', 'Niue': '🇳🇺', 'Samoa': pe('🇼🇸'),
    'Antarctica': '🇦🇶', 'Netherlands Antilles': '🇦🇼', 'Diego Garcia': '🇮🇴',
    'Ascension': '🇦🇨'
}

def detect_country_from_range(range_name):
    """Detect country from range name (e.g., 24491541XXXX -> Angola)"""
    if not range_name:
        return None
    
    # Extract digits from range name
    digits = re.findall(r'\d+', str(range_name))
    if not digits:
        # Try alternative pattern - check if range name itself contains country code
        range_str = str(range_name).replace('+', '').replace('-', '').replace(' ', '').replace('X', '').upper()
        for code_len in [3, 2, 1]:
            if len(range_str) >= code_len:
                code = range_str[:code_len]
                if code in COUNTRY_CODES:
                    return COUNTRY_CODES[code]
        return None
    
    first_part = digits[0]
    
    # Try to match country code (check from longest to shortest - most specific first)
    for code_len in [3, 2, 1]:
        if len(first_part) >= code_len:
            code = first_part[:code_len]
            if code in COUNTRY_CODES:
                return COUNTRY_CODES[code]
    
    # If still not found, try alternative patterns
    # Some ranges might have format like "+244" or "244-"
    range_str = str(range_name).replace('+', '').replace('-', '').replace(' ', '').replace('X', '').replace('x', '')
    for code_len in [3, 2, 1]:
        if len(range_str) >= code_len:
            code = range_str[:code_len]
            if code.isdigit() and code in COUNTRY_CODES:
                return COUNTRY_CODES[code]
                
    range_str_upper = str(range_name).upper()
    for code, country_name in COUNTRY_CODES.items():
        if code in range_str_upper or country_name.upper() in range_str_upper:
            return country_name
    
    return None

def get_country_flag(country_name):
    """Get flag emoji for country"""
    if not country_name or country_name == 'Unknown':
        return '🌍'
    
    # Exact match first
    if country_name in COUNTRY_FLAGS:
        return COUNTRY_FLAGS[country_name]
    
    # Partial match
    country_lower = country_name.lower()
    for key, flag in COUNTRY_FLAGS.items():
        if key.lower() == country_lower or key.lower() in country_lower or country_lower in key.lower():
            return flag
    
    # Try removing spaces and special characters
    country_normalized = country_name.replace(' ', '').replace('-', '').replace('_', '').lower()
    for key, flag in COUNTRY_FLAGS.items():
        key_normalized = key.replace(' ', '').replace('-', '').replace('_', '').lower()
        if key_normalized == country_normalized or key_normalized in country_normalized:
            return flag
    
    return '🌍'

# Country to ISO country code mapping (for #DK format)
COUNTRY_TO_ISO = {
    'Denmark': 'DK', 'USA': 'US', 'UK': 'GB', 'India': 'IN', 'Bangladesh': 'BD',
    'Pakistan': 'PK', 'Brazil': 'BR', 'China': 'CN', 'Japan': 'JP', 'South Korea': 'KR',
    'Germany': 'DE', 'France': 'FR', 'Italy': 'IT', 'Spain': 'ES', 'Netherlands': 'NL',
    'Belgium': 'BE', 'Switzerland': 'CH', 'Austria': 'AT', 'Sweden': 'SE', 'Norway': 'NO',
    'Finland': 'FI', 'Poland': 'PL', 'Russia': 'RU', 'Turkey': 'TR', 'Saudi Arabia': 'SA',
    'UAE': 'AE', 'Egypt': 'EG', 'South Africa': 'ZA', 'Nigeria': 'NG', 'Kenya': 'KE',
    'Ghana': 'GH', 'Ivory Coast': 'CI', 'Indonesia': 'ID', 'Philippines': 'PH', 'Thailand': 'TH',
    'Vietnam': 'VN', 'Malaysia': 'MY', 'Singapore': 'SG', 'Australia': 'AU', 'New Zealand': 'NZ',
    'Canada': 'CA', 'Mexico': 'MX', 'Argentina': 'AR', 'Chile': 'CL', 'Colombia': 'CO',
    'Peru': 'PE', 'Venezuela': 'VE', 'Greece': 'GR', 'Portugal': 'PT', 'Ireland': 'IE',
    'Czech Republic': 'CZ', 'Romania': 'RO', 'Hungary': 'HU', 'Bulgaria': 'BG', 'Croatia': 'HR',
    'Serbia': 'RS', 'Ukraine': 'UA', 'Belarus': 'BY', 'Kazakhstan': 'KZ', 'Israel': 'IL',
    'Iran': 'IR', 'Iraq': 'IQ', 'Afghanistan': 'AF', 'Sri Lanka': 'LK', 'Myanmar': 'MM',
    'Nepal': 'NP', 'Bhutan': 'BT', 'Maldives': 'MV', 'Lebanon': 'LB', 'Jordan': 'JO',
    'Syria': 'SY', 'Yemen': 'YE', 'Oman': 'OM', 'Kuwait': 'KW', 'Qatar': 'QA', 'Bahrain': 'BH',
    'Algeria': 'DZ', 'Morocco': 'MA', 'Tunisia': 'TN', 'Libya': 'LY', 'Sudan': 'SD',
    'Ethiopia': 'ET', 'Tanzania': 'TZ', 'Uganda': 'UG', 'Rwanda': 'RW', 'Angola': 'AO',
    'Mozambique': 'MZ', 'Zambia': 'ZM', 'Zimbabwe': 'ZW', 'Botswana': 'BW', 'Namibia': 'NA',
    'Madagascar': 'MG', 'Mauritius': 'MU', 'Senegal': 'SN', 'Mali': 'ML', 'Burkina Faso': 'BF',
    'Niger': 'NE', 'Chad': 'TD', 'Cameroon': 'CM', 'Gabon': 'GA', 'Congo': 'CG',
    'DR Congo': 'CD', 'Central African Republic': 'CF', 'Equatorial Guinea': 'GQ', 'Sao Tome and Principe': 'ST',
    'Guinea': 'GN', 'Sierra Leone': 'SL', 'Liberia': 'LR', 'Togo': 'TG', 'Benin': 'BJ',
    'Gambia': 'GM', 'Guinea-Bissau': 'GW', 'Cape Verde': 'CV', 'Mauritania': 'MR',
    'Djibouti': 'DJ', 'Eritrea': 'ER', 'Somalia': 'SO', 'Comoros': 'KM', 'Seychelles': 'SC',
    'Malawi': 'MW', 'Lesotho': 'LS', 'Swaziland': 'SZ', 'Eswatini': 'SZ', 'Burundi': 'BI',
    'Albania': 'AL', 'Armenia': 'AM', 'Azerbaijan': 'AZ', 'Georgia': 'GE', 'Moldova': 'MD',
    'Lithuania': 'LT', 'Latvia': 'LV', 'Estonia': 'EE', 'Slovenia': 'SI', 'Slovakia': 'SK',
    'Bosnia': 'BA', 'Macedonia': 'MK', 'Montenegro': 'ME', 'Kosovo': 'XK', 'Luxembourg': 'LU',
    'Malta': 'MT', 'Cyprus': 'CY', 'Iceland': 'IS', 'Liechtenstein': 'LI', 'Monaco': 'MC',
    'San Marino': 'SM', 'Andorra': 'AD', 'Vatican': 'VA', 'Greenland': 'GL', 'Faroe Islands': 'FO',
    'Taiwan': 'TW', 'Hong Kong': 'HK', 'Macau': 'MO', 'Mongolia': 'MN', 'North Korea': 'KP',
    'Laos': 'LA', 'Cambodia': 'KH', 'Brunei': 'BN', 'East Timor': 'TL', 'Papua New Guinea': 'PG',
    'Fiji': 'FJ', 'Solomon Islands': 'SB', 'Vanuatu': 'VU', 'New Caledonia': 'NC', 'French Polynesia': 'PF',
    'Samoa': 'WS', 'Tonga': 'TO', 'Palau': 'PW', 'Micronesia': 'FM', 'Marshall Islands': 'MH',
    'Kiribati': 'KI', 'Nauru': 'NR', 'Tuvalu': 'TV', 'Cook Islands': 'CK', 'Niue': 'NU',
    'Uruguay': 'UY', 'Paraguay': 'PY', 'Bolivia': 'BO', 'Ecuador': 'EC', 'Guyana': 'GY',
    'Suriname': 'SR', 'French Guiana': 'GF', 'Belize': 'BZ', 'Guatemala': 'GT', 'El Salvador': 'SV',
    'Honduras': 'HN', 'Nicaragua': 'NI', 'Costa Rica': 'CR', 'Panama': 'PA', 'Cuba': 'CU',
    'Jamaica': 'JM', 'Haiti': 'HT', 'Dominican Republic': 'DO', 'Trinidad and Tobago': 'TT',
    'Barbados': 'BB', 'Bahamas': 'BS', 'Grenada': 'GD', 'Saint Lucia': 'LC', 'Saint Vincent': 'VC',
    'Antigua and Barbuda': 'AG', 'Dominica': 'DM', 'Saint Kitts': 'KN', 'Bermuda': 'BM',
    'Cayman Islands': 'KY', 'British Virgin Islands': 'VG', 'US Virgin Islands': 'VI',
    'Puerto Rico': 'PR', 'Guam': 'GU', 'Northern Mariana Islands': 'MP', 'American Samoa': 'AS',
    'Falkland Islands': 'FK', 'Gibraltar': 'GI', 'Reunion': 'RE', 'Mayotte': 'YT',
    'French Guiana': 'GF', 'Martinique': 'MQ', 'Guadeloupe': 'GP', 'Saint Pierre': 'PM',
    'Wallis': 'WF', 'Cook Islands': 'CK', 'Niue': 'NU', 'Tokelau': 'TK', 'Pitcairn': 'PN',
    'Saint Helena': 'SH', 'Ascension': 'AC', 'Tristan da Cunha': 'TA', 'Diego Garcia': 'IO',
    'Antarctica': 'AQ', 'South Georgia': 'GS', 'Svalbard': 'SJ', 'Jan Mayen': 'SJ',
    'Bouvet Island': 'BV', 'Heard Island': 'HM', 'French Southern Territories': 'TF',
    'British Indian Ocean Territory': 'IO', 'Christmas Island': 'CX', 'Cocos Islands': 'CC',
    'Norfolk Island': 'NF', 'Palestine': 'PS', 'Western Sahara': 'EH', 'Sahrawi Arab Democratic Republic': 'EH'
}

def get_country_code(country_name):
    """Get ISO country code from country name (e.g., Denmark -> DK)"""
    if not country_name or country_name == 'Unknown':
        return 'XX'
    
    # Exact match first
    if country_name in COUNTRY_TO_ISO:
        return COUNTRY_TO_ISO[country_name]
    
    # Partial match
    country_lower = country_name.lower()
    for key, code in COUNTRY_TO_ISO.items():
        if key.lower() == country_lower or key.lower() in country_lower or country_lower in key.lower():
            return code
    
    # Try removing spaces and special characters
    country_normalized = country_name.replace(' ', '').replace('-', '').replace('_', '').lower()
    for key, code in COUNTRY_TO_ISO.items():
        key_normalized = key.replace(' ', '').replace('-', '').replace('_', '').lower()
        if key_normalized == country_normalized or key_normalized in country_normalized:
            return code
    
    # If not found, try to extract from country name (first 2 uppercase letters)
    if len(country_name) >= 2:
        # Try common patterns
        words = country_name.split()
        if len(words) > 0:
            first_word = words[0]
            if len(first_word) >= 2:
                return first_word[:2].upper()
    
    return 'XX'

def detect_country_from_number(number):
    """Detect country name from number prefix."""
    if not number:
        return None

    digits = ''.join(filter(str.isdigit, str(number)))
    for code_len in [3, 2, 1]:
        if len(digits) >= code_len:
            code = digits[:code_len]
            if code in COUNTRY_CODES:
                return COUNTRY_CODES[code]
    return None

def _sanitize_start_token(value, max_len=48):
    """Keep deep-link safe chars including underscores."""
    if not value:
        return ""
    return re.sub(r'[^A-Za-z0-9_\-]', '', str(value))[:max_len]

def infer_range_from_number(number):
    """Best-effort range guess from a phone number."""
    digits = ''.join(filter(str.isdigit, str(number or "")))
    if len(digits) >= 7:
        return f"{digits[:-3]}XXX"
    return digits or None

def normalize_service_name(service_name):
    """Normalize service text to internal key."""
    if not service_name:
        return None

    normalized = re.sub(r'[^a-z0-9]+', '', str(service_name).lower())
    if "whatsapp" in normalized:
        return "whatsapp"
    if "facebook" in normalized:
        return "facebook"
    if "telegram" in normalized:
        return "telegram"
    return None

def build_range_start_payload(range_value, service_name=None):
    """Build /start deep-link payload for range."""
    range_token = _sanitize_start_token(range_value, max_len=40).replace('x', 'X')
    if not range_token:
        return None

    service_token = _sanitize_start_token(service_name, max_len=12).lower()
    if service_token:
        return f"rng_{range_token}_{service_token}"
    return f"rng_{range_token}"

def parse_range_start_payload(payload):
    """Parse deep-link payload -> (range_value, service_hint)."""
    if not payload or not payload.startswith("rng_"):
        return None, None

    rest = payload[4:]
    if "_" in rest:
        # Use rsplit to handle ranges that contain underscores like b_42
        range_part, service_part = rest.rsplit("_", 1)
    else:
        range_part, service_part = rest, ""

    range_value = _sanitize_start_token(range_part, max_len=40).replace('x', 'X')
    service_hint = _sanitize_start_token(service_part, max_len=12).lower() or None

    if not range_value:
        return None, None

    return range_value, service_hint

async def build_range_deeplink(context: ContextTypes.DEFAULT_TYPE, range_value, service_name=None):
    """Build t.me deep link URL for opening bot with range payload."""
    global bot_username_cache

    payload = build_range_start_payload(range_value, service_name)
    if not payload:
        return None

    if not bot_username_cache:
        try:
            me = await context.bot.get_me()
            bot_username_cache = me.username
        except Exception as e:
            logger.warning(f"Unable to resolve bot username for range link: {e}")
            return None

    if not bot_username_cache:
        return None

    return f"https://t.me/{bot_username_cache}?start={payload}"

async def send_numbers_from_range_link(update: Update, context: ContextTypes.DEFAULT_TYPE, range_value, service_hint=None):
    """Fetch numbers for a deep-link range and start OTP monitor."""
    user_id = update.effective_user.id
    api_client = get_global_api_client()
    if not api_client:
        await update.message.reply_text("pe('❌') API connection error. Please try again.")
        return

    session = get_user_session(user_id)
    number_count = session.get('number_count', 2) if session else 2
    base_range = _sanitize_start_token(range_value, max_len=40).replace('x', 'X')

    if len(base_range) < 4:
        await update.message.reply_text("pe('❌') Invalid range.")
        return

    # Fast path for range-button links: console ranges often come without XXX.
    # Try the pattern form first to avoid slow retries on invalid raw prefixes.
    candidates = [base_range]
    if 'X' not in base_range:
        candidates = [f"{base_range}XXX", base_range]

    numbers_data = None
    selected_range = None
    for candidate in candidates:
        response = await run_api_call(api_client.get_multiple_numbers, candidate, candidate, number_count)
        if response:
            numbers_data = response
            selected_range = candidate
            break

    if not numbers_data:
        await update.message.reply_text(f"pe('❌') Failed to get numbers for range {base_range}.")
        return

    numbers_list = []
    for num_data in numbers_data:
        number = num_data.get('number', '')
        if number:
            numbers_list.append(number)

    if not numbers_list:
        await update.message.reply_text("pe('❌') No valid numbers received. Please try again.")
        return

    # Format numbers with + prefix for consistency
    formatted_numbers = []
    for num in numbers_list:
        display_num = str(num)
        if not display_num.startswith('+'):
            digits_only = ''.join(filter(str.isdigit, display_num))
            display_num = '+' + (digits_only if digits_only else display_num)
        formatted_numbers.append(display_num)

    country_name = detect_country_from_number(formatted_numbers[0]) or detect_country_from_range(selected_range) or 'Unknown'
    found_service = (
        normalize_service_name(service_hint)
        or normalize_service_name(session.get('service') if session else None)
        or "whatsapp"
    )

    keyboard = []
    for display_num in formatted_numbers:
        keyboard.append([InlineKeyboardButton(
            f"pe('📱') {display_num}",
            api_kwargs={"copy_text": {"text": display_num}}
        )])

    # Allow fetching fresh numbers from the same range via existing rng_ callback flow.
    context.user_data.setdefault('range_mapping', {})
    change_hash = hashlib.md5(f"{found_service}_{selected_range}".encode()).hexdigest()[:12]
    context.user_data['range_mapping'][change_hash] = {
        'service': found_service,
        'range_id': selected_range,
        'range_name': selected_range
    }
    keyboard.append([InlineKeyboardButton("pe('🔄') Change Numbers", callback_data=f"rng_{change_hash}", api_kwargs={"style": "success"})])
    reply_markup = InlineKeyboardMarkup(keyboard)

    country_flag = get_country_flag(country_name)
    service_icons = {
        "whatsapp": "pe('💬')",
        "facebook": "👥",
        "telegram": "pe('✈️')"
    }
    service_icon = service_icons.get(found_service, "pe('📱')")
    message_text = (
        f"{service_icon} {found_service.upper()}\n"
        f"{country_flag} {country_name}\n"
        f"pe('📋') Range: {selected_range}\n\n"
        f"pe('✅') {len(numbers_list)} numbers received:\n\n"
        "Tap a number to copy it."
    )

    sent_msg = await update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )

    update_user_session(
        user_id,
        service=found_service,
        country=country_name,
        range_id=selected_range,
        number=','.join(formatted_numbers),
        monitoring=1
    )

    if user_id in user_jobs:
        try:
            user_jobs[user_id].schedule_removal()
        except Exception as e:
            logger.debug(f"Error removing old job in send_numbers_from_range_link: {e}")

    if context.job_queue:
        job_data = {
            'user_id': user_id,
            'numbers': formatted_numbers,
            'service': found_service,
            'range_id': selected_range,
            'start_time': time.time(),
            'message_id': sent_msg.message_id
        }
        if country_name and country_name != 'Unknown':
            job_data['country'] = country_name

        job = context.job_queue.run_repeating(
            monitor_otp,
            interval=3,
            first=5,
            data=job_data
        )
        user_jobs[user_id] = job

def sort_numbers_for_ivory_coast(numbers_list, country_name):
    """
    Sort numbers for Ivory Coast - prioritize numbers starting with 22507
    """
    # Check if this is Ivory Coast
    ivory_coast_names = ['Ivory Coast', 'Côte d\'Ivoire', 'Cote d\'Ivoire', 'CI']
    is_ivory_coast = any(name.lower() in str(country_name).lower() for name in ivory_coast_names)
    
    if not is_ivory_coast:
        return numbers_list  # No sorting needed for other countries
    
    def get_sort_key(number):
        """Return sort key: 0 for 22507 prefix (priority), 1 for others"""
        # Extract digits from number
        digits = ''.join(filter(str.isdigit, str(number)))
        
        # Check if starts with 22507
        if digits.startswith('22507'):
            return (0, number)  # Priority 0 - comes first
        else:
            return (1, number)  # Priority 1 - comes after
    
    # Sort numbers: 22507 prefix first, then others
    sorted_numbers = sorted(numbers_list, key=get_sort_key)
    return sorted_numbers

def sort_ranges_for_ivory_coast(ranges_list):
    """
    Sort ranges for Ivory Coast - prioritize ranges starting with 22507 in range name
    """
    def get_sort_key(range_item):
        """Return sort key: 0 for 22507 prefix in range name (priority), 1 for others"""
        range_name = str(range_item.get('name', range_item.get('id', '')))
        # Extract digits from range name
        digits = ''.join(filter(str.isdigit, range_name))
        
        # Check if range name starts with 22507
        if digits.startswith('22507') or range_name.startswith('22507'):
            return (0, range_name)  # Priority 0 - comes first
        else:
            return (1, range_name)  # Priority 1 - comes after
    
    # Sort ranges: 22507 prefix first, then others
    sorted_ranges = sorted(ranges_list, key=get_sort_key)
    return sorted_ranges

def mask_number(number):
    """Mask only 3-4 middle digits, keeping range prefix and 3 digits at the end visible."""
    if not number:
        return number

    # Remove + and spaces, keep only digits
    digits = ''.join(filter(str.isdigit, number))
    has_plus = number.startswith('+')

    length = len(digits)
    if length < 10:
        if length > 6:
            masked = digits[:3] + 'XXX' + digits[-2:]
        else:
            return number
    else:
        # For typical 10-13 digit numbers:
        # Keep first 7 (range) and last 3, mask what's in between (usually 1-4 digits)
        # For 13 digits (like +2250789185820): 7 + 3 (mask) + 3 = 13
        # Result: +2250789XXX820
        prefix = digits[:7]
        suffix = digits[-3:]
        mask_len = length - 10
        if mask_len <= 0:
            # At least mask something if it's 10 digits
            masked = digits[:4] + 'XXX' + digits[-3:]
        else:
            masked = prefix + ('X' * max(3, mask_len)) + suffix

    # Add + back if it was there
    if has_plus:
        masked = '+' + masked

    return masked


def _strip_accents(text):
    """Normalize latin accents for matching."""
    return ''.join(
        ch for ch in unicodedata.normalize('NFKD', text)
        if not unicodedata.combining(ch)
    )


def _detect_language_by_script(text):
    """Fast script-based detection for non-latin SMS bodies."""
    counts = {
        'arabic': 0,
        'cyrillic': 0,
        'greek': 0,
        'hebrew': 0,
        'devanagari': 0,
        'bengali': 0,
        'thai': 0,
        'hangul': 0,
        'kana': 0,
        'cjk': 0,
    }
    total_letters = 0

    for ch in text:
        if ch.isalpha():
            total_letters += 1
        cp = ord(ch)
        if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F or 0x08A0 <= cp <= 0x08FF:
            counts['arabic'] += 1
        elif 0x0400 <= cp <= 0x052F:
            counts['cyrillic'] += 1
        elif 0x0370 <= cp <= 0x03FF:
            counts['greek'] += 1
        elif 0x0590 <= cp <= 0x05FF:
            counts['hebrew'] += 1
        elif 0x0900 <= cp <= 0x097F:
            counts['devanagari'] += 1
        elif 0x0980 <= cp <= 0x09FF:
            counts['bengali'] += 1
        elif 0x0E00 <= cp <= 0x0E7F:
            counts['thai'] += 1
        elif 0x1100 <= cp <= 0x11FF or 0xAC00 <= cp <= 0xD7AF:
            counts['hangul'] += 1
        elif 0x3040 <= cp <= 0x30FF:
            counts['kana'] += 1
        elif 0x4E00 <= cp <= 0x9FFF:
            counts['cjk'] += 1

    if total_letters == 0:
        return None

    script, count = max(counts.items(), key=lambda kv: kv[1])
    # Require a minimum absolute/relative dominance to avoid mixed-text false positives.
    if count < 3 or (count / total_letters) < 0.45:
        return None

    mapping = {
        'arabic': 'Arabic',
        'cyrillic': 'Russian',
        'greek': 'Greek',
        'hebrew': 'Hebrew',
        'devanagari': 'Hindi',
        'bengali': 'Bengali',
        'thai': 'Thai',
        'hangul': 'Korean',
        'kana': 'Japanese',
        'cjk': 'Chinese',
    }
    return mapping.get(script)


def detect_language_from_sms(sms_content):
    """Detect SMS language with script + weighted OTP phrase matching."""
    if not sms_content:
        return 'Unknown'

    text = str(sms_content).strip()
    if not text:
        return 'Unknown'

    script_language = _detect_language_by_script(text)
    if script_language:
        return script_language

    normalized = _strip_accents(text).lower()
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    if not normalized:
        return 'English'

    padded = f" {normalized} "
    template_overrides = [
        (" ny kaody facebook nao ", "Malagasy"),
        (" kaody facebook nao ", "Malagasy"),
        (" ny kaody ", "Malagasy"),
        (" adalah kode facebook anda ", "Indonesian"),
        (" kode konfirmasi facebook anda ", "Indonesian"),
        (" est votre code facebook ", "French"),
        (" is your facebook code ", "English"),
    ]
    for phrase, language in template_overrides:
        if phrase in padded:
            return language

    tokens = set(normalized.split())
    language_patterns = {
        'English': {
            'phrases': [
                ('your code is', 5), ('verification code', 5), ('one time password', 5),
                ('do not share', 4), ('security code', 4), ('use this code', 3)
            ],
            'tokens': [('otp', 3), ('verify', 2), ('secure', 2), ('password', 1)],
        },
        'French': {
            'phrases': [
                ('votre code est', 6), ('code de verification', 5), ('ne partagez pas', 5),
                ('mot de passe', 4)
            ],
            'tokens': [('verifier', 3), ('confirmer', 2), ('connexion', 2), ('votre', 1)],
        },
        'Spanish': {
            'phrases': [
                ('tu codigo es', 6), ('codigo de verificacion', 5), ('no compartas', 5),
                ('codigo de seguridad', 4)
            ],
            'tokens': [('contrasena', 4), ('verificacion', 3), ('confirmar', 2), ('tu', 1)],
        },
        'Portuguese': {
            'phrases': [
                ('seu codigo e', 6), ('codigo de verificacao', 5), ('nao compartilhe', 5),
                ('codigo de seguranca', 4)
            ],
            'tokens': [('senha', 4), ('verificacao', 3), ('confirmar', 2), ('seu', 1)],
        },
        'German': {
            'phrases': [
                ('ihr code ist', 6), ('dein code ist', 6), ('nicht teilen', 5),
                ('bestatigungscode', 5)
            ],
            'tokens': [('passwort', 4), ('verifizieren', 3), ('bestaetigen', 3)],
        },
        'Italian': {
            'phrases': [
                ('il tuo codice e', 6), ('codice di verifica', 5), ('non condividere', 5)
            ],
            'tokens': [('conferma', 3), ('verifica', 3), ('password', 2)],
        },
        'Dutch': {
            'phrases': [
                ('uw code is', 6), ('deel deze code niet', 5), ('verificatiecode', 5)
            ],
            'tokens': [('wachtwoord', 4), ('bevestig', 3), ('verifieren', 3)],
        },
        'Turkish': {
            'phrases': [
                ('dogrulama kodu', 6), ('kimseyle paylasmayin', 5)
            ],
            'tokens': [('kodunuz', 5), ('sifre', 4), ('dogrulama', 3), ('onay', 2)],
        },
        'Indonesian': {
            'phrases': [
                ('kode verifikasi', 6), ('jangan bagikan', 5), ('kode anda adalah', 5),
                ('adalah kode facebook anda', 7), ('kode konfirmasi facebook anda', 7)
            ],
            'tokens': [('verifikasi', 4), ('konfirmasi', 3), ('sandi', 3), ('anda', 2), ('adalah', 2)],
        },
        'Malay': {
            'phrases': [
                ('kod pengesahan', 6), ('jangan kongsi', 5), ('kod anda ialah', 5)
            ],
            'tokens': [('pengesahan', 4), ('sahkan', 3), ('laluan', 3), ('anda', 2)],
        },
        'Swahili': {
            'phrases': [
                ('msimbo wa kuthibitisha', 6), ('nambari yako ni', 5), ('usishiriki', 5)
            ],
            'tokens': [('uthibitishaji', 4), ('thibitisha', 3), ('neno', 2), ('siri', 2)],
        },
        'Malagasy': {
            'phrases': [
                ('kaody fanamarinana', 6), ('kaody anao', 5), ('aza zaraina', 5)
            ],
            'tokens': [('fanamarinana', 4), ('tenimiafina', 4), ('hamarinina', 3), ('kaody', 4), ('nao', 2)],
        },
    }

    scores = {}
    for lang, rules in language_patterns.items():
        score = 0
        for phrase, weight in rules['phrases']:
            phrase_hits = padded.count(f" {phrase} ")
            if phrase_hits:
                score += phrase_hits * weight
        for token, weight in rules['tokens']:
            if token in tokens:
                score += weight
        if score:
            scores[lang] = score

    if not scores:
        return 'English'

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_language, best_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    # Require minimum confidence and clear lead over runner-up.
    if best_score < 4:
        return 'English'
    if second_score and (best_score - second_score) < 2:
        # Resolve common close-pairs using unique markers.
        if {'laluan', 'pengesahan', 'kongsi'} & tokens:
            return 'Malay'
        if {'verifikasi', 'konfirmasi', 'bagikan', 'sandi'} & tokens:
            return 'Indonesian'
        if {'senha', 'nao', 'seu'} & tokens:
            return 'Portuguese'
        if {'contrasena', 'compartas', 'tu'} & tokens:
            return 'Spanish'
        if {'votre', 'partagez', 'mot'} & tokens:
            return 'French'

    return best_language


def extract_masked_otp_from_sms(sms_content):
    """Extract masked OTP token (e.g., ****** or ***-***)."""
    if not sms_content:
        return None

    text = str(sms_content).replace("\n", " ")

    patterns = [
        r'(?:otp|code|verification|confirm)[^0-9*]*([0-9*]{3,8}(?:-[0-9*]{3,8})?)',
        r'\b([0-9*]{3,8}-[0-9*]{3,8})\b',
        r'\b([0-9*]{4,10})\b'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        token = match.group(1).strip()
        # Console OTP values are masked with "*", keep masked format only.
        if "*" in token:
            return token

    return None

def is_console_otp_sms(sms_content, app_name=''):
    """Best-effort OTP detection for console stream logs."""
    text = f"{sms_content or ''} {app_name or ''}".lower()
    keywords = [
        "otp", "code", "verification", "verify", "facebook", "whatsapp",
        "auth", "security", "confirm", "confirmation"
    ]
    if any(keyword in text for keyword in keywords):
        return True

    if sms_content and "*" in sms_content and re.search(r'[0-9*]{3,8}(?:-[0-9*]{3,8})?', sms_content):
        return True

    return False

def remember_console_log(log_key):
    """Track forwarded console log keys with bounded memory."""
    if not log_key:
        return

    if log_key in forwarded_console_ids:
        return

    forwarded_console_ids.add(log_key)
    forwarded_console_order.append(log_key)

    if len(forwarded_console_order) > MAX_FORWARDED_CONSOLE_IDS:
        old_key = forwarded_console_order.pop(0)
        forwarded_console_ids.discard(old_key)

def build_console_channel_message(log_item):
    """Build channel message using legacy one-line channel template."""
    country = str(log_item.get('country') or 'Unknown').strip() or 'Unknown'
    service_raw = str(log_item.get('app_name') or 'Unknown').strip() or 'Unknown'
    
    # Prioritize 'range' field for number extraction as it contains full number in this API
    raw_range = str(log_item.get('range') or '').strip()
    raw_number = str(log_item.get('number') or '').strip()
    number_value = raw_range or raw_number or 'Unknown'
    
    # Format and mask the number
    if number_value != 'Unknown':
        # Ensure it has a + prefix for the mask_number function to handle properly
        display_number = number_value
        if not display_number.startswith('+'):
            digits_only = ''.join(filter(str.isdigit, display_number))
            display_number = '+' + (digits_only if digits_only else display_number)
        
        number_masked = mask_number(display_number)
    else:
        number_masked = 'Unknown'

    sms_content = str(log_item.get('sms') or '').strip()
    language = detect_language_from_sms(sms_content) if sms_content else 'English'
    service_key = normalize_service_name(service_raw)

    country_flag = get_country_flag(country)
    country_code = get_country_code(country)
    service_display = {
        "whatsapp": "WhatsApp",
        "facebook": "Facebook",
        "telegram": "Telegram"
    }.get(service_key, service_raw)

    return f"{country_flag} #{country_code} {html.escape(service_display)} {html.escape(number_masked)} {html.escape(language)}"

# Bot Handlers
async def rangechkr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rangechkr command - Show ranges grouped by service"""
    user_id = update.effective_user.id
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await update.message.reply_text("pe('❌') Your access is pending approval.")
        return
    
    # Get global API client
    api_client = get_global_api_client()
    if not api_client:
        await update.message.reply_text("pe('❌') API connection error. Please try again.")
        return
    
    # Show service selection first (fixed three: WhatsApp, Facebook, Others)
    keyboard = [
        [InlineKeyboardButton("pe('💬') WhatsApp", callback_data="rangechkr_service_whatsapp", api_kwargs={"style": "success"})],
        [InlineKeyboardButton("👥 Facebook", callback_data="rangechkr_service_facebook", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("pe('✈️') Telegram", callback_data="rangechkr_service_telegram", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("pe('✨') Others", callback_data="rangechkr_service_others", api_kwargs={"style": "danger"})]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🧭 Range Explorer\nSelect a service:",
        reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"
    deep_link_arg = context.args[0] if context.args else None
    deep_link_range, deep_link_service = parse_range_start_payload(deep_link_arg)
    
    # Get current status first (before adding user)
    status = get_user_status(user_id)
    
    # Add user to database only if status is 'pending' (user doesn't exist or is pending)
    # This prevents overwriting approved/rejected status
    if status == 'pending':
        add_user(user_id, username)
        # Re-check status after adding
        status = get_user_status(user_id)
    
    if status == 'approved':
        # Get current number count setting
        session = get_user_session(user_id)
        current_count = session.get('number_count', 2) if session else 2
        
        # Show main menu buttons
        keyboard = [
            [KeyboardButton("pe('🚀') Get Number", api_kwargs={"style": "success"})],
            [KeyboardButton("pe('🎛') Number Count", api_kwargs={"style": "primary"})],
            [KeyboardButton("pe('📈') My Stats", api_kwargs={"style": "primary"})]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "Welcome.\n\n"
            "Use **Get Number** to start a new OTP session.\n"
            "Use **Number Count** to choose how many numbers you receive per request.\n"
            f"📌 Current setting: **{current_count}** number(s)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        # If user opened bot from channel "Range" button, fetch numbers immediately.
        if deep_link_range:
            await update.message.reply_text(f"pe('⏳') Processing range: {deep_link_range}")
            await send_numbers_from_range_link(update, context, deep_link_range, deep_link_service)
    elif status == 'rejected':
        await update.message.reply_text("pe('❌') Your access has been rejected. Please contact admin.")
    else:
        # Notify admin
        try:
            admin_message = f"🆕 New user request:\n\n"
            admin_message += f"User ID: {user_id}\n"
            admin_message += f"Username: @{username}\n"
            admin_message += f"Name: {user.first_name or 'N/A'}"
            
            keyboard = [
                [
                    InlineKeyboardButton("pe('✅') Approve", callback_data=f"admin_approve_{user_id}", api_kwargs={"style": "success"}),
                    InlineKeyboardButton("pe('❌') Reject", callback_data=f"admin_reject_{user_id}", api_kwargs={"style": "danger"})
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=admin_message,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
        
        await update.message.reply_text(
            "pe('⏳') Your request has been sent to admin. Please wait for approval."
        )

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin commands"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("pe('❌') Access denied. Admin only.")
        return
    
    command = update.message.text.split()[0] if update.message.text else ""
    
    if command == "/users":
        users = get_all_users()
        if not users:
            await update.message.reply_text("pe('📋') No users found.")
            return
        
        message = "pe('📋') All Users:\n\n"
        for uid, uname, status in users:
            message += f"ID: {uid}\n"
            message += f"Username: @{uname or 'N/A'}\n"
            message += f"Status: {status}\n"
            message += f"{'─' * 20}\n"
        
        await update.message.reply_text(message[:4000])  # Telegram limit

    elif command.startswith("/add"):
        # Usage: /add <user_id>
        try:
            target_id = int(context.args[0]) if context.args else None
            if not target_id:
                await update.message.reply_text("Usage: /add <user_id>")
                return

            # Ensure user exists (username unknown here) then approve
            add_user(target_id, username=None)
            approve_user(target_id)
            await update.message.reply_text(f"pe('✅') User {target_id} approved/added successfully.")
        except Exception as e:
            await update.message.reply_text(f"pe('❌') Error: {e}")
    
    elif command.startswith("/remove"):
        try:
            target_id = int(context.args[0]) if context.args else None
            if target_id:
                # Stop any latest monitoring job for this user
                if target_id in user_jobs:
                    try:
                        user_jobs[target_id].schedule_removal()
                    except:
                        pass
                    del user_jobs[target_id]
                remove_user(target_id)
                await update.message.reply_text(f"pe('✅') User {target_id} removed successfully.")
            else:
                await update.message.reply_text("Usage: /remove <user_id>")
        except Exception as e:
            await update.message.reply_text(f"pe('❌') Error: {e}")
    
    elif command == "/pending":
        pending = get_pending_users()
        if not pending:
            await update.message.reply_text("pe('✅') No pending users.")
            return
        
        message = "pe('⏳') Pending Users:\n\n"
        for uid, uname in pending:
            message += f"ID: {uid} - @{uname or 'N/A'}\n"
        
        await update.message.reply_text(message)

    elif command == "/broadcast":
        # Usage:
        # - /broadcast your message here
        # - Reply to a message with /broadcast (broadcasts replied text/caption)
        if not update.message:
            return

        broadcast_text = None
        if context.args:
            broadcast_text = " ".join(context.args).strip()
        elif update.message.reply_to_message:
            rt = update.message.reply_to_message
            broadcast_text = (rt.text or rt.caption or "").strip()

        if not broadcast_text:
            await update.message.reply_text(
                "pe('📣') Broadcast usage:\n"
                "- Reply any message then type: /broadcast\n"
                "- Or: /broadcast <your message>"
            )
            return

        approved_user_ids = get_approved_user_ids()
        if not approved_user_ids:
            await update.message.reply_text("pe('ℹ️') No approved users found to broadcast to.")
            return

        await update.message.reply_text(f"pe('📣') Broadcasting to {len(approved_user_ids)} approved user(s)...")

        sent = 0
        failed = 0
        failed_ids = []

        for uid in approved_user_ids:
            try:
                await context.bot.send_message(chat_id=uid, text=broadcast_text)
                sent += 1
            except Exception as e:
                failed += 1
                failed_ids.append(uid)
                logger.error(f"Broadcast failed to {uid}: {e}")
            # Small delay to reduce flood-limit risk
            await asyncio.sleep(0.05)

        summary = f"pe('✅') Broadcast done.\n\nSent: {sent}\nFailed: {failed}"
        if failed_ids:
            preview = ", ".join(map(str, failed_ids[:30]))
            more = "" if len(failed_ids) <= 30 else f" ... (+{len(failed_ids) - 30} more)"
            summary += f"\n\nFailed user_ids: {preview}{more}"

        await update.message.reply_text(summary)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    # Answer callback immediately to prevent timeout - with error handling
    try:
        await query.answer()
    except Exception as e:
        # Query might be too old, continue anyway
        logger.debug(f"Callback query answer failed (might be old): {e}")
    
    data = query.data
    user_id = query.from_user.id
    
    # Admin actions
    if data.startswith("admin_"):
        if user_id != ADMIN_USER_ID:
            await query.edit_message_text("pe('❌') Access denied.")
            return
        
        if data.startswith("admin_approve_"):
            target_user_id = int(data.split("_")[2])
            approve_user(target_user_id)
            await query.edit_message_text(f"pe('✅') User {target_user_id} approved.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="pe('✅') Your request has been approved! Use /start to begin."
                )
            except:
                pass
        
        elif data.startswith("admin_reject_"):
            target_user_id = int(data.split("_")[2])
            reject_user(target_user_id)
            await query.edit_message_text(f"pe('❌') User {target_user_id} rejected.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="pe('❌') Your request has been rejected."
                )
            except:
                pass
        return
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await query.edit_message_text("pe('❌') Your access is pending approval.")
        return
    
    # Handle number count setting (1-5)
    if data.startswith("set_count_"):
        try:
            count = int(data.split("_")[2])
            if count < 1 or count > 5:
                await query.edit_message_text("pe('❌') Invalid count. Please select 1-5.")
                return
            
            # Update user session with new count
            update_user_session(user_id, number_count=count)
            
            await query.edit_message_text(
                f"pe('✅') Number count set to {count}.\n\n"
                f"Now you will receive {count} number(s) when you request numbers."
            )
        except (ValueError, IndexError) as e:
            logger.error(f"Error setting number count: {e}")
            await query.edit_message_text("pe('❌') Error setting number count. Please try again.")
        return
    
    # Main menu Others pagination handlers
    if data == "sel_others_prev":
        page = context.user_data.get('service_others_page', 0)
        context.user_data['service_others_page'] = max(0, page - 1)
        query.data = "service_others"
        # Since we modified query.data, we can just let it fall through to service_ handler
        # But explicit call is safer if service_ handler is below
        # Wait, if I call await button_callback, it recurses.
        # But if I change data and let it continue?
        # NO, 'data' variable is local string copy. Modifying it doesn't affect subsequent checks unless I modify 'data' var AND code is structured to check updated 'data'.
        # The code below checks `if data.startswith("service_"):`.
        # So if I update `data = "service_others"`, it will fall through!
        data = "service_others" 
        # Fall through to service_ handler
    
    elif data == "sel_others_next":
        page = context.user_data.get('service_others_page', 0)
        context.user_data['service_others_page'] = page + 1
        data = "service_others"
        # Fall through
        
    elif data == "sel_others_noop":
        try: await query.answer("Current page")
        except: pass
        return

    # Main menu Others specific service selection
    elif data.startswith("sel_others_"):
        try:
            # Format: sel_others_{idx}
            idx = int(data.split("_")[2])
            discovered = context.user_data.get('discovered_services', [])
            if 0 <= idx < len(discovered):
                svc = discovered[idx]
                logger.info(f"Selected {svc} from Main Menu Others")
                # Redirect to standard service handler
                data = f"service_{svc}"
                # Fall through to service_ handler
            else:
                await query.edit_message_text("pe('❌') Service not found. Please reload.")
                return
        except Exception as e:
            logger.error(f"Error selecting from others: {e}")
            await query.edit_message_text("pe('❌') Error selecting service.")
            return
    # Service selection (from inline buttons)
    if data.startswith("service_"):
        service_name = data.split("_", 1)[1]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("pe('❌') API connection error. Please try again.")
            return
        
        # If Others clicked, first show dynamic service list (excluding WhatsApp/Facebook)
        if service_name == "others":
            await query.edit_message_text("pe('⏳') Discovering services (this may take a moment)...")
            try:
                # Use get_ranges("others") which searches many keywords
                # No lock needed as APIClient handles internal state
                ranges = await run_api_call(api_client.get_ranges, "others")
                
                if not ranges:
                    await query.edit_message_text("pe('❌') No services found.")
                    return

                # Aggregate by service
                services_found = {} # {service_name: count}
                
                for r in ranges:
                    svc = r.get('service', 'Other')
                    if not svc: svc = 'Other'
                    svc = str(svc).strip()
                    if svc == "": svc = "Other"
                    
                    if svc not in services_found:
                        services_found[svc] = 0
                        
                    services_found[svc] += 1
                
                sorted_services = sorted(services_found.keys())
                context.user_data['discovered_services'] = sorted_services
                
                # Pagination logic
                page = context.user_data.get('service_others_page', 0)
                services_per_page = 90
                total_pages = (len(sorted_services) + services_per_page - 1) // services_per_page
                
                start_idx = page * services_per_page
                end_idx = min(start_idx + services_per_page, len(sorted_services))
                page_services = sorted_services[start_idx:end_idx]
                
                keyboard = []
                row = []
                for idx in range(start_idx, end_idx):
                     svc = sorted_services[idx]
                     # Skip primary if found (optional, but better UX to keep separate)
                     # But if user wants EVERYTHING in others, I could remove this.
                     # "Whatsapp and Facebook flow unchanged" implies they stay in main menu.
                     if svc.lower() in ['whatsapp', 'facebook']: continue
                     
                     count = services_found[svc]
                     # Capitalize for display
                     label = f"{svc} ({count})"
                     
                     # Callback: sel_others_{idx} (Changed from service_others to avoid conflict)
                     row.append(InlineKeyboardButton(label, callback_data=f"sel_others_{idx}", api_kwargs={"style": "primary"}))
                     
                     if len(row) == 2:
                         keyboard.append(row)
                         row = []
                
                if row:
                    keyboard.append(row)
                
                # Pagination buttons
                if total_pages > 1:
                    nav_row = []
                    if page > 0:
                        nav_row.append(InlineKeyboardButton("◀️ Prev", api_kwargs={"style": "primary"}, callback_data="sel_others_prev"))
                    nav_row.append(InlineKeyboardButton(f"Page {page + 1}/{total_pages}", callback_data="sel_others_noop"))
                    if page < total_pages - 1:
                        nav_row.append(InlineKeyboardButton("Next ▶️", api_kwargs={"style": "primary"}, callback_data="sel_others_next"))
                    keyboard.append(nav_row)
                
                keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="back_services")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                page_info = f" (Page {page + 1}/{total_pages})" if total_pages > 1 else ""
                await query.edit_message_text(
                    f"pe('📋') Found {len(sorted_services)} Services{page_info}:\nShowing {len(page_services)} services", 
                    reply_markup=reply_markup
                )
            
            except Exception as e:
                logger.error(f"Error discovering services: {e}")
                await query.edit_message_text(f"pe('❌') Error discovering services: {str(e)}")
            return
        
        # For primary services (WhatsApp/Facebook)
        app_id = resolve_app_id(service_name, context)
        if not app_id:
            await query.edit_message_text("pe('❌') Invalid service.")
            return
        
        ranges = await run_api_call(api_client.get_ranges, app_id)
        
        if not ranges:
            await query.edit_message_text(f"pe('❌') No active ranges available for {service_name}.")
            return

        # Group ranges by country - detect from range name if country not available
        country_ranges = {}
        for r in ranges:
            range_name = r.get('name', r.get('id', ''))
            # Try to get country from API response first
            country = r.get('cantryName', r.get('country', ''))
            
            # If country not found or Unknown, detect from range name
            if not country or country == 'Unknown' or str(country).strip() == '':
                country = detect_country_from_range(range_name)
            
            # Final fallback
            if not country:
                country = 'Unknown'
            
            country_ranges.setdefault(country, []).append(r)

        # Create country buttons - INLINE KEYBOARD
        keyboard = []
        
        # Helper to get "best" time for a country
        def get_country_best_time(c_name):
            ranges_list = country_ranges.get(c_name, [])
            best_min = 999999
            best_str = ""
            for r in ranges_list:
                t_str = r.get('datetime', '')
                t_min = parse_time_ago(t_str)
                if t_min < best_min:
                    best_min = t_min
                    best_str = t_str
            return best_min, best_str

        # Sort countries by recency (Ascending minutes ago)
        # Using 999999 as default sort key ensures unknown times go to bottom
        sorted_countries = sorted(
            [c for c in country_ranges.keys() if c != 'Unknown'],
            key=lambda c: get_country_best_time(c)[0]
        )
        
        if 'Unknown' in country_ranges and len(sorted_countries) == 0:
            sorted_countries.append('Unknown')

        # Helper for UI Truncation
        def format_country_label(flag, name, time_str, max_len=30):
            # Keep country sort behavior by time, but do not show time text.
            available_len = max_len - 3
            if available_len < 5:
                available_len = 5

            if len(name) > available_len:
                name = name[:available_len - 3] + "..."

            return f"{flag} {name}"

        for i in range(0, len(sorted_countries), 2):
            row = []
            
            c1 = sorted_countries[i]
            _, time1 = get_country_best_time(c1)
            flag1 = get_country_flag(c1)
            label1 = format_country_label(flag1, c1, time1)
            
            row.append(InlineKeyboardButton(label1, callback_data=f"country_{service_name}_{c1}", api_kwargs={"style": "primary"}))
            
            if i + 1 < len(sorted_countries):
                c2 = sorted_countries[i + 1]
                _, time2 = get_country_best_time(c2)
                flag2 = get_country_flag(c2)
                label2 = format_country_label(flag2, c2, time2)
                row.append(InlineKeyboardButton(label2, callback_data=f"country_{service_name}_{c2}", api_kwargs={"style": "primary"}))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="back_services")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"pe('📱') {service_name.upper()} - Select Country:",
            reply_markup=reply_markup
        )
        return

    # Service selection for dynamic Others list (New Flow)
    if data.startswith("service_others_"):
        try:
            idx = int(data.split("_")[2])
            discovered = context.user_data.get('discovered_services', [])
            if idx < 0 or idx >= len(discovered):
                await query.edit_message_text("pe('❌') Invalid service.")
                return
                
            service_name = discovered[idx]
            # Create a safe key for callback
            service_key = f"others_{idx}"
            
            # Register in custom_services for resolution
            context.user_data.setdefault('custom_services', {})
            context.user_data['custom_services'][service_key] = service_name
            
            # Get API client
            api_client = get_global_api_client()
            if not api_client:
                await query.edit_message_text("pe('❌') API connection error.")
                return
                
            # Get ranges "others" (cached)
            ranges = await run_api_call(api_client.get_ranges, "others")
            
            if not ranges:
                await query.edit_message_text("pe('❌') No ranges found (session expired?).")
                return
                
            # Filter by service (Relaxed matching)
            service_ranges = []
            service_norm = service_name.lower()
            for r in ranges:
                 s = str(r.get('service', 'Other')).lower()
                 if s and (service_norm in s or s in service_norm):
                     service_ranges.append(r)
            
            # Debug log for filtering failure
            if not service_ranges:
                 logger.info(f"Filtering mismatch: Target='{service_name}'. Samples: {[r.get('service') for r in ranges[:5]]}")
            
            if not service_ranges:
                 await query.edit_message_text(f"pe('❌') No ranges found for {service_name}.")
                 return
                 
            # Group by Country
            country_ranges = {}
            for r in service_ranges:
                range_name = r.get('name', r.get('id', ''))
                country = r.get('cantryName', r.get('country', ''))
                
                if not country or country == 'Unknown' or str(country).strip() == '':
                    country = detect_country_from_range(range_name)
                
                if not country or country == 'Unknown':
                    range_str = str(range_name).upper()
                    for code, c_name in COUNTRY_CODES.items():
                        if code in range_str or c_name.upper() in range_str:
                            country = c_name
                            break
                
                if not country: country = 'Unknown'
                
                country_ranges.setdefault(country, []).append(r)
            
            # Create country buttons
            keyboard = []
            
            # Helper to get "best" time for a country
            def get_country_best_time(c_name):
                ranges_list = country_ranges.get(c_name, [])
                # Use cached timestamps if available, or parse again
                best_min = 999999
                best_str = ""
                for r in ranges_list:
                    t_str = r.get('datetime', '')
                    t_min = parse_time_ago(t_str)
                    if t_min < best_min:
                        best_min = t_min
                        best_str = t_str
                return best_min, best_str

            # Sort countries by recency
            sorted_countries = sorted(
                [c for c in country_ranges.keys() if c != 'Unknown'],
                key=lambda c: get_country_best_time(c)[0]
            )
            
            if 'Unknown' in country_ranges and len(sorted_countries) == 0:
                sorted_countries.append('Unknown')
                
            for i in range(0, len(sorted_countries), 2):
                row = []
                
                c1 = sorted_countries[i]
                _, time1 = get_country_best_time(c1)
                flag1 = get_country_flag(c1)
                label1 = format_country_label(flag1, c1, time1)
                
                row.append(InlineKeyboardButton(label1, callback_data=f"country_{service_key}_{c1}", api_kwargs={"style": "primary"}))
                
                if i + 1 < len(sorted_countries):
                    c2 = sorted_countries[i + 1]
                    _, time2 = get_country_best_time(c2)
                    flag2 = get_country_flag(c2)
                    label2 = format_country_label(flag2, c2, time2)
                    row.append(InlineKeyboardButton(label2, callback_data=f"country_{service_key}_{c2}", api_kwargs={"style": "primary"}))
                
                keyboard.append(row)
                
            keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="service_others")]) 
            # Back goes to Main Others List (handled by service_others in main handler)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"pe('📱') {service_name} - Select Country:", reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in service_others: {e}")
            await query.edit_message_text("pe('❌') Error loading countries.")
        return
    
    # Note: num_copy_ handler removed - using copy_text parameter in InlineKeyboardButton
    # When copy_text is used, button click directly copies text without callback
    
    # Country selection
    elif data.startswith("country_"):
        parts = data.split("_", 2)
        service_name = parts[1]
        country = parts[2]
        
        app_id = resolve_app_id(service_name, context)
        if not app_id:
            await query.edit_message_text("pe('❌') Invalid service.")
            return
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("pe('❌') API connection error. Please try again.")
            return
        
        ranges = await run_api_call(api_client.get_ranges, app_id)
        
        # Find ranges for this country - collect all matching ranges first
        # Match by detecting country from range name, not just API country field
        matching_ranges = []
        for r in ranges:
            range_name = r.get('name', r.get('id', ''))
            r_country_api = r.get('cantryName', r.get('country', ''))
            is_match = False
            
            # Hybrid approach: validate API country against range name to prevent API-side errors
            # This ensures we don't show Ivory Coast (225) numbers when user selects Cameroon
            if r_country_api and r_country_api.lower() == country.lower():
                # API says this is the right country, but verify with range name
                r_country_detected = detect_country_from_range(range_name)
                logger.info(f"Range {range_name}: API says '{r_country_api}', detected from name: '{r_country_detected}', looking for: '{country}'")
                if r_country_detected:
                    # If range name suggests a different country, skip this range
                    if r_country_detected.lower() == country.lower():
                        is_match = True
                        logger.info(f"✓ Range {range_name} MATCHED (both API and name agree on {country})")
                    else:
                        logger.info(f"✗ Range {range_name} SKIPPED (API says {r_country_api} but name suggests {r_country_detected})")
                else:
                    # Can't detect from range name, trust API
                    is_match = True
                    logger.info(f"✓ Range {range_name} MATCHED (trusting API {r_country_api}, can't detect from name)")
            # Fallback: if API provides no country info, use range name detection
            elif not r_country_api or r_country_api.strip() == '' or r_country_api == 'Unknown':
                r_country_detected = detect_country_from_range(range_name)
                if r_country_detected and r_country_detected.lower() == country.lower():
                    is_match = True
                    logger.info(f"✓ Range {range_name} MATCHED (no API country, detected {r_country_detected})")
                elif not r_country_detected and country.lower() == 'unknown':
                    is_match = True
                    logger.info(f"✓ Range {range_name} MATCHED (no API country, could not detect, matched Unknown)")
            
            if is_match:
                matching_ranges.append(r)
        
        # Sort ranges for Ivory Coast (22507 priority)
        if matching_ranges:
            matching_ranges = sort_ranges_for_ivory_coast(matching_ranges)
            selected_range = matching_ranges[0]  # Use first (priority) range
        else:
            selected_range = None
        
        if not selected_range:
            await query.edit_message_text(f"pe('❌') No ranges found for {country}.")
            return
        
        range_id = selected_range.get('numerical_id', selected_range.get('range_id', selected_range.get('id', '')))
        range_name = selected_range.get('pattern', selected_range.get('name', ''))
        
        # Delete old message and send new one at the bottom as requested
        try:
            await query.message.delete()
        except Exception as e:
            logger.debug(f"Could not delete message: {e}")
        
        sent_loading_msg = await context.bot.send_message(
            chat_id=user_id,
            text="pe('⏳') Requesting numbers..."
        )
        loading_message_id = sent_loading_msg.message_id
        try:
            await query.answer()  # Acknowledge callback immediately to prevent timeout
        except Exception as e:
            logger.debug(f"Callback query answer failed (might be old): {e}")
        
        # Request numbers in background (async task) - use user's preference
        async def fetch_and_send_numbers():
            try:
                # Get user's number count preference
                session = get_user_session(user_id)
                number_count = session.get('number_count', 2) if session else 2
                
                # with api_lock:
                # Try range_name first, then range_id (like otp_tool.py)
                numbers_data = await run_api_call(api_client.get_multiple_numbers, range_id, range_name, number_count)
                
                if not numbers_data or len(numbers_data) == 0:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text="pe('❌') Failed to get numbers. Please try again."
                    )
                    return
                
                # Extract numbers from data (now pre-filtered by get_multiple_numbers)
                numbers_list = []
                for num_data in numbers_data:
                    number = num_data.get('number', '')
                    if number:
                        numbers_list.append(number)
                
                if not numbers_list:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text="pe('❌') No valid numbers received. Please try again."
                    )
                    return
                
                country_name = numbers_data[0].get('cantryName', numbers_data[0].get('country', country))
                
                # Sort numbers for Ivory Coast (22507 priority)
                numbers_list = sort_numbers_for_ivory_coast(numbers_list, country_name)
                
                # Format numbers with + prefix
                formatted_numbers = []
                for num in numbers_list:
                    display_num = str(num)
                    if not display_num.startswith('+'):
                        digits_only = ''.join(filter(str.isdigit, display_num))
                        display_num = '+' + (digits_only if digits_only else display_num)
                    formatted_numbers.append(display_num)

                # Store all numbers in session (comma-separated)
                numbers_str = ','.join(formatted_numbers)
                update_user_session(user_id, service_name, country, range_id, numbers_str, 1)

                # Start monitoring all numbers in background
                # First, cancel any existing job to reset 15-min timer
                if user_id in user_jobs:
                    try:
                        old_job = user_jobs[user_id]
                        old_job.schedule_removal()
                    except Exception as e:
                        logger.error(f"Error cancelling old job: {e}")

                job = context.job_queue.run_repeating(
                    monitor_otp,
                    interval=BOT_CONFIG['poll_interval'],
                    first=1,
                    chat_id=user_id,
                    data={'numbers': formatted_numbers, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time(), 'message_id': loading_message_id}
                )
                user_jobs[user_id] = job  # Store job reference

                # Create inline keyboard with 5 numbers (click to copy using copy_text parameter)
                keyboard = []
                for display_num in formatted_numbers:
                    # Use copy_text via api_kwargs - Telegram Bot API 7.0+ feature
                    # Format: {"copy_text": {"text": "number"}} - clicking button will copy the number
                    keyboard.append([InlineKeyboardButton(f"pe('📱') {display_num}", api_kwargs={"copy_text": {"text": display_num}})])
                # Get country flag
                country_flag = get_country_flag(country_name)
                
                # Get service icon
                service_icons = {
                    "whatsapp": "pe('💬')",
                    "facebook": "👥",
                    "telegram": "pe('✈️')"
                }
                service_icon = service_icons.get(service_name, "pe('📱')")
                
                keyboard.append([InlineKeyboardButton("pe('🔄') Next Number", callback_data=f"country_{service_name}_{country}", api_kwargs={"style": "success"})])
                keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="back_services")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Format message like the reference image
                message = f"Country: {country_flag} {country_name}\n"
                message += f"Service: {service_icon} {service_name.capitalize()}\n"
                message += f"Waiting for OTP...... pe('⏳')"
                
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=loading_message_id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Error fetching numbers: {e}")
                import traceback
                logger.error(traceback.format_exc())
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text=f"pe('❌') Error: {str(e)}"
                    )
                except:
                    pass
        
        # Run in background
        import asyncio
        asyncio.create_task(fetch_and_send_numbers())
        return
    
    # Range checker service selection from dynamic list (Others) - New Flow
    elif data.startswith("rangechkr_others_"):
        try:
            idx = int(data.split("_")[2])
            discovered = context.user_data.get('rangechkr_discovered_services', [])
            if idx < 0 or idx >= len(discovered):
                await query.edit_message_text("pe('❌') Invalid service.")
                return
            
            service_name = discovered[idx]
            # Unique key to avoid conflict with main flow
            service_key = f"rng_others_{idx}"
            
            # Register in custom_services for resolution (shared map)
            context.user_data.setdefault('custom_services', {})
            context.user_data['custom_services'][service_key] = service_name
            
            # Get global API client
            api_client = get_global_api_client()
            if not api_client:
                await query.edit_message_text("pe('❌') API connection error. Please try again.")
                return
            
            # Get ranges "others" (cached fast)
            ranges = await run_api_call(api_client.get_ranges, "others")
            
            if not ranges:
                await query.edit_message_text(f"pe('❌') No ranges found for {service_name}.")
                return
            
            # Filter by service
            service_ranges = []
            for r in ranges:
                s = r.get('service', 'Other')
                if s and str(s).strip() == service_name:
                    service_ranges.append(r)
            
            if not service_ranges:
                await query.edit_message_text(f"pe('❌') No ranges found for {service_name}.")
                return
                
            # Group ranges by country - detect from range name if country not available
            country_ranges = {}
            for r in service_ranges:
                range_name = r.get('name', r.get('id', ''))
                country = r.get('cantryName', r.get('country', ''))
                
                if not country or country == 'Unknown' or str(country).strip() == '':
                    country = detect_country_from_range(range_name)
                
                if not country or country == 'Unknown':
                    range_str = str(range_name).upper()
                    for code, country_name in COUNTRY_CODES.items():
                        if code in range_str or country_name.upper() in range_str:
                            country = country_name
                            break
                
                if not country: country = 'Unknown'
                
                country_ranges.setdefault(country, []).append(r)

            # Create country buttons - INLINE KEYBOARD
            keyboard = []
            country_list = [c for c in sorted(country_ranges.keys()) if c != 'Unknown']
            if 'Unknown' in country_ranges and len(country_list) == 0:
                country_list.append('Unknown')

            for i in range(0, len(country_list), 2):
                row = []
                flag1 = get_country_flag(country_list[i])
                row.append(InlineKeyboardButton(
                    f"{flag1} {country_list[i]}",
                    callback_data=f"rangechkr_country_{service_key}_{country_list[i]}"
                ))
                if i + 1 < len(country_list):
                    flag2 = get_country_flag(country_list[i + 1])
                    row.append(InlineKeyboardButton(
                        f"{flag2} {country_list[i + 1]}",
                        callback_data=f"rangechkr_country_{service_key}_{country_list[i + 1]}"
                    ))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔙 Services", api_kwargs={"style": "danger"}, callback_data="rangechkr_service_others")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"pe('📋') {service_name} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error fetching ranges for {service_name}: {e}")
            await query.edit_message_text(f"pe('❌') Failed to load ranges.")
            return
    
    # Others service pagination handlers
    elif data == "rangechkr_others_prev":
        page = context.user_data.get('rangechkr_others_page', 0)
        context.user_data['rangechkr_others_page'] = max(0, page - 1)
        # Trigger service list reload by simulating rangechkr_service_others callback
        query.data = "rangechkr_service_others"
        await button_callback(update, context)
        return
    
    elif data == "rangechkr_others_next":
        page = context.user_data.get('rangechkr_others_page', 0)
        context.user_data['rangechkr_others_page'] = page + 1
        # Trigger service list reload
        query.data = "rangechkr_service_others"
        await button_callback(update, context)
        return
    
    elif data == "rangechkr_others_noop":
        # Just answer the callback, don't do anything
        try:
            await query.answer("Current page")
        except:
            pass
        return
    
    # Selection of specific service from Others list
    elif data.startswith("rangechkr_others_"):
        try:
            # Format: rangechkr_others_{idx}
            idx_str = data.split("_")[2]
            if idx_str.isdigit():
                idx = int(idx_str)
                discovered_services = context.user_data.get('rangechkr_discovered_services', [])
                if 0 <= idx < len(discovered_services):
                    service_name = discovered_services[idx]
                    logger.info(f"User selected service from Others list: {service_name} (index {idx})")
                    # Redirect to standard service handler
                    query.data = f"rangechkr_service_{service_name}"
                    await button_callback(update, context)
                    return
                else:
                    await query.edit_message_text("pe('❌') Service not found in session. Please reload.")
                    return
        except Exception as e:
            logger.error(f"Error handling others service selection: {e}")
            await query.edit_message_text("pe('❌') Error selecting service.")
            return
    
    # Range checker country selection
    elif data.startswith("rangechkr_country_"):
        parts = data.split("_", 3)
        if len(parts) < 4:
            await query.edit_message_text("pe('❌') Invalid selection.")
            return
            
        service_name = parts[2]
        country = parts[3]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("pe('❌') API connection error.")
            return
            
        await query.edit_message_text(f"pe('⏳') Loading ranges for {country}...")
        
        try:
            # Determine App ID
            app_id = resolve_app_id(service_name, context)
            if not app_id:
                app_id = service_name
            
            # Fetch ranges
            ranges = await run_api_call(api_client.get_ranges, app_id)
            
            # Filter by country
            filtered_ranges = []
            if ranges:
                for r in ranges:
                    range_name = r.get('name', r.get('id', ''))
                    r_country = r.get('cantryName', r.get('country', ''))
                    if not r_country or r_country == 'Unknown' or str(r_country).strip() == '':
                         r_country = detect_country_from_range(range_name)
                         if not r_country or r_country == 'Unknown':
                             range_str = str(range_name).upper()
                             for code, cname in COUNTRY_CODES.items():
                                 if code in range_str or cname.upper() in range_str:
                                     r_country = cname
                                     break
                    if not r_country: r_country = 'Unknown'
                    
                    if r_country == country:
                        filtered_ranges.append(r)
            
            if not filtered_ranges:
                await query.edit_message_text(f"pe('❌') No ranges found for {country}.")
                return
            
            # Create keyboard with filtered ranges
            keyboard = []
            if 'range_mapping' not in context.user_data:
                context.user_data['range_mapping'] = {}
            
            for i in range(0, len(filtered_ranges), 2):
                row = []
                range1 = filtered_ranges[i]
                range_name1 = range1.get('pattern', range1.get('name', ''))
                # Use range_id (which is now the pattern) as primary identifier
                range_id1 = range1.get('range_id') or range1.get('numerical_id') or range_name1
                range_id_field1 = range1.get('numerical_id') or range1.get('range_id') or ''
                actual_service = service_name # Use the service/app ID we are browsing
                
                range_hash1 = hashlib.md5(f"{actual_service}_{range_id1}".encode()).hexdigest()[:12]
                context.user_data['range_mapping'][range_hash1] = {
                    'service': actual_service,
                    'range_id': range_id1,
                    'range_name': range_name1,
                    'range_id_field': range_id_field1
                }
                display_name1 = range_name1[:20] + "..." if len(range_name1) > 20 else range_name1
                row.append(InlineKeyboardButton(display_name1, callback_data=f"rng_{range_hash1}", api_kwargs={"style": "primary"}))
                
                if i + 1 < len(filtered_ranges):
                    range2 = filtered_ranges[i + 1]
                    range_name2 = range2.get('pattern', range2.get('name', ''))
                    # Use range_id (which is now the pattern) as primary identifier
                    range_id2 = range2.get('range_id') or range2.get('numerical_id') or range_name2
                    range_id_field2 = range2.get('numerical_id') or range2.get('range_id') or ''
                    actual_service2 = service_name
                    
                    range_hash2 = hashlib.md5(f"{actual_service2}_{range_id2}".encode()).hexdigest()[:12]
                    context.user_data['range_mapping'][range_hash2] = {
                        'service': actual_service2,
                        'range_id': range_id2,
                        'range_name': range_name2,
                        'range_id_field': range_id_field2
                    }
                    display_name2 = range_name2[:20] + "..." if len(range_name2) > 20 else range_name2
                    row.append(InlineKeyboardButton(display_name2, callback_data=f"rng_{range_hash2}", api_kwargs={"style": "primary"}))
                
                keyboard.append(row)
            
            # Back Button
            if service_name.lower() in ['whatsapp', 'facebook']:
                 keyboard.append([InlineKeyboardButton("🔙 Countries", api_kwargs={"style": "danger"}, callback_data=f"rangechkr_service_{service_name}")])
            else:
                 # For Others, just go back to App List for now
                 keyboard.append([InlineKeyboardButton("🔙 Services", api_kwargs={"style": "danger"}, callback_data="rangechkr_service_others")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            
            display_service = service_name.upper() if service_name in ['whatsapp', 'facebook'] else service_name
            await query.edit_message_text(
                f"pe('📋') {display_service} - {country} ({len(filtered_ranges)} ranges):\nSelect a range:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in rangechkr_country: {e}")
            await query.edit_message_text(f"pe('❌') Error: {str(e)}")

    # Range checker service selection
    elif data.startswith("rangechkr_service_"):
        service_name = data.split("_", 2)[2]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("pe('❌') API connection error. Please try again.")
            return
        
        await query.edit_message_text("pe('⏳') Loading ranges...")
        
        try:
            # Handle "others" - first show dynamic service list
            # Handle "others" - first show dynamic service list (New Flow)
            if service_name == "others":
                await query.edit_message_text("pe('⏳') Discovering services (this may take a moment)...")
                try:
                    # Get ranges "others"
                    ranges = await run_api_call(api_client.get_ranges, "others")
                    
                    if not ranges:
                        await query.edit_message_text("pe('❌') No services found.")
                        return

                    # Aggregate by service
                    services_found = {} # {service_name: count}
                    for r in ranges:
                        svc = r.get('service', 'Other')
                        if not svc: svc = 'Other'
                        svc = str(svc).strip()
                        if svc == "": svc = "Other"
                        
                        if svc not in services_found:
                            services_found[svc] = 0
                        services_found[svc] += 1
                    
                    sorted_services = sorted(services_found.keys())
                    context.user_data['rangechkr_discovered_services'] = sorted_services
                    context.user_data['rangechkr_services_dict'] = services_found
                    
                    # Pagination: Show 90 services per page (leaving room for navigation buttons)
                    page = context.user_data.get('rangechkr_others_page', 0)
                    services_per_page = 90
                    total_pages = (len(sorted_services) + services_per_page - 1) // services_per_page
                    
                    start_idx = page * services_per_page
                    end_idx = min(start_idx + services_per_page, len(sorted_services))
                    page_services = sorted_services[start_idx:end_idx]
                    
                    keyboard = []
                    row = []
                    for idx in range(start_idx, end_idx):
                        svc = sorted_services[idx]
                        # Skip primary
                        if svc.lower() in ['whatsapp', 'facebook']: 
                            continue
                        
                        count = services_found[svc]
                        label = f"{svc} ({count})"
                        
                        # Callback: rangechkr_others_{idx}
                        row.append(InlineKeyboardButton(label, callback_data=f"rangechkr_others_{idx}", api_kwargs={"style": "primary"}))
                        
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
                    
                    if row:
                        keyboard.append(row)
                    
                    # Pagination buttons
                    if total_pages > 1:
                        nav_row = []
                        if page > 0:
                            nav_row.append(InlineKeyboardButton("◀️ Prev", api_kwargs={"style": "primary"}, callback_data="rangechkr_others_prev"))
                        nav_row.append(InlineKeyboardButton(f"Page {page + 1}/{total_pages}", callback_data="rangechkr_others_noop"))
                        if page < total_pages - 1:
                            nav_row.append(InlineKeyboardButton("Next ▶️", api_kwargs={"style": "primary"}, callback_data="rangechkr_others_next"))
                        keyboard.append(nav_row)
                    
                    keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="rangechkr_back_services")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    page_info = f" (Page {page + 1}/{total_pages})" if total_pages > 1 else ""
                    await query.edit_message_text(
                        f"pe('📋') Found {len(sorted_services)} Services{page_info}:\nShowing {len(page_services)} services", 
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error discovering services: {e}")
                    await query.edit_message_text(f"pe('❌') Error discovering services.")
                return
            else:
                # Handle specific services (WhatsApp, Facebook)
                app_id = resolve_app_id(service_name, context)
                if not app_id:
                    await query.edit_message_text("pe('❌') Invalid service.")
                    return

                ranges = await run_api_call(api_client.get_ranges, app_id)

                if not ranges or len(ranges) == 0:
                    await query.edit_message_text(f"pe('❌') No ranges found for {service_name.upper()}.")
                    return
            
            # Group ranges by country - detect from range name if country not available
            country_ranges = {}
            for r in ranges:
                range_name = r.get('name', r.get('id', ''))
                # Try to get country from API response first
                country = r.get('cantryName', r.get('country', ''))
                
                # If country not found or Unknown, detect from range name
                if not country or country == 'Unknown' or str(country).strip() == '':
                    country = detect_country_from_range(range_name)
                
                # Only use Unknown as last resort - try harder to detect
                if not country or country == 'Unknown':
                    range_str = str(range_name).upper()
                    for code, country_name in COUNTRY_CODES.items():
                        if code in range_str or country_name.upper() in range_str:
                            country = country_name
                            break
                
                # Final fallback
                if not country:
                    country = 'Unknown'
                
                country_ranges.setdefault(country, []).append(r)

            # Create country buttons - INLINE KEYBOARD
            keyboard = []
            country_list = [c for c in sorted(country_ranges.keys()) if c != 'Unknown']
            if 'Unknown' in country_ranges and len(country_list) == 0:
                country_list.append('Unknown')

            for i in range(0, len(country_list), 2):
                row = []
                flag1 = get_country_flag(country_list[i])
                row.append(InlineKeyboardButton(
                    f"{flag1} {country_list[i]}",
                    callback_data=f"rangechkr_country_{service_name}_{country_list[i]}"
                ))
                if i + 1 < len(country_list):
                    flag2 = get_country_flag(country_list[i + 1])
                    row.append(InlineKeyboardButton(
                        f"{flag2} {country_list[i + 1]}",
                        callback_data=f"rangechkr_country_{service_name}_{country_list[i + 1]}"
                    ))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔙 Services", api_kwargs={"style": "danger"}, callback_data="rangechkr_back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            display_service_name = "Others" if service_name == "others" else service_name.upper()
            await query.edit_message_text(
                f"pe('📋') {display_service_name} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error loading ranges: {e}")
            await query.edit_message_text(f"pe('❌') Error loading ranges: {str(e)}")
    
    # Range checker range selection (using hash)
    elif data.startswith("rng_"):
        range_hash = data.split("_", 1)[1]
        
        # Retrieve range info from context
        logger.info(f"Range hash received: {range_hash}, user_data keys: {list(context.user_data.keys())}")
        if 'range_mapping' not in context.user_data:
            logger.error(f"range_mapping not found in user_data for user {user_id}")
            await query.edit_message_text("pe('❌') Range mapping not found. Please select range again from /rangechkr.")
            return
        
        if range_hash not in context.user_data['range_mapping']:
            logger.error(f"Range hash {range_hash} not found in mapping. Available hashes: {list(context.user_data['range_mapping'].keys())}")
            await query.edit_message_text("pe('❌') Range not found. Please select range again from /rangechkr.")
            return
        
        range_info = context.user_data['range_mapping'][range_hash]
        service_name = range_info['service']
        range_id = range_info['range_id']
        range_name = range_info.get('range_name', range_id)
        range_id_field = range_info.get('range_id_field', '')
        
        logger.info(f"Retrieved range: service={service_name}, range_id={range_id}, range_name={range_name}, range_id_field={range_id_field}")
        
        # Delete old message and send new one at the bottom as requested
        try:
            await query.message.delete()
        except Exception as e:
            logger.debug(f"Could not delete message: {e}")
        
        sent_loading_msg = await context.bot.send_message(
            chat_id=user_id,
            text="pe('⏳') Requesting numbers from range..."
        )
        loading_message_id = sent_loading_msg.message_id
        try:
            await query.answer()
        except Exception as e:
            logger.debug(f"Callback query answer failed: {e}")
        
        # Request 5 numbers in background
        async def fetch_and_send_range_numbers():
            try:
                logger.info(f"Fetching numbers for range_id: {range_id}")
                api_client = get_global_api_client()
                if not api_client:
                    logger.error("API client not available")
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text="pe('❌') API connection error. Please try again."
                    )
                    return
                
                # Get user's number count preference
                session = get_user_session(user_id)
                number_count = session.get('number_count', 2) if session else 2
                
                # with api_lock:
                logger.info(f"Calling get_multiple_numbers with range_name={range_name}, range_id={range_id}, count={number_count}")
                # Try range_name first, then range_id (like otp_tool.py)
                numbers_data = await run_api_call(api_client.get_multiple_numbers, range_id, range_name, number_count)
                logger.info(f"get_multiple_numbers returned {len(numbers_data) if numbers_data else 0} item(s)")
                
                if not numbers_data or len(numbers_data) == 0:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text="pe('❌') Failed to get numbers from this range. Please try again."
                    )
                    return
                
                # Extract numbers
                numbers_list = []
                for num_data in numbers_data:
                    if isinstance(num_data, dict):
                        number = num_data.get('number', '')
                        if not number:
                            # Try alternative keys
                            number = num_data.get('num', '')
                        if number:
                            numbers_list.append(str(number))
                    elif isinstance(num_data, str):
                        numbers_list.append(num_data)
                
                if not numbers_list:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text="pe('❌') No valid numbers received. Please try again."
                    )
                    return
                
                # Get service info
                app_id = resolve_app_id(service_name, context)
                if not app_id:
                    logger.error(f"Invalid service_name in range selection: {service_name}")
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text=f"pe('❌') Invalid service: {service_name}"
                    )
                    return
                
                # Detect country from range
                country_name = None
                if numbers_list:
                    # Try to detect country from first number
                    first_num = numbers_list[0].replace('+', '').replace(' ', '').replace('-', '')
                    for code_len in [3, 2, 1]:
                        if len(first_num) >= code_len:
                            code = first_num[:code_len]
                            if code in COUNTRY_CODES:
                                country_name = COUNTRY_CODES[code]
                                break
                
                # Create inline keyboard with numbers (click-to-copy)
                # Remove callback_data to allow copy_text to work properly
                keyboard = []
                formatted_numbers = []
                for num in numbers_list:
                    display_num = str(num)
                    if not display_num.startswith('+'):
                        digits_only = ''.join(filter(str.isdigit, display_num))
                        display_num = '+' + (digits_only if digits_only else display_num)
                    formatted_numbers.append(display_num)
                    # Use copy_text via api_kwargs - no callback_data needed for copy
                    keyboard.append([InlineKeyboardButton(
                        f"pe('📱') {display_num}",
                        api_kwargs={"copy_text": {"text": display_num}}
                    )])
                
                # Use hash for change numbers button too
                if 'range_mapping' not in context.user_data:
                    context.user_data['range_mapping'] = {}
                change_hash = hashlib.md5(f"{service_name}_{range_id}_{range_name}".encode()).hexdigest()[:12]
                context.user_data['range_mapping'][change_hash] = {
                    'service': service_name, 
                    'range_id': range_id,
                    'range_name': range_name
                }
                keyboard.append([InlineKeyboardButton("pe('🔄') Change Numbers", callback_data=f"rng_{change_hash}", api_kwargs={"style": "success"})])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Get country flag
                country_flag = get_country_flag(country_name) if country_name else "🌍"
                
                # Get service icon
                service_icons = {
                    "whatsapp": "pe('💬')",
                    "facebook": "👥",
                    "telegram": "pe('✈️')"
                }
                service_icon = service_icons.get(service_name, "pe('📱')")
                
                message_text = f"{service_icon} {service_name.upper()}\n"
                if country_name:
                    message_text += f"{country_flag} {country_name}\n"
                message_text += f"pe('📋') Range: {range_name}\n\n"
                message_text += f"pe('✅') {len(numbers_list)} numbers received:\n\n"
                message_text += "Tap a number to copy it."
                
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=loading_message_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
                
                # Store numbers and start monitoring
                update_user_session(user_id, service=service_name, range_id=range_id, number=','.join(formatted_numbers), monitoring=1)
                
                # Start OTP monitoring job
                if user_id in user_jobs:
                    try:
                        old_job = user_jobs[user_id]
                        old_job.schedule_removal()
                    except Exception as e:
                        logger.error(f"Error cancelling old job: {e}")
                
                job = context.job_queue.run_repeating(
                    monitor_otp,
                    interval=BOT_CONFIG['poll_interval'],
                    first=1,
                    chat_id=user_id,
                    data={'numbers': formatted_numbers, 'user_id': user_id, 'country': country_name, 'service': service_name, 'start_time': time.time(), 'message_id': loading_message_id}
                )
                user_jobs[user_id] = job
                
            except Exception as e:
                logger.error(f"Error fetching range numbers: {e}")
                import traceback
                logger.error(traceback.format_exc())
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=loading_message_id,
                        text=f"pe('❌') Error: {str(e)}\n\nRange ID: {range_id}\nService: {service_name}"
                    )
                except:
                    pass
        
        # Run async task
        import asyncio
        asyncio.create_task(fetch_and_send_range_numbers())
    
    # Range checker back to services
    elif data == "rangechkr_back_services":
        keyboard = [
            [InlineKeyboardButton("pe('💬') WhatsApp", callback_data="rangechkr_service_whatsapp", api_kwargs={"style": "success"})],
            [InlineKeyboardButton("👥 Facebook", callback_data="rangechkr_service_facebook", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("pe('✈️') Telegram", callback_data="rangechkr_service_telegram", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("pe('✨') Others", callback_data="rangechkr_service_others", api_kwargs={"style": "danger"})]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🧭 Range Explorer\nSelect a service:",
            reply_markup=reply_markup
        )
    
    # Back to services
    elif data == "back_services":
        keyboard = [
            [InlineKeyboardButton("pe('💬') WhatsApp", callback_data="service_whatsapp", api_kwargs={"style": "success"})],
            [InlineKeyboardButton("👥 Facebook", callback_data="service_facebook", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("pe('✈️') Telegram", callback_data="service_telegram", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("pe('✨') Others", callback_data="service_others", api_kwargs={"style": "danger"})]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "pe('🎯') Select a service:",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (keyboard button presses)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await update.message.reply_text("pe('❌') Your access is pending approval.")
        return
    
    # Handle "Get Number" button
    if text in ("Get Number", "📲 Get Number", "pe('🚀') Get Number"):
        keyboard = [
            [InlineKeyboardButton("pe('💬') WhatsApp", callback_data="service_whatsapp", api_kwargs={"style": "success"})],
            [InlineKeyboardButton("👥 Facebook", callback_data="service_facebook", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("pe('✈️') Telegram", callback_data="service_telegram", api_kwargs={"style": "primary"})],
            [InlineKeyboardButton("pe('✨') Others", callback_data="service_others", api_kwargs={"style": "danger"})]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "pe('🎯') Select a service:",
            reply_markup=reply_markup
        )
        return
    
    # Handle "Set Number Count" button
    if text in ("Set Number Count", "🧮 Set Number Count", "pe('⚙️') Number Count", "pe('🎛') Number Count", "Number Count"):
        # Get current count
        session = get_user_session(user_id)
        current_count = session.get('number_count', 2) if session else 2
        
        keyboard = [
            [InlineKeyboardButton("1", callback_data="set_count_1"),
             InlineKeyboardButton("2", callback_data="set_count_2"),
             InlineKeyboardButton("3", callback_data="set_count_3")],
            [InlineKeyboardButton("4", callback_data="set_count_4"),
             InlineKeyboardButton("5", callback_data="set_count_5")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Numbers per request\n\n"
            f"Current setting: {current_count} number(s)",
            reply_markup=reply_markup
        )
        return
    
    # Handle "My Stats" button
    if text in ("My Stats", "pe('📊') My Stats", "pe('📈') My Stats"):
        today_count = get_today_otp_count(user_id)
        bd_now = get_bd_now()
        await update.message.reply_text(
            "My Stats\n\n"
            f"🕒 BD time now: {bd_now.strftime('%Y-%m-%d %I:%M:%S %p')}\n"
            f"pe('✅') Today you received: {today_count} OTP(s)."
        )
        return
    
    # Handle service selection (old format - for backward compatibility)
    if text in ["pe('💬') WhatsApp", "👥 Facebook", "pe('✈️') Telegram", "🟢 WhatsApp", "🔵 Facebook", "🛩 Telegram", "WhatsApp", "Facebook", "Telegram"]:
        service_map = {
            "pe('💬') WhatsApp": "whatsapp",
            "👥 Facebook": "facebook",
            "pe('✈️') Telegram": "telegram",
            "🟢 WhatsApp": "whatsapp",
            "🔵 Facebook": "facebook",
            "🛩 Telegram": "telegram",
            "WhatsApp": "whatsapp",
            "Facebook": "facebook",
            "Telegram": "telegram"
        }
        service_name = service_map[text]
        app_id_map = {
            "whatsapp": "verifyed-access-whatsapp",
            "facebook": "verifyed-access-facebook",
            "telegram": "verifyed-access-telegram"
        }
        app_id = app_id_map.get(service_name)
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await update.message.reply_text("pe('❌') API connection error. Please try again.")
            return
        
        try:
            ranges = await run_api_call(api_client.get_ranges, app_id)
            
            if not ranges:
                await update.message.reply_text(f"pe('❌') No active ranges available for {service_name}.")
                return
            
            # Group ranges by country - detect from range name
            country_ranges = {}
            for r in ranges:
                range_name = r.get('name', r.get('id', ''))
                country = r.get('cantryName', r.get('country', ''))
                
                # If country not found or Unknown, detect from range name
                if not country or country == 'Unknown' or country.strip() == '':
                    country = detect_country_from_range(range_name)
                
                # Only use Unknown as last resort - try harder to detect
                if not country or country == 'Unknown':
                    # Try to extract from range name more aggressively
                    range_str = str(range_name).upper()
                    # Sometimes range name contains country code in different format
                    for code, country_name in COUNTRY_CODES.items():
                        if code in range_str or country_name.upper() in range_str:
                            country = country_name
                            break
                
                # Final fallback - use detected or keep as Unknown
                if not country:
                    country = 'Unknown'
                
                if country not in country_ranges:
                    country_ranges[country] = []
                country_ranges[country].append(r)
            
            # Create country buttons - INLINE KEYBOARD
            keyboard = []
            # Filter out Unknown countries - try to detect them first
            country_list = []
            for country in sorted(country_ranges.keys()):
                if country != 'Unknown':
                    country_list.append(country)
            
            # Only add Unknown if we really can't detect any country
            if 'Unknown' in country_ranges and len(country_list) == 0:
                country_list.append('Unknown')
            
            # Create inline keyboard rows (2 buttons per row)
            for i in range(0, len(country_list), 2):
                row = []
                flag1 = get_country_flag(country_list[i])
                row.append(InlineKeyboardButton(f"{flag1} {country_list[i]}", callback_data=f"country_{service_name}_{country_list[i]}"))
                if i + 1 < len(country_list):
                    flag2 = get_country_flag(country_list[i + 1])
                    row.append(InlineKeyboardButton(f"{flag2} {country_list[i + 1]}", callback_data=f"country_{service_name}_{country_list[i + 1]}"))
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"pe('📱') {service_name.upper()} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in handle_message service selection: {e}")
            await update.message.reply_text(f"pe('❌') Error: {str(e)}")
    
    # Handle direct range input (e.g., "24491501XXX" or "24491501")
    elif re.match(r'^[\dXx]+$', text) and len(text) >= 6:
        # Direct range buy: always use WhatsApp without active-range lookup.
        range_pattern = text.upper()
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await update.message.reply_text("pe('❌') API connection error. Please try again.")
            return

        found_service = "whatsapp"
        range_name = range_pattern
        range_id = range_pattern
        await update.message.reply_text("pe('⏳') Buying directly via WhatsApp...")
        
        try:
            # Get user's number count preference
            session = get_user_session(user_id)
            number_count = session.get('number_count', 2) if session else 2
            
            # Try range_name first, then range_id (like otp_tool.py)
            numbers_data = await run_api_call(api_client.get_multiple_numbers, range_id, range_name, number_count)

            # If user typed digits-only range, retry once with XXX suffix.
            if (not numbers_data or len(numbers_data) == 0) and 'X' not in range_pattern:
                range_name = f"{range_pattern}XXX"
                range_id = range_name
                numbers_data = await run_api_call(api_client.get_multiple_numbers, range_id, range_name, number_count)
            
            if not numbers_data or len(numbers_data) == 0:
                await update.message.reply_text("pe('❌') Failed to get numbers from this range. Please try again.")
                return
            
            # Extract numbers
            numbers_list = []
            for num_data in numbers_data:
                number = num_data.get('number', '')
                if number:
                    numbers_list.append(number)
            
            if not numbers_list:
                await update.message.reply_text("pe('❌') No valid numbers received. Please try again.")
                return
            
            # Detect country from first number
            country_name = None
            if numbers_list:
                first_num = numbers_list[0].replace('+', '').replace(' ', '').replace('-', '')
                for code_len in [3, 2, 1]:
                    if len(first_num) >= code_len:
                        code = first_num[:code_len]
                        if code in COUNTRY_CODES:
                            country_name = COUNTRY_CODES[code]
                            break
            
            # Create inline keyboard with numbers (click-to-copy)
            # Remove callback_data to allow copy_text to work properly
            keyboard = []
            for num in numbers_list:
                display_num = num
                if not display_num.startswith('+'):
                    digits_only = ''.join(filter(str.isdigit, display_num))
                    if len(digits_only) >= 10:
                        display_num = '+' + digits_only
                    else:
                        display_num = '+' + display_num
                # Use copy_text via api_kwargs - no callback_data needed for copy
                keyboard.append([InlineKeyboardButton(
                    f"pe('📱') {display_num}",
                    api_kwargs={"copy_text": {"text": display_num}}
                )])
            
            # Use hash for change numbers button
            if 'range_mapping' not in context.user_data:
                context.user_data['range_mapping'] = {}
            # For direct input, range_name is same as range_id usually
            range_name = range_id 
            change_hash = hashlib.md5(f"{found_service}_{range_id}_{range_name}".encode()).hexdigest()[:12]
            context.user_data['range_mapping'][change_hash] = {
                'service': found_service, 
                'range_id': range_id,
                'range_name': range_name
            }
            keyboard.append([InlineKeyboardButton("pe('🔄') Change Numbers", callback_data=f"rng_{change_hash}", api_kwargs={"style": "success"})])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Get country flag
            country_flag = get_country_flag(country_name) if country_name else "🌍"
            
            # Get service icon
            service_icons = {
                "whatsapp": "pe('💬')",
                "facebook": "👥",
                "telegram": "pe('✈️')"
            }
            service_icon = service_icons.get(found_service, "pe('📱')")
            
            message_text = f"{service_icon} {found_service.upper()}\n"
            if country_name:
                message_text += f"{country_flag} {country_name}\n"
            message_text += f"pe('📋') Range: {range_id}\n\n"
            message_text += f"pe('✅') {len(numbers_list)} numbers received:\n\n"
            message_text += "Tap a number to copy it."
            
            sent_msg = await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
            
            # Store numbers and start monitoring
            update_user_session(user_id, service=found_service, range_id=range_id, number=','.join(numbers_list), monitoring=1)
            
            # Start OTP monitoring job
            if user_id in user_jobs:
                try:
                    old_job = user_jobs[user_id]
                    old_job.schedule_removal()
                except Exception as e:
                    logger.debug(f"Error removing old job in handle_direct_range_input: {e}")
            
            # Add country to job data if available
            # Store start_time in variable first to avoid scope issues
            start_time_value = time.time()
            job_data = {
                'user_id': user_id,
                'numbers': numbers_list,
                'service': found_service,
                'range_id': range_id,
                'start_time': start_time_value,
                'message_id': sent_msg.message_id
            }
            if country_name:
                job_data['country'] = country_name
            
            job = context.job_queue.run_repeating(
                monitor_otp,
                interval=3,
                first=5,
                data=job_data
            )
            user_jobs[user_id] = job
            
        except Exception as e:
            logger.error(f"Error handling direct range input: {e}", exc_info=True)
            error_msg = str(e)
            # Check if it's the time variable error
            if "cannot access local variable 'time'" in error_msg:
                error_msg = "Internal error occurred. Please try again."
            await update.message.reply_text(f"pe('❌') Error: {error_msg}")
    
    # Handle country selection (old format - for backward compatibility)
    elif any(text.startswith(f) for f in ["pe('🇦🇴')", "pe('🇰🇲')", "pe('🇷🇴')", "pe('🇩🇰')", "pe('🇧🇩')", "pe('🇮🇳')", "pe('🇺🇸')", "pe('🇬🇧')", "🌍"]) or "🔙" in text or "Back" in text:
        if "Back" in text:
            keyboard = [
                [KeyboardButton("pe('🚀') Get Number", api_kwargs={"style": "success"})],
                [KeyboardButton("pe('🎛') Number Count", api_kwargs={"style": "primary"})],
                [KeyboardButton("pe('📈') My Stats", api_kwargs={"style": "primary"})]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(
                "pe('✨') Ready when you are. Tap pe('🚀') Get Number to start.",
                reply_markup=reply_markup
            )
            return
        
        # Extract country name from button text (remove flag)
        country = re.sub(r'^[🇦-🇿\s]+', '', text).strip()
        
        # Get service from user session
        session = get_user_session(user_id)
        service_name = session.get('service') if session else None
        
        if not service_name:
            # Try to detect - for now default to whatsapp
            service_name = "whatsapp"
        
        app_id = resolve_app_id(service_name, context)
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await update.message.reply_text("pe('❌') API connection error. Please try again.")
            return
        
        try:
            ranges = await run_api_call(api_client.get_ranges, app_id)
            
            # Find ranges for this country - collect all matching ranges first
            # Match by detecting country from range name, not just API country field
            matching_ranges = []
            for r in ranges:
                range_name = r.get('name', r.get('id', ''))
                r_country_api = r.get('cantryName', r.get('country', ''))
                is_match = False
                
                # Try API country first (case-insensitive)
                if r_country_api and r_country_api.lower() == country.lower():
                    is_match = True
                
                # Detect country from range name
                if not is_match:
                    r_country_detected = detect_country_from_range(range_name)
                    if r_country_detected and r_country_detected.lower() == country.lower():
                        is_match = True
                
                # Also try more aggressive detection if needed
                if not is_match:
                    range_str = str(range_name).upper()
                    for code, country_name in COUNTRY_CODES.items():
                        if code in range_str and country_name.lower() == country.lower():
                            is_match = True
                            break
                
                if is_match:
                    matching_ranges.append(r)
            
            # Sort ranges for Ivory Coast (22507 priority)
            if matching_ranges:
                matching_ranges = sort_ranges_for_ivory_coast(matching_ranges)
                selected_range = matching_ranges[0]  # Use first (priority) range
            else:
                selected_range = None
            
            if not selected_range:
                await update.message.reply_text(f"pe('❌') No ranges found for {country}.")
                return
            
            range_id = selected_range.get('name', selected_range.get('id', ''))
            range_name = selected_range.get('name', '')
            
            # Get user's number count preference
            session = get_user_session(user_id)
            number_count = session.get('number_count', 2) if session else 2
            
            # Request numbers
            await update.message.reply_text(f"pe('⏳') Requesting {number_count} number(s)...")
            
            # Try range_name first, then range_id (like otp_tool.py)
            numbers_data = await run_api_call(api_client.get_multiple_numbers, range_id, range_name, number_count)
            
            if not numbers_data or len(numbers_data) == 0:
                await update.message.reply_text("pe('❌') Failed to get numbers. Please try again.")
                return
            
            # Extract numbers and store them
            numbers_list = []
            for num_data in numbers_data:
                number = num_data.get('number', '')
                if number:
                    numbers_list.append(number)
            
            if not numbers_list:
                await update.message.reply_text("pe('❌') No valid numbers received. Please try again.")
                return
            
            country_name = numbers_data[0].get('cantryName', numbers_data[0].get('country', country))
            
            # Sort numbers for Ivory Coast (22507 priority)
            numbers_list = sort_numbers_for_ivory_coast(numbers_list, country_name)
            
            # Store all numbers in session (comma-separated)
            numbers_str = ','.join(numbers_list)
            update_user_session(user_id, service_name, country, range_id, numbers_str, 1)
            
            # Create inline keyboard with 5 numbers (click to copy supported via <code> tag)
            keyboard = []
            for i, num in enumerate(numbers_list, 1):
                # Format number for display (ensure + prefix as requested)
                display_num = num
                if not display_num.startswith('+'):
                    digits_only = ''.join(filter(str.isdigit, display_num))
                    display_num = '+' + (digits_only if digits_only else display_num)
                # Use copy_text via api_kwargs - Telegram Bot API 7.0+ feature
                # Format: {"copy_text": {"text": "number"}} - clicking button will copy the number directly
                keyboard.append([InlineKeyboardButton(f"pe('📱') {display_num}", api_kwargs={"copy_text": {"text": display_num}})])
            
            # Get country flag
            country_flag = get_country_flag(country_name)
            
            # Get service icon
            service_icons = {
                "whatsapp": "pe('💬')",
                "facebook": "👥",
                "telegram": "pe('✈️')"
            }
            service_icon = service_icons.get(service_name, "pe('📱')")
            
            keyboard.append([InlineKeyboardButton("pe('🔄') Next Number", callback_data=f"country_{service_name}_{country_name}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", api_kwargs={"style": "danger"}, callback_data="back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Format message like the reference image
            message = f"Country: {country_flag} {country_name}\n"
            message += f"Service: {service_icon} {service_name.capitalize()}\n"
            message += f"Waiting for OTP...... pe('⏳')"
            
            sent_msg = await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

            # Start monitoring all numbers in background - move after sent_msg to have message_id
            job = context.job_queue.run_repeating(
                monitor_otp,
                interval=2,
                first=2,
                chat_id=user_id,
                data={'numbers': numbers_list, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time(), 'message_id': sent_msg.message_id}
            )
            user_jobs[user_id] = job
        except Exception as e:
            logger.error(f"Error in handle_message country selection: {e}")
            await update.message.reply_text(f"pe('❌') Error: {str(e)}")

async def monitor_otp(context: ContextTypes.DEFAULT_TYPE):
    """Monitor OTP in background for multiple numbers - continues until all numbers receive OTP"""
    job = context.job
    job_data = job.data if hasattr(job, 'data') else {}
    # Get user_id from job_data first (always set), fallback to job.chat_id
    user_id = job_data.get('user_id') or job.chat_id
    start_time = job_data.get('start_time', time.time())
    message_id = job_data.get('message_id')  # Get message_id for editing
    
    # Validate user_id
    if not user_id:
        logger.error(f"pe('❌') monitor_otp: user_id is None! job_data: {job_data}, job.chat_id: {job.chat_id}")
        return  # Can't proceed without user_id
    
    # Track which numbers have already received OTP
    received_otps = job_data.get('received_otps', {})  # {number: True}
    
    # Support both single number (backward compatibility) and multiple numbers
    if 'numbers' in job_data:
        numbers = job_data['numbers']
    elif 'number' in job_data:
        numbers = [job_data['number']]
    else:
        return
    
    # Timeout after 15 minutes
    if time.time() - start_time > 900:  # 15 minutes = 900 seconds
        try:
            job.schedule_removal()
        except:
            pass
        if user_id in user_jobs:
            del user_jobs[user_id]
        update_user_session(user_id, monitoring=0)
        try:
            # Keep the same numbers visible and mark unresolved numbers as expired.
            service_name = str(job_data.get('service') or 'Unknown')
            country_name = str(job_data.get('country') or 'Unknown')
            range_id = str(job_data.get('range_id') or '').strip()

            service_icons = {
                "whatsapp": "pe('💬')",
                "facebook": "👥",
                "telegram": "pe('✈️')"
            }
            service_icon = service_icons.get(service_name, "pe('📱')")
            country_flag = get_country_flag(country_name) if country_name and country_name != 'Unknown' else "🌍"

            keyboard = []
            status_lines = []
            for num in numbers:
                status_label = "OTP" if num in received_otps else "Expired"
                button_label = f"pe('📱') {num} ({status_label})"
                keyboard.append([InlineKeyboardButton(
                    button_label,
                    api_kwargs={"copy_text": {"text": num}}
                )])
                status_lines.append(f"{num} - {status_label}")

            timeout_text = f"{service_icon} {service_name.upper()}\n"
            if country_name and country_name != 'Unknown':
                timeout_text += f"{country_flag} {country_name}\n"
            if range_id:
                timeout_text += f"pe('📋') Range: {range_id}\n"
            timeout_text += "\n⏱️ Timeout! No OTP received within 15 minutes.\n\n"
            timeout_text += "Number status:\n" + "\n".join(status_lines)

            timeout_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            # Edit the existing message instead of sending a new one
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=timeout_text,
                    reply_markup=timeout_markup
                )
            else:
                # Fallback to sending new message if message_id not available
                await context.bot.send_message(
                    chat_id=user_id,
                    text=timeout_text,
                    reply_markup=timeout_markup
                )
        except Exception as e:
            logger.error(f"Error updating timeout message: {e}")
        return
    
    # Get global API client
    api_client = get_global_api_client()
    if not api_client:
        return
    
    try:
        # Check OTP for all numbers in one batch call - much faster (no lag)
        # Use timeout to prevent hanging
        try:
            # We don't use api_lock here anymore to allow high concurrency
            # The APIClient.login method is now internally thread-safe
            otp_results = await run_api_call(api_client.check_otp_batch, numbers)
        except Exception as api_error:
            logger.error(f"API error in check_otp_batch: {api_error}")
            return  # Skip this check, will retry next interval
        
        # Process results for each number
        for number in numbers:
            otp_data = otp_results.get(number)
            
            if not otp_data:
                continue  # No OTP data for this number yet
            
            # Handle list response (shouldn't happen with batch, but keep for safety)
            if isinstance(otp_data, list):
                # Find the specific number in the list
                target_normalized = number.replace('+', '').replace(' ', '').replace('-', '').strip()
                target_digits = ''.join(filter(str.isdigit, target_normalized))
                
                found_num_data = None
                for num in otp_data:
                    if isinstance(num, dict):
                        num_value = num.get('number', '')
                        num_normalized = num_value.replace('+', '').replace(' ', '').replace('-', '').strip()
                        # Try exact match first
                        if num_normalized == target_normalized:
                            found_num_data = num
                            break
                        # Try last 9 digits match
                        elif len(target_digits) >= 9:
                            num_digits = ''.join(filter(str.isdigit, num_value))
                            if len(num_digits) >= 9 and num_digits[-9:] == target_digits[-9:]:
                                found_num_data = num
                                break
                
                if found_num_data:
                    otp_data = found_num_data
                else:
                    # Number not found in list yet, continue to next number
                    continue
            
            if otp_data and isinstance(otp_data, dict):
                # Get OTP - directly from 'otp' field first
                otp_raw = otp_data.get('otp')
                sms_content = otp_data.get('sms_content', '')
                status = otp_data.get('status', '')
                
                # Convert OTP to string - Enhanced OTP extraction (multiple patterns)
                otp = ''
                if otp_raw is not None and otp_raw != '':
                    otp = str(otp_raw).strip()
                    logger.info(f"OTP from raw field for {number}: {otp}")
                elif sms_content:
                    # Extract OTP from SMS content - try multiple patterns
                    # Pattern 1: 123-456 or 12345678 format (most common)
                    otp_match = re.search(r'(\d{3,6}-?\d{3,6})', sms_content)
                    if otp_match:
                        otp = otp_match.group(1).replace('-', '').strip()
                        logger.info(f"OTP extracted (pattern 1) for {number}: {otp}")
                    else:
                        # Pattern 2: 4-8 digit standalone number
                        otp_match = re.search(r'\b(\d{4,8})\b', sms_content)
                        if otp_match:
                            otp = otp_match.group(1).strip()
                            logger.info(f"OTP extracted (pattern 2) for {number}: {otp}")
                        else:
                            # Pattern 3: Any 3+ digit sequence (last resort)
                            otp_match = re.search(r'(\d{3,})', sms_content)
                            if otp_match:
                                potential_otp = otp_match.group(1).strip()
                                # Filter out very long numbers (likely not OTP)
                                if len(potential_otp) <= 8:
                                    otp = potential_otp
                                    logger.info(f"OTP extracted (pattern 3) for {number}: {otp}")
                
                # Additional debug logging
                if otp:
                    logger.info(f"pe('✅') OTP detected for {number}: {otp}")
                elif sms_content:
                    logger.debug(f"⚠️ SMS content found but no OTP extracted: {sms_content[:100]}")
                elif status:
                    logger.debug(f"Status: {status}, No OTP data yet for {number}")
                
                if otp:
                    # Check if we already sent OTP for this number (avoid duplicates)
                    if number in received_otps:
                        continue  # Already sent OTP for this number, skip
                    
                    # Mark this number as received OTP
                    received_otps[number] = True
                    job_data['received_otps'] = received_otps  # Update job data
                    
                    # Record this number as used (no reuse for 24 hours)
                    add_used_number(number)
                    
                    # Get country and service info from job data (most reliable) or session
                    session = get_user_session(user_id)
                    
                    # Try to get country from job data first (most reliable), then session
                    country = job_data.get('country') if job_data else None
                    if not country and session:
                        country = session.get('country')
                    
                    # Try to get service from job data first, then session
                    service = job_data.get('service') if job_data else None
                    if not service and session:
                        service = session.get('service')
                    
                    # Handle None values
                    if not country:
                        country = 'Unknown'
                    if not service:
                        service = 'Unknown'
                    
                    # Format number for display (ensure + prefix as requested)
                    display_number = number
                    if not display_number.startswith('+'):
                        digits_only = ''.join(filter(str.isdigit, display_number))
                        display_number = '+' + (digits_only if digits_only else display_number)

                    # Get country flag and code
                    country_flag = get_country_flag(country)
                    country_code = get_country_code(country)

                    # Detect language from SMS content
                    language = detect_language_from_sms(sms_content) if sms_content else 'English'
                    motivation_line = html.escape(get_random_bn_otp_motivation())

                    # Format OTP message for USER: "pe('🇩🇰') #DK WhatsApp <code>4540797881</code> English"
                    # Use <code> tag for click-to-copy (Telegram default format)
                    user_otp_msg = (
                        f"{country_flag} #{country_code} {service.capitalize()} <code>{display_number}</code> {language}\n\n"
                        f"<b>আজকের প্রেরণা:</b> {motivation_line}"
                    )

                    # Format OTP message for CHANNEL: "pe('🇩🇰') #DK WhatsApp 4540XXXX81 English"
                    # Mask number for channel (middle digits with XXXX)
                    masked_number = mask_number(display_number)
                    if not masked_number.startswith('+'):
                         masked_number = '+' + masked_number
                    channel_otp_msg = f"{country_flag} #{country_code} {service.capitalize()} {masked_number} {language}"
                    
                    # Build deep-link URL for the "Range" button (channel only)
                    range_for_button = None
                    if job_data:
                        range_for_button = job_data.get('range_id')
                    if not range_for_button and session:
                        range_for_button = session.get('range_id')
                    if not range_for_button:
                        range_for_button = infer_range_from_number(number)
                    if range_for_button and job_data and not job_data.get('range_id'):
                        job_data['range_id'] = range_for_button

                    range_url = await build_range_deeplink(context, range_for_button, service)

                    # User keyboard keeps only OTP copy.
                    user_keyboard = [[InlineKeyboardButton(f"pe('🔐') {otp}", api_kwargs={"copy_text": {"text": otp}})]]
                    user_reply_markup = InlineKeyboardMarkup(user_keyboard)

                    # Channel keyboard: OTP copy + Range button side by side.
                    channel_row = [InlineKeyboardButton(f"pe('🔐') {otp}", api_kwargs={"copy_text": {"text": otp}})]
                    if range_url:
                        channel_row.append(InlineKeyboardButton("Range", url=range_url))
                    channel_reply_markup = InlineKeyboardMarkup([channel_row])
                    
                    # Send OTP message to user FIRST (important!)
                    user_message_sent = False
                    try:
                        logger.info(f"Attempting to send OTP to user {user_id} for number {number}: {otp}")
                        sent_msg = await context.bot.send_message(
                            chat_id=user_id,
                            text=user_otp_msg,
                            reply_markup=user_reply_markup,
                            parse_mode='HTML'
                        )
                        user_message_sent = True
                        logger.info(f"pe('✅') OTP message sent successfully to user {user_id} (message_id: {sent_msg.message_id}) for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"❌ Error sending OTP message to user {user_id}: {type(e).__name__}: {e}")
                        logger.error(f"   OTP was: {otp}, Number: {number}, Message: {user_otp_msg}")
                        # Still try to send to channel even if user message fails
                    
                    # Send OTP message to channel (with masked number)
                    try:
                        await context.bot.send_message(
                            chat_id=OTP_CHANNEL_ID,
                            text=channel_otp_msg,
                            reply_markup=channel_reply_markup,
                            parse_mode='HTML'
                        )
                        logger.info(f"pe('✅') OTP forwarded to channel {OTP_CHANNEL_ID} for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"❌ Error sending OTP message to channel {OTP_CHANNEL_ID}: {type(e).__name__}: {e}")
                    
                    # Log warning if user message failed but channel succeeded
                    if not user_message_sent:
                        logger.warning(f"⚠️ OTP sent to channel but NOT to user {user_id} for {number}: {otp}")
                    
                    # Increment per-day OTP counter (BD time)
                    increment_otp_count(user_id)

                    # Check if all numbers have received OTP
                    all_received = all(num in received_otps for num in numbers)
                    if all_received:
                        # All numbers received OTP, stop monitoring
                        logger.info(f"pe('✅') All numbers received OTP for user {user_id}, stopping monitoring")
                        try:
                            job.schedule_removal()
                        except:
                            pass
                        if user_id in user_jobs:
                            del user_jobs[user_id]
                        update_user_session(user_id, monitoring=0)
                        return
                    # Otherwise, continue monitoring for remaining numbers
    except Exception as e:
        logger.error(f"Error monitoring OTP for user {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

async def monitor_console_logs(context: ContextTypes.DEFAULT_TYPE):
    """Monitor masked console OTP stream and forward unique new entries to channel."""
    global console_bootstrapped

    api_client = get_global_api_client()
    if not api_client:
        return

    try:
        logs = await run_api_call(api_client.get_console_logs)
        if not logs:
            return

        normalized_logs = []
        for item in logs:
            if not isinstance(item, dict):
                continue

            raw_id = item.get('id')
            log_id = None
            if raw_id is not None:
                try:
                    log_id = int(raw_id)
                except (TypeError, ValueError):
                    log_id = None

            if log_id is not None:
                log_key = f"id:{log_id}"
            else:
                fallback = f"{item.get('time','')}|{item.get('number','')}|{item.get('app_name','')}|{item.get('sms','')}"
                log_key = f"sig:{hashlib.md5(fallback.encode('utf-8')).hexdigest()}"

            normalized_logs.append((log_id, log_key, item))

        if not normalized_logs:
            return

        with console_lock:
            if not console_bootstrapped:
                for _, key, _ in normalized_logs:
                    remember_console_log(key)
                console_bootstrapped = True
                logger.info(f"Console monitor bootstrapped with {len(normalized_logs)} existing logs")
                return

        normalized_logs.sort(
            key=lambda row: (row[0] is None, row[0] if row[0] is not None else 0),
            reverse=True
        )

        cycle_deadline = time.time() + max(0.5, CONSOLE_CYCLE_BUDGET_SECONDS)
        sent_this_cycle = 0

        for _, log_key, log_item in normalized_logs:
            if time.time() > cycle_deadline:
                logger.debug("Console monitor cycle budget reached; continuing next run")
                break

            with console_lock:
                if log_key in forwarded_console_ids:
                    continue

            sms_content = str(log_item.get('sms') or '')
            service = str(log_item.get('app_name') or '')
            service_key = normalize_service_name(service)

            # Forward only allowed service groups (fixed for now).
            if CONSOLE_FORWARD_SERVICE_KEYS and service_key not in CONSOLE_FORWARD_SERVICE_KEYS:
                with console_lock:
                    remember_console_log(log_key)
                continue

            if not is_console_otp_sms(sms_content, service):
                with console_lock:
                    remember_console_log(log_key)
                continue

            channel_message = build_console_channel_message(log_item)
            masked_otp = extract_masked_otp_from_sms(sms_content) or "******"
            
            # Prioritize carrier as the most accurate base for ranges from this API
            raw_carrier = normalize_range_token(log_item.get('carrier'))
            raw_range = normalize_range_token(log_item.get('range'))
            raw_number = normalize_range_token(log_item.get('number'))
            
            if raw_carrier and raw_carrier.isdigit() and len(raw_carrier) >= 4:
                range_value = f"{raw_carrier}XXX"
            else:
                range_value = raw_range or raw_number
                if range_value and range_value.isdigit() and len(range_value) >= 7:
                    # If it's a full phone number, truncate last 3 digits to make it a range
                    range_value = f"{range_value[:-3]}XXX"
            
            range_url = await build_range_deeplink(context, range_value, service_key)

            channel_row = [InlineKeyboardButton(f"pe('🔐') {masked_otp}", api_kwargs={"copy_text": {"text": masked_otp}})]
            if range_url:
                channel_row.append(InlineKeyboardButton("Range", url=range_url))
            channel_reply_markup = InlineKeyboardMarkup([channel_row])

            try:
                await context.bot.send_message(
                    chat_id=OTP_CHANNEL_ID,
                    text=channel_message,
                    reply_markup=channel_reply_markup,
                    parse_mode='HTML'
                )
                logger.info(f"Console OTP forwarded to channel: {log_key}")
            except Exception as send_error:
                logger.error(f"Error forwarding console OTP {log_key}: {type(send_error).__name__}: {send_error}")
                continue

            with console_lock:
                remember_console_log(log_key)

            sent_this_cycle += 1
            if sent_this_cycle >= max(1, CONSOLE_MAX_FORWARDS_PER_CYCLE):
                logger.debug("Console monitor send cap reached; continuing next run")
                break
    except Exception as e:
        logger.error(f"Error in monitor_console_logs: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    """Start the bot"""
    # Start Flask app in a separate thread for Render port binding
    port = int(os.getenv("PORT", 10000))
    flask_app = Flask(__name__)
    
    @flask_app.route("/")
    def health_check():
        return "Bot is running", 200
    
    def run_flask():
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info(f"Flask server started on port {port} for Render health checks")
    
    # Initialize global API client (login will retry on first API call if needed)
    logger.info("Initializing global API client...")
    api_client = get_global_api_client()
    if api_client:
        logger.info("pe('✅') API client initialized (login will retry on first API call if needed)")
    
    # Create application
    # Enable concurrent update handling so one user's long request doesn't block others.
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(UPDATE_CONCURRENCY)
        .build()
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rangechkr", rangechkr))
    application.add_handler(CommandHandler("users", admin_commands))
    application.add_handler(CommandHandler("add", admin_commands))
    application.add_handler(CommandHandler("remove", admin_commands))
    application.add_handler(CommandHandler("pending", admin_commands))
    application.add_handler(CommandHandler("broadcast", admin_commands))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler for conflict errors
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors, especially Conflict errors from multiple instances"""
        error = context.error
        if isinstance(error, Conflict):
            logger.warning(f"⚠️ Conflict error detected: {error}. This usually means multiple bot instances are running. Waiting and retrying...")
            # Wait a bit and let the other instance handle it, or this instance will take over
            await asyncio.sleep(5)
        else:
            logger.error(f"pe('❌') Error: {error}", exc_info=error)
    
    application.add_error_handler(error_handler)

    # Global console stream monitor (masked OTP logs from /mdashboard/console)
    if application.job_queue:
        application.job_queue.run_repeating(
            monitor_console_logs,
            interval=CONSOLE_MONITOR_INTERVAL,
            first=5,
            name="console_otp_monitor",
            job_kwargs={
                "max_instances": 1,
                "coalesce": True,
                "misfire_grace_time": 15
            }
        )
        logger.info("Console OTP monitor job started")
    else:
        logger.warning("Job queue not available; console OTP monitor not started")
    
    # Start bot with drop_pending_updates to avoid conflicts
    logger.info("Bot starting...")
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
    except Conflict as e:
        logger.error(f"pe('❌') Conflict error on startup: {e}. Another bot instance may be running.")
        logger.info("pe('💡') If you're sure only one instance should run, wait a few seconds and the bot will retry.")
        # Wait and retry once
        import time
        time.sleep(10)
        logger.info("pe('🔄') Retrying bot startup...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )

if __name__ == "__main__":
    main()

