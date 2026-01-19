import json
import pandas as pd
import networkx as nx
from collections import deque

def run_json_generation():
    print("Loading implications...")
    try:
        with open('data/implications.json', 'r') as f:
            implications = json.load(f)
    except FileNotFoundError:
        print("Error: data/implications.json not found.")
        return

    # 1. Build PREREQUISITE map
    # Edge u -> v means u is prereq for v.
    prereqs = {}
    items = set()
    
    # Also need all items from the original data if not in implications
    # But for now, let's assume items in implications cover most, 
    # except isolated ones.
    # We should really load the item list from CSV to be sure we include isolated items.
    
    try:
        df = pd.read_csv('data/cleaned_responses.csv')
        all_items = set([c for c in df.columns if c != 'standort'])
    except:
        all_items = set()
        for edge in implications:
            all_items.add(edge['source'])
            all_items.add(edge['target'])
            
    items = sorted(list(all_items))
    item_to_id = {name: i for i, name in enumerate(items)}
    
    for item in items:
        prereqs[item] = set()

    for edge in implications:
        u, v = edge['source'], edge['target']
        if v in prereqs:
            prereqs[v].add(u)
        else: # Should not happen if initialized
            prereqs[v] = {u}

    print(f"Total items: {len(items)}")

    # 2. Generate States (Ideals of the Poset)
    # Start with Empty Set.
    # Find all items whose prereqs are satisfied.
    
    # We represent state as a frozezenset of item names
    initial_state = frozenset()
    
    # Structure for JSON: { "{a, b}": ["{a, b, c}", ...], ... }
    # We use string representation as key
    
    ks_graph = {} # Adjacency list for states
    
    queue = deque([initial_state])
    visited = {initial_state}
    
    # Check for explosion
    MAX_STATES = 5000
    
    print("Generating knowledge states...")
    
    while queue:
        current_state = queue.popleft()
        
        # Prepare key string
        # Sort items for consistent string key
        # Format: "{a, b, c}"
        # If empty: "{}"
        curr_list = sorted(list(current_state))
        if not curr_list:
            curr_key = "{}"
        else:
            curr_str = ", ".join(curr_list)
            curr_key = "{" + curr_str + "}"
            
        if curr_key not in ks_graph:
            ks_graph[curr_key] = []
            
        # Find successors (Covering relation)
        # Identify items 'x' not in current_state such that prereqs[x] <= current_state
        candidates = []
        for item in items:
            if item not in current_state:
                if prereqs[item].issubset(current_state):
                    candidates.append(item)
        
        # Add edges
        for item in candidates:
            next_state = current_state | {item}
            
            # Format next key
            next_list = sorted(list(next_state))
            next_str = ", ".join(next_list)
            next_key = "{" + next_str + "}"
            
            # Add to graph
            ks_graph[curr_key].append(next_key)
            
            if next_state not in visited:
                visited.add(next_state)
                queue.append(next_state)
                
                if len(visited) > MAX_STATES:
                    print(f"WARNING: State space explosion! Stopped at {MAX_STATES} states.")
                    # We continue just to finish the queue/graph for CURRENT nodes
                    # but stop adding new ones?
                    # Actually, better to break.
                    break
        
        if len(visited) > MAX_STATES:
            break

    print(f"Generated {len(visited)} states.")
    
    # 3. Save to JSON
    output_path = 'data/knowledge_space.json'
    with open(output_path, 'w') as f:
        json.dump(ks_graph, f, indent=2)
        
    print(f"Saved knowledge space to {output_path}")

if __name__ == "__main__":
    run_json_generation()
