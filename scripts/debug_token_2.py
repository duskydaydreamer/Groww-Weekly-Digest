import urllib.request
import re
import ssl

url = "https://apps.apple.com/in/app/groww-stocks-mutual-fund-ipo/id1404877701"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    response = urllib.request.urlopen(req, context=ctx)
    html = response.read().decode('utf-8')
    
    # Try to find anything looking like a bearer token
    print("Searching for token in HTML...")
    tokens = set(re.findall(r'bearer%20([a-zA-Z0-9\-\._~]+)', html))
    if not tokens:
        tokens = set(re.findall(r'token[^>]+([a-zA-Z0-9\-\._~]{30,})', html))
        
    print(f"Found {len(tokens)} potential tokens:")
    for t in list(tokens)[:5]:
        print(t[:20] + "...")
        
    if "web-experience-app" in html:
        print("web-experience-app IS in HTML")
    else:
        print("web-experience-app IS NOT in HTML")
        
except Exception as e:
    print("Error:", e)
