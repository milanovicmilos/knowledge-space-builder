#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEMANTIC WEB PRAKTIČNA DEMONSTRACIJA
Pokazuje kako se RDF ontologija koristi u praksi za adaptive tutoring
"""

import json
import sys
from pathlib import Path

# Učitaj sve potrebne fajlove
base_path = Path(__file__).parent.parent / "output"

# 1. LLM klasifikacije (121 pitanja → 23 koncepta)
with open(base_path / "llm_item_classifications.json", "r") as f:
    llm_classifications = json.load(f)

# 2. Knowledge space (355 mogućih state-ova)
with open(base_path / "knowledge_space.json", "r") as f:
    knowledge_space = json.load(f)

# 3. Semantic klasteri (24 grupe sličnih pitanja)
with open(base_path / "semantic_clusters.json", "r") as f:
    semantic_clusters = json.load(f)

# 4. Prerequisite implications (30 relacija)
with open(base_path / "implications.json", "r") as f:
    implications = json.load(f)

print("=" * 80)
print("🌐 SEMANTIC WEB DEMONSTRACIJA - INTELIGENTNI TUTOR SISTEM")
print("=" * 80)

# ============================================================================
# PRIMER 1: Kako Ontologija Mapira Pitanja na Koncepte
# ============================================================================

print("\n" + "=" * 80)
print("PRIMER 1: LLM MAPIRANJE - Od Pitanja do Semantičkog Koncepta")
print("=" * 80)

print("\n📝 Šta je LLM klasifikacija?")
print("-" * 80)
print("LLM (Large Language Model) čita svako pitanje i kaže:")
print("'Ovo pitanje je o KOM konceptu?'\n")

# Prikaži prvih 10 mapiranja
print("Primeri iz ljm_item_classifications.json:\n")
for i, (item_id, concept) in enumerate(list(llm_classifications.items())[:10]):
    print(f"  {i+1}. {item_id:12s} → '{concept}'")

print(f"\n  ... (još {len(llm_classifications) - 10} mapiranja)")
print(f"\n✅ REZULTAT: 121 pitanja maplirano na {len(set(llm_classifications.values()))} unikatan koncepta")

# ============================================================================
# PRIMER 2: Semantic Klasteri - Automatsko Grupisanje
# ============================================================================

print("\n" + "=" * 80)
print("PRIMER 2: SEMANTIC KLASTERI - Pronalaženje Sličnih Pitanja")
print("=" * 80)

print("\n🔗 Šta su semantic klasteri?")
print("-" * 80)
print("Nakon što LLM mapira pitanja, sistem koristi SentenceTransformer embeddings")
print("da pronađe koja pitanja su SEMANTIČKI SLIČNA.\n")

# Prikaži jedan klaster detaljno
first_cluster_id = list(semantic_clusters.keys())[0]
first_cluster_items = semantic_clusters[first_cluster_id]
print(f"Primer klastera broj: {first_cluster_id}")
print(f"Broj pitanja u klasteru: {len(first_cluster_items)}")
print(f"Pitanja u ovom klasteru:")
for item in first_cluster_items[:5]:
    print(f"  - {item}")
if len(first_cluster_items) > 5:
    print(f"  ... (još {len(first_cluster_items) - 5} pitanja)")

print(f"\n✅ REZULTAT: Pronađeno {len(semantic_clusters)} klastera sličnih pitanja")

# ============================================================================
# PRIMER 3: Prerequisite Implications - Učenje Redosled
# ============================================================================

print("\n" + "=" * 80)
print("PRIMER 3: PREREQUISITE IMPLICATIONS - Redosled Učenja")
print("=" * 80)

print("\n🎓 Šta su prerequisiti?")
print("-" * 80)
print("IITA algoritam analizira podatke 692 učenika i pronalazi:")
print("'Ako student NE zna KONCEPT A, često ne zna ni KONCEPT B'")
print("To znači: A je PREREQUISIT za B\n")

# Grupiraj implications po source-u
prerequisite_graph = {}
for impl in implications:
    source = impl["source"]
    target = impl["target"]
    if source not in prerequisite_graph:
        prerequisite_graph[source] = []
    prerequisite_graph[source].append(target)

# Prikaži čitav graf
print("Kompletan prerequisite graf (30 relacija):\n")
for source in sorted(prerequisite_graph.keys()):
    targets = prerequisite_graph[source]
    print(f"  {source}")
    for target in sorted(targets):
        print(f"    → {target}")

print(f"\n✅ REZULTAT: {len(implications)} prerequisite relacija pronađeno")

# ============================================================================
# PRIMER 4: Knowledge Space - Moguća Stanja Učenika
# ============================================================================

print("\n" + "=" * 80)
print("PRIMER 4: KNOWLEDGE SPACE - Putanja Učenika")
print("=" * 80)

print("\n📊 Šta je knowledge space?")
print("-" * 80)
print(f"Sve moguće kombinacije znanja koje su validne.")
print(f"Kombinacija je VALIDNA ako su svi prerequisiti zadovoljeni.\n")

# Prikaži nekoliko primenih states
all_states = list(knowledge_space.keys())
sample_states = all_states[:15]
print(f"Primeri state-ova (prvvih 15 od {len(all_states)}):\n")

for i, state in enumerate(sample_states, 1):
    next_states = knowledge_space[state]
    state_display = state if state != "{}" else "(nema znanja)"
    print(f"  State {i:3d}: {state_display}")
    if next_states:
        print(f"           → Može dalje u: {len(next_states)} state-ova")

print(f"\n✅ REZULTAT: {len(all_states)} mogućih knowledge state-ova")

# ============================================================================
# PRIMER 5: Praktična Primjena - Adaptive Tutoring Scenario
# ============================================================================

print("\n" + "=" * 80)
print("PRIMER 5: ADAPTIVE TUTORING - Kako Tutor Koristi Ontologiju")
print("=" * 80)

print("""
SCENARIO: Učenik je radio zadatke i usavršio sledeće koncepte:
  ✓ Allgemeingültige Gleichungen
  ✓ Geradengleichungen und Steigungen
  ✓ Funktionen und Graphen

Sada tutor koristi Knowledge Space da kaže:
""")

current_knowledge = {
    "Allgemeingültige Gleichungen",
    "Geradengleichungen und Steigungen", 
    "Funktionen und Graphen"
}

print(f"Učenikovo trenutno znanje: {current_knowledge}\n")

# Pronađi sledeće moguće koncepte
print("ANALIZA ONTOLOGIJE:\n")

# Iz knowledge space, pronađi state koji odgovara učenikovom znanju
current_state = "{" + ", ".join(sorted(current_knowledge)) + "}"
print(f"1. Pronađi trenutni state u knowledge space-u:")
print(f"   {current_state}\n")

if current_state in knowledge_space:
    next_states = knowledge_space[current_state]
    print(f"2. Pronađi sve dostupne sledeće state-ove:")
    print(f"   ({len(next_states)} mogućnosti)\n")
    
    # Pronađi koja znanja se mogu dodati
    available_concepts = set()
    for next_state_str in next_states:
        # Parsiraj state string
        next_state = next_state_str.strip("{}").split(", ")
        next_state = {c.strip() for c in next_state if c.strip()}
        added = next_state - current_knowledge
        available_concepts.update(added)
    
    print(f"3. Koncepti koji se mogu naučiti sledeći:")
    for concept in sorted(available_concepts):
        # Pronađi prerequisite
        needs_first = []
        for impl in implications:
            if impl["target"] == concept:
                if impl["source"] not in current_knowledge:
                    needs_first.append(impl["source"])
        
        if needs_first:
            print(f"   ⚠️  {concept}")
            print(f"       Trebalo bi prvo: {', '.join(needs_first)}")
        else:
            print(f"   ✅ {concept}")
            print(f"       Svi prerequisiti su zadovoljeni!")
else:
    print(f"   (State nije pronađen u knowledge space-u)")
    print(f"   Greška pri parsiranju - mogu pokazati primere:")
    
    all_states = list(knowledge_space.keys())
    for state in all_states[:5]:
        next_states = knowledge_space[state]
        print(f"\n   {state} → {len(next_states)} mogućnosti")

# ============================================================================
# PRIMER 6: RDF/TTL Ontologija - Semantic Web Standard
# ============================================================================

print("\n\n" + "=" * 80)
print("PRIMER 6: RDF/TTL ONTOLOGIJA - Semantic Web Standard")
print("=" * 80)

print("""
RDF (Resource Description Framework) je format koji omogućava
računarima da razumeju ZNAČENJE podataka.

Umesto:
  data = {"s1m11a091": "Concept_10"}

Piše se:
  <sotis:Item_s1m11a091> <sotis:belongsTo> <sotis:Concept_10> .

PREDNOSTI:
  1. Standardan format (može se koristiti sa bilo kojim tools-om)
  2. Mašinski čitljiv (mogu ga obraditi drugi sistemi)
  3. Linked data (može se povezati sa drugim ontologijama)
  4. SPARQL queryable (mogu se pisati inteligentne upite)

Tvoj sistem generiše sotis_ontology.ttl sa svim relacijama:
  • Koja pitanja pripadaju kojem konceptu
  • Koji su koncepti prerequisiti za druge
  • Koje je semantičke klastere
  • Struktura celog knowledge space-a
""")

print(f"\n✅ REZULTAT: Ontologija je spremna za SOTIS integraciju!")

# ============================================================================
# ZAKLJUČAK
# ============================================================================

print("\n" + "=" * 80)
print("🎯 ZAKLJUČAK: KAKO SEMANTIC WEB RADI")
print("=" * 80)

print(f"""
PROCES:
  1. LLM mapira 121 pitanja na 23 koncepta
  2. SentenceTransformer pronalazi semantičke klastere (24 klastera)
  3. IITA analitika pronalazi 30 prerequisite relacija
  4. Knowledge space generiše 355 mogućih state-ova
  5. Ontologija se eksportuje u RDF/TTL format
  6. SOTIS koristi ovu ontologiju za adaptive tutoring

REZULTAT:
  ✅ Inteligentni sistem koji razume ZNAČENJE znanja
  ✅ Personalizovane preporuke na osnovu prerequisiti
  ✅ Automatsko detektovanje manjka znanja
  ✅ Mogućnost integracije sa drugim platformama
  ✅ Standardan format (RDF/TTL/SPARQL)

PREDNOSTI:
  🎓 Edukacija: Svaki učenik dobija personalizovanu putanju
  🔬 Istraživanje: Mogu se analizirati learning patterns
  🌐 Interoperabilnost: Mogu se deliti ontologije između institucija
  🤖 Automatizacija: Svi procesi su deterministički i reproducibilni
""")

print("=" * 80)
