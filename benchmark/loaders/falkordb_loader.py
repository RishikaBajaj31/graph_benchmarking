"""
loaders/falkordb_loader.py — Batched dataset loader for FalkorDB.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from rich.console import Console

from benchmark.config import get_batch_size
from benchmark.connectors.falkordb import FalkorDBConnector
from benchmark.loaders.dataset import load_nodes_csv, load_relationships_csv

console = Console()
FALKOR_GRAPH_NAME = "pokec"


def load_falkordb(batch_size: int | None = None) -> dict[str, Any]:
    if batch_size is None:
        batch_size = get_batch_size(default=2500)

    nodes = load_nodes_csv()
    relationships = load_relationships_csv()

    start_dt = datetime.now()
    t0 = time.time()

    with FalkorDBConnector.from_env() as conn:
        graph = conn.select_graph(FALKOR_GRAPH_NAME)

        # 1. Clean existing graph data
        console.print(f"[cyan]FalkorDB:[/cyan] Clearing graph '{FALKOR_GRAPH_NAME}' ...")
        try:
            graph.delete()
        except Exception:
            pass
        graph = conn.select_graph(FALKOR_GRAPH_NAME)

        # 2. Create index on :User(user_id)
        console.print("[cyan]FalkorDB:[/cyan] Creating index on :User(user_id) ...")
        try:
            graph.query("CREATE INDEX FOR (u:User) ON (u.user_id)")
        except Exception:
            pass

        # 3. Load nodes in batches
        console.print(f"[cyan]FalkorDB:[/cyan] Loading {len(nodes):,} nodes (batch size {batch_size}) ...")
        node_query = """
        UNWIND $batch AS row
        CREATE (u:User {
            user_id: toInteger(row.user_id),
            public: toInteger(row.public),
            completion_percentage: toInteger(row.completion_percentage),
            gender: toInteger(row.gender),
            region: row.region,
            age: toInteger(row.age)
        })
        """
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            graph.query(node_query, {"batch": batch})

        # 4. Load relationships in batches
        console.print(f"[cyan]FalkorDB:[/cyan] Loading {len(relationships):,} relationships (batch size {batch_size}) ...")
        rel_query = """
        UNWIND $batch AS row
        MATCH (src:User {user_id: toInteger(row.source)}), (tgt:User {user_id: toInteger(row.target)})
        CREATE (src)-[:FRIEND_OF]->(tgt)
        """
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i : i + batch_size]
            graph.query(rel_query, {"batch": batch})

    t1 = time.time()
    end_dt = datetime.now()
    duration = t1 - t0

    nodes_loaded = len(nodes)
    rels_loaded = len(relationships)

    nodes_per_sec = nodes_loaded / duration if duration > 0 else 0
    rels_per_sec = rels_loaded / duration if duration > 0 else 0

    return {
        "platform": "FalkorDB",
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "total_load_time_sec": round(duration, 2),
        "nodes_loaded": nodes_loaded,
        "relationships_loaded": rels_loaded,
        "nodes_per_sec": round(nodes_per_sec, 2),
        "relationships_per_sec": round(rels_per_sec, 2),
        "batch_size": batch_size,
    }
