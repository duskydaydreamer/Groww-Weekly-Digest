import urllib.request
import json
import ssl

url = "https://itunes.apple.com/in/rss/customerreviews/page=1/id=1404877799/sortby=mostrecent/json"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    response = urllib.request.urlopen(req, context=ctx)
    raw = response.read().decode('utf-8')
    data = json.loads(raw)
    print("KEYS in data:", list(data.keys()))
    if 'feed' in data:
        print("KEYS in feed:", list(data['feed'].keys()))
        if 'entry' in data['feed']:
            entries = data['feed']['entry']
            print(f"Number of entries: {len(entries)}")
            if len(entries) > 0:
                print("First entry keys:", list(entries[0].keys()))
        else:
            print("No 'entry' key in 'feed'.")
    else:
        print("No 'feed' key in data.")
except Exception as e:
    print("Error:", e)
