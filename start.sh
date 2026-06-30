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

echo ">>> Verification de la configuration Django (settings.py)..."
if ! python manage.py check --deploy 2>&1; then
  echo "════════════════════════════════════════"
  echo "  ERREUR: settings.py a une erreur de configuration."
  echo "  Verifiez vos variables d'environnement (CLOUDINARY_URL, etc.)"
  echo "  Le serveur va quand meme tenter de demarrer."
  echo "════════════════════════════════════════"
fi

echo ">>> Application des migrations (creation des tables si absentes)..."
python manage.py migrate --no-input --verbosity 2

echo ">>> Verification des tables critiques..."
python manage.py shell -c "
from django.db import connection
tables = connection.introspection.table_names()
critical = ['auth_user', 'django_session', 'quiz_userprofile', 'quiz_dailyquestion']
missing = [t for t in critical if t not in tables]
if missing:
    print('ATTENTION: tables manquantes apres migration:', missing)
    print('Tentative de re-migration forcee...')
else:
    print('OK: toutes les tables critiques sont presentes.')
" || echo "Verification ignoree (shell indisponible), poursuite du demarrage."

echo ">>> Lancement de Gunicorn..."
exec gunicorn kingch_project.wsgi:application \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --timeout 120 \
  --log-file -
