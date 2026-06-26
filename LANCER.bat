@echo off
title KING CH - Demarrage
color 0E
echo.
echo  ================================================
echo    KING CH - Plateforme de Quiz
echo    Cree par Emmanuel Christopher Badio
echo  ================================================
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR: Python n'est pas installe.
    echo  Telechargez Python sur https://www.python.org/downloads/
    pause
    exit /b
)

REM Installer les dependances
echo  [1/4] Installation des dependances...
pip install -r requirements.txt --quiet

REM Creer les migrations
echo  [2/4] Creation de la base de donnees...
python manage.py makemigrations quiz --no-input 2>nul
python manage.py migrate --no-input

REM Collecter les fichiers statiques
echo  [3/4] Preparation des fichiers statiques...
python manage.py collectstatic --no-input --clear 2>nul

REM Verifier si un superuser existe
echo  [4/4] Demarrage du serveur...
echo.
echo  ================================================
echo    Ouvrez votre navigateur sur:
echo    http://127.0.0.1:8000
echo.
echo    Interface admin:
echo    http://127.0.0.1:8000/admin/
echo  ================================================
echo.
echo  (Appuyez sur CTRL+C pour arreter le serveur)
echo.

python manage.py runserver 0.0.0.0:8000
pause
