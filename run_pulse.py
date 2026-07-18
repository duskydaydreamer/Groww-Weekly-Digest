import argparse
import sys
import logging
from src.config import get_settings
from src.pipeline import run_pipeline

def main():
    parser = argparse.ArgumentParser(description="App Store Review Pulse CLI")
    parser.add_argument("--dry-run", action="store_true", help="Generate pulse locally; skip MCP delivery")
    parser.add_argument("--step", type=str, choices=["ingest", "scrub", "cluster", "generate", "deliver"], 
                        help="Run a single step of the pipeline")
    parser.add_argument("--config", type=str, default=".env", help="Path to .env file (default: .env)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", force=True)
    
    settings = get_settings()
    
    print("=======================================")
    print("      APP STORE REVIEW PULSE           ")
    print("=======================================")
    if args.dry_run:
        print(">> MODE: DRY RUN (Delivery Skipped)")
    if args.step:
        print(f">> MODE: STEP-WISE ({args.step})")
        
    result = run_pipeline(settings, dry_run=args.dry_run, step=args.step)
    
    print("\n--- Pipeline Summary ---")
    print(f"Reviews Loaded:  {result.reviews_loaded}")
    print(f"Themes Found:    {result.themes_found}")
    print(f"Word Count:      {result.pulse_word_count}")
    print(f"Duration:        {result.duration_seconds:.1f}s")
    if result.errors:
        print(f"Errors:          {len(result.errors)}")
        for err in result.errors:
            print(f"  - {err}")
    if result.delivery:
        print(f"Delivery:        {result.delivery.model_dump_json()}")
        
    if result.errors:
        sys.exit(1)

if __name__ == "__main__":
    main()
