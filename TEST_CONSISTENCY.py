#!/usr/bin/env python3
"""
TEST_CONSISTENCY.py - Verifikuj determinističnost između terminal i frontend pokretanja

Ovaj test:
1. Pokreće algoritam preko terminala 3 puta
2. Čuva rezultate iz learning_space_generator/output/
3. Proverava da li su svi rezultati identični
4. Ispisuje finalne brojeve koji MORAJU biti u bazi kada se frontend pokrene
"""

import json
import subprocess
import sys
from pathlib import Path

def run_algorithm():
    """Pokreni algoritam."""
    print("\n" + "="*80)
    print("Pokrenuo: learning_space_generator algoritam")
    print("="*80)
    
    result = subprocess.run(
        [sys.executable, "-c", 
         "import sys; sys.path.insert(0, '.'); import sys; sys.argv = ['main.py', 'all']; from learning_space_generator.app.main import main; main()"],
        cwd=".",
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ GREŠKA: {result.stderr}")
        return None
    
    return result.stdout

def load_results(output_dir: Path):
    """Učitaj rezultate iz output direktorijuma."""
    results = {}
    
    try:
        with open(output_dir / "implications.json") as f:
            implications = json.load(f)
            results["prerequisites_found"] = len(implications)
    except:
        results["prerequisites_found"] = None
    
    try:
        with open(output_dir / "knowledge_space.json") as f:
            ks = json.load(f)
            results["knowledge_space_states"] = len(ks)
    except:
        results["knowledge_space_states"] = None
    
    try:
        with open(output_dir / "semantic_clusters.json") as f:
            sc = json.load(f)
            results["semantic_clusters"] = len(sc)
    except:
        results["semantic_clusters"] = None
    
    return results

def main():
    output_dir = Path("learning_space_generator/output")
    run_count = 3
    all_results = []
    
    print("\n🔄 TESTIRANJE DETERMINISTIČNOSTI")
    print(f"Pokretanje algoritma {run_count} puta bez prosledi argumenata...\n")
    
    for i in range(run_count):
        print(f"\n▶️  Run #{i+1}/{run_count}")
        stdout = run_algorithm()
        if stdout is None:
            print(f"❌ Run #{i+1} failed")
            return False
        
        results = load_results(output_dir)
        all_results.append(results)
        
        print(f"   ✅ prerequisites_found: {results['prerequisites_found']}")
        print(f"   ✅ knowledge_space_states: {results['knowledge_space_states']}")
        print(f"   ✅ semantic_clusters: {results['semantic_clusters']}")
    
    # Proveri da li su svi rezultati identični
    print("\n" + "="*80)
    print("VERIFIKACIJA DETERMINISTIČNOSTI")
    print("="*80)
    
    first = all_results[0]
    all_same = all(r == first for r in all_results)
    
    if all_same:
        print("✅ SVE POKRETANJA SU IDENTIČNA!")
        print(f"\n📊 FINALNI REZULTATI (za bazu):")
        print(f"   prerequisites_found = {first['prerequisites_found']}")
        print(f"   knowledge_space_states = {first['knowledge_space_states']}")
        print(f"   semantic_clusters = {first['semantic_clusters']}")
        print(f"\n⚠️  FRONTEND TASK MORA DA IMA TAČNO OVE BROJEVE!")
        return True
    else:
        print("❌ REZULTATI NISU IDENTIČNI - POSTOJI NEDETERMINIZAM!")
        for i, r in enumerate(all_results):
            print(f"   Run #{i+1}: {r}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
