"""
connectors/cognodb.py — CognoDB Cloud connection module.

CognoDB is Neo4j-protocol-compatible, so we use the official
`neo4j` Python driver pointed at the Bolt+S endpoint.

Usage
-----
    from benchmark.connectors.cognodb import CognoDBConnector

    with CognoDBConnector.from_env() as conn:
        info = conn.ping()
        print(info)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

from neo4j import GraphDatabase, Driver, Session

from benchmark.config import CognoDBConfig, load_cognodb_config

# Driver-level defaults — tweak if the free tier needs more lenient timeouts
_CONNECTION_TIMEOUT_SECONDS = 30
_MAX_TRANSACTION_RETRY_TIME_SECONDS = 15


class CognoDBConnector:
    """
    Thin wrapper around the Neo4j Driver for CognoDB Cloud.

    Responsibilities
    ----------------
    * Open / close the underlying Bolt connection.
    * Provide a context-manager interface so callers cannot forget to close.
    * Expose a ping() helper for connectivity verification.
    * Expose a session() context-manager for running arbitrary Cypher.

    Not responsible for
    -------------------
    * Query logic — kept in workload modules (future phases).
    * Result parsing — callers receive raw neo4j Record objects.
    """

    def __init__(self, config: CognoDBConfig) -> None:
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
    def from_env(cls) -> "CognoDBConnector":
        """Create a connector using credentials from the environment."""
        return cls(load_cognodb_config())

    # ------------------------------------------------------------------
    # Context-manager support  (with CognoDBConnector.from_env() as c:)
    # ------------------------------------------------------------------

    def __enter__(self) -> "CognoDBConnector":
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
            db_name     — name of the connected database
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
