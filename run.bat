@echo off
echo ===================================================
echo      LiteFlow - Initialisation du Lancement
echo ===================================================

echo [1/3] Installation/Verification des dependances...
call venv\Scripts\python -m pip install -r requirements.txt

echo [2/3] Demarrage du Backend FastAPI...
start "LiteFlow Backend" cmd /k "venv\Scripts\uvicorn main:app --reload --host 127.0.0.1 --port 8000"

echo [3/3] Demarrage du Frontend Streamlit...
echo Attente du demarrage du backend...
timeout /t 5 /nobreak
start "LiteFlow Frontend" cmd /k "venv\Scripts\streamlit run app.py"

echo ===================================================
echo               Lancement effectue !
echo      Backend: http://127.0.0.1:8000/docs
echo      Frontend: http://localhost:8501
echo ===================================================
