import requests

API_URL = "http://localhost:8000"

def test_user_management():
    print("--- Testing User Management System ---")
    
    # 1. Ensure at least one group exists
    groups = requests.get(f"{API_URL}/groups/").json()
    if not groups:
        print("Creating a support group...")
        resp = requests.post(f"{API_URL}/groups/", json={"name": "Support N1", "classification_ids": [1]})
        group_id = resp.json()['id']
    else:
        group_id = groups[0]['id']
        print(f"Using existing group: {groups[0]['name']} (ID: {group_id})")

    # 2. Test User Creation
    user_data = {
        "first_name": "Jean",
        "last_name": "Dupont",
        "address": "123 Rue de Rivoli, Paris",
        "group_ids": [group_id]
    }
    
    print("Creating user 1...")
    resp = requests.post(f"{API_URL}/users/", json=user_data)
    if resp.status_code == 200:
        user1 = resp.json()
        print(f"SUCCESS: Created User 1 with code: {user1['user_code']}")
    else:
        print(f"FAILURE: {resp.text}")
        return

    print("Creating user 2...")
    resp = requests.post(f"{API_URL}/users/", json=user_data)
    if resp.status_code == 200:
        user2 = resp.json()
        print(f"SUCCESS: Created User 2 with code: {user2['user_code']}")
    else:
        print(f"FAILURE: {resp.text}")

    # 3. Test User Listing
    print("Listing users...")
    users = requests.get(f"{API_URL}/users/").json()
    print(f"Total users found: {len(users)}")
    for u in users:
        grps = [g['name'] for g in u['groups']]
        print(f"- {u['user_code']}: {u['first_name']} {u['last_name']} (Groups: {', '.join(grps)})")

    # 4. Test User Update
    print(f"Updating user {user1['id']}...")
    update_data = {"first_name": "Jean-Pierre"}
    resp = requests.put(f"{API_URL}/users/{user1['id']}", json=update_data)
    if resp.status_code == 200:
        print(f"SUCCESS: User updated name: {resp.json()['first_name']}")
    else:
        print(f"FAILURE: {resp.text}")

    # 5. Cleanup
    print("Cleaning up test users...")
    requests.delete(f"{API_URL}/users/{user1['id']}")
    requests.delete(f"{API_URL}/users/{user2['id']}")
    print("Cleanup complete.")

if __name__ == "__main__":
    try:
        test_user_management()
    except Exception as e:
        print(f"ERROR during test: {e}")
