import os
import threading
import time
import asyncio
import concurrent.futures
from datetime import datetime, timedelta, timezone
import requests
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
import base64

try:
    from Cryptodome.Cipher import AES
except ImportError:
    try:
        from Crypto.Cipher import AES
    except ImportError:
        AES = None

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = "https://api.2oo9.cloud/MXS47FLFX0U/tness"
WIRE_ALPHABET = "8sNpKxR7vQzJgYhCdW3FmTaB5ueIoP9rfk2L0wXyZitc4nAVMSjEUDqGl1H6bO"

API_EMAIL = os.getenv("API_EMAIL", "roni791158@gmail.com")
API_PASSWORD = os.getenv("API_PASSWORD", "53561106@Roni")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://sgnnqvfoajqsfdyulolm.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNnbm5xdmZvYWpxc2ZkeXVsb2xtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQxNzE1MjcsImV4cCI6MjA3OTc0NzUyN30.dFniV0odaT-7bjs5iQVFQ-N23oqTGMAgQKjswhaHSP4")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "5742928021"))
OTP_CHANNEL_ID = int(os.getenv("OTP_CHANNEL_ID", "-1003403204287"))

UPDATE_CONCURRENCY = int(os.getenv("UPDATE_CONCURRENCY", "128"))
CONSOLE_MONITOR_INTERVAL = int(os.getenv("CONSOLE_MONITOR_INTERVAL", "3"))
CONSOLE_MAX_FORWARDS_PER_CYCLE = int(os.getenv("CONSOLE_MAX_FORWARDS_PER_CYCLE", "6"))
CONSOLE_CYCLE_BUDGET_SECONDS = float(os.getenv("CONSOLE_CYCLE_BUDGET_SECONDS", "2.2"))

SERVICE_APP_IDS = {
    "whatsapp": "WhatsApp",
    "facebook": "Facebook",
    "telegram": "Telegram",
}

HAS_CURL_CFFI = False
try:
    from curl_cffi import requests as curl_requests
    HAS_CURL_CFFI = True
except ImportError:
    pass

HAS_CLOUDSCRAPER = False
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    pass

# Supabase Database setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def _build_bengali_proverb_pool(target_size=1000):
    starters = ["à¦§à§ˆà¦°à§à¦¯ à¦§à¦°à¦²à§‡", "à¦¸à¦¤à¦¤à¦¾ à¦°à¦¾à¦–à¦²à§‡", "à¦ªà¦°à¦¿à¦¶à§à¦°à¦® à¦•à¦°à¦²à§‡", "à¦¸à¦®à§Ÿà¦•à§‡ à¦¸à¦®à§à¦®à¦¾à¦¨ à¦•à¦°à¦²à§‡"]
    middles = ["à¦¸à¦¾à¦«à¦²à§à¦¯ à¦à¦•à¦¦à¦¿à¦¨ à¦¦à¦°à¦œà¦¾à§Ÿ à¦•à§œà¦¾ à¦¨à¦¾à§œà¦¬à§‡à¦‡", "à¦­à¦¾à¦—à§à¦¯à¦“ à¦ªà¦°à¦¿à¦¶à§à¦°à¦®à§€à¦° à¦ªà¦¾à¦¶à§‡ à¦¦à¦¾à¦à§œà¦¾à§Ÿ"]
    endings = ["à¦¤à¦¾à¦‡ à¦†à¦œà¦“ à¦à¦—à¦¿à§Ÿà§‡ à¦¯à¦¾à¦“", "à¦¤à¦¾à¦‡ à¦¨à¦¿à¦œà§‡à¦° à¦—à¦¤à¦¿à¦¤à§‡ à¦šà¦²à¦¤à§‡ à¦¥à¦¾à¦•à§‹"]
    lines = [f"{a}, {b} - {c}à¥¤" for a in starters for b in middles for c in endings]
    return lines[:target_size]

BN_OTP_MOTIVATION_LINES = _build_bengali_proverb_pool(1000)

def get_random_bn_otp_motivation():
    return random.choice(BN_OTP_MOTIVATION_LINES) if BN_OTP_MOTIVATION_LINES else "à¦ªà¦°à¦¿à¦¶à§à¦°à¦® à¦•à¦°à§à¦¨à¥¤"

# --- API Helpers & Client ---

def b62_encode(data):
    base = len(WIRE_ALPHABET)
    res = int.from_bytes(data, 'big')
    if res == 0: return WIRE_ALPHABET[0]
    out = ""
    while res > 0:
        res, rem = divmod(res, base)
        out = WIRE_ALPHABET[rem] + out
    return out

def b62_decode(data):
    base = len(WIRE_ALPHABET)
    res = 0
    for char in data:
        res = res * base + WIRE_ALPHABET.index(char)
    byte_len = (res.bit_length() + 7) // 8
    return res.to_bytes(byte_len, 'big')

class WireCodec:
    def __init__(self, sid="M0000000001"):
        self.sid = sid
        prefix = "AES-GCM_KEY_"
        self.key = hashlib.sha256((prefix + self.sid).encode()).digest()

    def encrypt(self, payload_dict):
        if AES is None:
            raise ImportError("Crypto library not found.")
        plaintext = json.dumps(payload_dict, separators=(',', ':')).encode()
        nonce = hashlib.sha256(str(time.time()).encode()).digest()[:12]
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)
        return b62_encode(nonce + ciphertext + tag)

    def decrypt(self, enc_data):
        if not enc_data: return None
        try:
            decoded = b62_decode(enc_data)
            if len(decoded) < 28: return None
            nonce = decoded[:12]
            ciphertext = decoded[12:-16]
            tag = decoded[-16:]
            cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return json.loads(plaintext)
        except Exception:
            return None

class APIClient:
    def __init__(self):
        self.base_url = BASE_URL
        if HAS_CURL_CFFI:
            self.session = curl_requests.Session(impersonate="chrome110")
            self.use_curl = True
        elif HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper()
            self.use_curl = False
        else:
            self.session = requests.Session()
            self.use_curl = False
        
        self.auth_token = None
        self.email = API_EMAIL
        self.password = API_PASSWORD
        self.codec = WireCodec("M0000000001") 
        
        self.browser_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9",
            "Content-Type": "text/plain; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest"
        }
        self._ranges_cache = {}
        self._lock = threading.Lock()

    def _get_sid_from_jwt(self, token):
        try:
            parts = token.split('.')
            if len(parts) < 2: return None
            payload_b64 = parts[1]
            payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
            import base64
            data = json.loads(base64.b64decode(payload_b64).decode())
            return data.get('sid')
        except Exception:
            return None

    def _api_call(self, method, endpoint, payload=None, retry_login=True):
        if not self.auth_token and endpoint != "/@auth/login":
            if not self.login(): return None
        headers = self.browser_headers.copy()
        if self.auth_token: headers["mauth"] = self.auth_token
        data = self.codec.encrypt(payload) if payload is not None else None
        try:
            url = f"{self.base_url}{endpoint}"
            if method.upper() == "POST":
                resp = self.session.post(url, data=data, headers=headers, timeout=15)
            else:
                resp = self.session.get(url, headers=headers, timeout=15)
            if resp.status_code in [401, 403]:
                if retry_login:
                    self.auth_token = None
                    if self.login(): return self._api_call(method, endpoint, payload, False)
                return None
            if resp.status_code == 200:
                dec = self.codec.decrypt(resp.text)
                if dec: return dec
                try: return resp.json()
                except: return None
            return None
        except Exception as e:
            logger.error(f"API Error {endpoint}: {e}")
            return None

    def login(self):
        with self._lock:
            try:
                self.codec = WireCodec("M0000000001")
                payload = {"email": self.email, "password": self.password, "remember": True}
                data = self._api_call("POST", "/@auth/login", payload, False)
                if data and data.get('meta', {}).get('code') == 200:
                    token = data['data'].get('session_token')
                    if token:
                        self.auth_token = token
                        sid = self._get_sid_from_jwt(token)
                        if sid: self.codec = WireCodec(sid)
                        logger.info(f"Login successful. SID: {sid}")
                        return True
                return False
            except Exception as e:
                logger.error(f"Login exception: {e}")
                return False

    def get_console_logs(self):
        try:
            data = self._api_call("GET", "/@dashboard/dialer/console/info")
            if data and 'data' in data: return data['data'].get('logs', [])
            return []
        except Exception: return []

    def _normalize_range_token(self, value):
        if value is None: return ""
        return re.sub(r'[^0-9Xx]', '', str(value)).upper()

    def get_number(self, range_id):
        try:
            normalized = self._normalize_range_token(range_id)
            if not normalized: return None
            range_for_api = normalized if 'X' in normalized else f"{normalized}XXX"
            data = self._api_call("POST", "/@dashboard/dialer/getnum/request", {"range": range_for_api})
            if (not data or data.get('meta', {}).get('code') != 200) and normalized.isdigit():
                data = self._api_call("POST", "/@dashboard/dialer/getnum/request", {"range_id": normalized})
            if data and data.get('meta', {}).get('code') == 200:
                number = data['data'].get('number') or data['data'].get('copy')
                if number:
                    return {'number': number, 'range': range_for_api, 'country_code': data['data'].get('country_code', ''), 'status': 'pending'}
            return None
        except Exception: return None

    def check_otp_batch(self, numbers):
        try:
            data = self._api_call("GET", "/@dashboard/dialer/getnum/list?page=1")
            result = {}
            if data and 'data' in data and data['data']:
                numbers_list = data['data'].get('numbers', [])
                if numbers_list:
                    target_map_exact = {n.replace('+', '').replace(' ', '').strip(): n for n in numbers}
                    target_map_last9 = {n.replace('+', '').replace(' ', '').strip()[-9:]: n for n in numbers if len(n.replace('+', '').replace(' ', '').strip()) >= 9}
                    for num_obj in numbers_list:
                        api_num = num_obj.get('number', '').replace('+', '').strip()
                        msg = num_obj.get('message') or num_obj.get('otp', '')
                        if msg: num_obj['sms_content'] = msg
                        target_num = target_map_exact.get(api_num) or target_map_last9.get(api_num[-9:])
                        if target_num: result[target_num] = num_obj
            return result
        except Exception: return {}

    def get_ranges(self, app_id, max_retries=3, keyword=""):
        try:
            app_id_norm = str(app_id or "").strip().lower()
            logs = self.get_console_logs()
            all_ranges = self._build_ranges_from_console_logs(logs)
            primary_services = {"whatsapp", "facebook", "telegram"}
            filtered = []
            for r in all_ranges:
                service_norm = normalize_service_name(r.get('service'))
                if app_id_norm in primary_services:
                    if service_norm == app_id_norm: filtered.append(r)
                elif app_id_norm == "others":
                    if service_norm not in primary_services: filtered.append(r)
                else:
                    if app_id_norm in str(r.get('service')).lower(): filtered.append(r)
            return filtered
        except Exception: return []

    def _build_ranges_from_console_logs(self, logs):
        if not isinstance(logs, list) or not logs: return []
        range_map = {}
        for idx, item in enumerate(logs):
            app_name_raw = str(item.get('app_name') or "").strip()
            if not app_name_raw: continue
            if app_name_raw in ["******", "alymscintl"]: app_name_raw = "WhatsApp"
            service_key = normalize_service_name(app_name_raw)
            range_token = self._normalize_range_token(item.get('range') or item.get('number'))
            if not range_token or len(re.sub(r'[^0-9]', '', range_token)) < 4: continue
            range_for_api = range_token if 'X' in range_token else f"{range_token}XXX"
            country = str(item.get('country') or "Unknown")
            obj = {
                'id': range_for_api, 'range_id': range_for_api, 'name': range_for_api,
                'pattern': range_for_api, 'country': country, 'service': app_name_raw, 
                'operator': str(item.get('carrier') or "Unknown").strip(),
                'datetime': f"{idx} mins ago"
            }
            map_key = (service_key, range_for_api)
            if map_key not in range_map: range_map[map_key] = obj
        return list(range_map.values())

    def get_applications(self, max_retries=3):
        return [{'id': 'whatsapp', 'name': 'WhatsApp'}, {'id': 'facebook', 'name': 'Facebook'}, {'id': 'telegram', 'name': 'Telegram'}, {'id': 'others', 'name': 'Others'}]

    def get_multiple_numbers(self, range_id, range_name=None, count=2, max_retries=10):
        numbers = []
        total_attempts = 0
        max_total_attempts = count * 10
        logger.info(f"Requesting {count} numbers from range {range_id}")
        while len(numbers) < count and total_attempts < max_total_attempts:
            total_attempts += 1
            number_data = self.get_number(range_name or range_id)
            if number_data:
                num_val = number_data.get('number')
                if num_val and not is_number_used(num_val):
                    numbers.append(number_data)
                    logger.info(f"Added fresh number: {num_val}")
                else:
                    logger.info(f"Skipping recently used number: {num_val}")
            else:
                logger.warning(f"get_number returned None (attempt {total_attempts})")
            time.sleep(1)
        return numbers

global_api_client = None
api_lock = threading.Lock()

def get_global_api_client():
    global global_api_client
    if global_api_client is None:
        global_api_client = APIClient()
        global_api_client.login()
    return global_api_client

def refresh_global_token():
    global global_api_client
    with api_lock:
        if global_api_client:
            if not global_api_client.login():
                global_api_client = APIClient()
                global_api_client.login()
        else:
            get_global_api_client()

class BestEffortLock:
    def __init__(self, timeout=0.05):
        self._lock = threading.Lock()
        self._timeout = timeout
        self._acquired = False
    def __enter__(self):
        try: self._acquired = self._lock.acquire(timeout=self._timeout)
        except Exception: self._acquired = False
        return self
    def __exit__(self, exc_type, exc, tb):
        if self._acquired:
            try: self._lock.release()
            except Exception: pass
        self._acquired = False
        return False

db_lock = BestEffortLock(timeout=0.05)
user_jobs = {}
console_lock = threading.Lock()
console_bootstrapped = False
forwarded_console_ids = set()
forwarded_console_order = []
MAX_FORWARDED_CONSOLE_IDS = 5000
bot_username_cache = None
CONSOLE_FORWARD_SERVICE_KEYS = {"whatsapp", "telegram"}

def parse_time_ago(time_str):
    try:
        if not time_str or 'just now' in time_str.lower(): return 0
        parts = str(time_str).lower().split()
        if len(parts) >= 2:
            val = float(parts[0])
            unit = parts[1]
            if 'sec' in unit: return val / 60
            if 'min' in unit: return val
            if 'hour' in unit: return val * 60
            if 'day' in unit: return val * 1440
        return 999999
    except: return 999999

def get_user_status(user_id):
    if int(user_id) == ADMIN_USER_ID: return 'approved'
    try:
        with db_lock:
            result = supabase.table('users').select('status').eq('user_id', int(user_id)).execute()
            return result.data[0].get('status', 'pending') if result.data else 'pending'
    except: return 'pending'

def add_user(user_id, username):
    try:
        with db_lock:
            supabase.table('users').upsert({'user_id': int(user_id), 'username': username, 'status': 'pending'}).execute()
    except: pass

def get_user_session(user_id):
    try:
        with db_lock:
            result = supabase.table('user_sessions').select('*').eq('user_id', int(user_id)).execute()
            if result.data:
                row = result.data[0]
                return {'user_id': row['user_id'], 'service': row.get('selected_service'), 'number_count': row.get('number_count', 2)}
    except: pass
    return {'number_count': 2}

def update_user_session(user_id, service=None, number_count=None):
    try:
        with db_lock:
            data = {'user_id': int(user_id), 'last_check': datetime.now().isoformat()}
            if service: data['selected_service'] = service
            if number_count: data['number_count'] = number_count
            supabase.table('user_sessions').upsert(data).execute()
    except: pass

def is_number_used(number):
    try:
        norm = ''.join(filter(str.isdigit, str(number)))
        res = supabase.table('used_numbers').select('*').eq('number', norm).execute()
        if res.data:
            used_at = datetime.fromisoformat(res.data[0]['used_at'].replace('Z', '+00:00'))
            if datetime.now(timezone.utc) - used_at < timedelta(hours=24): return True
    except: pass
    return False

def add_used_number(number):
    try:
        norm = ''.join(filter(str.isdigit, str(number)))
        supabase.table('used_numbers').upsert({'number': norm, 'used_at': datetime.now(timezone.utc).isoformat()}).execute()
    except: pass

def get_bd_today_str(): return datetime.now(timezone(timedelta(hours=6))).strftime("%Y-%m-%d")
def get_bd_now(): return datetime.now(timezone(timedelta(hours=6)))

def increment_otp_count(user_id):
    try:
        today = get_bd_today_str()
        with db_lock:
            res = supabase.table('users').select('otp_count, otp_date').eq('user_id', int(user_id)).execute()
            count = 1
            if res.data and res.data[0].get('otp_date') == today:
                count = (res.data[0].get('otp_count') or 0) + 1
            supabase.table('users').update({'otp_count': count, 'otp_date': today}).eq('user_id', int(user_id)).execute()
    except: pass

def get_today_otp_count(user_id):
    try:
        today = get_bd_today_str()
        with db_lock:
            res = supabase.table('users').select('otp_count, otp_date').eq('user_id', int(user_id)).execute()
            if res.data and res.data[0].get('otp_date') == today:
                return res.data[0].get('otp_count') or 0
    except: pass
    return 0

def normalize_service_name(service_name):
    if not service_name: return None
    norm = re.sub(r'[^a-z0-9]+', '', str(service_name).lower())
    if "whatsapp" in norm or "alymscintl" in norm or service_name == "******": return "whatsapp"
    if "facebook" in norm: return "facebook"
    if "telegram" in norm: return "telegram"
    return "others"

def resolve_app_id(service_name, context):
    if service_name in SERVICE_APP_IDS: return SERVICE_APP_IDS[service_name]
    return service_name or "Others"

def get_country_flag(country): return "ðŸŒ"
def get_country_code(country): return "XX"
def detect_language_from_sms(text): return "English"
def detect_country_from_range(r): return None
def detect_country_from_number(n): return None

def build_console_channel_message(log_item):
    country = str(log_item.get('country') or 'Unknown')
    service_raw = str(log_item.get('app_name') or 'Unknown')
    number_masked = str(log_item.get('number') or 'Unknown')
    sms_content = str(log_item.get('sms') or '')
    service_key = normalize_service_name(service_raw)
    service_display = {"whatsapp":"WhatsApp","facebook":"Facebook","telegram":"Telegram"}.get(service_key, service_raw)
    if service_raw in ["******", "alymscintl"]: service_display = "WhatsApp"
    return f"ðŸŒ {service_display} {number_masked} {sms_content}"

def is_console_otp_sms(sms, app): return True
def remember_console_log(key): 
    forwarded_console_ids.add(key)
    forwarded_console_order.append(key)
    if len(forwarded_console_order) > MAX_FORWARDED_CONSOLE_IDS:
        old = forwarded_console_order.pop(0)
        forwarded_console_ids.discard(old)

def extract_masked_otp_from_sms(sms):
    m = re.search(r'(\d{3}[\s-]?\d{3})', sms)
    return m.group(1) if m else None

async def build_range_deeplink(c, r, s): return f"https://t.me/bot?start=rng_{r}_{s}"
async def rangechkr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rangechkr command - Show ranges grouped by service"""
    user_id = update.effective_user.id
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await update.message.reply_text("âŒ Your access is pending approval.")
        return
    
    # Get global API client
    api_client = get_global_api_client()
    if not api_client:
        await update.message.reply_text("âŒ API connection error. Please try again.")
        return
    
    # Show service selection first (fixed three: WhatsApp, Facebook, Others)
    keyboard = [
        [InlineKeyboardButton("ðŸ’¬ WhatsApp", callback_data="rangechkr_service_whatsapp")],
        [InlineKeyboardButton("ðŸ‘¥ Facebook", callback_data="rangechkr_service_facebook")],
        [InlineKeyboardButton("âœˆï¸ Telegram", callback_data="rangechkr_service_telegram")],
        [InlineKeyboardButton("âœ¨ Others", callback_data="rangechkr_service_others")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "ðŸ§­ Range Explorer\nSelect a service:",
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
            [KeyboardButton("ðŸš€ Get Number")],
            [KeyboardButton("ðŸŽ› Number Count")],
            [KeyboardButton("ðŸ“ˆ My Stats")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "Welcome.\n\n"
            "Use **Get Number** to start a new OTP session.\n"
            "Use **Number Count** to choose how many numbers you receive per request.\n"
            f"ðŸ“Œ Current setting: **{current_count}** number(s)",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

        # If user opened bot from channel "Range" button, fetch numbers immediately.
        if deep_link_range:
            await update.message.reply_text(f"â³ Processing range: {deep_link_range}")
            await send_numbers_from_range_link(update, context, deep_link_range, deep_link_service)
    elif status == 'rejected':
        await update.message.reply_text("âŒ Your access has been rejected. Please contact admin.")
    else:
        # Notify admin
        try:
            admin_message = f"ðŸ†• New user request:\n\n"
            admin_message += f"User ID: {user_id}\n"
            admin_message += f"Username: @{username}\n"
            admin_message += f"Name: {user.first_name or 'N/A'}"
            
            keyboard = [
                [
                    InlineKeyboardButton("âœ… Approve", callback_data=f"admin_approve_{user_id}"),
                    InlineKeyboardButton("âŒ Reject", callback_data=f"admin_reject_{user_id}")
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
            "â³ Your request has been sent to admin. Please wait for approval."
        )

async def admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin commands"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text("âŒ Access denied. Admin only.")
        return
    
    command = update.message.text.split()[0] if update.message.text else ""
    
    if command == "/users":
        users = get_all_users()
        if not users:
            await update.message.reply_text("ðŸ“‹ No users found.")
            return
        
        message = "ðŸ“‹ All Users:\n\n"
        for uid, uname, status in users:
            message += f"ID: {uid}\n"
            message += f"Username: @{uname or 'N/A'}\n"
            message += f"Status: {status}\n"
            message += f"{'â”€' * 20}\n"
        
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
            await update.message.reply_text(f"âœ… User {target_id} approved/added successfully.")
        except Exception as e:
            await update.message.reply_text(f"âŒ Error: {e}")
    
    elif command.startswith("/remove"):
        try:
            target_id = int(context.args[0]) if context.args else None
            if target_id:
                # Stop any latest monitoring job for this user
                if target_id in user_jobs:
                    user_jobs[target_id].schedule_removal()
                    del user_jobs[target_id]
                remove_user(target_id)
                await update.message.reply_text(f"âœ… User {target_id} removed successfully.")
            else:
                await update.message.reply_text("Usage: /remove <user_id>")
        except Exception as e:
            await update.message.reply_text(f"âŒ Error: {e}")
    
    elif command == "/pending":
        pending = get_pending_users()
        if not pending:
            await update.message.reply_text("âœ… No pending users.")
            return
        
        message = "â³ Pending Users:\n\n"
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
                "ðŸ“£ Broadcast usage:\n"
                "- Reply any message then type: /broadcast\n"
                "- Or: /broadcast <your message>"
            )
            return

        approved_user_ids = get_approved_user_ids()
        if not approved_user_ids:
            await update.message.reply_text("â„¹ï¸ No approved users found to broadcast to.")
            return

        await update.message.reply_text(f"ðŸ“£ Broadcasting to {len(approved_user_ids)} approved user(s)...")

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

        summary = f"âœ… Broadcast done.\n\nSent: {sent}\nFailed: {failed}"
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
            await query.edit_message_text("âŒ Access denied.")
            return
        
        if data.startswith("admin_approve_"):
            target_user_id = int(data.split("_")[2])
            approve_user(target_user_id)
            await query.edit_message_text(f"âœ… User {target_user_id} approved.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="âœ… Your request has been approved! Use /start to begin."
                )
            except:
                pass
        
        elif data.startswith("admin_reject_"):
            target_user_id = int(data.split("_")[2])
            reject_user(target_user_id)
            await query.edit_message_text(f"âŒ User {target_user_id} rejected.")
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="âŒ Your request has been rejected."
                )
            except:
                pass
        return
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await query.edit_message_text("âŒ Your access is pending approval.")
        return
    
    # Handle number count setting (1-5)
    if data.startswith("set_count_"):
        try:
            count = int(data.split("_")[2])
            if count < 1 or count > 5:
                await query.edit_message_text("âŒ Invalid count. Please select 1-5.")
                return
            
            # Update user session with new count
            update_user_session(user_id, number_count=count)
            
            await query.edit_message_text(
                f"âœ… Number count set to {count}.\n\n"
                f"Now you will receive {count} number(s) when you request numbers."
            )
        except (ValueError, IndexError) as e:
            logger.error(f"Error setting number count: {e}")
            await query.edit_message_text("âŒ Error setting number count. Please try again.")
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
                await query.edit_message_text("âŒ Service not found. Please reload.")
                return
        except Exception as e:
            logger.error(f"Error selecting from others: {e}")
            await query.edit_message_text("âŒ Error selecting service.")
            return
    # Service selection (from inline buttons)
    if data.startswith("service_"):
        service_name = data.split("_", 1)[1]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("âŒ API connection error. Please try again.")
            return
        
        # If Others clicked, first show dynamic service list (excluding WhatsApp/Facebook)
        if service_name == "others":
            await query.edit_message_text("â³ Discovering services (this may take a moment)...")
            try:
                # Use get_ranges("others") which searches many keywords
                # No lock needed as APIClient handles internal state
                ranges = await run_api_call(api_client.get_ranges, "others")
                
                if not ranges:
                    await query.edit_message_text("âŒ No services found.")
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
                     row.append(InlineKeyboardButton(label, callback_data=f"sel_others_{idx}"))
                     
                     if len(row) == 2:
                         keyboard.append(row)
                         row = []
                
                if row:
                    keyboard.append(row)
                
                # Pagination buttons
                if total_pages > 1:
                    nav_row = []
                    if page > 0:
                        nav_row.append(InlineKeyboardButton("â—€ï¸ Prev", callback_data="sel_others_prev"))
                    nav_row.append(InlineKeyboardButton(f"Page {page + 1}/{total_pages}", callback_data="sel_others_noop"))
                    if page < total_pages - 1:
                        nav_row.append(InlineKeyboardButton("Next â–¶ï¸", callback_data="sel_others_next"))
                    keyboard.append(nav_row)
                
                keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_services")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                page_info = f" (Page {page + 1}/{total_pages})" if total_pages > 1 else ""
                await query.edit_message_text(
                    f"ðŸ“‹ Found {len(sorted_services)} Services{page_info}:\nShowing {len(page_services)} services", 
                    reply_markup=reply_markup
                )
            
            except Exception as e:
                logger.error(f"Error discovering services: {e}")
                await query.edit_message_text(f"âŒ Error discovering services: {str(e)}")
            return
        
        # For primary services (WhatsApp/Facebook)
        app_id = resolve_app_id(service_name, context)
        if not app_id:
            await query.edit_message_text("âŒ Invalid service.")
            return
        
        ranges = await run_api_call(api_client.get_ranges, app_id)
        
        if not ranges:
            await query.edit_message_text(f"âŒ No active ranges available for {service_name}.")
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
            
            row.append(InlineKeyboardButton(label1, callback_data=f"country_{service_name}_{c1}"))
            
            if i + 1 < len(sorted_countries):
                c2 = sorted_countries[i + 1]
                _, time2 = get_country_best_time(c2)
                flag2 = get_country_flag(c2)
                label2 = format_country_label(flag2, c2, time2)
                row.append(InlineKeyboardButton(label2, callback_data=f"country_{service_name}_{c2}"))
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_services")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"ðŸ“± {service_name.upper()} - Select Country:",
            reply_markup=reply_markup
        )
        return

    # Service selection for dynamic Others list (New Flow)
    if data.startswith("service_others_"):
        try:
            idx = int(data.split("_")[2])
            discovered = context.user_data.get('discovered_services', [])
            if idx < 0 or idx >= len(discovered):
                await query.edit_message_text("âŒ Invalid service.")
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
                await query.edit_message_text("âŒ API connection error.")
                return
                
            # Get ranges "others" (cached)
            ranges = await run_api_call(api_client.get_ranges, "others")
            
            if not ranges:
                await query.edit_message_text("âŒ No ranges found (session expired?).")
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
                 await query.edit_message_text(f"âŒ No ranges found for {service_name}.")
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
                
                row.append(InlineKeyboardButton(label1, callback_data=f"country_{service_key}_{c1}"))
                
                if i + 1 < len(sorted_countries):
                    c2 = sorted_countries[i + 1]
                    _, time2 = get_country_best_time(c2)
                    flag2 = get_country_flag(c2)
                    label2 = format_country_label(flag2, c2, time2)
                    row.append(InlineKeyboardButton(label2, callback_data=f"country_{service_key}_{c2}"))
                
                keyboard.append(row)
                
            keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="service_others")]) 
            # Back goes to Main Others List (handled by service_others in main handler)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"ðŸ“± {service_name} - Select Country:", reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in service_others: {e}")
            await query.edit_message_text("âŒ Error loading countries.")
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
            await query.edit_message_text("âŒ Invalid service.")
            return
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("âŒ API connection error. Please try again.")
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
                        logger.info(f"âœ“ Range {range_name} MATCHED (both API and name agree on {country})")
                    else:
                        logger.info(f"âœ— Range {range_name} SKIPPED (API says {r_country_api} but name suggests {r_country_detected})")
                else:
                    # Can't detect from range name, trust API
                    is_match = True
                    logger.info(f"âœ“ Range {range_name} MATCHED (trusting API {r_country_api}, can't detect from name)")
            # Fallback: if API provides no country info, use range name detection
            elif not r_country_api or r_country_api.strip() == '' or r_country_api == 'Unknown':
                r_country_detected = detect_country_from_range(range_name)
                if r_country_detected and r_country_detected.lower() == country.lower():
                    is_match = True
                    logger.info(f"âœ“ Range {range_name} MATCHED (no API country, detected {r_country_detected})")
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
            await query.edit_message_text(f"âŒ No ranges found for {country}.")
            return
        
        range_id = selected_range.get('numerical_id', selected_range.get('range_id', selected_range.get('id', '')))
        range_name = selected_range.get('pattern', selected_range.get('name', ''))
        
        # Show loading message and acknowledge callback immediately
        await query.edit_message_text("â³ Requesting numbers...")
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
                        message_id=query.message.message_id,
                        text="âŒ Failed to get numbers. Please try again."
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
                        text="âŒ No valid numbers received. Please try again."
                    )
                    return
                
                country_name = numbers_data[0].get('cantryName', numbers_data[0].get('country', country))
                
                # Sort numbers for Ivory Coast (22507 priority)
                numbers_list = sort_numbers_for_ivory_coast(numbers_list, country_name)
                
                # Store all numbers in session (comma-separated)
                numbers_str = ','.join(numbers_list)
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
                    keyboard.append([InlineKeyboardButton(f"ðŸ“± {display_num}", api_kwargs={"copy_text": {"text": display_num}})])
                
                # Get country flag
                country_flag = get_country_flag(country_name)
                
                # Get service icon
                service_icons = {
                    "whatsapp": "ðŸ’¬",
                    "facebook": "ðŸ‘¥",
                    "telegram": "âœˆï¸"
                }
                service_icon = service_icons.get(service_name, "ðŸ“±")
                
                keyboard.append([InlineKeyboardButton("ðŸ”„ Next Number", callback_data=f"country_{service_name}_{country}")])
                keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_services")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Format message like the reference image
                message = f"Country: {country_flag} {country_name}\n"
                message += f"Service: {service_icon} {service_name.capitalize()}\n"
                message += f"Waiting for OTP...... â³"
                
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
                        text=f"âŒ Error: {str(e)}"
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
                await query.edit_message_text("âŒ Invalid service.")
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
                await query.edit_message_text("âŒ API connection error. Please try again.")
                return
            
            # Get ranges "others" (cached fast)
            ranges = await run_api_call(api_client.get_ranges, "others")
            
            if not ranges:
                await query.edit_message_text(f"âŒ No ranges found for {service_name}.")
                return
            
            # Filter by service
            service_ranges = []
            for r in ranges:
                s = r.get('service', 'Other')
                if s and str(s).strip() == service_name:
                    service_ranges.append(r)
            
            if not service_ranges:
                await query.edit_message_text(f"âŒ No ranges found for {service_name}.")
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
            
            keyboard.append([InlineKeyboardButton("ðŸ”™ Services", callback_data="rangechkr_service_others")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"ðŸ“‹ {service_name} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error fetching ranges for {service_name}: {e}")
            await query.edit_message_text(f"âŒ Failed to load ranges.")
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
                    await query.edit_message_text("âŒ Service not found in session. Please reload.")
                    return
        except Exception as e:
            logger.error(f"Error handling others service selection: {e}")
            await query.edit_message_text("âŒ Error selecting service.")
            return
    
    # Range checker country selection
    elif data.startswith("rangechkr_country_"):
        parts = data.split("_", 3)
        if len(parts) < 4:
            await query.edit_message_text("âŒ Invalid selection.")
            return
            
        service_name = parts[2]
        country = parts[3]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("âŒ API connection error.")
            return
            
        await query.edit_message_text(f"â³ Loading ranges for {country}...")
        
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
                await query.edit_message_text(f"âŒ No ranges found for {country}.")
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
                row.append(InlineKeyboardButton(display_name1, callback_data=f"rng_{range_hash1}"))
                
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
                    row.append(InlineKeyboardButton(display_name2, callback_data=f"rng_{range_hash2}"))
                
                keyboard.append(row)
            
            # Back Button
            if service_name.lower() in ['whatsapp', 'facebook']:
                 keyboard.append([InlineKeyboardButton("ðŸ”™ Countries", callback_data=f"rangechkr_service_{service_name}")])
            else:
                 # For Others, just go back to App List for now
                 keyboard.append([InlineKeyboardButton("ðŸ”™ Services", callback_data="rangechkr_service_others")])

            reply_markup = InlineKeyboardMarkup(keyboard)
            
            display_service = service_name.upper() if service_name in ['whatsapp', 'facebook'] else service_name
            await query.edit_message_text(
                f"ðŸ“‹ {display_service} - {country} ({len(filtered_ranges)} ranges):\nSelect a range:",
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"Error in rangechkr_country: {e}")
            await query.edit_message_text(f"âŒ Error: {str(e)}")

    # Range checker service selection
    elif data.startswith("rangechkr_service_"):
        service_name = data.split("_", 2)[2]
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await query.edit_message_text("âŒ API connection error. Please try again.")
            return
        
        await query.edit_message_text("â³ Loading ranges...")
        
        try:
            # Handle "others" - first show dynamic service list
            # Handle "others" - first show dynamic service list (New Flow)
            if service_name == "others":
                await query.edit_message_text("â³ Discovering services (this may take a moment)...")
                try:
                    # Get ranges "others"
                    ranges = await run_api_call(api_client.get_ranges, "others")
                    
                    if not ranges:
                        await query.edit_message_text("âŒ No services found.")
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
                        row.append(InlineKeyboardButton(label, callback_data=f"rangechkr_others_{idx}"))
                        
                        if len(row) == 2:
                            keyboard.append(row)
                            row = []
                    
                    if row:
                        keyboard.append(row)
                    
                    # Pagination buttons
                    if total_pages > 1:
                        nav_row = []
                        if page > 0:
                            nav_row.append(InlineKeyboardButton("â—€ï¸ Prev", callback_data="rangechkr_others_prev"))
                        nav_row.append(InlineKeyboardButton(f"Page {page + 1}/{total_pages}", callback_data="rangechkr_others_noop"))
                        if page < total_pages - 1:
                            nav_row.append(InlineKeyboardButton("Next â–¶ï¸", callback_data="rangechkr_others_next"))
                        keyboard.append(nav_row)
                    
                    keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="rangechkr_back_services")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    page_info = f" (Page {page + 1}/{total_pages})" if total_pages > 1 else ""
                    await query.edit_message_text(
                        f"ðŸ“‹ Found {len(sorted_services)} Services{page_info}:\nShowing {len(page_services)} services", 
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error discovering services: {e}")
                    await query.edit_message_text(f"âŒ Error discovering services.")
                return
            else:
                # Handle specific services (WhatsApp, Facebook)
                app_id = resolve_app_id(service_name, context)
                if not app_id:
                    await query.edit_message_text("âŒ Invalid service.")
                    return

                ranges = await run_api_call(api_client.get_ranges, app_id)

                if not ranges or len(ranges) == 0:
                    await query.edit_message_text(f"âŒ No ranges found for {service_name.upper()}.")
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
            
            keyboard.append([InlineKeyboardButton("ðŸ”™ Services", callback_data="rangechkr_back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            display_service_name = "Others" if service_name == "others" else service_name.upper()
            await query.edit_message_text(
                f"ðŸ“‹ {display_service_name} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error loading ranges: {e}")
            await query.edit_message_text(f"âŒ Error loading ranges: {str(e)}")
    
    # Range checker range selection (using hash)
    elif data.startswith("rng_"):
        range_hash = data.split("_", 1)[1]
        
        # Retrieve range info from context
        logger.info(f"Range hash received: {range_hash}, user_data keys: {list(context.user_data.keys())}")
        if 'range_mapping' not in context.user_data:
            logger.error(f"range_mapping not found in user_data for user {user_id}")
            await query.edit_message_text("âŒ Range mapping not found. Please select range again from /rangechkr.")
            return
        
        if range_hash not in context.user_data['range_mapping']:
            logger.error(f"Range hash {range_hash} not found in mapping. Available hashes: {list(context.user_data['range_mapping'].keys())}")
            await query.edit_message_text("âŒ Range not found. Please select range again from /rangechkr.")
            return
        
        range_info = context.user_data['range_mapping'][range_hash]
        service_name = range_info['service']
        range_id = range_info['range_id']
        range_name = range_info.get('range_name', range_id)
        range_id_field = range_info.get('range_id_field', '')
        
        logger.info(f"Retrieved range: service={service_name}, range_id={range_id}, range_name={range_name}, range_id_field={range_id_field}")
        
        await query.edit_message_text("â³ Requesting numbers from range...")
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
                        text="âŒ API connection error. Please try again."
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
                        message_id=query.message.message_id,
                        text="âŒ Failed to get numbers from this range. Please try again."
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
                        text="âŒ No valid numbers received. Please try again."
                    )
                    return
                
                # Get service info
                app_id = resolve_app_id(service_name, context)
                if not app_id:
                    logger.error(f"Invalid service_name in range selection: {service_name}")
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=query.message.message_id,
                        text=f"âŒ Invalid service: {service_name}"
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
                        f"ðŸ“± {display_num}",
                        api_kwargs={"copy_text": {"text": display_num}}
                    )])
                
                # Use hash for change numbers button too
                change_hash = hashlib.md5(f"{service_name}_{range_id}".encode()).hexdigest()[:12]
                context.user_data['range_mapping'][change_hash] = {'service': service_name, 'range_id': range_id}
                keyboard.append([InlineKeyboardButton("ðŸ”„ Change Numbers", callback_data=f"rng_{change_hash}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Get country flag
                country_flag = get_country_flag(country_name) if country_name else "ðŸŒ"
                
                # Get service icon
                service_icons = {
                    "whatsapp": "ðŸ’¬",
                    "facebook": "ðŸ‘¥",
                    "telegram": "âœˆï¸"
                }
                service_icon = service_icons.get(service_name, "ðŸ“±")
                
                message_text = f"{service_icon} {service_name.upper()}\n"
                if country_name:
                    message_text += f"{country_flag} {country_name}\n"
                message_text += f"ðŸ“‹ Range: {range_id}\n\n"
                message_text += f"âœ… {len(numbers_list)} numbers received:\n\n"
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
                    'start_time': time.time(),
                    'message_id': query.message.message_id
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
                        text=f"âŒ Error: {str(e)}\n\nRange ID: {range_id}\nService: {service_name}"
                    )
                except:
                    pass
        
        # Run async task
        import asyncio
        asyncio.create_task(fetch_and_send_range_numbers())
    
    # Range checker back to services
    elif data == "rangechkr_back_services":
        keyboard = [
            [InlineKeyboardButton("ðŸ’¬ WhatsApp", callback_data="rangechkr_service_whatsapp")],
            [InlineKeyboardButton("ðŸ‘¥ Facebook", callback_data="rangechkr_service_facebook")],
            [InlineKeyboardButton("âœˆï¸ Telegram", callback_data="rangechkr_service_telegram")],
            [InlineKeyboardButton("âœ¨ Others", callback_data="rangechkr_service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "ðŸ§­ Range Explorer\nSelect a service:",
            reply_markup=reply_markup
        )
    
    # Back to services
    elif data == "back_services":
        keyboard = [
            [InlineKeyboardButton("ðŸ’¬ WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("ðŸ‘¥ Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("âœˆï¸ Telegram", callback_data="service_telegram")],
            [InlineKeyboardButton("âœ¨ Others", callback_data="service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "ðŸŽ¯ Select a service:",
            reply_markup=reply_markup
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (keyboard button presses)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Check if user is approved
    status = get_user_status(user_id)
    if status != 'approved':
        await update.message.reply_text("âŒ Your access is pending approval.")
        return
    
    # Handle "Get Number" button
    if text in ("Get Number", "ðŸ“² Get Number", "ðŸš€ Get Number"):
        keyboard = [
            [InlineKeyboardButton("ðŸ’¬ WhatsApp", callback_data="service_whatsapp")],
            [InlineKeyboardButton("ðŸ‘¥ Facebook", callback_data="service_facebook")],
            [InlineKeyboardButton("âœˆï¸ Telegram", callback_data="service_telegram")],
            [InlineKeyboardButton("âœ¨ Others", callback_data="service_others")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "ðŸŽ¯ Select a service:",
            reply_markup=reply_markup
        )
        return
    
    # Handle "Set Number Count" button
    if text in ("Set Number Count", "ðŸ§® Set Number Count", "âš™ï¸ Number Count", "ðŸŽ› Number Count", "Number Count"):
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
    if text in ("My Stats", "ðŸ“Š My Stats", "ðŸ“ˆ My Stats"):
        today_count = get_today_otp_count(user_id)
        bd_now = get_bd_now()
        await update.message.reply_text(
            "My Stats\n\n"
            f"ðŸ•’ BD time now: {bd_now.strftime('%Y-%m-%d %I:%M:%S %p')}\n"
            f"âœ… Today you received: {today_count} OTP(s)."
        )
        return
    
    # Handle service selection (old format - for backward compatibility)
    if text in ["ðŸ’¬ WhatsApp", "ðŸ‘¥ Facebook", "âœˆï¸ Telegram", "ðŸŸ¢ WhatsApp", "ðŸ”µ Facebook", "ðŸ›© Telegram", "WhatsApp", "Facebook", "Telegram"]:
        service_map = {
            "ðŸ’¬ WhatsApp": "whatsapp",
            "ðŸ‘¥ Facebook": "facebook",
            "âœˆï¸ Telegram": "telegram",
            "ðŸŸ¢ WhatsApp": "whatsapp",
            "ðŸ”µ Facebook": "facebook",
            "ðŸ›© Telegram": "telegram",
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
            await update.message.reply_text("âŒ API connection error. Please try again.")
            return
        
        try:
            ranges = await run_api_call(api_client.get_ranges, app_id)
            
            if not ranges:
                await update.message.reply_text(f"âŒ No active ranges available for {service_name}.")
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
            
            keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"ðŸ“± {service_name.upper()} - Select Country:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error in handle_message service selection: {e}")
            await update.message.reply_text(f"âŒ Error: {str(e)}")
    
    # Handle direct range input (e.g., "24491501XXX" or "24491501")
    elif re.match(r'^[\dXx]+$', text) and len(text) >= 6:
        # Direct range buy: always use WhatsApp without active-range lookup.
        range_pattern = text.upper()
        
        # Get global API client
        api_client = get_global_api_client()
        if not api_client:
            await update.message.reply_text("âŒ API connection error. Please try again.")
            return

        found_service = "whatsapp"
        range_name = range_pattern
        range_id = range_pattern
        await update.message.reply_text("â³ Buying directly via WhatsApp...")
        
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
                await update.message.reply_text("âŒ Failed to get numbers from this range. Please try again.")
                return
            
            # Extract numbers
            numbers_list = []
            for num_data in numbers_data:
                number = num_data.get('number', '')
                if number:
                    numbers_list.append(number)
            
            if not numbers_list:
                await update.message.reply_text("âŒ No valid numbers received. Please try again.")
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
                    f"ðŸ“± {display_num}",
                    api_kwargs={"copy_text": {"text": display_num}}
                )])
            
            # Use hash for change numbers button
            if 'range_mapping' not in context.user_data:
                context.user_data['range_mapping'] = {}
            change_hash = hashlib.md5(f"{found_service}_{range_id}".encode()).hexdigest()[:12]
            context.user_data['range_mapping'][change_hash] = {'service': found_service, 'range_id': range_id}
            keyboard.append([InlineKeyboardButton("ðŸ”„ Change Numbers", callback_data=f"rng_{change_hash}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Get country flag
            country_flag = get_country_flag(country_name) if country_name else "ðŸŒ"
            
            # Get service icon
            service_icons = {
                "whatsapp": "ðŸ’¬",
                "facebook": "ðŸ‘¥",
                "telegram": "âœˆï¸"
            }
            service_icon = service_icons.get(found_service, "ðŸ“±")
            
            message_text = f"{service_icon} {found_service.upper()}\n"
            if country_name:
                message_text += f"{country_flag} {country_name}\n"
            message_text += f"ðŸ“‹ Range: {range_id}\n\n"
            message_text += f"âœ… {len(numbers_list)} numbers received:\n\n"
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
            await update.message.reply_text(f"âŒ Error: {error_msg}")
    
    # Handle country selection (old format - for backward compatibility)
    elif any(text.startswith(f) for f in ["ðŸ‡¦ðŸ‡´", "ðŸ‡°ðŸ‡²", "ðŸ‡·ðŸ‡´", "ðŸ‡©ðŸ‡°", "ðŸ‡§ðŸ‡©", "ðŸ‡®ðŸ‡³", "ðŸ‡ºðŸ‡¸", "ðŸ‡¬ðŸ‡§", "ðŸŒ"]) or "ðŸ”™" in text or "Back" in text:
        if "Back" in text:
            keyboard = [
                [KeyboardButton("ðŸš€ Get Number")],
                [KeyboardButton("ðŸŽ› Number Count")],
                [KeyboardButton("ðŸ“ˆ My Stats")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            await update.message.reply_text(
                "âœ¨ Ready when you are. Tap ðŸš€ Get Number to start.",
                reply_markup=reply_markup
            )
            return
        
        # Extract country name from button text (remove flag)
        country = re.sub(r'^[ðŸ‡¦-ðŸ‡¿\s]+', '', text).strip()
        
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
            await update.message.reply_text("âŒ API connection error. Please try again.")
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
                await update.message.reply_text(f"âŒ No ranges found for {country}.")
                return
            
            range_id = selected_range.get('name', selected_range.get('id', ''))
            range_name = selected_range.get('name', '')
            
            # Get user's number count preference
            session = get_user_session(user_id)
            number_count = session.get('number_count', 2) if session else 2
            
            # Request numbers
            await update.message.reply_text(f"â³ Requesting {number_count} number(s)...")
            
            # Try range_name first, then range_id (like otp_tool.py)
            numbers_data = await run_api_call(api_client.get_multiple_numbers, range_id, range_name, number_count)
            
            if not numbers_data or len(numbers_data) == 0:
                await update.message.reply_text("âŒ Failed to get numbers. Please try again.")
                return
            
            # Extract numbers and store them
            numbers_list = []
            for num_data in numbers_data:
                number = num_data.get('number', '')
                if number:
                    numbers_list.append(number)
            
            if not numbers_list:
                await update.message.reply_text("âŒ No valid numbers received. Please try again.")
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
                keyboard.append([InlineKeyboardButton(f"ðŸ“± {display_num}", api_kwargs={"copy_text": {"text": display_num}})])
            
            # Get country flag
            country_flag = get_country_flag(country_name)
            
            # Get service icon
            service_icons = {
                "whatsapp": "ðŸ’¬",
                "facebook": "ðŸ‘¥",
                "telegram": "âœˆï¸"
            }
            service_icon = service_icons.get(service_name, "ðŸ“±")
            
            keyboard.append([InlineKeyboardButton("ðŸ”„ Next Number", callback_data=f"country_{service_name}_{country_name}")])
            keyboard.append([InlineKeyboardButton("ðŸ”™ Back", callback_data="back_services")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Format message like the reference image
            message = f"Country: {country_flag} {country_name}\n"
            message += f"Service: {service_icon} {service_name.capitalize()}\n"
            message += f"Waiting for OTP...... â³"
            
            sent_msg = await update.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error in handle_message country selection: {e}")
            await update.message.reply_text(f"âŒ Error: {str(e)}")

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
        logger.error(f"âŒ monitor_otp: user_id is None! job_data: {job_data}, job.chat_id: {job.chat_id}")
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
            # Keep the same numbers visible and mark unresolved numbers as expired.
            service_name = str(job_data.get('service') or 'Unknown')
            country_name = str(job_data.get('country') or 'Unknown')
            range_id = str(job_data.get('range_id') or '').strip()

            service_icons = {
                "whatsapp": "ðŸ’¬",
                "facebook": "ðŸ‘¥",
                "telegram": "âœˆï¸"
            }
            service_icon = service_icons.get(service_name, "ðŸ“±")
            country_flag = get_country_flag(country_name) if country_name and country_name != 'Unknown' else "ðŸŒ"

            keyboard = []
            status_lines = []
            for num in numbers:
                status_label = "OTP" if num in received_otps else "Expired"
                button_label = f"ðŸ“± {num} ({status_label})"
                keyboard.append([InlineKeyboardButton(
                    button_label,
                    api_kwargs={"copy_text": {"text": num}}
                )])
                status_lines.append(f"{num} - {status_label}")

            timeout_text = f"{service_icon} {service_name.upper()}\n"
            if country_name and country_name != 'Unknown':
                timeout_text += f"{country_flag} {country_name}\n"
            if range_id:
                timeout_text += f"ðŸ“‹ Range: {range_id}\n"
            timeout_text += "\nâ±ï¸ Timeout! No OTP received within 15 minutes.\n\n"
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
                    logger.info(f"âœ… OTP detected for {number}: {otp}")
                elif sms_content:
                    logger.debug(f"âš ï¸ SMS content found but no OTP extracted: {sms_content[:100]}")
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
                    motivation_line = html.escape(get_random_bn_otp_motivation())
                    
                    # Format OTP message for USER: "ðŸ‡©ðŸ‡° #DK WhatsApp <code>4540797881</code> English"
                    # Use <code> tag for click-to-copy (Telegram default format)
                    user_otp_msg = (
                        f"{country_flag} #{country_code} {service.capitalize()} <code>{display_number}</code> {language}\n\n"
                        f"<b>à¦†à¦œà¦•à§‡à¦° à¦ªà§à¦°à§‡à¦°à¦£à¦¾:</b> {motivation_line}"
                    )
                    
                    # Format OTP message for CHANNEL: "ðŸ‡©ðŸ‡° #DK WhatsApp 4540XXXX81 English"
                    # Mask number for channel (middle digits with XXXX)
                    masked_number = mask_number(number)
                    if masked_number.startswith('+'):
                        masked_number = masked_number[1:]  # Remove + for display
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
                    user_keyboard = [[InlineKeyboardButton(f"ðŸ” {otp}", api_kwargs={"copy_text": {"text": otp}})]]
                    user_reply_markup = InlineKeyboardMarkup(user_keyboard)

                    # Channel keyboard: OTP copy + Range button side by side.
                    channel_row = [InlineKeyboardButton(f"ðŸ” {otp}", api_kwargs={"copy_text": {"text": otp}})]
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
                        logger.info(f"âœ… OTP message sent successfully to user {user_id} (message_id: {sent_msg.message_id}) for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"âŒ Error sending OTP message to user {user_id}: {type(e).__name__}: {e}")
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
                        logger.info(f"âœ… OTP forwarded to channel {OTP_CHANNEL_ID} for {number}: {otp}")
                    except Exception as e:
                        logger.error(f"âŒ Error sending OTP message to channel {OTP_CHANNEL_ID}: {type(e).__name__}: {e}")
                    
                    # Log warning if user message failed but channel succeeded
                    if not user_message_sent:
                        logger.warning(f"âš ï¸ OTP sent to channel but NOT to user {user_id} for {number}: {otp}")
                    
                    # Increment per-day OTP counter (BD time)
                    increment_otp_count(user_id)

                    # Check if all numbers have received OTP
                    all_received = all(num in received_otps for num in numbers)
                    if all_received:
                        # All numbers received OTP, stop monitoring
                        logger.info(f"âœ… All numbers received OTP for user {user_id}, stopping monitoring")
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
            if service in ["******", "alymscintl"]:
                service = "WhatsApp"
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
            range_value = str(log_item.get('range') or '').strip()
            range_url = await build_range_deeplink(context, range_value, service_key)

            channel_row = [InlineKeyboardButton(f"ðŸ” {masked_otp}", api_kwargs={"copy_text": {"text": masked_otp}})]
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
        logger.info("âœ… API client initialized (login will retry on first API call if needed)")
    
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
            logger.warning(f"âš ï¸ Conflict error detected: {error}. This usually means multiple bot instances are running. Waiting and retrying...")
            # Wait a bit and let the other instance handle it, or this instance will take over
            await asyncio.sleep(5)
        else:
            logger.error(f"âŒ Error: {error}", exc_info=error)
    
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
        logger.error(f"âŒ Conflict error on startup: {e}. Another bot instance may be running.")
        logger.info("ðŸ’¡ If you're sure only one instance should run, wait a few seconds and the bot will retry.")
        # Wait and retry once
        import time
        time.sleep(10)
        logger.info("ðŸ”„ Retrying bot startup...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )

if __name__ == "__main__":
    main()

