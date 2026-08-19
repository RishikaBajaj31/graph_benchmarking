"""
scripts/prepare_dataset.py — Reproducible Pokec Dataset Preparation Pipeline.

Reads raw SNAP soc-Pokec dataset files streamingly:
    - data/raw/soc-pokec-relationships.txt.gz
    - data/raw/soc-pokec-profiles.txt.gz

Produces clean, minimal CSV files:
    - data/processed/nodes.csv
    - data/processed/relationships.csv

Target relationship count: 125,000 (reproducible, deterministic prefix sampling).
"""

import csv
import gzip
import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REL_FILE = RAW_DIR / "soc-pokec-relationships.txt.gz"
PROF_FILE = RAW_DIR / "soc-pokec-profiles.txt.gz"

TARGET_RELATIONSHIPS = 125000


def prepare_dataset() -> None:
    console.print(Panel("[bold]Pokec Dataset Preparation Pipeline[/bold]", expand=False))

    if not REL_FILE.exists() or not PROF_FILE.exists():
        console.print(f"[bold red]Error:[/bold red] Raw files missing in {RAW_DIR}")
        sys.exit(1)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    console.print(f"Streaming relationships from [cyan]{REL_FILE}[/cyan] ...")

    relationships = []
    node_ids = set()
    seen_edges = set()

    with gzip.open(REL_FILE, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) != 2:
                continue
            u, v = parts[0], parts[1]

            # Exclude self-loops and duplicate edges
            if u == v or (u, v) in seen_edges:
                continue

            seen_edges.add((u, v))
            relationships.append((u, v))
            node_ids.add(u)
            node_ids.add(v)

            if len(relationships) >= TARGET_RELATIONSHIPS:
                break

    console.print(
        f"Collected [green]{len(relationships):,}[/green] relationships "
        f"across [green]{len(node_ids):,}[/green] unique nodes ({time.time() - t0:.2f}s)."
    )

    t1 = time.time()
    console.print(f"Matching profiles from [cyan]{PROF_FILE}[/cyan] ...")

    nodes = {}
    matched_count = 0
    total_target_nodes = len(node_ids)

    with gzip.open(PROF_FILE, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if not line:
                continue
            fields = line.split("\t")
            if not fields:
                continue

            uid = fields[0]
            if uid in node_ids:
                # Extract essential fields with clean fallbacks
                # 0: user_id, 1: public, 2: completion_percentage, 3: gender, 4: region, 7: age
                public = fields[1] if len(fields) > 1 and fields[1] != "null" else "1"
                completion = fields[2] if len(fields) > 2 and fields[2] != "null" else "0"
                gender = fields[3] if len(fields) > 3 and fields[3] != "null" else "0"
                raw_region = fields[4] if len(fields) > 4 and fields[4] != "null" else "unknown"
                region = raw_region.replace('"', "").replace(",", " ").strip()
                age = fields[7] if len(fields) > 7 and fields[7] != "null" else "0"

                nodes[uid] = {
                    "user_id": uid,
                    "public": public,
                    "completion_percentage": completion,
                    "gender": gender,
                    "region": region,
                    "age": age,
                }
                matched_count += 1
                if matched_count == total_target_nodes:
                    break

    # For any nodes present in relationships but missing in profiles, create a default profile record
    missing_profiles = node_ids - set(nodes.keys())
    if missing_profiles:
        console.print(f"[yellow]Creating default profiles for {len(missing_profiles)} nodes ...[/yellow]")
        for uid in missing_profiles:
            nodes[uid] = {
                "user_id": uid,
                "public": "1",
                "completion_percentage": "0",
                "gender": "0",
                "region": "unknown",
                "age": "0",
            }

    console.print(f"Matched profiles for [green]{len(nodes):,}[/green] nodes ({time.time() - t1:.2f}s).")

    # Write data/processed/relationships.csv
    rel_csv_path = PROCESSED_DIR / "relationships.csv"
    console.print(f"Writing [cyan]{rel_csv_path}[/cyan] ...")
    with open(rel_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target"])
        writer.writerows(relationships)

    # Write data/processed/nodes.csv
    nodes_csv_path = PROCESSED_DIR / "nodes.csv"
    console.print(f"Writing [cyan]{nodes_csv_path}[/cyan] ...")
    with open(nodes_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["user_id", "public", "completion_percentage", "gender", "region", "age"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for uid in sorted(nodes.keys(), key=lambda x: int(x) if x.isdigit() else x):
            writer.writerow(nodes[uid])

    console.print(
        f"\n[bold green]Dataset preparation COMPLETE.[/bold green]\n"
        f"  • Nodes file:         {nodes_csv_path} ({len(nodes):,} rows)\n"
        f"  • Relationships file: {rel_csv_path} ({len(relationships):,} rows)\n"
        f"  • Total time:         {time.time() - t0:.2f}s"
    )


if __name__ == "__main__":
    prepare_dataset()
