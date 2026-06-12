from pathlib import Path
from typing import Tuple

from backend.database.schema_loader import format_schema_for_prompt, get_schema
from backend.retrieval.semantic_schema_search import search_relevant_schema, format_retrieved_schema_for_prompt
from backend.nlp.entity_extractor import ExtractedEntities
from backend.nlp.intent_classifier import SQLIntent
from backend.planner.decomposition import classify_complexity
from backend.planner.query_planner import plan_query, format_plan_for_prompt

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

def load_system_prompt() -> str:
    prompt_path = PROMPTS_DIR / "system_prompt.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"System prompt file not found at '{prompt_path}'. "
            f"Ensure 'prompts/system_prompt.txt' exists in the project root."
        )
    return prompt_path.read_text(encoding="utf-8")

async def build_prompt(
    user_input: str,
    intent: SQLIntent,
    entities: ExtractedEntities,
    max_rows: int = 50
) -> Tuple[str, str]:
    # Build system prompt
    raw_prompt = load_system_prompt()
    schema = await get_schema()
    
    chunks = await search_relevant_schema(user_input, intent)
    if len(chunks) < 3:
        schema_context = format_schema_for_prompt(schema)
    else:
        schema_context = format_retrieved_schema_for_prompt(chunks, schema)

    complexity, _ = classify_complexity(user_input)
    if complexity == "COMPLEX":
        plan = await plan_query(user_input, intent, entities, schema)
        plan_text = format_plan_for_prompt(plan)
        schema_context = schema_context + "\n\n" + plan_text

    system_prompt = (
        raw_prompt
        .replace("{schema_context}", schema_context)
        .replace("{max_rows}", str(max_rows))
    )

    # Build user message
    if intent.value == "UPDATE" and entities.date:
        date_label = f"new_date (only use if user wants to change the date): {entities.date}"
    else:
        date_label = f"Date: {entities.date if entities.date else 'not specified'}"

    user_message = f"""Intent: {intent.value}
    {date_label}
    Time: {entities.time if entities.time else 'not specified'}
    Customer: {entities.customer_name if entities.customer_name else 'not specified'}
    Status: {entities.status if entities.status else 'not specified'}
    Original query: {user_input}"""

    return system_prompt, user_message
