import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
from pathlib import Path
from textblob import TextBlob
from typing import List

from src.ingest import Review, EnrichedReview
from src.pii_scrubber import scrub_text

logger = logging.getLogger(__name__)

# Feature taxonomy mapping
FEATURE_TAXONOMY = {
    "Trading & Brokerage": ["brokerage", "charge", "stt", "gst", "dp", "margin", "intraday", "delivery", "f&o", "options", "buy", "sell", "order"],
    "Mutual Funds & SIP": ["mutual fund", "mf", "sip", "dividend", "idcw", "reinvestment", "payout", "nav"],
    "App Performance": ["glitch", "refreshing", "hang", "crash", "slow", "stuck", "loading", "bug", "update", "ui"],
    "Customer Support": ["customer care", "support", "call", "email", "reply", "response", "worst service"],
    "Onboarding & KYC": ["kyc", "pan", "aadhar", "account", "login", "password", "pin", "fingerprint"]
}

# Actionable keywords
ACTION_KEYWORDS = ["fix", "failed", "error", "charge", "add", "update", "issue", "problem", "solve", "refund", "not working", "worst", "terrible", "improve"]

def analyze_sentiment(text: str) -> tuple[float, str]:
    """Analyze sentiment and return score (-1.0 to 1.0) and label."""
    if not text:
        return 0.0, "Neutral"
        
    blob = TextBlob(text)
    score = blob.sentiment.polarity
    
    if score > 0.1:
        label = "Positive"
    elif score < -0.1:
        label = "Negative"
    else:
        label = "Neutral"
        
    return score, label

def extract_features(text: str) -> List[str]:
    """Map text to product features based on taxonomy."""
    if not text:
        return []
        
    text_lower = text.lower()
    found_features = set()
    
    for feature_name, keywords in FEATURE_TAXONOMY.items():
        for kw in keywords:
            if kw in text_lower:
                found_features.add(feature_name)
                break
                
    return list(found_features)

def check_actionability(text: str) -> bool:
    """Flag review if it contains actionable keywords."""
    if not text:
        return False
        
    text_lower = text.lower()
    return any(kw in text_lower for kw in ACTION_KEYWORDS)

def enrich_review(review: Review) -> EnrichedReview:
    """Apply PII scrubbing and data enrichment to a Review."""
    # 1. PII Scrubbing
    scrubbed_title = scrub_text(review.title) if review.title else None
    scrubbed_text = scrub_text(review.text)
    
    # 2. Enrichment
    score, label = analyze_sentiment(scrubbed_text)
    features = extract_features(scrubbed_text)
    actionable = check_actionability(scrubbed_text)
    
    return EnrichedReview(
        id=review.id,
        source=review.source,
        rating=review.rating,
        title=scrubbed_title,
        text=scrubbed_text,
        date=review.date,
        word_count=review.word_count,
        sentiment_score=score,
        sentiment_label=label,
        feature_tags=features,
        is_actionable=actionable
    )

def analyze_all_reviews() -> int:
    from src.config import PROCESSED_DATA_DIR
    
    input_path = PROCESSED_DATA_DIR / "normalized_reviews.json"
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 0
        
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        reviews = [Review(**r) for r in data]
        
    logger.info(f"Loaded {len(reviews)} normalized reviews for enrichment.")
    
    enriched_reviews = []
    for r in reviews:
        try:
            enriched_reviews.append(enrich_review(r))
        except Exception as e:
            logger.warning(f"Failed to enrich review {r.id}: {e}")
            
    out_path = PROCESSED_DATA_DIR / "enriched_reviews.json"
    
    # Save enriched reviews
    output_data = [r.model_dump(mode='json') for r in enriched_reviews]
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
        
    logger.info(f"Successfully enriched {len(enriched_reviews)} reviews and saved to {out_path}")
    return len(enriched_reviews)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    analyze_all_reviews()
