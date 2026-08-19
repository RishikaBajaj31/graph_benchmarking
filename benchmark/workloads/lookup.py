"""
benchmark/workloads/lookup.py — Point lookup and indexed/filtered lookup benchmarks.
"""

from __future__ import annotations

import random
from typing import Any

from benchmark.connectors.arangodb import ArangoDBConnector
from benchmark.connectors.cognodb import CognoDBConnector
from benchmark.connectors.falkordb import FalkorDBConnector
from benchmark.connectors.memgraph import MemgraphConnector
from benchmark.connectors.neo4j import Neo4jConnector
from benchmark.loaders.dataset import load_nodes_csv
from benchmark.workloads.base import (
    MEASURED_ITERATIONS,
    WARMUP_ITERATIONS,
    calculate_percentiles,
    measure_execution,
)


def _get_sample_user_ids(count: int = 150, seed: int = 42) -> list[int]:
    nodes = load_nodes_csv()
    rng = random.Random(seed)
    user_ids = [n["user_id"] for n in nodes]
    return rng.choices(user_ids, k=count)


def benchmark_point_lookup(db_name: str) -> dict[str, Any]:
    """
    Run Point Lookup benchmark (fetching a single node by user_id).
    """
    sample_ids = _get_sample_user_ids(count=WARMUP_ITERATIONS + MEASURED_ITERATIONS)
    warmup_ids = sample_ids[:WARMUP_ITERATIONS]
    measured_ids = sample_ids[WARMUP_ITERATIONS:]

    durations: list[float] = []

    if db_name in ("CognoDB Cloud", "Neo4j AuraDB", "Memgraph"):
        connector_cls = {
            "CognoDB Cloud": CognoDBConnector,
            "Neo4j AuraDB": Neo4jConnector,
            "Memgraph": MemgraphConnector,
        }[db_name]
        query = "MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age, u.gender, u.region"

        with connector_cls.from_env() as conn:
            with conn.session() as s:
                for uid in warmup_ids:
                    s.run(query, uid=uid).consume()

                for uid in measured_ids:
                    dur = measure_execution(lambda u=uid: s.run(query, uid=u).consume())
                    durations.append(dur)

    elif db_name == "FalkorDB":
        query = "MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age, u.gender, u.region"
        with FalkorDBConnector.from_env() as conn:
            graph = conn.select_graph("pokec")
            for uid in warmup_ids:
                graph.query(query, {"uid": uid})

            for uid in measured_ids:
                dur = measure_execution(lambda u=uid: graph.query(query, {"uid": u}))
                durations.append(dur)

    elif db_name == "ArangoDB":
        query = "FOR u IN User FILTER u.user_id == @uid RETURN {user_id: u.user_id, age: u.age, gender: u.gender}"
        with ArangoDBConnector.from_env() as conn:
            db = conn.get_db("pokec")
            for uid in warmup_ids:
                list(db.aql.execute(query, bind_vars={"uid": uid}))

            for uid in measured_ids:
                dur = measure_execution(lambda u=uid: list(db.aql.execute(query, bind_vars={"uid": u})))
                durations.append(dur)

    else:
        raise ValueError(f"Unknown database: {db_name}")

    stats = calculate_percentiles(durations)
    stats["workload"] = "Point Lookup"
    stats["database"] = db_name
    stats["iterations"] = len(durations)
    return stats


def benchmark_filtered_lookup(db_name: str) -> dict[str, Any]:
    """
    Run Filtered / Indexed Lookup benchmark (filtering nodes by property age=25 and gender=1).
    """
    durations: list[float] = []
    age, gender = 25, 1

    if db_name in ("CognoDB Cloud", "Neo4j AuraDB", "Memgraph"):
        connector_cls = {
            "CognoDB Cloud": CognoDBConnector,
            "Neo4j AuraDB": Neo4jConnector,
            "Memgraph": MemgraphConnector,
        }[db_name]
        query = "MATCH (u:User) WHERE u.age = $age AND u.gender = $gender RETURN u.user_id, u.region LIMIT 100"

        with connector_cls.from_env() as conn:
            with conn.session() as s:
                for _ in range(WARMUP_ITERATIONS):
                    s.run(query, age=age, gender=gender).consume()

                for _ in range(MEASURED_ITERATIONS):
                    dur = measure_execution(lambda: s.run(query, age=age, gender=gender).consume())
                    durations.append(dur)

    elif db_name == "FalkorDB":
        query = "MATCH (u:User) WHERE u.age = $age AND u.gender = $gender RETURN u.user_id, u.region LIMIT 100"
        with FalkorDBConnector.from_env() as conn:
            graph = conn.select_graph("pokec")
            for _ in range(WARMUP_ITERATIONS):
                graph.query(query, {"age": age, "gender": gender})

            for _ in range(MEASURED_ITERATIONS):
                dur = measure_execution(lambda: graph.query(query, {"age": age, "gender": gender}))
                durations.append(dur)

    elif db_name == "ArangoDB":
        query = "FOR u IN User FILTER u.age == @age AND u.gender == @gender LIMIT 100 RETURN u.user_id"
        with ArangoDBConnector.from_env() as conn:
            db = conn.get_db("pokec")
            for _ in range(WARMUP_ITERATIONS):
                list(db.aql.execute(query, bind_vars={"age": age, "gender": gender}))

            for _ in range(MEASURED_ITERATIONS):
                dur = measure_execution(lambda: list(db.aql.execute(query, bind_vars={"age": age, "gender": gender})))
                durations.append(dur)

    else:
        raise ValueError(f"Unknown database: {db_name}")

    stats = calculate_percentiles(durations)
    stats["workload"] = "Indexed / Filtered Lookup"
    stats["database"] = db_name
    stats["iterations"] = len(durations)
    return stats
