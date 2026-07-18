from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import hashlib
import json
import logging
from datetime import date
from typing import Literal, Optional
from pathlib import Path
import pandas as pd
from pydantic import BaseModel
import emoji
from langdetect import detect, LangDetectException

logger = logging.getLogger(__name__)

class Review(BaseModel):
    id: str
    source: Literal["play_store", "app_store"]
    rating: int
    title: Optional[str]
    text: str
    date: date
    word_count: int

class EnrichedReview(Review):
    sentiment_score: float
    sentiment_label: Literal["Positive", "Neutral", "Negative"]
    feature_tags: list[str]
    is_actionable: bool

def generate_hash(source: str, text: str, review_date: date) -> str:
    """Generate a deterministic hash for deduplication."""
    content = f"{source}:{text}:{review_date.isoformat()}".encode('utf-8')
    return hashlib.sha256(content).hexdigest()[:16]

def load_play_store_reviews(filepath: Path | str) -> list[Review]:
    """Parse Google Play Store reviews CSV."""
    df = pd.read_csv(filepath)
    reviews = []
    
    date_col = 'Review Submit Date and Time' if 'Review Submit Date and Time' in df.columns else 'Date'
    rating_col = 'Star Rating' if 'Star Rating' in df.columns else 'Rating'
    text_col = 'Review Text' if 'Review Text' in df.columns else 'Text'
    
    for _, row in df.iterrows():
        try:
            text = str(row.get(text_col, '')).strip()
            if not text or text == 'nan':
                continue
                
            review_date = pd.to_datetime(row[date_col]).date()
            rating = int(row.get(rating_col, 0))
            
            if not (1 <= rating <= 5):
                continue
                
            rev = Review(
                id=generate_hash("play_store", text, review_date),
                source="play_store",
                rating=rating,
                title=None,
                text=text,
                date=review_date,
                word_count=len(text.split())
            )
            reviews.append(rev)
        except Exception as e:
            logger.warning(f"Failed to parse Play Store row: {e}")
            
    return reviews

def load_app_store_reviews(filepath: Path | str) -> list[Review]:
    """Parse Apple App Store reviews CSV."""
    df = pd.read_csv(filepath)
    reviews = []
    
    date_col = 'Date'
    rating_col = 'Rating'
    text_col = 'Text'
    title_col = 'title'
    
    for _, row in df.iterrows():
        try:
            text = str(row.get(text_col, '')).strip()
            if not text or text == 'nan':
                continue
                
            review_date = pd.to_datetime(row[date_col]).date()
            rating = int(row.get(rating_col, 0))
            title = str(row.get(title_col, '')).strip()
            
            if not (1 <= rating <= 5):
                continue
                
            rev = Review(
                id=generate_hash("app_store", text, review_date),
                source="app_store",
                rating=rating,
                title=title if title and title != 'nan' else None,
                text=text,
                date=review_date,
                word_count=len(text.split())
            )
            reviews.append(rev)
        except Exception as e:
            logger.warning(f"Failed to parse App Store row: {e}")
            
    return reviews

def normalize_reviews(reviews: list[Review]) -> list[Review]:
    """Filter, deduplicate and sort reviews."""
    valid_reviews = []
    
    # Apply filtering rules
    for r in reviews:
        # Rule 1: Less than 8 words are not required
        if r.word_count < 8:
            continue
            
        # Rule 2: Reviews which have emoji are not required
        if emoji.emoji_count(r.text) > 0:
            continue
            
        # Rule 3: Reviews in Hindi language are not required
        try:
            if detect(r.text) == 'hi':
                continue
        except LangDetectException:
            # If langdetect fails (e.g., text is just numbers/symbols), we might skip or keep. We keep.
            pass
            
        valid_reviews.append(r)
        
    unique_reviews = {}
    for r in valid_reviews:
        # Keep the newest/first encountered if there's a hash collision
        if r.id not in unique_reviews:
            unique_reviews[r.id] = r
            
    # Sort descending by date
    sorted_reviews = sorted(unique_reviews.values(), key=lambda x: x.date, reverse=True)
    return sorted_reviews

def save_normalized(reviews: list[Review], output_path: Path | str) -> None:
    """Save normalized reviews to a JSON file."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = [r.model_dump(mode='json') for r in reviews]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def ingest_reviews() -> int:
    from src.config import RAW_DATA_DIR, PROCESSED_DATA_DIR
    
    all_reviews = []
        
    play_store_csv = RAW_DATA_DIR / "play_store_reviews.csv"
    if play_store_csv.exists():
        logger.info("Loading Play Store reviews...")
        play_reviews = load_play_store_reviews(play_store_csv)
        all_reviews.extend(play_reviews)
        
    app_store_csv = RAW_DATA_DIR / "app_store_reviews.csv"
    if app_store_csv.exists():
        logger.info("Loading App Store reviews...")
        app_reviews = load_app_store_reviews(app_store_csv)
        all_reviews.extend(app_reviews)
        
    if not all_reviews:
        logger.error("No reviews found to process!")
        return 0
        
    logger.info(f"Loaded {len(all_reviews)} total raw reviews.")
    normalized = normalize_reviews(all_reviews)
    
    out_path = PROCESSED_DATA_DIR / "normalized_reviews.json"
    save_normalized(normalized, out_path)
    logger.info(f"Saved {len(normalized)} normalized and filtered reviews to {out_path}")
    return len(normalized)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    ingest_reviews()
