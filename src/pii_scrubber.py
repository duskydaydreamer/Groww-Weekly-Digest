import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import re
import json
import logging
from typing import List, Optional
from pathlib import Path
from copy import deepcopy

from src.ingest import Review
from src.config import get_settings

logger = logging.getLogger(__name__)

# Regex patterns for India-specific PII
EMAIL_REGEX = re.compile(r'(?<![\w.-])[\w.+-]+@[\w-]+\.[\w.]+(?![\w.-])')
UPI_REGEX = re.compile(r'(?<![\w.-])[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b')
PHONE_REGEX = re.compile(r'(?<!\d)(?:\+91[- ]?)?[6-9]\d{9}(?!\d)')
PAN_REGEX = re.compile(r'(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z]{1}(?![A-Z0-9])')
AADHAR_REGEX = re.compile(r'(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)')

# For mentions, we exclude UPI formats by doing a negative lookbehind if needed, but since we run UPI first, UPI will be replaced by [UPI_REDACTED]
MENTION_REGEX = re.compile(r'@\w+')
# URL patterns
URL_REGEX = re.compile(r'https?://[^\s]+')
# UUIDs
UUID_REGEX = re.compile(r'(?<![0-9a-fA-F])[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?![0-9a-fA-F])')

def scrub_text(text: Optional[str]) -> Optional[str]:
    """Applies regex patterns sequentially for known India-specific PII types."""
    if not text:
        return text

    scrubbed = text
    
    # 1. UUIDs
    scrubbed = UUID_REGEX.sub('[ID_REDACTED]', scrubbed)
    # 2. URLs
    scrubbed = URL_REGEX.sub('[URL_REDACTED]', scrubbed)
    # 3. Emails
    scrubbed = EMAIL_REGEX.sub('[EMAIL_REDACTED]', scrubbed)
    # 4. UPI IDs
    scrubbed = UPI_REGEX.sub('[UPI_REDACTED]', scrubbed)
    # 5. Phone numbers
    scrubbed = PHONE_REGEX.sub('[PHONE_REDACTED]', scrubbed)
    # 6. PAN Number
    scrubbed = PAN_REGEX.sub('[PAN_REDACTED]', scrubbed)
    # 7. Aadhar Number
    scrubbed = AADHAR_REGEX.sub('[AADHAR_REDACTED]', scrubbed)
    # 8. Mentions
    scrubbed = MENTION_REGEX.sub('[USER_REDACTED]', scrubbed)
    
    return scrubbed

def llm_ner_pass(text: str, settings) -> str:
    """Send flagged text to LLM for Hinglish/Indian context NER."""
    # Simplified version for now, could be expanded.
    if not settings.llm_pii_check or not settings.llm_api_key:
        return text
    
    try:
        from google import genai
        client = genai.Client(api_key=settings.llm_api_key)
        
        prompt = (
            "You are a PII Redaction expert that understands Hinglish and Roman Hindi.\n"
            "Redact any Indian personal names, physical addresses, or any other PII from the following text.\n"
            "Replace names with [NAME_REDACTED] and addresses with [ADDRESS_REDACTED].\n"
            "Output ONLY the redacted text, with no other comments.\n\n"
            f"Original text: {text}"
        )
        response = client.models.generate_content(
            model=settings.llm_model,
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip()
    except Exception as e:
        logger.warning(f"LLM NER pass failed: {e}")
        
    return text

def scrub_reviews(reviews: List[Review]) -> List[Review]:
    """Apply scrub_text() to both title and text fields of each review."""
    settings = get_settings()
    scrubbed_reviews = []
    
    redactions_count = 0
    
    for review in reviews:
        # Pydantic copy
        safe_review = review.model_copy()
        
        orig_title = safe_review.title
        if safe_review.title:
            safe_review.title = scrub_text(safe_review.title)
            if settings.llm_pii_check and safe_review.title != orig_title:
                pass # Can do LLM pass here if needed
            
            if safe_review.title != orig_title:
                redactions_count += 1
                
        orig_text = safe_review.text
        if safe_review.text:
            safe_review.text = scrub_text(safe_review.text)
            
            # If LLM check is enabled, run the LLM pass on the text
            if settings.llm_pii_check:
                safe_review.text = llm_ner_pass(safe_review.text, settings)
                
            if safe_review.text != orig_text:
                redactions_count += 1
                
        scrubbed_reviews.append(safe_review)
        
    logger.info(f"Performed PII redactions on {redactions_count} review fields.")
    return scrubbed_reviews

def main():
    from src.config import PROCESSED_DATA_DIR
    input_path = PROCESSED_DATA_DIR / 'normalized_reviews.json'
    
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return
        
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        reviews = [Review(**r) for r in data]
        
    logger.info(f"Loaded {len(reviews)} reviews for PII scrubbing.")
    
    scrubbed_reviews = scrub_reviews(reviews)
    
    output_data = [r.model_dump(mode='json') for r in scrubbed_reviews]
    with open(input_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4)
        
    logger.info("Successfully scrubbed PII and saved back to JSON.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
