import os
import sys
import threading
import time
import signal
from datetime import datetime
import requests
import json
import re
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import logging
from supabase import create_client, Client
from flask import Flask, request, Response

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

# Bot Configuration
BOT_TOKEN = "8354306480:AAEwHbjWU1Hyz_W6wTExyMZ_bVhSr-YwMfs"
ADMIN_USER_ID = 7325836764

# API Configuration (from otp_tool.py)
BASE_URL = "https://v2.mnitnetwork.com"
API_EMAIL = "roni791158@gmail.com"
API_PASSWORD = "47611858@Dove"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sgnnqvfoajqsfdyulolm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNnbm5xdmZvYWpxc2ZkeXVsb2xtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNzE1MjcsImV4cCI6MjA3OTc0NzUyN30.dFniV0odaT-7bjs5iQVFQ-N23oqTGMAgQKjswhaHSP4")

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

def add_user(user_id, username):
    """Add new user to database"""
    try:
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

def approve_user(user_id):
    """Approve user in database"""
    try:
        update_data = {
            'status': 'approved',
            'approved_at': datetime.now().isoformat()
        }
        supabase.table('users').update(update_data).eq('telegram_user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error in approve_user: {e}")

def reject_user(user_id):
    """Reject user in database"""
    try:
        supabase.table('users').update({'status': 'rejected'}).eq('telegram_user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error in reject_user: {e}")

def remove_user(user_id):
    """Remove user from database"""
    try:
        # Delete from user_sessions first (due to foreign key) - but check if table exists
        try:
            supabase.table('user_sessions').delete().eq('user_id', user_id).execute()
        except:
            pass  # Table might not exist, skip
        # Then delete from users
        supabase.table('users').delete().eq('telegram_user_id', user_id).execute()
    except Exception as e:
        logger.error(f"Error in remove_user: {e}")

def get_pending_users():
    """Get list of pending users"""
    try:
        result = supabase.table('users').select('telegram_user_id, username').eq('status', 'pending').execute()
        return [(user['telegram_user_id'], user['username']) for user in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error in get_pending_users: {e}")
        return []

def get_all_users():
    """Get all users"""
    try:
        result = supabase.table('users').select('telegram_user_id, username, status').execute()
        return [(user['telegram_user_id'], user['username'], user['status']) for user in result.data] if result.data else []
    except Exception as e:
        logger.error(f"Error in get_all_users: {e}")
        return []

def update_user_session(user_id, service=None, country=None, range_id=None, number=None, monitoring=0):
    """Update user session in database"""
    try:
        # For now, user_sessions table might not exist in Supabase
        # We can skip this or use bot_sessions like working bot
        # For simplicity, we'll skip session storage for now since it's optional
        pass
    except Exception as e:
        logger.error(f"Error in update_user_session: {e}")

def get_user_session(user_id):
    """Get user session from database"""
    try:
        # For now, user_sessions table might not exist in Supabase
        # Return None - session info will be stored in memory instead
        return None
    except Exception as e:
        logger.error(f"Error in get_user_session: {e}")
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
                    self.auth_token = hitauth_data['data']['token']
                    
                    # Set account type cookie
                    self.session.cookies.set('mnitnetworkcom_accountType', 'user', domain='v2.mnitnetwork.com')
                    
                    # Store mhitauth token in cookie (browser does this)
                    self.session.cookies.set('mnitnetworkcom_mhitauth', self.auth_token, domain='v2.mnitnetwork.com')
                    
                    logger.info("Login successful")
                    return True
            logger.error(f"Login failed with status {login_resp.status_code}")
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
    
    def check_otp(self, number):
        """Check for OTP on a number"""
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
            
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'] is not None:
                    data_obj = data['data']
                    if isinstance(data_obj, dict) and 'num' in data_obj and data_obj['num'] is not None:
                        numbers = data_obj['num']
                        if isinstance(numbers, list):
                            target_normalized = number.replace('+', '').replace(' ', '').replace('-', '').strip()
                            for num_data in numbers:
                                if isinstance(num_data, dict):
                                    num_value = num_data.get('number', '')
                                    num_normalized = num_value.replace('+', '').replace(' ', '').replace('-', '').strip()
                                    if num_normalized == target_normalized:
                                        return num_data
                            
                            target_digits = ''.join(filter(str.isdigit, target_normalized))
                            if len(target_digits) >= 9:
                                for num_data in numbers:
                                    if isinstance(num_data, dict):
                                        num_value = num_data.get('number', '')
                                        num_digits = ''.join(filter(str.isdigit, num_value))
                                        if len(num_digits) >= 9 and num_digits[-9:] == target_digits[-9:]:
                                            return num_data
            return None
        except Exception as e:
            logger.error(f"Error checking OTP: {e}")
            return None

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

# Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or "Unknown"
    
    # Add user to database
    add_user(user_id, username)
    
    status = get_user_status(user_id)
    
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
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
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
    await query.answer()
    
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
    
    # Country selection
    elif data.startswith("country_"):
        # Re-check approval status for security
        status = get_user_status(user_id)
        if status != 'approved':
            await query.edit_message_text("❌ Your access is pending approval.")
            return
        
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
        
        if not selected_range:
            await query.edit_message_text(f"❌ No ranges found for {country}.")
            return
        
        range_id = selected_range.get('name', selected_range.get('id', ''))
        
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
        # Check if job_queue is available
        if context.job_queue is None:
            logger.warning("JobQueue not available. Cannot start OTP monitoring.")
            await query.edit_message_text("❌ Error: JobQueue not initialized. Please contact admin.")
            return
        
        job = context.job_queue.run_repeating(
            monitor_otp,
            interval=2,
            first=2,
            chat_id=user_id,
            data={'number': number, 'user_id': user_id, 'country': country, 'service': service_name, 'start_time': time.time()}
        )
        user_jobs[user_id] = job  # Store job reference
        
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
        )
    
    # Back to services
    elif data == "back_services":
        # Re-check approval status for security
        status = get_user_status(user_id)
        if status != 'approved':
            await query.edit_message_text("❌ Your access is pending approval.")
            return
        
        keyboard = [
            [InlineKeyboardButton("💬 WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("👥 Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("✈️ Telegram", callback_data="service_telegram")]
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
    
    # Handle service selection
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
            
            if not selected_range:
                await update.message.reply_text(f"❌ No ranges found for {country}.")
                return
            
            range_id = selected_range.get('name', selected_range.get('id', ''))
            
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
                monitor_otp,
                interval=2,
                first=2,
                chat_id=user_id,
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
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in handle_message country selection: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")

async def monitor_otp(context: ContextTypes.DEFAULT_TYPE):
    """Monitor OTP in background"""
    job = context.job
    user_id = job.chat_id
    number = job.data['number']
    start_time = job.data.get('start_time', time.time())
    
    # Timeout after 5 minutes
    if time.time() - start_time > 300:
        job.schedule_removal()
        if user_id in user_jobs:
            del user_jobs[user_id]
        update_user_session(user_id, monitoring=0)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏱️ Timeout! No OTP received for number {number} within 5 minutes."
            )
        except:
            pass
        return
    
    # Get global API client
    api_client = get_global_api_client()
    if not api_client:
        return
    
    try:
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
    except Exception as e:
        logger.error(f"Error monitoring OTP for user {user_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Global application instance
application = None

# ==================== FLASK APP (for Webhook) ====================
flask_app = Flask(__name__)

# Global event loop for webhook mode
webhook_loop = None

def get_or_create_event_loop():
    """Get existing event loop or create new one"""
    global webhook_loop
    try:
        if webhook_loop is None or webhook_loop.is_closed():
            webhook_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(webhook_loop)
        return webhook_loop
    except RuntimeError:
        webhook_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(webhook_loop)
        return webhook_loop

def get_background_loop():
    """Get the background event loop that's running JobQueue"""
    global webhook_loop
    return webhook_loop

@flask_app.route('/')
def health_check():
    """Health check endpoint for Render"""
    return Response('OK - Bot is running', status=200)

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram updates via webhook"""
    global application
    
    # Ensure application is initialized
    if application is None:
        logger.warning("Application not initialized, initializing now...")
        try:
            init_application_if_needed()
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            return Response('Internal Server Error', status=500)
    
    if request.method == 'POST':
        try:
            json_data = request.get_json(force=True)
            update = Update.de_json(json_data, application.bot)
            
            # Get the background event loop (running in background thread for JobQueue)
            loop = get_background_loop()
            
            if loop and loop.is_running():
                # Loop is running in background thread, schedule coroutine safely
                # Don't wait for result - Telegram expects quick response
                asyncio.run_coroutine_threadsafe(
                    application.process_update(update),
                    loop
                )
            else:
                # Loop not running yet, use temporary event loop
                temp_loop = get_or_create_event_loop()
                temp_loop.run_until_complete(application.process_update(update))
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            import traceback
            traceback.print_exc()
        return Response('OK', status=200)
    return Response('Method not allowed', status=405)

def init_application_if_needed():
    """Initialize application if not already initialized (for gunicorn)"""
    global application
    
    if application is not None:
        return
    
    logger.info("Initializing application...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", admin_commands))
    application.add_handler(CommandHandler("remove", admin_commands))
    application.add_handler(CommandHandler("pending", admin_commands))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
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
    
    # Initialize application for webhook mode
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not render_url:
        render_url = os.environ.get('WEBHOOK_URL', '')
    
    if render_url:
        # Setup webhook
        if setup_webhook():
            # Initialize the application
            loop = get_or_create_event_loop()
            
            # Start application in background to keep JobQueue running
            async def start_application():
                await application.initialize()
                await application.start()
                logger.info("✅ Application initialized and started for webhook mode")
                
                # Verify JobQueue is available
                if application.job_queue:
                    logger.info("✅ JobQueue is available and running")
                else:
                    logger.warning("⚠️ JobQueue is not available - OTP monitoring may not work")
                
                # Keep event loop running to process JobQueue tasks
                while True:
                    await asyncio.sleep(1)
            
            # Run application.start() in background thread to keep JobQueue active
            def run_event_loop():
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_application())
            
            import threading
            event_loop_thread = threading.Thread(target=run_event_loop, daemon=True)
            event_loop_thread.start()
            logger.info("✅ Started background event loop thread for JobQueue")
        else:
            logger.warning("Failed to setup webhook, application may not work correctly")

def setup_webhook():
    """Setup webhook for Telegram bot"""
    # Get Render URL from environment or use WEBHOOK_URL
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not render_url:
        render_url = os.environ.get('WEBHOOK_URL', '')
    
    if render_url:
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
    else:
        logger.warning("⚠️ RENDER_EXTERNAL_URL or WEBHOOK_URL not set, running in polling mode")
        return False

def main():
    """Start the bot"""
    global application
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", admin_commands))
    application.add_handler(CommandHandler("remove", admin_commands))
    application.add_handler(CommandHandler("pending", admin_commands))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot started!")
    logger.info(f"Admin User ID: {ADMIN_USER_ID}")
    
    # Check if running on Render (webhook mode) or locally (polling mode)
    render_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if not render_url:
        render_url = os.environ.get('WEBHOOK_URL', '')
    
    if render_url:
        # Webhook mode for Render
        logger.info("🌐 Running in WEBHOOK mode (Render)")
        
        # Setup webhook
        if setup_webhook():
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
            
            # Initialize the application
            loop = get_or_create_event_loop()
            
            # Start application in background to keep JobQueue running
            async def start_application():
                await application.initialize()
                await application.start()
                logger.info("✅ Application initialized and started for webhook mode")
                
                # Verify JobQueue is available
                if application.job_queue:
                    logger.info("✅ JobQueue is available and running")
                else:
                    logger.warning("⚠️ JobQueue is not available - OTP monitoring may not work")
                
                # Keep event loop running to process JobQueue tasks
                while True:
                    await asyncio.sleep(1)
            
            # Run application.start() in background thread to keep JobQueue active
            def run_event_loop():
                asyncio.set_event_loop(loop)
                loop.run_until_complete(start_application())
            
            event_loop_thread = threading.Thread(target=run_event_loop, daemon=True)
            event_loop_thread.start()
            logger.info("✅ Started background event loop thread for JobQueue")
            
            # Start Flask server
            port = int(os.environ.get('PORT', 10000))
            logger.info(f"🚀 Starting Flask server on port {port}")
            flask_app.run(host='0.0.0.0', port=port, threaded=True)
        else:
            logger.error("Failed to setup webhook, falling back to polling")
            run_polling_mode()
    else:
        # Polling mode for local development
        logger.info("🔄 Running in POLLING mode (Local)")
        
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
        
        run_polling_mode()

def run_polling_mode():
    """Run bot in polling mode (for local development)"""
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            stop_signals=None
        )
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Bot shutdown complete")
        if application:
            try:
                application.stop()
            except:
                pass

# Initialize application when module is imported (for gunicorn)
if os.environ.get('RENDER_EXTERNAL_URL') or os.environ.get('WEBHOOK_URL'):
    # Running in webhook mode - initialize when module loads
    try:
        init_application_if_needed()
    except Exception as e:
        logger.error(f"Failed to initialize application on import: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

