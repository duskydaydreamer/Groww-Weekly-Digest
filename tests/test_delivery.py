import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from src.delivery import deliver_async, deliver, DocResult, DraftResult, DeliveryResult
from src.config import Settings

@pytest.fixture
def mock_settings():
    return Settings(
        pulse_email_to="test@example.com",
        pulse_doc_id="Test Document"
    )

def test_deliver_async_success(mock_settings):
    pulse_md = "# Pulse Data"
    email_body = "Hello"
    
    async def run_test():
    
        with patch("src.delivery.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            with patch("src.delivery.aconnect_sse") as mock_aconnect_sse:
                mock_event_source = AsyncMock()
                mock_aconnect_sse.return_value.__aenter__.return_value = mock_event_source
                
                # Mock SSE events
                class MockEvent:
                    def __init__(self, event, data):
                        self.event = event
                        self.data = data
                
                async def mock_aiter_sse():
                    yield MockEvent("endpoint", "/test_endpoint")
                    pass
                
                mock_event_source.aiter_sse = mock_aiter_sse
                
                with patch("src.delivery.publish_to_google_docs", new_callable=AsyncMock) as mock_pub:
                    mock_pub.return_value = DocResult(doc_id="1", doc_url="http://doc", status="created")
                    with patch("src.delivery.create_gmail_draft", new_callable=AsyncMock) as mock_draft:
                        mock_draft.return_value = DraftResult(draft_id="1", message="ok", status="created")
                        
                        result = await deliver_async(pulse_md, email_body, mock_settings)
                        
                        assert isinstance(result, DeliveryResult)
                        assert not result.fallback_used
                        assert result.doc.status == "created"
                        assert result.draft.status == "created"
    
    asyncio.run(run_test())

def test_deliver_sync(mock_settings):
    pulse = MagicMock()
    pulse_md = "# Pulse"
    email_body = "Test email"
    
    with patch("src.delivery.asyncio.run") as mock_run:
        mock_run.return_value = DeliveryResult(
            doc=DocResult(doc_id="1", doc_url="http", status="created"),
            draft=DraftResult(draft_id="1", message="ok", status="created"),
            fallback_used=False
        )
        result = deliver(pulse, pulse_md, email_body, mock_settings)
        assert result.doc.doc_id == "1"
        assert result.draft.draft_id == "1"
