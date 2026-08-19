"""
connectors/arangodb.py — ArangoDB connection module.

ArangoDB uses HTTP/REST API via the official `python-arango` client package.

Local Docker defaults:
    Host: localhost
    Port: 8529
    Web UI: http://localhost:8529

Usage
-----
    from benchmark.connectors.arangodb import ArangoDBConnector

    with ArangoDBConnector.from_env() as conn:
        info = conn.ping()
        print(info)
"""

from __future__ import annotations

from typing import Any
from arango import ArangoClient
from arango.database import StandardDatabase

from benchmark.config import ArangoDBConfig, load_arangodb_config


class ArangoDBConnector:
    """
    Thin wrapper around the python-arango client.

    Responsibilities
    ----------------
    * Initialize connection to ArangoDB endpoint.
    * Provide a context-manager interface.
    * Expose ping() for connectivity verification against `_system` database.
    * Expose get_db() to connect to database handles.
    """

    def __init__(self, config: ArangoDBConfig) -> None:
        self._config = config
        self._client = ArangoClient(hosts=config.http_url)

    @classmethod
    def from_env(cls) -> ArangoDBConnector:
        """Create a connector using credentials from the environment."""
        return cls(load_arangodb_config())

    def __enter__(self) -> ArangoDBConnector:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close client connection / clean up resources."""
        # python-arango manages HTTP sessions internally
        pass

    def get_db(self, name: str = "_system") -> StandardDatabase:
        """Connect to specified database with configured credentials."""
        return self._client.db(
            name,
            username=self._config.username,
            password=self._config.password,
        )

    def ping(self) -> dict[str, Any]:
        """
        Verify connectivity by connecting to _system database and executing a simple read-only AQL query.

        Returns a dict with:
            connected   — bool
            host        — str
            port        — int
            version     — str (ArangoDB server version)
        """
        db = self.get_db("_system")
        version = db.version()
        cursor = db.aql.execute("RETURN 1")
        alive = False
        for doc in cursor:
            if doc == 1:
                alive = True

        return {
            "connected": alive,
            "host": self._config.host,
            "port": self._config.port,
            "version": str(version),
        }
