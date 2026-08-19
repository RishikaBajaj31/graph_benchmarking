"""
scripts/validate_dataset.py — Validation script for prepared Pokec CSV files.

Verifies and reports:
    - Final node count
    - Final relationship count
    - Duplicate relationships count
    - Missing source nodes count
    - Missing target nodes count
    - Malformed records count
"""

import csv
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
stderr_console = Console(stderr=True)

PROCESSED_DIR = Path("data/processed")
NODES_CSV = PROCESSED_DIR / "nodes.csv"
RELATIONSHIPS_CSV = PROCESSED_DIR / "relationships.csv"


def validate_dataset() -> int:
    console.print(Panel("[bold]Pokec Dataset Validation[/bold]", expand=False))

    if not NODES_CSV.exists():
        stderr_console.print(f"[bold red]Error:[/bold red] Missing {NODES_CSV}")
        return 1
    if not RELATIONSHIPS_CSV.exists():
        stderr_console.print(f"[bold red]Error:[/bold red] Missing {RELATIONSHIPS_CSV}")
        return 1

    malformed_records = 0

    # 1. Validate nodes.csv
    nodes = set()
    node_count = 0
    duplicate_nodes = 0

    with open(NODES_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or header != ["user_id", "public", "completion_percentage", "gender", "region", "age"]:
            console.print("[yellow]Warning:[/yellow] Unexpected nodes.csv header format")
            malformed_records += 1

        for line_num, row in enumerate(reader, start=2):
            if len(row) != 6:
                malformed_records += 1
                continue
            uid = row[0].strip()
            if not uid:
                malformed_records += 1
                continue
            if uid in nodes:
                duplicate_nodes += 1
            nodes.add(uid)
            node_count += 1

    # 2. Validate relationships.csv
    relationship_count = 0
    seen_relationships = set()
    duplicate_relationships = 0
    missing_source_nodes = 0
    missing_target_nodes = 0

    with open(RELATIONSHIPS_CSV, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or header != ["source", "target"]:
            console.print("[yellow]Warning:[/yellow] Unexpected relationships.csv header format")
            malformed_records += 1

        for line_num, row in enumerate(reader, start=2):
            if len(row) != 2:
                malformed_records += 1
                continue
            src, tgt = row[0].strip(), row[1].strip()
            if not src or not tgt:
                malformed_records += 1
                continue

            if (src, tgt) in seen_relationships:
                duplicate_relationships += 1
            seen_relationships.add((src, tgt))
            relationship_count += 1

            if src not in nodes:
                missing_source_nodes += 1
            if tgt not in nodes:
                missing_target_nodes += 1

    # 3. Output results table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="white")
    table.add_column("Value", style="bold green")
    table.add_column("Status", style="bold")

    is_valid = True

    # Node count check
    table.add_row("Final Node Count", f"{node_count:,}", "[green]OK[/green]")

    # Relationship count check (>= 100,000 required)
    rel_status = "[green]OK (>= 100,000)[/green]" if relationship_count >= 100000 else "[red]FAIL (< 100,000)[/red]"
    if relationship_count < 100000:
        is_valid = False
    table.add_row("Final Relationship Count", f"{relationship_count:,}", rel_status)

    # Duplicates check
    dup_status = "[green]0[/green]" if duplicate_relationships == 0 else f"[red]{duplicate_relationships}[/red]"
    if duplicate_relationships > 0:
        is_valid = False
    table.add_row("Duplicate Relationships", f"{duplicate_relationships}", dup_status)

    # Missing source nodes
    src_status = "[green]0[/green]" if missing_source_nodes == 0 else f"[red]{missing_source_nodes}[/red]"
    if missing_source_nodes > 0:
        is_valid = False
    table.add_row("Missing Source Nodes", f"{missing_source_nodes}", src_status)

    # Missing target nodes
    tgt_status = "[green]0[/green]" if missing_target_nodes == 0 else f"[red]{missing_target_nodes}[/red]"
    if missing_target_nodes > 0:
        is_valid = False
    table.add_row("Missing Target Nodes", f"{missing_target_nodes}", tgt_status)

    # Malformed records
    mal_status = "[green]0[/green]" if malformed_records == 0 else f"[red]{malformed_records}[/red]"
    if malformed_records > 0:
        is_valid = False
    table.add_row("Malformed Records", f"{malformed_records}", mal_status)

    console.print(table)

    if is_valid:
        console.print("\n[bold green]Dataset Validation PASSED.[/bold green]")
        return 0
    else:
        console.print("\n[bold red]Dataset Validation FAILED.[/bold red]")
        return 1


if __name__ == "__main__":
    sys.exit(validate_dataset())
