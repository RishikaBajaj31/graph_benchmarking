"""
connectors/falkordb.py — FalkorDB connection module.

FalkorDB uses a Redis-compatible wire protocol. The official
`falkordb` Python client connects via host + port (not a URI).

Local Docker defaults:
    Host: localhost
    Port: 6379
    Browser: http://localhost:3001

Usage
-----
    from benchmark.connectors.falkordb import FalkorDBConnector

    with FalkorDBConnector.from_env() as conn:
        info = conn.ping()
        print(info)
"""

from __future__ import annotations

from typing import Any

from falkordb import FalkorDB

from benchmark.config import FalkorDBConfig, load_falkordb_config

# Name of the temporary graph used only for connectivity verification.
# It is a transient empty graph and is deleted after the ping.
_PING_GRAPH_NAME = "_benchmark_ping_"


class FalkorDBConnector:
    """
    Thin wrapper around the FalkorDB Python client.

    Responsibilities
    ----------------
    * Open the connection to FalkorDB.
    * Provide a context-manager interface so callers cannot forget to close.
    * Expose ping() for connectivity verification.
    * Expose select_graph() to get a named graph handle for callers.

    Not responsible for
    -------------------
    * Query logic — kept in workload modules (future phases).
    * Graph creation or data loading.
    """

    def __init__(self, config: FalkorDBConfig) -> None:
        self._config = config
        self._client: FalkorDB = FalkorDB(
            host=config.host,
            port=config.port,
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "FalkorDBConnector":
        """Create a connector using credentials from the environment."""
        return cls(load_falkordb_config())

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "FalkorDBConnector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying Redis connection pool."""
        try:
            self._client.connection.close()
        except Exception:  # noqa: BLE001
            pass  # best-effort — no-op if already closed

    def select_graph(self, name: str) -> Any:
        """Return a FalkorDB graph handle for the given graph name."""
        return self._client.select_graph(name)

    def ping(self) -> dict[str, Any]:
        """
        Verify connectivity with a lightweight read-only query.

        Selects a temporary graph and runs `RETURN 1 AS alive`.
        FalkorDB creates the graph lazily on first write, but
        `RETURN 1` is pure computation and requires no graph data.

        Returns a dict with:
            connected   — bool
            host        — str
            port        — int
            server_info — raw PING response string from the Redis layer
        """
        # Raw Redis PING to confirm socket-level connectivity
        raw_ping = self._client.connection.ping()

        # Cypher query on a temporary graph handle (no data written)
        graph = self._client.select_graph(_PING_GRAPH_NAME)
        result = graph.query("RETURN 1 AS alive")
        alive = False
        if result.result_set:
            alive = result.result_set[0][0] == 1

        return {
            "connected": alive,
            "host": self._config.host,
            "port": self._config.port,
            "server_info": str(raw_ping),
        }
