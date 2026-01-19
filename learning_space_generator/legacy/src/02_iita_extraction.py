import pandas as pd
import numpy as np
import networkx as nx
import json
import os

def run_iita_extraction():
    print("Loading cleaned data...")
    try:
        data = pd.read_csv('data/cleaned_responses.csv')
    except FileNotFoundError:
        print("Error: data/cleaned_responses.csv not found. Run step 01 first.")
        return

    items = data.columns.tolist()
    # Assuming the first column might be 'standort' or ID if it's not a question.
    # Checking previous output: 'standort' was present.
    # We should exclude non-item columns.
    # The columns starting with 's' followed by numbers look like items. 
    # Let's heuristically drop columns that look like metadata if needed, 
    # or rely on the fact that preprocessing might have handled it.
    # In 01_data_preprocessing, I see: "standort" and "s1m..." columns.
    # I should drop "standort" if it exists.
    
    if 'standort' in items:
        data = data.drop(columns=['standort'])
        items = data.columns.tolist()

    n_items = len(items)
    n_students = len(data)
    print(f"Items: {n_items}, Students: {n_students}")

    # Calculate Counter-Example Matrix (b_xy)
    # entry [i, j] = count of students who failed i (0) but solved j (1)
    # Hypothesized relation: i -> j (i is prereq for j)
    # Violation: failed i, solved j.
    
    print("Calculating implication metrics...")
    
    # Convert to numpy for speed
    X = data.values 
    # X shape: (students, items)
    
    # We want count(X[:, i] == 0 AND X[:, j] == 1) for all i, j
    # This is equivalent to dot product of (1-X)^T  and X
    # Let NotX = 1 - X (where 0 becomes 1, 1 becomes 0)
    # Matrix B = (NotX.T) @ X
    # B[i, j] = sum_k (NotX[k, i] * X[k, j]) 
    #         = sum_k ( (1 if x_ki==0) * (1 if x_kj==1) )
    #         = count of (0, 1) patterns for i -> j
    
    NotX = 1 - X
    B = np.dot(NotX.T, X)
    
    # Set diagonal to infinity or ignore (i -> i is always true, error 0, but trivial)
    np.fill_diagonal(B, n_students) # Ignore self-loops for now

    # Thresholding
    # diff values are effectively the entries in B.
    # We check if B[i, j] / n_students < threshold_rate
    
    threshold_rate = 0.05 # 5% tolerance
    max_exceptions = n_students * threshold_rate
    
    print(f"Applying threshold: Max exceptions = {max_exceptions:.2f} ({threshold_rate*100}%)")
    
    implications = []
    
    for i in range(n_items):
        for j in range(n_items):
            if i == j: continue
            if B[i, j] <= max_exceptions:
                # Valid implication i -> j
                implications.append((items[i], items[j]))
    
    print(f"Change 1: Found {len(implications)} raw implications.")
    
    # Check if graph is cyclic. KST assumes partial order (DAG).
    # If cyclic, we might need to break cycles or just let transitive reduction handle/fail.
    G = nx.DiGraph()
    G.add_nodes_from(items)
    G.add_edges_from(implications)
    
    if not nx.is_directed_acyclic_graph(G):
        print("Warning: Graph contains cycles. Removing cycles using feedback arc set heuristic (simple approx).")
        # For simplicity in this demo, we might drop edges contributing to cycles 
        # or just proceed. cycles break 'transitive_reduction'.
        # A simple approach: remove edge with highest error count in the cycle?
        # For now, let's trust the logic usually yields DAGs or close to it. 
        # If not, we remove back-edges in DFS.
        while not nx.is_directed_acyclic_graph(G):
            cycle = nx.find_cycle(G)
            # Remove the edge in the cycle with specific property? 
            # Or just the last one.
            G.remove_edge(*cycle[-1])
            
    print("Performing transitive reduction...")
    # Transitive reduction: Remove A->C if A->B->C exists.
    TR = nx.transitive_reduction(G)
    
    # Get reduced edges
    reduced_edges = list(TR.edges())
    print(f"Reduced to {len(reduced_edges)} essential edges.")
    
    # Save results
    output_path = 'data/implications.json'
    output_data = [
        {"source": u, "target": v} for u, v in reduced_edges
    ]
    
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
        
    print(f"Saved implications to {output_path}")

if __name__ == "__main__":
    run_iita_extraction()
