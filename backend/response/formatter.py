from backend.nlp.intent_classifier import SQLIntent
from backend.database.executor import ExecutionResult
from backend.nlp.entity_extractor import ExtractedEntities
from typing import Optional


def format_select_result(result: ExecutionResult, user_query: str) -> dict:
    if not result.success:
        return {"message": f"Query failed: {result.error}", "table": [], "count": 0, "columns": []}
    if len(result.rows) == 0:
        return {"message": "No records found matching your request.", "table": [], "count": 0, "columns": result.columns}
    count = len(result.rows)
    message = f"Found {count} appointment{'s' if count != 1 else ''}."
    return {"message": message, "table": result.rows, "count": count, "columns": result.columns}


def format_insert_result(result: ExecutionResult, entities: Optional[ExtractedEntities] = None) -> dict:
    if not result.success:
        return {"message": f"Failed to create appointment: {result.error}", "affected_rows": 0}
    if result.affected_rows == 0:
        name = entities.customer_name if entities and entities.customer_name else "the customer"
        date_str = f" on {entities.date}" if entities and entities.date else ""
        time_str = f" at {entities.time}" if entities and entities.time else ""
        return {
            "message": (
                f"Could not book appointment for {name}{date_str}{time_str}. "
                f"This time slot may already be taken — another appointment exists "
                f"within 1 hour of this time. Try a different time slot."
            ),
            "affected_rows": 0
        }
    name = entities.customer_name if entities and entities.customer_name else "the customer"
    date_str = f" on {entities.date}" if entities and entities.date else ""
    time_str = f" at {entities.time}" if entities and entities.time else ""
    return {
        "message": f"Appointment booked for {name}{date_str}{time_str}.",
        "affected_rows": result.affected_rows
    }

def format_update_result(result: ExecutionResult, entities: Optional[ExtractedEntities] = None) -> dict:
    if not result.success:
        return {"message": f"Update failed: {result.error}", "affected_rows": 0}
    if result.affected_rows == 0:
        customer = getattr(entities, "customer_name", None) if entities else None
        name_part = f" for {customer}" if customer else ""
        return {
            "message": (
                f"No upcoming appointment found{name_part}. "
                f"It may already be completed or cancelled. "
                f"Try 'show all appointments' to check current status."
            ),
            "affected_rows": 0
        }
    n = result.affected_rows
    return {"message": f"Updated {n} appointment{'s' if n != 1 else ''} successfully.", "affected_rows": n}


def format_delete_result(result: ExecutionResult, entities: Optional[ExtractedEntities] = None) -> dict:
    if not result.success:
        return {"message": f"Cancellation failed: {result.error}", "affected_rows": 0}
    if result.affected_rows == 0:
        customer = getattr(entities, "customer_name", None) if entities else None
        name_part = f" for {customer}" if customer else ""
        return {
            "message": (
                f"No matching appointment found{name_part}. "
                f"It may already be cancelled or completed. "
                f"Try 'show all appointments' to see current status."
            ),
            "affected_rows": 0
        }
    n = result.affected_rows
    return {"message": f"Cancelled {n} appointment{'s' if n != 1 else ''}.", "affected_rows": n}


def format_error(error_message: str, sql: Optional[str] = None) -> dict:
    return {
        "message": f"I couldn't process that request. {error_message}",
        "error": True,
        "sql": sql,
        "table": [],
        "count": 0,
        "affected_rows": 0
    }


def format_response(
    intent: SQLIntent,
    result: ExecutionResult,
    user_query: str,
    entities: Optional[ExtractedEntities],
    sql: str
) -> dict:
    if intent == SQLIntent.SELECT:
        result_dict = format_select_result(result, user_query)
    elif intent == SQLIntent.INSERT:
        result_dict = format_insert_result(result, entities)
    elif intent == SQLIntent.UPDATE:
        result_dict = format_update_result(result, entities)
    elif intent == SQLIntent.DELETE:
        result_dict = format_delete_result(result, entities)
    else:
        result_dict = format_error("Unknown intent", sql)

    result_dict["sql_used"] = sql
    result_dict["execution_time_ms"] = result.execution_time_ms
    result_dict["intent"] = intent.value
    return result_dict