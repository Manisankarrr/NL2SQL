from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from backend.nlp.intent_classifier import SQLIntent
from backend.nlp.entity_extractor import ExtractedEntities
from backend.retrieval.relationship_graph import build_relationship_graph, find_join_path
from backend.middleware.logger import pipeline_logger

@dataclass
class QueryPlan:
    complexity: str
    query_type: str
    primary_table: Optional[str] = None
    required_tables: List[str] = field(default_factory=list)
    required_joins: List[str] = field(default_factory=list)
    aggregation: Optional[str] = None
    group_by: List[str] = field(default_factory=list)
    order_by: Optional[str] = None
    filters: List[str] = field(default_factory=list)
    limit: Optional[int] = None
    reasoning_steps: List[str] = field(default_factory=list)

COMPLEXITY_SIGNALS = {
    "AGGREGATION": ["how many", "count", "total", "sum", "average", "most", "least", "highest", "lowest"],
    "TEMPORAL_FILTER": ["this week", "last month", "between", "since", "before", "after", "yesterday"],
    "COMPARISON": ["more than", "less than", "greater", "over", "under", "compare"],
    "MULTI_TABLE_JOIN": ["with barber", "with service", "customer name", "barber name", "service name"]
}

def classify_complexity(user_query: str) -> Tuple[str, str]:
    query_lower = user_query.lower()
    for q_type, signals in COMPLEXITY_SIGNALS.items():
        for signal in signals:
            if signal in query_lower:
                return "COMPLEX", q_type
    return "SIMPLE", "LOOKUP"

def detect_required_tables(user_query: str, entities: ExtractedEntities, schema: dict) -> List[str]:
    required = ["appointments"]
    query_lower = user_query.lower()
    
    if entities.customer_name:
        required.append("customers")
        
    if "barber" in query_lower or entities.barber_name:
        if "barbers" not in required:
            required.append("barbers")
            
    if "service" in query_lower or entities.service_name:
        if "services" not in required:
            required.append("services")
            
    return list(set(required))

def build_reasoning_steps(user_query: str, query_type: str, required_tables: List[str], entities: ExtractedEntities) -> List[str]:
    steps = []
    steps.append(f"Identify the core intent and the primary table which is appointments.")
    
    if len(required_tables) > 1:
        tables_str = ", ".join(t for t in required_tables if t != "appointments")
        steps.append(f"Join the appointments table with {tables_str} to gather all necessary data.")
        
    if entities.customer_name or entities.date or entities.time:
        filters = []
        if entities.customer_name: filters.append("customer name")
        if entities.date: filters.append("date")
        if entities.time: filters.append("time")
        steps.append(f"Apply WHERE clause filters for: {', '.join(filters)}.")
        
    if query_type == "AGGREGATION":
        steps.append("Apply aggregate functions (e.g., COUNT, SUM) to the filtered results.")
    elif query_type == "TEMPORAL_FILTER":
        steps.append("Ensure date ranges correctly map to the requested temporal filter.")
    elif query_type == "COMPARISON":
        steps.append("Compare the result sets or apply HAVING/WHERE clauses with comparison operators.")
        
    steps.append("Add LIMIT if necessary and return the final SQL statement.")
    return steps

async def create_query_plan(user_query: str, intent: SQLIntent, entities: ExtractedEntities, schema: dict) -> QueryPlan:
    complexity, query_type = classify_complexity(user_query)
    
    if complexity == "SIMPLE":
        _simple_plan = QueryPlan(
            complexity="SIMPLE",
            query_type=query_type,
            primary_table="appointments",
            required_tables=["appointments"],
        )
        pipeline_logger.plan(
            _simple_plan.complexity,
            _simple_plan.query_type,
            _simple_plan.required_tables,
            len(_simple_plan.required_joins) > 0,
        )
        return _simple_plan
        
    required_tables = detect_required_tables(user_query, entities, schema)
    primary_table = "appointments"
    
    graph = build_relationship_graph(schema)
    required_joins = []
    
    for table in required_tables:
        if table != primary_table:
            path = find_join_path(primary_table, table, graph)
            if path:
                required_joins.extend(path)
                
    # Deduplicate required joins
    required_joins = list(dict.fromkeys(required_joins))
    
    reasoning_steps = build_reasoning_steps(user_query, query_type, required_tables, entities)
    
    _complex_plan = QueryPlan(
        complexity=complexity,
        query_type=query_type,
        primary_table=primary_table,
        required_tables=required_tables,
        required_joins=required_joins,
        reasoning_steps=reasoning_steps
    )
    pipeline_logger.plan(
        _complex_plan.complexity,
        _complex_plan.query_type,
        _complex_plan.required_tables,
        len(_complex_plan.required_joins) > 0,
    )
    return _complex_plan
