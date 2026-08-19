"""
loaders/cognodb_loader.py — Batched dataset loader for CognoDB Cloud.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from rich.console import Console

from benchmark.config import get_batch_size
from benchmark.connectors.cognodb import CognoDBConnector
from benchmark.loaders.dataset import load_nodes_csv, load_relationships_csv

console = Console()


def load_cognodb(batch_size: int | None = None) -> dict[str, Any]:
    if batch_size is None:
        batch_size = 1000  # Smaller batch size for cloud query string buffer stability

    nodes = load_nodes_csv()
    relationships = load_relationships_csv()

    start_dt = datetime.now()
    t0 = time.time()

    _DELETE_BATCH = 1000  # Small batches to avoid cloud timeout on clear

    with CognoDBConnector.from_env() as conn:
        with conn.session() as s:
            # 1. Clean existing data in batches to avoid cloud timeout
            console.print("[cyan]CognoDB:[/cyan] Clearing existing graph data ...")
            delete_query = "MATCH (n) WITH n LIMIT $limit DETACH DELETE n RETURN count(n) AS deleted"
            while True:
                result = s.execute_write(
                    lambda tx: tx.run(delete_query, limit=_DELETE_BATCH).single()["deleted"]
                )
                if result == 0:
                    break

            # 2. Create uniqueness constraint on :User(user_id)
            console.print("[cyan]CognoDB:[/cyan] Creating index on :User(user_id) ...")
            try:
                s.run("CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE")
            except Exception:
                try:
                    s.run("CREATE INDEX user_id_idx IF NOT EXISTS FOR (u:User) ON (u.user_id)")
                except Exception:
                    pass

            try:
                s.run("CALL db.awaitIndexes(30)")
            except Exception:
                pass

            # 3. Load nodes in batches using literal list UNWIND (CognoDB Cypher parser requires literals)
            console.print(f"[cyan]CognoDB:[/cyan] Loading {len(nodes):,} nodes (batch size {batch_size}) ...")
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i : i + batch_size]
                items = [
                    f"{{user_id: {r['user_id']}, public: {r['public']}, completion_percentage: {r['completion_percentage']}, gender: {r['gender']}, region: '{r['region']}', age: {r['age']}}}"
                    for r in batch
                ]
                node_query = (
                    "UNWIND [" + ",".join(items) + "] AS row "
                    "MERGE (u:User {user_id: row.user_id}) "
                    "SET u.public = row.public, "
                    "u.completion_percentage = row.completion_percentage, "
                    "u.gender = row.gender, "
                    "u.region = row.region, "
                    "u.age = row.age"
                )
                s.execute_write(lambda tx, q=node_query: tx.run(q).consume())

            try:
                s.run("CALL db.awaitIndexes(60)")
            except Exception:
                pass

            # 4. Load relationships in batches using literal list UNWIND
            console.print(f"[cyan]CognoDB:[/cyan] Loading {len(relationships):,} relationships (batch size {batch_size}) ...")
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i : i + batch_size]
                items = [f"{{src: {r['source']}, tgt: {r['target']}}}" for r in batch]
                rel_query = (
                    "UNWIND [" + ",".join(items) + "] AS row "
                    "MATCH (src:User {user_id: row.src}) "
                    "MATCH (tgt:User {user_id: row.tgt}) "
                    "CREATE (src)-[:FRIEND_OF]->(tgt)"
                )
                s.execute_write(lambda tx, q=rel_query: tx.run(q).consume())


    t1 = time.time()
    end_dt = datetime.now()
    duration = t1 - t0

    nodes_loaded = len(nodes)
    rels_loaded = len(relationships)

    nodes_per_sec = nodes_loaded / duration if duration > 0 else 0
    rels_per_sec = rels_loaded / duration if duration > 0 else 0

    return {
        "platform": "CognoDB",
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "total_load_time_sec": round(duration, 2),
        "nodes_loaded": nodes_loaded,
        "relationships_loaded": rels_loaded,
        "nodes_per_sec": round(nodes_per_sec, 2),
        "relationships_per_sec": round(rels_per_sec, 2),
        "batch_size": batch_size,
    }
