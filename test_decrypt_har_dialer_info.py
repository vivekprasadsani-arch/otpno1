import json
import os
import codec

har_path = "C:/Users/Roni/Downloads/otpno1-main (2)/test.har"
if not os.path.exists(har_path):
    print("HAR file not found!")
    exit(1)

with open(har_path, "r", encoding="utf-8") as f:
    har = json.load(f)

key = "M0E89NUFVTO"
found = False

for entry in har['log']['entries']:
    url = entry['request']['url']
    if '@dashboard/dialer/info' in url:
        found = True
        status = entry['response']['status']
        text = entry['response']['content'].get('text', '')
        print(f"URL: {url}")
        print(f"Response Status: {status}")
        if text:
            try:
                decrypted = codec.decrypt(text.strip(), key)
                print("Decrypted Info:")
                print(json.dumps(decrypted, indent=2))
            except Exception as e:
                print(f"Decryption failed: {e}")
        else:
            print("Response text is empty")
        print("-" * 50)

if not found:
    print("@dashboard/dialer/info request not found in HAR file.")
