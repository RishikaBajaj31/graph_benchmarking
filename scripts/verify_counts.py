"""
scripts/verify_counts.py — Database-side count verification script.

Queries all five graph databases directly to confirm exact node
and relationship counts:
    Expected Nodes:         62,679
    Expected Relationships: 125,000
"""

import sys
import io
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.connectors.arangodb import ArangoDBConnector
from benchmark.connectors.cognodb import CognoDBConnector
from benchmark.connectors.falkordb import FalkorDBConnector
from benchmark.connectors.memgraph import MemgraphConnector
from benchmark.connectors.neo4j import Neo4jConnector

console = Console()
stderr_console = Console(stderr=True)

EXPECTED_NODES = 62679
EXPECTED_RELS = 125000


def count_cognodb() -> tuple[int, int]:
    with CognoDBConnector.from_env() as conn:
        with conn.session() as s:
            n_res = s.run("MATCH (n:User) RETURN count(n) AS count").single()
            r_res = s.run("MATCH ()-[r:FRIEND_OF]->() RETURN count(r) AS count").single()
            return (n_res["count"] if n_res else 0, r_res["count"] if r_res else 0)


def count_neo4j() -> tuple[int, int]:
    with Neo4jConnector.from_env() as conn:
        with conn.session() as s:
            n_res = s.run("MATCH (n:User) RETURN count(n) AS count").single()
            r_res = s.run("MATCH ()-[r:FRIEND_OF]->() RETURN count(r) AS count").single()
            return (n_res["count"] if n_res else 0, r_res["count"] if r_res else 0)


def count_memgraph() -> tuple[int, int]:
    with MemgraphConnector.from_env() as conn:
        with conn.session() as s:
            n_res = s.run("MATCH (n:User) RETURN count(n) AS count").single()
            r_res = s.run("MATCH ()-[r:FRIEND_OF]->() RETURN count(r) AS count").single()
            return (n_res["count"] if n_res else 0, r_res["count"] if r_res else 0)


def count_falkordb() -> tuple[int, int]:
    with FalkorDBConnector.from_env() as conn:
        graph = conn.select_graph("pokec")
        n_res = graph.query("MATCH (n:User) RETURN count(n)")
        r_res = graph.query("MATCH ()-[r:FRIEND_OF]->() RETURN count(r)")
        nodes = n_res.result_set[0][0] if n_res.result_set else 0
        rels = r_res.result_set[0][0] if r_res.result_set else 0
        return (nodes, rels)


def count_arangodb() -> tuple[int, int]:
    with ArangoDBConnector.from_env() as conn:
        db = conn.get_db("pokec")
        n_count = db.collection("User").count()
        r_count = db.collection("FRIEND_OF").count()
        return (n_count, r_count)


def verify_all() -> int:
    console.print(Panel("[bold]Database Post-Load Count Verification[/bold]", expand=False))

    targets: list[tuple[str, Any]] = [
        ("CognoDB Cloud", count_cognodb),
        ("Neo4j AuraDB", count_neo4j),
        ("Memgraph", count_memgraph),
        ("FalkorDB", count_falkordb),
        ("ArangoDB", count_arangodb),
    ]

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Database", style="white")
    table.add_column("Node Count", style="bold")
    table.add_column("Relationship Count", style="bold")
    table.add_column("Status", style="bold")

    all_passed = True

    for name, count_fn in targets:
        try:
            nodes, rels = count_fn()
            nodes_ok = nodes == EXPECTED_NODES
            rels_ok = rels == EXPECTED_RELS

            if nodes_ok and rels_ok:
                status = "[green]PASSED[/green]"
            else:
                status = "[red]FAILED[/red]"
                all_passed = False

            table.add_row(
                name,
                f"{nodes:,}" if nodes_ok else f"[red]{nodes:,}[/red]",
                f"{rels:,}" if rels_ok else f"[red]{rels:,}[/red]",
                status,
            )
        except Exception as exc:  # noqa: BLE001
            table.add_row(name, "[red]ERR[/red]", "[red]ERR[/red]", f"[red]ERROR: {type(exc).__name__}[/red]")
            all_passed = False

    console.print(table)

    if all_passed:
        console.print("\n[bold green]All database count verifications PASSED.[/bold green]")
        return 0
    else:
        console.print("\n[bold red]Count verification FAILED for one or more databases.[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(verify_all())
