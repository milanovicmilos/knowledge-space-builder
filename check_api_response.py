import requests
import json

response = requests.get("http://localhost:8000/api/v1/analysis/11/statistics")
print("Status Code:", response.status_code)
print("\nResponse JSON:")
print(json.dumps(response.json(), indent=2))
