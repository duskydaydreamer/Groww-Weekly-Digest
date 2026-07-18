import pytest
from unittest.mock import patch, mock_open, MagicMock
import datetime
from src.pipeline import run_pipeline, PipelineResult
from src.config import Settings

@pytest.fixture
def mock_settings():
    return Settings(
        pulse_email_to="test@example.com",
        pulse_doc_id="test_doc_id"
    )

@patch("src.pipeline.ingest_reviews", return_value=10)
@patch("src.pipeline.scrub_reviews", return_value=[])
@patch("src.pipeline.analyze_all_reviews")
@patch("src.pipeline.run_theme_clustering")
@patch("src.pipeline.generate_pulse")
@patch("src.pipeline.deliver")
@patch("builtins.open", new_callable=mock_open)
@patch("pathlib.Path.mkdir")
@patch("src.pipeline.json.load")
@patch("src.pipeline.json.dump")
def test_pipeline_dry_run(
    mock_json_dump, mock_json_load, mock_mkdir, mock_file, 
    mock_deliver, mock_generate, mock_cluster, mock_analyze, 
    mock_scrub, mock_ingest, mock_settings
):
    # Mock some data structure for json.load
    mock_json_load.return_value = []
    
    # Mock run_theme_clustering
    mock_cluster.return_value = [MagicMock(name="theme1")]
    
    # Mock generate_pulse
    mock_pulse = MagicMock()
    mock_pulse.word_count = 150
    mock_pulse.model_dump_json.return_value = "{}"
    mock_generate.return_value = mock_pulse
    
    # Execute
    result = run_pipeline(mock_settings, dry_run=True)
    
    # Assert
    assert isinstance(result, PipelineResult)
    assert len(result.errors) == 0
    assert result.reviews_loaded == 10
    assert result.pulse_word_count == 150
    
    # Ensure delivery was skipped
    mock_deliver.assert_not_called()

@patch("src.pipeline.ingest_reviews", return_value=10)
@patch("builtins.open", new_callable=mock_open)
@patch("src.pipeline.json.load", return_value=[])
def test_pipeline_step_ingest(mock_json_load, mock_file, mock_ingest, mock_settings):
    result = run_pipeline(mock_settings, step="ingest")
    
    assert isinstance(result, PipelineResult)
    assert len(result.errors) == 0
    assert result.reviews_loaded == 10
    
    # It shouldn't run other steps, so themes_found should be 0 because we didn't mock open correctly to load them
    # Actually, in ingest-only mode, the rest are skipped and might attempt to load from disk.
    assert mock_ingest.called

@patch("src.pipeline.ingest_reviews", side_effect=Exception("Database down"))
@patch("builtins.open", new_callable=mock_open)
def test_pipeline_error_handling(mock_file, mock_ingest, mock_settings):
    result = run_pipeline(mock_settings)
    
    assert isinstance(result, PipelineResult)
    assert len(result.errors) == 1
    assert "Database down" in result.errors[0]
