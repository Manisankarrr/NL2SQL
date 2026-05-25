import logging
from typing import Any, Dict

from backend.config import settings
from backend.llm import groq_client, openrouter_client

logger = logging.getLogger(__name__)

async def generate_sql(system_prompt: str, user_message: str) -> Dict[str, str]:
    if settings.llm_provider == "openrouter":
        try:
            sql = await openrouter_client.generate_sql(system_prompt, user_message, settings.llm_model)
            provider_used = "openrouter"
            model_used = settings.llm_model
        except RuntimeError as e:
            logger.warning(f"OpenRouter failed: {e}. Trying Groq fallback...")
            if settings.groq_api_key:
                try:
                    fallback_model = "llama-3.3-70b-versatile"
                    sql = await groq_client.generate_sql(system_prompt, user_message, model=fallback_model)
                    provider_used = "groq_fallback"
                    model_used = fallback_model
                except RuntimeError as e2:
                    raise RuntimeError(f"Both providers failed. OpenRouter: {e} | Groq: {e2}")
            else:
                raise RuntimeError(f"OpenRouter failed and no GROQ_API_KEY set as fallback. Error: {e}")

    elif settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("LLM_PROVIDER is groq but GROQ_API_KEY is not set in .env")
        sql = await groq_client.generate_sql(system_prompt, user_message, model=settings.llm_model)
        provider_used = "groq"
        model_used = settings.llm_model

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: '{settings.llm_provider}'. Set to 'openrouter' or 'groq' in .env")

    logger.info(f"LLM [{provider_used}] [{model_used}] — query: {user_message[:80]}")
    
    return {
        "sql": sql,
        "provider": provider_used,
        "model": model_used
    }

async def health_check() -> Dict[str, Any]:
    try:
        or_status = await openrouter_client.health_check()
    except Exception:
        or_status = False
        
    try:
        groq_status = await groq_client.health_check()
    except Exception:
        groq_status = False

    return {
        "openrouter": or_status,
        "groq": groq_status,
        "active_provider": settings.llm_provider,
        "active_model": settings.llm_model
    }
