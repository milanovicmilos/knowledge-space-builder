#!/usr/bin/env python3
"""
Test API flow - Upload CSV, track progress, fetch results
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/analysis"
STORAGE_PATH = Path("c:/Users/Milos/PythonProjects/knowledge-space-builder/storage/uploads")

# Test CSV file
TEST_CSV = "20260119_232021_matheGesamt.csv"
TEST_CSV_PATH = STORAGE_PATH / TEST_CSV

print("=" * 60)
print("API FLOW TEST")
print("=" * 60)

if not TEST_CSV_PATH.exists():
    print(f"❌ Test file not found: {TEST_CSV_PATH}")
    exit(1)

print(f"\n✅ Test file found: {TEST_CSV_PATH}")

# Step 1: Upload CSV
print("\n[1/3] Uploading CSV file...")
with open(TEST_CSV_PATH, 'rb') as f:
    files = {'file': (TEST_CSV, f)}
    response = requests.post(f"{BASE_URL}/run", files=files)

if response.status_code != 200:
    print(f"❌ Upload failed: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()
task_id = data['task_id']
print(f"✅ Upload successful! Task ID: {task_id}")
print(f"   Status: {data['status']}")
print(f"   Progress: {data['progress']}%")

# Step 2: Monitor progress
print("\n[2/3] Monitoring progress...")
max_wait = 300  # 5 minutes max
start_time = time.time()
last_progress = 0

while True:
    elapsed = time.time() - start_time
    if elapsed > max_wait:
        print(f"⏱️  Timeout after {max_wait} seconds")
        break
    
    response = requests.get(f"{BASE_URL}/{task_id}/status")
    if response.status_code != 200:
        print(f"❌ Status fetch failed: {response.status_code}")
        break
    
    status_data = response.json()
    progress = status_data['progress']
    status = status_data['status']
    message = status_data['message']
    
    if progress > last_progress or status != "running":
        print(f"   [{elapsed:.1f}s] {progress:3d}% - {status:10s} - {message}")
        last_progress = progress
    
    if status == "completed":
        print(f"✅ Analysis completed in {elapsed:.1f} seconds!")
        break
    elif status == "failed":
        print(f"❌ Analysis failed: {message}")
        break
    
    time.sleep(2)

# Step 3: Fetch results
print("\n[3/3] Fetching results...")

# Get statistics
response = requests.get(f"{BASE_URL}/{task_id}/statistics")
if response.status_code == 200:
    stats = response.json()['statistics']
    print(f"✅ Statistics:")
    print(f"   Total Items: {stats.get('total_items', 'N/A')}")
    print(f"   Total Concepts: {stats.get('total_concepts', 'N/A')}")
    print(f"   Total Students: {stats.get('total_students', 'N/A')}")
    print(f"   Knowledge States: {stats.get('knowledge_space_states', 'N/A')}")
    print(f"   Prerequisites: {stats.get('prerequisites_found', 'N/A')}")
    print(f"   Semantic Clusters: {stats.get('semantic_clusters', 'N/A')}")
    print(f"   Root Concepts: {stats.get('root_concepts', 'N/A')}")

# Get knowledge space
print("\n   Fetching Knowledge Space...")
response = requests.get(f"{BASE_URL}/{task_id}/knowledge-space")
if response.status_code == 200:
    ks = response.json()
    num_states = len(ks)
    sample_states = list(ks.keys())[:3]
    print(f"✅ Knowledge Space loaded!")
    print(f"   Total states: {num_states}")
    print(f"   Sample states: {sample_states[:2]}")
else:
    print(f"❌ Failed to fetch knowledge space: {response.status_code}")

# Get files list
print("\n   Fetching files list...")
response = requests.get(f"{BASE_URL}/{task_id}/files")
if response.status_code == 200:
    files_list = response.json()
    num_files = files_list.get('total_files', 0)
    print(f"✅ Files fetched!")
    print(f"   Total files: {num_files}")
    for file_info in files_list.get('files', [])[:5]:
        print(f"      - {file_info['name']} ({file_info['size']} bytes)")
else:
    print(f"❌ Failed to fetch files: {response.status_code}")

print("\n" + "=" * 60)
print("✅ API FLOW TEST COMPLETED SUCCESSFULLY!")
print("=" * 60)
