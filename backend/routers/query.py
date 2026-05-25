from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from backend.nlp.intent_classifier import classify_intent, SQLIntent
from backend.nlp.entity_extractor import extract_entities
from backend.llm.prompt_builder import build_prompt
from backend.llm.client import generate_sql, health_check as llm_health
from backend.validation.sql_validator import validate_sql, get_user_friendly_error
from backend.database.schema_loader import get_schema
from backend.database.executor import execute_sql
from backend.response.formatter import format_response
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["query"])

class QueryRequest(BaseModel):
    user_input: str
    session_id: str = "default"

class QueryResponse(BaseModel):
    message: str
    sql_used: Optional[str] = None
    intent: str = "UNKNOWN"
    entities: dict = {}
    table: Optional[list] = None
    columns: Optional[list] = None
    affected_rows: Optional[int] = None
    execution_time_ms: Optional[float] = None
    error: bool = False
    provider: Optional[str] = None
    count: int = 0


@router.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    try:
        # STEP 1
        intent = classify_intent(request.user_input)
        
        # STEP 2
        entities = extract_entities(request.user_input)
        
        # STEP 3
        if intent == SQLIntent.UNKNOWN:
            return QueryResponse(
                message="I couldn't understand that. Try: 'Show appointments for tomorrow', 'Add appointment for Rahul at 5 PM', 'Cancel Ravi appointment', 'Update Priya to 6 PM'",
                intent="UNKNOWN", 
                error=False
            )
        
        # STEP 4
        schema = await get_schema()
        
        # STEP 5
        system_prompt, user_message = await build_prompt(request.user_input, intent, entities)
        
        # STEP 6
        llm_result = await generate_sql(system_prompt, user_message)
        raw_sql = llm_result["sql"]
        provider = llm_result["provider"]
        
        # STEP 7
        validation = validate_sql(raw_sql, schema, expected_intent=intent.value)
        if not validation.ok:
            friendly_error = get_user_friendly_error(validation)
            logger.warning(f"Validation blocked SQL: {validation.reason} | SQL: {raw_sql[:100]}")
            return QueryResponse(message=friendly_error, sql_used=raw_sql, intent=intent.value, error=True, provider=provider)
        
        # STEP 8
        exec_result = await execute_sql(validation.cleaned_sql)
        
        # STEP 9
        response_data = format_response(intent, exec_result, request.user_input, entities, validation.cleaned_sql)
        
        # STEP 10
        entities_dict = {k: v for k, v in vars(entities).items() if v is not None} if entities else {}
        
        return QueryResponse(**response_data, entities=entities_dict, provider=provider)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return QueryResponse(message=f"Unexpected error: {str(e)}", error=True)


@router.get("/health")
async def health():
    llm_status = await llm_health()
    try:
        schema = await get_schema()
        db_ok = len(schema.get("tables", {})) > 0
    except Exception:
        schema = {}
        db_ok = False
        
    return {
        "status": "ok", 
        "db_connected": db_ok, 
        "tables_loaded": list(schema.get("tables", {}).keys()) if db_ok else [], 
        **llm_status
    }
