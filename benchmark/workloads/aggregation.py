"""
benchmark/workloads/aggregation.py — Aggregation workload benchmark.
"""

from __future__ import annotations

from typing import Any

from benchmark.connectors.arangodb import ArangoDBConnector
from benchmark.connectors.cognodb import CognoDBConnector
from benchmark.connectors.falkordb import FalkorDBConnector
from benchmark.connectors.memgraph import MemgraphConnector
from benchmark.connectors.neo4j import Neo4jConnector
from benchmark.workloads.base import (
    MEASURED_ITERATIONS,
    WARMUP_ITERATIONS,
    calculate_percentiles,
    measure_execution,
)


def benchmark_aggregation(db_name: str) -> dict[str, Any]:
    """
    Run Aggregation benchmark (GROUP BY gender, count nodes, calculate avg age).
    """
    durations: list[float] = []

    if db_name in ("CognoDB Cloud", "Neo4j AuraDB", "Memgraph"):
        connector_cls = {
            "CognoDB Cloud": CognoDBConnector,
            "Neo4j AuraDB": Neo4jConnector,
            "Memgraph": MemgraphConnector,
        }[db_name]
        query = "MATCH (u:User) RETURN u.gender AS gender, count(u) AS count, avg(u.age) AS avg_age"

        with connector_cls.from_env() as conn:
            with conn.session() as s:
                for _ in range(WARMUP_ITERATIONS):
                    s.run(query).consume()

                for _ in range(MEASURED_ITERATIONS):
                    dur = measure_execution(lambda: s.run(query).consume())
                    durations.append(dur)

    elif db_name == "FalkorDB":
        query = "MATCH (u:User) RETURN u.gender, count(u), avg(u.age)"
        with FalkorDBConnector.from_env() as conn:
            graph = conn.select_graph("pokec")
            for _ in range(WARMUP_ITERATIONS):
                graph.query(query)

            for _ in range(MEASURED_ITERATIONS):
                dur = measure_execution(lambda: graph.query(query))
                durations.append(dur)

    elif db_name == "ArangoDB":
        query = "FOR u IN User COLLECT gender = u.gender AGGREGATE count = LENGTH(1), avg_age = AVG(u.age) RETURN {gender, count, avg_age}"
        with ArangoDBConnector.from_env() as conn:
            db = conn.get_db("pokec")
            for _ in range(WARMUP_ITERATIONS):
                list(db.aql.execute(query))

            for _ in range(MEASURED_ITERATIONS):
                dur = measure_execution(lambda: list(db.aql.execute(query)))
                durations.append(dur)

    else:
        raise ValueError(f"Unknown database: {db_name}")

    stats = calculate_percentiles(durations)
    stats["workload"] = "Aggregation"
    stats["database"] = db_name
    stats["iterations"] = len(durations)
    return stats
