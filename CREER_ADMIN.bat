@echo off
title KING CH - Creer un compte administrateur
color 0E
echo.
echo  ================================================
echo    KING CH - Creer un compte administrateur
echo  ================================================
echo.
echo  Ce script cree un compte administrateur
echo  pour acceder a http://127.0.0.1:8000/admin/
echo.
python manage.py createsuperuser
echo.
echo  Compte cree! Lancez LANCER.bat puis allez sur
echo  http://127.0.0.1:8000/admin/
echo.
pause
