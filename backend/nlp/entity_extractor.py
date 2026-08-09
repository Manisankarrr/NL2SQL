import re
import dateparser
from dateparser.search import search_dates
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class ExtractedEntities:
    customer_name: Optional[str] = None
    barber_name: Optional[str] = None
    service_name: Optional[str] = None
    date: Optional[str] = None        # ISO: YYYY-MM-DD
    time: Optional[str] = None        # 24h: HH:MM:SS
    status: Optional[str] = None
    raw_date_text: Optional[str] = None
    raw_time_text: Optional[str] = None

DATE_TRIGGER_WORDS = [
    "today", "tomorrow", "yesterday", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday",
    "next", "last", "this week", "this month", "january",
    "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep",
    "oct", "nov", "dec", "morning", "evening", "night",
    "tonight", "weekend", "/", "-"
]

def _has_date_reference(text: str) -> bool:
    text_lower = text.lower()
    return any(word in text_lower for word in DATE_TRIGGER_WORDS)

def extract_date(text: str) -> Tuple[Optional[str], Optional[str]]:
    if not _has_date_reference(text):
        return None, None

    settings = {"PREFER_DATES_FROM": "future", "RETURN_AS_TIMEZONE_AWARE": False}
    
    # search_dates is more robust for finding dates inside a sentence
    dates = search_dates(text, settings=settings)
    if dates:
        matched_text, dt = dates[0]
        return dt.strftime("%Y-%m-%d"), matched_text
        
    # fallback to just parse if search_dates didn't catch it
    parsed = dateparser.parse(text, settings=settings)
    if parsed:
        return parsed.strftime("%Y-%m-%d"), text
        
    return None, None

def extract_time(text: str) -> Tuple[Optional[str], Optional[str]]:
    pattern = r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|AM|PM)?\b'
    match = re.search(pattern, text)
    if match:
        matched_text = match.group(0)
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = (match.group(3) or "").lower()
        
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
            
        return f"{hour:02d}:{minute:02d}:00", matched_text
        
    return None, None

def extract_customer_name(text: str) -> Optional[str]:
    patterns = [
        r'for\s+([A-Z][a-z]+)',
        r"([A-Z][a-z]+)'s",
        r"([A-Z][a-z]+)'s\s+appointment",
        r'of\s+([A-Z][a-z]+)',
        r'(?:cancel|show|update|reschedule|book|add|list|get|find|delete)\s+(?:duplicate\s+|all\s+)?([A-Z][a-z]+)',
        r'^([A-Z][a-z]+)\s+appointment'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
            
    # Pattern 6
    EXCLUDE_WORDS = {
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
        "Saturday", "Sunday", "January", "February", "March",
        "April", "June", "July", "August", "September", "October",
        "November", "December", "Show", "List", "Find", "Get",
        "Cancel", "Update", "Add", "Book", "Delete", "What", 
        "When", "Where", "How", "Which", "The", "This", "That"
    }
    
    words = text.split()
    for word in words:
        clean = re.sub(r"[^a-zA-Z]", "", word)
        if (clean and clean[0].isupper() and 
            clean[1:].islower() and 
            len(clean) >= 3 and 
            clean not in EXCLUDE_WORDS):
            return clean
            
    return None

def extract_status(text: str) -> Optional[str]:
    text_lower = text.lower()
    if re.search(r'\bcancell?ed\b', text_lower):
        return "cancelled"
    if re.search(r'\bcompleted\b', text_lower):
        return "completed"
    if re.search(r'\bscheduled\b', text_lower):
        return "scheduled"
    return None

def extract_entities(text: str) -> ExtractedEntities:
    date_str, date_raw = extract_date(text)
    time_str, time_raw = extract_time(text)
    customer = extract_customer_name(text)
    status = extract_status(text)
    
    return ExtractedEntities(
        customer_name=customer,
        date=date_str,
        time=time_str,
        status=status,
        raw_date_text=date_raw,
        raw_time_text=time_raw
    )
