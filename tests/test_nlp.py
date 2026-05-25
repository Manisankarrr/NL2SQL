from backend.nlp.intent_classifier import classify_intent, SQLIntent
from backend.nlp.entity_extractor import extract_entities, extract_time, extract_date


def test_select_intent():
    """'Show' triggers SELECT"""
    assert classify_intent("Show all appointments for today") == SQLIntent.SELECT


def test_insert_intent():
    """'Add' triggers INSERT"""
    assert classify_intent("Add appointment for Rahul at 5 PM") == SQLIntent.INSERT


def test_delete_intent():
    """'Cancel' triggers DELETE"""
    assert classify_intent("Cancel Ravi's appointment") == SQLIntent.DELETE


def test_update_intent():
    """'Update' triggers UPDATE"""
    assert classify_intent("Update Priya appointment to 7 PM") == SQLIntent.UPDATE


def test_unknown_intent():
    """Unrecognised input returns UNKNOWN"""
    assert classify_intent("Hello there how are you") == SQLIntent.UNKNOWN


def test_extract_time_pm():
    """'5 PM' converts to 17:00:00"""
    t, _ = extract_time("appointment at 5 PM tomorrow")
    assert t == "17:00:00"


def test_extract_time_am():
    """'9 AM' converts to 09:00:00"""
    t, _ = extract_time("at 9 AM")
    assert t == "09:00:00"


def test_extract_time_24h():
    """24h time '17:30' converts to 17:30:00"""
    t, _ = extract_time("at 17:30")
    assert t == "17:30:00"


def test_extract_date_not_none():
    """'tomorrow' resolves to a non-None date string"""
    d, _ = extract_date("appointment tomorrow")
    assert d is not None


def test_extract_customer_for():
    """'for Rahul' extracts customer name Rahul"""
    e = extract_entities("Add appointment for Rahul tomorrow at 5 PM")
    assert e.customer_name == "Rahul"


def test_extract_customer_possessive():
    """'Ravi's appointment' extracts Ravi"""
    e = extract_entities("Cancel Ravi's appointment")
    assert e.customer_name == "Ravi"


def test_extract_status_cancelled():
    """'cancelled' extracted as status"""
    e = extract_entities("show all cancelled appointments")
    assert e.status == "cancelled"
