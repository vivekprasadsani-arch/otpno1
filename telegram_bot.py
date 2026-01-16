import os
import threading
import time
import asyncio
import concurrent.futures
from datetime import datetime, timedelta, timezone
from datetime import datetime, timedelta, timezone
import requests
import json
import re
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import Conflict
import logging
from supabase import create_client, Client
from dotenv import load_dotenv
from flask import Flask

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
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7325836764"))
OTP_CHANNEL_ID = int(os.getenv("OTP_CHANNEL_ID", "-1002724043027"))  # Channel ID for forwarding OTP messages

# API Configuration (from otp_tool.py)
BASE_URL = "https://stexsms.com"
API_EMAIL = os.getenv("API_EMAIL", "roni791158@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "53561106@Roni")

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sgnnqvfoajqsfdyulolm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNnbm5xdmZvYWpxc2ZkeXVsb2xtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNzE1MjcsImV4cCI6MjA3OTc0NzUyN30.dFniV0odaT-7bjs5iQVFQ-N23oqTGMAgQKjswhaHSP4")

# Supabase Database setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Service → appId mapping (known primary services)
SERVICE_APP_IDS = {
    "whatsapp": "WhatsApp",
    "facebook": "Facebook",
}

def init_database():
    """Initialize Supabase database (tables should be created manually via SQL)"""
    try:
        # Test connection
        result = supabase.table('users').select('user_id').limit(1).execute()
        logger.info("✅ Supabase connection successful")
    except Exception as e:
        logger.warning(f"⚠️ Supabase connection test failed (tables may not exist yet): {e}")

# Initialize database on import
init_database()

# Global locks for thread safety
db_lock = threading.Lock()
user_jobs = {}  # Store latest monitoring job per user (older jobs may still run)

# Global API client - single session for all users
global_api_client = None
api_lock = threading.Lock()

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

def get_user_status(user_id):
    """Get user approval status from database"""
    try:
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
        self._cache_duration = 300  # 5 minutes cache
    
    def login(self):
        """Login to API - Using hypothesized endpoint /mapi/v1/mauth/login based on stexsms structure"""
        try:
            login_headers = {
                **self.browser_headers,
                "Referer": f"{self.base_url}/mdashboard/access"
            }
            # Hypothesized login endpoint
            login_url = f"{self.base_url}/mapi/v1/mauth/login"
            
            logger.info(f"Attempting login to {login_url}")
            login_resp = self.session.post(
                login_url,
                json={"email": self.email, "password": self.password},
                headers=login_headers,
                timeout=15
            )
            
            if login_resp.status_code in [200, 201]:
                login_data = login_resp.json()
                
                # Check for token in response
                token = None
                if 'data' in login_data and 'token' in login_data['data']:
                    token = login_data['data']['token']
                elif 'token' in login_data:
                    token = login_data['token']
                elif 'meta' in login_data and 'token' in login_data['meta']:
                    token = login_data['meta']['token']
                
                if token:
                    self.auth_token = token
                    self.session.headers.update({"mauthtoken": self.auth_token})
                    logger.info("Login successful")
                    return True
                else:
                    logger.error(f"Login response missing token: {login_data}")
            else:
                logger.error(f"Login failed with status {login_resp.status_code}: {login_resp.text[:200]}")
                if login_resp.status_code == 404:
                     logger.error("Login endpoint not found. Please check API documentation or provide a HAR with login.")

            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _fetch_ranges_with_keyword(self, app_id, keyword, use_origin=True):
        """Helper to fetch ranges with a specific keyword
        
        Args:
            app_id: Service name (e.g., 'WhatsApp', 'Facebook')
            keyword: Search keyword
            use_origin: If True, filter by service (origin). If False, search all services.
        """
        try:
            if not self.auth_token:
                return []
            
            headers = {
                **self.browser_headers,
                "mauthtoken": self.auth_token,
                "Referer": f"{self.base_url}/mdashboard/access"
            }
            
            payload = {
                "prefix": "",
                "origin": app_id if use_origin else "",  # Empty origin for "Others"
                "keyword": keyword
            }
            
            resp = self.session.post(
                f"{self.base_url}/mapi/v1/mdashboard/access/info",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
                    ranges = []
                    for item in data['data']:
                        destination = item.get('destination', 'Unknown')
                        country = destination.split('-')[0].strip() if '-' in destination else destination
                        
                        range_val = item.get('test_number')
                        if range_val:
                            ranges.append({
                                'id': range_val,
                                'range_id': str(item.get('id')),
                                'name': range_val,
                                'country': country,
                                'cantryName': country,
                                'operator': destination,
                                'service': item.get('origin', 'Unknown'),  # Service name for Others
                                'limit_day': item.get('limit_day'),
                                'limit_hour': item.get('limit_hour')
                            })
                    return ranges
            return []
        except Exception as e:
            logger.warning(f"Error fetching with keyword '{keyword}': {e}")
            return []

    def get_ranges(self, app_id, max_retries=3, keyword=""):
        """Get ranges for application - Service-specific fetching
        
        - WhatsApp/Facebook: Search with origin filter (service-specific)
        - Others: Search without origin filter (all services, with service labels)
        """
        try:
            if not self.auth_token:
                if not self.login():
                    return []
            
            # Check cache first
            cache_key = f"{app_id}_multi"
            if cache_key in self._ranges_cache:
                entry = self._ranges_cache[cache_key]
                if time.time() - entry['timestamp'] < self._cache_duration:
                    logger.info(f"Returning cached ranges for {app_id}")
                    return entry['data']
            
            # Determine if we should filter by service (origin)
            # WhatsApp & Facebook: use origin filter
            # Others: search all services (no origin filter)
            use_origin = app_id in ["WhatsApp", "Facebook"]
            
            # Multiple keywords to search - aggregates more results
            keywords = [
                app_id,           # e.g., "WhatsApp"
                "verification",   # Common SMS keyword
                "otp",           # OTP messages
                "code",          # Verification codes
                "",              # Empty for general results
            ]
            
            all_ranges = []
            unique_range_ids = set()
            
            for kw in keywords:
                ranges = self._fetch_ranges_with_keyword(app_id, kw, use_origin)
                
                # Add only unique ranges (by range_id)
                for r in ranges:
                    if r['range_id'] not in unique_range_ids:
                        unique_range_ids.add(r['range_id'])
                        all_ranges.append(r)
            
            filter_type = "service-specific" if use_origin else "all services"
            logger.info(f"Found {len(all_ranges)} unique ranges for {app_id} ({filter_type}) using {len(keywords)} keywords")
            
            # Update cache
            self._ranges_cache[cache_key] = {
                'timestamp': time.time(),
                'data': all_ranges
            }
            
            return all_ranges
            
        except Exception as e:
            logger.error(f"Error getting ranges: {e}")
            return []

    def get_applications(self, max_retries=3):
        """Get available applications - Mapped from SERVICE_APP_IDS for compatibility"""
        # The new API doesn't list "all apps" easily, we search by name.
        # But for 'Others' menu, we might want to return some defaults or nothing.
        # Current bot logic allows 'Others' to fetch dynamic list.
        # For now, we return the primary ones + maybe some popular ones if we want?
        # Or simply return empty list for others if we don't support dynamic discovery yet.
        # Let's return the primary ones to ensure they appear if needed.
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
            
            headers = {
                **self.browser_headers,
                "mauthtoken": self.auth_token,
                "Referer": f"{self.base_url}/mdashboard/getnum?range={range_id}"
            }
            
            # New API: POST /mapi/v1/mdashboard/getnum/number
            payload = {
                "range": range_id,
                "is_national": False,
                "remove_plus": False
            }
            
            resp = self.session.post(
                f"{self.base_url}/mapi/v1/mdashboard/getnum/number",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    number_data = data['data']
                    # Response: {"data":{"number":"+937...", ...}}
                    if isinstance(number_data, dict):
                        if 'number' in number_data:
                            return number_data
                        # Handle potential alias
                        if 'copy' in number_data:
                            number_data['number'] = number_data['copy']
                            return number_data
            
            logger.warning(f"get_number failed: {resp.text[:200]}")
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
                # Try range_name first (like otp_tool.py line 561)
                number_data = None
                if range_name:
                    number_data = self.get_number(range_name)
                
                # If range_name didn't work, try range_id
                if not number_data:
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
            logger.error(f"❌ Failed to get any valid numbers from range {range_id} after {total_attempts} attempts.")
        else:
            logger.info(f"✅ Successfully obtained {len(numbers)}/{count} numbers for range {range_id}.")
            
        return numbers
    
    def check_otp(self, number):
        """Check for OTP on a number - using NEW API /mapi/v1/mdashboard/getnum/info"""
        try:
            if not self.auth_token:
                if not self.login():
                    return None
            
            # Date format YYYY-MM-DD for new API
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            headers = {
                **self.browser_headers,
                "mauthtoken": self.auth_token,
                "Referer": f"{self.base_url}/mdashboard/getnum"
            }
            
            # New API: GET /mapi/v1/mdashboard/getnum/info?date=...
            resp = self.session.get(
                f"{self.base_url}/mapi/v1/mdashboard/getnum/info?date={today_str}&page=1&search=&status=",
                headers=headers,
                timeout=8
            )
            
            if resp.status_code == 401:
                logger.info("Token expired in check_otp, refreshing...")
                if self.login():
                    headers["mauthtoken"] = self.auth_token
                    resp = self.session.get(
                        f"{self.base_url}/mapi/v1/mdashboard/getnum/info?date={today_str}&page=1&search=&status=",
                        headers=headers,
                        timeout=8
                    )
                else:
                    return None
            
            if resp.status_code == 200:
                data = resp.json()
                # Expected: {"data": {"numbers": [{"number": "...", "message": "..."}, ...]}}
                if 'data' in data and data['data']:
                    numbers_list = data['data'].get('numbers', [])
                    if numbers_list:
                        target_normalized = number.replace('+', '').replace(' ', '').strip()
                        
                        for num_obj in numbers_list:
                            api_num = num_obj.get('number', '').replace('+', '').strip()
                            # Check match & last 9 digits
                            if api_num == target_normalized or (len(api_num) >= 9 and len(target_normalized) >= 9 and api_num[-9:] == target_normalized[-9:]):
                                # Found the number.
                                # New API returns full message in 'otp' and 'message' fields.
                                # We map 'message' to 'sms_content' and clear 'otp' to let monitor_otp extract the code.
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
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            headers = {
                **self.browser_headers,
                "mauthtoken": self.auth_token,
                "Referer": f"{self.base_url}/mdashboard/getnum"
            }
            
            resp = self.session.get(
                f"{self.base_url}/mapi/v1/mdashboard/getnum/info?date={today_str}&page=1&search=&status=",
                headers=headers,
                timeout=8
            )
            
            if resp.status_code == 401:
                if self.login():
                    headers["mauthtoken"] = self.auth_token
                    resp = self.session.get(
                        f"{self.base_url}/mapi/v1/mdashboard/getnum/info?date={today_str}&page=1&search=&status=",
                        headers=headers,
                        timeout=8
                    )
                else:
                    return {}

            result = {}
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data']:
                    numbers_list = data['data'].get('numbers', [])
                    if numbers_list:
                        # Create map of API numbers to their data
                        # We also handle last 9 digits and exact matches
                        
                        target_map_exact = {n.replace('+', '').replace(' ', '').strip(): n for n in numbers}
                        target_map_last9 = {n.replace('+', '').replace(' ', '').strip()[-9:]: n for n in numbers if len(n.replace('+', '').replace(' ', '').strip()) >= 9}
                        
                        for num_obj in numbers_list:
                            api_num = num_obj.get('number', '').replace('+', '').strip()
                            
                            # Prepare object logic (same as check_otp)
                            msg = num_obj.get('message') or num_obj.get('otp', '')
                            if msg:
                                num_obj['sms_content'] = msg
                                num_obj['otp'] = None # Forces extraction in monitor_otp

                            # Check match
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
    'Angola': '🇦🇴', 'Afghanistan': '🇦🇫', 'Albania': '🇦🇱', 'Algeria': '🇩🇿',
    'Andorra': '🇦🇩', 'Argentina': '🇦🇷', 'Armenia': '🇦🇲', 'Aruba': '🇦🇼',
    'Australia': '🇦🇺', 'Austria': '🇦🇹', 'Azerbaijan': '🇦🇿', 'Bahrain': '🇧🇭',
    'Bangladesh': '🇧🇩', 'Belarus': '🇧🇾', 'Belgium': '🇧🇪', 'Belize': '🇧🇿',
    'Benin': '🇧🇯', 'Bhutan': '🇧🇹', 'Bolivia': '🇧🇴', 'Bosnia': '🇧🇦',
    'Botswana': '🇧🇼', 'Brazil': '🇧🇷', 'Brunei': '🇧🇳', 'Bulgaria': '🇧🇬',
    'Burkina Faso': '🇧🇫', 'Burundi': '🇧🇮', 'Cameroon': '🇨🇲', 'Cambodia': '🇰🇭', 'Canada': '🇨🇦',
    'Chile': '🇨🇱', 'China': '🇨🇳', 'Colombia': '🇨🇴', 'Congo': '🇨🇬',
    'Costa Rica': '🇨🇷', 'Croatia': '🇭🇷', 'Cuba': '🇨🇺', 'Cyprus': '🇨🇾',
    'Central African Republic': '🇨🇫', 'Chad': '🇹🇩', 'Nigeria': '🇳🇬', 'Cape Verde': '🇨🇻', 'Sao Tome and Principe': '🇸🇹',
    'Czech Republic': '🇨🇿', 'DR Congo': '🇨🇩', 'Denmark': '🇩🇰', 'Djibouti': '🇩🇯',
    'Ecuador': '🇪🇨', 'Egypt': '🇪🇬', 'El Salvador': '🇸🇻', 'Equatorial Guinea': '🇬🇶',
    'Eritrea': '🇪🇷', 'Estonia': '🇪🇪', 'Ethiopia': '🇪🇹', 'Fiji': '🇫🇯',
    'Finland': '🇫🇮', 'France': '🇫🇷', 'French Guiana': '🇬🇫', 'Gabon': '🇬🇦',
    'Gambia': '🇬🇲', 'Georgia': '🇬🇪', 'Germany': '🇩🇪', 'Ghana': '🇬🇭',
    'Gibraltar': '🇬🇮', 'Greece': '🇬🇷', 'Greenland': '🇬🇱', 'Guadeloupe': '🇬🇵',
    'Guatemala': '🇬🇹', 'Guinea': '🇬🇳', 'Guinea-Bissau': '🇬🇼', 'Guyana': '🇬🇾',
    'Haiti': '🇭🇹', 'Honduras': '🇭🇳', 'Hong Kong': '🇭🇰', 'Hungary': '🇭🇺',
    'Iceland': '🇮🇸', 'India': '🇮🇳', 'Indonesia': '🇮🇩', 'Iran': '🇮🇷',
    'Iraq': '🇮🇶', 'Ireland': '🇮🇪', 'Israel': '🇮🇱', 'Italy': '🇮🇹',
    'Ivory Coast': '🇨🇮', 'Japan': '🇯🇵', 'Jordan': '🇯🇴', 'Kenya': '🇰🇪',
    'Kiribati': '🇰🇮', 'Kosovo': '🇽🇰', 'Kuwait': '🇰🇼', 'Kyrgyzstan': '🇰🇬',
    'Laos': '🇱🇦', 'Latvia': '🇱🇻', 'Lebanon': '🇱🇧', 'Lesotho': '🇱🇸',
    'Liberia': '🇱🇷', 'Libya': '🇱🇾', 'Liechtenstein': '🇱🇮', 'Lithuania': '🇱🇹',
    'Luxembourg': '🇱🇺', 'Macau': '🇲🇴', 'Macedonia': '🇲🇰', 'Madagascar': '🇲🇬',
    'Malawi': '🇲🇼', 'Malaysia': '🇲🇾', 'Maldives': '🇲🇻', 'Mali': '🇲🇱',
    'Malta': '🇲🇹', 'Martinique': '🇲🇶', 'Mauritania': '🇲🇷', 'Mauritius': '🇲🇺',
    'Mexico': '🇲🇽', 'Moldova': '🇲🇩', 'Monaco': '🇲🇨', 'Mongolia': '🇲🇳',
    'Montenegro': '🇲🇪', 'Morocco': '🇲🇦', 'Mozambique': '🇲🇿', 'Myanmar': '🇲🇲',
    'Namibia': '🇳🇦', 'Nauru': '🇳🇷', 'Nepal': '🇳🇵', 'Netherlands': '🇳🇱',
    'New Caledonia': '🇳🇨', 'New Zealand': '🇳🇿', 'Nicaragua': '🇳🇮', 'Niger': '🇳🇪',
    'Nigeria': '🇳🇬', 'North Korea': '🇰🇵', 'Norway': '🇳🇴', 'Oman': '🇴🇲',
    'Pakistan': '🇵🇰', 'Palau': '🇵🇼', 'Palestine': '🇵🇸', 'Panama': '🇵🇦',
    'Papua New Guinea': '🇵🇬', 'Paraguay': '🇵🇾', 'Peru': '🇵🇪', 'Philippines': '🇵🇭',
    'Poland': '🇵🇱', 'Portugal': '🇵🇹', 'Qatar': '🇶🇦', 'Reunion': '🇷🇪',
    'Romania': '🇷🇴', 'Russia': '🇷🇺', 'Rwanda': '🇷🇼', 'Saudi Arabia': '🇸🇦',
    'Senegal': '🇸🇳', 'Serbia': '🇷🇸', 'Seychelles': '🇸🇨', 'Sierra Leone': '🇸🇱',
    'Singapore': '🇸🇬', 'Slovakia': '🇸🇰', 'Slovenia': '🇸🇮', 'Solomon Islands': '🇸🇧',
    'Somalia': '🇸🇴', 'South Africa': '🇿🇦', 'South Korea': '🇰🇷', 'Spain': '🇪🇸',
    'Sri Lanka': '🇱🇰', 'Sudan': '🇸🇩', 'Suriname': '🇸🇷', 'Swaziland': '🇸🇿',
    'Sweden': '🇸🇪', 'Switzerland': '🇨🇭', 'Syria': '🇸🇾', 'Taiwan': '🇹🇼',
    'Tajikistan': '🇹🇯', 'Tanzania': '🇹🇿', 'Thailand': '🇹🇭', 'Togo': '🇹🇬',
    'Tonga': '🇹🇴', 'Tunisia': '🇹🇳', 'Turkey': '🇹🇷', 'Turkmenistan': '🇹🇲',
    'Tuvalu': '🇹🇻', 'UAE': '🇦🇪', 'Uganda': '🇺🇬', 'UK': '🇬🇧',
    'Ukraine': '🇺🇦', 'Uruguay': '🇺🇾', 'USA': '🇺🇸', 'Uzbekistan': '🇺🇿',
    'Vanuatu': '🇻🇺', 'Venezuela': '🇻🇪', 'Vietnam': '🇻🇳', 'Yemen': '🇾🇪',
    'Zambia': '🇿🇲', 'Zimbabwe': '🇿🇼', 'Comoros': '🇰🇲', 'East Timor': '🇹🇱',
    'Falkland Islands': '🇫🇰', 'Faroe Islands': '🇫🇴', 'French Polynesia': '🇵🇫',
    'Guinea-Bissau': '🇬🇼', 'Saint Helena': '🇸🇭', 'Saint Pierre': '🇵🇲',
    'Wallis': '🇼🇫', 'Cook Islands': '🇨🇰', 'Niue': '🇳🇺', 'Samoa': '🇼🇸',
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
    """Mask number middle digits with XXXX (e.g., +1234567890 -> +1234XXXX90)"""
    if not number:
        return number
    
    # Remove + and spaces, keep only digits
    digits = ''.join(filter(str.isdigit, number))
    has_plus = number.startswith('+')
    
    if len(digits) < 6:
        # Too short to mask, return as is
        return number
    
    # Keep first 4 and last 2 digits, mask the middle
    if len(digits) >= 6:
        masked = digits[:4] + 'XXXX' + digits[-2:]
    else:
        masked = digits
    
    # Add + back if it was there
    if has_plus:
        masked = '+' + masked
    
    return masked

def detect_language_from_sms(sms_content):
    """Detect language from SMS content"""
    if not sms_content:
        return 'Unknown'
    
    sms_lower = sms_content.lower()
    
    # Common language indicators
    # NOTE: "code" is too generic (exists in many languages). We prefer longer phrases / accented words.
    language_keywords = {
        'English': ['your code is', 'verification code', 'otp', 'one-time password', 'do not share', 'verify', 'confirm', 'code is', 'code'],
        'French': ['votre code est', 'vérification', 'vérifier', 'mot de passe', 'confirmer', 'connexion', 'sécurité', 'ne partagez pas'],
        'Spanish': ['tu código es', 'código', 'verificación', 'contraseña', 'confirmar', 'verificar'],
        'German': ['dein code ist', 'ihr code ist', 'bestätigung', 'passwort', 'bestätigen', 'verifizieren'],
        'Italian': ['codice', 'verifica', 'password', 'confermare', 'verificare', 'il tuo codice è'],
        'Portuguese': ['código', 'verificação', 'senha', 'confirmar', 'verificar', 'seu código é'],
        'Russian': ['код', 'подтверждение', 'пароль', 'подтвердить', 'проверить', 'ваш код'],
        'Arabic': ['رمز', 'التحقق', 'كلمة المرور', 'تأكيد', 'التحقق من', 'رمزك هو'],
        'Hindi': ['कोड', 'सत्यापन', 'पासवर्ड', 'पुष्टि', 'सत्यापित', 'आपका कोड है'],
        'Bengali': ['কোড', 'যাচাইকরণ', 'পাসওয়ার্ড', 'নিশ্চিত', 'যাচাই', 'আপনার কোড'],
        'Chinese': ['代码', '验证', '密码', '确认', '验证', '您的代码是'],
        'Japanese': ['コード', '確認', 'パスワード', '確認する', '検証', 'あなたのコードは'],
        'Korean': ['코드', '확인', '비밀번호', '확인하다', '검증', '귀하의 코드는'],
        'Turkish': ['kod', 'doğrulama', 'şifre', 'onayla', 'doğrula', 'kodunuz'],
        'Dutch': ['uw code is', 'verificatie', 'wachtwoord', 'bevestigen', 'verifiëren'],
        'Polish': ['kod', 'weryfikacja', 'hasło', 'potwierdź', 'zweryfikuj', 'twój kod to'],
        'Thai': ['รหัส', 'การยืนยัน', 'รหัสผ่าน', 'ยืนยัน', 'ตรวจสอบ', 'รหัสของคุณคือ'],
        'Vietnamese': ['mã', 'xác minh', 'mật khẩu', 'xác nhận', 'xác minh', 'mã của bạn là'],
        'Indonesian': ['kode', 'verifikasi', 'kata sandi', 'konfirmasi', 'verifikasi', 'kode anda adalah'],
        'Malay': ['kod', 'pengesahan', 'kata laluan', 'mengesahkan', 'mengesahkan', 'kod anda ialah'],
        'Filipino': ['code', 'beripikasyon', 'password', 'kumpirmahin', 'beripikahin', 'ang iyong code ay'],
        'Swedish': ['kod', 'verifiering', 'lösenord', 'bekräfta', 'verifiera', 'din kod är'],
        'Norwegian': ['kode', 'verifisering', 'passord', 'bekreft', 'verifiser', 'din kode er'],
        'Danish': ['kode', 'verificering', 'adgangskode', 'bekræft', 'verificer', 'din kode er'],
        'Finnish': ['koodi', 'vahvistus', 'salasana', 'vahvista', 'vahvistaa', 'koodisi on'],
        'Greek': ['κωδικός', 'επιβεβαίωση', 'κωδικός πρόσβασης', 'επιβεβαιώστε', 'επιβεβαιώστε', 'ο κωδικός σας είναι'],
        'Hebrew': ['קוד', 'אימות', 'סיסמה', 'אשר', 'אמת', 'הקוד שלך הוא'],
        'Romanian': ['cod', 'verificare', 'parolă', 'confirmă', 'verifică', 'codul tău este'],
        'Czech': ['kód', 'ověření', 'heslo', 'potvrdit', 'ověřit', 'váš kód je'],
        'Hungarian': ['kód', 'igazolás', 'jelszó', 'megerősít', 'igazol', 'a kódod'],
        'Bulgarian': ['код', 'потвърждение', 'парола', 'потвърди', 'провери', 'вашият код е'],
        'Croatian': ['kod', 'verifikacija', 'lozinka', 'potvrdi', 'verificiraj', 'vaš kod je'],
        'Serbian': ['код', 'верификација', 'лозинка', 'потврди', 'верификуј', 'ваш код је'],
        'Slovak': ['kód', 'overenie', 'heslo', 'potvrď', 'over', 'váš kód je'],
        'Slovenian': ['koda', 'verifikacija', 'geslo', 'potrdi', 'verificiraj', 'vaša koda je'],
        'Ukrainian': ['код', 'підтвердження', 'пароль', 'підтвердити', 'перевірити', 'ваш код'],
        'Belarusian': ['код', 'пацвярджэнне', 'пароль', 'пацвердзіць', 'праверыць', 'ваш код'],
        'Kazakh': ['код', 'растау', 'құпия сөз', 'растау', 'тексеру', 'сіздің кодыңыз'],
        'Uzbek': ['kod', 'tasdiqlash', 'parol', 'tasdiqlash', 'tekshirish', 'sizning kodingiz'],
        'Azerbaijani': ['kod', 'təsdiq', 'şifrə', 'təsdiqlə', 'yoxla', 'sizin kodunuz'],
        'Georgian': ['კოდი', 'დადასტურება', 'პაროლი', 'დადასტურება', 'შემოწმება', 'თქვენი კოდია'],
        'Armenian': ['կոդ', 'հաստատում', 'գաղտնաբառ', 'հաստատել', 'ստուգել', 'ձեր կոդն է'],
        'Mongolian': ['код', 'баталгаажуулалт', 'нууц үг', 'баталгаажуулах', 'шалгах', 'таны код'],
        'Nepali': ['कोड', 'प्रमाणीकरण', 'पासवर्ड', 'पुष्टि', 'प्रमाणित', 'तपाईंको कोड'],
        'Sinhala': ['කේතය', 'සත්‍යාපනය', 'මුරපදය', 'තහවුරු', 'සත්‍යාපනය', 'ඔබේ කේතය'],
        'Tamil': ['குறியீடு', 'சரிபார்ப்பு', 'கடவுச்சொல்', 'உறுதிப்படுத்த', 'சரிபார்க்க', 'உங்கள் குறியீடு'],
        'Telugu': ['కోడ్', 'ధృవీకరణ', 'పాస్వర్డ్', 'నిర్ధారించండి', 'ధృవీకరించండి', 'మీ కోడ్'],
        'Marathi': ['कोड', 'सत्यापन', 'पासवर्ड', 'पुष्टी', 'सत्यापित', 'तुमचा कोड'],
        'Gujarati': ['કોડ', 'ચકાસણી', 'પાસવર્ડ', 'પુષ્ટિ', 'ચકાસો', 'તમારો કોડ'],
        'Kannada': ['ಕೋಡ್', 'ಪರಿಶೀಲನೆ', 'ಪಾಸ್ವರ್ಡ್', 'ದೃಢೀಕರಿಸಿ', 'ಪರಿಶೀಲಿಸಿ', 'ನಿಮ್ಮ ಕೋಡ್'],
        'Malayalam': ['കോഡ്', 'സ്ഥിരീകരണം', 'പാസ്‌വേഡ്', 'സ്ഥിരീകരിക്കുക', 'പരിശോധിക്കുക', 'നിങ്ങളുടെ കോഡ്'],
        'Punjabi': ['ਕੋਡ', 'ਪੜਤਾਲ', 'ਪਾਸਵਰਡ', 'ਪੁਸ਼ਟੀ', 'ਪੜਤਾਲ', 'ਤੁਹਾਡਾ ਕੋਡ'],
        'Urdu': ['کوڈ', 'تصدیق', 'پاس ورڈ', 'تصدیق', 'تصدیق', 'آپ کا کوڈ'],
        'Pashto': ['کوډ', 'تصدیق', 'پاسورډ', 'تصدیق', 'تصدیق', 'ستاسو کوډ'],
        'Persian': ['کد', 'تأیید', 'رمز عبور', 'تأیید', 'تأیید', 'کد شما'],
        'Kurdish': ['کۆد', 'دڵنیاکردنەوە', 'تێپەڕەوشە', 'دڵنیاکردنەوە', 'دڵنیاکردنەوە', 'کۆدی تۆ'],
        'Amharic': ['ኮድ', 'ማረጋገጥ', 'የይለፍ ቃል', 'አረጋግጥ', 'ማረጋገጥ', 'ኮድዎ'],
        'Swahili': ['kodi', 'uthibitishaji', 'neno la siri', 'thibitisha', 'thibitisha', 'kodi yako ni'],
        'Afrikaans': ['kode', 'verifikasie', 'wagwoord', 'bevestig', 'verifieer', 'jou kode is'],
        'Zulu': ['ikhodi', 'ukuqinisekisa', 'iphasiwedi', 'qinisekisa', 'qinisekisa', 'ikhodi yakho iyinto'],
        'Xhosa': ['ikhowudi', 'ukuqinisekisa', 'iphasiwedi', 'qinisekisa', 'qinisekisa', 'ikhowudi yakho'],
        'Igbo': ['koodu', 'nkwenye', 'paswọọdụ', 'kwado', 'kwado', 'koodu gị bụ'],
        'Yoruba': ['koodu', 'ijẹrisi', 'ọrọ aṣina', 'jẹrisi', 'jẹrisi', 'koodu rẹ jẹ'],
        'Hausa': ['lambar', 'tabbatarwa', 'kalmar sirri', 'tabbatar', 'tabbatar', 'lambar ku'],
        'Somali': ['koodhka', 'xaqiijinta', 'ereyga sirta ah', 'xaqiiji', 'xaqiiji', 'koodhkaagu waa'],
        'Oromo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Tigrinya': ['ኮድ', 'ምርመራ', 'ዓንቀጽ', 'ምርመራ', 'ምርመራ', 'ኮድካ'],
        'Kinyarwanda': ['kode', 'kwemeza', 'ijambo ryibanga', 'kwemeza', 'kwemeza', 'kode yawe ni'],
        'Luganda': ['koodi', 'okukakasa', 'ekiwandiiko', 'kakasa', 'kakasa', 'koodi yo'],
        'Kiswahili': ['nambari', 'uthibitishaji', 'neno la siri', 'thibitisha', 'thibitisha', 'nambari yako ni'],
        'Malagasy': ['kaody', 'fanamarinana', 'tenimiafina', 'hamarinina', 'hamarinina', 'kaody anao'],
        'Sesotho': ['khoutu', 'tiisetsa', 'lefoko la sephiri', 'tiisetsa', 'tiisetsa', 'khoutu ea hau'],
        'Setswana': ['khoutu', 'tiisetsa', 'lefoko la sephiri', 'tiisetsa', 'tiisetsa', 'khoutu ya gago'],
        'Xitsonga': ['khodi', 'ntirhisano', 'vito ra xiviri', 'tirhisa', 'tirhisa', 'khodi ya wena'],
        'Tshivenda': ['khodi', 'u ṱoḓisisa', 'ḽiṅwalwa ḽa tshifhinga', 'ṱoḓisisa', 'ṱoḓisisa', 'khodi yawe'],
        'isiNdebele': ['ikhodi', 'ukuqinisekisa', 'igama elingaphandle', 'qinisekisa', 'qinisekisa', 'ikhodi yakho'],
        'siSwati': ['ikhodi', 'ukuqinisekisa', 'ligama lephasiwedi', 'qinisekisa', 'qinisekisa', 'ikhodi yakho'],
        'Kirundi': ['kode', 'kwemeza', 'ijambo ryibanga', 'kwemeza', 'kwemeza', 'kode yawe ni'],
        'Chichewa': ['khodi', 'kutsimikiza', 'mawu achinsinsi', 'tsimikiza', 'tsimikiza', 'khodi yanu'],
        'Kikuyu': ['koodi', 'gũthibitithia', 'rĩtwa rĩa thĩinĩ', 'thibitithia', 'thibitithia', 'koodi yaku'],
        'Luo': ['kod', 'kelo', 'wach kelo', 'kelo', 'kelo', 'kod ma'],
        'Wolof': ['kood', 'seere', 'baat bu nekk ci', 'seere', 'seere', 'kood bi'],
        'Fula': ['koode', 'seedugol', 'baatol seedugol', 'seedugol', 'seedugol', 'koode maa'],
        'Mandinka': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Bambara': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Soninke': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Songhay': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Hausa': ['lambar', 'tabbatarwa', 'kalmar sirri', 'tabbatar', 'tabbatar', 'lambar ku'],
        'Yoruba': ['koodu', 'ijẹrisi', 'ọrọ aṣina', 'jẹrisi', 'jẹrisi', 'koodu rẹ jẹ'],
        'Igbo': ['koodu', 'nkwenye', 'paswọọdụ', 'kwado', 'kwado', 'koodu gị bụ'],
        'Ewe': ['koodu', 'nudzudzɔ', 'ŋuti', 'nudzudzɔ', 'nudzudzɔ', 'koodu wò'],
        'Twi': ['koodu', 'sɛɛ', 'asɛm', 'sɛɛ', 'sɛɛ', 'koodu wo'],
        'Ga': ['koodu', 'sɛɛ', 'asɛm', 'sɛɛ', 'sɛɛ', 'koodu wo'],
        'Fante': ['koodu', 'sɛɛ', 'asɛm', 'sɛɛ', 'sɛɛ', 'koodu wo'],
        'Akan': ['koodu', 'sɛɛ', 'asɛm', 'sɛɛ', 'sɛɛ', 'koodu wo'],
        'Bambara': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Wolof': ['kood', 'seere', 'baat bu nekk ci', 'seere', 'seere', 'kood bi'],
        'Fula': ['koode', 'seedugol', 'baatol seedugol', 'seedugol', 'seedugol', 'koode maa'],
        'Mandinka': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Soninke': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Songhay': ['koodo', 'seedeyaa', 'baatool seedeyaa', 'seedeyaa', 'seedeyaa', 'koodo maa'],
        'Berber': ['akud', 'asentem', 'awal n usentem', 'sentem', 'sentem', 'akud nnek'],
        'Tamazight': ['akud', 'asentem', 'awal n usentem', 'sentem', 'sentem', 'akud nnek'],
        'Afar': ['kood', 'xaqiijinta', 'ereyga sirta ah', 'xaqiiji', 'xaqiiji', 'koodkaagu'],
        'Oromo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Tigrinya': ['ኮድ', 'ምርመራ', 'ዓንቀጽ', 'ምርመራ', 'ምርመራ', 'ኮድካ'],
        'Amharic': ['ኮድ', 'ማረጋገጥ', 'የይለፍ ቃል', 'አረጋግጥ', 'ማረጋገጥ', 'ኮድዎ'],
        'Gurage': ['ኮድ', 'ማረጋገጥ', 'የይለፍ ቃል', 'አረጋግጥ', 'ማረጋገጥ', 'ኮድዎ'],
        'Harari': ['ኮድ', 'ማረጋገጥ', 'የይለፍ ቃል', 'አረጋግጥ', 'ማረጋገጥ', 'ኮድዎ'],
        'Sidamo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Gedeo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Hadiyya': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Kambaata': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Gamo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Gofa': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Wolaytta': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Bench': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Sheko': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Majang': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Suri': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Mursi': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Bodi': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Kwegu': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Karo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Hamer': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Banna': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Bashada': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Aari': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Dime': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Nyangatom': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Toposa': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Turkana': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Pokot': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Samburu': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Rendille': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'El Molo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Boni': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Aweer': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Dahalo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Yaaku': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Elgon': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Okiek': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Ogiek': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Akiek': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Ndorobo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Dorobo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Sanye': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Boni': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Aweer': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Dahalo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Yaaku': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Elgon': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Okiek': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Ogiek': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Akiek': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Ndorobo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Dorobo': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee'],
        'Sanye': ['koodii', 'mirkaneessi', 'jecha icciitii', 'mirkaneessi', 'mirkaneessi', 'koodiin kee']
    }
    
    # Score-based detection (prevents generic "code" forcing English)
    scores = {}
    for lang, keywords in language_keywords.items():
        score = 0
        for keyword in keywords:
            if keyword and keyword in sms_lower:
                # Longer phrases are more informative
                score += max(1, len(keyword) // 4)
        if score > 0:
            scores[lang] = score

    # Pick best scoring language (if any)
    if scores:
        best_lang = max(scores.items(), key=lambda kv: kv[1])[0]
        return best_lang

    # Default fallback
    return 'English'

# Bot Handlers
async def rangechkr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rangechkr command - Show ranges grouped by service"""
    user_id = update.effective_user.id
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await update.message.reply_text("❌ Your access is pending approval.")
        return
    
    # Get global API client
    api_client = get_global_api_client()
    if not api_client:
        await update.message.reply_text("❌ API connection error. Please try again.")
        return
    
    # Show service selection first (fixed three: WhatsApp, Facebook, Others)
    keyboard = [
        [InlineKeyboardButton("💬 WhatsApp", callback_data="rangechkr_service_whatsapp")],
        [InlineKeyboardButton("👥 Facebook", callback_data="rangechkr_service_facebook")],
        [InlineKeyboardButton("✨ Others", callback_data="rangechkr_service_others")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🗂️ Select service to view ranges:",
        reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"
    
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
            [KeyboardButton("📲 Get Number")],
            [KeyboardButton("🧮 Set Number Count")],
            [KeyboardButton("📊 My Stats")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "✨ Welcome!\n\n"
            "📲 Tap **Get Number** to start getting numbers.\n"
            "🧮 Use **Set Number Count** to choose how many numbers you receive.\n"
            f"📌 Current setting: **{current_count}** number(s)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif status == 'rejected':
        await update.message.reply_text("❌ Your access has been rejected. Please contact admin.")
    else:
        # Notify admin
        try:
            admin_message = f"🆕 New user request:\n\n"
            admin_message += f"User ID: {user_id}\n"
            admin_message += f"Username: @{username}\n"
            admin_message += f"Name: {user.first_name or 'N/A'}"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_{user_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_{user_id}")
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
            "⏳ Your request has been sent to admin. Please wait for approval."
        )

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin commands"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return
    
    command = update.message.text.split()[0] if update.message.text else ""
    
    if command == "/users":
        users = get_all_users()
        if not users:
            await update.message.reply_text("📋 No users found.")
            return
        
        message = "📋 All Users:\n\n"
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
            await update.message.reply_text(f"✅ User {target_id} approved/added successfully.")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif command.startswith("/remove"):
        try:
            target_id = int(context.args[0]) if context.args else None
            if target_id:
                # Stop any latest monitoring job for this user
                if target_id in user_jobs:
                    user_jobs[target_id].schedule_removal()
                    del user_jobs[target_id]
                remove_user(target_id)
                await update.message.reply_text(f"✅ User {target_id} removed successfully.")
            else:
                await update.message.reply_text("Usage: /remove <user_id>")
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {e}")
    
    elif command == "/pending":
        pending = get_pending_users()
        if not pending:
            await update.message.reply_text("✅ No pending users.")
            return
        
        message = "⏳ Pending Users:\n\n"
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
                "📣 Broadcast usage:\n"
                "- Reply any message then type: /broadcast\n"
                "- Or: /broadcast <your message>"
            )
            return

        approved_user_ids = get_approved_user_ids()
        if not approved_user_ids:
            await update.message.reply_text("ℹ️ No approved users found to broadcast to.")
            return

        await update.message.reply_text(f"📣 Broadcasting to {len(approved_user_ids)} approved user(s)...")

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

        summary = f"✅ Broadcast done.\n\nSent: {sent}\nFailed: {failed}"
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
            await query.edit_message_text("❌ Access denied.")
            return
        
        if data.startswith("admin_approve_"):
            target_user_id = int(data.split("_")[2])
            approve_user(target_user_id)
            await query.edit_message_text(f"✅ User {target_user_id} approved.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="✅ Your request has been approved! Use /start to begin."
                )
            except:
                pass
        
        elif data.startswith("admin_reject_"):
            target_user_id = int(data.split("_")[2])
            reject_user(target_user_id)
            await query.edit_message_text(f"❌ User {target_user_id} rejected.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="❌ Your request has been rejected."
                )
            except:
                pass
        return
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await query.edit_message_text("❌ Your access is pending approval.")
        return
    
    # Handle number count setting (1-5)
    if data.startswith("set_count_"):
        try:
            count = int(data.split("_")[2])
            if count < 1 or count > 5:
                await query.edit_message_text("❌ Invalid count. Please select 1-5.")
                return
            
            # Update user session with new count
            update_user_session(user_id, number_count=count)
            
            await query.edit_message_text(
                f"✅ Number count set to {count}.\n\n"
                f"Now you will receive {count} number(s) when you request numbers."
            )
        except (ValueError, IndexError) as e:
            logger.error(f"Error setting number count: {e}")
            await query.edit_message_text("❌ Error setting number count. Please try again.")
        return
    
    # Service selection (from inline buttons)
    if data.startswith("service_"):
        service_name = data.split("_")[1]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("❌ API connection error. Please try again.")
            return
        
        # If Others clicked, first show dynamic service list (excluding WhatsApp/Facebook)
        if service_name == "others":
            try:
                with api_lock:
                    apps = api_client.get_applications()
                if not apps:
                    await query.edit_message_text("❌ No services found.")
                    return

                primary_ids = set(SERVICE_APP_IDS.values())
                other_apps = []
                for app in apps:
                    app_id = app.get('appId') or app.get('id')
                    app_name = app.get('name') or app.get('application') or app_id
                    if app_id and app_id not in primary_ids:
                        other_apps.append({"id": app_id, "name": app_name})

                if not other_apps:
                    await query.edit_message_text("❌ No other services available.")
                    return

                context.user_data['other_services'] = other_apps
                context.user_data.setdefault('custom_services', {})

                keyboard = []
                for idx, app in enumerate(other_apps):
                    label = app['name'] or app['id']
                    keyboard.append([InlineKeyboardButton(label, callback_data=f"serviceapp_{idx}")])
                keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_services")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("📋 Select a service:", reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error loading applications: {e}")
                await query.edit_message_text("❌ Failed to load services. Please try again.")
            return
        
        # For primary services (WhatsApp/Facebook)
        app_id = resolve_app_id(service_name, context)
        if not app_id:
            await query.edit_message_text("❌ Invalid service.")
            return
        
        with api_lock:
            ranges = api_client.get_ranges(app_id)
        
        if not ranges:
            await query.edit_message_text(f"❌ No active ranges available for {service_name}.")
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

        # Check if this is "Others" service to show service labels
        is_others = service_name == "others" or service_name.startswith("app")
        
        for i in range(0, len(country_list), 2):
            row = []
            flag1 = get_country_flag(country_list[i])
            
            # For Others, show service name in button
            if is_others and country_ranges[country_list[i]]:
                # Get service from first range in this country
                service_label = country_ranges[country_list[i]][0].get('service', '')
                button_text = f"{flag1} {country_list[i]} | 📱 {service_label}"
            else:
                button_text = f"{flag1} {country_list[i]}"
            
            row.append(InlineKeyboardButton(
                button_text,
                callback_data=f"country_{service_name}_{country_list[i]}"
            ))
            
            if i + 1 < len(country_list):
                flag2 = get_country_flag(country_list[i + 1])
                
                # For Others, show service name in button
                if is_others and country_ranges[country_list[i + 1]]:
                    service_label = country_ranges[country_list[i + 1]][0].get('service', '')
                    button_text = f"{flag2} {country_list[i + 1]} | 📱 {service_label}"
                else:
                    button_text = f"{flag2} {country_list[i + 1]}"
                
                row.append(InlineKeyboardButton(
                    button_text,
                    callback_data=f"country_{service_name}_{country_list[i + 1]}"
                ))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_services")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        service_display = "OTHERS" if is_others else service_name.upper()
        await query.edit_message_text(
            f"📱 {service_display} - Select Country:",
            reply_markup=reply_markup
        )
        return

    # Service selection for dynamic Others list
    if data.startswith("serviceapp_"):
        idx = int(data.split("_")[1])
        other_apps = context.user_data.get('other_services', [])
        if idx < 0 or idx >= len(other_apps):
            await query.edit_message_text("❌ Invalid service.")
            return
        app = other_apps[idx]
        app_id = app['id']
        service_key = f"app{idx}"
        service_label = app.get('name') or app_id

        # Register this custom service for this user (used later in country callbacks)
        context.user_data.setdefault('custom_services', {})
        context.user_data['custom_services'][service_key] = app_id

        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("❌ API connection error. Please try again.")
            return

        with api_lock:
            ranges = api_client.get_ranges(app_id)

        if not ranges:
            await query.edit_message_text(f"❌ No active ranges available for {service_label}.")
            return
        
        # For downstream country callback, use service_key as identifier
        service_name = service_key
        
        # Group ranges by country - detect from range name if country not available
        country_ranges = {}
        for r in ranges:
            range_name = r.get('name', r.get('id', ''))
            # Try to get country from API response first
            country = r.get('cantryName', r.get('country', ''))
            
            # If country not found or Unknown, detect from range name
            if not country or country == 'Unknown' or country.strip() == '':
                country = detect_country_from_range(range_name)
            
            # Only use Unknown as last resort - try harder to detect
            if not country or country == 'Unknown':
                # Try to extract from range name more aggressively
                range_str = str(range_name).upper()
                # Sometimes range name contains country code in different format
                for code, c_name in COUNTRY_CODES.items():
                    if code in range_str or c_name.upper() in range_str:
                        country = c_name
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
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_services")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📱 {service_name.upper()} - Select Country:",
            reply_markup=reply_markup
        )
    
    # Note: num_copy_ handler removed - using copy_text parameter in InlineKeyboardButton
    # When copy_text is used, button click directly copies text without callback
    
    # Country selection
    elif data.startswith("country_"):
        parts = data.split("_", 2)
        service_name = parts[1]
        country = parts[2]
        
        app_id = resolve_app_id(service_name, context)
        if not app_id:
            await query.edit_message_text("❌ Invalid service.")
            return
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("❌ API connection error. Please try again.")
            return
        
        with api_lock:
            ranges = api_client.get_ranges(app_id)
        
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
                # Also try more aggressive detection if needed
                # Aggressive detection removed to prevent false positives (e.g., matching 244 in 232...)
                pass
            
            if is_match:
                matching_ranges.append(r)
        
        # Sort ranges for Ivory Coast (22507 priority)
        if matching_ranges:
            matching_ranges = sort_ranges_for_ivory_coast(matching_ranges)
            selected_range = matching_ranges[0]  # Use first (priority) range
        else:
            selected_range = None
        
        if not selected_range:
            await query.edit_message_text(f"❌ No ranges found for {country}.")
            return
        
        range_id = selected_range.get('name', selected_range.get('id', ''))
        range_name = selected_range.get('name', '')
        
        # Show loading message and acknowledge callback immediately
        await query.edit_message_text("⏳ Requesting numbers...")
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
                
                with api_lock:
                    # Try range_name first, then range_id (like otp_tool.py)
                    numbers_data = api_client.get_multiple_numbers(range_id, range_name, number_count)
                
                if not numbers_data or len(numbers_data) == 0:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=query.message.message_id,
                        text="❌ Failed to get numbers. Please try again."
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
                        message_id=query.message.message_id,
                        text="❌ No valid numbers received. Please try again."
                    )
                    return
                
                country_name = numbers_data[0].get('cantryName', numbers_data[0].get('country', country))
                
                # Sort numbers for Ivory Coast (22507 priority)
                numbers_list = sort_numbers_for_ivory_coast(numbers_list, country_name)
                
                # Store all numbers in session (comma-separated)
                numbers_str = ','.join(numbers_list)
                update_user_session(user_id, service_name, country, range_id, numbers_str, 1)
                
                # Start monitoring all numbers in background
                job = context.job_queue.run_repeating(
                    monitor_otp,
                    interval=3,  # Increased to 3 seconds to prevent overlap
                    first=3,
                    chat_id=user_id,
                    data={'numbers': numbers_list, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time(), 'message_id': query.message.message_id}
                )
                user_jobs[user_id] = job  # Store job reference
                
                # Create inline keyboard with 5 numbers (click to copy using copy_text parameter)
                keyboard = []
                for i, num in enumerate(numbers_list, 1):
                    # Format number for display
                    display_num = num
                    if not display_num.startswith('+'):
                        digits_only = ''.join(filter(str.isdigit, display_num))
                        if len(digits_only) >= 10:
                            display_num = '+' + digits_only
                    # Use copy_text via api_kwargs - Telegram Bot API 7.0+ feature
                    # Format: {"copy_text": {"text": "number"}} - clicking button will copy the number
                    keyboard.append([InlineKeyboardButton(f"📱 {display_num}", api_kwargs={"copy_text": {"text": display_num}})])
                
                # Get country flag
                country_flag = get_country_flag(country_name)
                
                # Get service icon
                service_icons = {
                    "whatsapp": "💬",
                    "facebook": "👥",
                    "telegram": "✈️"
                }
                service_icon = service_icons.get(service_name, "📱")
                
                keyboard.append([InlineKeyboardButton("🔄 Next Number", callback_data=f"country_{service_name}_{country}")])
                keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_services")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Format message like the reference image
                message = f"Country: {country_flag} {country_name}\n"
                message += f"Service: {service_icon} {service_name.capitalize()}\n"
                message += f"Waiting for OTP...... ⏳"
                
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=query.message.message_id,
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
                        message_id=query.message.message_id,
                        text=f"❌ Error: {str(e)}"
                    )
                except:
                    pass
        
        # Run in background
        import asyncio
        asyncio.create_task(fetch_and_send_numbers())
        return
    
    # Range checker service selection from dynamic list (Others)
    elif data.startswith("rangechkr_serviceapp_"):
        idx = int(data.split("_")[2])
        other_apps = context.user_data.get('rangechkr_other_services', [])
        if idx < 0 or idx >= len(other_apps):
            await query.edit_message_text("❌ Invalid service.")
            return
        service_app = other_apps[idx]
        service_name = service_app.get('id')
        service_label = service_app.get('name', service_name)
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("❌ API connection error. Please try again.")
            return
        
        await query.edit_message_text(f"⏳ Loading ranges for {service_label}...")
        
        try:
            with api_lock:
                ranges = api_client.get_ranges(service_name)
            
            if not ranges or len(ranges) == 0:
                await query.edit_message_text(f"❌ No ranges found for {service_label}.")
                return
        except Exception as e:
            logger.error(f"Error fetching ranges for {service_label}: {e}")
            await query.edit_message_text(f"❌ Failed to load ranges for {service_label}.")
            return
    # Range checker service selection
    elif data.startswith("rangechkr_service_"):
        service_name = data.split("_")[2]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("❌ API connection error. Please try again.")
            return
        
        await query.edit_message_text("⏳ Loading ranges...")
        
        try:
            # Handle "others" - first show dynamic service list
            if service_name == "others":
                try:
                    with api_lock:
                        apps = api_client.get_applications()
                    if not apps:
                        await query.edit_message_text("❌ No services found.")
                        return

                    primary_ids = set(SERVICE_APP_IDS.values())
                    other_apps = []
                    for app in apps:
                        app_id = app.get('appId') or app.get('id')
                        app_name = app.get('name') or app.get('application') or app_id
                        if app_id and app_id not in primary_ids:
                            other_apps.append({"id": app_id, "name": app_name})

                    if not other_apps:
                        await query.edit_message_text("❌ No other services available.")
                        return

                    context.user_data['rangechkr_other_services'] = other_apps

                    keyboard = []
                    for idx, app in enumerate(other_apps):
                        label = app['name'] or app['id']
                        keyboard.append([InlineKeyboardButton(label, callback_data=f"rangechkr_serviceapp_{idx}")])
                    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="rangechkr_back_services")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text("📋 Select a service:", reply_markup=reply_markup)
                except Exception as e:
                    logger.error(f"Error loading applications for rangechkr: {e}")
                    await query.edit_message_text("❌ Failed to load services. Please try again.")
                return
            else:
                # Handle specific services (WhatsApp, Facebook)
                app_id = resolve_app_id(service_name, context)
                if not app_id:
                    await query.edit_message_text("❌ Invalid service.")
                    return

                with api_lock:
                    ranges = api_client.get_ranges(app_id)

                if not ranges or len(ranges) == 0:
                    await query.edit_message_text(f"❌ No ranges found for {service_name.upper()}.")
                    return
            
            # Create keyboard with ranges
            keyboard = []
            # Store range mapping in context for this user (using hash to keep callback_data short)
            if 'range_mapping' not in context.user_data:
                context.user_data['range_mapping'] = {}
            
            # Group ranges in rows of 2
            for i in range(0, len(ranges), 2):
                row = []
                range1 = ranges[i]
                range_name1 = range1.get('name', range1.get('id', ''))
                # Use 'name' as primary identifier, fallback to 'id'
                range_id1 = range1.get('name') or range1.get('id', '')
                # Also get the 'id' field separately (might be different from name)
                range_id_field1 = range1.get('id', '')
                # For "others", get actual service from range's _service field
                actual_service = range1.get('_service', service_name) if service_name == "others" else service_name
                # Create short hash for callback_data (max 64 bytes limit)
                range_hash1 = hashlib.md5(f"{actual_service}_{range_id1}".encode()).hexdigest()[:12]
                # Store both range_name and range_id (like otp_tool.py)
                context.user_data['range_mapping'][range_hash1] = {
                    'service': actual_service,  # Store actual service (e.g., "telegram") not "others"
                    'range_id': range_id1,
                    'range_name': range_name1,
                    'range_id_field': range_id_field1
                }
                # Truncate long range names
                display_name1 = range_name1[:20] + "..." if len(range_name1) > 20 else range_name1
                row.append(InlineKeyboardButton(display_name1, callback_data=f"rng_{range_hash1}"))
                
                if i + 1 < len(ranges):
                    range2 = ranges[i + 1]
                    range_name2 = range2.get('name', range2.get('id', ''))
                    # Use 'name' as primary identifier, fallback to 'id'
                    range_id2 = range2.get('name') or range2.get('id', '')
                    # Also get the 'id' field separately (might be different from name)
                    range_id_field2 = range2.get('id', '')
                    # For "others", get actual service from range's _service field
                    actual_service2 = range2.get('_service', service_name) if service_name == "others" else service_name
                    range_hash2 = hashlib.md5(f"{actual_service2}_{range_id2}".encode()).hexdigest()[:12]
                    # Store both range_name and range_id (like otp_tool.py)
                    context.user_data['range_mapping'][range_hash2] = {
                        'service': actual_service2,  # Store actual service (e.g., "telegram") not "others"
                        'range_id': range_id2,
                        'range_name': range_name2,
                        'range_id_field': range_id_field2
                    }
                    display_name2 = range_name2[:20] + "..." if len(range_name2) > 20 else range_name2
                    row.append(InlineKeyboardButton(display_name2, callback_data=f"rng_{range_hash2}"))
                
                keyboard.append(row)
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Services", callback_data="rangechkr_back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            display_service_name = "Others" if service_name == "others" else service_name.upper()
            await query.edit_message_text(
                f"📋 {display_service_name} Ranges ({len(ranges)} available):\n\nSelect a range:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error loading ranges: {e}")
            await query.edit_message_text(f"❌ Error loading ranges: {str(e)}")
    
    # Range checker range selection (using hash)
    elif data.startswith("rng_"):
        range_hash = data.split("_", 1)[1]
        
        # Retrieve range info from context
        logger.info(f"Range hash received: {range_hash}, user_data keys: {list(context.user_data.keys())}")
        if 'range_mapping' not in context.user_data:
            logger.error(f"range_mapping not found in user_data for user {user_id}")
            await query.edit_message_text("❌ Range mapping not found. Please select range again from /rangechkr.")
            return
        
        if range_hash not in context.user_data['range_mapping']:
            logger.error(f"Range hash {range_hash} not found in mapping. Available hashes: {list(context.user_data['range_mapping'].keys())}")
            await query.edit_message_text("❌ Range not found. Please select range again from /rangechkr.")
            return
        
        range_info = context.user_data['range_mapping'][range_hash]
        service_name = range_info['service']
        range_id = range_info['range_id']
        range_name = range_info.get('range_name', range_id)
        range_id_field = range_info.get('range_id_field', '')
        
        logger.info(f"Retrieved range: service={service_name}, range_id={range_id}, range_name={range_name}, range_id_field={range_id_field}")
        
        await query.edit_message_text("⏳ Requesting numbers from range...")
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
                        message_id=query.message.message_id,
                        text="❌ API connection error. Please try again."
                    )
                    return
                
                # Get user's number count preference
                session = get_user_session(user_id)
                number_count = session.get('number_count', 2) if session else 2
                
                with api_lock:
                    logger.info(f"Calling get_multiple_numbers with range_name={range_name}, range_id={range_id}, count={number_count}")
                    # Try range_name first, then range_id (like otp_tool.py)
                    numbers_data = api_client.get_multiple_numbers(range_id, range_name, number_count)
                    logger.info(f"get_multiple_numbers returned: {numbers_data}")
                
                if not numbers_data or len(numbers_data) == 0:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=query.message.message_id,
                        text="❌ Failed to get numbers from this range. Please try again."
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
                        message_id=query.message.message_id,
                        text="❌ No valid numbers received. Please try again."
                    )
                    return
                
                # Get service info
                app_id = resolve_app_id(service_name, context)
                if not app_id:
                    logger.error(f"Invalid service_name in range selection: {service_name}")
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=query.message.message_id,
                        text=f"❌ Invalid service: {service_name}"
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
                for num in numbers_list:
                    display_num = num
                    # Use copy_text via api_kwargs - no callback_data needed for copy
                    keyboard.append([InlineKeyboardButton(
                        f"📱 {display_num}",
                        api_kwargs={"copy_text": {"text": display_num}}
                    )])
                
                # Use hash for change numbers button too
                change_hash = hashlib.md5(f"{service_name}_{range_id}".encode()).hexdigest()[:12]
                context.user_data['range_mapping'][change_hash] = {'service': service_name, 'range_id': range_id}
                keyboard.append([InlineKeyboardButton("🔄 Change Numbers", callback_data=f"rng_{change_hash}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Get country flag
                country_flag = get_country_flag(country_name) if country_name else "🌍"
                
                # Get service icon
                service_icons = {
                    "whatsapp": "💬",
                    "facebook": "👥",
                    "telegram": "✈️"
                }
                service_icon = service_icons.get(service_name, "📱")
                
                message_text = f"{service_icon} {service_name.upper()}\n"
                if country_name:
                    message_text += f"{country_flag} {country_name}\n"
                message_text += f"📋 Range: {range_id}\n\n"
                message_text += f"✅ {len(numbers_list)} numbers received:\n\n"
                message_text += "Tap a number to copy it."
                
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=query.message.message_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
                
                # Store numbers and start monitoring
                update_user_session(user_id, service=service_name, range_id=range_id, number=','.join(numbers_list), monitoring=1)
                
                # Start OTP monitoring job
                if user_id in user_jobs:
                    old_job = user_jobs[user_id]
                    old_job.schedule_removal()
                
                # Add country to job data if available
                job_data = {
                    'user_id': user_id,
                    'numbers': numbers_list,
                    'service': service_name,
                    'range_id': range_id,
                    'start_time': time.time()
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
                logger.error(f"Error fetching range numbers: {e}")
                import traceback
                logger.error(traceback.format_exc())
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=query.message.message_id,
                        text=f"❌ Error: {str(e)}\n\nRange ID: {range_id}\nService: {service_name}"
                    )
                except:
                    pass
        
        # Run async task
        import asyncio
        asyncio.create_task(fetch_and_send_range_numbers())
    
    # Range checker back to services
    elif data == "rangechkr_back_services":
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", callback_data="rangechkr_service_whatsapp")],
            [InlineKeyboardButton("👥 Facebook", callback_data="rangechkr_service_facebook")],
            [InlineKeyboardButton("✨ Others", callback_data="rangechkr_service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🗂️ Select service to view ranges:",
            reply_markup=reply_markup
        )
    
    # Back to services
    elif data == "back_services":
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("👥 Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("✨ Others", callback_data="service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🎯 Select a service:",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (keyboard button presses)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await update.message.reply_text("❌ Your access is pending approval.")
        return
    
    # Handle "Get Number" button
    if text in ("Get Number", "📲 Get Number"):
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("👥 Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("✨ Others", callback_data="service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🎯 Select a service:",
            reply_markup=reply_markup
        )
        return
    
    # Handle direct range input (e.g., 244912XXX) - skip service selection
    # Check if message matches range pattern
    if re.match(r'^\d{6,}X+$', text, re.IGNORECASE):
        # User typed a range directly - call rangechkr logic
        await rangechkr(update, context)
        return
    
    # Handle "Set Number Count" button
    if text in ("Set Number Count", "🧮 Set Number Count"):
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
            f"📊 Set how many numbers you want to receive:\n\n"
            f"Current setting: {current_count} numbers",
            reply_markup=reply_markup
        )
        return
    
    # Handle "My Stats" button
    if text in ("My Stats", "📊 My Stats"):
        today_count = get_today_otp_count(user_id)
        bd_now = get_bd_now()
        await update.message.reply_text(
            "📊 My Stats\n\n"
            f"🕒 BD time now: {bd_now.strftime('%Y-%m-%d %I:%M:%S %p')}\n"
            f"✅ Today you received: {today_count} OTP(s)."
        )
        return
    
    # Handle service selection (old format - for backward compatibility)
    if text in ["💬 WhatsApp", "👥 Facebook", "✈️ Telegram"]:
        service_map = {
            "💬 WhatsApp": "whatsapp",
            "👥 Facebook": "facebook",
            "✈️ Telegram": "telegram"
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
            await update.message.reply_text("❌ API connection error. Please try again.")
            return
        
        try:
            with api_lock:
                ranges = api_client.get_ranges(app_id)
            
            if not ranges:
                await update.message.reply_text(f"❌ No active ranges available for {service_name}.")
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
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📱 {service_name.upper()} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in handle_message service selection: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    # Handle direct range input (e.g., "24491501XXX" or "24491501")
    elif re.match(r'^[\dXx]+$', text) and len(text) >= 6:
        # Looks like a range pattern - search across all services
        range_pattern = text.upper()
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await update.message.reply_text("❌ API connection error. Please try again.")
            return
        
        service_map = {
            "whatsapp": "verifyed-access-whatsapp",
            "facebook": "verifyed-access-facebook",
            "telegram": "verifyed-access-telegram"
        }
        
        # Search for range across all services
        found_range = None
        found_service = None
        
        await update.message.reply_text("⏳ Searching for range...")
        
        try:
            for service_name, app_id in service_map.items():
                with api_lock:
                    ranges = api_client.get_ranges(app_id)
                
                # Search for matching range
                for r in ranges:
                    range_name = r.get('name', r.get('id', ''))
                    range_id = r.get('id', r.get('name', ''))
                    
                    # Check if range matches pattern (remove X's and compare)
                    range_clean = str(range_name).replace('X', '').replace('x', '').replace('+', '').replace('-', '').replace(' ', '')
                    pattern_clean = range_pattern.replace('X', '').replace('x', '')
                    
                    # Try exact match or partial match
                    if pattern_clean in range_clean or range_clean.startswith(pattern_clean) or pattern_clean.startswith(range_clean[:len(pattern_clean)]):
                        found_range = r
                        found_service = service_name
                        break
                
                if found_range:
                    break
            
            if not found_range:
                await update.message.reply_text(f"❌ Range '{text}' not found in any service.")
                return
            
            # Found range - get numbers (like otp_tool.py)
            range_name = found_range.get('name', '')
            range_id = found_range.get('id', found_range.get('name', ''))
            
            # Get user's number count preference
            session = get_user_session(user_id)
            number_count = session.get('number_count', 2) if session else 2
            
            with api_lock:
                # Try range_name first, then range_id (like otp_tool.py)
                numbers_data = api_client.get_multiple_numbers(range_id, range_name, number_count)
            
            if not numbers_data or len(numbers_data) == 0:
                await update.message.reply_text("❌ Failed to get numbers from this range. Please try again.")
                return
            
            # Extract numbers
            numbers_list = []
            for num_data in numbers_data:
                number = num_data.get('number', '')
                if number:
                    numbers_list.append(number)
            
            if not numbers_list:
                await update.message.reply_text("❌ No valid numbers received. Please try again.")
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
                # Use copy_text via api_kwargs - no callback_data needed for copy
                keyboard.append([InlineKeyboardButton(
                    f"📱 {display_num}",
                    api_kwargs={"copy_text": {"text": display_num}}
                )])
            
            # Use hash for change numbers button
            if 'range_mapping' not in context.user_data:
                context.user_data['range_mapping'] = {}
            change_hash = hashlib.md5(f"{found_service}_{range_id}".encode()).hexdigest()[:12]
            context.user_data['range_mapping'][change_hash] = {'service': found_service, 'range_id': range_id}
            keyboard.append([InlineKeyboardButton("🔄 Change Numbers", callback_data=f"rng_{change_hash}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Get country flag
            country_flag = get_country_flag(country_name) if country_name else "🌍"
            
            # Get service icon
            service_icons = {
                "whatsapp": "💬",
                "facebook": "👥",
                "telegram": "✈️"
            }
            service_icon = service_icons.get(found_service, "📱")
            
            message_text = f"{service_icon} {found_service.upper()}\n"
            if country_name:
                message_text += f"{country_flag} {country_name}\n"
            message_text += f"📋 Range: {range_id}\n\n"
            message_text += f"✅ {len(numbers_list)} numbers received:\n\n"
            message_text += "Tap a number to copy it."
            
            sent_msg = await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
            
            # Store numbers and start monitoring
            update_user_session(user_id, service=found_service, range_id=range_id, number=','.join(numbers_list), monitoring=1)
            
            # Start OTP monitoring job
            if user_id in user_jobs:
                old_job = user_jobs[user_id]
                old_job.schedule_removal()
            
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
            await update.message.reply_text(f"❌ Error: {error_msg}")
    
    # Handle country selection (old format - for backward compatibility)
    elif any(text.startswith(f) for f in ["🇦🇴", "🇰🇲", "🇷🇴", "🇩🇰", "🇧🇩", "🇮🇳", "🇺🇸", "🇬🇧", "🌍"]) or "🔙" in text:
        if text == "🔙 Back":
            keyboard = [
                [KeyboardButton("📲 Get Number")],
                [KeyboardButton("🧮 Set Number Count")],
                [KeyboardButton("📊 My Stats")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(
                "✨ Ready when you are — tap 📲 Get Number to start:",
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
            await update.message.reply_text("❌ API connection error. Please try again.")
            return
        
        try:
            with api_lock:
                ranges = api_client.get_ranges(app_id)
            
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
                await update.message.reply_text(f"❌ No ranges found for {country}.")
                return
            
            range_id = selected_range.get('name', selected_range.get('id', ''))
            range_name = selected_range.get('name', '')
            
            # Get user's number count preference
            session = get_user_session(user_id)
            number_count = session.get('number_count', 2) if session else 2
            
            # Request numbers
            await update.message.reply_text(f"⏳ Requesting {number_count} number(s)...")
            
            with api_lock:
                # Try range_name first, then range_id (like otp_tool.py)
                numbers_data = api_client.get_multiple_numbers(range_id, range_name, number_count)
            
            if not numbers_data or len(numbers_data) == 0:
                await update.message.reply_text("❌ Failed to get numbers. Please try again.")
                return
            
            # Extract numbers and store them
            numbers_list = []
            for num_data in numbers_data:
                number = num_data.get('number', '')
                if number:
                    numbers_list.append(number)
            
            if not numbers_list:
                await update.message.reply_text("❌ No valid numbers received. Please try again.")
                return
            
            country_name = numbers_data[0].get('cantryName', numbers_data[0].get('country', country))
            
            # Sort numbers for Ivory Coast (22507 priority)
            numbers_list = sort_numbers_for_ivory_coast(numbers_list, country_name)
            
            # Store all numbers in session (comma-separated)
            numbers_str = ','.join(numbers_list)
            update_user_session(user_id, service_name, country, range_id, numbers_str, 1)
            
            # Start monitoring all numbers in background
            job = context.job_queue.run_repeating(
                monitor_otp,
                interval=2,
                first=2,
                chat_id=user_id,
                data={'numbers': numbers_list, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time(), 'message_id': sent_msg.message_id}
            )
            user_jobs[user_id] = job
            
            # Create inline keyboard with 5 numbers (click to copy supported via <code> tag)
            keyboard = []
            for i, num in enumerate(numbers_list, 1):
                # Format number for display
                display_num = num
                if not display_num.startswith('+'):
                    digits_only = ''.join(filter(str.isdigit, display_num))
                    if len(digits_only) >= 10:
                        display_num = '+' + digits_only
                # Use copy_text via api_kwargs - Telegram Bot API 7.0+ feature
                # Format: {"copy_text": {"text": "number"}} - clicking button will copy the number directly
                keyboard.append([InlineKeyboardButton(f"📱 {display_num}", api_kwargs={"copy_text": {"text": display_num}})])
            
            # Get country flag
            country_flag = get_country_flag(country_name)
            
            # Get service icon
            service_icons = {
                "whatsapp": "💬",
                "facebook": "👥",
                "telegram": "✈️"
            }
            service_icon = service_icons.get(service_name, "📱")
            
            keyboard.append([InlineKeyboardButton("🔄 Next Number", callback_data=f"country_{service_name}_{country_name}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Format message like the reference image
            message = f"Country: {country_flag} {country_name}\n"
            message += f"Service: {service_icon} {service_name.capitalize()}\n"
            message += f"Waiting for OTP...... ⏳"
            
            sent_msg = await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in handle_message country selection: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

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
        logger.error(f"❌ monitor_otp: user_id is None! job_data: {job_data}, job.chat_id: {job.chat_id}")
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
        job.schedule_removal()
        if user_id in user_jobs:
            del user_jobs[user_id]
        update_user_session(user_id, monitoring=0)
        try:
            # Edit the existing message instead of sending a new one
            if message_id:
                await context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=f"⏱️ Timeout! No OTP received within 15 minutes."
                )
            else:
                # Fallback to sending new message if message_id not available
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏱️ Timeout! No OTP received within 15 minutes."
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
            with api_lock:
                otp_results = api_client.check_otp_batch(numbers)
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
                    logger.info(f"✅ OTP detected for {number}: {otp}")
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
                    
                    # Format number for display (remove + for display, keep digits only)
                    display_number = number
                    if display_number.startswith('+'):
                        display_number = display_number[1:]  # Remove + for display
                    else:
                        digits_only = ''.join(filter(str.isdigit, display_number))
                        if len(digits_only) >= 10:
                            display_number = digits_only
                    
                    # Get country flag and code
                    country_flag = get_country_flag(country)
                    country_code = get_country_code(country)
                    
                    # Detect language from SMS content
                    language = detect_language_from_sms(sms_content) if sms_content else 'English'
                    
                    # Format OTP message for USER: "🇩🇰 #DK WhatsApp <code>4540797881</code> English"
                    # Use <code> tag for click-to-copy (Telegram default format)
                    user_otp_msg = f"{country_flag} #{country_code} {service.capitalize()} <code>{display_number}</code> {language}"
                    
                    # Format OTP message for CHANNEL: "🇩🇰 #DK WhatsApp 4540XXXX81 English"
                    # Mask number for channel (middle digits with XXXX)
                    masked_number = mask_number(number)
                    if masked_number.startswith('+'):
                        masked_number = masked_number[1:]  # Remove + for display
                    channel_otp_msg = f"{country_flag} #{country_code} {service.capitalize()} {masked_number} {language}"
                    
                    # Create inline keyboard with OTP copy button
                    keyboard = [[InlineKeyboardButton(f"🔐 {otp}", api_kwargs={"copy_text": {"text": otp}})]] 
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send OTP message to user FIRST (important!)
                    user_message_sent = False
                    try:
                        logger.info(f"Attempting to send OTP to user {user_id} for number {number}: {otp}")
                        sent_msg = await context.bot.send_message(
                            chat_id=user_id,
                            text=user_otp_msg,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                        user_message_sent = True
                        logger.info(f"✅ OTP message sent successfully to user {user_id} (message_id: {sent_msg.message_id}) for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"❌ Error sending OTP message to user {user_id}: {type(e).__name__}: {e}")
                        logger.error(f"   OTP was: {otp}, Number: {number}, Message: {user_otp_msg}")
                        # Still try to send to channel even if user message fails
                    
                    # Send OTP message to channel (with masked number)
                    try:
                        await context.bot.send_message(
                            chat_id=OTP_CHANNEL_ID,
                            text=channel_otp_msg,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                        logger.info(f"✅ OTP forwarded to channel {OTP_CHANNEL_ID} for {number}: {otp}")
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
                        logger.info(f"✅ All numbers received OTP for user {user_id}, stopping monitoring")
                        job.schedule_removal()
                        if user_id in user_jobs:
                            del user_jobs[user_id]
                        update_user_session(user_id, monitoring=0)
                        return
                    # Otherwise, continue monitoring for remaining numbers
    except Exception as e:
        logger.error(f"Error monitoring OTP for user {user_id}: {e}")
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
        logger.info("✅ API client initialized (login will retry on first API call if needed)")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
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
            logger.error(f"❌ Error: {error}", exc_info=error)
    
    application.add_error_handler(error_handler)
    
    # Start bot with drop_pending_updates to avoid conflicts
    logger.info("Bot starting...")
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
    except Conflict as e:
        logger.error(f"❌ Conflict error on startup: {e}. Another bot instance may be running.")
        logger.info("💡 If you're sure only one instance should run, wait a few seconds and the bot will retry.")
        # Wait and retry once
        import time
        time.sleep(10)
        logger.info("🔄 Retrying bot startup...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )

if __name__ == "__main__":
    main()

