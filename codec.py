import subprocess
import os
import sys
import json
import logging

logger = logging.getLogger(__name__)

NODE_PATH = "node"

def _run_node_codec(action, key, data):
    dir_path = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(dir_path, "codec.js")
    
    try:
        is_windows = os.name == 'nt'
        
        # Check for local node binary (useful for Render deployment)
        local_node = os.path.join(dir_path, "bin", "node")
        node_exec = NODE_PATH
        if not is_windows and os.path.exists(local_node):
            node_exec = local_node
            
        process = subprocess.Popen(
            [node_exec, script_path, action, key],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            cwd=dir_path
        )
        stdout, stderr = process.communicate(input=data)
        
        if process.returncode != 0:
            raise RuntimeError(f"Node codec failed: {stderr.strip()}")
            
        return stdout
    except FileNotFoundError:
        raise RuntimeError("Node.js executable not found. Please make sure Node.js is installed and in your PATH.")
    except Exception as e:
        raise RuntimeError(f"Codec execution error: {e}")

def encrypt(payload_dict_or_str, key):
    if isinstance(payload_dict_or_str, dict):
        data = json.dumps(payload_dict_or_str)
    else:
        data = str(payload_dict_or_str)
    return _run_node_codec("encode", key, data)

def decrypt(ciphertext, key):
    decrypted_str = _run_node_codec("decode", key, ciphertext)
    try:
        return json.loads(decrypted_str)
    except json.JSONDecodeError:
        return decrypted_str
