"""
Migrate production data to Neo4j Aura Cloud (automatic)
"""
import csv
import json
from neo4j import GraphDatabase

# Neo4j CLOUD connection
NEO4J_URI = "neo4j+s://e3726068.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "G9i5LgmTpcWW_82gHk6UzrxoXIA76m6zkgtKaoDIrOc"

print(f"Connecting to: {NEO4J_URI}")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def clear_database():
    """Clear all existing data"""
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    print("🗑️  Database cleared")

def parse_csv(csv_path):
    """Parse the CSV and extract entities"""
    kitchens = {}
    recipes = {}
    categories = set()
    components = {}
    recipe_components = []
    recipe_requires = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            kitchen_name = row['kitchen_name']
            kitchen_type = row['kitchen_type']
            recipe_name = row['recipe_name']
            directions = row['directions']
            time = row['time']
            category_name = row['category_name']
            component_name = row['component_name']
            component_type = row['component_type']
            amount = row['amount']
            unit = row['unit']
            
            if recipe_name == 'null' or not recipe_name:
                if kitchen_name not in kitchens:
                    kitchens[kitchen_name] = kitchen_type
                continue
            
            if kitchen_name not in kitchens:
                kitchens[kitchen_name] = kitchen_type
            
            recipe_key = (kitchen_name, recipe_name)
            if recipe_key not in recipes:
                try:
                    directions_list = json.loads(directions.replace("'", '"')) if directions != 'null' else []
                except:
                    directions_list = []
                
                time_minutes = 0
                if time and time != 'null':
                    parts = time.split(':')
                    time_minutes = int(parts[0]) * 60 + int(parts[1])
                
                recipes[recipe_key] = {
                    'name': recipe_name,
                    'kitchen': kitchen_name,
                    'directions': directions_list,
                    'time_minutes': time_minutes,
                    'category': category_name if category_name != 'null' else None
                }
            
            if category_name and category_name != 'null':
                categories.add((kitchen_name, category_name))
            
            if component_name and component_name != 'null':
                if component_type == 'Preparation':
                    if amount and amount != 'null':
                        recipe_requires.append({
                            'parent_recipe': recipe_key,
                            'sub_recipe_name': component_name,
                            'sub_recipe_kitchen': kitchen_name,
                            'amount': float(amount),
                            'unit': unit if unit != 'null' else 'prep'
                        })
                else:
                    comp_key = (kitchen_name, component_name)
                    if comp_key not in components:
                        components[comp_key] = component_type if component_type != 'null' else 'Raw_Ingredient'
                    
                    if amount and amount != 'null':
                        recipe_components.append({
                            'recipe': recipe_key,
                            'component': comp_key,
                            'amount': float(amount),
                            'unit': unit if unit != 'null' else 'unit'
                        })
    
    return kitchens, recipes, categories, components, recipe_components, recipe_requires

def load_to_neo4j(kitchens, recipes, categories, components, recipe_components, recipe_requires):
    """Load data into Neo4j"""
    with driver.session() as session:
        print("\n📦 Creating kitchens...")
        for kitchen_name, kitchen_type in kitchens.items():
            session.run("""
                CREATE (k:Kitchen {
                    kitchen_id: randomUUID(),
                    name: $name,
                    type: $type
                })
            """, name=kitchen_name, type=kitchen_type)
        print(f"✅ Created {len(kitchens)} kitchens")
        
        print("\n📁 Creating categories...")
        for kitchen_name, category_name in categories:
            session.run("""
                MATCH (k:Kitchen {name: $kitchen_name})
                CREATE (c:Category {
                    category_id: randomUUID(),
                    name: $category_name
                })
                CREATE (k)-[:HAS_CATEGORY]->(c)
            """, kitchen_name=kitchen_name, category_name=category_name)
        print(f"✅ Created {len(categories)} categories")
        
        print("\n🥕 Creating components...")
        for (kitchen_name, component_name), component_type in components.items():
            session.run("""
                MATCH (k:Kitchen {name: $kitchen_name})
                CREATE (c:Component {
                    component_id: randomUUID(),
                    name: $component_name,
                    type: $component_type
                })
                CREATE (k)-[:HAS_COMPONENT]->(c)
            """, kitchen_name=kitchen_name, component_name=component_name, component_type=component_type)
        print(f"✅ Created {len(components)} raw ingredients")
        
        print("\n🍳 Creating recipes...")
        for (kitchen_name, recipe_name), recipe_data in recipes.items():
            query = """
                MATCH (k:Kitchen {name: $kitchen_name})
                CREATE (r:Recipe {
                    recipe_id: randomUUID(),
                    name: $recipe_name,
                    directions: $directions,
                    time_minutes: $time_minutes
                })
                CREATE (k)-[:HAS_RECIPE]->(r)
            """
            
            if recipe_data['category']:
                query += """
                WITH r, k
                MATCH (c:Category {name: $category_name})<-[:HAS_CATEGORY]-(k)
                CREATE (r)-[:IN_CATEGORY]->(c)
                """
            
            session.run(query,
                kitchen_name=kitchen_name,
                recipe_name=recipe_name,
                directions=recipe_data['directions'],
                time_minutes=recipe_data['time_minutes'],
                category_name=recipe_data['category']
            )
        print(f"✅ Created {len(recipes)} recipes")
        
        print("\n🔗 Creating recipe → ingredient links...")
        for rc in recipe_components:
            kitchen_name, recipe_name = rc['recipe']
            comp_kitchen, component_name = rc['component']
            
            session.run("""
                MATCH (k:Kitchen {name: $kitchen_name})
                MATCH (k)-[:HAS_RECIPE]->(r:Recipe {name: $recipe_name})
                MATCH (k)-[:HAS_COMPONENT]->(c:Component {name: $component_name})
                MERGE (r)-[u:USES]->(c)
                SET u.amount = $amount, u.unit = $unit
            """,
                kitchen_name=kitchen_name,
                recipe_name=recipe_name,
                component_name=component_name,
                amount=rc['amount'],
                unit=rc['unit']
            )
        print(f"✅ Created {len(recipe_components)} recipe → ingredient links")
        
        print("\n🔗 Creating recipe → sub-recipe links...")
        successful = 0
        for rr in recipe_requires:
            kitchen_name, parent_recipe_name = rr['parent_recipe']
            sub_recipe_name = rr['sub_recipe_name']
            
            result = session.run("""
                MATCH (k:Kitchen {name: $kitchen_name})
                MATCH (k)-[:HAS_RECIPE]->(parent:Recipe {name: $parent_name})
                MATCH (k)-[:HAS_RECIPE]->(sub:Recipe {name: $sub_name})
                MERGE (parent)-[req:REQUIRES]->(sub)
                SET req.amount = $amount, req.unit = $unit
                RETURN parent, sub
            """,
                kitchen_name=kitchen_name,
                parent_name=parent_recipe_name,
                sub_name=sub_recipe_name,
                amount=rr['amount'],
                unit=rr['unit']
            )
            
            if result.single():
                successful += 1
                
        print(f"✅ Created {successful} recipe → sub-recipe links")

if __name__ == "__main__":
    CSV_PATH = "/home/yotambg/Desktop/Supabase Snippet Kitchen recipes with components and categories.csv"
    
    print("🚀 Migrating to Neo4j Aura Cloud")
    print("=" * 60)
    
    # Test connection
    try:
        driver.verify_connectivity()
        print("✅ Connected to Neo4j Aura!")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nMake sure:")
        print("1. URI is correct (neo4j+s://...)")
        print("2. Password is correct")
        print("3. Instance is running")
        exit(1)
    
    # Clear and migrate
    clear_database()
    
    print("\n📖 Reading CSV...")
    kitchens, recipes, categories, components, recipe_components, recipe_requires = parse_csv(CSV_PATH)
    print(f"✅ Parsed:")
    print(f"   • {len(kitchens)} kitchens")
    print(f"   • {len(recipes)} recipes")
    print(f"   • {len(categories)} categories")
    print(f"   • {len(components)} ingredients")
    print(f"   • {len(recipe_components)} ingredient links")
    print(f"   • {len(recipe_requires)} sub-recipe links")
    
    print("\n💾 Loading to cloud...")
    load_to_neo4j(kitchens, recipes, categories, components, recipe_components, recipe_requires)
    
    print("\n✅ Migration to cloud complete!")
    print(f"🌐 Your data is now in Neo4j Aura!")
    print(f"🔗 Instance: e3726068.databases.neo4j.io")
    
    driver.close()
