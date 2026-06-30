# Guide complet — Donnees permanentes sur Render

KING CH stocke deux types de donnees qui doivent toutes les deux
etre rendues persistantes :

| Type de donnee | Exemple | Solution |
|---|---|---|
| Donnees en base | Comptes utilisateurs, points, questions, reponses, sessions | **PostgreSQL** |
| Fichiers uploades | Photos de profil, certificats, logo manno.png | **Cloudinary ou Backblaze B2** |

Sans les deux, les informations disparaissent a chaque redemarrage
du service (apres 15 min d'inactivite sur le plan gratuit, ou a
chaque nouveau deploiement), car Render utilise un disque ephemere.

---

## PARTIE 1 — Base de donnees PostgreSQL (deja configuree)

### Avec render.yaml (recommande)
1. Poussez `kingch_project/` sur GitHub
2. Render -> **New > Blueprint** -> connectez le repo
3. Render cree automatiquement le service web + la base PostgreSQL
   et lie `DATABASE_URL` automatiquement
4. Cliquez **Apply**

### Configuration manuelle
1. Render -> **New > PostgreSQL** -> nommez `kingch-db` -> Create
2. Copiez l'**Internal Database URL**
3. Sur votre service web -> **Environment** -> ajoutez :
   - `DATABASE_URL` = (URL copiee)

Verification dans les logs du build, vous devez voir :
```
DATABASE_URL detectee — PostgreSQL sera utilise (persistant).
```

---

## PARTIE 2 — Stockage des images

Vous avez deja un compte Cloudinary, voici comment l'utiliser
(OPTION A). Backblaze B2 reste disponible en alternative (OPTION B).

### OPTION A — Cloudinary (vous avez deja ce compte)

Sur votre Dashboard Cloudinary (console.cloudinary.com), vous voyez :

| Champ affiche | Exemple sur votre capture |
|---|---|
| Nom du nuage | `dxv28qy7z` |
| Cle API | `175119436122486` |
| Secret de l'API | cliquez **Reveler** pour l'afficher |

**IMPORTANT — securite** : ne partagez jamais ces 3 valeurs
publiquement (captures d'ecran publiques, depot GitHub public, etc.)
Le secret API donne un acces complet a votre compte Cloudinary.

#### Etape 1 — Construire votre CLOUDINARY_URL
Le format est :
```
cloudinary://CLE_API:SECRET_API@NOM_DU_NUAGE
```

Avec votre exemple (remplacez SECRET_API par votre vrai secret
revele sur le dashboard) :
```
cloudinary://175119436122486:VOTRE_SECRET_ICI@dxv28qy7z
```

#### Etape 2 — Ajouter la variable sur Render
1. Sur Render, ouvrez votre service web `kingch`
2. Onglet **Environment**
3. Ajoutez :

   | Cle | Valeur |
   |---|---|
   | `CLOUDINARY_URL` | `cloudinary://175119436122486:VOTRE_SECRET@dxv28qy7z` |

4. Cliquez **Save Changes** — Render redeploiera automatiquement

#### Etape 3 — Verifier
Apres le redeploiement, uploadez une photo de profil ou un certificat
depuis l'admin. L'URL de l'image doit commencer par :
```
https://res.cloudinary.com/dxv28qy7z/...
```
Cela confirme que Cloudinary fonctionne et que vos images sont
desormais persistantes.

---

### OPTION B — Backblaze B2 (alternative)

Si vous preferez ne pas utiliser Cloudinary, Backblaze B2 reste
disponible et configure dans le projet.

1. Compte gratuit sur https://www.backblaze.com/sign-up/cloud-storage
2. Activer B2 Cloud Storage dans **My Settings**
3. Creer un bucket public nomme `kingch-media`
4. Creer une cle d'application limitee a ce bucket
5. Ajouter sur Render :

   | Cle | Valeur |
   |---|---|
   | `B2_ACCESS_KEY_ID` | votre keyID |
   | `B2_SECRET_ACCESS_KEY` | votre applicationKey |
   | `B2_BUCKET_NAME` | `kingch-media` |
   | `B2_ENDPOINT_URL` | ex: `https://s3.us-west-004.backblazeb2.com` |

**Note** : si `CLOUDINARY_URL` ET les variables B2 sont toutes
definies en meme temps, Cloudinary sera utilise en priorite.

---

### Sans aucune configuration
Si vous ne configurez ni Cloudinary ni Backblaze, le site fonctionne
quand meme normalement, mais les images uploadees seront perdues a
chaque redemarrage du service (les donnees texte en base PostgreSQL,
elles, resteront intactes).

---

## Depannage — erreur "Invalid CLOUDINARY_URL scheme"

Si vos logs Render affichent :
```
ValueError: Invalid CLOUDINARY_URL scheme. Expecting to start with 'cloudinary://'
```

Cela signifie que la variable `CLOUDINARY_URL` collee sur Render est
mal formee. Causes les plus frequentes :

1. **Le prefixe `cloudinary://` est manquant** — vous avez colle
   uniquement `CLE:SECRET@CLOUD_NAME` sans le debut.
2. **Des guillemets ont ete colles par erreur**, ex:
   `"cloudinary://..."` au lieu de `cloudinary://...`
3. **Un espace** s'est glisse au debut ou a la fin de la valeur.

**Cette version du projet corrige automatiquement ces 3 cas** (le
code nettoie la valeur au demarrage). Si l'erreur persiste malgre
tout, verifiez que :
- Le **Secret de l'API** a bien ete "Revele" et copie en entier sur
  Cloudinary (pas seulement les premiers caracteres visibles)
- Aucun retour a la ligne ne s'est glisse dans le champ Render
- La variable s'appelle exactement `CLOUDINARY_URL` (sensible a la
  casse) dans l'onglet Environment de Render

Apres correction, Render redeploiera automatiquement.

---

## Recapitulatif des variables d'environnement Render

| Variable | Obligatoire | Role |
|---|---|---|
| `DEBUG` | Oui | `False` en production |
| `SECRET_KEY` | Oui | Cle secrete Django |
| `ALLOWED_HOSTS` | Oui | `.onrender.com` |
| `DATABASE_URL` | **Oui** | Connexion PostgreSQL (persistance des donnees) |
| `CLOUDINARY_URL` | **Recommande** | Stockage persistant des images (Option A) |
| `B2_ACCESS_KEY_ID` | Alternative | Cle Backblaze B2 (Option B) |
| `B2_SECRET_ACCESS_KEY` | Alternative | Secret Backblaze B2 (Option B) |
| `B2_BUCKET_NAME` | Alternative | Nom du bucket B2 (Option B) |
| `B2_ENDPOINT_URL` | Alternative | URL endpoint B2 (Option B) |
| `DJANGO_SUPERUSER_USERNAME` | Optionnel | Cree l'admin automatiquement au build |
| `DJANGO_SUPERUSER_PASSWORD` | Optionnel | Mot de passe de l'admin auto-cree |
| `DJANGO_SUPERUSER_EMAIL` | Optionnel | Email de l'admin auto-cree |
| `WHATSAPP_NUMBER` | Optionnel | Numero affiche dans le footer |

---

## Creer le compte admin

### Methode 1 — Render Shell
1. Service web -> onglet **Shell**
2. `python manage.py createsuperuser`

### Methode 2 — Automatique au build
Ajoutez `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_PASSWORD`,
`DJANGO_SUPERUSER_EMAIL` avant le premier deploiement.

---

## Fichiers concernes

| Fichier | Role |
|---|---|
| `render.yaml` | Service web + base PostgreSQL liee automatiquement |
| `build.sh` | Installe, migre, collecte le statique |
| `start.sh` | Re-applique les migrations a chaque demarrage (filet de securite) |
| `requirements.txt` | Versions figees + Cloudinary + Backblaze B2 (au choix) |
| `runtime.txt` | Force Python 3.12.7 |
| `settings.py` | Active Cloudinary si `CLOUDINARY_URL` est presente, sinon Backblaze B2 si `B2_*` est presente |
