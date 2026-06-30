#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════
# KING CH — Script de build Render
# Installe les dependances, applique les migrations PostgreSQL,
# collecte les fichiers statiques, cree le superuser si fourni.
# ════════════════════════════════════════════════════════════════
set -o errexit  # stop immediatement si une commande echoue

echo "════════════════════════════════════════"
echo "  KING CH — Build en cours..."
echo "════════════════════════════════════════"

echo ">>> [1/4] Installation des dependances..."
pip install -r requirements.txt

echo ">>> [2/4] Verification de la base de donnees..."
if [ -z "$DATABASE_URL" ]; then
  echo "ATTENTION: DATABASE_URL n'est pas definie !"
  echo "Sans DATABASE_URL, Django utilise SQLite local qui sera EFFACE"
  echo "a chaque redeploiement sur Render (disque ephemere)."
  echo "Ajoutez une base PostgreSQL et la variable DATABASE_URL"
  echo "dans les parametres de votre service Render."
else
  echo "DATABASE_URL detectee — PostgreSQL sera utilise (persistant)."
fi

echo ">>> [3/4] Application des migrations..."
python manage.py migrate --no-input

echo ">>> [4/4] Collecte des fichiers statiques..."
python manage.py collectstatic --no-input --clear

# Creation automatique du superuser si les variables sont fournies
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo ">>> Creation du superuser '$DJANGO_SUPERUSER_USERNAME'..."
  python manage.py createsuperuser \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@kingch.com}" \
    --noinput || echo "Superuser existe deja ou erreur ignoree."
fi

echo "════════════════════════════════════════"
echo "  Build termine avec succes !"
echo "════════════════════════════════════════"
