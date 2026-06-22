

import logging
from typing import Optional

from backend.reasoning.ambiguity_detector import AmbiguitySignal

logger = logging.getLogger(__name__)


_COLUMN_LABEL_MAP: dict[str, str] = {
    # Common barber-shop column names → human-readable labels
    "appointment_date":  "By appointment date",
    "appointment_time":  "By appointment time",
    "created_at":        "By creation date",
    "updated_at":        "By last updated",
    "price":             "By price",
    "amount":            "By amount",
    "duration":          "By duration",
    "id":                "By record ID",
    "customer_id":       "By customer",
    "barber_id":         "By barber",
    "service_id":        "By service",
    "status":            "By status",
    "name":              "By name",
}


def _humanise_column(col_name: str) -> str:
    """
    Convert a raw column name to a human-readable label.
    Falls back to title-casing the column name with underscores replaced.
    """
    return _COLUMN_LABEL_MAP.get(col_name, col_name.replace("_", " ").title())



def generate_clarification_question(
    signal: AmbiguitySignal,
    original_query: str,
    schema: dict,
) -> dict:
    """
    Convert an AmbiguitySignal into a clarification question dict.

    Returns:
        {
            "question":           str,
            "options":            list[str] | None,
            "requires_free_text": bool,
        }
    """
    ambiguity_type = signal.ambiguity_type or "CLEAR"

    # ---- COLUMN_AMBIGUITY ------------------------------------------------ #
    if ambiguity_type == "COLUMN_AMBIGUITY":
        term = signal.ambiguous_term or "that"
        options = [_humanise_column(c) for c in signal.candidate_interpretations]
        question = (
            f"I'm not sure how you want to sort or filter by \"{term}\". "
            f"Which of these did you mean?"
        )
        return {
            "question": question,
            "options": options if options else None,
            "requires_free_text": False,
        }

    # ---- FILTER_MISSING -------------------------------------------------- #
    elif ambiguity_type == "FILTER_MISSING":
        missing = signal.ambiguous_term or "the required detail"
        question = (
            f"To complete your request, I need to know {missing}. "
            f"Please provide it."
        )
        return {
            "question": question,
            "options": None,
            "requires_free_text": True,
        }

    # ---- TEMPORAL_VAGUE -------------------------------------------------- #
    elif ambiguity_type == "TEMPORAL_VAGUE":
        term = signal.ambiguous_term or "that time"
        options = signal.candidate_interpretations or ["today", "this week", "next 7 days"]
        question = (
            f'When you said "{term}", which time range did you mean?'
        )
        return {
            "question": question,
            "options": options,
            "requires_free_text": False,
        }

    # ---- SCOPE_UNCLEAR --------------------------------------------------- #
    elif ambiguity_type == "SCOPE_UNCLEAR":
        question = (
            "Your request is a bit broad. Could you be more specific about "
            "which records you're referring to?"
        )
        return {
            "question": question,
            "options": None,
            "requires_free_text": True,
        }

    # ---- CLEAR / default ------------------------------------------------- #
    else:
        logger.debug("generate_clarification_question called with CLEAR signal — no question needed")
        return {
            "question": "",
            "options": None,
            "requires_free_text": False,
        }


def format_clarification_response(clarification: dict) -> str:
    """
    Render a clarification dict as a user-facing string.

    If options are present: numbered list.
    Always ends with an instruction to reply with a number or describe freely.
    """
    question: str = clarification.get("question", "")
    options: Optional[list[str]] = clarification.get("options")
    requires_free_text: bool = clarification.get("requires_free_text", False)

    if not question:
        return ""

    lines: list[str] = [question]

    if options:
        lines.append("")  # blank line before the list
        for i, opt in enumerate(options, start=1):
            lines.append(f"  {i}. {opt}")
        lines.append("")
        lines.append("Reply with a number to choose, or describe what you meant.")
    elif requires_free_text:
        lines.append("Please type your answer.")

    return "\n".join(lines)
