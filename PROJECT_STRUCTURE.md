# 📁 Structure du Projet

## Vue d'ensemble

```
name_to_domain/
├── backend/                    # Backend FastAPI
│   ├── __init__.py
│   ├── main.py                # 🚀 API principale et endpoints
│   ├── config.py              # ⚙️ Configuration et variables d'env
│   └── enrichment_engine.py   # 🧠 Logique d'enrichissement
│
├── frontend/                   # Frontend (HTML/CSS/JS)
│   ├── index.html             # 📄 Interface utilisateur
│   ├── styles.css             # 🎨 Styles et design
│   └── app.js                 # ⚡ Logique frontend et WebSocket
│
├── data/                       # Données (créé automatiquement)
│   ├── uploads/               # 📤 Fichiers uploadés
│   └── results/               # 📥 Fichiers enrichis
│
├── requirements.txt            # 📦 Dépendances Python
├── Dockerfile                  # 🐳 Image Docker
├── docker-compose.yml          # 🐳 Configuration Docker Compose
├── .dockerignore              # 🐳 Exclusions Docker
│
├── .env                        # 🔑 Variables d'environnement (vos clés API)
├── .env.example               # 📝 Template de .env
├── .gitignore                 # 📝 Exclusions Git
│
├── start.sh                   # 🚀 Script de démarrage (macOS/Linux)
├── start.bat                  # 🚀 Script de démarrage (Windows)
│
├── README.md                  # 📚 Documentation complète
├── QUICKSTART.md              # ⚡ Guide de démarrage rapide
├── PROJECT_STRUCTURE.md       # 📁 Ce fichier
│
└── example_data.csv           # 📊 Données d'exemple pour test
```

## 📋 Description des fichiers principaux

### Backend

#### `backend/main.py`
**Rôle** : API principale FastAPI

**Endpoints** :
- `POST /api/upload` : Upload de fichier CSV/Excel
- `POST /api/enrich` : Démarrage de l'enrichissement
- `GET /api/status/{job_id}` : Statut d'un job
- `GET /api/download/{job_id}` : Téléchargement du résultat
- `WS /ws/{job_id}` : WebSocket pour progression en temps réel
- `GET /api/jobs` : Liste de tous les jobs
- `DELETE /api/jobs/{job_id}` : Suppression d'un job

**Fonctionnalités** :
- Gestion des uploads de fichiers
- Détection automatique des colonnes
- Job queue en mémoire
- WebSocket pour temps réel
- Serve le frontend statique

#### `backend/config.py`
**Rôle** : Configuration centralisée

**Contenu** :
- Chargement des variables d'environnement
- Configuration des API (OpenAI, Serper)
- Paramètres de performance (RPS, concurrence)
- Chemins de fichiers

#### `backend/enrichment_engine.py`
**Rôle** : Cœur de la logique d'enrichissement

**Composants principaux** :

1. **Helpers** :
   - Tokenization des domaines et noms
   - Calcul de similarité (Levenshtein)
   - Détection de contexte
   - Score de confiance

2. **Recherche Web** :
   - `serper_search()` : Recherche via Serper API
   - Rate limiting (50 RPS)
   - Filtrage des résultats

3. **OpenAI** :
   - `openai_choose()` : Sélection du bon domaine via GPT-4
   - Prompts optimisés
   - Gestion des erreurs et retry

4. **Vérification légale** :
   - Crawling des pages légales
   - Extraction SIREN/SIRET/VAT/KVK
   - Validation Luhn (SIREN/SIRET)

5. **Enrichissement** :
   - `EnrichmentEngine` : Classe principale
   - Traitement asynchrone
   - Callback de progression
   - Checkpointing

### Frontend

#### `frontend/index.html`
**Sections** :
1. Upload : Drag & drop de fichiers
2. Mapping : Configuration des colonnes
3. Processing : Barre de progression
4. Complete : Téléchargement du résultat
5. Error : Gestion des erreurs

#### `frontend/styles.css`
**Caractéristiques** :
- Design moderne et épuré
- Variables CSS pour personnalisation
- Responsive (mobile-friendly)
- Animations fluides
- Système de toast notifications

#### `frontend/app.js`
**Fonctionnalités** :
- Gestion de l'état de l'application
- Upload de fichiers (drag & drop)
- Communication API
- WebSocket pour temps réel
- Transitions entre sections
- Notifications toast

### Configuration

#### `.env`
**Variables principales** :
```env
OPENAI_API_KEY=...           # Clé API OpenAI
SERPER_API_KEY=...           # Clé API Serper
APP_PORT=8000                # Port de l'application
SERP_MAX_RPS=50              # Limite de requêtes/seconde
OPENAI_CONCURRENCY=24        # Requêtes OpenAI simultanées
```

### Docker

#### `Dockerfile`
**Étapes** :
1. Base image : Python 3.11-slim
2. Installation des dépendances système
3. Installation des packages Python
4. Copie du code
5. Création des dossiers data
6. Healthcheck
7. Lancement de l'application

#### `docker-compose.yml`
**Services** :
- `app` : Application principale
  - Port : 8000
  - Volumes : data/uploads, data/results
  - Environment : Variables API

## 🔄 Flux de données

### 1. Upload
```
User → Frontend → POST /api/upload → Backend
                                    ↓
                            Sauvegarde fichier
                                    ↓
                            Détection colonnes
                                    ↓
                            ← job_id + colonnes
```

### 2. Mapping
```
User configure → Frontend (JavaScript)
```

### 3. Enrichissement
```
Frontend → POST /api/enrich → Backend
                                ↓
                        Démarrage async job
                                ↓
                        ← job_id + status
                                ↓
                    WebSocket connection
                                ↓
        ┌───────────────────────┴────────────────────┐
        ↓                                             ↓
EnrichmentEngine                            WebSocket updates
        ↓                                             ↓
Pour chaque entreprise:                          Frontend
    1. SERP Search (Serper)                    (mise à jour UI)
    2. OpenAI GPT-4 (choix domaine)
    3. Legal crawl (si SIREN/VAT)
    4. Calcul score confiance
    5. Callback progression → WebSocket
        ↓
Sauvegarde résultat
        ↓
Notification completion
```

### 4. Téléchargement
```
User → Frontend → GET /api/download/{job_id} → Backend
                                                    ↓
                                            Lecture fichier
                                                    ↓
                                            ← Fichier enrichi
```

## 🧩 Composants clés

### Rate Limiting (RPSLimiter)
- Token bucket algorithm
- 50 requêtes/seconde vers Serper
- Évite les dépassements de quota

### WebSocket Manager
- Connexions par job_id
- Mises à jour en temps réel
- Fallback sur polling si WS échoue

### Column Detection
- Recherche fuzzy dans les noms de colonnes
- Priorité : "company name" obligatoire
- Contexte : pays, secteur, description, IDs légaux

### Confidence Scoring
- Base : type de domaine (entity=95, country=78, group=65)
- Pénalités : ambiguïté, contexte manquant
- Bonus : contexte présent, vérification légale
- Score final : 1-100%

## 🔧 Points d'extension

### Ajouter une nouvelle API de recherche
Éditez `enrichment_engine.py` :
```python
async def nouvelle_api_search(...):
    # Votre implémentation
    pass
```

### Ajouter un champ de contexte
Éditez `enrichment_engine.py` :
```python
CTX_VOTRE_CATEGORIE = {"votre_champ", "autre_champ"}
```

### Personnaliser le scoring
Éditez la fonction `process_row()` dans `enrichment_engine.py`

### Ajouter une page frontend
1. Créez le HTML dans `index.html`
2. Ajoutez les styles dans `styles.css`
3. Gérez la logique dans `app.js`

## 📊 Performance

### Goulots d'étranglement
1. **Serper API** : 50 RPS max
2. **OpenAI API** : 24 requêtes simultanées
3. **Legal crawl** : ~5-10s par domaine (optionnel)

### Optimisations
- Caching des recherches SERP
- Caching des réponses LLM
- Traitement parallèle (asyncio)
- Checkpointing pour reprise

## 🔒 Sécurité

### Implémenté
- ✅ Validation de type de fichier
- ✅ Limite de taille (50MB)
- ✅ CORS configuré
- ✅ Pas de stockage des clés dans le code

### À ajouter pour production
- 🔲 HTTPS/SSL
- 🔲 Authentification utilisateur
- 🔲 Rate limiting par utilisateur
- 🔲 Validation plus stricte des inputs
- 🔲 Logging et monitoring
- 🔲 Backup des données

---

**Questions ?** Consultez [README.md](README.md) ou [QUICKSTART.md](QUICKSTART.md)
