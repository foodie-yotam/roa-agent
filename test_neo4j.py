#!/usr/bin/env python3
"""Test Neo4j connection and check what recipes exist"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

print(f"🔗 Connecting to Neo4j...")
print(f"   URI: {NEO4J_URI}")
print(f"   User: {NEO4J_USER}")
print()

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

try:
    with driver.session() as session:
        # Test connection
        print("✅ Connected successfully!")
        print()
        
        # Check what recipes exist
        print("📋 Checking recipes in database...")
        result = session.run("MATCH (r:Recipe) RETURN r.name as name LIMIT 20")
        recipes = [record["name"] for record in result]
        
        if recipes:
            print(f"✅ Found {len(recipes)} recipes:")
            for recipe in recipes:
                print(f"   - {recipe}")
        else:
            print("❌ No recipes found in database")
        
        print()
        
        # Check kitchens
        print("🏪 Checking kitchens...")
        result = session.run("MATCH (k:Kitchen) RETURN k.name as name LIMIT 10")
        kitchens = [record["name"] for record in result]
        
        if kitchens:
            print(f"✅ Found {len(kitchens)} kitchens:")
            for kitchen in kitchens:
                print(f"   - {kitchen}")
        else:
            print("❌ No kitchens found in database")
            
        print()
        
        # Check if "arruz sushi" exists (search for similar names)
        print("🔍 Searching for 'sushi' recipes...")
        result = session.run("MATCH (r:Recipe) WHERE toLower(r.name) CONTAINS 'sushi' RETURN r.name as name")
        sushi_recipes = [record["name"] for record in result]
        
        if sushi_recipes:
            print(f"✅ Found {len(sushi_recipes)} sushi recipes:")
            for recipe in sushi_recipes:
                print(f"   - {recipe}")
        else:
            print("❌ No sushi recipes found")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.close()
