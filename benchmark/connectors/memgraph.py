"""
connectors/memgraph.py — Memgraph connection module.

Memgraph implements the Bolt protocol and is fully compatible
with the official neo4j Python driver. No additional driver needed.

Local Docker default: bolt://localhost:7687
Memgraph Lab UI:      http://localhost:3000

Usage
-----
    from benchmark.connectors.memgraph import MemgraphConnector

    with MemgraphConnector.from_env() as conn:
        info = conn.ping()
        print(info)

Compatibility note
------------------
Memgraph >= v2.11 advertises its own server name and does not require
any extra configuration. For older versions, start Memgraph with:
    --bolt-server-name-for-init=Neo4j/5.2.0
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from neo4j import GraphDatabase, Driver, Session

from benchmark.config import MemgraphConfig, load_memgraph_config

_CONNECTION_TIMEOUT_SECONDS = 30
_MAX_TRANSACTION_RETRY_TIME_SECONDS = 15


class MemgraphConnector:
    """
    Thin wrapper around the Neo4j Driver pointed at a Memgraph Bolt endpoint.

    Responsibilities
    ----------------
    * Open / close the Bolt connection to Memgraph.
    * Provide a context-manager interface.
    * Expose ping() for connectivity verification.
    * Expose session() for running arbitrary Cypher.

    Not responsible for
    -------------------
    * Query logic — kept in workload modules (future phases).
    """

    def __init__(self, config: MemgraphConfig) -> None:
        self._config = config
        # Memgraph accepts username/password auth; if both are empty the
        # driver still connects (anonymous auth is allowed by default).
        auth = (config.username, config.password) if config.username else None
        self._driver: Driver = GraphDatabase.driver(
            config.uri,
            auth=auth,
            connection_timeout=_CONNECTION_TIMEOUT_SECONDS,
            max_transaction_retry_time=_MAX_TRANSACTION_RETRY_TIME_SECONDS,
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "MemgraphConnector":
        """Create a connector using credentials from the environment."""
        return cls(load_memgraph_config())

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "MemgraphConnector":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the driver and all underlying connections."""
        self._driver.close()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Yield a Neo4j Session; closes it on exit even if an exception occurs."""
        s = self._driver.session()
        try:
            yield s
        finally:
            s.close()

    def ping(self) -> dict[str, Any]:
        """
        Verify connectivity and return basic server information.

        Returns a dict with:
            connected   — bool
            server_info — neo4j ServerInfo object (address, agent, protocol version)
        """
        server_info = self._driver.get_server_info()
        with self.session() as s:
            result = s.run("RETURN 1 AS alive")
            record = result.single()
            alive = record["alive"] == 1 if record else False

        return {
            "connected": alive,
            "server_info": server_info,
        }
