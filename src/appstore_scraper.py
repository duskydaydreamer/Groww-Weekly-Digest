import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from app_store_web_scraper import AppStoreEntry, AppStoreSession
except ImportError:
    AppStoreEntry = None
    AppStoreSession = None

def scrape_appstore_reviews(app_id: str, app_name: str, country: str = "us", count: int = 1000) -> pd.DataFrame:
    """
    Scrapes reviews from the Apple App Store using the modern app-store-web-scraper library
    and returns them as a pandas DataFrame.
    """
    if not AppStoreEntry:
        logger.error("app-store-web-scraper is not installed. Please install it using pip.")
        return pd.DataFrame()

    logger.info(f"Downloading App Store reviews for {app_name} (ID: {app_id}) in {country} via Web Scraper")
    
    try:
        session = AppStoreSession()
        app = AppStoreEntry(app_id=int(app_id), country=country, session=session)
        
        unified = []
        # The library uses a generator that yields reviews
        for i, review in enumerate(app.reviews()):
            if i >= count:
                break
                
            review_date = getattr(review, "date", None)
            if isinstance(review_date, datetime):
                date_str = review_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = str(review_date) if review_date else ""

            unified.append({
                "Date": date_str,
                "Rating": getattr(review, "rating", 0),
                "Text": getattr(review, "content", ""),
                "userName": getattr(review, "user_name", ""),
                "reviewId": getattr(review, "id", ""),
                "title": getattr(review, "title", ""),
                "version": getattr(review, "app_version", "")
            })
            
        df = pd.DataFrame(unified)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'])
            logger.info(f"Successfully fetched {len(df)} App Store reviews.")
        else:
            logger.warning("No reviews fetched from App Store.")
            
        return df

    except Exception as e:
        logger.error(f"Error scraping App Store reviews: {e}")
        return pd.DataFrame()
