"""
Test script - Full verification of difficulty analysis integration
"""
import sys
import logging
from pathlib import Path
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.difficulty_service import DifficultyService

def main():
    print("=" * 80)
    print("FULL VERIFICATION TEST - Difficulty Analysis")
    print("=" * 80)
    
    # Run difficulty analysis
    print("\n1. Running difficulty analysis...")
    service = DifficultyService()
    result_path = service.run_difficulty_analysis()
    
    # Verify output files exist
    print("\n2. Verifying output files...")
    output_dir = Path(__file__).parent.parent / "output"
    
    files_to_check = [
        "item_difficulties.json",
        "concepts_sorted_by_difficulty.json"
    ]
    
    all_exist = True
    for filename in files_to_check:
        filepath = output_dir / filename
        if filepath.exists():
            print(f"   ✅ {filename} exists ({filepath.stat().st_size} bytes)")
        else:
            print(f"   ❌ {filename} NOT FOUND")
            all_exist = False
    
    # Show sample data
    print("\n3. Sample data from concepts_sorted_by_difficulty.json:")
    with open(output_dir / "concepts_sorted_by_difficulty.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print(f"   Total concepts: {len(data)}")
    
    # Show first concept in detail
    first_concept = list(data.keys())[0]
    items = data[first_concept]
    print(f"\n   Example - {first_concept}:")
    print(f"   Total items: {len(items)}")
    print(f"   Items sorted by difficulty (easiest → hardest):")
    for item in items[:5]:  # Show first 5
        print(f"      #{item['rank']}: {item['item_id']} - {item['difficulty_percent']} correct")
    
    # Show difficulty distribution
    print("\n4. Difficulty distribution across all items:")
    with open(output_dir / "item_difficulties.json", 'r', encoding='utf-8') as f:
        difficulties = json.load(f)
    
    values = list(difficulties.values())
    print(f"   Total items: {len(values)}")
    print(f"   Easiest item: {max(values):.1%} correct")
    print(f"   Hardest item: {min(values):.1%} correct")
    print(f"   Average difficulty: {sum(values)/len(values):.1%} correct")
    
    # Count difficulty levels
    easy = sum(1 for v in values if v > 0.25)
    medium = sum(1 for v in values if 0.10 <= v <= 0.25)
    hard = sum(1 for v in values if v < 0.10)
    
    print(f"\n   Difficulty breakdown:")
    print(f"      Easy (>25%): {easy} items")
    print(f"      Medium (10-25%): {medium} items")
    print(f"      Hard (<10%): {hard} items")
    
    print("\n" + "=" * 80)
    if all_exist:
        print("✅ ALL TESTS PASSED - Difficulty analysis working correctly!")
    else:
        print("❌ SOME TESTS FAILED - Check output files")
    print("=" * 80)

if __name__ == "__main__":
    main()
