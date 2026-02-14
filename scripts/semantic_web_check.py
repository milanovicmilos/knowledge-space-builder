import json
import os
import sys
import time
import urllib.parse
import urllib.request

BASE_URL = os.getenv("SEMANTIC_WEB_CHECK_BASE_URL", "http://127.0.0.1:8000/api/v1/analysis")
TASK_ID = sys.argv[1] if len(sys.argv) > 1 else "23"
OUTPUT_PATH = f"semantic_web_check_results_task_{TASK_ID}.json"
REQUEST_TIMEOUT_SECONDS = 25
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2


def get_json(url: str) -> dict:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                data = resp.read().decode("utf-8")
            return json.loads(data)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SECONDS)
    raise last_error


def main() -> int:
    results = {
        "task_id": TASK_ID,
        "status": None,
        "statistics": None,
        "goals": None,
        "goal_path": None,
        "errors": [],
    }

    try:
        status = get_json(f"{BASE_URL}/{TASK_ID}/status")
        results["status"] = status
    except Exception as exc:
        results["errors"].append(f"status_error: {exc}")

    try:
        stats = get_json(f"{BASE_URL}/{TASK_ID}/statistics")
        results["statistics"] = stats
    except Exception as exc:
        results["errors"].append(f"statistics_error: {exc}")

    goals = None
    try:
        goals = get_json(f"{BASE_URL}/{TASK_ID}/goals")
        results["goals"] = goals
    except Exception as exc:
        results["errors"].append(f"goals_error: {exc}")

    if goals and goals.get("goals"):
        first_goal = goals["goals"][0]
        goal_id = first_goal.get("id")
        if goal_id:
            try:
                params = urllib.parse.urlencode({"goal_id": goal_id})
                goal_path = get_json(f"{BASE_URL}/{TASK_ID}/goal-path?{params}")
                results["goal_path"] = goal_path
            except Exception as exc:
                results["errors"].append(f"goal_path_error: {exc}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=True)

    print(f"Wrote results to {OUTPUT_PATH}")
    if results["errors"]:
        print("Errors:")
        for err in results["errors"]:
            print(f"- {err}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
