import sys
import os
import json
import logging
import datetime
import time
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import get_settings, Settings
from src.ingest import ingest_reviews, Review, EnrichedReview
from src.pii_scrubber import scrub_reviews
from src.analyzer import analyze_all_reviews
from src.theme_engine import run_theme_clustering, ThemeSummary
from src.pulse_generator import generate_pulse, format_pulse_markdown
from src.delivery import deliver, DeliveryResult

logger = logging.getLogger(__name__)

class PipelineResult(BaseModel):
    timestamp: datetime.datetime
    reviews_loaded: int
    reviews_after_scrub: int
    themes_found: int
    pulse_word_count: int
    delivery: Optional[DeliveryResult]
    errors: List[str]
    duration_seconds: float

def log_pipeline_result(result: PipelineResult):
    log_file = Path('data/processed/run_log.jsonl')
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(result.model_dump_json() + '\n')

def run_pipeline(settings: Settings, dry_run: bool = False, step: Optional[str] = None) -> PipelineResult:
    start_time = time.time()
    errors = []
    
    # State tracking
    reviews_loaded = 0
    reviews_after_scrub = 0
    themes_found = 0
    pulse_word_count = 0
    delivery_result = None

    def should_run(current_step: str) -> bool:
        if step is None:
            return True
        return current_step == step

    try:
        # STEP 1: Ingest
        if should_run('ingest'):
            logger.info("=== STEP 1: Scraping & Ingesting Data ===")
            # 1a. Scrape fresh data
            from src.scraper import main as run_scraper
            run_scraper()
            
            # 1b. Load into pipeline
            reviews_loaded = ingest_reviews()
            if reviews_loaded == 0:
                raise ValueError("No reviews ingested.")
        else:
            try:
                with open('data/processed/normalized_reviews.json', 'r') as f:
                    reviews_loaded = len(json.load(f))
            except Exception:
                pass

        # STEP 2 & 3: Scrub & Enrich
        if should_run('scrub'):
            logger.info("=== STEP 2: Scrubbing PII ===")
            with open('data/processed/normalized_reviews.json', 'r', encoding='utf-8') as f:
                raw_reviews = [Review(**r) for r in json.load(f)]
            
            scrubbed = scrub_reviews(raw_reviews)
            reviews_after_scrub = len(scrubbed)
            
            with open('data/processed/normalized_reviews.json', 'w', encoding='utf-8') as f:
                json.dump([r.model_dump(mode='json') for r in scrubbed], f, indent=4)
                
            logger.info("=== STEP 3: Enriching Data ===")
            analyze_all_reviews()
        else:
            try:
                with open('data/processed/enriched_reviews.json', 'r') as f:
                    reviews_after_scrub = len(json.load(f))
            except Exception:
                pass

        # STEP 4: Cluster
        if should_run('cluster'):
            logger.info("=== STEP 4: Extracting Themes (LLM) ===")
            with open('data/processed/enriched_reviews.json', 'r', encoding='utf-8') as f:
                enriched = [EnrichedReview(**r) for r in json.load(f)]
                
            # Process most recent to avoid massive rate limits
            enriched.sort(key=lambda x: x.date, reverse=True)
            recent_reviews = enriched[:15] # Temporarily reduced for quick test
            
            themes = run_theme_clustering(recent_reviews)
            if not themes:
                raise ValueError("Theme extraction failed.")
            themes_found = len(themes)
            
            with open('data/processed/themes.json', 'w', encoding='utf-8') as f:
                json.dump([t.model_dump(mode='json') for t in themes], f, indent=4)
        else:
            try:
                with open('data/processed/themes.json', 'r') as f:
                    themes_found = len(json.load(f))
            except Exception:
                pass

        # STEP 5: Generate
        if should_run('generate'):
            logger.info("=== STEP 5: Generating Weekly Pulse Report ===")
            with open('data/processed/themes.json', 'r', encoding='utf-8') as f:
                theme_summaries = [ThemeSummary(**d) for d in json.load(f)]
                
            period_end = datetime.date.today()
            period_start = period_end - datetime.timedelta(days=7)
            
            with open('data/processed/enriched_reviews.json', 'r', encoding='utf-8') as f:
                enriched = [EnrichedReview(**r) for r in json.load(f)]
            
            total_reviews = min(len(enriched), 300)
            sources = list(set(r.source for r in enriched[:300]))
            
            pulse = generate_pulse(theme_summaries, total_reviews, sources, period_start, period_end)
            pulse_word_count = pulse.word_count
            md_content = format_pulse_markdown(pulse)
            
            exports_dir = Path('data/exports')
            exports_dir.mkdir(parents=True, exist_ok=True)
            with open(exports_dir / 'weekly_pulse.md', 'w', encoding='utf-8') as f:
                f.write(md_content)
                
            with open(exports_dir / 'pulse.json', 'w', encoding='utf-8') as f:
                f.write(pulse.model_dump_json())
        else:
            try:
                with open('data/exports/pulse.json', 'r') as f:
                    pulse_data = json.load(f)
                    pulse_word_count = pulse_data.get('word_count', 0)
            except Exception:
                pass

        # STEP 6: Deliver
        if should_run('deliver'):
            logger.info("=== STEP 6: Delivering via MCP ===")
            if dry_run:
                logger.info("DRY RUN ENABLED: Skipping MCP Delivery.")
            else:
                with open('data/exports/pulse.json', 'r', encoding='utf-8') as f:
                    import importlib
                    pulse_module = importlib.import_module('src.pulse_generator')
                    pulse = pulse_module.PulseReport(**json.load(f))
                
                with open('data/exports/weekly_pulse.md', 'r', encoding='utf-8') as f:
                    md_content = f.read()
                    
                email_body = (
                    f"Hello Team,\n\n"
                    f"The Weekly Review Pulse for {pulse.period_start} to {pulse.period_end} is ready for review.\n\n"
                    f"This week, the AI analyzed {pulse.total_reviews} recent user reviews and identified {len(pulse.top_themes)} core themes affecting our users.\n\n"
                    f"Please click the link below to read the full automated report."
                )
                delivery_result = deliver(pulse, md_content, email_body, settings)
                logger.info(f"Delivery result: {delivery_result}")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        errors.append(str(e))

    duration = time.time() - start_time
    
    result = PipelineResult(
        timestamp=datetime.datetime.now(),
        reviews_loaded=reviews_loaded,
        reviews_after_scrub=reviews_after_scrub,
        themes_found=themes_found,
        pulse_word_count=pulse_word_count,
        delivery=delivery_result,
        errors=errors,
        duration_seconds=duration
    )
    
    log_pipeline_result(result)
    
    if errors:
        logger.error(f"Pipeline finished with errors in {duration:.2f}s")
    else:
        logger.info(f"Pipeline completed successfully in {duration:.2f}s")
        
    return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    settings = get_settings()
    run_pipeline(settings)
