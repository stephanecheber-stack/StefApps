# -*- coding: utf-8 -*-
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# --- IMPORTS DE L'APPLICATION ---
try:
    from main import app
    from engine import process_workflow
    import models
except ImportError as e:
    print(f"Erreur d'import : {e}")
    sys.exit(1)

# --- CONFIGURATION DES TESTS ---
client = TestClient(app)

# --- 1. TESTS API ---
def test_api_tasks():
    """Vérifie que GET /tasks/ répond 200."""
    # On mock l'authentification pour bypasser dependency injection si nécessaire
    # ou on envoie un jeton bidon si le mock auth_client est en place
    with patch("main.auth_client") as mock_auth:
        mock_auth.get_user.return_value = MagicMock(user=MagicMock(id="test-uuid"))
        response = client.get("/tasks/", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200

def test_api_classifications():
    """Vérifie que GET /classifications/ répond 200."""
    with patch("main.auth_client") as mock_auth:
        mock_auth.get_user.return_value = MagicMock(user=MagicMock(id="test-uuid"))
        response = client.get("/classifications/", headers={"Authorization": "Bearer fake_token"})
        assert response.status_code == 200

# --- 2. TESTS MOTEUR DE WORKFLOW ---
def test_workflow_engine_no_crash():
    """Vérifie qu'aucun crash NoneType ne survient dans process_workflow."""
    mock_db = MagicMock()
    mock_task = MagicMock()
    mock_task.id = 999
    mock_task.title = "Test Task"
    mock_task.status = "Nouveau"
    mock_task.closed_at = None
    
    # On simule le retour de la base de données
    mock_db.query().filter().first.return_value = mock_task
    
    try:
        process_workflow(999, mock_db)
        success = True
    except Exception as e:
        print(f"Workflow Crash : {e}")
        success = False
    
    assert success is True

# --- 3. TESTS UI (STREAMLIT TESTING) ---
def test_ui_flow():
    """Simule l'initialisation de base de l'application Streamlit."""
    from streamlit.testing.v1 import AppTest
    
    at = AppTest.from_file("app.py", default_timeout=30)
    
    # Exécution de la première frame de l'application
    at.run()
    
    # Le moteur d'état s'initialise (authenticated devrait être False car pas de token par défaut)
    assert at.session_state["authenticated"] is False
    assert getattr(at.session_state, "token", None) is None
    
    # L'écran de login devrait être présent contenant les text_input Email / Mot de passe
    assert len(at.text_input) >= 2

# --- 4. EXÉCUTION ET RAPPORT ASCII ---
if __name__ == "__main__":
    results = []
    
    print("\n" + "="*50)
    print("      LITEFLOW PRO - QA AUTOMATED SUITE")
    print("="*50 + "\n")

    # API - Tasks
    try:
        test_api_tasks()
        results.append(("API: GET /tasks/", "PASS"))
    except Exception as e:
        results.append(("API: GET /tasks/", f"FAIL ({e})"))

    # API - Classifications
    try:
        test_api_classifications()
        results.append(("API: GET /classifications/", "PASS"))
    except Exception as e:
        results.append(("API: GET /classifications/", f"FAIL ({e})"))

    # Workflow
    try:
        test_workflow_engine_no_crash()
        results.append(("MOTEUR: process_workflow logic", "PASS"))
    except Exception as e:
        results.append(("MOTEUR: process_workflow logic", f"FAIL ({e})"))

    # UI Flow (On lance pytest pour l'UI car plus complexe à isoler manuellement)
    print("Execution des tests UI avec pytest...")
    retcode = pytest.main(["-q", "--tb=short", "test_suite.py::test_ui_flow"])
    ui_status = "PASS" if retcode == 0 else "FAIL"
    results.append(("UI: Login & Onglets", ui_status))

    # RAPPORT FINAL
    print("\n" + "-"*30)
    print(" RAPPORT FINAL DE TESTS")
    print("-"*30)
    for test, status in results:
        indicator = f"[{status}]" if status == "PASS" else "[FAIL]"
        print(f"{test:<35} {indicator}")
    print("-"*30 + "\n")
