import os
<<<<<<< HEAD
import threading
import time
=======
import sys
import threading
import time
import signal
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
from datetime import datetime
import requests
import json
import re
<<<<<<< HEAD
import hashlib
=======
import asyncio
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import logging
from supabase import create_client, Client
<<<<<<< HEAD
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
=======
from flask import Flask, request, Response
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

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

<<<<<<< HEAD
# Bot Configuration (from environment variables)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8348617982:AAGYXuOo6g8YNDTI079yf9nV0nf-zmFFHvA")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "7325836764"))
OTP_CHANNEL_ID = int(os.getenv("OTP_CHANNEL_ID", "-1002724043027"))  # Channel ID for forwarding OTP messages

# API Configuration (from otp_tool.py)
BASE_URL = "https://v2.mnitnetwork.com"
API_EMAIL = os.getenv("API_EMAIL", "roni791158@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "47611858@Dove")
=======
# Bot Configuration
BOT_TOKEN = "8354306480:AAEwHbjWU1Hyz_W6wTExyMZ_bVhSr-YwMfs"
ADMIN_USER_ID = 7325836764

# API Configuration (from otp_tool.py)
BASE_URL = "https://v2.mnitnetwork.com"
API_EMAIL = "roni791158@gmail.com"
API_PASSWORD = "47611858@Dove"
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sgnnqvfoajqsfdyulolm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNnbm5xdmZvYWpxc2ZkeXVsb2xtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNzE1MjcsImV4cCI6MjA3OTc0NzUyN30.dFniV0odaT-7bjs5iQVFQ-N23oqTGMAgQKjswhaHSP4")

<<<<<<< HEAD
# Supabase Database setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
=======
# ==================== SUPABASE CLIENT ====================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_database():
    """Initialize Supabase client (already done above, this is for compatibility)"""
    try:
        # Test connection - use telegram_user_id as per working bot schema
        supabase.table('users').select('telegram_user_id').limit(1).execute()
        logger.info("✅ Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Error testing Supabase connection: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# Global locks for thread safety
# Database will be initialized on first use to avoid blocking startup
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
user_jobs = {}  # Store monitoring jobs per user

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
<<<<<<< HEAD
        with db_lock:
            result = supabase.table('users').select('status').eq('user_id', user_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]['status']
        return None
    except Exception as e:
        logger.error(f"Error getting user status: {e}")
        return None
=======
        result = supabase.table('users').select('status').eq('telegram_user_id', user_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]['status']
        # If user not found in database, return 'pending' (not None)
        # This ensures new users are blocked until approved
        return 'pending'
    except Exception as e:
        logger.error(f"Error in get_user_status: {e}")
        # On error, default to 'pending' for security
        return 'pending'
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

def add_user(user_id, username):
    """Add new user to database"""
    try:
<<<<<<< HEAD
        with db_lock:
            supabase.table('users').upsert({
                'user_id': user_id,
                'username': username,
                'status': 'pending'
            }).execute()
    except Exception as e:
        logger.error(f"Error adding user: {e}")
=======
        # Check if user exists first
        existing = supabase.table('users').select('telegram_user_id').eq('telegram_user_id', user_id).execute()
        if not existing.data:
            new_user = {
                'telegram_user_id': user_id,
                'username': username,
                'status': 'pending'
            }
            supabase.table('users').insert(new_user).execute()
    except Exception as e:
        logger.error(f"Error in add_user: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

def approve_user(user_id):
    """Approve user in database"""
    try:
<<<<<<< HEAD
        with db_lock:
            supabase.table('users').update({
                'status': 'approved',
                'approved_at': datetime.now().isoformat()
            }).eq('user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error approving user: {e}")
=======
        update_data = {
            'status': 'approved',
            'approved_at': datetime.now().isoformat()
        }
        supabase.table('users').update(update_data).eq('telegram_user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error in approve_user: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

def reject_user(user_id):
    """Reject user in database"""
    try:
<<<<<<< HEAD
        with db_lock:
            supabase.table('users').update({
                'status': 'rejected'
            }).eq('user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error rejecting user: {e}")
=======
        supabase.table('users').update({'status': 'rejected'}).eq('telegram_user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error in reject_user: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

def remove_user(user_id):
    """Remove user from database"""
    try:
<<<<<<< HEAD
        with db_lock:
            supabase.table('users').delete().eq('user_id', user_id).execute()
            supabase.table('user_sessions').delete().eq('user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error removing user: {e}")
=======
        # Delete from user_sessions first (due to foreign key) - but check if table exists
        try:
            supabase.table('user_sessions').delete().eq('user_id', user_id).execute()
        except:
            pass  # Table might not exist, skip
        # Then delete from users
        supabase.table('users').delete().eq('telegram_user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error in remove_user: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

def get_pending_users():
    """Get list of pending users"""
    try:
<<<<<<< HEAD
        with db_lock:
            result = supabase.table('users').select('user_id, username').eq('status', 'pending').execute()
            return [(row['user_id'], row['username']) for row in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error getting pending users: {e}")
=======
        result = supabase.table('users').select('telegram_user_id, username').eq('status', 'pending').execute()
        return [(user['telegram_user_id'], user['username']) for user in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error in get_pending_users: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        return []

def get_all_users():
    """Get all users"""
    try:
<<<<<<< HEAD
        with db_lock:
            result = supabase.table('users').select('user_id, username, status').execute()
            return [(row['user_id'], row['username'], row['status']) for row in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
=======
        result = supabase.table('users').select('telegram_user_id, username, status').execute()
        return [(user['telegram_user_id'], user['username'], user['status']) for user in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error in get_all_users: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        return []

def update_user_session(user_id, service=None, country=None, range_id=None, number=None, monitoring=0):
    """Update user session in database"""
    try:
<<<<<<< HEAD
        with db_lock:
            supabase.table('user_sessions').upsert({
                'user_id': user_id,
                'selected_service': service,
                'selected_country': country,
                'range_id': range_id,
                'number': number,
                'monitoring': monitoring,
                'last_check': datetime.now().isoformat()
            }).execute()
    except Exception as e:
        logger.error(f"Error updating user session: {e}")
=======
        # For now, user_sessions table might not exist in Supabase
        # We can skip this or use bot_sessions like working bot
        # For simplicity, we'll skip session storage for now since it's optional
        pass
    except Exception as e:
        logger.error(f"Error in update_user_session: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

def get_user_session(user_id):
    """Get user session from database"""
    try:
<<<<<<< HEAD
        with db_lock:
            result = supabase.table('user_sessions').select('*').eq('user_id', user_id).execute()
            if result.data and len(result.data) > 0:
                row = result.data[0]
                return {
                    'user_id': row['user_id'],
                    'service': row.get('selected_service'),
                    'country': row.get('selected_country'),
                    'range_id': row.get('range_id'),
                    'number': row.get('number'),
                    'monitoring': row.get('monitoring', 0)
                }
        return None
    except Exception as e:
        logger.error(f"Error getting user session: {e}")
=======
        # For now, user_sessions table might not exist in Supabase
        # Return None - session info will be stored in memory instead
        return None
    except Exception as e:
        logger.error(f"Error in get_user_session: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        return None

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
    
    def login(self):
        """Login to API - EXACT COPY from otp_tool.py"""
        try:
            login_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.browser_headers["User-Agent"],
                "Accept": self.browser_headers["Accept"],
                "Origin": self.browser_headers["Origin"],
                "Referer": f"{self.base_url}/auth/login"
            }
            login_resp = self.session.post(
                f"{self.base_url}/api/v1/mnitnetworkcom/auth/login",
                data={"email": self.email, "password": self.password},
                headers=login_headers,
                timeout=15
            )
            
            if login_resp.status_code in [200, 201]:
                login_data = login_resp.json()
<<<<<<< HEAD
                
                # Check if response has expected structure
                if not login_data or 'data' not in login_data or not login_data.get('data'):
                    logger.error(f"Login response missing data: {login_data}")
                    return False
                
                if 'user' not in login_data['data'] or 'session' not in login_data['data']['user']:
                    logger.error(f"Login response missing user session: {login_data}")
                    return False
                
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                session_token = login_data['data']['user']['session']
                
                # Set session cookie properly
                self.session.cookies.set('mnitnetworkcom_session', session_token, domain='v2.mnitnetwork.com')
                
                # If using curl_cffi, minimal headers needed
                if self.use_curl:
                    hitauth_headers = {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Origin": self.browser_headers["Origin"],
                        "Referer": f"{self.base_url}/dashboard/getnum"
                    }
                else:
                    hitauth_headers = {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": self.browser_headers["User-Agent"],
                        "Accept": self.browser_headers["Accept"],
                        "Origin": self.browser_headers["Origin"],
                        "Referer": f"{self.base_url}/dashboard/getnum"
                    }
                hitauth_resp = self.session.post(
                    f"{self.base_url}/api/v1/mnitnetworkcom/auth/hitauth",
                    data={
                        "mnitnetworkcom_session": session_token,
                        "mnitnetworkcom_url": f"{self.base_url}/dashboard/index"
                    },
                    headers=hitauth_headers,
                    timeout=15
                )
                
                if hitauth_resp.status_code in [200, 201]:
                    hitauth_data = hitauth_resp.json()
<<<<<<< HEAD
                    
                    # Check if hitauth response has expected structure
                    if not hitauth_data or 'data' not in hitauth_data or not hitauth_data.get('data'):
                        logger.error(f"Hitauth response missing data: {hitauth_data}")
                        return False
                    
                    if 'token' not in hitauth_data['data']:
                        logger.error(f"Hitauth response missing token: {hitauth_data}")
                        return False
                    
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                    self.auth_token = hitauth_data['data']['token']
                    
                    # Set account type cookie
                    self.session.cookies.set('mnitnetworkcom_accountType', 'user', domain='v2.mnitnetwork.com')
                    
                    # Store mhitauth token in cookie (browser does this)
                    self.session.cookies.set('mnitnetworkcom_mhitauth', self.auth_token, domain='v2.mnitnetwork.com')
                    
                    logger.info("Login successful")
                    return True
<<<<<<< HEAD
                else:
                    logger.error(f"Hitauth failed with status {hitauth_resp.status_code}: {hitauth_resp.text[:200]}")
            else:
                logger.error(f"Login failed with status {login_resp.status_code}: {login_resp.text[:200]}")
=======
            logger.error(f"Login failed with status {login_resp.status_code}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def get_ranges(self, app_id):
        """Get active ranges for an application"""
        try:
            if not self.auth_token:
                if not self.login():
                    return []
            
            headers = {
                "mhitauth": self.auth_token,
                **{k: v for k, v in self.browser_headers.items() if k not in ["Origin", "Referer", "Content-Type"]}
            }
            headers["Origin"] = self.base_url
            headers["Referer"] = f"{self.base_url}/dashboard/getnum"
            
            resp = self.session.get(
                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getac?type=carriers&appId={app_id}",
                headers=headers,
                timeout=15
            )
            
            # Check if token expired
            if resp.status_code == 401 or (resp.status_code == 200 and 'expired' in resp.text.lower()):
                logger.info("Token expired, refreshing...")
                if self.login():
                    # Retry request
                    resp = self.session.get(
                        f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getac?type=carriers&appId={app_id}",
                        headers=headers,
                        timeout=15
                    )
            
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'] is not None:
                    return data['data']
            return []
        except Exception as e:
            logger.error(f"Error getting ranges: {e}")
            return []
    
    def get_number(self, range_id):
        """Request a number from a range"""
        try:
            if not self.auth_token:
                if not self.login():
                    return None
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "mhitauth": self.auth_token,
                **{k: v for k, v in self.browser_headers.items() if k != "Content-Type"}
            }
            headers["Referer"] = f"{self.base_url}/dashboard/getnum?range={range_id}"
            
            resp = self.session.post(
                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnum",
                data={
                    "range": range_id,
                    "national": "false",
                    "removePlus": "false",
                    "app": "null",
                    "carrier": "null"
                },
                headers=headers,
                timeout=15
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data:
                    number_data = data['data']
                    if isinstance(number_data, dict):
                        if 'number' in number_data:
                            return number_data
                        elif 'num' in number_data and isinstance(number_data['num'], list) and len(number_data['num']) > 0:
                            return number_data['num'][0]
                    elif isinstance(number_data, list) and len(number_data) > 0:
                        return number_data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting number: {e}")
            return None
    
<<<<<<< HEAD
    def get_multiple_numbers(self, range_id, range_name=None, count=5):
        """Request multiple numbers from a range - try range_name first, then range_id (like otp_tool.py)"""
        numbers = []
        for i in range(count):
            # Try range_name first (like otp_tool.py line 561)
            if range_name:
                number_data = self.get_number(range_name)
            else:
                number_data = None
            
            # If range_name didn't work, try range_id (like otp_tool.py line 562-563)
            if not number_data:
                number_data = self.get_number(range_id)
            
            if number_data:
                numbers.append(number_data)
            else:
                # If we can't get more numbers, break
                break
        return numbers
    
    def check_otp(self, number):
        """Check for OTP on a number - optimized for speed"""
=======
    def check_otp(self, number):
        """Check for OTP on a number"""
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        try:
            if not self.auth_token:
                if not self.login():
                    return None
            
            today = datetime.now().strftime("%d_%m_%Y")
            timestamp = int(time.time() * 1000)
            
            headers = {
                **{k: v for k, v in self.browser_headers.items() if k not in ["Origin", "Referer", "Content-Type"]}
            }
            headers["Origin"] = self.base_url
            headers["Referer"] = f"{self.base_url}/dashboard/getnum"
            
<<<<<<< HEAD
            # Reduced timeout for faster response
            resp = self.session.get(
                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                headers=headers,
                timeout=8  # Reduced from 15 to 8 seconds
            )
            
            # Check if token expired - only retry once
            if resp.status_code == 401 or (resp.status_code == 200 and 'expired' in resp.text.lower()):
                logger.info("Token expired in check_otp, refreshing...")
                if self.login():
                    # Retry request once
                    resp = self.session.get(
                        f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                        headers=headers,
                        timeout=8
                    )
                else:
                    return None  # Login failed, return None
=======
            resp = self.session.get(
                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                headers=headers,
                timeout=15
            )
            
            # Check if token expired
            if resp.status_code == 401 or (resp.status_code == 200 and 'expired' in resp.text.lower()):
                logger.info("Token expired in check_otp, refreshing...")
                if self.login():
                    # Retry request
                    resp = self.session.get(
                        f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                        headers=headers,
                        timeout=15
                    )
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'] is not None:
                    data_obj = data['data']
                    if isinstance(data_obj, dict) and 'num' in data_obj and data_obj['num'] is not None:
                        numbers = data_obj['num']
                        if isinstance(numbers, list):
                            target_normalized = number.replace('+', '').replace(' ', '').replace('-', '').strip()
<<<<<<< HEAD
                            target_digits = ''.join(filter(str.isdigit, target_normalized))
                            
                            # Optimized search - check exact match and last 9 digits in one pass
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                            for num_data in numbers:
                                if isinstance(num_data, dict):
                                    num_value = num_data.get('number', '')
                                    num_normalized = num_value.replace('+', '').replace(' ', '').replace('-', '').strip()
<<<<<<< HEAD
                                    # Exact match
                                    if num_normalized == target_normalized:
                                        return num_data
                                    # Last 9 digits match
                                    if len(target_digits) >= 9:
=======
                                    if num_normalized == target_normalized:
                                        return num_data
                            
                            target_digits = ''.join(filter(str.isdigit, target_normalized))
                            if len(target_digits) >= 9:
                                for num_data in numbers:
                                    if isinstance(num_data, dict):
                                        num_value = num_data.get('number', '')
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                                        num_digits = ''.join(filter(str.isdigit, num_value))
                                        if len(num_digits) >= 9 and num_digits[-9:] == target_digits[-9:]:
                                            return num_data
            return None
        except Exception as e:
            logger.error(f"Error checking OTP: {e}")
            return None
<<<<<<< HEAD
    
    def check_otp_batch(self, numbers):
        """Check OTP for multiple numbers in one API call - much faster"""
        try:
            if not self.auth_token:
                if not self.login():
                    return {}
            
            today = datetime.now().strftime("%d_%m_%Y")
            timestamp = int(time.time() * 1000)
            
            headers = {
                **{k: v for k, v in self.browser_headers.items() if k not in ["Origin", "Referer", "Content-Type"]}
            }
            headers["Origin"] = self.base_url
            headers["Referer"] = f"{self.base_url}/dashboard/getnum"
            
            # Single API call for all numbers
            resp = self.session.get(
                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                headers=headers,
                timeout=8
            )
            
            # Check if token expired - only retry once
            if resp.status_code == 401 or (resp.status_code == 200 and 'expired' in resp.text.lower()):
                logger.info("Token expired in check_otp_batch, refreshing...")
                if self.login():
                    resp = self.session.get(
                        f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                        headers=headers,
                        timeout=8
                    )
                else:
                    return {}  # Login failed
            
            result = {}
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'] is not None:
                    data_obj = data['data']
                    if isinstance(data_obj, dict) and 'num' in data_obj and data_obj['num'] is not None:
                        api_numbers = data_obj['num']
                        if isinstance(api_numbers, list):
                            # Normalize all target numbers - create lookup maps
                            target_exact_match = {}  # exact normalized -> original
                            target_last9_match = {}  # last 9 digits -> original
                            
                            for num in numbers:
                                normalized = num.replace('+', '').replace(' ', '').replace('-', '').strip()
                                target_exact_match[normalized] = num
                                # Also store last 9 digits
                                digits = ''.join(filter(str.isdigit, normalized))
                                if len(digits) >= 9:
                                    target_last9_match[digits[-9:]] = num
                            
                            # Match all numbers in one pass
                            for num_data in api_numbers:
                                if isinstance(num_data, dict):
                                    num_value = num_data.get('number', '')
                                    num_normalized = num_value.replace('+', '').replace(' ', '').replace('-', '').strip()
                                    num_digits = ''.join(filter(str.isdigit, num_value))
                                    
                                    # Check exact match first
                                    if num_normalized in target_exact_match:
                                        original_num = target_exact_match[num_normalized]
                                        if original_num not in result:  # Don't overwrite if already found
                                            result[original_num] = num_data
                                    # Check last 9 digits match
                                    elif len(num_digits) >= 9 and num_digits[-9:] in target_last9_match:
                                        original_num = target_last9_match[num_digits[-9:]]
                                        if original_num not in result:  # Don't overwrite if already found
                                            result[original_num] = num_data
            
            return result
        except Exception as e:
            logger.error(f"Error checking OTP batch: {e}")
            return {}
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

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
    'Burkina Faso': '🇧🇫', 'Burundi': '🇧🇮', 'Cambodia': '🇰🇭', 'Canada': '🇨🇦',
    'Chile': '🇨🇱', 'China': '🇨🇳', 'Colombia': '🇨🇴', 'Congo': '🇨🇬',
    'Costa Rica': '🇨🇷', 'Croatia': '🇭🇷', 'Cuba': '🇨🇺', 'Cyprus': '🇨🇾',
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

<<<<<<< HEAD
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

def detect_language_from_sms(sms_content):
    """Detect language from SMS content"""
    if not sms_content:
        return 'Unknown'
    
    sms_lower = sms_content.lower()
    
    # Common language indicators
    language_keywords = {
        'English': ['code', 'verification', 'otp', 'password', 'confirm', 'verify', 'your code is', 'use this code'],
        'Spanish': ['código', 'verificación', 'contraseña', 'confirmar', 'verificar', 'tu código es'],
        'French': ['code', 'vérification', 'mot de passe', 'confirmer', 'vérifier', 'votre code est'],
        'German': ['code', 'bestätigung', 'passwort', 'bestätigen', 'verifizieren', 'ihr code ist'],
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
        'Dutch': ['code', 'verificatie', 'wachtwoord', 'bevestigen', 'verifiëren', 'uw code is'],
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
    
    # Check for language keywords
    for lang, keywords in language_keywords.items():
        for keyword in keywords:
            if keyword in sms_lower:
                return lang
    
    # Default to English if no match found
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
    
    service_map = {
        "whatsapp": "verifyed-access-whatsapp",
        "facebook": "verifyed-access-facebook",
        "telegram": "verifyed-access-telegram"
    }
    
    # Show service selection first
    keyboard = [
        [InlineKeyboardButton("WhatsApp", callback_data="rangechkr_service_whatsapp")],
        [InlineKeyboardButton("Facebook", callback_data="rangechkr_service_facebook")],
        [InlineKeyboardButton("Others", callback_data="rangechkr_service_others")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📋 Select service to view ranges:",
        reply_markup=reply_markup
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"
    
    # Add user to database
    add_user(user_id, username)
    
    status = get_user_status(user_id)
    
    if status == 'approved':
        # Show only "Get Number" button
        keyboard = [
            [KeyboardButton("Get Number")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "✅ Welcome! Click 'Get Number' to start:",
            reply_markup=reply_markup
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
=======
# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        logger.info(f"📥 /start command received from user {update.effective_user.id if update.effective_user else 'unknown'}")
        user = update.effective_user
        user_id = user.id
        username = user.username or user.first_name or "Unknown"
        
        logger.info(f"Processing /start for user {user_id} ({username})")
        
        # Add user to database
        add_user(user_id, username)
        logger.info(f"✅ User {user_id} added to database")
        
        status = get_user_status(user_id)
        logger.info(f"User {user_id} status: {status}")
        
        if status == 'approved':
            # Show service menu with ReplyKeyboardMarkup
            keyboard = [
                [KeyboardButton("💬 WhatsApp"), KeyboardButton("👥 Facebook")],
                [KeyboardButton("✈️ Telegram")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            try:
                await update.message.reply_text(
                    "✅ Welcome! Please select a service:",
                    reply_markup=reply_markup,
                    read_timeout=30,
                    write_timeout=30,
                    connect_timeout=30
                )
                logger.info(f"✅ Welcome message sent to user {user_id}")
            except Exception as e:
                logger.error(f"Error sending welcome message: {e}")
        elif status == 'rejected':
            await update.message.reply_text("❌ Your access has been rejected. Please contact admin.")
            logger.info(f"✅ Rejection message sent to user {user_id}")
        else:
            # Notify admin
            logger.info(f"User {user_id} is pending approval, notifying admin...")
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
                
                try:
                    await context.bot.send_message(
                        chat_id=ADMIN_USER_ID,
                        text=admin_message,
                        reply_markup=reply_markup,
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30
                    )
                except Exception as send_error:
                    logger.error(f"Error sending admin notification: {send_error}")
            except Exception as e:
                logger.error(f"Error notifying admin: {e}")
            
            await update.message.reply_text(
                "⏳ Your request has been sent to admin. Please wait for approval."
            )
            logger.info(f"✅ Pending message sent to user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error in start handler: {e}")
        import traceback
        traceback.print_exc()
        try:
            await update.message.reply_text("❌ An error occurred. Please try again later.")
        except:
            pass
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

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
    
    elif command.startswith("/remove"):
        try:
            target_id = int(context.args[0]) if context.args else None
            if target_id:
                # Stop any monitoring jobs for this user
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

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
<<<<<<< HEAD
    # Answer callback immediately to prevent timeout - with error handling
    try:
        await query.answer()
    except Exception as e:
        # Query might be too old, continue anyway
        logger.debug(f"Callback query answer failed (might be old): {e}")
=======
    await query.answer()
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
    
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
    
    # Service selection
    if data.startswith("service_"):
        service_name = data.split("_")[1]
<<<<<<< HEAD
=======
        service_map = {
            "whatsapp": "verifyed-access-whatsapp",
            "facebook": "verifyed-access-facebook",
            "telegram": "verifyed-access-telegram"
        }
        
        app_id = service_map.get(service_name)
        if not app_id:
            await query.edit_message_text("❌ Invalid service.")
            return
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("❌ API connection error. Please try again.")
            return
        
<<<<<<< HEAD
        # Handle "others" - get ranges from all services except WhatsApp and Facebook
        if service_name == "others":
            # List of all service app_ids except WhatsApp and Facebook
            other_services = {
                "telegram": "verifyed-access-telegram"
                # Add more services here as needed
            }
            
            # Fetch ranges from all "other" services
            all_ranges = []
            for svc_name, app_id in other_services.items():
                try:
                    with api_lock:
                        svc_ranges = api_client.get_ranges(app_id)
                    # Add service name to each range for identification
                    for r in svc_ranges:
                        r['_service'] = svc_name
                    all_ranges.extend(svc_ranges)
                except Exception as e:
                    logger.error(f"Error fetching ranges for {svc_name}: {e}")
                    continue
            
            ranges = all_ranges
            if not ranges:
                await query.edit_message_text("❌ No active ranges available in Others.")
                return
        else:
            # Handle specific services (WhatsApp, Facebook)
            service_map = {
                "whatsapp": "verifyed-access-whatsapp",
                "facebook": "verifyed-access-facebook"
            }
            
            app_id = service_map.get(service_name)
            if not app_id:
                await query.edit_message_text("❌ Invalid service.")
                return
            
            with api_lock:
                ranges = api_client.get_ranges(app_id)
            
            if not ranges:
                await query.edit_message_text(f"❌ No active ranges available for {service_name}.")
                return
=======
        with api_lock:
            ranges = api_client.get_ranges(app_id)
        
        if not ranges:
            await query.edit_message_text(f"❌ No active ranges available for {service_name}.")
            return
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        
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
        
        await query.edit_message_text(
            f"📱 {service_name.upper()} - Select Country:",
            reply_markup=reply_markup
        )
    
<<<<<<< HEAD
    # Note: num_copy_ handler removed - using copy_text parameter in InlineKeyboardButton
    # When copy_text is used, button click directly copies text without callback
    
    # Country selection
    elif data.startswith("country_"):
=======
    # Country selection
    elif data.startswith("country_"):
        # Re-check approval status for security
        status = get_user_status(user_id)
        if status != 'approved':
            await query.edit_message_text("❌ Your access is pending approval.")
            return
        
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        parts = data.split("_", 2)
        service_name = parts[1]
        country = parts[2]
        
        # Stop any existing monitoring jobs for this user
        if user_id in user_jobs:
            old_job = user_jobs[user_id]
            old_job.schedule_removal()
            del user_jobs[user_id]
        
        service_map = {
            "whatsapp": "verifyed-access-whatsapp",
            "facebook": "verifyed-access-facebook",
            "telegram": "verifyed-access-telegram"
        }
        
        app_id = service_map.get(service_name)
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
        
<<<<<<< HEAD
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
=======
        # Find ranges for this country (use first range)
        # Match by detecting country from range name, not just API country field
        selected_range = None
        for r in ranges:
            range_name = r.get('name', r.get('id', ''))
            r_country_api = r.get('cantryName', r.get('country', ''))
            
            # Try API country first (case-insensitive)
            if r_country_api and r_country_api.lower() == country.lower():
                selected_range = r
                break
            
            # Detect country from range name
            r_country_detected = detect_country_from_range(range_name)
            if r_country_detected and r_country_detected.lower() == country.lower():
                selected_range = r
                break
            
            # Also try more aggressive detection if needed
            if not r_country_detected or r_country_detected == 'Unknown':
                range_str = str(range_name).upper()
                for code, country_name in COUNTRY_CODES.items():
                    if code in range_str and country_name.lower() == country.lower():
                        selected_range = r
                        break
                if selected_range:
                    break
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        
        if not selected_range:
            await query.edit_message_text(f"❌ No ranges found for {country}.")
            return
        
        range_id = selected_range.get('name', selected_range.get('id', ''))
<<<<<<< HEAD
        range_name = selected_range.get('name', '')
        
        # Show loading message and acknowledge callback immediately
        await query.edit_message_text("⏳ Requesting numbers...")
        try:
            await query.answer()  # Acknowledge callback immediately to prevent timeout
        except Exception as e:
            logger.debug(f"Callback query answer failed (might be old): {e}")
        
        # Request 5 numbers in background (async task)
        async def fetch_and_send_numbers():
            try:
                with api_lock:
                    # Try range_name first, then range_id (like otp_tool.py)
                    numbers_data = api_client.get_multiple_numbers(range_id, range_name, 5)
                
                if not numbers_data or len(numbers_data) == 0:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=query.message.message_id,
                        text="❌ Failed to get numbers. Please try again."
                    )
                    return
                
                # Extract numbers and store them
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
                import time
                job = context.job_queue.run_repeating(
                    monitor_otp,
                    interval=3,  # Increased to 3 seconds to prevent overlap
                    first=3,
                    chat_id=user_id,
                    data={'numbers': numbers_list, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time()}
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
            # Handle "others" - get ranges from all services except WhatsApp and Facebook
            if service_name == "others":
                # List of all service app_ids except WhatsApp and Facebook
                other_services = {
                    "telegram": "verifyed-access-telegram"
                    # Add more services here as needed
                }
                
                # Fetch ranges from all "other" services
                all_ranges = []
                for svc_name, app_id in other_services.items():
                    try:
                        with api_lock:
                            svc_ranges = api_client.get_ranges(app_id)
                        # Add service name to each range for identification
                        for r in svc_ranges:
                            r['_service'] = svc_name
                        all_ranges.extend(svc_ranges)
                    except Exception as e:
                        logger.error(f"Error fetching ranges for {svc_name}: {e}")
                        continue
                
                ranges = all_ranges
                if not ranges or len(ranges) == 0:
                    await query.edit_message_text("❌ No ranges found in Others.")
                    return
            else:
                # Handle specific services (WhatsApp, Facebook)
                service_map = {
                    "whatsapp": "verifyed-access-whatsapp",
                    "facebook": "verifyed-access-facebook"
                }
                
                app_id = service_map.get(service_name)
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
        
        # Stop any existing monitoring jobs for this user
        if user_id in user_jobs:
            old_job = user_jobs[user_id]
            old_job.schedule_removal()
            del user_jobs[user_id]
        
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
                
                with api_lock:
                    logger.info(f"Calling get_multiple_numbers with range_name={range_name}, range_id={range_id}, count=5")
                    # Try range_name first, then range_id (like otp_tool.py)
                    numbers_data = api_client.get_multiple_numbers(range_id, range_name, 5)
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
                service_map = {
                    "whatsapp": "verifyed-access-whatsapp",
                    "facebook": "verifyed-access-facebook",
                    "telegram": "verifyed-access-telegram"
                }
                app_id = service_map.get(service_name)
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
            [InlineKeyboardButton("WhatsApp", callback_data="rangechkr_service_whatsapp")],
            [InlineKeyboardButton("Facebook", callback_data="rangechkr_service_facebook")],
            [InlineKeyboardButton("Others", callback_data="rangechkr_service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📋 Select service to view ranges:",
            reply_markup=reply_markup
=======
        
        # Request number
        await query.edit_message_text("⏳ Requesting number...")
        
        with api_lock:
            number_data = api_client.get_number(range_id)
        
        if not number_data:
            await query.edit_message_text("❌ Failed to get number. Please try again.")
            return
        
        number = number_data.get('number', 'N/A')
        country_name = number_data.get('cantryName', number_data.get('country', country))
        
        # Update session
        update_user_session(user_id, service_name, country, range_id, number, 1)
        
        # Start monitoring in background (5 minutes timeout = 150 checks at 2s interval)
        import time
        # Check if job_queue is available - try context first, then application
        job_queue = context.job_queue
        if job_queue is None:
            global application
            if application and application.job_queue:
                job_queue = application.job_queue
                logger.info(f"Using application.job_queue for user {user_id} (callback)")
            else:
                logger.error(f"JobQueue not available for user {user_id}. Context: {context.job_queue}, Application: {application.job_queue if application else 'None'}")
                await query.edit_message_text("❌ Error: JobQueue not initialized. Please contact admin.")
                return
        
        job = job_queue.run_repeating(
            monitor_otp,
            interval=2,
            first=2,
            chat_id=user_id,
            data={'number': number, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time()}
        )
        user_jobs[user_id] = job  # Store job reference
        logger.info(f"✅ Started OTP monitoring job for user {user_id}, number {number} (callback), job_queue: {job_queue}, job: {job}")
        
        # Make number clickable - ensure it has + prefix for Telegram auto-detection
        display_number = number
        if not display_number.startswith('+'):
            digits_only = ''.join(filter(str.isdigit, display_number))
            if len(digits_only) >= 10:
                display_number = '+' + digits_only
        
        keyboard = [[InlineKeyboardButton("🔄 Change Number", callback_data=f"country_{service_name}_{country}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ Number received!\n\n"
            f"📱 Number: <code>{display_number}</code>\n"
            f"🌍 Country: {country_name}\n"
            f"⏳ Monitoring for OTP...",
            reply_markup=reply_markup,
            parse_mode='HTML'
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        )
    
    # Back to services
    elif data == "back_services":
<<<<<<< HEAD
        keyboard = [
            [InlineKeyboardButton("WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("Telegram", callback_data="service_telegram")]
=======
        # Re-check approval status for security
        status = get_user_status(user_id)
        if status != 'approved':
            await query.edit_message_text("❌ Your access is pending approval.")
            return
        
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("👥 Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("✈️ Telegram", callback_data="service_telegram")]
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "✅ Please select a service:",
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
    
<<<<<<< HEAD
    # Handle "Get Number" button
    if text == "Get Number":
        keyboard = [
            [InlineKeyboardButton("WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("Telegram", callback_data="service_telegram")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "✅ Please select a service:",
            reply_markup=reply_markup
        )
        return
    
    # Handle service selection (old format - for backward compatibility)
=======
    # Handle service selection
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
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
    
<<<<<<< HEAD
    # Handle direct range input (e.g., "24491501XXX" or "24491501")
    elif re.match(r'^[\dXx]+$', text) and len(text) >= 6:
        # Looks like a range pattern - search across all services
        range_pattern = text.upper()
        
        # Stop any existing monitoring jobs
        if user_id in user_jobs:
            old_job = user_jobs[user_id]
            old_job.schedule_removal()
            del user_jobs[user_id]
        
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
            
            # Found range - get 5 numbers (like otp_tool.py)
            range_name = found_range.get('name', '')
            range_id = found_range.get('id', found_range.get('name', ''))
            
            with api_lock:
                # Try range_name first, then range_id (like otp_tool.py)
                numbers_data = api_client.get_multiple_numbers(range_id, range_name, 5)
            
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
            
            await update.message.reply_text(
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
            job_data = {
                'user_id': user_id,
                'numbers': numbers_list,
                'service': found_service,
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
            logger.error(f"Error handling direct range input: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    # Handle country selection (old format - for backward compatibility)
    elif any(text.startswith(f) for f in ["🇦🇴", "🇰🇲", "🇷🇴", "🇩🇰", "🇧🇩", "🇮🇳", "🇺🇸", "🇬🇧", "🌍"]) or "🔙" in text:
        if text == "🔙 Back":
            keyboard = [
                [KeyboardButton("Get Number")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(
                "✅ Click 'Get Number' to start:",
=======
    # Handle country selection
    elif any(text.startswith(f) for f in ["🇦🇴", "🇰🇲", "🇷🇴", "🇩🇰", "🇧🇩", "🇮🇳", "🇺🇸", "🇬🇧", "🌍"]) or "🔙" in text:
        # Re-check approval status for security
        status = get_user_status(user_id)
        if status != 'approved':
            await update.message.reply_text("❌ Your access is pending approval.")
            return
        
        if text == "🔙 Back":
            keyboard = [
                [KeyboardButton("💬 WhatsApp"), KeyboardButton("👥 Facebook")],
                [KeyboardButton("✈️ Telegram")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(
                "✅ Please select a service:",
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
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
        
        service_map = {
            "whatsapp": "verifyed-access-whatsapp",
            "facebook": "verifyed-access-facebook",
            "telegram": "verifyed-access-telegram"
        }
        app_id = service_map.get(service_name)
        
        # Stop any existing monitoring jobs
        if user_id in user_jobs:
            old_job = user_jobs[user_id]
            old_job.schedule_removal()
            del user_jobs[user_id]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await update.message.reply_text("❌ API connection error. Please try again.")
            return
        
        try:
            with api_lock:
                ranges = api_client.get_ranges(app_id)
            
<<<<<<< HEAD
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
=======
            # Find ranges for this country (use first range)
            # Find ranges for this country (use first range)
            # Match by detecting country from range name, not just API country field
            selected_range = None
            for r in ranges:
                range_name = r.get('name', r.get('id', ''))
                r_country_api = r.get('cantryName', r.get('country', ''))
                
                # Try API country first (case-insensitive)
                if r_country_api and r_country_api.lower() == country.lower():
                    selected_range = r
                    break
                
                # Detect country from range name
                r_country_detected = detect_country_from_range(range_name)
                if r_country_detected and r_country_detected.lower() == country.lower():
                    selected_range = r
                    break
                
                # Also try more aggressive detection if needed
                if not r_country_detected or r_country_detected == 'Unknown':
                    range_str = str(range_name).upper()
                    for code, country_name in COUNTRY_CODES.items():
                        if code in range_str and country_name.lower() == country.lower():
                            selected_range = r
                            break
                    if selected_range:
                        break
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            
            if not selected_range:
                await update.message.reply_text(f"❌ No ranges found for {country}.")
                return
            
            range_id = selected_range.get('name', selected_range.get('id', ''))
<<<<<<< HEAD
            range_name = selected_range.get('name', '')
            
            # Request 5 numbers
            await update.message.reply_text("⏳ Requesting numbers...")
            
            with api_lock:
                # Try range_name first, then range_id (like otp_tool.py)
                numbers_data = api_client.get_multiple_numbers(range_id, range_name, 5)
            
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
            import time
            job = context.job_queue.run_repeating(
=======
            
            # Request number
            await update.message.reply_text("⏳ Requesting number...")
            
            with api_lock:
                number_data = api_client.get_number(range_id)
            
            if not number_data:
                await update.message.reply_text("❌ Failed to get number. Please try again.")
                return
            
            number = number_data.get('number', 'N/A')
            country_name = number_data.get('cantryName', number_data.get('country', country))
            
            # Update session
            update_user_session(user_id, service_name, country_name, range_id, number, 1)
            
            # Start monitoring in background
            import time
            # Check if job_queue is available - try context.job_queue first, then application.job_queue
            job_queue = context.job_queue
            if job_queue is None:
                # Fallback to application's job_queue
                global application
                if application and application.job_queue:
                    job_queue = application.job_queue
                    logger.info(f"Using application.job_queue for user {user_id}")
                else:
                    logger.error(f"JobQueue not available for user {user_id}. Context: {context.job_queue}, Application: {application.job_queue if application else 'None'}")
                    await update.message.reply_text("❌ Error: JobQueue not initialized. Please contact admin.")
                    return
            
            job = job_queue.run_repeating(
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                monitor_otp,
                interval=2,
                first=2,
                chat_id=user_id,
<<<<<<< HEAD
                data={'numbers': numbers_list, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time()}
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
            
            await update.message.reply_text(
                message,
=======
                data={'number': number, 'user_id': user_id, 'country': country_name, 'service': service_name, 'start_time': time.time()}
            )
            user_jobs[user_id] = job
            logger.info(f"✅ Started OTP monitoring job for user {user_id}, number {number}")
            
            # Make number clickable - ensure it has + prefix for Telegram auto-detection
            display_number = number
            if not display_number.startswith('+'):
                digits_only = ''.join(filter(str.isdigit, display_number))
                if len(digits_only) >= 10:
                    display_number = '+' + digits_only
            
            # Show "Change Number" button
            session = get_user_session(user_id)
            service_name = session.get('service') if session else 'whatsapp'
            keyboard = [[InlineKeyboardButton("🔄 Change Number", callback_data=f"country_{service_name}_{country_name}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Number received!\n\n"
                f"📱 Number: <code>{display_number}</code>\n"
                f"🌍 Country: {country_name}\n"
                f"⏳ Monitoring for OTP...",
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in handle_message country selection: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

async def monitor_otp(context: ContextTypes.DEFAULT_TYPE):
<<<<<<< HEAD
    """Monitor OTP in background for multiple numbers - continues until all numbers receive OTP"""
    job = context.job
    job_data = job.data if hasattr(job, 'data') else {}
    # Get user_id from job_data first (always set), fallback to job.chat_id
    user_id = job_data.get('user_id') or job.chat_id
    start_time = job_data.get('start_time', time.time())
    
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
=======
    """Monitor OTP in background"""
    job = context.job
    user_id = job.chat_id
    number = job.data['number']
    start_time = job.data.get('start_time', time.time())
    
    # Debug: Log that monitoring is running
    logger.info(f"🔍 Monitoring OTP for user {user_id}, number {number} (elapsed: {int(time.time() - start_time)}s)")
    
    # Timeout after 5 minutes
    if time.time() - start_time > 300:
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        job.schedule_removal()
        if user_id in user_jobs:
            del user_jobs[user_id]
        update_user_session(user_id, monitoring=0)
        try:
<<<<<<< HEAD
            numbers_str = ', '.join(numbers)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏱️ Timeout! No OTP received for numbers within 15 minutes."
=======
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏱️ Timeout! No OTP received for number {number} within 5 minutes."
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            )
        except:
            pass
        return
    
    # Get global API client
    api_client = get_global_api_client()
    if not api_client:
        return
    
    try:
<<<<<<< HEAD
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
                    
                    # Format OTP message: "🇩🇰 #DK WhatsApp 4540797881 English"
                    otp_msg = f"{country_flag} #{country_code} {service.capitalize()} {display_number} {language}"
                    
                    # Create inline keyboard with OTP copy button
                    keyboard = [[InlineKeyboardButton(f"🔐 {otp}", api_kwargs={"copy_text": {"text": otp}})]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    # Send OTP message to user FIRST (important!)
                    user_message_sent = False
                    try:
                        logger.info(f"Attempting to send OTP to user {user_id} for number {number}: {otp}")
                        sent_msg = await context.bot.send_message(
                            chat_id=user_id,
                            text=otp_msg,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                        user_message_sent = True
                        logger.info(f"✅ OTP message sent successfully to user {user_id} (message_id: {sent_msg.message_id}) for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"❌ Error sending OTP message to user {user_id}: {type(e).__name__}: {e}")
                        logger.error(f"   OTP was: {otp}, Number: {number}, Message: {otp_msg}")
                        # Still try to send to channel even if user message fails
                    
                    # Send OTP message to channel
                    try:
                        await context.bot.send_message(
                            chat_id=OTP_CHANNEL_ID,
                            text=otp_msg,
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                        logger.info(f"✅ OTP forwarded to channel {OTP_CHANNEL_ID} for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"❌ Error sending OTP message to channel {OTP_CHANNEL_ID}: {type(e).__name__}: {e}")
                    
                    # Log warning if user message failed but channel succeeded
                    if not user_message_sent:
                        logger.warning(f"⚠️ OTP sent to channel but NOT to user {user_id} for {number}: {otp}")
                    
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
=======
        with api_lock:
            otp_data = api_client.check_otp(number)
        
        # Handle list response - EXACT same logic as otp_tool.py (lines 481-508)
        if isinstance(otp_data, list):
            # Find the specific number in the list - EXACT same matching logic
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
                # Number not found in list yet, continue waiting
                return
        
        if otp_data and isinstance(otp_data, dict):
            # Get OTP - EXACT SAME LOGIC AS otp_tool.py (lines 510-527)
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
                # Stop monitoring
                job.schedule_removal()
                if user_id in user_jobs:
                    del user_jobs[user_id]
                update_user_session(user_id, monitoring=0)
                
                # Get country and service info from job data (most reliable) or session
                job_data = job.data if hasattr(job, 'data') else {}
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
                
                # Make number clickable - ensure it has + prefix for Telegram auto-detection
                display_number = number
                if not display_number.startswith('+'):
                    digits_only = ''.join(filter(str.isdigit, display_number))
                    if len(digits_only) >= 10:
                        display_number = '+' + digits_only
                
                # Format OTP message in new format
                otp_msg = f"🔔 OTP Received\n\n"
                otp_msg += f"📞 Number: {display_number}\n"
                otp_msg += f"🔐 OTP: <code>{otp}</code>\n"
                otp_msg += f"💬 Service: {service.upper()}"
                
                # Send OTP message
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=otp_msg,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Error sending OTP message: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
    except Exception as e:
        logger.error(f"Error monitoring OTP for user {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

<<<<<<< HEAD
def main():
    """Start the bot"""
    # Initialize global API client (login will retry on first API call if needed)
    logger.info("Initializing global API client...")
    api_client = get_global_api_client()
    if api_client:
        logger.info("✅ API client initialized (login will retry on first API call if needed)")
=======
# Global application instance
application = None

# Global event loop for webhook mode - used by background thread for JobQueue
bot_event_loop = None
bot_thread = None

def get_bot_event_loop():
    """Get the bot's event loop (running in background thread for JobQueue)"""
    global bot_event_loop
    return bot_event_loop

def setup_webhook(render_url):
    """Setup webhook for Telegram bot"""
    webhook_url = f"{render_url}/webhook" if not render_url.endswith('/webhook') else render_url
    
    # Delete any existing webhook first
    delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    try:
        requests.get(delete_url, timeout=5)
        time.sleep(1)
    except:
        pass
    
    # Set new webhook
    set_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(set_url, json={
        'url': webhook_url,
        'drop_pending_updates': True,
        'allowed_updates': ['message', 'callback_query']
    }, timeout=10)
    
    if response.status_code == 200:
        logger.info(f"✅ Webhook set successfully: {webhook_url}")
        return True
    else:
        logger.error(f"❌ Failed to set webhook: {response.text}")
        return False

def init_application_for_webhook():
    """Initialize application for webhook mode (called when module is imported by Gunicorn)"""
    global application, bot_event_loop, bot_thread
    
    # Only initialize if not already initialized
    if application is not None:
        return
    
    logger.info("🔄 Initializing application for webhook mode...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", admin_commands))
    application.add_handler(CommandHandler("remove", admin_commands))
    application.add_handler(CommandHandler("pending", admin_commands))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("✅ Application created with handlers")
    
    # Initialize database
    try:
        init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        logger.warning("Bot will continue but database operations may fail")
    
    # Initialize global API client
    logger.info("Initializing global API client...")
    api_client = get_global_api_client()
    if api_client:
        logger.info("✅ API client initialized")
    
    # Get Render URL
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not render_url:
        render_url = os.environ.get('WEBHOOK_URL', '')
    
    if render_url:
        # Setup webhook
        if setup_webhook(render_url):
            # Create event loop for background thread (JobQueue needs continuous loop)
            bot_event_loop = asyncio.new_event_loop()
            
            # Initialize and start application in background thread - JobQueue needs continuous loop
            def run_bot():
                global bot_event_loop
                try:
                    logger.info("🔄 Starting bot background thread...")
                    # Set this loop as the thread's event loop
                    asyncio.set_event_loop(bot_event_loop)
                    logger.info("✅ Event loop set for background thread")
                    
                    # Initialize and start application
                    logger.info("🔄 Initializing application...")
                    bot_event_loop.run_until_complete(application.initialize())
                    logger.info("✅ Application initialized")
                    
                    logger.info("🔄 Starting application...")
                    bot_event_loop.run_until_complete(application.start())
                    logger.info("✅ Application started for webhook mode")
                    
                    # Verify JobQueue is available
                    if application.job_queue:
                        logger.info("✅ JobQueue is available and running")
                        logger.info(f"✅ JobQueue scheduler: {application.job_queue.scheduler}")
                    else:
                        logger.error("❌ JobQueue is NOT available - OTP monitoring will NOT work")
                    
                    # Keep event loop running for JobQueue
                    logger.info("🔄 Event loop running forever for JobQueue...")
                    bot_event_loop.run_forever()
                except Exception as e:
                    logger.error(f"❌ Error in bot thread: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Start bot in background thread so event loop keeps running for JobQueue
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            
            # Give bot time to initialize
            time.sleep(3)
            logger.info("✅ Bot initialization complete for webhook mode")
        else:
            logger.error("❌ Failed to setup webhook")

# ==================== FLASK APP (for Webhook) ====================
flask_app = Flask(__name__)

# Initialize application when module is imported (for Gunicorn)
# Check if running on Render (has RENDER_EXTERNAL_URL)
if os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('WEBHOOK_URL'):
    init_application_for_webhook()

@flask_app.route('/')
def health_check():
    """Health check endpoint for Render"""
    return Response('OK - Bot is running', status=200)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates via webhook"""
    global application
    
    if application is None:
        logger.error("Application not initialized")
        return Response('Internal Server Error', status=500)
    
    if request.method == 'POST':
        try:
            json_data = request.get_json(force=True)
            update = Update.de_json(json_data, application.bot)
            
            if not update:
                return Response('Invalid Update', status=400)
            
            # Log update details for debugging
            update_type = "unknown"
            if update.message:
                update_type = f"message: {update.message.text[:50] if update.message.text else 'no text'}"
            elif update.callback_query:
                update_type = f"callback_query: {update.callback_query.data}"
            logger.info(f"📨 Received update: {update_type}, update_id: {update.update_id}")
            
            # Process update directly in a new event loop (simpler and more reliable for webhook mode)
            # This ensures the update is processed immediately without waiting for background loop
            logger.info(f"🔄 Processing update {update.update_id} directly")
            try:
                # Create a new event loop for this update
                temp_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(temp_loop)
                
                # Process the update
                temp_loop.run_until_complete(application.process_update(update))
                logger.info(f"✅ Update {update.update_id} processed successfully")
                
                temp_loop.close()
            except Exception as e:
                logger.error(f"❌ Error processing update {update.update_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                try:
                    temp_loop.close()
                except:
                    pass
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            import traceback
            traceback.print_exc()
        
        return Response('OK', status=200)
    return Response('Method not allowed', status=405)

def main():
    """Start the bot - for local development (polling mode)"""
    global application
    
    # Only run main() for local development (when no Render URL)
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not render_url:
        render_url = os.environ.get('WEBHOOK_URL', '')
    
    if render_url:
        # Webhook mode - already initialized by init_application_for_webhook()
        logger.info("🌐 Running in WEBHOOK mode (Render) - already initialized")
        logger.info("🚀 Flask app is ready for Gunicorn")
        return
    
    # Local development - use polling (like backup bot)
    logger.info("🔄 Running in POLLING mode (Local)")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
<<<<<<< HEAD
    application.add_handler(CommandHandler("rangechkr", rangechkr))
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
    application.add_handler(CommandHandler("users", admin_commands))
    application.add_handler(CommandHandler("remove", admin_commands))
    application.add_handler(CommandHandler("pending", admin_commands))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
<<<<<<< HEAD
    # Start bot
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
=======
    logger.info("Bot starting...")
    logger.info(f"Admin User ID: {ADMIN_USER_ID}")
    
    # Initialize database
    try:
        init_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        logger.warning("Bot will continue but database operations may fail")
    
    # Initialize global API client
    logger.info("Initializing global API client...")
    api_client = get_global_api_client()
    if api_client:
        logger.info("✅ API client initialized")
    
    # Run in polling mode (EXACTLY like backup bot)
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3

if __name__ == "__main__":
    main()

