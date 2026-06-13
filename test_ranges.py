import sys
import os
import traceback
import json
import codec

out_path = r"C:\Users\Roni\Downloads\otpno1-main (2)\otpno1\py_out.txt"

try:
    import telegram_bot
    bot = telegram_bot.APIClient()
    
    out = []
    out.append("Testing login...")
    bot.login()
    out.append(f"Token: {str(bot.auth_token)[:20]}...")
    
    def fetch_api(path):
        out.append(f"\n--- Fetching {path} ---")
        try:
            resp = bot.session.get(bot.base_api_url + path)
            out.append(f"Status: {resp.status_code}")
            try:
                decrypted = codec.decrypt(resp.text.strip(), "M0000000001")
                if isinstance(decrypted, dict):
                    out.append("Decrypted JSON:")
                    out.append(json.dumps(decrypted, indent=2)[:2000])
                else:
                    out.append(f"Decrypted text: {str(decrypted)[:500]}")
            except Exception as e:
                out.append(f"Decryption error: {e}")
                out.append(f"Raw body: {resp.text[:500]}")
        except Exception as e:
            out.append(f"Request error: {e}")

    fetch_api("/@dashboard/dialer/getnum/ranges?country=Togo&limit=10")
    fetch_api("/@dashboard/dialer/getnum/range-sids?prefix=22898")
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(out))
        
except Exception as e:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("FATAL ERROR:\n" + traceback.format_exc())
