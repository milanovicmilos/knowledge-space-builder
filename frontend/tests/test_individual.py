"""Individual endpoint tests.

Use these helpers when you want to test a single endpoint without running
the entire workflow.
"""

import requests
import sys
from pathlib import Path


# Global timeout (seconds) for all HTTP calls
REQUEST_TIMEOUT = 10

BASE_URL = "http://localhost/api"
API_BASE = f"{BASE_URL}/v1/analysis"


def upload_csv(csv_path):
    """Upload a CSV file and create a task.

    Args:
        csv_path: Path to the CSV file

    Returns:
        task_id or None
    """
    print(f"Uploading {csv_path}...")
    
    if not Path(csv_path).exists():
        print(f"ERROR: File {csv_path} does not exist!")
        return None
    
    try:
        with open(csv_path, 'rb') as f:
            files = {'file': (Path(csv_path).name, f, 'text/csv')}
            response = requests.post(
                f"{API_BASE}/run",
                files=files,
                timeout=REQUEST_TIMEOUT,
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"SUCCESS: Task created with ID: {data.get('task_id')}")
                print(f"Status: {data.get('status')}")
                print(f"Progress: {data.get('progress')}%")
                print(f"Message: {data.get('message')}")
                return data.get('task_id')
            else:
                print(f"ERROR: {response.status_code}")
                print(response.text)
                return None
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print("ERROR: Timeout during upload (POST /run)")
            print("Tip: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print(f"ERROR: {str(e)}")
        return None


def check_status(task_id):
    """Check the status of a task.

    Args:
        task_id: Task ID
    """
    print(f"Checking status for task {task_id}...")
    
    try:
        response = requests.get(
            f"{API_BASE}/{task_id}/status",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Task ID: {data.get('task_id')}")
            print(f"Status: {data.get('status')}")
            print(f"Progress: {data.get('progress')}%")
            print(f"Message: {data.get('message')}")
            print(f"Created: {data.get('created_at')}")
            print(f"Started: {data.get('started_at')}")
            print(f"Completed: {data.get('completed_at')}")
            
            if data.get('error_message'):
                print(f"ERROR: {data.get('error_message')}")
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print("ERROR: Timeout while checking status (GET /status)")
            print("Tip: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print(f"ERROR: {str(e)}")


def get_results(task_id):
    """Retrieve analysis results for a task.

    Args:
        task_id: Task ID
    """
    print(f"Getting results for task {task_id}...")
    
    try:
        response = requests.get(
            f"{API_BASE}/{task_id}/results",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Task ID: {data.get('task_id')}")
            print(f"Status: {data.get('status')}")
            print(f"Completed: {data.get('completed_at')}")
            
            files = data.get('files', {})
            print(f"\nTotal files: {len(files)}")
            for filename in files.keys():
                print(f"  - {filename}")
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print("ERROR: Timeout while retrieving results (GET /results)")
            print("Tip: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print(f"ERROR: {str(e)}")


def get_statistics(task_id):
    """Retrieve statistics for a task.

    Args:
        task_id: Task ID
    """
    print(f"Getting statistics for task {task_id}...")
    
    try:
        response = requests.get(
            f"{API_BASE}/{task_id}/statistics",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('statistics', {})
            
            print(f"Task ID: {data.get('task_id')}")
            print(f"Status: {data.get('status')}")
            print("\nStatistics:")
            print(f"  Total Items: {stats.get('total_items')}")
            print(f"  Total Concepts: {stats.get('total_concepts')}")
            print(f"  Total Students: {stats.get('total_students')}")
            print(f"  Knowledge Space States: {stats.get('knowledge_space_states')}")
            print(f"  Prerequisites Found: {stats.get('prerequisites_found')}")
            print(f"  Semantic Clusters: {stats.get('semantic_clusters')}")
            print(f"  Root Concepts: {stats.get('root_concepts')}")
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print("ERROR: Timeout while retrieving statistics (GET /statistics)")
            print("Tip: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print(f"ERROR: {str(e)}")


def get_visualization(task_id):
    """Get visualization info for a task.

    Args:
        task_id: Task ID
    """
    print(f"Getting visualization for task {task_id}...")
    
    try:
        response = requests.get(
            f"{API_BASE}/{task_id}/visualization",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Task ID: {data.get('task_id')}")
            print(f"Graph file: {data.get('graph_file')}")
            print(f"Graph exists: {data.get('graph_exists')}")
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print("ERROR: Timeout while retrieving visualization (GET /visualization)")
            print("Tip: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print(f"ERROR: {str(e)}")


def list_files(task_id):
    """List all available result files for a task.

    Args:
        task_id: Task ID
    """
    print(f"Listing files for task {task_id}...")
    
    try:
        response = requests.get(
            f"{API_BASE}/{task_id}/files",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Task ID: {data.get('task_id')}")
            print(f"Total files: {data.get('total_files')}")
            
            files = data.get('files', [])
            if files:
                print("\nFiles:")
                for file in files:
                    size_kb = file.get('size', 0) / 1024
                    print(f"  - {file.get('name')} ({size_kb:.2f} KB)")
                    print(f"    Path: {file.get('path')}")
        else:
            print(f"ERROR: {response.status_code}")
            print(response.text)
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print("ERROR: Timeout while listing files (GET /files)")
            print("Tip: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print(f"ERROR: {str(e)}")


def print_usage():
    """Show script usage"""
    print("""
USAGE:
    python test_individual.py <command> [args]

COMMANDS:
    upload <csv_path>       - Upload CSV file and create a task
    status <task_id>        - Check task status
    results <task_id>       - Retrieve results
    statistics <task_id>    - Retrieve statistics
    visualization <task_id> - Retrieve visualization info
    files <task_id>         - List all files

EXAMPLES:
    python test_individual.py upload test_data.csv
    python test_individual.py status 1
    python test_individual.py results 1
    python test_individual.py statistics 1
    python test_individual.py visualization 1
    python test_individual.py files 1
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "upload":
        if len(sys.argv) < 3:
            print("ERROR: Missing CSV path!")
            print("Usage: python test_individual.py upload <csv_path>")
            sys.exit(1)
        upload_csv(sys.argv[2])
    
    elif command == "status":
        if len(sys.argv) < 3:
            print("ERROR: Missing task_id!")
            print("Usage: python test_individual.py status <task_id>")
            sys.exit(1)
        check_status(int(sys.argv[2]))
    
    elif command == "results":
        if len(sys.argv) < 3:
            print("ERROR: Missing task_id!")
            print("Usage: python test_individual.py results <task_id>")
            sys.exit(1)
        get_results(int(sys.argv[2]))
    
    elif command == "statistics":
        if len(sys.argv) < 3:
            print("ERROR: Missing task_id!")
            print("Usage: python test_individual.py statistics <task_id>")
            sys.exit(1)
        get_statistics(int(sys.argv[2]))
    
    elif command == "visualization":
        if len(sys.argv) < 3:
            print("ERROR: Missing task_id!")
            print("Usage: python test_individual.py visualization <task_id>")
            sys.exit(1)
        get_visualization(int(sys.argv[2]))
    
    elif command == "files":
        if len(sys.argv) < 3:
            print("ERROR: Missing task_id!")
            print("Usage: python test_individual.py files <task_id>")
            sys.exit(1)
        list_files(int(sys.argv[2]))
    
    else:
        print(f"ERROR: Unknown command '{command}'")
        print_usage()
        sys.exit(1)
