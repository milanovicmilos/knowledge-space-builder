"""
Test API endpoints - Simulira sve zahteve koje frontend salje backend-u

Testira kompletnu workflow:
1. Upload CSV fajla
2. Kreiranje task-a
3. Pracenje progresa
4. Preuzimanje rezultata, statistike, vizualizacije, fajlova
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
    """ANSI colors za terminal output"""
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
    """
    Test 1: Upload CSV fajla i kreiranje task-a
    
    POST /api/v1/analysis/run
    
    Frontend šalje:
    - file: FormData sa CSV fajlom
    
    Backend vraća:
    - task_id: int
    - status: str
    - progress: int
    - message: str
    """
    print("\n" + "="*60)
    print_info("Test 1: Upload CSV i kreiranje task-a")
    print("="*60)
    
    # Koristi matheGesamt.csv iz LSG data
    test_csv_path = Path(CSV_PATH)
    if not test_csv_path.exists():
        print_error(f"CSV fajl ne postoji: {test_csv_path}")
        return None
    print_info(f"Koristim CSV: {test_csv_path}")
    
    try:
        with open(test_csv_path, 'rb') as f:
            files = {'file': ('test_data.csv', f, 'text/csv')}
            
            print_info(f"Šaljem POST {API_BASE}/run")
            response = requests.post(
                f"{API_BASE}/run",
                files=files,
                timeout=REQUEST_TIMEOUT,
            )
            
            print_info(f"Status kod: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print_success("CSV uspešno upload-ovan!")
                print(f"  Task ID: {data.get('task_id')}")
                print(f"  Status: {data.get('status')}")
                print(f"  Progress: {data.get('progress')}%")
                print(f"  Message: {data.get('message')}")
                
                # Vrati task_id za sledeće testove
                return data.get('task_id')
            else:
                print_error(f"Upload failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return None
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout pri upload-u (POST /run)")
            print_warning("Proveri logove: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Greška: {str(e)}")
        return None
    
    finally:
        pass


def test_2_check_status(task_id):
    """
    Test 2: Provera statusa task-a
    
    GET /api/v1/analysis/{task_id}/status
    
    Frontend poziva ovaj endpoint svake 1 sekunde dok je task aktivan
    
    Backend vraća:
    - task_id: int
    - status: str (pending, running, completed, failed)
    - progress: int (0-100)
    - message: str
    - created_at: str
    - started_at: str | null
    - completed_at: str | null
    - error_message: str | null
    """
    print("\n" + "="*60)
    print_info("Test 2: Praćenje statusa task-a")
    print("="*60)
    
    if not task_id:
        print_error("Nema task_id za testiranje!")
        return False
    
    max_attempts = 60  # 60 sekundi max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            print_info(f"Pokušaj {attempt + 1}/{max_attempts} - GET {API_BASE}/{task_id}/status")
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
                    print_success("Task završen uspešno!")
                    print(f"  Started at: {data.get('started_at')}")
                    print(f"  Completed at: {data.get('completed_at')}")
                    return True
                
                elif status == 'failed':
                    print_error("Task neuspešan!")
                    print(f"  Error: {data.get('error_message')}")
                    return False
                
                elif status in ['pending', 'running']:
                    print_info(f"Task još uvek radi... ({progress}%)")
                    time.sleep(1)
                    attempt += 1
                    continue
                
            else:
                print_error(f"Status check failed: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
        
        except Exception as e:
            if isinstance(e, requests.Timeout):
                print_error("Timeout pri proveri statusa (GET /status)")
                print_warning("Proveri logove: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
            else:
                print_error(f"Greška: {str(e)}")
            return False
    
    print_warning("Timeout - task nije završen u predviđenom vremenu")
    return False


def test_3_get_results(task_id):
    """
    Test 3: Preuzimanje rezultata analize
    
    GET /api/v1/analysis/{task_id}/results
    
    Backend vraća:
    - task_id: int
    - status: str
    - completed_at: str
    - files: dict sa JSON podacima iz output fajlova
    """
    print("\n" + "="*60)
    print_info("Test 3: Preuzimanje rezultata")
    print("="*60)
    
    if not task_id:
        print_error("Nema task_id za testiranje!")
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
            print_success("Rezultati uspešno preuzeti!")
            print(f"  Task ID: {data.get('task_id')}")
            print(f"  Status: {data.get('status')}")
            print(f"  Completed at: {data.get('completed_at')}")
            print(f"  Broj fajlova: {len(data.get('files', {}))}")
            
            # Prikaži dostupne fajlove
            files = data.get('files', {})
            if files:
                print_info("Dostupni fajlovi:")
                for filename in files.keys():
                    print(f"    - {filename}")

            # Uporedi sadržaj sa lokalnim output JSON fajlovima
            all_match = True
            for filename, content in files.items():
                if filename.endswith('.json'):
                    local_path = Path(OUTPUT_DIR) / filename
                    if not local_path.exists():
                        print_warning(f"Lokalni fajl ne postoji: {local_path}")
                        all_match = False
                        continue
                    try:
                        with open(local_path, 'r', encoding='utf-8') as lf:
                            local_json = json.load(lf)
                        if local_json == content:
                            print_success(f"Podudaranje: {filename}")
                        else:
                            print_error(f"NE PODUDARA se: {filename}")
                            all_match = False
                    except Exception as e:
                        print_error(f"Greška pri poređenju {filename}: {e}")
                        all_match = False
            if all_match:
                print_success("Svi JSON fajlovi u bazi identični su lokalnim output fajlovima!")
            else:
                print_warning("Postoje razlike između baze i lokalnih output fajlova.")
        
        else:
            print_error(f"Get results failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout pri preuzimanju rezultata (GET /results)")
            print_warning("Proveri logove: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Greška: {str(e)}")


def test_4_get_statistics(task_id):
    """
    Test 4: Preuzimanje statistike
    
    GET /api/v1/analysis/{task_id}/statistics
    
    Backend vraća:
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
    print_info("Test 4: Preuzimanje statistike")
    print("="*60)
    
    if not task_id:
        print_error("Nema task_id za testiranje!")
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
            print_success("Statistika uspešno preuzeta!")
            print(f"  Task ID: {data.get('task_id')}")
            
            stats = data.get('statistics', {})
            print_info("Statistika:")
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
            print_error("Timeout pri preuzimanju statistike (GET /statistics)")
            print_warning("Proveri logove: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Greška: {str(e)}")


def test_5_get_visualization(task_id):
    """
    Test 5: Preuzimanje vizualizacije (graph PNG)
    
    GET /api/v1/analysis/{task_id}/visualization
    
    Backend vraća:
    - task_id: int
    - graph_file: str (path to PNG)
    - graph_exists: bool
    """
    print("\n" + "="*60)
    print_info("Test 5: Preuzimanje vizualizacije")
    print("="*60)
    
    if not task_id:
        print_error("Nema task_id za testiranje!")
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
            print_success("Vizualizacija info uspešno preuzet!")
            print(f"  Task ID: {data.get('task_id')}")
            print(f"  Graph file: {data.get('graph_file')}")
            print(f"  Graph exists: {data.get('graph_exists')}")
        
        else:
            print_error(f"Get visualization failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout pri preuzimanju vizualizacije (GET /visualization)")
            print_warning("Proveri logove: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Greška: {str(e)}")


def test_6_list_files(task_id):
    """
    Test 6: Lista svih dostupnih fajlova
    
    GET /api/v1/analysis/{task_id}/files
    
    Backend vraća:
    - task_id: int
    - total_files: int
    - files: list[dict]
        - name: str
        - size: int
        - path: str
    """
    print("\n" + "="*60)
    print_info("Test 6: Lista svih fajlova")
    print("="*60)
    
    if not task_id:
        print_error("Nema task_id za testiranje!")
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
            print_success("Lista fajlova uspešno preuzeta!")
            print(f"  Task ID: {data.get('task_id')}")
            print(f"  Total files: {data.get('total_files')}")
            
            files = data.get('files', [])
            if files:
                print_info("Fajlovi:")
                for file in files:
                    size_kb = file.get('size', 0) / 1024
                    print(f"    - {file.get('name')} ({size_kb:.2f} KB)")
        
        else:
            print_error(f"List files failed: {response.status_code}")
            print(f"  Response: {response.text}")
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout pri listanju fajlova (GET /files)")
            print_warning("Proveri logove: docker compose logs backend --tail=100 && docker compose logs celery_worker --tail=100")
        else:
            print_error(f"Greška: {str(e)}")


def test_health():
    """
    Test 0: Proveri da li je backend dostupan
    """
    print("\n" + "="*60)
    print_info("Test 0: Health check - Da li je backend dostupan?")
    print("="*60)
    
    try:
        print_info(f"GET {BASE_URL}/health")
        response = requests.get(
            f"{BASE_URL}/health",
            timeout=REQUEST_TIMEOUT,
        )
        
        if response.status_code == 200:
            print_success("Backend je dostupan!")
            return True
        else:
            print_error(f"Backend nije dostupan! Status: {response.status_code}")
            return False
    
    except Exception as e:
        if isinstance(e, requests.Timeout):
            print_error("Timeout pri health check-u (/docs)")
            print_warning("Proveri logove: docker compose logs backend --tail=100")
        else:
            print_error(f"Backend nije dostupan! Greška: {str(e)}")
        print_warning("Da li je Docker pokrenut? Komanda: docker compose up -d")
        return False


def run_all_tests():
    """
    Pokreni sve testove redom
    """
    print("\n")
    print("="*60)
    print(f"{Colors.BLUE}{'TESTIRANJE SVIH API ZAHTEVA SA FRONT-A':^60}{Colors.END}")
    print("="*60)
    
    # Test 0: Health check
    if not test_health():
        print_error("\nBackend nije dostupan! Prekidam testiranje.")
        return
    
    # Test 1: Upload CSV
    task_id = test_1_upload_csv()
    
    if not task_id:
        print_error("\nUpload neuspešan! Prekidam testiranje.")
        return
    
    # Test 2: Prati status dok se ne završi
    completed = test_2_check_status(task_id)
    
    if not completed:
        print_warning("\nTask nije završen, ali nastavljam sa testovima...")
    
    # Test 3-6: Preuzmi rezultate
    test_3_get_results(task_id)
    test_4_get_statistics(task_id)
    test_5_get_visualization(task_id)
    test_6_list_files(task_id)
    
    # Završni izvještaj
    print("\n" + "="*60)
    print(f"{Colors.GREEN}{'TESTIRANJE ZAVRŠENO':^60}{Colors.END}")
    print("="*60)
    print_info(f"Task ID: {task_id}")
    print_info("Svi endpointi su testirani!")


if __name__ == "__main__":
    run_all_tests()
