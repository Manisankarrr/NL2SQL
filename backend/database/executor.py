import datetime
import decimal
from backend.database.connection import get_connection, get_cursor
from backend.config import settings
from dataclasses import dataclass, field
from typing import Optional
import aiomysql, logging, time

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    success: bool
    rows: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    affected_rows: int = 0
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    sql_used: str = ""


def _convert_timedelta(value) -> str:
    total = int(value.total_seconds())
    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _serialize_row(row: dict) -> dict:
    new_row = {}
    for k, v in row.items():
        if isinstance(v, datetime.timedelta):
            new_row[k] = _convert_timedelta(v)
        elif isinstance(v, datetime.datetime):
            new_row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(v, datetime.date):
            new_row[k] = v.strftime("%Y-%m-%d")
        elif isinstance(v, datetime.time):
            new_row[k] = v.strftime("%H:%M:%S")
        elif isinstance(v, decimal.Decimal):
            new_row[k] = float(v)
        else:
            new_row[k] = v
    return new_row


async def execute_select(sql: str) -> ExecutionResult:
    start = time.perf_counter()
    try:
        async with get_connection() as conn:
            cursor = await get_cursor(conn, dict_cursor=True)
            await cursor.execute(sql)
            raw_rows = await cursor.fetchmany(settings.max_result_rows)
            rows = [_serialize_row(dict(row)) for row in raw_rows]
            columns = [d[0] for d in cursor.description] if cursor.description else []
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            logger.info(f"SELECT executed in {elapsed}ms, {len(rows)} rows")
            return ExecutionResult(success=True, rows=rows, columns=columns, execution_time_ms=elapsed, sql_used=sql)
    except aiomysql.Error as e:
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.error(f"SELECT failed: {e}")
        return ExecutionResult(success=False, error=str(e), execution_time_ms=elapsed, sql_used=sql)


async def execute_write(sql: str) -> ExecutionResult:
    start = time.perf_counter()
    try:
        async with get_connection() as conn:
            cursor = await get_cursor(conn, dict_cursor=False)
            try:
                await cursor.execute(sql)
                await conn.commit()
            except aiomysql.Error:
                try:
                    await conn.rollback()
                except Exception:
                    pass
                raise
            affected = cursor.rowcount
            elapsed = round((time.perf_counter() - start) * 1000, 2)
            logger.info(f"WRITE executed in {elapsed}ms, {affected} rows affected")
            return ExecutionResult(success=True, affected_rows=affected, execution_time_ms=elapsed, sql_used=sql)
    except aiomysql.Error as e:
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.error(f"WRITE failed: {e}")
        return ExecutionResult(success=False, error=str(e), execution_time_ms=elapsed, sql_used=sql)


async def execute_sql(sql: str) -> ExecutionResult:
    first_word = sql.strip().upper().split()[0]
    if first_word == "SELECT":
        return await execute_select(sql)
    else:
        return await execute_write(sql)
