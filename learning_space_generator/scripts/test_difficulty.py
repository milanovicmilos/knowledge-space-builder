"""
Test script for difficulty analysis
"""
import sys
import logging
from pathlib import Path

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.difficulty_service import DifficultyService

if __name__ == "__main__":
    print("Starting difficulty analysis...")
    service = DifficultyService()
    result = service.run_difficulty_analysis()
    print(f"Difficulty analysis complete! Results saved to: {result}")
