import json

har_path = r"c:\Users\Roni\Downloads\rrrincome24-7-main\rrrincome24-7-main\stexsms.com.har"

with open(har_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

entries = data['log']['entries']
for entry in entries:
    request = entry['request']
    response = entry['response']
    url = request['url']
    method = request['method']
    
    if "login" in url.lower():
        print(f"\n{'='*80}")
        print(f"METHOD: {method}")
        print(f"URL: {url}")
        print(f"\nREQUEST HEADERS:")
        for header in request['headers']:
            print(f"  {header['name']}: {header['value']}")
        
        if method == "POST":
            post_data = request.get('postData', {})
            text = post_data.get('text', '')
            if text:
                print(f"\nREQUEST BODY:")
                try:
                    print(f"  {json.dumps(json.loads(text), indent=2)}")
                except:
                    print(f"  {text}")
        
        print(f"\nRESPONSE STATUS: {response['status']} {response['statusText']}")
        print(f"\nRESPONSE HEADERS:")
        for header in response['headers']:
            print(f"  {header['name']}: {header['value']}")
        
        content = response.get('content', {})
        text = content.get('text', '')
        if text:
            print(f"\nRESPONSE BODY:")
            try:
                print(f"  {json.dumps(json.loads(text), indent=2)}")
            except:
                print(f"  {text[:500]}")
