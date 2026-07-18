import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import datetime
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader

from src.config import get_settings, TEMPLATES_DIR, PROCESSED_DATA_DIR
from src.llm_client import LLMClient
from src.theme_engine import ThemeSummary

logger = logging.getLogger(__name__)

class PulseTheme(BaseModel):
    name: str
    summary: str
    avg_sentiment: float
    actionable_count: int

class PulseQuote(BaseModel):
    text: str

class PulseReport(BaseModel):
    week_label: str
    period_start: datetime.date
    period_end: datetime.date
    total_reviews: int
    sources: List[str]
    top_themes: List[PulseTheme]
    user_quotes: List[PulseQuote]
    action_ideas: List[str]
    word_count: int

class ActionIdeasResult(BaseModel):
    ideas: List[str]

def format_pulse_markdown(pulse: PulseReport) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("pulse_template.md")
    return template.render(**pulse.model_dump())

def format_pulse_email(pulse: PulseReport, doc_url: Optional[str] = None) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("email_template.md")
    return template.render(**pulse.model_dump(), doc_url=doc_url)

def generate_pulse(theme_summaries: List[ThemeSummary], total_reviews: int, sources: List[str], period_start: datetime.date, period_end: datetime.date) -> PulseReport:
    logger.info("Generating Pulse report...")
    top_themes = theme_summaries[:3]
    
    pulse_themes = [PulseTheme(name=t.name, summary=t.summary, avg_sentiment=t.avg_sentiment, actionable_count=t.actionable_count) for t in top_themes]
    
    pulse_quotes = []
    for t in top_themes:
        if t.representative_quotes:
            pulse_quotes.append(PulseQuote(text=t.representative_quotes[0]))
            
    client = LLMClient()
    themes_text = "\n".join([f"- {t.name}: {t.summary} (Sentiment: {t.avg_sentiment}, Actionable issues: {t.actionable_count})" for t in top_themes])
    prompt = f"""You are a Product Manager for an Indian fintech app. Based on these top 3 user feedback themes and their metadata (sentiment score ranges from -1.0 to 1.0), suggest 3 concrete, actionable product improvements. Keep each action to one very short sentence in professional English, even if the user quotes contain Hinglish or local jargon. Heavily prioritize themes with low sentiment and high actionable issues.
Themes:
{themes_text}

Return a JSON object with a list of strings called 'ideas'. Max 3 ideas."""

    for attempt in range(3):
        result = client.generate_json(prompt, ActionIdeasResult)
        action_ideas = result.ideas if result else []
        
        week_label = f"Week of {period_start.strftime('%B %d, %Y')}"
        
        pulse = PulseReport(
            week_label=week_label,
            period_start=period_start,
            period_end=period_end,
            total_reviews=total_reviews,
            sources=sources,
            top_themes=pulse_themes,
            user_quotes=pulse_quotes[:3],
            action_ideas=action_ideas[:3],
            word_count=0
        )
        
        md_content = format_pulse_markdown(pulse)
        word_count = len(md_content.split())
        pulse.word_count = word_count
        
        if word_count <= 250:
            break
            
        logger.warning(f"Word count {word_count} exceeds 250 limit. Retrying (attempt {attempt+1})...")
        prompt += "\n\nCRITICAL: Make the ideas even shorter. You must strictly limit the total word count."
        
    return pulse

def main():
    import json
    import glob
    from src.config import THEME_HISTORY_DIR, EXPORTS_DIR
    
    history_files = list(THEME_HISTORY_DIR.glob("*.json"))
    if not history_files:
        logger.error("No theme history files found. Run theme_engine.py first.")
        return
        
    latest_file = max(history_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Loading themes from {latest_file}")
    
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        theme_summaries = [ThemeSummary(**d) for d in data]
        
    period_end = datetime.date.today()
    period_start = period_end - datetime.timedelta(days=7)
    
    total_reviews = sum(t.review_count for t in theme_summaries)
    
    pulse = generate_pulse(theme_summaries, total_reviews, ["App Store", "Play Store"], period_start, period_end)
    md_content = format_pulse_markdown(pulse)
    
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPORTS_DIR / "weekly_pulse.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    logger.info(f"Pulse Markdown generated at {out_path} with word count {pulse.word_count}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    main()
