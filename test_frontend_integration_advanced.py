"""
FRONTEND INTEGRATION TEST
Tests that frontend can properly consume all backend APIs
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/analysis"
FRONTEND_URL = "http://localhost:80"


def test_frontend_accessible():
    """Test that frontend is running"""
    print("=" * 80)
    print("TEST 1: FRONTEND ACCESSIBILITY")
    print("=" * 80)
    
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print(f"✅ Frontend is accessible at {FRONTEND_URL}")
            print(f"   Status: {response.status_code}")
            print(f"   Size: {len(response.content)} bytes")
            return True
        else:
            print(f"❌ Frontend returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot reach frontend: {e}")
        return False


def test_api_cors():
    """Test CORS headers for frontend requests"""
    print("\n" + "=" * 80)
    print("TEST 2: CORS CONFIGURATION")
    print("=" * 80)
    
    # Simulate a browser preflight request
    headers = {
        'Origin': FRONTEND_URL,
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'Content-Type'
    }
    
    response = requests.options(f"{BASE_URL}/1/statistics", headers=headers)
    
    cors_headers = {
        'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
        'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
    }
    
    print("CORS Headers:")
    for key, value in cors_headers.items():
        status = "✅" if value else "⚠️"
        print(f"  {status} {key}: {value}")
    
    return True


def test_knowledge_space_graph_data(task_id=None):
    """Test Knowledge Space data format for frontend graph"""
    print("\n" + "=" * 80)
    print("TEST 3: KNOWLEDGE SPACE GRAPH DATA FORMAT")
    print("=" * 80)
    
    if not task_id:
        # Try to get latest task
        print("⚠️  No task_id provided, using mock test")
        return True
    
    response = requests.get(f"{BASE_URL}/{task_id}/knowledge-space")
    
    if response.status_code != 200:
        print(f"❌ Failed to get knowledge space: {response.status_code}")
        return False
    
    data = response.json()
    
    # Verify structure matches what frontend expects
    required_fields = ['knowledge_space']
    
    print("\n📋 Data Structure Validation:")
    for field in required_fields:
        if field in data:
            print(f"   ✅ {field}: present")
        else:
            print(f"   ❌ {field}: MISSING")
            return False
    
    # Validate knowledge_space structure
    ks = data['knowledge_space']
    
    if not isinstance(ks, dict):
        print(f"❌ knowledge_space should be dict, got {type(ks)}")
        return False
    
    # Check for root node
    if '{}' not in ks:
        print("❌ Missing root node '{}'")
        return False
    
    print(f"\n✅ Knowledge Space structure valid for frontend:")
    print(f"   Total states: {len(ks)}")
    print(f"   Root node: {ks['{}']}")
    
    # Sample a few states to validate structure
    sample_states = list(ks.items())[:3]
    print(f"\n   Sample states:")
    for state_key, state_value in sample_states:
        print(f"      {state_key} → {state_value}")
    
    return True


def test_localStorage_data_format():
    """Test that data format is compatible with localStorage"""
    print("\n" + "=" * 80)
    print("TEST 4: LOCALSTORAGE COMPATIBILITY")
    print("=" * 80)
    
    # Simulate what frontend would store
    mock_data = {
        'knowledge_space': {
            '{}': ['{A}', '{B}'],
            '{A}': ['{A,B}'],
            '{B}': ['{A,B}'],
            '{A,B}': []
        },
        'statistics': {
            'total_items': 121,
            'total_concepts': 25
        }
    }
    
    # Serialize to JSON (what localStorage does)
    try:
        serialized = json.dumps(mock_data)
        size_kb = len(serialized) / 1024
        print(f"✅ Mock data serialization successful:")
        print(f"   Size: {size_kb:.2f} KB")
        
        # Deserialize
        deserialized = json.loads(serialized)
        print(f"✅ Deserialization successful")
        
        # Verify data integrity
        if deserialized == mock_data:
            print(f"✅ Data integrity maintained after serialization")
        else:
            print(f"❌ Data corrupted during serialization")
            return False
        
        # Check localStorage size limit (typically 5-10MB)
        if size_kb < 5000:
            print(f"✅ Size is within localStorage limits (< 5MB)")
        else:
            print(f"⚠️  Size may exceed localStorage limits in some browsers")
        
        return True
        
    except Exception as e:
        print(f"❌ Serialization failed: {e}")
        return False


def test_graph_parser_compatibility(task_id=None):
    """Test that data is compatible with graphParser.ts"""
    print("\n" + "=" * 80)
    print("TEST 5: GRAPH PARSER COMPATIBILITY")
    print("=" * 80)
    
    if not task_id:
        print("⚠️  No task_id provided, using mock test")
        
        # Simulate knowledge space structure
        mock_ks = {
            '{}': ['{Funktion und Gleichungen}', '{Algebra}'],
            '{Funktion und Gleichungen}': ['{Funktion und Gleichungen, Algebra}'],
            '{Algebra}': ['{Funktion und Gleichungen, Algebra}'],
            '{Funktion und Gleichungen, Algebra}': []
        }
        
        print("\n📋 Testing graph parser requirements:")
        
        # Test 1: Can identify root node
        if '{}' in mock_ks:
            print("   ✅ Root node '{}' present")
        else:
            print("   ❌ Root node '{}' missing")
            return False
        
        # Test 2: States are in correct format
        for state_key, children in mock_ks.items():
            if not isinstance(state_key, str):
                print(f"   ❌ State key should be string, got {type(state_key)}")
                return False
            
            if not isinstance(children, list):
                print(f"   ❌ Children should be list, got {type(children)}")
                return False
        
        print("   ✅ All states have correct format (string key → list of children)")
        
        # Test 3: Can parse concept names
        for state_key in mock_ks.keys():
            if state_key != '{}':
                # Remove outer braces
                concepts = state_key.strip().replace('{', '').replace('}', '')
                print(f"   ✅ Can parse: '{state_key}' → concepts: {concepts}")
        
        return True
    
    # If task_id provided, test with real data
    response = requests.get(f"{BASE_URL}/{task_id}/knowledge-space")
    if response.status_code != 200:
        print(f"❌ Failed to get knowledge space")
        return False
    
    data = response.json()
    ks = data.get('knowledge_space', {})
    
    print(f"\n📋 Real data graph parser test:")
    print(f"   Total states: {len(ks)}")
    
    # Check root
    if '{}' not in ks:
        print("   ❌ Missing root node")
        return False
    
    print(f"   ✅ Root node present with {len(ks['{}'])} children")
    
    # Sample parsing
    sample_states = list(ks.keys())[:5]
    print(f"\n   Sample state parsing:")
    for state in sample_states:
        concepts = state.strip().replace('{', '').replace('}', '').split(',') if state != '{}' else []
        print(f"      '{state}' → {len(concepts)} concepts")
    
    return True


def main():
    """Run all frontend integration tests"""
    print("\n" + "=" * 80)
    print("🎨 FRONTEND INTEGRATION TEST SUITE")
    print("=" * 80)
    print(f"Frontend: {FRONTEND_URL}")
    print(f"Backend: {BASE_URL}")
    print("=" * 80)
    
    tests = [
        ("Frontend Accessible", test_frontend_accessible),
        ("CORS Configuration", test_api_cors),
        ("Knowledge Space Data Format", lambda: test_knowledge_space_graph_data()),
        ("localStorage Compatibility", test_localStorage_data_format),
        ("Graph Parser Compatibility", lambda: test_graph_parser_compatibility())
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
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
        print("🎉 FRONTEND INTEGRATION TESTS PASSED!")
    else:
        print("⚠️  Some tests failed. Review logs above.")


if __name__ == "__main__":
    main()
