"""
backend/reasoning/ambiguity_detector.py

Classifies incoming NL queries as ambiguous or clear before SQL
generation, returning structured signals that the clarification layer
acts on.

Real interfaces confirmed from source:

  ExtractedEntities (entity_extractor.py) fields:
      customer_name: Optional[str]
      barber_name:   Optional[str]
      service_name:  Optional[str]
      date:          Optional[str]   # ISO YYYY-MM-DD
      time:          Optional[str]   # 24h HH:MM:SS
      status:        Optional[str]
      raw_date_text: Optional[str]
      raw_time_text: Optional[str]

  SQLIntent (intent_classifier.py) values:
      SELECT, INSERT, UPDATE, DELETE, UNKNOWN
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from backend.nlp.intent_classifier import SQLIntent
from backend.nlp.entity_extractor import ExtractedEntities
from backend.middleware.logger import pipeline_logger

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAGUE_SUPERLATIVES: list[str] = [
    "top", "best", "most", "highest", "lowest",
    "recent", "latest", "expensive", "cheap",
    "popular", "frequent",
]

VAGUE_TEMPORAL: list[str] = [
    "sometime", "soon", "recently", "a while ago",
    "later", "eventually", "next available",
]


# ---------------------------------------------------------------------------
# Signal dataclass
# ---------------------------------------------------------------------------

@dataclass
class AmbiguitySignal:
    is_ambiguous: bool
    ambiguity_type: Optional[str] = None   # COLUMN_AMBIGUITY | FILTER_MISSING |
                                            # TEMPORAL_VAGUE | SCOPE_UNCLEAR | CLEAR
    ambiguous_term: Optional[str] = None
    candidate_interpretations: list[str] = field(default_factory=list)
    confidence_that_ambiguous: float = 0.0


# ---------------------------------------------------------------------------
# Detector helpers
# ---------------------------------------------------------------------------

def _find_vague_superlative(user_query: str) -> Optional[str]:
    """Return the first vague superlative found in user_query, or None."""
    lower = user_query.lower()
    for term in VAGUE_SUPERLATIVES:
        if re.search(r'\b' + re.escape(term) + r'\b', lower):
            return term
    return None


def _find_vague_temporal(user_query: str) -> Optional[str]:
    """Return the first vague temporal expression found, or None."""
    lower = user_query.lower()
    for term in VAGUE_TEMPORAL:
        if term in lower:          # multi-word phrases — substring check is correct here
            return term
    return None


def _collect_orderable_columns(schema: dict) -> list[str]:
    """
    Return column names from schema that are plausible ordering/filtering
    targets (numeric, date, or name-like columns).

    Schema shape: schema["tables"][table]["columns"] → list[str]
                  schema["tables"][table]["column_types"] → dict[str, str]
    """
    orderable: list[str] = []
    orderable_types = {"int", "bigint", "smallint", "tinyint", "decimal",
                       "float", "double", "date", "datetime", "timestamp",
                       "time", "year"}
    for table_info in schema.get("tables", {}).values():
        col_types: dict[str, str] = table_info.get("column_types", {})
        for col_name in table_info.get("columns", []):
            dtype = col_types.get(col_name, "").lower()
            if dtype in orderable_types or "price" in col_name or "amount" in col_name:
                orderable.append(col_name)
    return orderable


# ---------------------------------------------------------------------------
# Public detectors
# ---------------------------------------------------------------------------

def detect_column_ambiguity(
    user_query: str,
    schema: dict,
    intent: SQLIntent,
) -> Optional[AmbiguitySignal]:
    """
    If a vague superlative is found AND multiple schema columns could satisfy
    the implied ordering/filtering, return COLUMN_AMBIGUITY.
    Returns None if no ambiguity detected.
    """
    vague_term = _find_vague_superlative(user_query)
    if vague_term is None:
        return None

    candidates = _collect_orderable_columns(schema)
    if len(candidates) < 2:
        # Only one candidate — not genuinely ambiguous
        return None

    return AmbiguitySignal(
        is_ambiguous=True,
        ambiguity_type="COLUMN_AMBIGUITY",
        ambiguous_term=vague_term,
        candidate_interpretations=candidates,
        confidence_that_ambiguous=0.75,
    )


def detect_filter_ambiguity(
    user_query: str,
    entities: ExtractedEntities,
    intent: SQLIntent,
) -> Optional[AmbiguitySignal]:
    """
    Detect cases where a write operation is missing a critical identifying
    entity, making the query dangerously under-specified.

    Uses the real ExtractedEntities fields:
      customer_name, date, time  (all Optional[str])

    Rules:
      INSERT with no customer_name → FILTER_MISSING
      UPDATE with no date AND no time  → FILTER_MISSING
      DELETE with no customer_name  → FILTER_MISSING
    """
    if intent == SQLIntent.INSERT:
        if entities.customer_name is None:
            return AmbiguitySignal(
                is_ambiguous=True,
                ambiguity_type="FILTER_MISSING",
                ambiguous_term="customer name",
                candidate_interpretations=[],
                confidence_that_ambiguous=0.85,
            )

    elif intent == SQLIntent.UPDATE:
        if entities.date is None and entities.time is None:
            return AmbiguitySignal(
                is_ambiguous=True,
                ambiguity_type="FILTER_MISSING",
                ambiguous_term="appointment time / date",
                candidate_interpretations=[],
                confidence_that_ambiguous=0.80,
            )

    elif intent == SQLIntent.DELETE:
        if entities.customer_name is None:
            # Fallback check against raw user_query text
            EXCLUDE_WORDS = {
                "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                "Saturday", "Sunday", "January", "February", "March",
                "April", "June", "July", "August", "September", "October",
                "November", "December", "Show", "List", "Find", "Get",
                "Cancel", "Update", "Add", "Book", "Delete", "What", 
                "When", "Where", "How", "Which", "The", "This", "That"
            }
            has_potential_name = False
            words = user_query.split()
            for word in words:
                clean = re.sub(r"[^a-zA-Z]", "", word)
                if (clean and clean[0].isupper() and 
                    clean[1:].islower() and 
                    len(clean) >= 3 and 
                    clean not in EXCLUDE_WORDS):
                    has_potential_name = True
                    break
            
            confidence = 0.4 if has_potential_name else 0.55
            return AmbiguitySignal(
                is_ambiguous=True,
                ambiguity_type="FILTER_MISSING",
                ambiguous_term="customer name",
                candidate_interpretations=[],
                confidence_that_ambiguous=confidence,
            )

    return None


def detect_temporal_ambiguity(user_query: str) -> Optional[AmbiguitySignal]:
    """
    If a vague temporal expression is found, return TEMPORAL_VAGUE.
    Returns None otherwise.
    """
    vague_term = _find_vague_temporal(user_query)
    if vague_term is None:
        return None

    return AmbiguitySignal(
        is_ambiguous=True,
        ambiguity_type="TEMPORAL_VAGUE",
        ambiguous_term=vague_term,
        candidate_interpretations=["today", "this week", "next 7 days"],
        confidence_that_ambiguous=0.70,
    )


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

def analyze_ambiguity(
    user_query: str,
    intent: SQLIntent,
    entities: ExtractedEntities,
    schema: dict,
) -> AmbiguitySignal:
    """
    Run all three detectors and return the highest-confidence signal.
    If none fires, return a CLEAR signal.
    """
    candidates: list[AmbiguitySignal] = []

    col_sig = detect_column_ambiguity(user_query, schema, intent)
    if col_sig:
        candidates.append(col_sig)

    filter_sig = detect_filter_ambiguity(user_query, entities, intent)
    if filter_sig:
        candidates.append(filter_sig)

    temporal_sig = detect_temporal_ambiguity(user_query)
    if temporal_sig:
        candidates.append(temporal_sig)

    if not candidates:
        logger.debug("analyze_ambiguity: CLEAR for query=%r intent=%s", user_query[:60], intent)
        _clear = AmbiguitySignal(
            is_ambiguous=False,
            ambiguity_type="CLEAR",
            confidence_that_ambiguous=0.0,
        )
        pipeline_logger.ambiguity(
            _clear.ambiguity_type or "CLEAR",
            _clear.is_ambiguous,
            _clear.confidence_that_ambiguous,
            _clear.ambiguous_term,
        )
        return _clear

    # Return highest-confidence signal
    best = max(candidates, key=lambda s: s.confidence_that_ambiguous)
    if best.confidence_that_ambiguous < 0.6:
        _clear = AmbiguitySignal(
            is_ambiguous=False,
            ambiguity_type="CLEAR",
            confidence_that_ambiguous=0.0,
        )
        pipeline_logger.ambiguity(
            _clear.ambiguity_type or "CLEAR",
            _clear.is_ambiguous,
            _clear.confidence_that_ambiguous,
            _clear.ambiguous_term,
        )
        return _clear

    logger.debug(
        "analyze_ambiguity: %s (confidence=%.2f) for query=%r",
        best.ambiguity_type, best.confidence_that_ambiguous, user_query[:60],
    )
    pipeline_logger.ambiguity(
        best.ambiguity_type or "CLEAR",
        best.is_ambiguous,
        best.confidence_that_ambiguous,
        best.ambiguous_term,
    )
    return best
