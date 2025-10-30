"""Database connections and utilities"""
import os
from neo4j import GraphDatabase

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print(f"✅ Connected to Neo4j at {NEO4J_URI}")
except Exception as e:
    print(f"⚠️  Neo4j connection failed: {e}")
    driver = None


def run_query(query: str, params: dict = None):
    """Execute a Neo4j query and return results"""
    if not driver:
        return []
    
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]
