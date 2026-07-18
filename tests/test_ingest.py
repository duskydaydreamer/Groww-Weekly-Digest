import json
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.ingest import (
    Review,
    generate_hash,
    load_app_store_reviews,
    load_play_store_reviews,
    normalize_reviews,
    save_normalized,
)

def test_generate_hash():
    hash1 = generate_hash("app_store", "test", date(2026, 7, 15))
    hash2 = generate_hash("app_store", "test", date(2026, 7, 15))
    hash3 = generate_hash("play_store", "test", date(2026, 7, 15))
    
    assert hash1 == hash2  # Deterministic
    assert hash1 != hash3  # Source matters
    assert len(hash1) == 16

def test_load_app_store_reviews():
    sample_csv = Path(__file__).parent.parent / "data" / "raw" / "sample_app_store_reviews.csv"
def test_generate_hash_consistency():
    hash1 = generate_hash("play_store", "test", date(2026, 7, 15))
    hash2 = generate_hash("play_store", "test", date(2026, 7, 15))
    assert hash1 == hash2

def test_load_play_store_reviews():
    sample_csv = Path(__file__).parent.parent / "data" / "raw" / "sample_play_store_reviews.csv"
    reviews = load_play_store_reviews(sample_csv)
    
    assert len(reviews) > 0
    assert reviews[0].source == "play_store"
    assert reviews[0].rating in range(1, 6)

def test_normalize_deduplication():
    # Same hash due to same content, date, and source
    r1 = Review(id="1", source="play_store", rating=5, title=None, text="This is a test review with exactly eight words.", date=date(2026, 7, 10), word_count=9)
    r1_dup = Review(id="1", source="play_store", rating=5, title=None, text="This is a test review with exactly eight words.", date=date(2026, 7, 10), word_count=9)
    
    normalized = normalize_reviews([r1, r1_dup])
    assert len(normalized) == 1

def test_normalize_sorting():
    r1 = Review(id="1", source="play_store", rating=5, title=None, text="This is the first mock review with eight words.", date=date(2026, 7, 10), word_count=9)
    r2 = Review(id="2", source="play_store", rating=4, title=None, text="This is the second mock review with eight words.", date=date(2026, 7, 12), word_count=9)
    
    normalized = normalize_reviews([r1, r2])
    # Newest first
    assert normalized[0].id == "2"

def test_save_normalized(tmp_path):
    r1 = Review(id="1", source="play_store", rating=5, title=None, text="This is a test review with exactly eight words.", date=date(2026, 7, 10), word_count=9)
    
    out_file = tmp_path / "normalized.json"
    save_normalized([r1], out_file)
    
    assert out_file.exists()
    with open(out_file) as f:
        data = json.load(f)
        assert len(data) == 1
        assert data[0]["source"] == "play_store"
