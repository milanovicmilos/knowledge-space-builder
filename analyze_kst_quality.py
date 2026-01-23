import json
import itertools
from collections import deque

def check_closure_under_union(states_set):
    """
    KST Axiom 1: A knowledge structure is a knowledge space if it is closed under union.
    If K is a space, s1 in K and s2 in K implies (s1 U s2) in K.
    Returns: bool (is_space), list of missing states
    """
    missing = []
    # Test random pairs to save time if large, or all pairs if manageable.
    # 39k states is too large for O(N^2) exhaustive check in a quick script (~1.5 billion pairs).
    # We will test a sample.
    states_list = list(states_set)
    sample_size = min(len(states_list), 1000)
    import random
    random.seed(42)
    sample = random.sample(states_list, sample_size)
    
    count = 0
    failures = 0
    for i in range(len(sample)):
        for j in range(i + 1, len(sample)):
            s1 = sample[i]
            s2 = sample[j]
            union_state = s1.union(s2)
            if union_state not in states_set:
                failures += 1
                if failures < 5:
                    missing.append(union_state)
            count += 1
            if count > 5000: break # Limit check
        if count > 5000: break
    
    return failures == 0, failures

def check_well_gradedness(graph, states_set):
    """
    KST Property: Well-gradedness (or learning paths).
    A space is well-graded if for any states K, L with K subset L, there exists a chain
    K = S0 < S1 < ... < Sn = L where dist(Si, Si+1) = 1.
    Often simplified: Can we build the space item by item?
    We'll check if every non-empty state has a predecessor in the space with size - 1.
    """
    failures = []
    for state in states_set:
        if len(state) == 0: continue
        
        # Look for a predecessor
        found_pred = False
        state_list = list(state)
        for item in state_list:
            pred = set(state_list)
            pred.remove(item)
            if frozenset(pred) in states_set:
                found_pred = True
                break
        
        if not found_pred:
            failures.append(state)
            if len(failures) > 5: break
            
    return len(failures) == 0, failures

def analyze():
    # Load Knowledge Space
    print("Loading Knowledge Space...")
    try:
        with open('learning_space_generator/output/knowledge_space.json', 'r') as f:
            ks_data = json.load(f)
    except FileNotFoundError:
        print("Knowledge space file not found.")
        return

    # Convert string keys "{a, b}" to sets
    states_set = set()
    states_map = {}
    
    for k in ks_data.keys():
        if k == "{}":
            s = frozenset()
        else:
            # remove { and }
            content = k[1:-1]
            if not content: s = frozenset()
            else:
                items = [x.strip() for x in content.split(',')]
                s = frozenset(items)
        states_set.add(s)
        states_map[k] = s

    print(f"Total States: {len(states_set)}")
    
    # 1. Closure under Union
    print("\nChecking Closure under Union (Sampling)...")
    is_closed, miss_count = check_closure_under_union(states_set)
    print(f"Result: {'PASS' if is_closed else 'FAIL'}")
    if not is_closed:
        print(f"Failed on sample pairs. Found {miss_count} missing unions.")
        print("Note: Partial generation (pruning) often breaks strict closure under union, creating a 'Knowledge Structure' rather than a 'Space'.")

    # 2. Well-Gradedness
    print("\nChecking Well-Gradedness (Fringe Property)...")
    is_wg, bad_states = check_well_gradedness(ks_data, states_set)
    print(f"Result: {'PASS' if is_wg else 'FAIL'}")
    if not is_wg:
        print(f"Found states without immediate predecessors (size-1 subset in space): {len(bad_states)} examples found.")
        print(f"Example orphan state: {next(iter(bad_states)) if bad_states else ''}")

    # 3. Domain Analysis from Implications
    print("\nAnalyzing Implications (Prerequisites)...")
    try:
        with open('learning_space_generator/output/implications.json', 'r') as f:
            edges = json.load(f)
    except:
        edges = []
        
    print(f"Total Implication Rules: {len(edges)}")
    
    # Example chain
    g = {}
    for e in edges:
        src, tgt = e['source'], e['target']
        if src not in g: g[src] = []
        g[src].append(tgt)
        
    print("Top Prerequisite Concepts (most dependencies):")
    sorted_nodes = sorted(g.keys(), key=lambda k: len(g[k]), reverse=True)
    for n in sorted_nodes[:5]:
        print(f"  - {n} is prerequisite for {len(g[n])} concepts")

if __name__ == "__main__":
    analyze()
