import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = "https://itunes.apple.com/search?term=groww&country=in&entity=software"

try:
    print(f"Fetching: {url}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, context=ctx)
    data = json.loads(res.read().decode('utf-8'))
    
    results = data.get('results', [])
    print(f"Found {len(results)} results")
    for r in results:
        print(f"Name: {r.get('trackName')}")
        print(f"ID: {r.get('trackId')}")
        print(f"URL: {r.get('trackViewUrl')}")
        print("---")
except Exception as e:
    print("Error:", e)
