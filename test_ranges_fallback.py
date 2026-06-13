from telegram_bot import APIClient
import logging

logging.basicConfig(level=logging.INFO)
client = APIClient()

print("Login status:", client.login())

# Test get_ranges for WhatsApp
print("\n--- Fetching WhatsApp ranges ---")
ranges = client.get_ranges("whatsapp")
print(f"Total WhatsApp ranges found: {len(ranges)}")
if ranges:
    print("First 3 WhatsApp ranges:")
    for r in ranges[:3]:
        print(r)
else:
    print("WARNING: No WhatsApp ranges found!")
