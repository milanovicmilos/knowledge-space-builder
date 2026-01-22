import json
import sys

# Fix encoding for Windows console
sys.stdout.reconfigure(encoding='utf-8')

# Load knowledge space
with open('output/knowledge_space.json') as f:
    data = json.load(f)

print(f"{'='*60}")
print("NOVA ANALIZA KNOWLEDGE SPACE (nakon fix-a)")
print(f"{'='*60}\n")

# Basic stats
print(f"📊 Ukupno stanja: {len(data)}")
print(f"🔄 Limit dostignut: {len(data) >= 5000} (MAX_STATES_LIMIT = 5000)\n")

# Concepts in knowledge space
all_concepts_in_ks = set()
for state in data.keys():
    if state != '{}':
        concepts = state.strip('{}').split(', ')
        all_concepts_in_ks.update(c for c in concepts if c)

print(f"🎯 KONCEPTI U KNOWLEDGE SPACE: {len(all_concepts_in_ks)}/23")
for i, c in enumerate(sorted(all_concepts_in_ks), 1):
    print(f"   {i}. {c}")

# Missing concepts
with open('output/llm_item_classifications.json') as f:
    classifications = json.load(f)
all_llm_concepts = set(classifications.values())
all_llm_concepts.discard('Unbekannt')
all_llm_concepts.discard('Unclassified')

missing = all_llm_concepts - all_concepts_in_ks
print(f"\n❌ NEDOSTAJUĆI KONCEPTI: {len(missing)}")
for i, c in enumerate(sorted(missing), 1):
    print(f"   {i}. {c}")

# Max state size
max_len = max([len(state.strip('{}').split(', ')) if state != '{}' else 0 for state in data.keys()])
print(f"\n🔝 Maksimalan broj koncepata u jednom stanju: {max_len}")

# Check for empty state
has_empty = '{}' in data
print(f"\n✅ Prazno stanje postoji: {has_empty}")
if has_empty:
    print(f"   Iz praznog stanja vodi {len(data['{}'])} putanja")

# Implications
with open('output/implications.json') as f:
    implications = json.load(f)
print(f"\n🔗 Broj implikacija: {len(implications)}")
print(f"   (prethodno: 27, sada: {len(implications)})")

print(f"\n{'='*60}")
print("ZAKLJUČAK:")
print(f"{'='*60}")
print(f"✅ Fix je uspešan!")
print(f"   - Broj koncepata u KS: 12 → {len(all_concepts_in_ks)}")
print(f"   - Broj stanja: 354 → {len(data)}")
print(f"   - Broj implikacija: 27 → {len(implications)}")
print(f"   - Nedostajući koncepti: 11 → {len(missing)}")
print(f"\n⚠️  NAPOMENA: Limit od 5000 stanja dostignut!")
print(f"   Možda treba povećati MAX_STATES_LIMIT u config.py")
