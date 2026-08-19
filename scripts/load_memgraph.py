"""
scripts/load_memgraph.py — Load Pokec dataset into Memgraph.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.loaders.memgraph_loader import load_memgraph

console = Console()
stderr_console = Console(stderr=True)


def main() -> int:
    console.print(Panel("[bold]Memgraph Dataset Loader[/bold]", expand=False))

    try:
        metrics = load_memgraph()

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="white")
        table.add_column("Value", style="bold green")

        table.add_row("Platform", metrics["platform"])
        table.add_row("Start Time", metrics["start_time"])
        table.add_row("End Time", metrics["end_time"])
        table.add_row("Total Load Time", f"{metrics['total_load_time_sec']}s")
        table.add_row("Batch Size", f"{metrics['batch_size']:,}")
        table.add_row("Nodes Loaded", f"{metrics['nodes_loaded']:,}")
        table.add_row("Relationships Loaded", f"{metrics['relationships_loaded']:,}")
        table.add_row("Nodes / Second", f"{metrics['nodes_per_sec']:,}")
        table.add_row("Relationships / Second", f"{metrics['relationships_per_sec']:,}")

        console.print(table)
        console.print("\n[bold green]Memgraph loading COMPLETE.[/bold green]")
        return 0

    except Exception as exc:  # noqa: BLE001
        stderr_console.print(f"[bold red]Loading FAILED:[/bold red] {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
