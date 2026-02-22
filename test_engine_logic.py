import sys
import os

# Ensure we can import from local directory
sys.path.append(os.getcwd())

# Mock Task class to avoid DB dependency for this unit test
class MockTask:
    def __init__(self, title, description="", priority="Medium", status="New", assigned_to="", tags=""):
        self.title = title
        self.description = description
        self.priority = priority
        self.status = status
        self.assigned_to = assigned_to
        self.tags = tags
        self.parent_id = None

# Import the function to test
try:
    from engine import _evaluate_condition
except ImportError as e:
    print(f"Could not import engine: {e}")
    sys.exit(1)

def run_tests():
    tests = [
        {
            "name": "Simple Keyword Match",
            "trigger": "Urgent",
            "task": MockTask(title="This is an Urgent task"),
            "expected": True
        },
        {
            "name": "Simple Keyword Mismatch",
            "trigger": "Urgent",
            "task": MockTask(title="This is a regular task"),
            "expected": False
        },
        {
            "name": "Exact Expression Match",
            "trigger": "priority == 'High'",
            "task": MockTask(title="Bug", priority="High"),
            "expected": True
        },
         {
            "name": "Exact Expression Match (Lower Case in Trigger)",
            "trigger": "priority == 'high'",
            "task": MockTask(title="Bug", priority="High"),
            "expected": True
        },
        {
            "name": "Exact Expression Mismatch",
            "trigger": "priority == 'High'",
            "task": MockTask(title="Bug", priority="Low"),
            "expected": False
        },
        {
            "name": "Contains Helper",
            "trigger": "title.contains('bug')",
            "task": MockTask(title="Critical Bug Found"),
            "expected": True
        },
        {
            "name": "Contains Helper Case Insensitive",
            "trigger": "title.contains('BUG')",
            "task": MockTask(title="Critical bug Found"),
            "expected": True
        },
        {
            "name": "Contains Helper on Description",
             "trigger": "description.contains('security')",
             "task": MockTask(title="Hack", description="Security breach"),
             "expected": True
        },
        {
            "name": "Syntax Error Fallback (as keyword)",
            "trigger": "This is not python code",
            "task": MockTask(title="Title says This is not python code"),
            "expected": True # Fallback checks if "This is not python code" is in title
        }
    ]

    print("Running Engine Evaluation Tests...\n")
    passed = 0
    for t in tests:
        result = _evaluate_condition(t['trigger'], t['task'], "TestRule")
        status = "[OK] PASS" if result == t['expected'] else f"[ERREUR] FAIL (Expected {t['expected']}, got {result})"
        print(f"Test '{t['name']}': {status}")
        if result == t['expected']:
            passed += 1

    print(f"\n{passed}/{len(tests)} tests passed.")

if __name__ == "__main__":
    run_tests()
