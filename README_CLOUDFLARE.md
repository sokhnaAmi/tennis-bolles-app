# Déploiement sur Cloudflare Workers + Pages

Ce guide explique comment déployer l'application "Tennis pour les Bollés" sur Cloudflare.

## Architecture

- **Cloudflare Pages** : Sert les fichiers statiques (index.html, admin.html, logo.png)
- **Cloudflare Workers** : Gère toutes les API (backend)

## Prérequis

1. Compte Cloudflare (gratuit)
2. Node.js installé (pour Wrangler CLI)
3. Base de données PostgreSQL Neon (gratuite)

## Installation

### 1. Installer Wrangler CLI

```bash
npm install -g wrangler
```

### 2. Se connecter à Cloudflare

```bash
wrangler login
```

### 3. Installer les dépendances

```bash
npm install
```

## Configuration

### 1. Configurer les variables d'environnement

```bash
# URL de votre base de données Neon PostgreSQL
wrangler secret put DATABASE_URL

# Mot de passe admin par défaut (optionnel)
wrangler secret put ADMIN_SECRET
```

Quand vous exécutez ces commandes, Wrangler vous demandera de saisir les valeurs.

### 2. Bootstrap de la base de données

Avant de déployer, initialisez votre base de données :

```bash
# Définir DATABASE_URL localement
export DATABASE_URL="postgresql://user:password@host/database"

# Exécuter le script de bootstrap
npm run bootstrap
```

Cela va :
- Créer les tables nécessaires
- Importer les données depuis `data.json`
- Initialiser le mot de passe admin

## Déploiement

### 1. Déployer le Worker (API)

```bash
npm run deploy
```

Cela déploie le Worker sur Cloudflare. Notez l'URL du Worker (ex: `tennis-bolles.workers.dev`).

### 2. Déployer les fichiers statiques (Pages)

#### Option A : Via l'interface Cloudflare

1. Allez sur [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Sélectionnez "Pages" dans le menu
3. Cliquez sur "Create a project"
4. Connectez votre dépôt GitHub
5. Configurez :
   - **Build command** : (laisser vide)
   - **Build output directory** : `/` (racine)
6. Dans "Functions", ajoutez le Worker que vous avez créé

#### Option B : Via Wrangler (Pages)

```bash
# Déployer les fichiers statiques
wrangler pages deploy . --project-name=tennis-bolles
```

### 3. Configurer les routes Pages → Worker

Dans Cloudflare Pages, configurez les routes pour rediriger les API vers le Worker :

1. Allez dans votre projet Pages
2. Settings → Functions
3. Ajoutez le Worker comme "Function"
4. Configurez les routes :
   - `/api/*` → Worker
   - `/public-data` → Worker
   - Tout le reste → Pages (fichiers statiques)

## Structure des fichiers

```
.
├── src/
│   ├── index.js          # Worker principal (router)
│   ├── db.js             # Fonctions de base de données
│   ├── auth.js           # Fonctions d'authentification
│   └── routes/
│       └── api.js        # Routes API
├── scripts/
│   └── bootstrap.js     # Script d'initialisation DB
├── index.html            # Page principale (joueurs)
├── admin.html            # Page admin
├── logo.png             # Logo
├── data.json            # Données initiales
├── package.json         # Dépendances Node.js
├── wrangler.toml        # Configuration Cloudflare
└── README_CLOUDFLARE.md # Ce fichier
```

## Endpoints API

- `GET /api/ping` - Vérification auth
- `GET /api/data` - Données admin (requiert auth)
- `PUT /api/data` - Enregistrement (requiert auth)
- `POST /api/change-password` - Changement mot de passe (requiert auth)
- `GET /public-data` - Données publiques (sans auth)

## Développement local

Pour tester localement :

```bash
# Démarrer le Worker en mode développement
npm run dev
```

Cela démarre un serveur local sur `http://localhost:8787`.

## Notes importantes

1. **Fichiers statiques** : Les fichiers HTML doivent être servis par Cloudflare Pages, pas par le Worker
2. **Base de données** : Utilisez Neon PostgreSQL (gratuit et compatible Workers)
3. **Variables d'environnement** : Utilisez `wrangler secret put` pour les secrets
4. **Bootstrap** : Exécutez le script de bootstrap une seule fois pour initialiser la DB

## Dépannage

### Le Worker ne se connecte pas à la base de données

- Vérifiez que `DATABASE_URL` est correctement configuré
- Assurez-vous que Neon autorise les connexions depuis Cloudflare
- Vérifiez les logs : `wrangler tail`

### Les fichiers statiques ne se chargent pas

- Assurez-vous que les fichiers sont déployés sur Cloudflare Pages
- Vérifiez que les routes sont correctement configurées
- Les fichiers doivent être dans la racine du projet

### Erreur 401 sur les API

- Vérifiez que le header `X-Admin-Key` est présent
- Vérifiez que le mot de passe admin est correct
- Le mot de passe par défaut est `change-me-please` si non configuré

## Support

Pour plus d'aide, consultez :
- [Documentation Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [Documentation Cloudflare Pages](https://developers.cloudflare.com/pages/)
- [Documentation Neon](https://neon.tech/docs)


