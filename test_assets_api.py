import requests
import time

API_URL = "http://localhost:8000"

def test_assets():
    print("Testing Assets API...")
    
    # 1. Create an asset
    asset_payload = {
        "name": "Test Laptop",
        "type": "PC",
        "serial_number": f"SN-{int(time.time())}",
        "status": "En stock",
        "assigned_user": "John Doe"
    }
    resp = requests.post(f"{API_URL}/assets/", json=asset_payload)
    if resp.status_code != 200:
        print(f"Failed to create asset: {resp.text}")
        return
    asset = resp.json()
    asset_id = asset['id']
    print(f"Asset created: ID {asset_id}")

    # 2. Get assets
    resp = requests.get(f"{API_URL}/assets/")
    assets = resp.json()
    if any(a['id'] == asset_id for a in assets):
        print("Asset found in list.")
    else:
        print("Asset NOT found in list.")

    # 3. Create a task linked to asset
    task_payload = {
        "title": "Fix Laptop",
        "description": "Screen is broken",
        "priority": "Haute",
        "asset_id": asset_id
    }
    resp = requests.post(f"{API_URL}/tasks/", json=task_payload)
    if resp.status_code != 200:
        print(f"Failed to create task: {resp.text}")
    else:
        task = resp.json()
        print(f"Task created: ID {task['id']}, Asset ID: {task.get('asset_id')}")
        if task.get('asset_id') == asset_id:
            print("Task correctly linked to asset.")
        else:
            print(f"Task NOT correctly linked to asset. Got {task.get('asset_id')}")

    # 4. Clean up (optional but good)
    # requests.delete(f"{API_URL}/tasks/{task['id']}")
    # requests.delete(f"{API_URL}/assets/{asset_id}")

if __name__ == "__main__":
    test_assets()
