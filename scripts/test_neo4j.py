"""
scripts/test_neo4j.py — Verify Neo4j AuraDB connectivity.

Run from the project root:
    python scripts/test_neo4j.py

Exit codes:
    0 — connection successful
    1 — connection failed

Reads credentials from:
    .env file  OR  environment variables
    NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.connectors.neo4j import Neo4jConnector

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
    console.print(Panel("[bold]Neo4j AuraDB Connection Test[/bold]", expand=False))
    console.print("Reading credentials from environment / .env ...\n")

    try:
        with Neo4jConnector.from_env() as conn:
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
            "  - NEO4J_URI starts with   neo4j+s://\n"
            "  - NEO4J_USERNAME matches  the AuraDB instance username\n"
            "  - NEO4J_PASSWORD matches  the AuraDB instance password\n"
            "  - Your AuraDB instance is in the RUNNING state",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
