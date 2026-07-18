import logging
from app_store_web_scraper import AppStoreEntry, AppStoreSession

logging.basicConfig(level=logging.DEBUG)

try:
    session = AppStoreSession()
    app = AppStoreEntry(app_id=1404877799, country="in", session=session)
    
    print("Fetching reviews...")
    count = 0
    for review in app.reviews():
        print(review)
        count += 1
        if count >= 5:
            break
            
    print(f"Total fetched in debug: {count}")
except Exception as e:
    print(f"Exception: {e}")
