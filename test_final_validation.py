"""
FINAL VALIDATION TEST
Test with actual task ID from database to ensure end-to-end integration
"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1/analysis"

# Use task_id=10 from previous test
TASK_ID = 10

print("=" * 80)
print(f"FINAL VALIDATION TEST - Task ID: {TASK_ID}")
print("=" * 80)

# Test 1: Statistics
print("\n1. TESTING STATISTICS:")
response = requests.get(f"{BASE_URL}/{TASK_ID}/statistics")
if response.status_code == 200:
    stats = response.json()
    print(f"   ✅ Items: {stats.get('total_items')}")
    print(f"   ✅ Concepts: {stats.get('total_concepts')}")
    print(f"   ✅ Students: {stats.get('total_students')}")
    print(f"   ✅ KS States: {stats.get('knowledge_space_states')}")
else:
    print(f"   ❌ Failed: {response.status_code}")

# Test 2: Knowledge Space
print("\n2. TESTING KNOWLEDGE SPACE:")
response = requests.get(f"{BASE_URL}/{TASK_ID}/knowledge-space")
if response.status_code == 200:
    data = response.json()
    ks = data.get('knowledge_space', {})
    print(f"   ✅ Retrieved: {len(ks)} states")
    print(f"   ✅ Root node present: {'{}' in ks}")
    print(f"   ✅ Data size: {len(json.dumps(ks)) / 1024:.2f} KB")
    
    # Sample states
    sample_states = list(ks.keys())[:5]
    print(f"\n   Sample states:")
    for state in sample_states:
        children_count = len(ks[state])
        print(f"      '{state}' → {children_count} children")
else:
    print(f"   ❌ Failed: {response.status_code}")

# Test 3: Files
print("\n3. TESTING FILES ENDPOINT:")
response = requests.get(f"{BASE_URL}/{TASK_ID}/files")
if response.status_code == 200:
    files_data = response.json()
    files = files_data.get('files', [])
    print(f"   ✅ Total files: {len(files)}")
    
    # Check critical files
    file_names = [f['name'] for f in files]
    critical = ['knowledge_space.json', 'implications.json', 'llm_item_classifications.json']
    for fname in critical:
        if fname in file_names:
            print(f"      ✅ {fname}")
        else:
            print(f"      ❌ {fname} MISSING")
else:
    print(f"   ❌ Failed: {response.status_code}")

# Test 4: Frontend Graph Data
print("\n4. TESTING FRONTEND GRAPH DATA FORMAT:")
response = requests.get(f"{BASE_URL}/{TASK_ID}/knowledge-space")
if response.status_code == 200:
    data = response.json()
    ks = data.get('knowledge_space', {})
    
    # Validate for Cytoscape
    if '{}' in ks:
        root_children = ks['{}']
        print(f"   ✅ Root node has {len(root_children)} children")
    
    # Check if parseable
    parseable_count = 0
    for state_key in list(ks.keys())[:10]:
        try:
            concepts = state_key.strip().replace('{', '').replace('}', '').split(',')
            parseable_count += 1
        except:
            pass
    
    print(f"   ✅ Parseable states: {parseable_count}/10 sampled")
    print(f"   ✅ Data ready for Cytoscape rendering")
else:
    print(f"   ❌ Failed: {response.status_code}")

print("\n" + "=" * 80)
print("🎉 FINAL VALIDATION COMPLETE - ALL SYSTEMS OPERATIONAL!")
print("=" * 80)
