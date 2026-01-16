"""Check optimization results and compare with previous runs."""
import json
from pathlib import Path

def analyze_results(test_dir):
    """Analyze results from a test directory."""
    test_path = Path(test_dir)
    
    if not test_path.exists():
        print(f"❌ Directory {test_dir} does not exist yet")
        return None
        
    summary_file = test_path / "knowledge_space_k30_summary.json"
    if not summary_file.exists():
        # Try to find any summary file
        summary_files = list(test_path.glob("knowledge_space_k*_summary.json"))
        if not summary_files:
            print(f"⏳ {test_dir} - optimization still running (no summary file yet)")
            return None
        summary_file = summary_files[0]
    
    with open(summary_file) as f:
        summary = json.load(f)
    
    num_states = summary.get("num_states", 0)
    num_components = summary.get("weak_components", 0)
    num_edges = summary.get("num_edges", 0)
    
    print(f"\n📊 {test_dir}:")
    print(f"   States: {num_states}")
    print(f"   Components: {num_components}")
    print(f"   Edges: {num_edges}")
    
    if num_states < 10:
        print(f"   ⚠️  TRIVIAL GRAPH (< 10 states)")
    if num_components > 1:
        print(f"   ⚠️  FRAGMENTED ({num_components} components)")
    if num_states >= 10 and num_components == 1:
        print(f"   ✅ GOOD: Connected graph with meaningful size")
    
    return {
        "states": num_states,
        "components": num_components,
        "edges": num_edges
    }

if __name__ == "__main__":
    print("=" * 60)
    print("OPTIMIZATION RESULTS COMPARISON")
    print("=" * 60)
    
    test1 = analyze_results("output/matheGesamt_test")
    test2 = analyze_results("output/matheGesamt_test2")
    test3 = analyze_results("output/matheGesamt_test3")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Test 1 (original scoring): Fragmentation scoring only")
    print("Test 2 (v2 scoring): Quadratic state_count_penalty")
    print("Test 3 (v3 scoring): EXPONENTIAL state_count_penalty + 40% weight")
    print("=" * 60)
