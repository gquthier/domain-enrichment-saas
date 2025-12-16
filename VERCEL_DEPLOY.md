# 🚀 Guide de Déploiement Vercel - Simplifié

## ⚠️ IMPORTANT: Limitations Vercel

Cette application peut rencontrer des problèmes sur Vercel à cause de:
- **Timeouts**: Les enrichissements longs peuvent dépasser les 60 secondes
- **Stockage**: Vercel n'a pas de stockage persistant (fichiers perdus après chaque requête)
- Voir `VERCEL_NOTES.md` pour des alternatives comme Railway ou Render

## 📋 Prérequis

1. Compte GitHub
2. Compte Vercel (gratuit)
3. Clés API:
   - OpenAI API Key
   - Serper API Key

## 🔧 Étapes de Déploiement

### 1. Push vers GitHub

```bash
git add .
git commit -m "Préparation pour déploiement Vercel"
git push origin main
```

### 2. Importer sur Vercel

1. Allez sur [vercel.com](https://vercel.com)
2. Cliquez sur **"New Project"**
3. Importez votre repository `domain-enrichment-saas`
4. Vercel détectera automatiquement la configuration

### 3. Configurer les Variables d'Environnement

Dans le dashboard Vercel, avant de déployer:

1. Allez dans **Settings** → **Environment Variables**
2. Ajoutez ces variables:

| Variable | Valeur | Environnement |
|----------|--------|---------------|
| `OPENAI_API_KEY` | `votre_clé_openai` | Production, Preview, Development |
| `SERPER_API_KEY` | `votre_clé_serper` | Production, Preview, Development |

⚠️ **IMPORTANT**: Cochez tous les environnements (Production, Preview, Development)

### 4. Déployer

Cliquez sur **"Deploy"** - Vercel va:
- Installer les dépendances Python
- Déployer l'API via `api/index.py`
- Exposer l'application

## 🧪 Tester le Déploiement

Une fois déployé, testez avec:

```bash
curl https://votre-app.vercel.app/health
```

Devrait retourner: `{"status": "ok"}`

## 🐛 Résolution des Problèmes

### Erreur: "Secret does not exist"

✅ **RÉSOLU** - Le fichier `vercel.json` a été corrigé pour ne plus utiliser `@openai_api_key`

Maintenant, ajoutez simplement les variables dans le Dashboard Vercel.

### Timeout Error (508)

Limitez la taille des fichiers:
- Maximum 10-20 domaines par fichier
- Vercel a un timeout de 60 secondes max

### Module Import Error

Vérifiez que `requirements.txt` est à la racine du projet.

## 📦 Structure des Fichiers pour Vercel

```
domain-enrichment-saas/
├── api/
│   └── index.py          # Point d'entrée Vercel
├── backend/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   └── enrichment_engine.py
├── requirements.txt       # Dépendances Python
├── vercel.json           # Config Vercel
└── .env.example          # Template des variables
```

## 🔄 Déploiements Automatiques

Chaque push sur `main` déclenchera automatiquement un nouveau déploiement sur Vercel.

## 💡 Alternative Recommandée

Si vous rencontrez des problèmes de timeout ou de stockage, considérez:

1. **Railway** - Meilleur pour cette application
2. **Render** - Excellent free tier
3. Voir `VERCEL_NOTES.md` pour plus de détails

## 📞 Support

Pour des questions, consultez:
- [Documentation Vercel Python](https://vercel.com/docs/functions/serverless-functions/runtimes/python)
- `VERCEL_NOTES.md` pour les limitations
- `DEPLOYMENT.md` pour d'autres options
