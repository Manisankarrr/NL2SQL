from backend.planner.decomposition import QueryPlan

def should_use_planner(query_plan: QueryPlan) -> bool:
    return query_plan.complexity == "COMPLEX"

def get_routing_decision(query_plan: QueryPlan) -> dict:
    needs_join = len(query_plan.required_tables) > 1
    needs_aggregation = query_plan.query_type == "AGGREGATION"
    
    if should_use_planner(query_plan):
        return {
            "path": "complex",
            "reason": f"Query requires {query_plan.query_type} execution plan",
            "estimated_tables": len(query_plan.required_tables),
            "needs_join": needs_join,
            "needs_aggregation": needs_aggregation
        }
    else:
        return {
            "path": "simple",
            "reason": "Query is simple and requires no complex planning",
            "estimated_tables": 1,
            "needs_join": False,
            "needs_aggregation": False
        }
