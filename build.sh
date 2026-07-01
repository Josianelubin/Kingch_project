#!/usr/bin/env bash
set -o errexit

echo "════════════════════════════════════════"
echo "  KING CH — Build Render"
echo "════════════════════════════════════════"

echo ">>> [1/4] Installation des dependances..."
pip install -r requirements.txt

echo ">>> [2/4] Verification configuration..."
echo "    DEBUG       = ${DEBUG:-non defini → True en local}"
echo "    DATABASE_URL = ${DATABASE_URL:+definie (PostgreSQL)}"
echo "    DATABASE_URL = ${DATABASE_URL:-NON DEFINIE → SQLite ephemere !}"
echo "    CLOUDINARY   = ${CLOUDINARY_URL:+definie}"
echo "    CLOUDINARY   = ${CLOUDINARY_URL:-non definie}"

if [ -z "$DATABASE_URL" ]; then
  echo ""
  echo "  ATTENTION: DATABASE_URL absente !"
  echo "  Toutes les donnees seront perdues a chaque redeploiement."
  echo "  Ajoutez une base PostgreSQL dans les settings Render."
  echo ""
fi

echo ">>> [3/4] Migration de la base de donnees..."
python manage.py migrate --no-input --verbosity 1

echo ">>> [4/4] Collecte des fichiers statiques..."
python manage.py collectstatic --no-input --clear

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo ">>> Creation du superuser '$DJANGO_SUPERUSER_USERNAME'..."
  python manage.py createsuperuser \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@kingch.com}" \
    --noinput || echo "  (superuser existe deja)"
fi

echo "════════════════════════════════════════"
echo "  Build OK"
echo "════════════════════════════════════════"
