"""
connectors/neo4j.py — Neo4j AuraDB connection module.

Neo4j AuraDB uses the official neo4j Python driver over the
neo4j+s:// (Bolt+TLS) scheme.

Usage
-----
    from benchmark.connectors.neo4j import Neo4jConnector

    with Neo4jConnector.from_env() as conn:
        info = conn.ping()
        print(info)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from neo4j import GraphDatabase, Driver, Session

from benchmark.config import Neo4jConfig, load_neo4j_config

_CONNECTION_TIMEOUT_SECONDS = 30
_MAX_TRANSACTION_RETRY_TIME_SECONDS = 15


class Neo4jConnector:
    """
    Thin wrapper around the Neo4j Driver for Neo4j AuraDB.

    Responsibilities
    ----------------
    * Open / close the underlying Bolt+TLS connection to AuraDB.
    * Provide a context-manager interface.
    * Expose ping() for connectivity verification.
    * Expose session() for running arbitrary Cypher.

    Not responsible for
    -------------------
    * Query logic — kept in workload modules (future phases).
    """

    def __init__(self, config: Neo4jConfig) -> None:
        self._config = config
        self._driver: Driver = GraphDatabase.driver(
            config.uri,
            auth=(config.username, config.password),
            connection_timeout=_CONNECTION_TIMEOUT_SECONDS,
            max_transaction_retry_time=_MAX_TRANSACTION_RETRY_TIME_SECONDS,
        )

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> "Neo4jConnector":
        """Create a connector using credentials from the environment."""
        return cls(load_neo4j_config())

    # ------------------------------------------------------------------
    # Context-manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "Neo4jConnector":
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
