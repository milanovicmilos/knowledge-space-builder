#!/usr/bin/env python3
import json

with open('learning_space_generator/data/profesor_example.json', 'r', encoding='utf-8') as f:
    ks = json.load(f)

print("PROFESOROV Knowledge Space - SVA STANJA:")
print("="*80)

for i, (state, next_states) in enumerate(ks.items(), 1):
    concepts = state.strip('{}')
    if concepts:
        count = len(concepts.split(','))
        concept_list = [c.strip() for c in concepts.split(',')]
    else:
        count = 0
        concept_list = []
    
    print(f"\n{i:2}. Stanje: {state}")
    print(f"    Broj koncepata: {count}")
    if concept_list:
        print(f"    Koncepti: {concept_list}")
    print(f"    Ide do: {next_states}")

print("\n" + "="*80)
print("STATISTIKA:")
all_concepts = set()
for state in ks.keys():
    concepts = state.strip('{}')
    if concepts:
        all_concepts.update([c.strip() for c in concepts.split(',')])

print(f"Svi koncepti: {sorted(all_concepts)}")
print(f"Ukupno koncepata: {len(all_concepts)}")

max_state = None
max_count = 0
for state in ks.keys():
    concepts = state.strip('{}')
    if concepts:
        count = len(concepts.split(','))
    else:
        count = 0
    if count > max_count:
        max_count = count
        max_state = state

print(f"\nMaksimalno stanje: {max_state}")
print(f"Sa {max_count} koncepata od {len(all_concepts)}")

if max_count == len(all_concepts):
    print("\n✅ SVI koncepti su dostižni odjednom!")
else:
    print(f"\n⚠️  Samo {max_count}/{len(all_concepts)} koncepata u jednom stanju!")
    missing = all_concepts - set([c.strip() for c in max_state.strip('{}').split(',')])
    print(f"Nedostaje: {missing}")
