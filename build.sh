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

# Réinitialise le mot de passe d'un compte existant si ADMIN_RESET_EMAIL
# et ADMIN_RESET_PASSWORD sont fournis (utilitaire ponctuel, à retirer des
# variables d'environnement une fois utilisé).
if [ -n "$ADMIN_RESET_EMAIL" ] && [ -n "$ADMIN_RESET_PASSWORD" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
import os
User = get_user_model()
u = User.objects.filter(email=os.environ['ADMIN_RESET_EMAIL']).first()
if u:
    u.set_password(os.environ['ADMIN_RESET_PASSWORD'])
    u.save()
    print('password reset for', u.email)
else:
    print('no user found for', os.environ['ADMIN_RESET_EMAIL'])
"
fi
