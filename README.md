# KING CH — Plateforme de Quiz
Cree par Emmanuel Christopher Badio

---

## DEMARRAGE RAPIDE (Windows)

1. Double-cliquez sur **LANCER.bat**
2. La premiere fois, cliquez aussi sur **CREER_ADMIN.bat** pour creer un compte admin
3. Ouvrez http://127.0.0.1:8000 dans votre navigateur

---

## DEMARRAGE MANUEL (tous systemes)

```bash
cd kingch_project
pip install -r requirements.txt
python manage.py makemigrations quiz
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Ouvrez http://127.0.0.1:8000

---

## ERREUR ERR_SSL_PROTOCOL_ERROR

Si vous voyez cette erreur:
- Verifiez que l'URL commence par http:// et NON https://
- Tapez exactement: http://127.0.0.1:8000
- Cette erreur est maintenant corrigee dans ce fichier settings.py

---

## DEPLOIEMENT SUR RENDER.COM

1. Poussez le dossier kingch_project/ sur GitHub
2. Sur render.com: New > Web Service
3. Build Command: bash build.sh
4. Start Command: gunicorn kingch_project.wsgi:application --bind 0.0.0.0:$PORT
5. Variables d'environnement obligatoires:
   - DEBUG = False
   - SECRET_KEY = (une cle longue aleatoire)
   - ALLOWED_HOSTS = .onrender.com

---

## LOGO ADMIN (manno.png)

Remplacez le fichier static/images/manno.png par votre vraie image.
Le fichier actuel est un carre or de 64x64 pixels (placeholder).

---

## ACCES ADMIN

URL: http://127.0.0.1:8000/admin/
Connectez-vous avec le compte cree par createsuperuser ou CREER_ADMIN.bat

### Fonctionnalites admin:
- Bloquer / Debloquer un utilisateur
- Ajouter ou retirer des points
- Reinitialiser les points d'un utilisateur
- REINITIALISER LES POINTS DE TOUS LES UTILISATEURS (bouton global)
- Supprimer l'historique d'un utilisateur
- Supprimer un compte utilisateur
- Voir le hash du mot de passe
- Envoyer des certificats
- Gerer les questions quotidiennes
- Supprimer les questions passees

---

Cree par Emmanuel Christopher Badio — Haiti, Martissant 4
