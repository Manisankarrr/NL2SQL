import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    ok: bool
    reason: Optional[str] = None      # None if ok=True
    risk_level: str = "none"           # "none", "low", "medium", "high"
    cleaned_sql: Optional[str] = None  # SQL after cleanup, only if ok=True

BLOCKED_KEYWORDS = {
    "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE", "LOAD_FILE", "INTO OUTFILE", "INTO DUMPFILE",
    "BENCHMARK", "SLEEP", "INFORMATION_SCHEMA"
}

ALLOWED_FIRST_WORDS = {"SELECT", "INSERT", "UPDATE", "DELETE"}
MAX_SQL_LENGTH = 2000


def _strip_sql(sql: str) -> str:
    """
    Remove ```sql, ```, leading/trailing whitespace.
    Remove trailing semicolons then add exactly one back.
    Return clean SQL.
    """
    # Remove markdown codeblocks
    cleaned = re.sub(r'^```(?:sql)?\s*', '', sql, flags=re.IGNORECASE)
    cleaned = re.sub(r'```\s*$', '', cleaned)
    
    # Strip leading/trailing whitespace
    cleaned = cleaned.strip()
    
    # Remove trailing semicolons
    while cleaned.endswith(';'):
        cleaned = cleaned[:-1].strip()
        
    # Add exactly one back
    cleaned += ';'
    return cleaned


def _extract_table_names(sql: str) -> set[str]:
    """
    Use regex to find table names after: FROM, JOIN, INTO, UPDATE keywords.
    Pattern: r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([`"]?(\w+)[`"]?)'
    Return set of lowercased table name strings.
    """
    pattern = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+([`"]?(\w+)[`"]?)', re.IGNORECASE)
    matches = pattern.findall(sql)
    return {match[1].lower() for match in matches if match[1]}


def validate_sql(sql: str, schema: dict, expected_intent: Optional[str] = None) -> ValidationResult:
    # CHECK 1 — Empty check:
    if sql.strip() == "":
        return ValidationResult(ok=False, reason="LLM returned empty SQL", risk_level="high")

    # CHECK 2 — Length check:
    if len(sql) > MAX_SQL_LENGTH:
        return ValidationResult(ok=False, reason=f"SQL too long ({len(sql)} chars)", risk_level="high")

    # CHECK 3 — Blocked keywords:
    sql_upper = sql.upper()
    for keyword in BLOCKED_KEYWORDS:
        if keyword in sql_upper:
            return ValidationResult(ok=False, reason=f"Blocked dangerous keyword: {keyword}", risk_level="high")

    clean_sql = _strip_sql(sql)

    # CHECK 4 — Multiple statements:
    # Strip the SQL, if ";" appears more than once after stripping:
    if clean_sql.count(";") > 1:
        return ValidationResult(ok=False, reason="Multiple SQL statements not allowed", risk_level="high")

    # CHECK 5 — First word check:
    # Using clean_sql handles markdown prefixes. rstrip(';') handles single-word queries like 'SELECT;'
    first_word = clean_sql.strip().upper().split()[0].rstrip(';')
    if first_word not in ALLOWED_FIRST_WORDS:
        return ValidationResult(ok=False, reason=f"Operation not allowed: {first_word}", risk_level="high")

    # CHECK 6 — WHERE requirement:
    if first_word in {"UPDATE", "DELETE"} and "WHERE" not in sql.upper():
        return ValidationResult(ok=False, reason=f"{first_word} without WHERE clause is not allowed — too dangerous", risk_level="high")

    # CHECK 7 — Table validation:
    tables = _extract_table_names(sql)
    for table in tables:
        if table not in schema.get("tables", {}):
            return ValidationResult(
                ok=False, 
                reason=f"Unknown table referenced: '{table}'. Valid tables: {list(schema.get('tables', {}).keys())}", 
                risk_level="medium"
            )

    # CHECK 8 — Intent mismatch:
    if expected_intent is not None and first_word != expected_intent.upper():
        return ValidationResult(ok=False, reason=f"Expected {expected_intent} but LLM generated {first_word}", risk_level="medium")

    # If all checks pass:
    return ValidationResult(ok=True, risk_level="none", cleaned_sql=clean_sql)


def get_user_friendly_error(result: ValidationResult) -> str:
    """Maps result.reason to a user-friendly message string."""
    if result.ok:
        return "Query is valid."
        
    reason = result.reason or ""
    
    if "Blocked dangerous keyword" in reason:
        return "That request would require a dangerous database operation. I can only run safe queries."
    elif "without WHERE clause" in reason:
        return "I generated a query that could affect all records. Please be more specific."
    elif "Unknown table" in reason:
        return "I tried to access a table that doesn't exist. Try rephrasing your request."
        
    return "I couldn't generate a safe query. Try rephrasing."
