"""
benchmark/workloads/concurrent.py — Concurrent mixed read/write workload benchmark.
"""

from __future__ import annotations

import concurrent.futures
import random
import time
from typing import Any

from benchmark.connectors.arangodb import ArangoDBConnector
from benchmark.connectors.cognodb import CognoDBConnector
from benchmark.connectors.falkordb import FalkorDBConnector
from benchmark.connectors.memgraph import MemgraphConnector
from benchmark.connectors.neo4j import Neo4jConnector
from benchmark.loaders.dataset import load_nodes_csv

NUM_WORKERS = 4
DURATION_SECONDS = 10.0
READ_RATIO = 0.80  # 80% read, 20% write


def _get_user_id_pool() -> list[int]:
    nodes = load_nodes_csv()
    return [n["user_id"] for n in nodes]


def _worker_task_cypher(connector_cls: type, duration: float, user_ids: list[int]) -> tuple[int, int]:
    reads, writes = 0, 0
    t_end = time.time() + duration
    rng = random.Random()

    read_q = "MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age"
    write_q = "MATCH (u:User {user_id: $uid}) SET u.last_accessed = $ts"

    with connector_cls.from_env() as conn:
        with conn.session() as s:
            while time.time() < t_end:
                uid = rng.choice(user_ids)
                if rng.random() < READ_RATIO:
                    s.run(read_q, uid=uid).consume()
                    reads += 1
                else:
                    s.run(write_q, uid=uid, ts=int(time.time())).consume()
                    writes += 1

    return (reads, writes)


def _worker_task_falkordb(duration: float, user_ids: list[int]) -> tuple[int, int]:
    reads, writes = 0, 0
    t_end = time.time() + duration
    rng = random.Random()

    read_q = "MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age"
    write_q = "MATCH (u:User {user_id: $uid}) SET u.last_accessed = $ts"

    with FalkorDBConnector.from_env() as conn:
        graph = conn.select_graph("pokec")
        while time.time() < t_end:
            uid = rng.choice(user_ids)
            if rng.random() < READ_RATIO:
                graph.query(read_q, {"uid": uid})
                reads += 1
            else:
                graph.query(write_q, {"uid": uid, "ts": int(time.time())})
                writes += 1

    return (reads, writes)


def _worker_task_arangodb(duration: float, user_ids: list[int]) -> tuple[int, int]:
    reads, writes = 0, 0
    t_end = time.time() + duration
    rng = random.Random()

    read_q = "FOR u IN User FILTER u.user_id == @uid RETURN u.user_id"
    write_q = "FOR u IN User FILTER u.user_id == @uid UPDATE u WITH { last_accessed: @ts } IN User"

    with ArangoDBConnector.from_env() as conn:
        db = conn.get_db("pokec")
        while time.time() < t_end:
            uid = rng.choice(user_ids)
            if rng.random() < READ_RATIO:
                list(db.aql.execute(read_q, bind_vars={"uid": uid}))
                reads += 1
            else:
                db.aql.execute(write_q, bind_vars={"uid": uid, "ts": int(time.time())})
                writes += 1

    return (reads, writes)


def benchmark_concurrent(db_name: str) -> dict[str, Any]:
    """
    Run 4-worker concurrent 80/20 mixed read/write workload for 10 seconds.
    """
    user_ids = _get_user_id_pool()
    t0 = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        if db_name in ("CognoDB Cloud", "Neo4j AuraDB", "Memgraph"):
            connector_cls = {
                "CognoDB Cloud": CognoDBConnector,
                "Neo4j AuraDB": Neo4jConnector,
                "Memgraph": MemgraphConnector,
            }[db_name]
            futures = [
                executor.submit(_worker_task_cypher, connector_cls, DURATION_SECONDS, user_ids)
                for _ in range(NUM_WORKERS)
            ]
        elif db_name == "FalkorDB":
            futures = [
                executor.submit(_worker_task_falkordb, DURATION_SECONDS, user_ids)
                for _ in range(NUM_WORKERS)
            ]
        elif db_name == "ArangoDB":
            futures = [
                executor.submit(_worker_task_arangodb, DURATION_SECONDS, user_ids)
                for _ in range(NUM_WORKERS)
            ]
        else:
            raise ValueError(f"Unknown database: {db_name}")

        results = [f.result() for f in futures]

    t1 = time.perf_counter()
    actual_duration = t1 - t0

    total_reads = sum(r[0] for r in results)
    total_writes = sum(r[1] for r in results)
    total_ops = total_reads + total_writes
    qps = total_ops / actual_duration if actual_duration > 0 else 0.0

    return {
        "database": db_name,
        "workload": "Concurrent Mixed R/W",
        "sustained_qps": round(qps, 2),
        "total_ops": total_ops,
        "total_reads": total_reads,
        "total_writes": total_writes,
        "workers": NUM_WORKERS,
        "read_write_ratio": "80/20",
        "duration_sec": round(actual_duration, 2),
    }
