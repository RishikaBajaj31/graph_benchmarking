"""
loaders/dataset.py — Shared dataset reader for processed Pokec CSV files.
"""

import csv
from pathlib import Path
from typing import Any

NODES_CSV = Path("data/processed/nodes.csv")
RELATIONSHIPS_CSV = Path("data/processed/relationships.csv")


def load_nodes_csv(path: Path = NODES_CSV) -> list[dict[str, Any]]:
    """Read data/processed/nodes.csv into a list of parsed dictionaries."""
    nodes = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nodes.append({
                "user_id": int(row["user_id"]),
                "public": int(row["public"]),
                "completion_percentage": int(row["completion_percentage"]),
                "gender": int(row["gender"]),
                "region": row["region"],
                "age": int(row["age"]),
            })
    return nodes


def load_relationships_csv(path: Path = RELATIONSHIPS_CSV) -> list[dict[str, int]]:
    """Read data/processed/relationships.csv into a list of parsed dictionaries."""
    relationships = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            relationships.append({
                "source": int(row["source"]),
                "target": int(row["target"]),
            })
    return relationships
