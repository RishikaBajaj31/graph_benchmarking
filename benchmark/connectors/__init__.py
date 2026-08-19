"""
connectors — one module per database platform.

Each connector exposes a consistent interface:
    connect()   → returns a live connection / session factory
    close()     → cleanly tears it down
    ping()      → verifies connectivity

Current implementations:
    cognodb     — CognoDB Cloud (Bolt+S, Neo4j-compatible driver)

Planned:
    neo4j_aura, falkordb, memgraph, kuzu
"""
