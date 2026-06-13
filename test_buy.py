import sys
import os
import traceback

out_path = r"C:\Users\Roni\Downloads\otpno1-main (2)\otpno1\py_out.txt"

try:
    import telegram_bot
    
    bot = telegram_bot.APIClient()
    
    out = []
    out.append("Testing login...")
    bot.login()
    out.append(f"Token: {str(bot.auth_token)[:20]}...")
    
    ranges_to_test = [
        "22366XXX",
        "22366",
        "b_9",
        "22366611160",
        "22366611160XXX",
        "2290145XXX",
        "2290145"
    ]
    
    for r in ranges_to_test:
        out.append(f"\n--- Testing range: {r} ---")
        try:
            res = bot.get_number(r)
            if res:
                out.append(f"SUCCESS: {res}")
            else:
                out.append(f"FAILED for {r}")
        except Exception as inner_e:
            out.append(f"EXCEPTION for {r}: {str(inner_e)}")
            
    with open(out_path, "w", encoding="utf-8") as f:
        f.write('\n'.join(out))
        
except Exception as e:
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("FATAL ERROR:\n" + traceback.format_exc())
