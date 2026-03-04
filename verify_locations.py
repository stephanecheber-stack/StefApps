import time
import requests

API_URL = "http://localhost:8000"

def test_locations():
    print("--- Testing Locations CRUD ---")
    
    # 1. Create
    suffix = int(time.time())
    payload = {
        "name": f"Site Test {suffix}",
        "address": "123 Rue de la Paix",
        "zip_code": "75001",
        "city": "Paris"
    }
    resp = requests.post(f"{API_URL}/locations/", json=payload)
    if resp.status_code == 200:
        loc = resp.json()
        loc_id = loc['id']
        print(f"[OK] Created: {loc['name']} (ID: {loc_id})")
    else:
        print(f"[ERROR] Create failed: {resp.text}")
        return

    # 2. List
    resp = requests.get(f"{API_URL}/locations/")
    if resp.status_code == 200:
        print(f"[OK] List: {len(resp.json())} locations found")
    else:
        print(f"[ERROR] List failed: {resp.text}")

    # 3. Update
    update_payload = {"city": "Lyon"}
    resp = requests.put(f"{API_URL}/locations/{loc_id}", json=update_payload)
    if resp.status_code == 200:
        print(f"[OK] Updated city to: {resp.json()['city']}")
    else:
        print(f"[ERROR] Update failed: {resp.text}")

    # 4. Delete
    resp = requests.delete(f"{API_URL}/locations/{loc_id}")
    if resp.status_code == 200:
        print(f"[OK] Deleted: {resp.json()['status']}")
    else:
        print(f"[ERROR] Delete failed: {resp.text}")

if __name__ == "__main__":
    test_locations()
