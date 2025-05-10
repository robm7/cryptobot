"""
Database Query Optimizer

This module provides utilities for optimizing database queries in the Cryptobot system.
It includes functions for query analysis, optimization, and monitoring.
"""

import time
import logging
import functools
from typing import Dict, List, Any, Callable, Optional, Union, Tuple
from sqlalchemy import text, inspect, event
from sqlalchemy.orm import Session, Query
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import DeclarativeMeta

# Configure logging
logger = logging.getLogger(__name__)

# Global query statistics
query_stats = {
    "total_queries": 0,
    "slow_queries": 0,
    "optimized_queries": 0,
    "query_times": {},
    "slow_query_threshold": 0.5,  # seconds
}

# Query optimization rules
optimization_rules = [
    {
        "name": "select_specific_columns",
        "description": "Select specific columns instead of using SELECT *",
        "pattern": r"SELECT \* FROM",
        "suggestion": "Select only the columns you need"
    },
    {
        "name": "add_index",
        "description": "Add an index to columns used in WHERE clauses",
        "pattern": r"WHERE\s+(\w+)\s*=",
        "suggestion": "Consider adding an index to the column used in the WHERE clause"
    },
    {
        "name": "limit_results",
        "description": "Limit the number of results returned",
        "pattern": r"SELECT .* FROM .* (ORDER BY|GROUP BY)",
        "suggestion": "Add a LIMIT clause to reduce the number of results"
    },
    {
        "name": "avoid_or_operator",
        "description": "Avoid using OR operator in WHERE clauses",
        "pattern": r"WHERE .* OR .*",
        "suggestion": "Consider using UNION or restructuring the query"
    },
    {
        "name": "use_joins_instead_of_subqueries",
        "description": "Use JOINs instead of subqueries",
        "pattern": r"WHERE .* IN \(SELECT",
        "suggestion": "Use a JOIN instead of a subquery"
    }
]

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Event listener that fires before a query is executed.
    This function sets a start time for the query.
    """
    conn.info.setdefault('query_start_time', []).append(time.time())
    query_stats["total_queries"] += 1

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """
    Event listener that fires after a query is executed.
    This function calculates the query execution time and logs slow queries.
    """
    total_time = time.time() - conn.info['query_start_time'].pop()
    
    # Log query time
    query_key = statement[:100]  # Use first 100 chars as key
    if query_key in query_stats["query_times"]:
        query_stats["query_times"][query_key]["count"] += 1
        query_stats["query_times"][query_key]["total_time"] += total_time
        query_stats["query_times"][query_key]["max_time"] = max(
            query_stats["query_times"][query_key]["max_time"], total_time
        )
    else:
        query_stats["query_times"][query_key] = {
            "count": 1,
            "total_time": total_time,
            "max_time": total_time,
            "query": statement
        }
    
    # Log slow queries
    if total_time > query_stats["slow_query_threshold"]:
        query_stats["slow_queries"] += 1
        logger.warning(f"Slow query detected ({total_time:.4f}s): {statement}")
        
        # Analyze query for optimization opportunities
        optimization_suggestions = analyze_query(statement)
        if optimization_suggestions:
            logger.info(f"Query optimization suggestions: {optimization_suggestions}")

def analyze_query(query: str) -> List[str]:
    """
    Analyze a SQL query for optimization opportunities.
    
    Args:
        query: The SQL query to analyze
        
    Returns:
        A list of optimization suggestions
    """
    import re
    
    suggestions = []
    
    for rule in optimization_rules:
        if re.search(rule["pattern"], query, re.IGNORECASE):
            suggestions.append(f"{rule['name']}: {rule['suggestion']}")
    
    return suggestions

def optimize_query(query: Query) -> Query:
    """
    Optimize a SQLAlchemy query.
    
    Args:
        query: The SQLAlchemy query to optimize
        
    Returns:
        The optimized query
    """
    # Get the model class from the query
    model_class = None
    for entity in query._entities:
        if hasattr(entity, 'entity_zero') and hasattr(entity.entity_zero, 'class_'):
            model_class = entity.entity_zero.class_
            break
    
    if not model_class:
        return query
    
    # Get the primary key column
    inspector = inspect(model_class)
    primary_key = inspector.primary_key[0].name if inspector.primary_key else None
    
    # Check if the query has an order_by clause
    has_order_by = query._order_by is not None and len(query._order_by) > 0
    
    # Check if the query has a limit clause
    has_limit = query._limit is not None
    
    # Optimize the query
    optimized_query = query
    
    # Add a limit if not present
    if not has_limit and has_order_by:
        optimized_query = optimized_query.limit(1000)
    
    # Use specific columns instead of SELECT *
    if len(query._entities) == 1 and hasattr(query._entities[0], 'expr') and query._entities[0].expr == model_class:
        # Query is selecting all columns, optimize to select only necessary columns
        if primary_key:
            # If we're just counting, select only the primary key
            if query._statement._group_by or query._statement._having:
                optimized_query = optimized_query.with_entities(getattr(model_class, primary_key))
    
    # Log optimization
    if optimized_query != query:
        query_stats["optimized_queries"] += 1
        logger.info(f"Query optimized: {query} -> {optimized_query}")
    
    return optimized_query

def query_optimizer(func: Callable) -> Callable:
    """
    Decorator for optimizing database queries in repository methods.
    
    Args:
        func: The function to decorate
        
    Returns:
        The decorated function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # If the result is a SQLAlchemy Query, optimize it
        if isinstance(result, Query):
            return optimize_query(result)
        
        return result
    
    return wrapper

def get_query_stats() -> Dict[str, Any]:
    """
    Get query statistics.
    
    Returns:
        A dictionary of query statistics
    """
    stats = query_stats.copy()
    
    # Calculate average query times
    for query_key, query_data in stats["query_times"].items():
        query_data["avg_time"] = query_data["total_time"] / query_data["count"]
    
    # Sort query times by average time (descending)
    stats["query_times"] = dict(sorted(
        stats["query_times"].items(),
        key=lambda x: x[1]["avg_time"],
        reverse=True
    ))
    
    return stats

def reset_query_stats() -> None:
    """Reset query statistics."""
    global query_stats
    query_stats = {
        "total_queries": 0,
        "slow_queries": 0,
        "optimized_queries": 0,
        "query_times": {},
        "slow_query_threshold": query_stats["slow_query_threshold"],
    }

def set_slow_query_threshold(threshold: float) -> None:
    """
    Set the threshold for slow queries.
    
    Args:
        threshold: The threshold in seconds
    """
    query_stats["slow_query_threshold"] = threshold

def optimize_model_queries(model_class: DeclarativeMeta) -> None:
    """
    Add indexes to a model class based on common query patterns.
    
    Args:
        model_class: The SQLAlchemy model class to optimize
    """
    # Get the table name
    table_name = model_class.__tablename__
    
    # Get the engine
    engine = model_class.metadata.bind
    
    # Get existing indexes
    existing_indexes = []
    with engine.connect() as conn:
        result = conn.execute(text(f"PRAGMA index_list('{table_name}')"))
        for row in result:
            existing_indexes.append(row[1])
    
    # Get columns commonly used in WHERE clauses
    common_where_columns = []
    for query_key, query_data in query_stats["query_times"].items():
        if query_data["count"] > 10:  # Only consider queries executed more than 10 times
            query = query_data["query"]
            if f"FROM {table_name}" in query and "WHERE" in query:
                # Extract column names from WHERE clause
                import re
                where_clause = query.split("WHERE")[1].split("ORDER BY")[0].split("GROUP BY")[0].split("LIMIT")[0]
                column_matches = re.findall(r"(\w+)\s*=\s*[?:]", where_clause)
                common_where_columns.extend(column_matches)
    
    # Count occurrences of each column
    from collections import Counter
    column_counts = Counter(common_where_columns)
    
    # Add indexes for commonly used columns
    for column, count in column_counts.items():
        if count > 5:  # Only add index if column is used in more than 5 queries
            index_name = f"ix_{table_name}_{column}"
            if index_name not in existing_indexes:
                logger.info(f"Adding index {index_name} to {table_name}.{column}")
                with engine.connect() as conn:
                    conn.execute(text(f"CREATE INDEX {index_name} ON {table_name} ({column})"))

def get_slow_queries() -> List[Dict[str, Any]]:
    """
    Get a list of slow queries.
    
    Returns:
        A list of slow queries with execution times
    """
    slow_queries = []
    
    for query_key, query_data in query_stats["query_times"].items():
        if query_data["max_time"] > query_stats["slow_query_threshold"]:
            slow_queries.append({
                "query": query_data["query"],
                "count": query_data["count"],
                "avg_time": query_data["total_time"] / query_data["count"],
                "max_time": query_data["max_time"],
                "suggestions": analyze_query(query_data["query"])
            })
    
    # Sort by max_time (descending)
    slow_queries.sort(key=lambda x: x["max_time"], reverse=True)
    
    return slow_queries

def explain_query(session: Session, query: Union[str, Query]) -> List[Dict[str, Any]]:
    """
    Get the execution plan for a query.
    
    Args:
        session: The SQLAlchemy session
        query: The query to explain (either a string or a SQLAlchemy Query)
        
    Returns:
        The execution plan as a list of dictionaries
    """
    if isinstance(query, Query):
        query_str = str(query.statement.compile(
            dialect=session.bind.dialect,
            compile_kwargs={"literal_binds": True}
        ))
    else:
        query_str = query
    
    # Add EXPLAIN to the query
    explain_query_str = f"EXPLAIN QUERY PLAN {query_str}"
    
    # Execute the EXPLAIN query
    result = session.execute(text(explain_query_str))
    
    # Parse the result
    plan = []
    for row in result:
        plan.append(dict(row))
    
    return plan

def create_index_if_needed(session: Session, table_name: str, column_name: str) -> bool:
    """
    Create an index on a column if it doesn't exist.
    
    Args:
        session: The SQLAlchemy session
        table_name: The name of the table
        column_name: The name of the column
        
    Returns:
        True if the index was created, False otherwise
    """
    # Check if the index already exists
    index_name = f"ix_{table_name}_{column_name}"
    result = session.execute(text(f"PRAGMA index_list('{table_name}')"))
    for row in result:
        if row[1] == index_name:
            return False
    
    # Create the index
    session.execute(text(f"CREATE INDEX {index_name} ON {table_name} ({column_name})"))
    session.commit()
    
    logger.info(f"Created index {index_name} on {table_name}.{column_name}")
    return True

def optimize_database(session: Session) -> Dict[str, Any]:
    """
    Optimize the database by analyzing query patterns and adding indexes.
    
    Args:
        session: The SQLAlchemy session
        
    Returns:
        A dictionary with optimization results
    """
    # Get slow queries
    slow_queries = get_slow_queries()
    
    # Extract table and column names from slow queries
    table_column_pairs = []
    for query_data in slow_queries:
        query = query_data["query"]
        
        # Extract table name
        import re
        table_match = re.search(r"FROM\s+(\w+)", query, re.IGNORECASE)
        if not table_match:
            continue
        
        table_name = table_match.group(1)
        
        # Extract column names from WHERE clause
        where_match = re.search(r"WHERE(.*?)(ORDER BY|GROUP BY|LIMIT|$)", query, re.IGNORECASE)
        if not where_match:
            continue
        
        where_clause = where_match.group(1)
        column_matches = re.findall(r"(\w+)\s*=\s*[?:]", where_clause)
        
        for column_name in column_matches:
            table_column_pairs.append((table_name, column_name))
    
    # Count occurrences of each table-column pair
    from collections import Counter
    pair_counts = Counter(table_column_pairs)
    
    # Create indexes for commonly used columns
    indexes_created = []
    for (table_name, column_name), count in pair_counts.items():
        if count >= 3:  # Only create index if column is used in at least 3 slow queries
            if create_index_if_needed(session, table_name, column_name):
                indexes_created.append(f"{table_name}.{column_name}")
    
    # Analyze tables
    tables = session.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
    for table in tables:
        table_name = table[0]
        session.execute(text(f"ANALYZE {table_name}"))
    
    # Vacuum database
    session.execute(text("VACUUM"))
    
    # Return optimization results
    return {
        "slow_queries": len(slow_queries),
        "indexes_created": indexes_created,
        "tables_analyzed": [table[0] for table in tables]
    }