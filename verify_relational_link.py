import requests
import time

API_URL = "http://localhost:8000"

def verify_link():
    print("--- Verifying User-Location Link ---")
    
    # 1. Create a Location
    suffix = int(time.time())
    loc_name = f"Site Link Test {suffix}"
    loc_payload = {
        "name": loc_name,
        "address": "456 Link Road",
        "zip_code": "69000",
        "city": "Lyon"
    }
    print(f"Creating location: {loc_name}...")
    resp = requests.post(f"{API_URL}/locations/", json=loc_payload)
    if resp.status_code != 200:
        print(f"FAILED to create location: {resp.text}")
        return
    location = resp.json()
    loc_id = location['id']
    print(f"SUCCESS: Created Location ID {loc_id}")

    # 2. Create a User linked to this Location
    user_payload = {
        "first_name": "Lien",
        "last_name": "Test",
        "address": "789 User Blvd",
        "group_ids": [],
        "location_id": loc_id
    }
    print(f"Creating user linked to Location {loc_id}...")
    resp = requests.post(f"{API_URL}/users/", json=user_payload)
    if resp.status_code != 200:
        print(f"FAILED to create user: {resp.text}")
        return
    user = resp.json()
    user_id = user['id']
    print(f"SUCCESS: Created User ID {user_id} with location_id {user['location_id']}")

    # 3. Verify via GET /users/{id}
    print(f"Verifying User {user_id} details...")
    resp = requests.get(f"{API_URL}/users/{user_id}")
    user_data = resp.json()
    if user_data.get('location') and user_data['location']['id'] == loc_id:
        print(f"SUCCESS: User {user_id} is correctly linked to Location {loc_id} in output.")
    else:
        print(f"FAILED: User {user_id} link not found in output or mismatch. Data: {user_data.get('location')}")

    # 4. Verify via GET /locations/
    print("Verifying Location details (attached users)...")
    resp = requests.get(f"{API_URL}/locations/")
    locations = resp.json()
    target_loc = next((l for l in locations if l['id'] == loc_id), None)
    if target_loc and any(u['id'] == user_id for u in target_loc.get('users', [])):
        print(f"SUCCESS: User {user_id} found in Location {loc_id}'s users list.")
    else:
        print(f"FAILED: User not found in Location's list. Users: {target_loc.get('users') if target_loc else 'N/A'}")

    # 5. Cleanup
    print("Cleaning up...")
    requests.delete(f"{API_URL}/users/{user_id}")
    requests.delete(f"{API_URL}/locations/{loc_id}")
    print("Cleanup complete.")

if __name__ == "__main__":
    try:
        verify_link()
    except Exception as e:
        print(f"ERROR: {e}")
