from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.0
    review_window_weeks: int = 12
    max_themes: int = 5
    pulse_top_themes: int = 3
    pulse_max_words: int = 250
    pulse_email_to: str = ""
    pulse_doc_id: str = ""
    llm_pii_check: bool = False
    
    mcp_server_url: str = "https://mcp-server-1-igzm.onrender.com/sse"
    mcp_auth_token: str = ""
    
    target_play_store_package: str = "com.nextbillion.groww"
    target_app_store_id: str = "1404871703"
    target_app_store_name: str = "groww-stocks-mutual-fund-ipo"
    app_country: str = "in"




    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

def get_settings() -> Settings:
    return Settings()

# Path constants
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
THEME_HISTORY_DIR = PROCESSED_DATA_DIR / "theme_history"
TEMPLATES_DIR = BASE_DIR / "templates"
EXPORTS_DIR = DATA_DIR / "exports"
