import logging
import httpx
from typing import Dict

from backend.config import settings

logger = logging.getLogger(__name__)

FREE_MODELS: Dict[str, str] = {
    "best_sql": "deepseek/deepseek-coder",
    "best_general": "meta-llama/llama-3.1-8b-instruct:free",
    "fastest": "google/gemma-2-9b-it:free",
    "most_capable": "meta-llama/llama-3.3-70b-instruct:free"
}

DEFAULT_MODEL: str = "meta-llama/llama-3.3-70b-instruct:free"

def _clean_sql(raw: str) -> str:
    cleaned = raw.strip()
    if cleaned.startswith("```sql"):
        cleaned = cleaned[6:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    lines = cleaned.splitlines()
    while lines and lines[0].strip().startswith("--"):
        lines.pop(0)
        
    return "\n".join(lines).strip()

async def generate_sql(system_prompt: str, user_message: str, model: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "BarberSQL"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,
        "max_tokens": 500
    }
    
    timeout = httpx.Timeout(30.0)
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            
            cleaned_sql = _clean_sql(raw_content)
            if not cleaned_sql:
                raise ValueError("Empty SQL response from OpenRouter")
                
            logger.info(f"OpenRouter success. Model: {model}. Query: {user_message[:60]}")
            return cleaned_sql
            
    except httpx.TimeoutException:
        raise RuntimeError("OpenRouter API timeout. Check your internet connection.")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise RuntimeError("Invalid OpenRouter API key. Check OPENROUTER_API_KEY in .env")
        if e.response.status_code == 429:
            raise RuntimeError("OpenRouter rate limit hit. Wait a moment and retry.")
        raise RuntimeError(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")

async def health_check() -> bool:
    if not settings.openrouter_api_key:
        return False
        
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"}
            )
            return response.status_code == 200
    except Exception:
        return False
