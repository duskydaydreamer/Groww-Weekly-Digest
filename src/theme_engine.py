import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel
from src.config import get_settings, TEMPLATES_DIR, THEME_HISTORY_DIR
from src.ingest import EnrichedReview
from src.llm_client import LLMClient

logger = logging.getLogger(__name__)

class Theme(BaseModel):
    name: str
    description: str

class ThemeDiscoveryResult(BaseModel):
    themes: List[Theme]

class ThemeAssignment(BaseModel):
    review_id: str
    theme_name: str

class ThemeAssignmentResult(BaseModel):
    assignments: List[ThemeAssignment]

class QuoteSelectionResult(BaseModel):
    quotes: List[str]

class ThemeSummary(BaseModel):
    name: str
    summary: str
    review_count: int
    avg_rating: float
    avg_sentiment: float
    actionable_count: int
    representative_quotes: List[str]

class ThemeMap:
    def __init__(self, mapping: Dict[str, List[str]]):
        # mapping of theme_name to list of review_ids
        self.mapping = mapping

def load_prompt(filename: str) -> str:
    path = TEMPLATES_DIR / "prompts" / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def discover_themes(reviews: List[EnrichedReview], max_themes: int = 5) -> List[Theme]:
    logger.info(f"Discovering themes from {len(reviews)} reviews...")
    # Sample up to 20 reviews to safely stay under the strict 1K TPM limit
    sample_size = min(len(reviews), 20)
    
    formatted_reviews = []
    for r in reviews[:sample_size]:
        tags = ", ".join(r.feature_tags) if r.feature_tags else "None"
        formatted_reviews.append(f"- [Tags: {tags}] [Sentiment: {r.sentiment_label}] {r.text}")
        
    reviews_text = "\n".join(formatted_reviews)
    
    prompt_template = load_prompt("theme_discovery.txt")
    prompt = prompt_template.replace("{max_themes}", str(max_themes)).replace("{reviews}", reviews_text)
    
    client = LLMClient()
    result = client.generate_json(prompt, ThemeDiscoveryResult)
    
    if result:
        return result.themes
    return []

def assign_reviews_to_themes(reviews: List[EnrichedReview], themes: List[Theme]) -> ThemeMap:
    logger.info(f"Assigning {len(reviews)} reviews to {len(themes)} themes...")
    themes_text = "\n".join([f"- {t.name}: {t.description}" for t in themes])
    prompt_template = load_prompt("theme_assignment.txt")
    
    client = LLMClient()
    mapping: Dict[str, List[str]] = {t.name: [] for t in themes}
    mapping["Noise/Junk"] = [] # Ensure Noise theme exists in mapping
    
    # Batch in chunks of 20 to avoid exceeding 1K tokens in a single request
    batch_size = 20
    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i+batch_size]
        logger.info(f"Assigning batch {i//batch_size + 1}...")
        
        formatted_batch = []
        for r in batch:
            tags = ", ".join(r.feature_tags) if r.feature_tags else "None"
            formatted_batch.append(f"[{r.id}] [Tags: {tags}] [Sentiment: {r.sentiment_label}] {r.text}")
            
        reviews_text = "\n".join(formatted_batch)
        prompt = prompt_template.replace("{themes}", themes_text).replace("{reviews}", reviews_text)
        
        result = client.generate_json(prompt, ThemeAssignmentResult)
        if result:
            for assignment in result.assignments:
                if assignment.theme_name not in mapping:
                    mapping[assignment.theme_name] = []
                mapping[assignment.theme_name].append(assignment.review_id)
                
        if i + batch_size < len(reviews):
            logger.info("Sleeping for 65 seconds to respect 1K TPM rate limits...")
            import time
            time.sleep(65)
                
    return ThemeMap(mapping)

def build_theme_summary(theme_map: ThemeMap, reviews: List[EnrichedReview]) -> List[ThemeSummary]:
    logger.info("Building theme summaries...")
    reviews_by_id = {r.id: r for r in reviews}
    client = LLMClient()
    prompt_template = load_prompt("quote_selection.txt")
    
    summaries = []
    
    for theme_name, review_ids in theme_map.mapping.items():
        if not review_ids or theme_name.lower() == "noise/junk":
            continue
            
        theme_reviews = [reviews_by_id[rid] for rid in review_ids if rid in reviews_by_id]
        if not theme_reviews:
            continue
            
        avg_rating = sum(r.rating for r in theme_reviews) / len(theme_reviews)
        avg_sentiment = sum(r.sentiment_score for r in theme_reviews) / len(theme_reviews)
        actionable_count = sum(1 for r in theme_reviews if r.is_actionable)
        
        # Select representative quotes (Limit to 15 quotes to stay under 1K tokens)
        quotes_to_consider = "\n".join([f"- {r.text}" for r in theme_reviews[:15]]) # Send up to 15 for quote selection
        prompt = prompt_template.replace("{theme_name}", theme_name).replace("{reviews}", quotes_to_consider)
        
        result = client.generate_json(prompt, QuoteSelectionResult)
        selected_quotes = result.quotes if result else []
        
        summaries.append(ThemeSummary(
            name=theme_name,
            summary=f"Discovered theme focused on {theme_name}",
            review_count=len(theme_reviews),
            avg_rating=round(avg_rating, 2),
            avg_sentiment=round(avg_sentiment, 2),
            actionable_count=actionable_count,
            representative_quotes=selected_quotes[:3]
        ))
        
        logger.info("Sleeping for 65 seconds to respect 1K TPM rate limits...")
        import time
        time.sleep(65)
        
    # Sort by review count descending
    summaries.sort(key=lambda x: x.review_count, reverse=True)
    return summaries

def run_theme_clustering(reviews: List[EnrichedReview]) -> List[ThemeSummary]:
    settings = get_settings()
    
    themes = discover_themes(reviews, settings.max_themes)
    if not themes:
        logger.error("Failed to discover themes.")
        return []
        
    logger.info(f"Discovered {len(themes)} themes.")
    
    theme_map = assign_reviews_to_themes(reviews, themes)
    
    summaries = build_theme_summary(theme_map, reviews)
    return summaries

def main():
    import datetime
    from src.config import PROCESSED_DATA_DIR
    input_path = PROCESSED_DATA_DIR / 'enriched_reviews.json'
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return
        
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        reviews = [EnrichedReview(**r) for r in data]
        
    # Limit for live test to not hit rate limits heavily during testing
    logger.info("Running live test with 10 reviews...")
    summaries = run_theme_clustering(reviews[:10])
    
    if summaries:
        week = datetime.date.today().strftime("%Y-W%W")
        THEME_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        out_path = THEME_HISTORY_DIR / f"{week}.json"
        
        output_data = [s.model_dump(mode='json') for s in summaries]
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4)
        logger.info(f"Successfully extracted themes and saved to {out_path}")
    else:
        logger.error("Failed to extract themes.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
