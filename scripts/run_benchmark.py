"""
scripts/run_benchmark.py — Complete Benchmark Orchestrator Suite.

Executes all mandatory benchmark workloads across all five graph databases:
    1. CognoDB Cloud
    2. Neo4j AuraDB
    3. Memgraph
    4. FalkorDB
    5. ArangoDB

Generates:
    - results/results.csv (machine-readable)
    - Formatted Rich console summary tables
"""

from __future__ import annotations

import csv
import io
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure stdout handles UTF-8 on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.workloads.aggregation import benchmark_aggregation
from benchmark.workloads.concurrent import benchmark_concurrent
from benchmark.workloads.footprint import get_footprint
from benchmark.workloads.lookup import benchmark_filtered_lookup, benchmark_point_lookup
from benchmark.workloads.traversal import benchmark_traversal

console = Console()

RESULTS_DIR = Path("results")
RESULTS_CSV = RESULTS_DIR / "results.csv"

DATABASES = [
    "ArangoDB",
    "FalkorDB",
    "Memgraph",
    "Neo4j AuraDB",
    "CognoDB Cloud",
]

# Baseline recorded load metrics from Phase 8 verified runs
LOAD_METRICS: dict[str, dict[str, Any]] = {
    "ArangoDB": {"time_sec": 6.07, "nodes_sec": 10331.42, "rels_sec": 20603.84},
    "FalkorDB": {"time_sec": 12.32, "nodes_sec": 5087.40, "rels_sec": 10145.74},
    "Memgraph": {"time_sec": 7.90, "nodes_sec": 7935.87, "rels_sec": 15826.41},
    "Neo4j AuraDB": {"time_sec": 62.16, "nodes_sec": 1008.40, "rels_sec": 2011.05},
    "CognoDB Cloud": {"time_sec": 86.46, "nodes_sec": 724.96, "rels_sec": 1445.78},
}


def run_complete_benchmark() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    console.print(Panel("[bold green]Starting Graph Database Benchmark Execution[/bold green]", expand=False))
    console.print("[dim]Running warm-up (10 iter) + measured runs (100 iter) across all 5 databases...[/dim]\n")

    csv_rows: list[dict[str, Any]] = []
    summary_data: dict[str, dict[str, Any]] = {db: {} for db in DATABASES}

    for db_name in DATABASES:
        console.print(f"\n[bold cyan]=== Benchmarking {db_name} ===[/bold cyan]")

        # A. Load Throughput (recorded from load phase)
        load_info = LOAD_METRICS.get(db_name, {})
        summary_data[db_name]["load_sec"] = load_info.get("time_sec", 0.0)
        summary_data[db_name]["load_nodes_sec"] = load_info.get("nodes_sec", 0.0)
        summary_data[db_name]["load_rels_sec"] = load_info.get("rels_sec", 0.0)

        csv_rows.append({"database": db_name, "workload": "Load Throughput", "metric": "Total Load Time", "value": load_info.get("time_sec"), "unit": "sec", "details": "62,679 nodes + 125,000 rels"})
        csv_rows.append({"database": db_name, "workload": "Load Throughput", "metric": "Node Ingest Rate", "value": load_info.get("nodes_sec"), "unit": "nodes/sec", "details": "Batch ingestion"})
        csv_rows.append({"database": db_name, "workload": "Load Throughput", "metric": "Relationship Ingest Rate", "value": load_info.get("rels_sec"), "unit": "rels/sec", "details": "Batch ingestion"})

        # B. 1-Hop Traversal
        try:
            console.print("  Executing 1-Hop Traversal...")
            h1 = benchmark_traversal(db_name, hops=1)
            summary_data[db_name]["1hop_p50"] = h1["p50"]
            summary_data[db_name]["1hop_p95"] = h1["p95"]
            csv_rows.append({"database": db_name, "workload": "1-Hop Traversal", "metric": "p50 Latency", "value": h1["p50"], "unit": "ms", "details": "10 warmup, 100 measured"})
            csv_rows.append({"database": db_name, "workload": "1-Hop Traversal", "metric": "p95 Latency", "value": h1["p95"], "unit": "ms", "details": "10 warmup, 100 measured"})
        except Exception as exc:
            console.print(f"  [red]1-Hop Traversal FAILED: {exc}[/red]")

        # C. 2-Hop Traversal
        try:
            console.print("  Executing 2-Hop Traversal...")
            h2 = benchmark_traversal(db_name, hops=2)
            summary_data[db_name]["2hop_p50"] = h2["p50"]
            summary_data[db_name]["2hop_p95"] = h2["p95"]
            csv_rows.append({"database": db_name, "workload": "2-Hop Traversal", "metric": "p50 Latency", "value": h2["p50"], "unit": "ms", "details": "10 warmup, 100 measured"})
            csv_rows.append({"database": db_name, "workload": "2-Hop Traversal", "metric": "p95 Latency", "value": h2["p95"], "unit": "ms", "details": "10 warmup, 100 measured"})
        except Exception as exc:
            console.print(f"  [red]2-Hop Traversal FAILED: {exc}[/red]")

        # D. 3-Hop Traversal
        try:
            console.print("  Executing 3-Hop Traversal...")
            h3 = benchmark_traversal(db_name, hops=3)
            summary_data[db_name]["3hop_p50"] = h3["p50"]
            summary_data[db_name]["3hop_p95"] = h3["p95"]
            csv_rows.append({"database": db_name, "workload": "3-Hop Traversal", "metric": "p50 Latency", "value": h3["p50"], "unit": "ms", "details": "10 warmup, 100 measured"})
            csv_rows.append({"database": db_name, "workload": "3-Hop Traversal", "metric": "p95 Latency", "value": h3["p95"], "unit": "ms", "details": "10 warmup, 100 measured"})
        except Exception as exc:
            console.print(f"  [red]3-Hop Traversal FAILED: {exc}[/red]")

        # E. Point Lookup
        try:
            console.print("  Executing Point Lookup...")
            pl = benchmark_point_lookup(db_name)
            summary_data[db_name]["point_p50"] = pl["p50"]
            summary_data[db_name]["point_p95"] = pl["p95"]
            csv_rows.append({"database": db_name, "workload": "Point Lookup", "metric": "p50 Latency", "value": pl["p50"], "unit": "ms", "details": "Key lookup user_id"})
            csv_rows.append({"database": db_name, "workload": "Point Lookup", "metric": "p95 Latency", "value": pl["p95"], "unit": "ms", "details": "Key lookup user_id"})
        except Exception as exc:
            console.print(f"  [red]Point Lookup FAILED: {exc}[/red]")

        # F. Filtered Lookup
        try:
            console.print("  Executing Filtered Lookup...")
            fl = benchmark_filtered_lookup(db_name)
            summary_data[db_name]["filter_p50"] = fl["p50"]
            summary_data[db_name]["filter_p95"] = fl["p95"]
            csv_rows.append({"database": db_name, "workload": "Indexed Filtered Lookup", "metric": "p50 Latency", "value": fl["p50"], "unit": "ms", "details": "WHERE age=25 AND gender=1 LIMIT 100"})
            csv_rows.append({"database": db_name, "workload": "Indexed Filtered Lookup", "metric": "p95 Latency", "value": fl["p95"], "unit": "ms", "details": "WHERE age=25 AND gender=1 LIMIT 100"})
        except Exception as exc:
            console.print(f"  [red]Filtered Lookup FAILED: {exc}[/red]")

        # G. Aggregation
        try:
            console.print("  Executing Aggregation...")
            ag = benchmark_aggregation(db_name)
            summary_data[db_name]["agg_p50"] = ag["p50"]
            summary_data[db_name]["agg_p95"] = ag["p95"]
            csv_rows.append({"database": db_name, "workload": "Aggregation", "metric": "p50 Latency", "value": ag["p50"], "unit": "ms", "details": "GROUP BY gender, COUNT, AVG(age)"})
            csv_rows.append({"database": db_name, "workload": "Aggregation", "metric": "p95 Latency", "value": ag["p95"], "unit": "ms", "details": "GROUP BY gender, COUNT, AVG(age)"})
        except Exception as exc:
            console.print(f"  [red]Aggregation FAILED: {exc}[/red]")

        # H. Concurrent Workload
        try:
            console.print("  Executing Concurrent Mixed R/W Workload (4 workers, 80/20 ratio, 10s)...")
            cw = benchmark_concurrent(db_name)
            summary_data[db_name]["qps"] = cw["sustained_qps"]
            csv_rows.append({"database": db_name, "workload": "Concurrent Mixed R/W", "metric": "Sustained QPS", "value": cw["sustained_qps"], "unit": "QPS", "details": "4 workers, 80% read / 20% write, 10s"})
        except Exception as exc:
            console.print(f"  [red]Concurrent Workload FAILED: {exc}[/red]")

        # I. Footprint
        try:
            fp = get_footprint(db_name)
            summary_data[db_name]["footprint_ram"] = fp["observable_ram_rss"]
            csv_rows.append({"database": db_name, "workload": "Resource Footprint", "metric": "Observable Memory RSS", "value": fp["observable_ram_rss"], "unit": "Memory", "details": fp["configured_ram"]})
        except Exception as exc:
            console.print(f"  [red]Footprint Inspection FAILED: {exc}[/red]")

    # Export to results/results.csv
    with open(RESULTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["database", "workload", "metric", "value", "unit", "details"])
        writer.writeheader()
        writer.writerows(csv_rows)

    console.print(f"\n[bold green]Results successfully written to {RESULTS_CSV}[/bold green]\n")

    # Display Summary Table
    display_summary_tables(summary_data)


def display_summary_tables(data: dict[str, dict[str, Any]]) -> None:
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Database", style="bold white")
    table.add_column("Load Time (s)", justify="right")
    table.add_column("Point p50 (ms)", justify="right")
    table.add_column("1-Hop p50 (ms)", justify="right")
    table.add_column("2-Hop p50 (ms)", justify="right")
    table.add_column("3-Hop p50 (ms)", justify="right")
    table.add_column("Filter p50 (ms)", justify="right")
    table.add_column("Agg p50 (ms)", justify="right")
    table.add_column("QPS (4 workers)", justify="right")

    for db, m in data.items():
        table.add_row(
            db,
            f"{m.get('load_sec', 0.0):.2f}s",
            f"{m.get('point_p50', 0.0):.2f} ms",
            f"{m.get('1hop_p50', 0.0):.2f} ms",
            f"{m.get('2hop_p50', 0.0):.2f} ms",
            f"{m.get('3hop_p50', 0.0):.2f} ms",
            f"{m.get('filter_p50', 0.0):.2f} ms",
            f"{m.get('agg_p50', 0.0):.2f} ms",
            f"{m.get('qps', 0.0):,.1f}",
        )

    console.print(Panel(table, title="Final Benchmark Execution Summary", expand=False))


if __name__ == "__main__":
    run_complete_benchmark()
