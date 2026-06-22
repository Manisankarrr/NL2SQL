from backend.nlp.intent_classifier import SQLIntent
from backend.nlp.entity_extractor import ExtractedEntities
from backend.planner.decomposition import QueryPlan, create_query_plan
from backend.middleware.logger import pipeline_logger

async def plan_query(user_query: str, intent: SQLIntent, entities: ExtractedEntities, schema: dict) -> QueryPlan:
    pipeline_logger.step("Starting query planning phase")
    plan = await create_query_plan(user_query, intent, entities, schema)
    
    pipeline_logger.result(f"Query plan created: Complexity={plan.complexity}, Type={plan.query_type}")
    if plan.complexity == "COMPLEX":
        pipeline_logger.step(f"Plan involves tables: {', '.join(plan.required_tables)}")

    pipeline_logger.stage(
        f"Query plan built · {plan.complexity} · "
        f"{plan.query_type}"
    )
    return plan

def format_plan_for_prompt(query_plan: QueryPlan) -> str:
    tables_str = ", ".join(query_plan.required_tables)
    joins_str = "\n".join(query_plan.required_joins)
    
    steps_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(query_plan.reasoning_steps))
    
    return f"""
QUERY ANALYSIS:
Type: {query_plan.query_type}
Tables needed: {tables_str}
{joins_str}

REASONING STEPS:
{steps_str}
"""
