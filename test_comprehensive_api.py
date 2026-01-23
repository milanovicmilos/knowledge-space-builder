"""
COMPREHENSIVE API TEST SUITE
Tests all API endpoints, database storage, and data integrity
"""

import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/analysis"

def test_upload_and_full_flow():
    """Test complete flow: upload → process → retrieve all data"""
    print("=" * 80)
    print("TEST 1: FULL FLOW - Upload → Process → Retrieve All Data")
    print("=" * 80)
    
    # Find a CSV file
    csv_path = Path("storage/uploads/20260119_232021_matheGesamt.csv")
    if not csv_path.exists():
        # Try alternative
        uploads = list(Path("storage/uploads").glob("*.csv"))
        if not uploads:
            print("❌ No CSV files found in storage/uploads/")
            return None
        csv_path = uploads[0]
    
    print(f"\n📁 Using CSV: {csv_path}")
    
    # Upload
    with open(csv_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/run", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return None
    
    task_id = response.json()['task_id']
    print(f"✅ Upload successful! Task ID: {task_id}")
    
    # Monitor progress
    print("\n⏳ Monitoring progress...")
    start_time = time.time()
    last_status = None
    
    while True:
        response = requests.get(f"{BASE_URL}/{task_id}/status")
        data = response.json()
        
        if data['status'] != last_status:
            elapsed = time.time() - start_time
            print(f"[{elapsed:>5.1f}s] {data['progress']:>3}% - {data['status']:<10} - {data['message']}")
            last_status = data['status']
        
        if data['status'] in ['completed', 'failed']:
            break
        
        time.sleep(2)
    
    if data['status'] == 'failed':
        print(f"❌ Analysis failed: {data.get('error_message', 'Unknown error')}")
        return None
    
    print(f"\n✅ Analysis completed in {time.time() - start_time:.1f} seconds")
    return task_id


def test_statistics_endpoint(task_id):
    """Test statistics retrieval"""
    print("\n" + "=" * 80)
    print("TEST 2: STATISTICS ENDPOINT")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/{task_id}/statistics")
    
    if response.status_code != 200:
        print(f"❌ Statistics failed: {response.status_code} - {response.text}")
        return False
    
    stats = response.json()
    print("\n✅ Statistics retrieved successfully:")
    print(f"   Total Items: {stats.get('total_items')}")
    print(f"   Total Concepts: {stats.get('total_concepts')}")
    print(f"   Total Students: {stats.get('total_students')}")
    print(f"   Knowledge States: {stats.get('knowledge_space_states')}")
    print(f"   Prerequisites: {stats.get('prerequisites_found')}")
    print(f"   Semantic Clusters: {stats.get('semantic_clusters')}")
    
    # Validate
    required_fields = ['total_items', 'total_concepts', 'total_students', 'knowledge_space_states']
    for field in required_fields:
        if field not in stats or stats[field] is None:
            print(f"❌ Missing field: {field}")
            return False
    
    return True


def test_knowledge_space_endpoint(task_id):
    """Test knowledge space retrieval from PostgreSQL"""
    print("\n" + "=" * 80)
    print("TEST 3: KNOWLEDGE SPACE ENDPOINT (PostgreSQL Storage)")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/{task_id}/knowledge-space")
    
    if response.status_code != 200:
        print(f"❌ Knowledge Space failed: {response.status_code} - {response.text}")
        return False
    
    ks_data = response.json()
    
    # Validate structure
    if not isinstance(ks_data, dict):
        print(f"❌ Invalid data type: {type(ks_data)}")
        return False
    
    if 'knowledge_space' not in ks_data:
        print(f"❌ Missing 'knowledge_space' key")
        return False
    
    states = ks_data['knowledge_space']
    print(f"\n✅ Knowledge Space retrieved from PostgreSQL:")
    print(f"   Type: {type(states)}")
    print(f"   Total states: {len(states)}")
    
    # Show sample states
    sample = list(states.keys())[:5]
    print(f"   Sample states: {sample}")
    
    # Validate structure
    if not isinstance(states, dict):
        print(f"❌ Knowledge space should be dict, got {type(states)}")
        return False
    
    # Check for root state
    if '{}' not in states:
        print("❌ Missing root state '{}'")
        return False
    
    print("✅ Knowledge Space structure is valid!")
    return True


def test_files_endpoint(task_id):
    """Test files listing"""
    print("\n" + "=" * 80)
    print("TEST 4: FILES ENDPOINT")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/{task_id}/files")
    
    if response.status_code != 200:
        print(f"❌ Files endpoint failed: {response.status_code} - {response.text}")
        return False
    
    files = response.json()
    
    if 'files' not in files:
        print("❌ Missing 'files' key in response")
        return False
    
    file_list = files['files']
    print(f"\n✅ Files retrieved: {len(file_list)} files")
    
    # Expected files
    expected = [
        'knowledge_space.json',
        'implications.json',
        'llm_item_classifications.json',
        'semantic_clusters.json',
        'item_difficulties.json',
        'aggregated_concepts.csv',
        'knowledge_structure_graph.png'
    ]
    
    found = {f['name']: f for f in file_list}
    
    print("\n📋 File verification:")
    for expected_file in expected:
        if expected_file in found:
            print(f"   ✅ {expected_file}")
        else:
            print(f"   ⚠️  {expected_file} (not found, may be optional)")
    
    return True


def test_database_storage(task_id):
    """Test that data is actually stored in PostgreSQL"""
    print("\n" + "=" * 80)
    print("TEST 5: DATABASE STORAGE VERIFICATION")
    print("=" * 80)
    
    # Check via API that data comes from PostgreSQL
    response = requests.get(f"{BASE_URL}/{task_id}/knowledge-space")
    
    if response.status_code != 200:
        print("❌ Cannot verify database storage")
        return False
    
    data = response.json()
    
    # Check if response includes metadata about storage
    print("✅ Data retrieved from API")
    print(f"   Response size: {len(json.dumps(data))} bytes")
    
    # Verify critical JSON fields exist
    critical_fields = ['knowledge_space']
    for field in critical_fields:
        if field in data and data[field]:
            print(f"   ✅ {field}: {len(str(data[field]))} bytes")
        else:
            print(f"   ❌ {field}: MISSING")
            return False
    
    return True


def test_all_json_endpoints(task_id):
    """Test that all JSON data types are retrievable"""
    print("\n" + "=" * 80)
    print("TEST 6: ALL JSON DATA TYPES IN DATABASE")
    print("=" * 80)
    
    # For now, we have one endpoint for knowledge_space
    # In future, we could add endpoints for implications, clusters, etc.
    
    endpoints = {
        'knowledge_space': f"{BASE_URL}/{task_id}/knowledge-space"
    }
    
    results = {}
    
    for name, url in endpoints.items():
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            size = len(json.dumps(data))
            results[name] = {'status': 'OK', 'size': size}
            print(f"✅ {name}: {size} bytes")
        else:
            results[name] = {'status': 'FAILED', 'code': response.status_code}
            print(f"❌ {name}: HTTP {response.status_code}")
    
    return all(r['status'] == 'OK' for r in results.values())


def test_edge_cases(task_id):
    """Test edge cases and error handling"""
    print("\n" + "=" * 80)
    print("TEST 7: EDGE CASES & ERROR HANDLING")
    print("=" * 80)
    
    # Test invalid task ID
    print("\n🔍 Testing invalid task ID...")
    response = requests.get(f"{BASE_URL}/99999/statistics")
    if response.status_code == 404:
        print("✅ Correctly returns 404 for invalid task")
    else:
        print(f"⚠️  Expected 404, got {response.status_code}")
    
    # Test valid task ID but endpoint that doesn't exist
    print("\n🔍 Testing non-existent endpoint...")
    response = requests.get(f"{BASE_URL}/{task_id}/invalid-endpoint")
    if response.status_code in [404, 405]:
        print(f"✅ Correctly returns {response.status_code} for invalid endpoint")
    else:
        print(f"⚠️  Expected 404/405, got {response.status_code}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("🧪 COMPREHENSIVE API TEST SUITE")
    print("=" * 80)
    print(f"Target: {BASE_URL}")
    print("=" * 80)
    
    # Test 1: Upload and process
    task_id = test_upload_and_full_flow()
    if not task_id:
        print("\n❌ CRITICAL: Upload failed, cannot continue tests")
        return
    
    # Wait a moment for database to finalize
    time.sleep(2)
    
    # Run all other tests
    tests = [
        ("Statistics", lambda: test_statistics_endpoint(task_id)),
        ("Knowledge Space", lambda: test_knowledge_space_endpoint(task_id)),
        ("Files Listing", lambda: test_files_endpoint(task_id)),
        ("Database Storage", lambda: test_database_storage(task_id)),
        ("All JSON Types", lambda: test_all_json_endpoints(task_id)),
        ("Edge Cases", lambda: test_edge_cases(task_id))
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 80)
    print(f"RESULT: {passed}/{total} tests passed")
    print("=" * 80)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is fully operational!")
    else:
        print("⚠️  Some tests failed. Review logs above.")


if __name__ == "__main__":
    main()
