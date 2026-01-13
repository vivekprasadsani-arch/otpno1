import requests
import json

# Try with different methods
base_url = "https://stexsms.com"
email = "roni791158@gmail.com"
password = "53561106@Roni"

print("Testing login with different methods...\n")

# Method 1: Standard requests
print("=" * 80)
print("Method 1: Standard requests library")
print("=" * 80)
try:
    session = requests.Session()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
        "Origin": base_url,
        "Referer": f"{base_url}/mauth/login"
    }
    
    resp = session.post(
        f"{base_url}/mapi/v1/mauth/login",
        json={"email": email, "password": password},
        headers=headers,
        timeout=15
    )
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    print(f"Response Body: {resp.text[:500]}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nParsed JSON:")
        print(json.dumps(data, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Method 2: Try with curl_cffi if available
print("\n" + "=" * 80)
print("Method 2: curl_cffi library")
print("=" * 80)
try:
    from curl_cffi import requests as curl_requests
    
    session = curl_requests.Session(impersonate="chrome110")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": base_url,
        "Referer": f"{base_url}/mauth/login"
    }
    
    resp = session.post(
        f"{base_url}/mapi/v1/mauth/login",
        json={"email": email, "password": password},
        headers=headers,
        timeout=15
    )
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    print(f"Response Body: {resp.text[:500]}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nParsed JSON:")
        print(json.dumps(data, indent=2))
except ImportError:
    print("curl_cffi not available")
except Exception as e:
    print(f"Error: {e}")

# Method 3: Try with cloudscraper if available
print("\n" + "=" * 80)
print("Method 3: cloudscraper library")
print("=" * 80)
try:
    import cloudscraper
    
    session = cloudscraper.create_scraper()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
        "Origin": base_url,
        "Referer": f"{base_url}/mauth/login"
    }
    
    resp = session.post(
        f"{base_url}/mapi/v1/mauth/login",
        json={"email": email, "password": password},
        headers=headers,
        timeout=15
    )
    
    print(f"Status Code: {resp.status_code}")
    print(f"Response Headers: {dict(resp.headers)}")
    print(f"Response Body: {resp.text[:500]}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\nParsed JSON:")
        print(json.dumps(data, indent=2))
except ImportError:
    print("cloudscraper not available")
except Exception as e:
    print(f"Error: {e}")
