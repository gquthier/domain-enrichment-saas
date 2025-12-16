# 🌐 Domain Enrichment SaaS

Plateforme SaaS moderne pour enrichir automatiquement des noms d'entreprises en domaines web vérifiés, utilisant OpenAI GPT-4 et Serper API.

## ✨ Fonctionnalités

- 📤 **Upload de fichiers** CSV/Excel avec drag & drop
- 🎯 **Mapping de colonnes** intelligent avec détection automatique
- 🔍 **Enrichissement intelligent** via recherche web et IA
- ⚡ **Progression en temps réel** avec WebSocket
- 📊 **Score de confiance** pour chaque domaine trouvé
- 🔐 **Vérification des informations légales** (SIREN, SIRET, VAT, KVK)
- 📥 **Export automatique** dans le format d'origine
- 🎨 **Interface moderne et responsive**

## 🚀 Installation Rapide (Docker)

### Prérequis

- Docker et Docker Compose installés
- Clés API :
  - OpenAI API Key (GPT-4)
  - Serper API Key (Google Search)

### Installation

1. **Clonez le repository**

```bash
git clone <votre-repo>
cd name_to_domain
```

2. **Configurez vos clés API**

Le fichier `.env` est déjà configuré avec vos clés. Si besoin, éditez-le :

```bash
# .env est déjà créé avec vos clés
# Vérifiez les valeurs si nécessaire
cat .env
```

3. **Lancez l'application avec Docker**

```bash
# Build et démarrage
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

4. **Accédez à l'application**

Ouvrez votre navigateur : [http://localhost:8000](http://localhost:8000)

### Commandes Docker Utiles

```bash
# Arrêter l'application
docker-compose down

# Rebuild après modifications
docker-compose up -d --build

# Voir les logs
docker-compose logs -f app

# Redémarrer
docker-compose restart
```

## 💻 Installation Manuelle (Sans Docker)

### Prérequis

- Python 3.11+
- pip

### Installation

1. **Créez un environnement virtuel**

```bash
python -m venv venv

# Activation
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

2. **Installez les dépendances**

```bash
pip install -r requirements.txt
```

3. **Configurez les variables d'environnement**

Le fichier `.env` est déjà configuré. Vérifiez qu'il contient :

```env
OPENAI_API_KEY=sk-proj-VzUoMNuY...
SERPER_API_KEY=48c126b7ec5b59a02f5108c89bda63ea799af926
```

4. **Lancez l'application**

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

5. **Accédez à l'application**

Ouvrez [http://localhost:8000](http://localhost:8000)

## 📖 Utilisation

### 1. Upload du fichier

- Glissez-déposez votre fichier CSV/Excel ou cliquez pour parcourir
- Formats supportés : `.csv`, `.xlsx`, `.xls`
- Taille maximale : 50 MB

### 2. Mapping des colonnes

L'application détecte automatiquement :
- La colonne "company name" (obligatoire)
- Les colonnes de contexte (pays, secteur, description, SIREN, etc.)

Ajustez le mapping si nécessaire :
- **Nom de l'entreprise** : Requis
- **Pays** : Améliore la précision de recherche
- **Secteur** : Aide à identifier le bon domaine
- **Description** : Contexte supplémentaire
- **SIREN/SIRET/VAT** : Vérification légale automatique

### 3. Enrichissement

- Le système recherche et vérifie chaque domaine
- Progression en temps réel avec WebSocket
- Vérification des pages légales pour validation

### 4. Téléchargement

Une fois terminé :
- Téléchargez le fichier enrichi (même format que l'original)
- Nouvelles colonnes ajoutées :
  - `URL` : Le domaine trouvé
  - `URL_confidence_score` : Score de confiance (0-100%)

## 🏗️ Architecture

```
name_to_domain/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   └── enrichment_engine.py # Core enrichment logic
├── frontend/
│   ├── index.html           # Interface utilisateur
│   ├── styles.css           # Styles
│   └── app.js               # JavaScript
├── data/
│   ├── uploads/             # Fichiers uploadés
│   └── results/             # Résultats générés
├── requirements.txt         # Dépendances Python
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker compose config
├── .env                    # Variables d'environnement
└── README.md              # Ce fichier
```

## 🔧 Configuration Avancée

### Variables d'environnement

Éditez `.env` pour personnaliser :

```env
# API Keys
OPENAI_API_KEY=your_key
SERPER_API_KEY=your_key

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False

# Storage
UPLOAD_DIR=./data/uploads
RESULTS_DIR=./data/results
MAX_UPLOAD_SIZE=52428800  # 50MB

# Performance
SERP_MAX_RPS=50
SERP_CONCURRENCY=100
OPENAI_CONCURRENCY=24
MAX_CANDIDATES_PER_COMPANY=8
```

### Personnalisation

#### Ajouter de nouveaux champs de contexte

Éditez `backend/enrichment_engine.py` :

```python
CTX_LOCATION = {"country", "pays", "votre_champ", ...}
CTX_SECTOR = {"industry", "sector", "votre_champ", ...}
```

#### Modifier les patterns de recherche

Dans `enrichment_engine.py`, fonction `process_row` :

```python
queries = [
    company + " official website",
    company + " site officiel",
    # Ajoutez vos patterns
]
```

## 🌐 Déploiement en Production

### Option 1 : VPS/Serveur Dédié

1. **Installez Docker**

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

2. **Clonez et lancez**

```bash
git clone <votre-repo>
cd name_to_domain
docker-compose up -d
```

3. **Configurez un reverse proxy (Nginx)**

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Option 2 : Cloud Platform (Heroku, Railway, etc.)

1. Créez un `Procfile` :

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

2. Configurez les variables d'environnement sur la plateforme

3. Déployez via Git

## 🔒 Sécurité

- ✅ Validation des types de fichiers
- ✅ Limite de taille de fichiers
- ✅ CORS configuré
- ✅ Pas de stockage permanent des clés API
- ⚠️ Pour production : ajoutez HTTPS et authentification

## 📊 Performance

- **Throughput** : 50 requêtes/seconde vers Serper API
- **Concurrence** : 100 recherches simultanées
- **OpenAI** : 24 requêtes simultanées
- **Temps de traitement** : ~2-5 secondes par entreprise

## 🐛 Dépannage

### L'application ne démarre pas

```bash
# Vérifiez les logs
docker-compose logs -f

# Vérifiez que les ports ne sont pas déjà utilisés
lsof -i :8000

# Recréez les conteneurs
docker-compose down
docker-compose up -d --build
```

### Erreurs OpenAI

- Vérifiez votre clé API dans `.env`
- Vérifiez votre quota OpenAI
- Vérifiez votre connexion internet

### Erreurs Serper

- Vérifiez votre clé API
- Vérifiez votre quota Serper (100 recherches/mois en gratuit)

### WebSocket ne se connecte pas

- Si derrière un proxy, configurez le support WebSocket
- En développement local, cela devrait fonctionner directement

## 📝 Format des fichiers

### Fichier d'entrée attendu

```csv
company name,country,sector,description
Dassault Systèmes,France,Software,3D design software
Harvest,USA,Agriculture,Farm management
```

### Colonnes optionnelles mais recommandées

- `country` / `pays` : Code pays (FR, US, etc.)
- `sector` / `secteur` : Secteur d'activité
- `description` : Description de l'entreprise
- `siren` / `siret` : Numéros d'identification français
- `vat` : Numéro de TVA européen
- `kvk` : Numéro KVK (Pays-Bas)

## 🤝 Contribution

Les contributions sont bienvenues ! Ouvrez une issue ou un pull request.

## 📄 Licence

Ce projet est sous licence MIT.

## 🙏 Remerciements

- OpenAI pour GPT-4
- Serper pour l'API de recherche Google
- FastAPI pour le framework backend
- La communauté open source

## 📞 Support

Pour toute question ou problème :
1. Consultez la section Dépannage
2. Vérifiez les logs : `docker-compose logs -f`
3. Ouvrez une issue sur GitHub

---

**Note** : Ce projet utilise des API payantes (OpenAI, Serper). Surveillez vos coûts et configurez des limites appropriées.
