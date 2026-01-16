import json
import os

path = 'learning_space_generator/output/terminal_full/knowledge_space_lattice_k30.json'
if os.path.exists(path):
    with open(path, 'r') as f:
        data = json.load(f)
        num_states = len(data.keys())
        num_edges = sum(len(v) for v in data.values())
        
        print(f"Stats: {num_states} states, {num_edges} edges")
else:
    print("File not found")
