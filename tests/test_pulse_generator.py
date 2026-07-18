import pytest
import datetime
from unittest.mock import patch, MagicMock
from src.pulse_generator import (
    generate_pulse, format_pulse_markdown, format_pulse_email,
    PulseTheme, PulseQuote, PulseReport, ActionIdeasResult
)
from src.theme_engine import ThemeSummary

@pytest.fixture
def mock_theme_summaries():
    return [
        ThemeSummary(name="F&O Issues", summary="Users face F&O chart lags.", review_count=100, avg_rating=2.1, avg_sentiment=-0.8, actionable_count=40, representative_quotes=["Very bad lag on F&O"]),
        ThemeSummary(name="Brokerage", summary="Brokerage charges are too high.", review_count=50, avg_rating=1.5, avg_sentiment=-0.9, actionable_count=20, representative_quotes=["Please reduce brokerage", "Looting us!"]),
        ThemeSummary(name="UI Update", summary="The new UI is confusing.", review_count=30, avg_rating=3.0, avg_sentiment=0.0, actionable_count=5, representative_quotes=["I can't find portfolio tab."]),
        ThemeSummary(name="Extra", summary="Extra theme.", review_count=10, avg_rating=4.0, avg_sentiment=0.5, actionable_count=0, representative_quotes=["Good."]),
    ]

@patch('src.pulse_generator.LLMClient')
def test_generate_pulse(MockLLMClient, mock_theme_summaries):
    mock_instance = MockLLMClient.return_value
    mock_instance.generate_json.return_value = ActionIdeasResult(
        ideas=["Fix the F&O lag.", "Review brokerage slabs.", "Revert the UI changes."]
    )
    
    start_date = datetime.date(2026, 7, 1)
    end_date = datetime.date(2026, 7, 7)
    
    pulse = generate_pulse(mock_theme_summaries, total_reviews=200, sources=["App Store", "Play Store"], period_start=start_date, period_end=end_date)
    
    assert pulse.total_reviews == 200
    assert len(pulse.top_themes) == 3
    assert len(pulse.user_quotes) == 3
    assert len(pulse.action_ideas) == 3
    assert pulse.word_count <= 250
    assert "Week of July 01, 2026" == pulse.week_label
    
def test_format_pulse_markdown():
    pulse = PulseReport(
        week_label="Week of Test",
        period_start=datetime.date(2026, 7, 1),
        period_end=datetime.date(2026, 7, 7),
        total_reviews=200,
        sources=["App Store"],
        top_themes=[PulseTheme(name="Test Theme", summary="Test Summary", avg_sentiment=-0.5, actionable_count=10)],
        user_quotes=[PulseQuote(text="Test quote")],
        action_ideas=["Test action"],
        word_count=50
    )
    
    md = format_pulse_markdown(pulse)
    assert "📊 Weekly Review Pulse" in md
    assert "Test Theme" in md
    assert "Test quote" in md
    assert "Test action" in md
    assert "Reviews analyzed: 200" in md

def test_format_pulse_email():
    pulse = PulseReport(
        week_label="Week of Test",
        period_start=datetime.date(2026, 7, 1),
        period_end=datetime.date(2026, 7, 7),
        total_reviews=200,
        sources=["App Store"],
        top_themes=[PulseTheme(name="Test Theme", summary="Test Summary", avg_sentiment=-0.5, actionable_count=10)],
        user_quotes=[PulseQuote(text="Test quote")],
        action_ideas=["Test action"],
        word_count=50
    )
    
    email = format_pulse_email(pulse, doc_url="http://example.com/doc")
    assert "Subject: 📊 Weekly Review Pulse — Week of Test" in email
    assert "http://example.com/doc" in email
    assert "Test Theme" in email
