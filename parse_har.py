import json

har_path = r"c:\Users\Roni\Downloads\rrrincome24-7-main\rrrincome24-7-main\stexsms.com.har"

with open(har_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['log']['entries']
for entry in entries:
    request = entry['request']
    url = request['url']
    method = request['method']
    if "mapi/v1" in url:
        print(f"{method} {url}")
        if method == "POST":
            post_data = request.get('postData', {})
            params = post_data.get('params', [])
            text = post_data.get('text', '')
            if params:
                print(f"  Params: {params}")
            if text:
                print(f"  Text: {text}")
