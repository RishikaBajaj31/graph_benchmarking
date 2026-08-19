# Graph Database Benchmarking Suite

A reproducible benchmarking suite comparing **CognoDB Cloud**, **Neo4j AuraDB**, **Memgraph**, **FalkorDB**, and **ArangoDB** on an identical Pokec social network dataset.

---

## Executive Summary

### 50th Percentile Latencies (p50) & Throughput

| Platform | Deployment | Configured vCPU / RAM | Total Load Time (s) | Point Lookup p50 (ms) | 1-Hop Traversal p50 (ms) | 2-Hop Traversal p50 (ms) | 3-Hop Traversal p50 (ms) | Filtered Lookup p50 (ms) | Aggregation p50 (ms) | Sustained QPS (4 workers) |
|---|---|---|---|---|---|---|---|---|---|---|
| **ArangoDB** | Docker (Local) | 0.5 vCPU / 256 MB | 6.07 s | 58.90 ms | 55.51 ms | 61.74 ms | 59.53 ms | 43.47 ms | 67.02 ms | 17.96 QPS |
| **FalkorDB** | Docker (Local) | 0.5 vCPU / 256 MB | 12.32 s | 0.91 ms | 0.97 ms | 0.89 ms | 0.96 ms | 2.24 ms | 15.58 ms | 1150.23 QPS |
| **Memgraph** | Docker (Local) | 0.5 vCPU / 1024 MB* | 7.90 s | 1.16 ms | 1.17 ms | 1.07 ms | 1.13 ms | 3.91 ms | 68.93 ms | 1349.01 QPS |
| **Neo4j AuraDB** | Managed Cloud | Undisclosed (Free Tier) | 62.16 s | 90.15 ms | 91.24 ms | 91.69 ms | 91.57 ms | 97.63 ms | 117.40 ms | 36.57 QPS |
| **CognoDB Cloud** | Managed Cloud | 0.5 vCPU / 256 MB (c0 tier) | 86.46 s | 245.63 ms | 248.73 ms | 249.89 ms | 267.91 ms | 280.70 ms | 394.15 ms | 13.64 QPS |

### 95th Percentile Latencies (p95)

| Platform | Point Lookup p95 (ms) | 1-Hop Traversal p95 (ms) | 2-Hop Traversal p95 (ms) | 3-Hop Traversal p95 (ms) | Filtered Lookup p95 (ms) | Aggregation p95 (ms) |
|---|---|---|---|---|---|---|
| **ArangoDB** | 65.28 ms | 64.33 ms | 70.25 ms | 67.17 ms | 45.88 ms | 74.56 ms |
| **FalkorDB** | 1.70 ms | 2.04 ms | 1.66 ms | 2.38 ms | 2.96 ms | 59.83 ms |
| **Memgraph** | 1.77 ms | 2.06 ms | 1.71 ms | 2.03 ms | 5.00 ms | 78.02 ms |
| **Neo4j AuraDB** | 95.61 ms | 96.17 ms | 96.66 ms | 103.64 ms | 140.14 ms | 125.19 ms |
| **CognoDB Cloud** | 317.54 ms | 261.77 ms | 267.51 ms | 325.24 ms | 298.06 ms | 485.35 ms |

*\*Memgraph required a resource allocation adjustment to 1024 MB RAM to support the multi-process supervisor platform engine and in-memory graph structures without OOM failure.*

> **Resource Asymmetry & Hardware Limitations Disclaimer**:
> The five databases in this benchmark did **not** run on identical hardware resources due to platform architectural differences and tier constraints:
> - **FalkorDB & ArangoDB**: Docker containers constrained strictly to the reference tier (**0.5 vCPU / 256 MB RAM**).
> - **Memgraph**: Required **0.5 vCPU / 1024 MB RAM** due to startup OOM failures at 256 MB and 512 MB.
> - **CognoDB Cloud**: Managed cloud instance running on the **c0 reference tier** (**0.5 vCPU burstable / 256 MB RAM / 1 GB storage limit**).
> - **Neo4j AuraDB**: Managed cloud instance on the Free Tier with undisclosed server hardware allocations.
> - **Network Latency**: Local Docker containers (ArangoDB, FalkorDB, Memgraph) run over local loopback (`localhost`), whereas managed cloud results include client-to-cloud network overhead.

---

## Dataset Specifications

- **Source**: SNAP `soc-Pokec` relationships (`soc-pokec-relationships.txt.gz`) and user profiles (`soc-pokec-profiles.txt.gz`) from https://snap.stanford.edu/data/soc-Pokec.html
- **Sampling Methodology**: Deterministic streaming prefix sampling.
- **Node Count**: **62,679**
- **Relationship Count**: **125,000**
- **Dataset Properties**:
  - `user_id`: Integer primary key (indexed).
  - `public`: Integer flag (0/1).
  - `completion_percentage`: Integer.
  - `gender`: Integer flag (0/1).
  - `region`: String.
  - `age`: Integer.

---

## Resource Setup & Fairness Audit

### Reference Tier
The benchmark reference tier is defined as: **0.5 vCPU / 256 MB RAM / 1 GB Storage**.

### Database Configuration & Resource Limits

1. **FalkorDB** (Docker): `0.5 vCPU / 256 MB RAM` limit applied (`--cpus="0.5" --memory="256m"`). In-memory Redis module architecture. Fully operational at reference specs.
2. **ArangoDB** (Docker): `0.5 vCPU / 256 MB RAM` limit applied (`--cpus="0.5" --memory="256m"`). RocksDB storage engine. Fully operational at reference specs.
3. **Memgraph** (Docker): Attempted `0.5 vCPU / 256 MB RAM` and `512 MB RAM`. The container failed with OOM (`exit status 137`) during platform supervisord initialization and batch loading. Configured to **0.5 vCPU / 1024 MB RAM** as minimum operational limit.
4. **CognoDB Cloud**: Managed cloud instance (c0 reference tier: 0.5 vCPU burstable, 256 MB RAM, 1 GB storage limit).
5. **Neo4j AuraDB**: Managed cloud instance (Free Tier: undisclosed vCPU/RAM hardware allocation).

---

## Benchmark Workloads & Methodology

Each read latency workload executes **10 warm-up iterations** (excluded from measurements) followed by **100 measured iterations**. High-resolution timers (`time.perf_counter()`) measure execution latency. Percentiles p50 and p95 are calculated from measured iterations.

### Workload Definitions & Query Equivalence

1. **Load Throughput**: Measure total ingest time, nodes/sec, and rels/sec for batch ingestion of the identical CSV dataset.
2. **1-Hop Traversal**: Find 1-hop outgoing friends for random start nodes.
   - *Cypher*: `MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt)`
   - *AQL*: `FOR src IN User FILTER src.user_id == @uid FOR v IN 1..1 OUTBOUND src FRIEND_OF RETURN v._key`
3. **2-Hop Traversal**: Find distinct 2-hop friends.
   - *Cypher*: `MATCH (src:User {user_id: $uid})-[:FRIEND_OF*2]->(tgt:User) RETURN count(DISTINCT tgt)`
   - *AQL*: `FOR src IN User FILTER src.user_id == @uid FOR v IN 2..2 OUTBOUND src FRIEND_OF RETURN DISTINCT v._key`
4. **3-Hop Traversal**: Find distinct 3-hop friends.
   - *Cypher*: `MATCH (src:User {user_id: $uid})-[:FRIEND_OF*3]->(tgt:User) RETURN count(DISTINCT tgt)`
   - *AQL*: `FOR src IN User FILTER src.user_id == @uid FOR v IN 3..3 OUTBOUND src FRIEND_OF RETURN DISTINCT v._key`
5. **Point Lookup**: Retrieve node properties by primary key `user_id`.
6. **Indexed / Filtered Lookup**: Multi-property filter query: `WHERE age = 25 AND gender = 1 LIMIT 100`.
7. **Aggregation**: `GROUP BY gender`, count users, compute `AVG(age)`.
8. **Concurrent Mixed Read/Write Workload**: 4 worker threads running 80% point lookups and 20% property update writes for 10 seconds.
9. **Resource Footprint**: Record active RAM RSS memory usage and storage engine architecture.

---

## Reproduction Instructions

### 1. Environment Setup

```bash
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate   # On Linux/macOS
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file from `.env.example`:

```bash
COGNODB_URI=bolt+s://<your-cognodb-endpoint>
COGNODB_USERNAME=cognodb
COGNODB_PASSWORD=<your-password>

NEO4J_URI=neo4j+s://<your-aura-endpoint>
NEO4J_USERNAME=<your-username>
NEO4J_PASSWORD=<your-password>

MEMGRAPH_URI=bolt://localhost:7687
FALKORDB_HOST=localhost
FALKORDB_PORT=6379

ARANGO_HOST=localhost
ARANGO_PORT=8529
ARANGO_USERNAME=root
ARANGO_PASSWORD=<your-password>
```

### 3. Run Docker Database Containers with Resource Limits

```bash
# FalkorDB (0.5 vCPU, 256MB RAM)
docker run -d --name falkordb --cpus="0.5" --memory="256m" --memory-swap="256m" -p 6379:6379 -p 3001:3000 falkordb/falkordb:latest

# ArangoDB (0.5 vCPU, 256MB RAM)
docker run -d --name arangodb --cpus="0.5" --memory="256m" --memory-swap="256m" -p 8529:8529 -v arangodb_data:/var/lib/arangodb3 -v arangodb_apps:/var/lib/arangodb3-apps -e ARANGO_ROOT_PASSWORD=<your-password> arangodb:latest

# Memgraph (0.5 vCPU, 1024MB RAM)
docker run -d --name memgraph --cpus="0.5" --memory="1024m" --memory-swap="1024m" -p 7687:7687 -p 3000:3000 memgraph/memgraph-platform
```

### 4. Data Preparation & Loading

```bash
# Generate deterministic dataset
python scripts/prepare_dataset.py

# Validate dataset integrity (62,679 nodes, 125,000 rels)
python scripts/validate_dataset.py

# Load dataset into all five databases
python scripts/load_all.py

# Verify database-side node and relationship counts
python scripts/verify_counts.py
```

### 5. Execute Complete Benchmark Suite

```bash
python scripts/run_benchmark.py
```

The benchmark outputs detailed CSV results to `results/results.csv` and prints a summary table.

---

## Output Location

- Machine-readable results: `results/results.csv`
- Implementation code: `benchmark/` and `scripts/`
