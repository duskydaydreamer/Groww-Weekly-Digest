import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from pathlib import Path
import pandas as pd
import emoji
from langdetect import detect, LangDetectException
from src.config import get_settings, RAW_DATA_DIR
from src.appstore_scraper import scrape_appstore_reviews

def filter_reviews(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or 'Text' not in df.columns:
        return df
        
    initial_count = len(df)
    
    # Ensure Text is string and not null
    df = df[df['Text'].notna()]
    df = df[df['Text'].astype(str).str.strip() != ""]
    
    # 1. Less than 8 words are not required
    df = df[df['Text'].apply(lambda x: len(str(x).split()) >= 8)]
    
    # 2. Reviews which have emoji are not required
    def has_emoji(text):
        return emoji.emoji_count(str(text)) > 0
    df = df[~df['Text'].apply(has_emoji)]
    
    # 3. Reviews in hindi language are not required
    def is_hindi(text):
        try:
            return detect(str(text)) == 'hi'
        except LangDetectException:
            return False
    df = df[~df['Text'].apply(is_hindi)]
    
    logger.info(f"Filtering applied: kept {len(df)} out of {initial_count} reviews")
    return df

try:
    from google_play_scraper import reviews, Sort
except ImportError:
    reviews = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def download_play_store_reviews(package_name: str, country: str = "us", weeks: int = 12) -> pd.DataFrame:
    if not reviews:
        logger.error("google-play-scraper is not installed. Please install it to use this function.")
        return pd.DataFrame()

    logger.info(f"Downloading Play Store reviews for {package_name} in {country} (last {weeks} weeks)")
    
    from datetime import datetime, timedelta
    target_date = datetime.now() - timedelta(weeks=weeks)
    
    all_results = []
    continuation_token = None
    
    try:
        while True:
            result, continuation_token = reviews(
                package_name,
                lang='en',
                country=country,
                sort=Sort.NEWEST,
                count=500,
                continuation_token=continuation_token
            )
            
            if not result:
                break
                
            all_results.extend(result)
            oldest_in_batch = result[-1]['at']
            
            logger.info(f"Fetched {len(all_results)} reviews so far. Oldest date: {oldest_in_batch.date()}")
            
            if oldest_in_batch < target_date:
                break
                
            if not continuation_token:
                break
                
            if len(all_results) > 15000:
                logger.warning("Reached maximum 15,000 reviews limit to prevent infinite loops.")
                break
                
        if not all_results:
            logger.warning("No reviews found for Play Store.")
            return pd.DataFrame()
            
        df = pd.DataFrame(all_results)
        
        # Map to expected columns by ingest.py
        df = df.rename(columns={
            'at': 'Date',
            'score': 'Rating',
            'content': 'Text'
        })
        
        # Filter strictly by target date
        df['Date'] = pd.to_datetime(df['Date'])
        df = df[df['Date'] >= target_date]
        
        # Keep relevant columns if they exist
        cols = ['Date', 'Rating', 'Text']
        if 'userName' in df.columns: cols.append('userName')
        if 'reviewId' in df.columns: cols.append('reviewId')
            
        return df[cols]
    except Exception as e:
        logger.error(f"Error downloading Play Store reviews: {e}")
        return pd.DataFrame()

def main():
    settings = get_settings()
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    if settings.target_play_store_package:
        df_play = download_play_store_reviews(
            package_name=settings.target_play_store_package,
            country=settings.app_country,
            weeks=settings.review_window_weeks
        )
        if not df_play.empty:
            df_play = filter_reviews(df_play)
            if not df_play.empty:
                out_path = RAW_DATA_DIR / "play_store_reviews.csv"
                df_play.to_csv(out_path, index=False)
                logger.info(f"Saved {len(df_play)} Play Store reviews to {out_path}")
            else:
                logger.warning("No Play Store reviews left after filtering.")
            
    if settings.target_app_store_id and settings.target_app_store_name:
        df_appstore = scrape_appstore_reviews(
            app_id=settings.target_app_store_id,
            app_name=settings.target_app_store_name,
            country=settings.app_country,
            count=1000  # Default count, can be adjusted
        )
        
        if not df_appstore.empty:
            # Filter strictly by target date like Play Store
            from datetime import datetime, timedelta
            target_date = datetime.now() - timedelta(weeks=settings.review_window_weeks)
            df_appstore = df_appstore[df_appstore['Date'] >= target_date]
            
            df_appstore = filter_reviews(df_appstore)
            if not df_appstore.empty:
                out_path = RAW_DATA_DIR / "app_store_reviews.csv"
                df_appstore.to_csv(out_path, index=False)
                logger.info(f"Saved {len(df_appstore)} App Store reviews to {out_path}")
            else:
                logger.info("No App Store reviews found within the target window.")

if __name__ == "__main__":
    main()
