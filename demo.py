import asyncio
from backend.nlp.intent_classifier import classify_intent
from backend.nlp.entity_extractor import extract_entities
from backend.validation.sql_validator import validate_sql, get_user_friendly_error
from backend.middleware.logger import PipelineLogger

MOCK_SCHEMA = {
    "tables": {
        "appointments": {"columns": ["id","customer_id","barber_id","service_id","appointment_date","appointment_time","status","notes"]},
        "customers": {"columns": ["id","name","phone","email"]},
        "barbers": {"columns": ["id","name","specialty","is_active"]},
        "services": {"columns": ["id","name","duration_minutes","price"]}
    },
    "foreign_keys": []
}

DEMO_QUERIES = [
    ("Show all appointments for tomorrow",
     "SELECT * FROM appointments WHERE appointment_date = CURDATE() + INTERVAL 1 DAY LIMIT 50;"),
    ("Add appointment for Rahul at 5 PM tomorrow",
     "INSERT INTO appointments (customer_id, appointment_date, appointment_time, status) SELECT id, CURDATE()+INTERVAL 1 DAY, '17:00:00', 'scheduled' FROM customers WHERE name='Rahul';"),
    ("Update Priya appointment to 6 PM",
     "UPDATE appointments SET appointment_time='18:00:00' WHERE customer_id=(SELECT id FROM customers WHERE name='Priya');"),
    ("Cancel Ravi's appointment",
     "UPDATE appointments SET status='cancelled' WHERE customer_id=(SELECT id FROM customers WHERE name='Ravi');"),
    ("DROP TABLE appointments",
     "DROP TABLE appointments;")
]


async def main():
    log = PipelineLogger(app_name="BarberSQL Demo")
    log.stage("Running pipeline demo — no DB or API needed")

    for query, mock_sql in DEMO_QUERIES:
        log.step(f"Query: {query}")
        intent = classify_intent(query)
        entities = extract_entities(query)
        log.result(f"Intent: {intent.value} | Customer: {entities.customer_name} | Date: {entities.date} | Time: {entities.time}")
        validation = validate_sql(mock_sql, MOCK_SCHEMA)
        if validation.ok:
            log.ok(f"SQL validated: {validation.cleaned_sql[:60]}...")
        else:
            log.warn(f"BLOCKED: {validation.reason}")

    log.done("Demo complete")


if __name__ == "__main__":
    asyncio.run(main())
