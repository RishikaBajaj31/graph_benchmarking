"""
benchmark/workloads/footprint.py — Database footprint inspection.
"""

from __future__ import annotations

import subprocess
from typing import Any


def _get_docker_container_stats(container_name: str) -> dict[str, str]:
    try:
        cmd = [
            "docker", "stats", "--no-stream",
            "--format", "{{.MemUsage}} | {{.CPUPerc}}",
            container_name
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        if "|" in out:
            mem, cpu = out.split("|")
            return {"memory": mem.strip(), "cpu_pct": cpu.strip()}
    except Exception:
        pass
    return {"memory": "Not observable", "cpu_pct": "Not observable"}


def get_footprint(db_name: str) -> dict[str, Any]:
    """
    Return resource specs, observable memory, and storage footprint for the database.
    """
    if db_name == "CognoDB Cloud":
        return {
            "database": db_name,
            "deployment": "Managed Cloud",
            "configured_cpu": "0.5 vCPU (burstable)",
            "configured_ram": "512 MB",
            "storage_engine": "CognoDB Native Graph",
            "observable_ram_rss": "Not observable",
            "observable_storage_size": "Not observable (cloud managed)",
        }
    elif db_name == "Neo4j AuraDB":
        return {
            "database": db_name,
            "deployment": "Managed Cloud",
            "configured_cpu": "Undisclosed (Free Tier)",
            "configured_ram": "Undisclosed (Free Tier)",
            "storage_engine": "Neo4j Native Store",
            "observable_ram_rss": "Not observable",
            "observable_storage_size": "Not observable (cloud managed)",
        }
    elif db_name == "Memgraph":
        stats = _get_docker_container_stats("memgraph")
        return {
            "database": db_name,
            "deployment": "Docker (Local)",
            "configured_cpu": "0.5 vCPU",
            "configured_ram": "1024 MB (Limit)",
            "storage_engine": "In-Memory C++",
            "observable_ram_rss": stats["memory"],
            "observable_storage_size": "In-Memory (RAM)",
        }
    elif db_name == "FalkorDB":
        stats = _get_docker_container_stats("falkordb")
        return {
            "database": db_name,
            "deployment": "Docker (Local)",
            "configured_cpu": "0.5 vCPU",
            "configured_ram": "256 MB (Limit)",
            "storage_engine": "In-Memory Graph Engine (Redis module)",
            "observable_ram_rss": stats["memory"],
            "observable_storage_size": "In-Memory (RAM)",
        }
    elif db_name == "ArangoDB":
        stats = _get_docker_container_stats("arangodb")
        return {
            "database": db_name,
            "deployment": "Docker (Local)",
            "configured_cpu": "0.5 vCPU",
            "configured_ram": "256 MB (Limit)",
            "storage_engine": "RocksDB (Persistent)",
            "observable_ram_rss": stats["memory"],
            "observable_storage_size": "Disk (RocksDB SST)",
        }
    else:
        raise ValueError(f"Unknown database: {db_name}")
