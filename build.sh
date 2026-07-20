#!/usr/bin/env bash
# Script de build Render : installe les dépendances, collecte les fichiers
# statiques et applique les migrations avant chaque déploiement.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Crée le premier compte admin si les variables DJANGO_SUPERUSER_* sont
# présentes et qu'aucun superuser n'existe encore (sans échouer le build
# si le compte existe déjà).
if [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || true
fi
