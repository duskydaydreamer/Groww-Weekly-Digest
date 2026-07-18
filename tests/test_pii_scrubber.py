import pytest
from datetime import date
from src.pii_scrubber import scrub_text, scrub_reviews
from src.ingest import Review

def test_scrub_text_clean():
    """Test that text without PII is not modified."""
    text = "This is a great app! I love the features."
    assert scrub_text(text) == text

def test_scrub_text_email():
    text = "Contact me at test.user@example.com for more info."
    expected = "Contact me at [EMAIL_REDACTED] for more info."
    assert scrub_text(text) == expected

def test_scrub_text_upi():
    text = "I tried to pay from my UPI id rahul123@okicici but it failed. Or try 9876543210@paytm."
    expected = "I tried to pay from my UPI id [UPI_REDACTED] but it failed. Or try [UPI_REDACTED]."
    assert scrub_text(text) == expected

def test_scrub_text_phone():
    text = "Call me at +919876543210 or 9876543210 or +91-9876543210."
    expected = "Call me at [PHONE_REDACTED] or [PHONE_REDACTED] or [PHONE_REDACTED]."
    assert scrub_text(text) == expected

def test_scrub_text_pan():
    text = "My PAN is ABCDE1234F and it's not updating."
    expected = "My PAN is [PAN_REDACTED] and it's not updating."
    assert scrub_text(text) == expected
    
    # Negative test
    text2 = "Some random word ABCD1234EF doesn't match exactly."
    assert scrub_text(text2) == text2

def test_scrub_text_aadhar():
    text = "Aadhar 1234 5678 9012 is linked. Or 1234-5678-9012."
    expected = "Aadhar [AADHAR_REDACTED] is linked. Or [AADHAR_REDACTED]."
    assert scrub_text(text) == expected

def test_scrub_text_mentions():
    text = "Hey @customer_support, fix this."
    expected = "Hey [USER_REDACTED], fix this."
    assert scrub_text(text) == expected

def test_scrub_text_urls():
    text = "Check out my profile at http://example.com/user/123"
    expected = "Check out my profile at [URL_REDACTED]"
    assert scrub_text(text) == expected

def test_scrub_text_uuid():
    text = "Error code: 550e8400-e29b-41d4-a716-446655440000"
    expected = "Error code: [ID_REDACTED]"
    assert scrub_text(text) == expected

def test_scrub_mixed_content():
    text = "My email is test@test.com, PAN ABCDE1234F, call +919999999999. @support check http://test.com"
    expected = "My email is [EMAIL_REDACTED], PAN [PAN_REDACTED], call [PHONE_REDACTED]. [USER_REDACTED] check [URL_REDACTED]"
    assert scrub_text(text) == expected

def test_scrub_reviews():
    reviews = [
        Review(
            id="1",
            source="play_store",
            rating=5,
            title="Help @support",
            text="Please call me at 9876543210",
            date=date(2026, 1, 1),
            word_count=6
        ),
        Review(
            id="2",
            source="play_store",
            rating=1,
            title=None,
            text="Clean review here.",
            date=date(2026, 1, 2),
            word_count=3
        )
    ]
    
    scrubbed = scrub_reviews(reviews)
    
    assert len(scrubbed) == 2
    # Verify first review is scrubbed
    assert scrubbed[0].title == "Help [USER_REDACTED]"
    assert scrubbed[0].text == "Please call me at [PHONE_REDACTED]"
    # Verify original is not mutated
    assert reviews[0].title == "Help @support"
    assert reviews[0].text == "Please call me at 9876543210"
    
    # Verify second review is untouched
    assert scrubbed[1].title is None
    assert scrubbed[1].text == "Clean review here."
