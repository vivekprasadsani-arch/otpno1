import sys
import os

sys.path.append(r'C:\Users\Roni\Downloads\otpno1-main (2)\otpno1')
import codec

key = "1234567812345678"
payloads = [
    {"range": "22898XXX"},
    {"range": "25565XXX"},
    {"range": "22366XXX"},
    {"range_id": "12345678901234567890"},
    {"range_id": "r_12345"}
]

for p in payloads:
    enc = codec.encrypt(p, key)
    print(f"Payload: {p} -> Length: {len(enc)}")
