import logging
from typing import Any, Dict, Optional

from backend.database.connection import get_connection, get_cursor

logger = logging.getLogger(__name__)

_schema_cache: Optional[Dict[str, Any]] = None

async def load_schema() -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "tables": {},
        "foreign_keys": []
    }
    
    async with get_connection() as conn:
        cursor = await get_cursor(conn, dict_cursor=True)
        
        # Load tables and columns
        columns_query = """
            SELECT COLUMN_NAME, TABLE_NAME, DATA_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() 
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
        await cursor.execute(columns_query)
        columns = await cursor.fetchall()
        
        for row in columns:
            table_name = row['TABLE_NAME']
            column_name = row['COLUMN_NAME']
            data_type = row['DATA_TYPE']
            
            if table_name not in schema["tables"]:
                schema["tables"][table_name] = {
                    "columns": [],
                    "column_types": {}
                }
                
            schema["tables"][table_name]["columns"].append(column_name)
            schema["tables"][table_name]["column_types"][column_name] = data_type
            
        # Load foreign keys
        fk_query = """
            SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
        """
        await cursor.execute(fk_query)
        foreign_keys = await cursor.fetchall()
        
        for row in foreign_keys:
            schema["foreign_keys"].append({
                "table": row['TABLE_NAME'],
                "column": row['COLUMN_NAME'],
                "ref_table": row['REFERENCED_TABLE_NAME'],
                "ref_column": row['REFERENCED_COLUMN_NAME']
            })
            
    return schema

def format_schema_for_prompt(schema: Dict[str, Any]) -> str:
    lines = []
    
    # Pre-process foreign keys for quick lookup
    fk_map = {}
    for fk in schema.get("foreign_keys", []):
        key = (fk["table"], fk["column"])
        fk_map[key] = f"references {fk['ref_table']}.{fk['ref_column']}"
        
    for table_name, table_info in schema.get("tables", {}).items():
        lines.append(f"Table: {table_name}")
        
        for column_name in table_info.get("columns", []):
            data_type = table_info.get("column_types", {}).get(column_name, "unknown")
            fk_info = fk_map.get((table_name, column_name))
            
            line = f"  - {column_name} ({data_type})"
            if fk_info:
                line += f" → {fk_info}"
            lines.append(line)
            
        lines.append("")  # Empty line after each table
        
    return "\n".join(lines).strip()

async def get_schema() -> Dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = await load_schema()
    return _schema_cache

async def refresh_schema() -> Dict[str, Any]:
    global _schema_cache
    _schema_cache = None
    return await get_schema()
