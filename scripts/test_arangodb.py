"""
scripts/test_arangodb.py — Verify ArangoDB connectivity.

Run from the project root:
    python scripts/test_arangodb.py

Exit codes:
    0 — connection successful
    1 — connection failed

Reads configuration from:
    .env file  OR  environment variables
    ARANGO_HOST     (required — e.g. localhost)
    ARANGO_PORT     (required — e.g. 8529)
    ARANGO_USERNAME (required — e.g. root)
    ARANGO_PASSWORD (required)
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from benchmark.connectors.arangodb import ArangoDBConnector

console = Console()
stderr_console = Console(stderr=True)


def _build_result_table(info: dict) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("Connected", "[green]YES[/green]" if info["connected"] else "[red]NO[/red]")
    table.add_row("Host", str(info["host"]))
    table.add_row("Port", str(info["port"]))
    table.add_row("Server Version", str(info["version"]))

    return table


def main() -> int:
    console.print(Panel("[bold]ArangoDB Connection Test[/bold]", expand=False))
    console.print("Reading configuration from environment / .env ...\n")

    try:
        with ArangoDBConnector.from_env() as conn:
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
            "  - ARANGO_HOST is set to       localhost\n"
            "  - ARANGO_PORT is set to       8529\n"
            "  - ARANGO_USERNAME is set to   root\n"
            "  - ARANGO_PASSWORD is correct\n"
            "  - Docker container is running (docker ps)\n"
            "  - ArangoDB Web UI is at       http://localhost:8529",
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
