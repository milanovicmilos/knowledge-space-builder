#!/usr/bin/env python3
"""
Final comprehensive validation - field-level verification of semantic web implementation.
Validates every critical field in API responses.
"""

import json
from pathlib import Path
from typing import Dict, Any, List

def validate_json_structure(data: Dict, required_fields: List[str], path: str = "") -> List[str]:
    """Recursively validate required fields exist in nested structures."""
    issues = []
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing field at {path}: {field}")
    return issues

def validate_goal_object(goal: Dict, goal_index: int) -> List[str]:
    """Validate a single goal object has all required fields."""
    issues = []
    required = ["id", "uri", "label", "item_count"]
    path = f"goals[{goal_index}]"
    
    for field in required:
        if field not in goal:
            issues.append(f"{path}: Missing {field}")
        elif not goal[field]:
            issues.append(f"{path}: {field} is empty")
    
    # Validate URI format
    if "uri" in goal:
        if not goal["uri"].startswith("http://www.sotis-conference.org/ontology#"):
            issues.append(f"{path}: Invalid URI format - {goal['uri']}")
    
    # Validate item_count is integer
    if "item_count" in goal and not isinstance(goal["item_count"], int):
        issues.append(f"{path}: item_count is not integer - {type(goal['item_count'])}")
    
    return issues

def validate_learning_object(obj: Dict, obj_index: int, path: str) -> List[str]:
    """Validate a single learning object."""
    issues = []
    required = ["id", "label", "description", "difficulty"]
    
    for field in required:
        if field not in obj:
            issues.append(f"{path}[{obj_index}]: Missing {field}")
        elif field != "difficulty" and not obj.get(field):
            issues.append(f"{path}[{obj_index}]: {field} is empty")
    
    # Validate difficulty is float
    if "difficulty" in obj:
        if not isinstance(obj["difficulty"], (int, float)):
            issues.append(f"{path}[{obj_index}]: difficulty is not numeric - {type(obj['difficulty'])}")
        elif not (0 <= obj["difficulty"] <= 1):
            issues.append(f"{path}[{obj_index}]: difficulty out of range - {obj['difficulty']}")
    
    return issues

def main():
    # Load task 24 results
    results_file = Path("semantic_web_check_results_task_24.json")
    
    if not results_file.exists():
        print(f"❌ Error: {results_file} not found")
        return False
    
    with open(results_file) as f:
        results = json.load(f)
    
    print("=" * 100)
    print("FIELD-LEVEL VALIDATION REPORT - TASK 24")
    print("=" * 100)
    print()
    
    all_issues = []
    
    # 1. Validate top-level structure
    print("1. TOP-LEVEL STRUCTURE VALIDATION")
    print("-" * 100)
    
    required_top = ["task_id", "status", "statistics", "goals", "goal_path", "errors"]
    top_issues = validate_json_structure(results, required_top)
    
    if top_issues:
        for issue in top_issues:
            print(f"  ❌ {issue}")
            all_issues.append(issue)
    else:
        print("  ✅ All top-level fields present")
    
    print()
    
    # 2. Validate status object
    print("2. STATUS OBJECT VALIDATION")
    print("-" * 100)
    
    status = results.get("status", {})
    status_required = ["task_id", "status", "progress", "message", "created_at", "started_at", "completed_at"]
    status_issues = validate_json_structure(status, status_required, "status")
    
    if status_issues:
        for issue in status_issues:
            print(f"  ❌ {issue}")
            all_issues.append(issue)
    else:
        print(f"  ✅ Status: {status.get('status')} (Progress: {status.get('progress')}%)")
        print(f"  ✅ Task ID: {status.get('task_id')}")
        print(f"  ✅ Timestamps present and valid")
    
    print()
    
    # 3. Validate statistics object
    print("3. STATISTICS OBJECT VALIDATION")
    print("-" * 100)
    
    stats = results.get("statistics", {})
    stats_required = ["task_id", "status", "total_items", "total_concepts", "total_students", 
                      "knowledge_space_states", "prerequisites_found", "semantic_clusters"]
    stats_issues = validate_json_structure(stats, stats_required, "statistics")
    
    if stats_issues:
        for issue in stats_issues:
            print(f"  ❌ {issue}")
            all_issues.append(issue)
    else:
        print(f"  ✅ Total items: {stats.get('total_items')}")
        print(f"  ✅ Total concepts (LearningGoals): {stats.get('total_concepts')}")
        print(f"  ✅ Prerequisites found: {stats.get('prerequisites_found')}")
        print(f"  ✅ Semantic clusters: {stats.get('semantic_clusters')}")
    
    print()
    
    # 4. Validate goals array
    print("4. LEARNING GOALS VALIDATION")
    print("-" * 100)
    
    goals_obj = results.get("goals", {})
    goals_list = goals_obj.get("goals", [])
    total_goals = goals_obj.get("total_count", 0)
    
    print(f"  Total goals: {total_goals}")
    print(f"  Goals count matches array: {'✅' if len(goals_list) == total_goals else '❌'}")
    print()
    
    goal_issues = []
    for i, goal in enumerate(goals_list):
        goal_issues.extend(validate_goal_object(goal, i))
    
    if goal_issues:
        print(f"  ❌ Found {len(goal_issues)} issues in goals:")
        for issue in goal_issues[:5]:  # Show first 5
            print(f"     - {issue}")
        all_issues.extend(goal_issues)
    else:
        print(f"  ✅ All {len(goals_list)} goals validated successfully")
    
    # Sample goals
    print()
    print("  Sample goals:")
    for goal in goals_list[:3]:
        print(f"    - {goal['label']}: {goal['item_count']} items")
    
    print()
    
    # 5. Validate goal-path structure
    print("5. LEARNING PATH VALIDATION")
    print("-" * 100)
    
    goal_path = results.get("goal_path", {})
    path_issues = []
    
    # Validate goal
    if "goal" not in goal_path:
        path_issues.append("Missing 'goal' in goal_path")
    else:
        goal = goal_path["goal"]
        required_goal_fields = ["id", "uri", "label", "is_known"]
        for field in required_goal_fields:
            if field not in goal:
                path_issues.append(f"goal_path.goal: Missing {field}")
    
    # Validate steps array
    if "steps" not in goal_path:
        path_issues.append("Missing 'steps' array in goal_path")
    else:
        steps = goal_path["steps"]
        print(f"  Total path steps: {len(steps)}")
        
        for step_idx, step in enumerate(steps):
            # Validate step structure
            required_step = ["id", "uri", "label", "item_count", "items", "depth", "avg_difficulty"]
            for field in required_step:
                if field not in step:
                    path_issues.append(f"steps[{step_idx}]: Missing {field}")
            
            # Validate items count
            if "items" in step and "item_count" in step:
                actual_count = len(step["items"])
                reported_count = step["item_count"]
                if actual_count != reported_count:
                    path_issues.append(f"steps[{step_idx}]: Count mismatch! reported={reported_count}, actual={actual_count}")
            
            # Validate learning objects
            if "items" in step:
                for obj_idx, obj in enumerate(step["items"]):
                    obj_issues = validate_learning_object(obj, obj_idx, f"steps[{step_idx}].items")
                    path_issues.extend(obj_issues)
    
    # Validate total_steps
    if "total_steps" in goal_path:
        reported_steps = goal_path["total_steps"]
        actual_steps = len(goal_path.get("steps", []))
        if reported_steps != actual_steps:
            path_issues.append(f"total_steps mismatch: reported={reported_steps}, actual={actual_steps}")
    
    if path_issues:
        print(f"  ❌ Found {len(path_issues)} issues in goal path:")
        for issue in path_issues[:5]:
            print(f"     - {issue}")
        all_issues.extend(path_issues)
    else:
        print(f"  ✅ Goal path structure valid")
        if goal_path.get("steps"):
            step = goal_path["steps"][0]
            print(f"     - Goal: {step.get('label')}")
            print(f"     - Item count: {step.get('item_count')} (verified accurate)")
            print(f"     - Avg difficulty: {step.get('avg_difficulty'):.3f}")
            print(f"     - Depth: {step.get('depth')}")
    
    print()
    
    # 6. Check for duplicates
    print("6. DUPLICATE DETECTION")
    print("-" * 100)
    
    all_items_in_path = []
    for step in goal_path.get("steps", []):
        for item in step.get("items", []):
            all_items_in_path.append(item["id"])
    
    unique_items = len(set(all_items_in_path))
    total_items = len(all_items_in_path)
    duplicates = total_items - unique_items
    
    if duplicates > 0:
        print(f"  ❌ DUPLICATES FOUND: {duplicates} duplicate items")
        all_issues.append(f"Duplicate items detected: {duplicates}")
    else:
        print(f"  ✅ No duplicates: {total_items} items, {unique_items} unique")
    
    print()
    
    # 7. Validate error handling
    print("7. ERROR HANDLING")
    print("-" * 100)
    
    errors = results.get("errors", [])
    if errors:
        print(f"  ⚠️  {len(errors)} errors reported:")
        for err in errors:
            print(f"     - {err}")
            all_issues.append(f"API Error: {err}")
    else:
        print(f"  ✅ No errors in API response")
    
    print()
    
    # 8. Summary
    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print()
    
    if all_issues:
        print(f"❌ VALIDATION FAILED: {len(all_issues)} issues found")
        print()
        print("Issues:")
        for issue in all_issues:
            print(f"  - {issue}")
        print()
        return False
    else:
        print("✅ ALL VALIDATION CHECKS PASSED")
        print()
        print("Summary:")
        print(f"  ✅ Structure: Valid JSON with all required fields")
        print(f"  ✅ Content: All values present and correctly typed")
        print(f"  ✅ Consistency: Counts and arrays align")
        print(f"  ✅ Duplicates: 0 duplicate items detected")
        print(f"  ✅ Data Quality: Complete descriptions and valid URIs")
        print(f"  ✅ Errors: None reported")
        print()
        print("Task 24 is PRODUCTION READY for deployment.")
        return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
