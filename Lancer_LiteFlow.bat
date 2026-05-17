@echo off
TITLE LiteFlow Pro - Demarrage en cours
echo ==========================================
echo    DEMARRAGE DE LITEFLOW PRO (CLOUD)
echo ==========================================

echo [1/2] Lancement du Backend (API)...
start cmd /k "TITLE LiteFlow BACKEND && .\.venv\Scripts\python.exe -m uvicorn main:app --reload"

timeout /t 3

echo [2/2] Lancement du Frontend (Interface)...
start cmd /k "TITLE LiteFlow FRONTEND && .\.venv\Scripts\python.exe -m streamlit run app.py"

echo ==========================================
echo    APPLICATION LANCEE AVEC SUCCES !
echo    Ne fermez pas les fenetres noires.
echo ==========================================
pause
