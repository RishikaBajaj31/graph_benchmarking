"""
config.py — Load and validate environment variables for all platforms.

Reading from environment (or a .env file) keeps credentials out of source code.
Every connector imports from here; no hardcoded strings anywhere else.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load .env file if present (silently ignored in CI/CD where vars are injected)
load_dotenv()


@dataclass(frozen=True)
class CognoDBConfig:
    """Connection parameters for CognoDB Cloud."""

    uri: str
    username: str
    password: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in {
                "COGNODB_URI": self.uri,
                "COGNODB_USERNAME": self.username,
                "COGNODB_PASSWORD": self.password,
            }.items()
            if not value
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s): {', '.join(missing)}\n"
                "Copy .env.example → .env and fill in your credentials."
            )


def load_cognodb_config() -> CognoDBConfig:
    """Read CognoDB connection details from the environment."""
    return CognoDBConfig(
        uri=os.getenv("COGNODB_URI", ""),
        username=os.getenv("COGNODB_USERNAME", ""),
        password=os.getenv("COGNODB_PASSWORD", ""),
    )


@dataclass(frozen=True)
class Neo4jConfig:
    """Connection parameters for Neo4j AuraDB."""

    uri: str
    username: str
    password: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in {
                "NEO4J_URI": self.uri,
                "NEO4J_USERNAME": self.username,
                "NEO4J_PASSWORD": self.password,
            }.items()
            if not value
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s): {', '.join(missing)}\n"
                "Copy .env.example -> .env and fill in your Neo4j AuraDB credentials."
            )


def load_neo4j_config() -> Neo4jConfig:
    """Read Neo4j AuraDB connection details from the environment."""
    return Neo4jConfig(
        uri=os.getenv("NEO4J_URI", ""),
        username=os.getenv("NEO4J_USERNAME", ""),
        password=os.getenv("NEO4J_PASSWORD", ""),
    )


@dataclass(frozen=True)
class MemgraphConfig:
    """Connection parameters for Memgraph (local Docker or remote)."""

    uri: str
    username: str
    password: str

    def __post_init__(self) -> None:
        if not self.uri:
            raise EnvironmentError(
                "Missing required environment variable: MEMGRAPH_URI\n"
                "Set MEMGRAPH_URI=bolt://localhost:7687 (or your remote URI) in .env."
            )


def load_memgraph_config() -> MemgraphConfig:
    """Read Memgraph connection details from the environment."""
    return MemgraphConfig(
        uri=os.getenv("MEMGRAPH_URI", ""),
        username=os.getenv("MEMGRAPH_USERNAME", ""),
        password=os.getenv("MEMGRAPH_PASSWORD", ""),
    )


@dataclass(frozen=True)
class FalkorDBConfig:
    """
    Connection parameters for FalkorDB.

    FalkorDB uses a Redis-compatible protocol, so its client takes
    host + port rather than a URI. Both values are required.
    """

    host: str
    port: int

    def __post_init__(self) -> None:
        if not self.host:
            raise EnvironmentError(
                "Missing required environment variable: FALKORDB_HOST\n"
                "Set FALKORDB_HOST=localhost in .env."
            )
        if self.port <= 0:
            raise EnvironmentError(
                "Missing or invalid environment variable: FALKORDB_PORT\n"
                "Set FALKORDB_PORT=6379 in .env."
            )


def load_falkordb_config() -> FalkorDBConfig:
    """Read FalkorDB connection details from the environment."""
    raw_port = os.getenv("FALKORDB_PORT", "6379")
    try:
        port = int(raw_port)
    except ValueError:
        port = 0  # will fail validation in __post_init__
    return FalkorDBConfig(
        host=os.getenv("FALKORDB_HOST", ""),
        port=port,
    )


@dataclass(frozen=True)
class ArangoDBConfig:
    """Connection parameters for ArangoDB."""

    host: str
    port: int
    username: str
    password: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name, value in {
                "ARANGO_HOST": self.host,
                "ARANGO_USERNAME": self.username,
            }.items()
            if not value
        ]
        if self.port <= 0:
            missing.append("ARANGO_PORT")

        if missing:
            raise EnvironmentError(
                f"Missing or invalid required environment variable(s): {', '.join(missing)}\n"
                "Copy .env.example -> .env and fill in your ArangoDB credentials."
            )

    @property
    def http_url(self) -> str:
        """Construct HTTP URL for ArangoClient."""
        return f"http://{self.host}:{self.port}"


def load_arangodb_config() -> ArangoDBConfig:
    """Read ArangoDB connection details from the environment."""
    raw_port = os.getenv("ARANGO_PORT", "8529")
    try:
        port = int(raw_port)
    except ValueError:
        port = 0
    return ArangoDBConfig(
        host=os.getenv("ARANGO_HOST", ""),
        port=port,
        username=os.getenv("ARANGO_USERNAME", ""),
        password=os.getenv("ARANGO_PASSWORD", ""),
    )


def get_batch_size(default: int = 2500) -> int:
    """Read BATCH_SIZE environment variable for batch insertion tuning."""
    raw = os.getenv("BATCH_SIZE", str(default))
    try:
        val = int(raw)
        return val if val > 0 else default
    except ValueError:
        return default


