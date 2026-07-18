from google_play_scraper import reviews, Sort
from datetime import datetime, timedelta

def test_fetch_12_weeks():
    package_name = 'com.nextbillion.groww'
    target_date = datetime.now() - timedelta(weeks=12)
    
    all_reviews = []
    continuation_token = None
    
    print(f"Fetching reviews until {target_date.date()}...")
    
    while True:
        try:
            res, continuation_token = reviews(
                package_name,
                lang='en',
                country='in',
                sort=Sort.NEWEST,
                count=500,
                continuation_token=continuation_token
            )
        except Exception as e:
            print(f"Error: {e}")
            break
            
        if not res:
            print("No more reviews.")
            break
            
        all_reviews.extend(res)
        
        oldest_in_batch = res[-1]['at']
        print(f"Fetched batch. Current count: {len(all_reviews)}. Oldest in batch: {oldest_in_batch}")
        
        if oldest_in_batch < target_date:
            print("Reached target date!")
            break
            
        if not continuation_token:
            print("No continuation token.")
            break
            
        # Hard limit just in case
        if len(all_reviews) > 15000:
            print("Reached 15000 limit.")
            break
            
    print(f"Total fetched: {len(all_reviews)}")

if __name__ == '__main__':
    test_fetch_12_weeks()
