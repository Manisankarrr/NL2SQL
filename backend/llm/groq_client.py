import logging
from typing import Dict

import groq
from groq import AsyncGroq

from backend.config import settings

logger = logging.getLogger(__name__)

GROQ_FREE_MODELS: Dict[str, str] = {
    "best": "llama-3.3-70b-versatile",
    "fast": "llama-3.1-8b-instant",
    "balanced": "mixtral-8x7b-32768"
}

def _clean_sql(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```sql"):
        cleaned = cleaned[6:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    return cleaned

async def generate_sql(system_prompt: str, user_message: str, model: str = "llama-3.3-70b-versatile") -> str:
    try:
        # Note: Use async client to prevent event loop blocking
        client = AsyncGroq(api_key=settings.groq_api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        raw_content = response.choices[0].message.content
        if raw_content is None:
            raise ValueError("Empty response content from Groq")
            
        cleaned_sql = _clean_sql(raw_content)
        if not cleaned_sql:
            raise ValueError("Empty SQL response from Groq after cleaning")
            
        logger.info(f"Groq success. Model: {model}. Query: {user_message[:60]}")
        return cleaned_sql
        
    except groq.APIConnectionError:
        raise RuntimeError("Cannot connect to Groq API")
    except groq.RateLimitError:
        raise RuntimeError("Groq rate limit hit. Wait a moment.")
    except groq.AuthenticationError:
        raise RuntimeError("Invalid GROQ_API_KEY in .env")

async def health_check() -> bool:
    return bool(settings.groq_api_key and settings.groq_api_key.strip())
