@echo off
TITLE LiteFlow Pro - Arret en cours
echo ==========================================
echo    ARRET DE LITEFLOW PRO
echo ==========================================

echo [1/2] Fermeture du Backend...
taskkill /FI "WINDOWTITLE eq LiteFlow BACKEND*" /T /F >nul 2>&1

echo [2/2] Fermeture du Frontend...
taskkill /FI "WINDOWTITLE eq LiteFlow FRONTEND*" /T /F >nul 2>&1

echo ==========================================
echo    APPLICATION ARRETEE PROPREMENT.
echo ==========================================
timeout /t 3
