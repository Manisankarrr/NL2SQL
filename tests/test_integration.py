import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from backend.main import app

MOCK_SCHEMA = {
    "tables": {
        "appointments": {
            "columns": ["id","customer_id","appointment_date","appointment_time","status"]
        },
        "customers": {"columns": ["id","name","phone"]}
    },
    "foreign_keys": []
}


@pytest.fixture(autouse=True)
def mock_db_and_schema():
    """Automatically mock database connection pool and schema loader globally for all tests."""
    with patch("backend.database.connection.create_pool") as mock_create, \
         patch("backend.database.connection.close_pool") as mock_close, \
         patch("backend.database.schema_loader.load_schema", new_callable=AsyncMock) as mock_load_schema:
        
        mock_load_schema.return_value = MOCK_SCHEMA
        yield



@pytest.mark.asyncio
async def test_health_endpoint():
    """Test the API health status endpoint returns 200 and details."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "openrouter" in data
    assert "groq" in data


@pytest.mark.asyncio
async def test_select_query_pipeline():
    """Test a SELECT intent query pipeline through integration."""
    with patch("backend.routers.query.generate_sql", new_callable=AsyncMock) as mock_gen, \
         patch("backend.routers.query.execute_sql", new_callable=AsyncMock) as mock_exec:
        
        mock_gen.return_value = {
            "sql": "SELECT * FROM appointments LIMIT 50;",
            "provider": "openrouter",
            "model": "llama-3.3-70b"
        }
        
        # Mock DB execution
        from backend.database.executor import ExecutionResult
        mock_exec.return_value = ExecutionResult(
            success=True, 
            rows=[], 
            columns=["id", "customer_id", "appointment_date", "appointment_time", "status"]
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/query", json={"user_input": "show all appointments"})
            
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "SELECT"
    assert data["error"] is False


@pytest.mark.asyncio
async def test_insert_query_pipeline():
    """Test an INSERT intent query pipeline through integration."""
    with patch("backend.routers.query.generate_sql", new_callable=AsyncMock) as mock_gen, \
         patch("backend.routers.query.execute_sql", new_callable=AsyncMock) as mock_exec:
        
        mock_gen.return_value = {
            "sql": "INSERT INTO appointments (customer_id, appointment_date, appointment_time, status) VALUES (1, '2026-05-23', '17:00:00', 'scheduled');",
            "provider": "openrouter",
            "model": "llama-3.3-70b"
        }
        
        # Mock DB execution
        from backend.database.executor import ExecutionResult
        mock_exec.return_value = ExecutionResult(success=True, affected_rows=1)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/query", json={"user_input": "add appointment for Rahul tomorrow at 5 PM"})
            
    data = response.json()
    assert data["intent"] == "INSERT"


@pytest.mark.asyncio
async def test_dangerous_sql_blocked():
    """Test that a dangerous SQL statement gets blocked by validation."""
    with patch("backend.routers.query.generate_sql", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "sql": "DROP TABLE appointments;",
            "provider": "openrouter",
            "model": "test"
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/query", json={"user_input": "show appointments"})
            
    data = response.json()
    assert data["error"] is True
    assert "dangerous" in data["message"].lower() or "blocked" in data["message"].lower()


@pytest.mark.asyncio
async def test_unknown_intent_handled():
    """Test that unknown intents bypass LLM/SQL execution and return help tips."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/query", json={"user_input": "Hello there how are you today"})
        
    data = response.json()
    assert data["intent"] == "UNKNOWN"
    assert "Try:" in data["message"]



@pytest.mark.asyncio
async def test_update_without_where_blocked():
    """Test that an UPDATE without a WHERE clause gets blocked by safety validator."""
    with patch("backend.routers.query.generate_sql", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {
            "sql": "UPDATE appointments SET status='cancelled';",
            "provider": "openrouter",
            "model": "test"
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/query", json={"user_input": "cancel all appointments"})
            
    data = response.json()
    assert data["error"] is True
