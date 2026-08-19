"""
loaders/arangodb_loader.py — Batched dataset loader for ArangoDB.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from rich.console import Console

from benchmark.config import get_batch_size
from benchmark.connectors.arangodb import ArangoDBConnector
from benchmark.loaders.dataset import load_nodes_csv, load_relationships_csv

console = Console()
ARANGO_DB_NAME = "pokec"


def load_arangodb(batch_size: int | None = None) -> dict[str, Any]:
    if batch_size is None:
        batch_size = get_batch_size(default=2500)

    nodes = load_nodes_csv()
    relationships = load_relationships_csv()

    start_dt = datetime.now()
    t0 = time.time()

    with ArangoDBConnector.from_env() as conn:
        sys_db = conn.get_db("_system")

        # 1. Ensure 'pokec' database exists
        if not sys_db.has_database(ARANGO_DB_NAME):
            sys_db.create_database(ARANGO_DB_NAME)

        db = conn.get_db(ARANGO_DB_NAME)

        # 2. Reset collections
        console.print(f"[cyan]ArangoDB:[/cyan] Resetting collections in database '{ARANGO_DB_NAME}' ...")
        if db.has_collection("FRIEND_OF"):
            db.delete_collection("FRIEND_OF")
        if db.has_collection("User"):
            db.delete_collection("User")

        user_col = db.create_collection("User")
        friend_col = db.create_collection("FRIEND_OF", edge=True)

        # 3. Load nodes in batches
        console.print(f"[cyan]ArangoDB:[/cyan] Loading {len(nodes):,} nodes (batch size {batch_size}) ...")
        node_docs = [
            {
                "_key": str(n["user_id"]),
                "user_id": n["user_id"],
                "public": n["public"],
                "completion_percentage": n["completion_percentage"],
                "gender": n["gender"],
                "region": n["region"],
                "age": n["age"],
            }
            for n in nodes
        ]
        for i in range(0, len(node_docs), batch_size):
            batch = node_docs[i : i + batch_size]
            user_col.insert_many(batch)

        # 4. Load relationships in batches
        console.print(f"[cyan]ArangoDB:[/cyan] Loading {len(relationships):,} relationships (batch size {batch_size}) ...")
        rel_docs = [
            {
                "_from": f"User/{r['source']}",
                "_to": f"User/{r['target']}",
            }
            for r in relationships
        ]
        for i in range(0, len(rel_docs), batch_size):
            batch = rel_docs[i : i + batch_size]
            friend_col.insert_many(batch)

    t1 = time.time()
    end_dt = datetime.now()
    duration = t1 - t0

    nodes_loaded = len(nodes)
    rels_loaded = len(relationships)

    nodes_per_sec = nodes_loaded / duration if duration > 0 else 0
    rels_per_sec = rels_loaded / duration if duration > 0 else 0

    return {
        "platform": "ArangoDB",
        "start_time": start_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "end_time": end_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "total_load_time_sec": round(duration, 2),
        "nodes_loaded": nodes_loaded,
        "relationships_loaded": rels_loaded,
        "nodes_per_sec": round(nodes_per_sec, 2),
        "relationships_per_sec": round(rels_per_sec, 2),
        "batch_size": batch_size,
    }
