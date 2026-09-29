# Stockage des médias avec Supabase Storage

Sur Render (plan Free), le disque local n'est **pas persistant** : chaque
déploiement ou redémarrage efface tous les fichiers uploadés (photos de
profil, images de posts, couvertures d'articles, images d'annonces...).

Le code est déjà prêt pour basculer vers **Supabase Storage** (stockage
d'objets compatible S3) — il ne manque que la configuration côté Supabase et
les variables d'environnement côté Render. Tant que ces variables ne sont pas
toutes définies, l'app continue de fonctionner exactement comme aujourd'hui
(stockage local).

## 1. Créer le projet Supabase (si pas déjà fait)

1. Aller sur [supabase.com](https://supabase.com) → créer un compte / se connecter.
2. Créer un nouveau projet (choisir une région proche, ex. Europe).
3. Noter la **référence du projet** (le `project-ref`), visible dans l'URL du
   dashboard : `https://supabase.com/dashboard/project/<project-ref>`.

## 2. Créer le bucket de stockage

1. Dans le dashboard Supabase → **Storage** → **New bucket**.
2. Nom du bucket : `media` (ou un autre nom, à réutiliser ensuite).
3. Cocher **Public bucket** (les images/vidéos doivent être accessibles
   directement par URL depuis le site).

## 3. Générer les clés d'accès S3

1. Dashboard Supabase → **Project Settings** → **Storage** → onglet
   **S3 Access Keys** (parfois sous "Connection").
2. Cliquer **New access key** → noter :
   - `Access key ID`
   - `Secret access key` (affichée une seule fois, à copier immédiatement)
   - La **région** affichée à côté (ex. `eu-central-1`)

## 4. Configurer les variables d'environnement sur Render

Dans le dashboard Render → le service `Wanaag_Corner` → **Environment**,
ajouter :

| Variable                              | Valeur                                   |
|----------------------------------------|-------------------------------------------|
| `SUPABASE_STORAGE_PROJECT_REF`        | la référence du projet (étape 1)          |
| `SUPABASE_STORAGE_BUCKET`             | `media` (ou le nom choisi à l'étape 2)    |
| `SUPABASE_STORAGE_ACCESS_KEY_ID`      | la clé d'accès (étape 3)                  |
| `SUPABASE_STORAGE_SECRET_ACCESS_KEY`  | la clé secrète (étape 3)                  |
| `SUPABASE_STORAGE_REGION`             | la région affichée à l'étape 3            |

Sauvegarder → Render redéploie automatiquement le service avec ces variables.
Dès que les 4 premières variables sont présentes, `settings.py` bascule
automatiquement `STORAGES["default"]` vers Supabase — aucun changement de
code nécessaire.

## 5. Vérifier

Après le redéploiement, uploader une image quelque part sur le site (photo de
profil, post, annonce...) et vérifier que son URL pointe bien vers
`https://<project-ref>.supabase.co/storage/v1/object/public/<bucket>/...`
plutôt que vers `/media/...`. Redéployer une seconde fois (ou redémarrer le
service) et confirmer que l'image est toujours accessible — c'est le test qui
valide que le problème de persistance est résolu.

## Notes

- Le tier gratuit de Supabase Storage offre ~1 Go de stockage et ~2 Go de
  bande passante par mois — largement suffisant pour démarrer.
- Les fichiers déjà présents dans `media/` (uploadés avant la bascule) ne
  sont pas migrés automatiquement ; seuls les nouveaux uploads partent vers
  Supabase. Si besoin de migrer l'historique, on pourra écrire un script
  ponctuel plus tard.
- Cette bascule ne touche **que** le stockage des fichiers. La base de
  données reste sur Render Postgres — c'est un sujet séparé, à traiter plus
  tard si besoin.
