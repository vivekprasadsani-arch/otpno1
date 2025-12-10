import requests
import json
import time
import re
from datetime import datetime

<<<<<<< HEAD
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

class OTPTool:
    def __init__(self):
        self.base_url = "https://v2.mnitnetwork.com"
        # Use curl_cffi if available (best for Cloudflare bypass)
        if HAS_CURL_CFFI:
            self.session = curl_requests.Session(impersonate="chrome110")
            self.use_curl = True
            print("Using curl_cffi for Cloudflare bypass")
        elif HAS_CLOUDSCRAPER:
            self.session = cloudscraper.create_scraper()
            self.use_curl = False
            print("Using cloudscraper for Cloudflare bypass")
        else:
            self.session = requests.Session()
            self.use_curl = False
            print("Warning: No Cloudflare bypass available, using standard requests")
            print("Install curl_cffi for better Cloudflare bypass: pip install curl_cffi")
=======
class OTPTool:
    def __init__(self):
        self.base_url = "https://v2.mnitnetwork.com"
        self.session = requests.Session()
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
        self.auth_token = None
        self.selected_number = None
        self.selected_range = None
        self.email = "roni791158@gmail.com"
        self.password = "47611858@Dove"
        
        # Browser-like headers to avoid session expiration
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
        """Login to the panel"""
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
                    print(f"Login response missing data: {login_data}")
                    return False
                
                if 'user' not in login_data['data'] or 'session' not in login_data['data']['user']:
                    print(f"Login response missing user session: {login_data}")
                    return False
                
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                session_token = login_data['data']['user']['session']
                
                # Set session cookie properly
                self.session.cookies.set('mnitnetworkcom_session', session_token, domain='v2.mnitnetwork.com')
                
<<<<<<< HEAD
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
=======
                hitauth_headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": self.browser_headers["User-Agent"],
                    "Accept": self.browser_headers["Accept"],
                    "Origin": self.browser_headers["Origin"],
                    "Referer": f"{self.base_url}/dashboard/getnum"
                }
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
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
                        print(f"Hitauth response missing data: {hitauth_data}")
                        return False
                    
                    if 'token' not in hitauth_data['data']:
                        print(f"Hitauth response missing token: {hitauth_data}")
                        return False
                    
=======
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
                    self.auth_token = hitauth_data['data']['token']
                    
                    # Set account type cookie
                    self.session.cookies.set('mnitnetworkcom_accountType', 'user', domain='v2.mnitnetwork.com')
                    
                    # Store mhitauth token in cookie (browser does this)
                    self.session.cookies.set('mnitnetworkcom_mhitauth', self.auth_token, domain='v2.mnitnetwork.com')
                    
                    return True
<<<<<<< HEAD
            else:
                # Log non-200 status codes
                try:
                    error_data = login_resp.json()
                    print(f"Login failed with status {login_resp.status_code}: {error_data}")
                except:
                    print(f"Login failed with status {login_resp.status_code}: {login_resp.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Login network error: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"Login JSON decode error: {e}")
            try:
                print(f"Response text: {login_resp.text[:200]}")
            except:
                pass
            return False
        except Exception as e:
            print(f"Login error: {e}")
            import traceback
            print(traceback.format_exc())
=======
            return False
        except Exception as e:
            print(f"Login error: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            return False
    
    def refresh_token(self):
        """Refresh authentication token if expired"""
        try:
            # Get session token from cookies
            session_token = self.session.cookies.get('mnitnetworkcom_session', '')
            if not session_token:
                # If no session, need to login again
                return self.login()
            
<<<<<<< HEAD
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
=======
            hitauth_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": self.browser_headers["User-Agent"],
                "Accept": self.browser_headers["Accept"],
                "Origin": self.browser_headers["Origin"],
                "Referer": f"{self.base_url}/dashboard/getnum"
            }
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            
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
                    print(f"Token refresh response missing data: {hitauth_data}")
                    return False
                
                if 'token' not in hitauth_data['data']:
                    print(f"Token refresh response missing token: {hitauth_data}")
                    return False
                
                self.auth_token = hitauth_data['data']['token']
                self.session.cookies.set('mnitnetworkcom_mhitauth', self.auth_token, domain='v2.mnitnetwork.com')
                return True
            else:
                # Log non-200 status codes
                try:
                    error_data = hitauth_resp.json()
                    print(f"Token refresh failed with status {hitauth_resp.status_code}: {error_data}")
                except:
                    print(f"Token refresh failed with status {hitauth_resp.status_code}: {hitauth_resp.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Token refresh network error: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"Token refresh JSON decode error: {e}")
            try:
                print(f"Response text: {hitauth_resp.text[:200]}")
            except:
                pass
            return False
        except Exception as e:
            print(f"Token refresh error: {e}")
            import traceback
            print(traceback.format_exc())
=======
                self.auth_token = hitauth_data['data']['token']
                self.session.cookies.set('mnitnetworkcom_mhitauth', self.auth_token, domain='v2.mnitnetwork.com')
                return True
            return False
        except Exception as e:
            print(f"Token refresh error: {e}")
>>>>>>> 6262504419f048a0ff6b86dca2aca66cd3e031d3
            return False
    
    def _handle_token_expired(self):
        """Handle token expiration by refreshing"""
        print("\n[Token expired] Refreshing token...")
        if self.refresh_token():
            print("[Token refreshed successfully]")
            return True
        else:
            print("[Token refresh failed] Logging in again...")
            return self.login()
    
    def get_ranges(self, app_id):
        """Get active ranges for an application"""
        try:
            # HAR file shows getac API uses mhitauth as header (even for GET requests)
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
            if resp.status_code == 200:
                data = resp.json()
                if 'data' in data and data['data'] is not None:
                    return data['data']
                else:
                    # Check if token expired
                    if 'message' in data and ('expired' in data['message'].lower() or 'unauthorized' in data['message'].lower()):
                        if self._handle_token_expired():
                            # Retry the request
                            resp = self.session.get(
                                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getac?type=carriers&appId={app_id}",
                                headers=headers,
                                timeout=15
                            )
                            if resp.status_code == 200:
                                retry_data = resp.json()
                                if 'data' in retry_data and retry_data['data'] is not None:
                                    return retry_data['data']
                    else:
                        if 'message' in data:
                            print(f"Warning: {data['message']}")
            else:
                print(f"Error: API returned status {resp.status_code}")
                try:
                    error_data = resp.json()
                    if 'message' in error_data:
                        print(f"Error message: {error_data['message']}")
                except:
                    print(f"Response: {resp.text[:200]}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Network error getting ranges: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Response text: {resp.text[:200]}")
            return []
        except Exception as e:
            print(f"Unexpected error getting ranges: {e}")
            return []
    
    def get_number(self, range_id):
        """Request a number from a range"""
        try:
            # HAR file shows POST requests use mhitauth as header
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
                # Check if token expired
                if 'message' in data and ('expired' in data.get('message', '').lower() or 'unauthorized' in data.get('message', '').lower()):
                    if self._handle_token_expired():
                        # Retry the request
                        headers = {
                            "Content-Type": "application/x-www-form-urlencoded",
                            "mhitauth": self.auth_token,
                            **{k: v for k, v in self.browser_headers.items() if k not in ["Content-Type", "Origin", "Referer"]}
                        }
                        headers["Origin"] = self.base_url
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
                            self.selected_number = number_data['number']
                            self.selected_range = range_id
                            return number_data
                        elif 'num' in number_data and isinstance(number_data['num'], list) and len(number_data['num']) > 0:
                            num = number_data['num'][0]
                            self.selected_number = num.get('number')
                            self.selected_range = range_id
                            return num
                    elif isinstance(number_data, list) and len(number_data) > 0:
                        num = number_data[0]
                        if isinstance(num, dict) and 'number' in num:
                            self.selected_number = num['number']
                            self.selected_range = range_id
                            return num
                if 'message' in data:
                    print(f"Response: {data['message']}")
            return None
        except Exception as e:
            print(f"Error getting number: {e}")
            return None
    
    def check_otp(self, number=None):
        """Check for OTP on the selected number"""
        try:
            today = datetime.now().strftime("%d_%m_%Y")
            # HAR file shows cache buster timestamp parameter is used
            import time
            timestamp = int(time.time() * 1000)  # Milliseconds timestamp for cache busting
            
            # HAR file shows mhitauth is sent as query parameter, not header
            headers = {
                **{k: v for k, v in self.browser_headers.items() if k not in ["Origin", "Referer", "Content-Type"]}
            }
            headers["Origin"] = self.base_url
            headers["Referer"] = f"{self.base_url}/dashboard/getnum"
            # Add timestamp cache buster parameter like browser does
            resp = self.session.get(
                f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&_={timestamp}&mhitauth={self.auth_token}",
                headers=headers,
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                # Check if token expired
                if 'message' in data and ('expired' in data.get('message', '').lower() or 'unauthorized' in data.get('message', '').lower()):
                    if self._handle_token_expired():
                        # Retry the request
                        headers = {
                            **{k: v for k, v in self.browser_headers.items() if k not in ["Origin", "Referer", "Content-Type"]}
                        }
                        headers["Origin"] = self.base_url
                        headers["Referer"] = f"{self.base_url}/dashboard/getnum"
                        resp = self.session.get(
                            f"{self.base_url}/api/v1/mnitnetworkcom/dashboard/getnuminfo?_date={today}&_page=1&mhitauth={self.auth_token}",
                            headers=headers,
                            timeout=15
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                
                # Handle None or empty responses
                if not data or not isinstance(data, dict):
                    return None
                
                # Check if 'data' key exists and is not None
                if 'data' in data and data['data'] is not None:
                    data_obj = data['data']
                    # Check if 'num' key exists in data_obj and is not None
                    if isinstance(data_obj, dict) and 'num' in data_obj and data_obj['num'] is not None:
                        numbers = data_obj['num']
                        # Ensure numbers is a list
                        if not isinstance(numbers, list):
                            return None
                        
                        target = number or self.selected_number
                        if target:
                            # Normalize number comparison (with/without + and spaces)
                            target_normalized = target.replace('+', '').replace(' ', '').replace('-', '').strip()
                            # Find the specific number in the list
                            for num_data in numbers:
                                if isinstance(num_data, dict):
                                    num_value = num_data.get('number', '')
                                    num_normalized = num_value.replace('+', '').replace(' ', '').replace('-', '').strip()
                                    if num_normalized == target_normalized:
                                        return num_data
                            
                            # If exact match not found, try partial match (last 9-10 digits)
                            target_digits = ''.join(filter(str.isdigit, target_normalized))
                            if len(target_digits) >= 9:
                                last_digits = target_digits[-9:]  # Last 9 digits
                                for num_data in numbers:
                                    if isinstance(num_data, dict):
                                        num_value = num_data.get('number', '')
                                        num_digits = ''.join(filter(str.isdigit, num_value))
                                        if len(num_digits) >= 9 and num_digits[-9:] == last_digits:
                                            return num_data
                        # Return all numbers if no specific target
                        return numbers
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON response - {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error: Network request failed - {e}")
            return None
        except Exception as e:
            print(f"Error checking OTP: {e}")
            return None

def main():
    tool = OTPTool()
    
    print("=" * 70)
    print("OTP NUMBER TOOL - WhatsApp/Facebook/Telegram")
    print("=" * 70)
    print("\nLogging in...")
    
    if not tool.login():
        print("Login failed!")
        return
    
    print("Login successful!\n")
    
    app_map = {
        "1": "verifyed-access-whatsapp",
        "2": "verifyed-access-facebook", 
        "3": "verifyed-access-telegram"
    }
    
    app_names = {
        "verifyed-access-whatsapp": "WhatsApp",
        "verifyed-access-facebook": "Facebook",
        "verifyed-access-telegram": "Telegram"
    }
    
    while True:
        print("\n" + "=" * 70)
        print("MAIN MENU")
        print("=" * 70)
        print("1. WhatsApp Ranges")
        print("2. Facebook Ranges")
        print("3. Telegram Ranges")
        print("4. Check OTP (Current Number)")
        print("5. Exit")
        print("-" * 70)
        
        choice = input("Select option (1-5): ").strip()
        
        if choice == "5":
            print("\nExiting...")
            break
        
        if choice in ["1", "2", "3"]:
            app_id = app_map[choice]
            app_name = app_names[app_id]
            
            print(f"\nLoading {app_name} ranges...")
            ranges = tool.get_ranges(app_id)
            
            if not ranges:
                print(f"No active ranges found for {app_name}")
                continue
            
            print(f"\n{app_name} Active Ranges:")
            print("-" * 70)
            for i, r in enumerate(ranges, 1):
                range_name = r.get('name', r.get('id', 'Unknown'))
                print(f"{i}. {range_name}")
            
            print(f"\n{len(ranges)+1}. Back to Main Menu")
            print("-" * 70)
            
            range_choice = input(f"Select range (1-{len(ranges)}) or range name: ").strip()
            
            try:
                range_idx = int(range_choice) - 1
                if 0 <= range_idx < len(ranges):
                    selected_range = ranges[range_idx]
                else:
                    # Try to find by name
                    selected_range = None
                    for r in ranges:
                        if range_choice.lower() in r.get('name', '').lower() or range_choice.lower() in r.get('id', '').lower():
                            selected_range = r
                            break
                    if not selected_range:
                        print("Invalid selection")
                        continue
            except ValueError:
                # User entered range name
                selected_range = None
                for r in ranges:
                    if range_choice.lower() in r.get('name', '').lower() or range_choice.lower() in r.get('id', '').lower():
                        selected_range = r
                        break
                if not selected_range:
                    print(f"Range '{range_choice}' not found")
                    continue
            
            range_name = selected_range.get('name', '')
            range_id = selected_range.get('id', '')
            
            # Keep requesting numbers until user stops
            while True:
                print(f"\nRequesting number from range: {range_name}...")
                number_data = tool.get_number(range_name)
                if not number_data:
                    number_data = tool.get_number(range_id)
                
                if not number_data:
                    print("Failed to get number. Range might be unavailable.")
                    break
                number = number_data.get('number', 'N/A')
                print(f"\n[SUCCESS] Number received!")
                print(f"Number: {number}")
                print(f"Country: {number_data.get('country', 'N/A')}")
                print(f"Status: {number_data.get('status', 'N/A')}")
                
                if number_data.get('nuid'):
                    print(f"Number ID: {number_data.get('nuid')}")
                
                # Auto-monitor OTP by default (no prompt needed)
                print("\nAuto-monitoring for OTP... (Press Ctrl+C to stop)")
                start_time = time.time()
                timeout = 300
                check_interval = 2  # Check every 2 seconds for faster OTP detection
                
                try:
                    while True:
                        time.sleep(check_interval)
                        otp_data = tool.check_otp(number)
                        
                        # Always check OTP, even if None is returned
                        if otp_data is None:
                            elapsed = int(time.time() - start_time)
                            print(f"\rWaiting... ({elapsed}s) | No data yet", end="", flush=True)
                        elif isinstance(otp_data, list):
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
                                # Number not found in list yet, show waiting
                                elapsed = int(time.time() - start_time)
                                print(f"\rWaiting... ({elapsed}s) | Number not found in list yet", end="", flush=True)
                                continue
                        
                        if isinstance(otp_data, dict):
                            # Get OTP - directly from 'otp' field
                            otp_raw = otp_data.get('otp')
                            sms_content = otp_data.get('sms_content', '')
                            status = otp_data.get('status', '')
                            
                            # Convert OTP to string
                            if otp_raw is not None and otp_raw != '':
                                otp = str(otp_raw).strip()
                            elif sms_content and ('কোড' in sms_content or 'code' in sms_content.lower()):
                                # Extract OTP from SMS content
                                otp_match = re.search(r'(\d{3,6}-?\d{3,6})', sms_content)
                                if otp_match:
                                    otp = otp_match.group(1).replace('-', '').strip()
                                else:
                                    otp = ''
                            else:
                                otp = ''
                            
                            # Check if OTP has been received
                            if otp and len(otp) > 0:
                                print(f"\n\n{'='*70}")
                                print(f"[✓ OTP RECEIVED]")
                                print(f"{'='*70}")
                                print(f"Number: {otp_data.get('number', number)}")
                                print(f"OTP: {otp}")
                                print(f"Status: {status}")
                                if sms_content:
                                    print(f"SMS Content: {sms_content}")
                                print(f"{'='*70}\n")
                                
                                # Auto request next number - ask user
                                next_number = input("\nRequest next number from same range? (y/n): ").strip().lower()
                                if next_number == 'y':
                                    break  # Exit monitoring loop, continue while loop to get next number
                                else:
                                    return  # Exit completely
                            
                            # Show status while waiting
                            elapsed = int(time.time() - start_time)
                            if status:
                                status_msg = f"Status: {status}"
                                if otp and len(otp) > 0:
                                    status_msg += f" | OTP: {otp}"
                                print(f"\rWaiting... ({elapsed}s) | {status_msg}", end="", flush=True)
                            else:
                                print(f"\rWaiting... ({elapsed}s) | Checking for OTP...", end="", flush=True)
                        
                        if time.time() - start_time > timeout:
                            print(f"\n\nTimeout! No OTP received within 5 minutes.")
                            next_after_timeout = input("\nRequest next number? (y/n): ").strip().lower()
                            if next_after_timeout == 'y':
                                break  # Continue to next number
                            else:
                                return  # Exit
                except KeyboardInterrupt:
                    print("\n\nMonitoring stopped.")
                    next_after_stop = input("\nRequest next number? (y/n): ").strip().lower()
                    if next_after_stop == 'y':
                        break  # Continue to next number
                    else:
                        return  # Exit
                except Exception as e:
                    print(f"\nError during monitoring: {e}")
                    return
            else:
                print("Failed to get number. Range might be unavailable.")
        
        elif choice == "4":
            if not tool.selected_number:
                print("\nNo number selected. Please get a number first.")
                check_any = input("Check all recent numbers? (y/n): ").strip().lower()
                if check_any == 'y':
                    otp_data = tool.check_otp()
                    if otp_data:
                        if isinstance(otp_data, list):
                            print(f"\nFound {len(otp_data)} recent numbers:")
                            print("-" * 70)
                            for num_data in otp_data[:10]:
                                if isinstance(num_data, dict):
                                    # Get OTP from various possible fields
                                    otp = num_data.get('otp', '') or num_data.get('code', '') or num_data.get('verification_code', '')
                                    if otp:
                                        otp = str(otp).strip()
                                    print(f"\nNumber: {num_data.get('number')}")
                                    print(f"OTP: {otp if otp else 'Not received yet'}")
                                    print(f"Status: {num_data.get('status', 'N/A')}")
                                    if otp:
                                        print(f"SMS: {num_data.get('sms_content', 'N/A')}")
            else:
                print(f"\nChecking OTP for: {tool.selected_number}...")
                otp_data = tool.check_otp()
                
                if otp_data:
                    if isinstance(otp_data, list):
                        for num in otp_data:
                            if num.get('number') == tool.selected_number:
                                otp_data = num
                                break
                    
                    if isinstance(otp_data, dict):
                        # Get OTP from various possible fields
                        otp = otp_data.get('otp', '') or otp_data.get('code', '') or otp_data.get('verification_code', '')
                        if otp:
                            otp = str(otp).strip()
                        print(f"\nNumber: {otp_data.get('number')}")
                        print(f"OTP: {otp if otp else 'Not received yet'}")
                        print(f"Status: {otp_data.get('status', 'N/A')}")
                        print(f"Last Activity: {otp_data.get('last_activity', 'N/A')}")
                        if otp:
                            print(f"SMS Content: {otp_data.get('sms_content', 'N/A')}")
                    else:
                        print("No data found")
                else:
                    print("Failed to check OTP")
        
        else:
            print("Invalid option!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")
