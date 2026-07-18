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
        from groq import Groq
        self.client = Groq(api_key=self.settings.groq_api_key)

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
