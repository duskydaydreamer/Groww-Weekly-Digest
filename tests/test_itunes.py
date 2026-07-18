import urllib.request
import json

url = "https://itunes.apple.com/search?term=groww&country=in&entity=software"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
response = urllib.request.urlopen(req)
data = json.loads(response.read().decode('utf-8'))

for r in data['results']:
    print(f"Name: {r['trackName']}")
    print(f"App ID: {r['trackId']}")
    print(f"App Bundle: {r['bundleId']}")
    print("---")
