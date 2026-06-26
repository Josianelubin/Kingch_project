#!/bin/bash
echo ""
echo "  ================================================"
echo "    KING CH - Plateforme de Quiz"
echo "    Cree par Emmanuel Christopher Badio"
echo "  ================================================"
echo ""

set -e

echo "  [1/4] Installation des dependances..."
pip install -r requirements.txt -q

echo "  [2/4] Creation de la base de donnees..."
python manage.py makemigrations quiz --no-input 2>/dev/null || true
python manage.py migrate --no-input

echo "  [3/4] Fichiers statiques..."
python manage.py collectstatic --no-input --clear 2>/dev/null || true

echo ""
echo "  ================================================"
echo "    Ouvrez votre navigateur sur:"
echo "    http://127.0.0.1:8000"
echo ""
echo "    Interface admin:"
echo "    http://127.0.0.1:8000/admin/"
echo "  ================================================"
echo ""

python manage.py runserver 0.0.0.0:8000
