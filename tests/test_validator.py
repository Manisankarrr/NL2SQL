from backend.validation.sql_validator import validate_sql, ValidationResult

MOCK_SCHEMA = {
    "tables": {
        "appointments": {
            "columns": ["id","customer_id","barber_id","service_id",
                        "appointment_date","appointment_time","status","notes"],
            "column_types": {}
        },
        "customers": {"columns": ["id","name","phone","email"], "column_types": {}},
        "barbers": {"columns": ["id","name","specialty","is_active"], "column_types": {}},
        "services": {"columns": ["id","name","duration_minutes","price"], "column_types": {}}
    },
    "foreign_keys": []
}


def test_valid_select():
    """Valid SELECT passes validation"""
    r = validate_sql("SELECT * FROM appointments LIMIT 10;", MOCK_SCHEMA)
    assert r.ok is True


def test_valid_insert():
    """Valid INSERT passes validation"""
    r = validate_sql("INSERT INTO appointments (customer_id, appointment_date, appointment_time, status) VALUES (1, '2026-05-23', '17:00:00', 'scheduled');", MOCK_SCHEMA)
    assert r.ok is True


def test_valid_update():
    """Valid UPDATE with WHERE passes"""
    r = validate_sql("UPDATE appointments SET status='cancelled' WHERE id=1;", MOCK_SCHEMA)
    assert r.ok is True


def test_valid_delete():
    """Valid DELETE with WHERE passes"""
    r = validate_sql("DELETE FROM appointments WHERE id=1;", MOCK_SCHEMA)
    assert r.ok is True


def test_blocks_drop():
    """DROP TABLE must be blocked at high risk"""
    r = validate_sql("DROP TABLE appointments;", MOCK_SCHEMA)
    assert r.ok is False
    assert r.risk_level == "high"


def test_blocks_truncate():
    """TRUNCATE must be blocked"""
    r = validate_sql("TRUNCATE appointments;", MOCK_SCHEMA)
    assert r.ok is False


def test_blocks_alter():
    """ALTER must be blocked"""
    r = validate_sql("ALTER TABLE appointments ADD COLUMN x INT;", MOCK_SCHEMA)
    assert r.ok is False


def test_update_requires_where():
    """UPDATE without WHERE must be blocked"""
    r = validate_sql("UPDATE appointments SET status='cancelled';", MOCK_SCHEMA)
    assert r.ok is False


def test_delete_requires_where():
    """DELETE without WHERE must be blocked"""
    r = validate_sql("DELETE FROM appointments;", MOCK_SCHEMA)
    assert r.ok is False


def test_blocks_unknown_table():
    """Reference to unknown table must be blocked"""
    r = validate_sql("SELECT * FROM nonexistent_table;", MOCK_SCHEMA)
    assert r.ok is False


def test_blocks_multiple_statements():
    """Multiple statements separated by semicolon must be blocked"""
    r = validate_sql("SELECT 1; DROP TABLE appointments;", MOCK_SCHEMA)
    assert r.ok is False


def test_strips_markdown_fences():
    """SQL wrapped in markdown fences must be cleaned and pass"""
    r = validate_sql("```sql\nSELECT * FROM appointments;\n```", MOCK_SCHEMA)
    assert r.ok is True
    assert "```" not in (r.cleaned_sql or "")
