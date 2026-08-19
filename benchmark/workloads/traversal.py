"""
benchmark/workloads/traversal.py — 1-hop, 2-hop, and 3-hop graph traversal benchmarks.
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


def _get_sample_start_nodes(count: int = 150, seed: int = 42) -> list[int]:
    nodes = load_nodes_csv()
    rng = random.Random(seed)
    # Pick valid user_ids from dataset deterministically
    user_ids = [n["user_id"] for n in nodes]
    return rng.choices(user_ids, k=count)


def benchmark_traversal(db_name: str, hops: int) -> dict[str, Any]:
    """
    Run N-hop traversal benchmark (hops = 1, 2, or 3) for the specified database.
    Performs 10 warm-up iterations and 100 measured iterations.
    """
    sample_ids = _get_sample_start_nodes(count=WARMUP_ITERATIONS + MEASURED_ITERATIONS)
    warmup_ids = sample_ids[:WARMUP_ITERATIONS]
    measured_ids = sample_ids[WARMUP_ITERATIONS:]

    durations: list[float] = []

    if db_name in ("CognoDB Cloud", "Neo4j AuraDB", "Memgraph"):
        connector_cls = {
            "CognoDB Cloud": CognoDBConnector,
            "Neo4j AuraDB": Neo4jConnector,
            "Memgraph": MemgraphConnector,
        }[db_name]

        cypher_map = {
            1: "MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt) AS c",
            2: "MATCH (src:User {user_id: $uid})-[:FRIEND_OF*2]->(tgt:User) RETURN count(DISTINCT tgt) AS c",
            3: "MATCH (src:User {user_id: $uid})-[:FRIEND_OF*3]->(tgt:User) RETURN count(DISTINCT tgt) AS c",
        }
        query = cypher_map[hops]

        with connector_cls.from_env() as conn:
            with conn.session() as s:
                # Warm-up phase
                for uid in warmup_ids:
                    s.run(query, uid=uid).consume()

                # Measured phase
                for uid in measured_ids:
                    dur = measure_execution(lambda u=uid: s.run(query, uid=u).consume())
                    durations.append(dur)

    elif db_name == "FalkorDB":
        cypher_map = {
            1: "MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt)",
            2: "MATCH (src:User {user_id: $uid})-[:FRIEND_OF*2]->(tgt:User) RETURN count(DISTINCT tgt)",
            3: "MATCH (src:User {user_id: $uid})-[:FRIEND_OF*3]->(tgt:User) RETURN count(DISTINCT tgt)",
        }
        query = cypher_map[hops]

        with FalkorDBConnector.from_env() as conn:
            graph = conn.select_graph("pokec")
            # Warm-up phase
            for uid in warmup_ids:
                graph.query(query, {"uid": uid})

            # Measured phase
            for uid in measured_ids:
                dur = measure_execution(lambda u=uid: graph.query(query, {"uid": u}))
                durations.append(dur)

    elif db_name == "ArangoDB":
        aql_map = {
            1: "FOR src IN User FILTER src.user_id == @uid FOR v IN 1..1 OUTBOUND src FRIEND_OF RETURN v._key",
            2: "FOR src IN User FILTER src.user_id == @uid FOR v IN 2..2 OUTBOUND src FRIEND_OF RETURN DISTINCT v._key",
            3: "FOR src IN User FILTER src.user_id == @uid FOR v IN 3..3 OUTBOUND src FRIEND_OF RETURN DISTINCT v._key",
        }
        query = aql_map[hops]

        with ArangoDBConnector.from_env() as conn:
            db = conn.get_db("pokec")
            # Warm-up phase
            for uid in warmup_ids:
                list(db.aql.execute(query, bind_vars={"uid": uid}))

            # Measured phase
            for uid in measured_ids:
                dur = measure_execution(lambda u=uid: list(db.aql.execute(query, bind_vars={"uid": u})))
                durations.append(dur)

    else:
        raise ValueError(f"Unknown database: {db_name}")

    stats = calculate_percentiles(durations)
    stats["workload"] = f"{hops}-Hop Traversal"
    stats["database"] = db_name
    stats["iterations"] = len(durations)
    return stats
