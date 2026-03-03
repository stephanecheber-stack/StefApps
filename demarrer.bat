@echo off
echo Démarrage de LiteFlow...

:: Activation de l'environnement virtuel
if exist .venv\Scripts\activate (
    call .venv\Scripts\activate
) else if exist venv\Scripts\activate (
    call venv\Scripts\activate
) else (
    echo Environnement virtuel introuvable.
    pause
    exit /b
)

:: Lancement du Backend dans une nouvelle fenêtre
echo Lancement du backend (Uvicorn)...
start "LiteFlow Backend" python -m uvicorn main:app --reload

:: Lancement du Frontend dans la fenêtre actuelle
echo Lancement du frontend (Streamlit)...
python -m streamlit run app.py

pause
