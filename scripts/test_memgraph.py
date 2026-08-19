"""
scripts/test_memgraph.py — Verify Memgraph connectivity.

Run from the project root:
    python scripts/test_memgraph.py

Exit codes:
    0 — connection successful
    1 — connection failed

Reads credentials from:
    .env file  OR  environment variables
    MEMGRAPH_URI       (required — e.g. bolt://localhost:7687)
    MEMGRAPH_USERNAME  (optional — leave blank for anonymous auth)
    MEMGRAPH_PASSWORD  (optional — leave blank for anonymous auth)
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.connectors.memgraph import MemgraphConnector

console = Console()
stderr_console = Console(stderr=True)


def _build_result_table(info: dict) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")

    server = info["server_info"]
    table.add_row("Connected", "[green]YES[/green]" if info["connected"] else "[red]NO[/red]")
    table.add_row("Server address", str(server.address))
    table.add_row("Server agent", str(server.agent))
    table.add_row("Protocol version", str(server.protocol_version))

    return table


def main() -> int:
    console.print(Panel("[bold]Memgraph Connection Test[/bold]", expand=False))
    console.print("Reading credentials from environment / .env ...\n")

    try:
        with MemgraphConnector.from_env() as conn:
            console.print("Connecting ...")
            info = conn.ping()

        console.print(_build_result_table(info))
        console.print("\n[bold green]Connection test PASSED.[/bold green]")
        return 0

    except EnvironmentError as exc:
        stderr_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        return 1

    except Exception as exc:  # noqa: BLE001
        stderr_console.print(
            f"[bold red]Connection FAILED:[/bold red] {type(exc).__name__}: {exc}",
        )
        stderr_console.print(
            "\nCheck that:\n"
            "  - MEMGRAPH_URI is set to   bolt://localhost:7687\n"
            "  - Docker container is      running  (docker ps)\n"
            "  - Memgraph port 7687 is    accessible\n"
            "  - Memgraph Lab is          at http://localhost:3000",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
