"""
loaders/neo4j_loader.py — Batched dataset loader for Neo4j AuraDB.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from rich.console import Console

from benchmark.config import get_batch_size
from benchmark.connectors.neo4j import Neo4jConnector
from benchmark.loaders.dataset import load_nodes_csv, load_relationships_csv

console = Console()


def load_neo4j(batch_size: int | None = None) -> dict[str, Any]:
    if batch_size is None:
        batch_size = get_batch_size(default=2500)

    nodes = load_nodes_csv()
    relationships = load_relationships_csv()

    start_dt = datetime.now()
    t0 = time.time()

    with Neo4jConnector.from_env() as conn:
        with conn.session() as s:
            # 1. Clean existing data
            console.print("[cyan]Neo4j AuraDB:[/cyan] Clearing existing graph data ...")
            s.run("MATCH (n) DETACH DELETE n")

            # 2. Create index on :User(user_id)
            console.print("[cyan]Neo4j AuraDB:[/cyan] Creating index on :User(user_id) ...")
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

            # 3. Load nodes in batches
            console.print(f"[cyan]Neo4j AuraDB:[/cyan] Loading {len(nodes):,} nodes (batch size {batch_size}) ...")
            node_query = """
            UNWIND $batch AS row
            CREATE (u:User {
                user_id: row.user_id,
                public: row.public,
                completion_percentage: row.completion_percentage,
                gender: row.gender,
                region: row.region,
                age: row.age
            })
            """
            for i in range(0, len(nodes), batch_size):
                batch = nodes[i : i + batch_size]
                s.execute_write(lambda tx, b=batch: tx.run(node_query, batch=b))

            try:
                s.run("CALL db.awaitIndexes(60)")
            except Exception:
                pass

            # 4. Load relationships in batches
            console.print(f"[cyan]Neo4j AuraDB:[/cyan] Loading {len(relationships):,} relationships (batch size {batch_size}) ...")
            rel_query = """
            UNWIND $batch AS row
            MATCH (src:User {user_id: row.source})
            MATCH (tgt:User {user_id: row.target})
            CREATE (src)-[:FRIEND_OF]->(tgt)
            """
            for i in range(0, len(relationships), batch_size):
                batch = relationships[i : i + batch_size]
                s.execute_write(lambda tx, b=batch: tx.run(rel_query, batch=b))


    t1 = time.time()
    end_dt = datetime.now()
    duration = t1 - t0

    nodes_loaded = len(nodes)
    rels_loaded = len(relationships)

    nodes_per_sec = nodes_loaded / duration if duration > 0 else 0
    rels_per_sec = rels_loaded / duration if duration > 0 else 0

    return {
        "platform": "Neo4j AuraDB",
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "total_load_time_sec": round(duration, 2),
        "nodes_loaded": nodes_loaded,
        "relationships_loaded": rels_loaded,
        "nodes_per_sec": round(nodes_per_sec, 2),
        "relationships_per_sec": round(rels_per_sec, 2),
        "batch_size": batch_size,
    }
