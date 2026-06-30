#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
# KING CH — Script de demarrage Render
# Re-applique les migrations au demarrage (filet de securite)
# puis lance Gunicorn.
# ════════════════════════════════════════════════════════════════
set -o errexit

echo "════════════════════════════════════════"
echo "  KING CH — Demarrage du serveur"
echo "════════════════════════════════════════"

if [ -z "$DATABASE_URL" ]; then
  echo "ERREUR CRITIQUE: DATABASE_URL n'est pas definie."
  echo "Le site va demarrer mais TOUTES les donnees seront PERDUES"
  echo "au prochain redeploiement (SQLite sur disque ephemere)."
  echo "Configurez une base PostgreSQL sur Render et liez DATABASE_URL."
fi

echo ">>> Verification/application des migrations..."
python manage.py migrate --no-input

echo ">>> Lancement de Gunicorn..."
exec gunicorn kingch_project.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --timeout 120 \
  --log-file -
