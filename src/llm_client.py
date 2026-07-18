import time
import json
import logging
from typing import Any, Type, Optional, TypeVar
from pydantic import BaseModel
from src.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

class LLMClient:
    def __init__(self):
        self.settings = get_settings()
        if not self.settings.groq_api_key:
            logger.error("GROQ_API_KEY is empty or not set. Please check your environment variables or GitHub Secrets.")
            raise ValueError("GROQ_API_KEY is required but not set.")
            
        import httpx
        from groq import Groq
        
        # Use a custom HTTP client forcing IPv4, which resolves some Github Actions connection issues with Groq API
        http_client = httpx.Client(
            transport=httpx.HTTPTransport(local_address="0.0.0.0")
        )
        self.client = Groq(api_key=self.settings.groq_api_key, http_client=http_client)

    def generate_json(self, prompt: str, schema: Type[T]) -> Optional[T]:
        """Calls the LLM and parses the response into the provided Pydantic schema, with retries."""
        retries = [20, 65, 65]
        
        for attempt, backoff in enumerate(retries + [0]):
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=self.settings.groq_model,
                    temperature=self.settings.groq_temperature,
                    response_format={"type": "json_object"},
                )
                text = chat_completion.choices[0].message.content
                
                # Parse JSON and validate against schema
                data = json.loads(text)
                return schema.model_validate(data)
                
            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt+1}): {e}")
                if backoff:
                    logger.info(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                else:
                    logger.error("All retries failed for LLM call.")
                    return None
