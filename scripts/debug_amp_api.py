import urllib.request
import re
import ssl
import json

url = "https://apps.apple.com/in/app/groww/id1404855737"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    print(f"Fetching {url}")
    response = urllib.request.urlopen(req, context=ctx)
    html = response.read().decode('utf-8')
    
    print("Page fetched successfully. Searching for Bearer token...")
    
    # Apple's new token format is usually in a meta tag or javascript variable
    token_match = re.search(r'bearer%20([a-zA-Z0-9\-\._~]+)', html)
    if not token_match:
        token_match = re.search(r'token%22%3A%22([a-zA-Z0-9\-\._~]+)%22', html)
    if not token_match:
        token_match = re.search(r'token":"([a-zA-Z0-9\-\._~]+)"', html)
        
    if token_match:
        token = token_match.group(1)
        print(f"Found Token: {token[:15]}...{token[-5:]}")
        
        # Now try to fetch reviews with the token
        api_url = f"https://amp-api.apps.apple.com/v1/catalog/in/apps/1404855737/reviews?l=en-GB&offset=1&limit=20"
        api_req = urllib.request.Request(api_url, headers={
            'Authorization': f'Bearer {token}',
            'Origin': 'https://apps.apple.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        
        print(f"Requesting reviews from API...")
        api_response = urllib.request.urlopen(api_req, context=ctx)
        api_data = json.loads(api_response.read().decode('utf-8'))
        
        reviews = api_data.get('data', [])
        print(f"SUCCESS: Fetched {len(reviews)} reviews directly from Apple API!")
        if len(reviews) > 0:
            print("First review snippet:", reviews[0].get('attributes', {}).get('review'))
            
    else:
        print("Failed to find token in HTML.")
        print("HTML snippet around 'token':")
        for line in html.split('\n'):
            if 'token' in line.lower() or 'bearer' in line.lower():
                print(line[:200])
        
except Exception as e:
    print("Error:", e)
