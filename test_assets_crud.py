import requests

BASE_URL = "http://127.0.0.1:8000"

def test_assets():
    # 1. Create an asset
    asset_data = {
        "name": "PC-TEST-001",
        "asset_type": "PC",
        "serial_number": "SN123456789",
        "status": "En stock",
        "assigned_user": "User Test"
    }
    print("Creating asset...")
    response = requests.post(f"{BASE_URL}/assets/", json=asset_data)
    if response.status_code == 200:
        asset = response.json()
        print(f"Asset created: {asset}")
        asset_id = asset["id"]
    else:
        print(f"Failed to create asset: {response.status_code} - {response.text}")
        return

    # 2. Get all assets
    print("Getting assets...")
    response = requests.get(f"{BASE_URL}/assets/")
    if response.status_code == 200:
        assets = response.json()
        print(f"Assets found: {len(assets)}")
    else:
        print(f"Failed to get assets: {response.status_code}")

    # 3. Delete the asset
    print(f"Deleting asset {asset_id}...")
    response = requests.delete(f"{BASE_URL}/assets/{asset_id}")
    if response.status_code == 200:
        print(f"Asset deleted: {response.json()}")
    else:
        print(f"Failed to delete asset: {response.status_code}")

if __name__ == "__main__":
    # Note: This script assumes the server is running at BASE_URL
    # For CI/CD style testing, we would use a test client with the app object.
    print("Testing Assets CRUD...")
    try:
        test_assets()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the server at " + BASE_URL)
        print("Make sure the application is running (e.g., via 'uvicorn main:app --reload')")
