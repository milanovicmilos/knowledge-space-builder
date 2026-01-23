"""
OBJEKTIVNA ANALIZA - Da li je 39,170 stanja previše ili dobro?
================================================================
"""
import json
import pandas as pd
from collections import Counter

print("="*80)
print("OBJEKTIVNA ANALIZA PROSTORA ZNANJA")
print("="*80)

# 1. Analiziraj profesor primer
print("\n1. PROFESOR PRIMER (Idealan prostor):")
with open('learning_space_generator/data/profesor_example.json') as f:
    prof = json.load(f)
    
# Pronadjemo sve koncepte iz primera
all_concepts = set()
for key in prof.keys():
    if key == "{}": continue
    items = key[1:-1].split(", ")
    all_concepts.update(items)

prof_concepts = len(all_concepts)
prof_states = len(prof)
prof_max = 2**prof_concepts

print(f"   Koncepti: {prof_concepts}")
print(f"   Stanja: {prof_states}")
print(f"   Teorijski max (2^{prof_concepts}): {prof_max:,}")
print(f"   % od maksimalnog: {100*prof_states/prof_max:.2f}%")
print(f"   👉 Odnos stanja/koncepti: {prof_states/prof_concepts:.1f}")

# 2. Analiziraj naše podatke
print("\n2. NAŠI PODACI (Stvarni studenti):")
concept_df = pd.read_csv('learning_space_generator/output/aggregated_concepts_binary.csv')
n_students = len(concept_df)
n_concepts = len(concept_df.columns)

print(f"   Koncepti: {n_concepts}")
print(f"   Studenti: {n_students}")
print(f"   Teorijski max (2^{n_concepts}): {2**n_concepts:,}")

# Koliko jedinstvenih stanja postoji u podacima
unique_states = set()
for _, row in concept_df.iterrows():
    state = frozenset(concept_df.columns[row == 1])
    unique_states.add(state)

observed = len(unique_states)
print(f"   Posmatrana stanja (iz podataka): {observed}")
print(f"   % od maksimalnog: {100*observed/(2**n_concepts):.4f}%")

# 3. Analiziraj naš generisani prostor
print("\n3. NAŠ GENERISANI PROSTOR:")
with open('learning_space_generator/output/knowledge_space.json') as f:
    ks = json.load(f)

generated = len(ks)
print(f"   Generisano stanja: {generated:,}")
print(f"   % od maksimalnog: {100*generated/(2**n_concepts):.2f}%")
print(f"   👉 Odnos stanja/koncepti: {generated/n_concepts:.1f}")

# 4. Poređenje
print("\n" + "="*80)
print("POREĐENJE:")
print("="*80)
print(f"   Profesor primer: {prof_states/prof_concepts:.1f} stanja po konceptu")
print(f"   Naš prostor:     {generated/n_concepts:.1f} stanja po konceptu")
print(f"   Razlika: {(generated/n_concepts) / (prof_states/prof_concepts):.1f}x više")

# 5. Ekspanzija faktora
expansion_factor = generated / observed
print(f"\n📈 EKSPANZIJA FAKTORA:")
print(f"   Od {observed} posmatranih → {generated:,} generisanih")
print(f"   Faktor: {expansion_factor:.1f}x")

if expansion_factor > 100:
    print(f"   ⚠️  ALARM: Ekspanzija {expansion_factor:.0f}x je PREVIŠE!")
    print(f"   🎯 Preporuka: Idealno bi bilo 2x-10x ekspanzija")
elif expansion_factor > 50:
    print(f"   ⚠️  Ekspanzija {expansion_factor:.0f}x je na granici prihvatljivosti")
elif expansion_factor > 20:
    print(f"   ⚠️  Ekspanzija {expansion_factor:.0f}x je visoka")
else:
    print(f"   ✅ Ekspanzija {expansion_factor:.0f}x je prihvatljiva")

# 6. Analiza gustine
print(f"\n📊 GUSTINA PROSTORA:")
# Prosečan broj izlaznih veza po čvoru
total_edges = sum(len(v) for v in ks.values())
avg_out = total_edges / len(ks) if len(ks) > 0 else 0
print(f"   Prosečno izlaznih grana po čvoru: {avg_out:.2f}")

if avg_out < 1.5:
    print(f"   ✅ Prostor je dobro pruned (skoro linearno stablo)")
elif avg_out < 3:
    print(f"   ⚠️  Prostor se dosta grana")
else:
    print(f"   ❌ Prostor eksplodira ({avg_out:.1f} grana po čvoru)")

# 7. Finalna procena
print("\n" + "="*80)
print("FINALNA OBJEKTIVNA PROCENA:")
print("="*80)

if expansion_factor > 50:
    print("❌ PROBLEM: Previše stanja generisano.")
    print("   Razlog: Pruning algoritam je previše permisivan.")
    print("   Rezultat će biti težak za vizuelizaciju i neefikasan za tutor.")
    print(f"\n   Predlog: Pojačaj pruning da zadržiš najviše {observed * 10:,} stanja (~10x ekspanzija)")
elif expansion_factor > 20:
    print("⚠️  NA GRANICI: Broj stanja je visok ali možda prihvatljiv.")
    print(f"   {generated:,} stanja je mnogo, ali prostor je well-graded.")
    print("   Za UI vizuelizaciju može biti problem (pregleda samo top 1000).")
else:
    print("✅ DOBRO: Broj stanja je prihvatljiv.")
