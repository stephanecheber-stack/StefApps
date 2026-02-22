import sys
import os
sys.path.append(os.getcwd())

from database import SessionLocal, init_db
import models
from engine import cascade_completion

def test_hierarchy():
    print("--- Initializing DB ---")
    init_db()
    db = SessionLocal()
    
    try:
        # 1. Setup Data
        print("\n[TEST] Creating Parent and Child...")
        parent = models.Task(title="Parent Task", status="En cours")
        db.add(parent)
        db.commit()
        db.refresh(parent)
        
        child = models.Task(title="Child Task", parent_id=parent.id, status="En cours")
        db.add(child)
        db.commit()
        db.refresh(child)
        
        print(f"Parent ID: {parent.id}")
        print(f"Child ID: {child.id}, Parent ID: {child.parent_id}")

        # 2. Test Cascade Completion
        print("\n[TEST] Testing Cascade Completion...")
        # Simulate status update to Done
        parent.status = "Terminé"
        cascade_completion(parent, db)
        db.commit()
        
        db.refresh(child)
        if child.status == "Terminé":
            print("SUCCESS: Child status is 'Terminé'")
        else:
            print(f"FAILURE: Child status is '{child.status}'")
            
        # Check Audit Log
        logs = db.query(models.AuditLog).filter(models.AuditLog.task_id == child.id).all()
        found_log = any("[SYSTEME] Clôture automatique" in log.message for log in logs)
        if found_log:
            print("SUCCESS: Audit Log found")
        else:
            print("FAILURE: No Audit Log found")

        # 3. Test Cascade Deletion
        print("\n[TEST] Testing Cascade Deletion...")
        db.delete(parent)
        db.commit()
        
        child_check = db.query(models.Task).filter(models.Task.id == child.id).first()
        if child_check is None:
            print("SUCCESS: Child task deleted")
        else:
            print("FAILURE: Child task still exists")

    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_hierarchy()
