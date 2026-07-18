import pytest
from datetime import date
from src.ingest import Review
from src.analyzer import (
    analyze_sentiment,
    extract_features,
    check_actionability,
    enrich_review
)

def test_analyze_sentiment():
    score, label = analyze_sentiment("This app is amazing and very useful!")
    assert score > 0
    assert label == "Positive"
    
    score, label = analyze_sentiment("This is the worst app, it always crashes.")
    assert score < 0
    assert label == "Negative"
    
    score, label = analyze_sentiment("The app has a blue icon.")
    assert -0.1 <= score <= 0.1
    assert label == "Neutral"

def test_extract_features():
    features = extract_features("brokerage is too high for intraday trading")
    assert "Trading & Brokerage" in features
    
    features = extract_features("my mutual fund SIP failed")
    assert "Mutual Funds & SIP" in features
    
    features = extract_features("app is stuck on loading screen")
    assert "App Performance" in features

def test_check_actionability():
    assert check_actionability("please fix this issue immediately") == True
    assert check_actionability("why did you charge me extra") == True
    assert check_actionability("nice app, very good") == False

def test_enrich_review():
    r = Review(
        id="123",
        source="play_store",
        rating=1,
        title="Bad experience",
        text="Worst app ever, please fix the glitch where login fails.",
        date=date(2026, 7, 18),
        word_count=10
    )
    
    enriched = enrich_review(r)
    assert enriched.sentiment_label == "Negative"
    assert "App Performance" in enriched.feature_tags
    assert "Onboarding & KYC" in enriched.feature_tags
    assert enriched.is_actionable == True
