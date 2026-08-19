"""
Scratch query verification test for all 5 database connectors.
"""

import random
from benchmark.connectors.cognodb import CognoDBConnector
from benchmark.connectors.neo4j import Neo4jConnector
from benchmark.connectors.memgraph import MemgraphConnector
from benchmark.connectors.falkordb import FalkorDBConnector
from benchmark.connectors.arangodb import ArangoDBConnector
from benchmark.loaders.dataset import load_nodes_csv

nodes = load_nodes_csv()
sample_user_ids = [n["user_id"] for n in random.sample(nodes, 100)]
test_id = sample_user_ids[0]

print(f"Sample test user_id: {test_id}")

# 1. CognoDB
print("\n--- CognoDB Queries ---")
with CognoDBConnector.from_env() as conn:
    with conn.session() as s:
        # Point lookup
        res = s.run("MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age", uid=test_id).single()
        print("  Point Lookup:", res.data() if res else None)
        # Filtered lookup
        res = s.run("MATCH (u:User) WHERE u.age = 25 AND u.gender = 1 RETURN u.user_id LIMIT 5").data()
        print("  Filtered Lookup count:", len(res))
        # 1-hop
        res = s.run("MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt) AS c", uid=test_id).single()
        print("  1-Hop count:", res["c"])
        # 2-hop
        res = s.run("MATCH (src:User {user_id: $uid})-[:FRIEND_OF*2]->(tgt:User) RETURN count(DISTINCT tgt) AS c", uid=test_id).single()
        print("  2-Hop count:", res["c"])
        # 3-hop
        res = s.run("MATCH (src:User {user_id: $uid})-[:FRIEND_OF*3]->(tgt:User) RETURN count(DISTINCT tgt) AS c", uid=test_id).single()
        print("  3-Hop count:", res["c"])
        # Aggregation
        res = s.run("MATCH (u:User) RETURN u.gender AS gender, count(u) AS count, avg(u.age) AS avg_age").data()
        print("  Aggregation:", res)

# 2. Neo4j
print("\n--- Neo4j Queries ---")
with Neo4jConnector.from_env() as conn:
    with conn.session() as s:
        res = s.run("MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age", uid=test_id).single()
        print("  Point Lookup:", res.data() if res else None)
        res = s.run("MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt) AS c", uid=test_id).single()
        print("  1-Hop count:", res["c"])
        res = s.run("MATCH (u:User) RETURN u.gender AS gender, count(u) AS count, avg(u.age) AS avg_age").data()
        print("  Aggregation:", res)

# 3. Memgraph
print("\n--- Memgraph Queries ---")
with MemgraphConnector.from_env() as conn:
    with conn.session() as s:
        res = s.run("MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age", uid=test_id).single()
        print("  Point Lookup:", res.data() if res else None)
        res = s.run("MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt) AS c", uid=test_id).single()
        print("  1-Hop count:", res["c"])
        res = s.run("MATCH (u:User) RETURN u.gender AS gender, count(u) AS count, avg(u.age) AS avg_age").data()
        print("  Aggregation:", res)

# 4. FalkorDB
print("\n--- FalkorDB Queries ---")
with FalkorDBConnector.from_env() as conn:
    graph = conn.select_graph("pokec")
    res = graph.query("MATCH (u:User {user_id: $uid}) RETURN u.user_id, u.age", {"uid": test_id})
    print("  Point Lookup:", res.result_set)
    res = graph.query("MATCH (src:User {user_id: $uid})-[:FRIEND_OF]->(tgt:User) RETURN count(tgt)", {"uid": test_id})
    print("  1-Hop count:", res.result_set[0][0])
    res = graph.query("MATCH (u:User) RETURN u.gender, count(u), avg(u.age)")
    print("  Aggregation:", res.result_set)

# 5. ArangoDB
print("\n--- ArangoDB Queries ---")
with ArangoDBConnector.from_env() as conn:
    db = conn.get_db("pokec")
    cursor = db.aql.execute("FOR u IN User FILTER u.user_id == @uid RETURN {user_id: u.user_id, age: u.age}", bind_vars={"uid": test_id})
    print("  Point Lookup:", list(cursor))
    cursor = db.aql.execute("FOR src IN User FILTER src.user_id == @uid FOR v IN 1..1 OUTBOUND src FRIEND_OF RETURN v.user_id", bind_vars={"uid": test_id})
    print("  1-Hop count:", len(list(cursor)))
    cursor = db.aql.execute("FOR u IN User COLLECT gender = u.gender WITH COUNT INTO cnt AGGREGATE avg_age = AVG(u.age) RETURN {gender: gender, count: cnt, avg_age: avg_age}")
    print("  Aggregation:", list(cursor))

print("\nAll 5 DB queries verified successfully!")
