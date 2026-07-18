import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from src.ingest import EnrichedReview
from src.theme_engine import (
    Theme, ThemeDiscoveryResult, ThemeAssignment, ThemeAssignmentResult, QuoteSelectionResult,
    discover_themes, assign_reviews_to_themes, build_theme_summary, run_theme_clustering
)

@pytest.fixture
def mock_reviews():
    return [
        EnrichedReview(id="1", source="play_store", rating=5, title=None, text="Great app for F&O", date=date.today(), word_count=5, sentiment_score=0.8, sentiment_label="Positive", feature_tags=["Trading & Brokerage"], is_actionable=False),
        EnrichedReview(id="2", source="play_store", rating=1, title=None, text="High brokerage charges", date=date.today(), word_count=3, sentiment_score=-0.7, sentiment_label="Negative", feature_tags=["Trading & Brokerage"], is_actionable=True),
        EnrichedReview(id="3", source="play_store", rating=4, title=None, text="Easy demat account opening", date=date.today(), word_count=4, sentiment_score=0.6, sentiment_label="Positive", feature_tags=["Onboarding & KYC"], is_actionable=False),
    ]

@patch('src.theme_engine.LLMClient')
def test_discover_themes(MockLLMClient, mock_reviews):
    mock_instance = MockLLMClient.return_value
    mock_instance.generate_json.return_value = ThemeDiscoveryResult(
        themes=[
            Theme(name="Brokerage", description="Feedback on charges"),
            Theme(name="F&O", description="Futures and Options trading features"),
            Theme(name="Noise/Junk", description="Gibberish")
        ]
    )
    
    themes = discover_themes(mock_reviews, max_themes=5)
    assert len(themes) == 3
    assert themes[0].name == "Brokerage"

@patch('src.theme_engine.LLMClient')
def test_assign_reviews_to_themes(MockLLMClient, mock_reviews):
    mock_instance = MockLLMClient.return_value
    mock_instance.generate_json.return_value = ThemeAssignmentResult(
        assignments=[
            ThemeAssignment(review_id="1", theme_name="F&O"),
            ThemeAssignment(review_id="2", theme_name="Brokerage"),
            ThemeAssignment(review_id="3", theme_name="Demat"),
        ]
    )
    
    themes = [Theme(name="F&O", description=""), Theme(name="Brokerage", description="")]
    theme_map = assign_reviews_to_themes(mock_reviews, themes)
    
    assert "F&O" in theme_map.mapping
    assert "1" in theme_map.mapping["F&O"]
    assert "Brokerage" in theme_map.mapping
    assert "2" in theme_map.mapping["Brokerage"]

@patch('src.theme_engine.LLMClient')
def test_build_theme_summary(MockLLMClient, mock_reviews):
    mock_instance = MockLLMClient.return_value
    mock_instance.generate_json.return_value = QuoteSelectionResult(
        quotes=["High brokerage charges"]
    )
    
    # Manually create ThemeMap
    from src.theme_engine import ThemeMap
    mapping = {
        "Brokerage": ["2"],
        "F&O": ["1"],
        "Noise/Junk": ["3"] # test exclusion
    }
    theme_map = ThemeMap(mapping)
    
    summaries = build_theme_summary(theme_map, mock_reviews)
    
    assert len(summaries) == 2
    
    # Should be sorted by review count, since both have 1, the order may vary, but let's check content
    brokerage_summary = next((s for s in summaries if s.name == "Brokerage"), None)
    assert brokerage_summary is not None
    assert brokerage_summary.review_count == 1
    assert brokerage_summary.avg_rating == 1.0
    assert brokerage_summary.avg_sentiment == -0.7
    assert brokerage_summary.actionable_count == 1
    assert "High brokerage charges" in brokerage_summary.representative_quotes
    
    # Noise should be excluded
    noise_summary = next((s for s in summaries if s.name == "Noise/Junk"), None)
    assert noise_summary is None
