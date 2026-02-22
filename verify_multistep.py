import requests
import time
import shutil

API_URL = "http://localhost:8000"

def setup_test_rules():
    print("Setting up test rules...")
    shutil.copy("workflows_test.yaml", "workflows.yaml")

def test_multistep_execution():
    print("\n[TEST] Multi-Step Execution...")
    
    # Create Trigger Task
    payload = {
        "title": "Multistep Trigger",
        "description": "Triggering the engine",
        "priority": "Basse"
    }
    
    resp = requests.post(f"{API_URL}/tasks/", json=payload)
    if resp.status_code != 200:
        print(f"FAIL: Create task failed: {resp.text}")
        return
        
    task_id = resp.json()['id']
    print(f"Created Trigger Task ID: {task_id}")
    
    # Wait for processing (sync in this app, but safe to wait)
    time.sleep(1)
    
    # Verify Update Step
    updated_task = requests.get(f"{API_URL}/tasks/").json()
    # Find our task
    parent = next((t for t in updated_task if t['id'] == task_id), None)
    
    if parent['priority'] == "Haute":
        print("PASS: Step 1 (Update) successful.")
    else:
        print(f"FAIL: Step 1 Priority is {parent['priority']}")
        
    # Verify Create Subtask Step
    subtask = next((t for t in updated_task if t.get('parent_id') == task_id), None)
    
    if subtask:
        print(f"PASS: Step 2 (Create Task) successful. Subtask ID: {subtask['id']}")
        if subtask['title'] == "Subtask Auto":
             print("PASS: Subtask title correct.")
    else:
        print("FAIL: Step 2 Subtask NOT found.")
        
    # Verify Audit Logs
    logs = requests.get(f"{API_URL}/tasks/{task_id}/audit").json()
    step1_log = any("Step 1" in l['message'] for l in logs)
    step2_log = any("Step 2" in l['message'] for l in logs)
    
    if step1_log and step2_log:
        print("PASS: Audit logs found for both steps.")
    else:
        print(f"FAIL: Missing Audit logs. Found: {[l['message'] for l in logs]}")

if __name__ == "__main__":
    setup_test_rules()
    test_multistep_execution()
