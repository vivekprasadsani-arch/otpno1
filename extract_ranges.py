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
logs = []

for entry in har['log']['entries']:
    url = entry['request']['url']
    if '@dashboard/dialer/console/info' in url:
        text = entry['response']['content'].get('text', '')
        if text:
            decrypted = codec.decrypt(text.strip(), key)
            if isinstance(decrypted, dict):
                logs.extend(decrypted.get("data", {}).get("logs", []))
            else:
                try:
                    payload = json.loads(decrypted)
                    logs.extend(payload.get("data", {}).get("logs", []))
                except Exception:
                    pass

# Extract unique ranges & map ****** to WhatsApp
uniq = {}
for item in logs:
    rng = item.get('range')
    if not rng:
        continue
    app_name = item.get('app_name', '')
    if app_name == '******':
        app_name = 'WhatsApp'
    
    # Store unique combination of range and app
    uniq[(rng, app_name)] = {
        "range": rng,
        "app_name": app_name,
        "country": item.get("country", "Unknown"),
        "carrier": item.get("carrier", "Unknown"),
        "operator": item.get("operator", "Unknown")
    }

out_list = list(uniq.values())
print(f"Extracted {len(out_list)} unique range-app pairs.")

with open("har_ranges.json", "w", encoding="utf-8") as out:
    json.dump(out_list, out, indent=2)

print("Saved to har_ranges.json successfully!")
