"""
scripts/load_all.py — Sequential dataset loader runner for all 5 platforms.

Runs loaders in sequence:
    1. ArangoDB
    2. FalkorDB
    3. Memgraph
    4. CognoDB Cloud
    5. Neo4j AuraDB
Followed by count verification.
"""

import sys
import os


from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.loaders.arangodb_loader import load_arangodb
from benchmark.loaders.cognodb_loader import load_cognodb
from benchmark.loaders.falkordb_loader import load_falkordb
from benchmark.loaders.memgraph_loader import load_memgraph
from benchmark.loaders.neo4j_loader import load_neo4j
try:
    from scripts.verify_counts import verify_all
except ModuleNotFoundError:
    from verify_counts import verify_all


console = Console()


def main() -> int:
    console.print(Panel("[bold]Graph Benchmarking — Complete Dataset Loader Suite[/bold]", expand=False))

    loaders = [
        ("ArangoDB", load_arangodb),
        ("FalkorDB", load_falkordb),
        ("Memgraph", load_memgraph),
        ("CognoDB Cloud", load_cognodb),
        ("Neo4j AuraDB", load_neo4j),
    ]

    results = []

    for name, loader_fn in loaders:
        console.print(f"\n[bold cyan]>>> Loading {name} ...[/bold cyan]")
        try:
            m = loader_fn()
            results.append(m)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[bold red]FAILED to load {name}: {exc}[/bold red]")

    # Print comparative loading summary table
    summary_table = Table(show_header=True, header_style="bold cyan")
    summary_table.add_column("Platform", style="white")
    summary_table.add_column("Nodes", style="bold")
    summary_table.add_column("Relationships", style="bold")
    summary_table.add_column("Load Time (s)", style="bold yellow")
    summary_table.add_column("Nodes/sec", style="bold green")
    summary_table.add_column("Rels/sec", style="bold green")

    for r in results:
        summary_table.add_row(
            r["platform"],
            f"{r['nodes_loaded']:,}",
            f"{r['relationships_loaded']:,}",
            f"{r['total_load_time_sec']}s",
            f"{r['nodes_per_sec']:,}",
            f"{r['relationships_per_sec']:,}",
        )

    console.print("\n")
    console.print(Panel("[bold]Data Ingest Summary[/bold]", expand=False))
    console.print(summary_table)

    console.print("\n[bold cyan]>>> Running Database-Side Count Verification ...[/bold cyan]")
    return verify_all()


if __name__ == "__main__":
    sys.exit(main())
