"""
DATABASE DIRECT INSPECTION
Check PostgreSQL database content directly
"""

import psycopg2
import json

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="knowledge_space_builder",
    user="postgres",
    password="postgres"
)

cursor = conn.cursor()

print("=" * 80)
print("DATABASE INSPECTION")
print("=" * 80)

# Check tasks
print("\n📋 TASKS TABLE:")
cursor.execute("""
    SELECT id, status, progress, message, created_at 
    FROM tasks 
    ORDER BY created_at DESC 
    LIMIT 5
""")

tasks = cursor.fetchall()
for task in tasks:
    print(f"  Task {task[0]}: {task[1]} ({task[2]}%) - {task[3]}")

# Check results
print("\n📊 RESULTS TABLE:")
cursor.execute("""
    SELECT 
        id, 
        task_id, 
        total_items, 
        total_concepts, 
        total_students,
        knowledge_space_states,
        prerequisites_found,
        semantic_clusters,
        storage_location,
        source,
        created_at,
        CASE WHEN knowledge_space IS NOT NULL THEN 'YES' ELSE 'NO' END as has_ks,
        CASE WHEN implications IS NOT NULL THEN 'YES' ELSE 'NO' END as has_impl,
        CASE WHEN llm_classifications IS NOT NULL THEN 'YES' ELSE 'NO' END as has_llm
    FROM results 
    ORDER BY created_at DESC 
    LIMIT 5
""")

results = cursor.fetchall()
for result in results:
    print(f"\n  Result ID: {result[0]}")
    print(f"    Task ID: {result[1]}")
    print(f"    Items: {result[2]}, Concepts: {result[3]}, Students: {result[4]}")
    print(f"    KS States: {result[5]}, Prerequisites: {result[6]}, Clusters: {result[7]}")
    print(f"    Storage: {result[8]} ({result[9]})")
    print(f"    JSON Data: KS={result[11]}, Implications={result[12]}, LLM={result[13]}")
    print(f"    Created: {result[10]}")

# Check if knowledge_space JSON exists for latest result
print("\n🔍 CHECKING JSON DATA FOR LATEST RESULT:")
cursor.execute("""
    SELECT 
        id,
        jsonb_typeof(knowledge_space) as ks_type,
        CASE 
            WHEN knowledge_space IS NOT NULL 
            THEN jsonb_object_keys(knowledge_space) 
            ELSE NULL 
        END as ks_keys_sample
    FROM results 
    WHERE knowledge_space IS NOT NULL
    ORDER BY created_at DESC 
    LIMIT 1
""")

latest = cursor.fetchone()
if latest:
    print(f"  Result ID: {latest[0]}")
    print(f"  Knowledge Space Type: {latest[1]}")
    print(f"  Has keys: {latest[2] is not None}")
else:
    print("  ❌ No results with knowledge_space found!")

# Check one specific result with details
print("\n🔬 DETAILED INSPECTION OF LATEST RESULT:")
cursor.execute("""
    SELECT 
        id,
        task_id,
        total_items,
        total_concepts,
        knowledge_space_states,
        pg_column_size(knowledge_space) as ks_size_bytes,
        pg_column_size(implications) as impl_size_bytes,
        pg_column_size(llm_classifications) as llm_size_bytes
    FROM results 
    ORDER BY created_at DESC 
    LIMIT 1
""")

detail = cursor.fetchone()
if detail:
    print(f"  Result ID: {detail[0]}")
    print(f"  Task ID: {detail[1]}")
    print(f"  Statistics: {detail[2]} items, {detail[3]} concepts, {detail[4]} states")
    print(f"  Data Sizes:")
    print(f"    Knowledge Space: {detail[5] or 0} bytes ({(detail[5] or 0) / 1024:.2f} KB)")
    print(f"    Implications: {detail[6] or 0} bytes ({(detail[6] or 0) / 1024:.2f} KB)")
    print(f"    LLM Classifications: {detail[7] or 0} bytes ({(detail[7] or 0) / 1024:.2f} KB)")

cursor.close()
conn.close()

print("\n" + "=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)
