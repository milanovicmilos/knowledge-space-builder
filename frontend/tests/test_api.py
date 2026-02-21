"""API integration tests - simulate frontend requests to the backend.

Tests the full workflow:
1. Upload CSV
2. Create task
3. Poll progress
4. Retrieve results, statistics, visualization, and files
"""

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
import requests
import time
import json
from pathlib import Path


# Global timeout (seconds) for all HTTP calls
REQUEST_TIMEOUT = 10

# Backend URL (through nginx proxy in docker compose)
BASE_URL = "http://localhost/api"
API_BASE = f"{BASE_URL}/v1/analysis"


CSV_PATH = r"c:\Users\Milos\PythonProjects\knowledge-space-builder\learning_space_generator\data\matheGesamt.csv"
OUTPUT_DIR = r"c:\Users\Milos\PythonProjects\knowledge-space-builder\learning_space_generator\output"


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(msg):
    print(f"{Colors.GREEN}[OK] {msg}{Colors.END}")


def print_error(msg):
    print(f"{Colors.RED}[ERR] {msg}{Colors.END}")


def print_info(msg):
    print(f"{Colors.BLUE}[INFO] {msg}{Colors.END}")


def print_warning(msg):
    print(f"{Colors.YELLOW}[WARN] {msg}{Colors.END}")


def test_1_upload_csv():
    """Test 1: Upload CSV and create a task.

    POST /api/v1/analysis/run

    Client sends:
    - file: FormData with CSV

    Expected backend response:
    - task_id: int
    - status: str
    - progress: int
    - message: str
    """
    print("\n" + "="*60)
    print_info("Test 1: Upload CSV and create task")
    print("="*60)
    
    # Use matheGesamt.csv from LSG data
    test_csv_path = Path(CSV_PATH)
    if not test_csv_path.exists():
        print_error(f"CSV file does not exist: {test_csv_path}")
        return None
    print_info(f"Using CSV: {test_csv_path}")
    
    try:
        with open(test_csv_path, 'rb') as f:
            files = {'file': ('test_data.csv', f, 'text/csv')}
            
            print_info(f"Sending POST {API_BASE}/run")
            response = requests.post(
                f"{API_BASE}/run",
                files=files,
                timeout=REQUEST_TIMEOUT,
            )
            
            print_info(f"Status kod: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print_success("CSV uploaded successfully!")
                print(f"  Task ID: {data.get('task_id')}")
                print(f"  Status: {data.get('status')}")
                print(f"  Progress: {data.get('progress')}%")
                print(f"  Message: {data.get('message')}")
                
                # Return task_id for subsequent tests
                return data.get('task_id')
            else:
                print_error(f"Upload failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return None
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout during upload (POST /run)")
            print_warning("Check logs: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Error: {str(e)}")
        return None
    
    finally:
        pass


def test_2_check_status(task_id):
    """Test 2: Check task status.

    GET /api/v1/analysis/{task_id}/status

    Client polls this endpoint every second while the task is active.

    Expected response fields:
    - task_id: int
    - status: str (pending, running, completed, failed)
    - progress: int (0-100)
    - message: str
    - created_at, started_at, completed_at, error_message
    """
    print("\n" + "="*60)
    print_info("Test 2: Poll task status")
    print("="*60)
    
    if not task_id:
        print_error("No task_id provided for testing!")
        return False
    
    max_attempts = 60  # 60 seconds max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            print_info(f"Attempt {attempt + 1}/{max_attempts} - GET {API_BASE}/{task_id}/status")
            response = requests.get(
                f"{API_BASE}/{task_id}/status",
                timeout=REQUEST_TIMEOUT,
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                progress = data.get('progress', 0)
                message = data.get('message', '')
                
                print(f"  Status: {status} | Progress: {progress}% | Message: {message}")
                
                if status == 'completed':
                    print_success("Task completed successfully!")
                    print(f"  Started at: {data.get('started_at')}")
                    print(f"  Completed at: {data.get('completed_at')}")
                    return True
                
                elif status == 'failed':
                    print_error("Task failed!")
                    print(f"  Error: {data.get('error_message')}")
                    return False
                
                elif status in ['pending', 'running']:
                    print_info(f"Task still running... ({progress}%)")
                    time.sleep(1)
                    attempt += 1
                    continue
                
            else:
                print_error(f"Status check failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        
        except Exception as e:
            if isinstance(e, requests.Timeout):
                print_error("Timeout while checking status (GET /status)")
                print_warning("Check logs: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
            else:
                print_error(f"Error: {str(e)}")
            return False
    
    print_warning("Timeout - task did not finish in allotted time")
    return False


def test_3_get_results(task_id):
    """Test 3: Retrieve analysis results.

    GET /api/v1/analysis/{task_id}/results

    Expected response:
    - task_id, status, completed_at, files (mapping of output JSON files)
    """
    print("\n" + "="*60)
    print_info("Test 3: Retrieve results")
    print("="*60)
    
    if not task_id:
        print_error("No task_id provided for testing!")
        return
    
    try:
        print_info(f"GET {API_BASE}/{task_id}/results")
        response = requests.get(
            f"{API_BASE}/{task_id}/results",
            timeout=REQUEST_TIMEOUT,
        )
        
        print_info(f"Status kod: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Results retrieved successfully!")
            print(f"  Task ID: {data.get('task_id')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Completed at: {data.get('completed_at')}")
            print(f"  Number of files: {len(data.get('files', {}))}")
            
            # Show available files
            files = data.get('files', {})
            if files:
                print_info("Available files:")
                for filename in files.keys():
                    print(f"    - {filename}")

            # Compare content with local output JSON files
            all_match = True
            for filename, content in files.items():
                if filename.endswith('.json'):
                    local_path = Path(OUTPUT_DIR) / filename
                    if not local_path.exists():
                        print_warning(f"Local file does not exist: {local_path}")
                        all_match = False
                        continue
                    try:
                        with open(local_path, 'r', encoding='utf-8') as lf:
                            local_json = json.load(lf)
                        if local_json == content:
                            print_success(f"Match: {filename}")
                        else:
                            print_error(f"MISMATCH: {filename}")
                            all_match = False
                    except Exception as e:
                        print_error(f"Error comparing {filename}: {e}")
                        all_match = False
            if all_match:
                print_success("All JSON files in the DB match local output files!")
            else:
                print_warning("Differences found between DB and local output files.")
        
        else:
            print_error(f"Get results failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout while retrieving results (GET /results)")
            print_warning("Check logs: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Error: {str(e)}")


def test_4_get_statistics(task_id):
    """
    Test 4: Retrieve statistics

    GET /api/v1/analysis/{task_id}/statistics

    Backend returns:
    - task_id: int
    - status: str
    - statistics:
        - total_items: int
        - total_concepts: int
        - total_students: int
        - knowledge_space_states: int
        - prerequisites_found: int
        - semantic_clusters: int
        - root_concepts: int
    """
    print("\n" + "="*60)
    print_info("Test 4: Retrieve statistics")
    print("="*60)
    
    if not task_id:
        print_error("No task_id provided for testing!")
        return
    
    try:
        print_info(f"GET {API_BASE}/{task_id}/statistics")
        response = requests.get(
            f"{API_BASE}/{task_id}/statistics",
            timeout=REQUEST_TIMEOUT,
        )
        
        print_info(f"Status kod: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Statistics retrieved successfully!")
            print(f"  Task ID: {data.get('task_id')}")
            
            stats = data.get('statistics', {})
            print_info("Statistics:")
            print(f"    Total Items: {stats.get('total_items')}")
            print(f"    Total Concepts: {stats.get('total_concepts')}")
            print(f"    Total Students: {stats.get('total_students')}")
            print(f"    Knowledge Space States: {stats.get('knowledge_space_states')}")
            print(f"    Prerequisites Found: {stats.get('prerequisites_found')}")
            print(f"    Semantic Clusters: {stats.get('semantic_clusters')}")
            print(f"    Root Concepts: {stats.get('root_concepts')}")
        
        else:
            print_error(f"Get statistics failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout while retrieving statistics (GET /statistics)")
            print_warning("Check logs: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Error: {str(e)}")


def test_5_get_visualization(task_id):
    """
    Test 5: Retrieve visualization (graph PNG)

    GET /api/v1/analysis/{task_id}/visualization

    Backend returns:
    - task_id: int
    - graph_file: str (path to PNG)
    - graph_exists: bool
    """
    print("\n" + "="*60)
    print_info("Test 5: Retrieve visualization")
    print("="*60)
    
    if not task_id:
        print_error("No task_id provided for testing!")
        return
    
    try:
        print_info(f"GET {API_BASE}/{task_id}/visualization")
        response = requests.get(
            f"{API_BASE}/{task_id}/visualization",
            timeout=REQUEST_TIMEOUT,
        )
        
        print_info(f"Status kod: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Visualization info retrieved successfully!")
            print(f"  Task ID: {data.get('task_id')}")
            print(f"  Graph file: {data.get('graph_file')}")
            print(f"  Graph exists: {data.get('graph_exists')}")
        
        else:
            print_error(f"Get visualization failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout while retrieving visualization (GET /visualization)")
            print_warning("Check logs: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Error: {str(e)}")


def test_6_list_files(task_id):
    """
    Test 6: List all available files

    GET /api/v1/analysis/{task_id}/files

    Backend returns:
    - task_id: int
    - total_files: int
    - files: list[dict]
        - name: str
        - size: int
        - path: str
    """
    print("\n" + "="*60)
    print_info("Test 6: List all files")
    print("="*60)
    
    if not task_id:
        print_error("No task_id provided for testing!")
        return
    
    try:
        print_info(f"GET {API_BASE}/{task_id}/files")
        response = requests.get(
            f"{API_BASE}/{task_id}/files",
            timeout=REQUEST_TIMEOUT,
        )
        
        print_info(f"Status kod: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print_success("File list retrieved successfully!")
            print(f"  Task ID: {data.get('task_id')}")
            print(f"  Total files: {data.get('total_files')}")
            
            files = data.get('files', [])
            if files:
                print_info("Files:")
                for file in files:
                    size_kb = file.get('size', 0) / 1024
                    print(f"    - {file.get('name')} ({size_kb:.2f} KB)")
        
        else:
            print_error(f"List files failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout while listing files (GET /files)")
            print_warning("Check logs: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Error: {str(e)}")


def test_health():
    """
    Test 0: Proveri da li je backend dostupan
    """
    print("\n" + "="*60)
    print_info("Test 0: Health check - Is backend available?")
    print("="*60)
    
    try:
        print_info(f"GET {BASE_URL}/health")
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            print_success("Backend is available!")
            return True
        else:
            print_error(f"Backend not available! Status: {response.status_code}")
            return False
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout during health check (/docs)")
            print_warning("Check logs: docker compose logs backend --tail=100")
        else:
            print_error(f"Backend not available! Error: {str(e)}")
        print_warning("Is Docker running? Command: docker compose up -d")
        return False


def run_all_tests():
    """
    Run all tests in sequence
    """
    print("\n")
    print("="*60)
    print(f"{Colors.BLUE}{'RUNNING ALL FRONTEND API TESTS':^60}{Colors.END}")
    print("="*60)
    
    # Test 0: Health check
    if not test_health():
        print_error("\nBackend not available! Aborting tests.")
        return
    
    # Test 1: Upload CSV
    task_id = test_1_upload_csv()
    
    if not task_id:
        print_error("\nUpload failed! Aborting tests.")
        return
    
    # Test 2: Poll status until completion
    completed = test_2_check_status(task_id)
    
    if not completed:
        print_warning("\nTask did not complete, continuing with remaining tests...")
    
    # Test 3-6: Preuzmi rezultate
    test_3_get_results(task_id)
    test_4_get_statistics(task_id)
    test_5_get_visualization(task_id)
    test_6_list_files(task_id)
    
    # Final report
    print("\n" + "="*60)
    print(f"{Colors.GREEN}{'TESTING COMPLETE':^60}{Colors.END}")
    print("="*60)
    print_info(f"Task ID: {task_id}")
    print_info("All endpoints have been tested!")


if __name__ == "__main__":
    run_all_tests()
