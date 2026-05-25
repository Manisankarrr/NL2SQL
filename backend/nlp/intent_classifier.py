import re
from enum import Enum

class SQLIntent(str, Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UNKNOWN = "UNKNOWN"

INTENT_PATTERNS = {
    SQLIntent.SELECT: ["show", "list", "get", "find", "what", "how many", "count", "display", "fetch", "give me", "see"],
    SQLIntent.INSERT: ["add", "book", "create", "schedule", "new", "set up", "register", "make an"],
    SQLIntent.UPDATE: ["update", "change", "move", "reschedule", "modify", "edit", "shift", "change"],
    SQLIntent.DELETE: ["cancel", "delete", "remove"]
}

def classify_intent(text: str) -> SQLIntent:
    text_lower = text.lower()
    scores = {intent: 0 for intent in SQLIntent}
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(r'\b' + re.escape(pattern) + r'\b', text_lower):
                scores[intent] += 1
                
    if all(score == 0 for score in scores.values()):
        return SQLIntent.UNKNOWN
        
    tie_break_order = [SQLIntent.INSERT, SQLIntent.UPDATE, SQLIntent.DELETE, SQLIntent.SELECT]
    max_score = max(scores.values())
    
    for intent in tie_break_order:
        if scores[intent] == max_score and max_score > 0:
            return intent
            
    return SQLIntent.UNKNOWN

def is_write_operation(intent: SQLIntent) -> bool:
    return intent in (SQLIntent.INSERT, SQLIntent.UPDATE, SQLIntent.DELETE)
