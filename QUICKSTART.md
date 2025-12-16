# 🚀 Quick Start Guide

## Démarrage en 3 minutes

### Option 1 : Avec Docker (Recommandé)

```bash
# 1. Vérifiez que Docker est installé
docker --version

# 2. Lancez l'application
docker-compose up -d

# 3. Ouvrez votre navigateur
open http://localhost:8000
```

### Option 2 : Sans Docker

**macOS/Linux :**
```bash
./start.sh
```

**Windows :**
```bash
start.bat
```

### Option 3 : Manuel

```bash
# 1. Créez un environnement virtuel
python -m venv venv
source venv/bin/activate  # macOS/Linux
# ou
venv\Scripts\activate  # Windows

# 2. Installez les dépendances
pip install -r requirements.txt

# 3. Lancez l'application
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📝 Test avec données d'exemple

Un fichier `example_data.csv` est fourni avec 10 entreprises test.

### Étapes :

1. **Ouvrez** http://localhost:8000
2. **Uploadez** `example_data.csv`
3. **Vérifiez** le mapping des colonnes (détecté automatiquement)
4. **Lancez** l'enrichissement
5. **Téléchargez** le résultat enrichi

## 🔑 Clés API Configurées

Vos clés API sont déjà configurées dans `.env` :
- ✅ OpenAI API Key
- ✅ Serper API Key

## 📊 Voir les logs

```bash
# Avec Docker
docker-compose logs -f

# Sans Docker
# Les logs s'affichent directement dans le terminal
```

## 🛑 Arrêter l'application

```bash
# Avec Docker
docker-compose down

# Sans Docker
# Appuyez sur Ctrl+C dans le terminal
```

## ⚙️ Ports utilisés

- **8000** : Application web (interface + API)

Assurez-vous que ce port est disponible.

## 🐛 Problèmes courants

### Port 8000 déjà utilisé

```bash
# Trouvez le processus
lsof -i :8000

# Ou changez le port dans .env
APP_PORT=8080
```

### Erreur de clé API

Vérifiez que vos clés sont correctes dans `.env` :
```bash
cat .env
```

### Docker ne démarre pas

```bash
# Vérifiez Docker
docker ps

# Redémarrez Docker Desktop (macOS/Windows)
# ou le service Docker (Linux)
sudo systemctl restart docker
```

## 📚 Documentation complète

Consultez [README.md](README.md) pour la documentation complète.

## 🎯 Fonctionnalités principales

- ✅ Upload CSV/Excel (drag & drop)
- ✅ Mapping automatique des colonnes
- ✅ Enrichissement intelligent avec IA
- ✅ Progression en temps réel
- ✅ Score de confiance pour chaque domaine
- ✅ Vérification légale (SIREN/SIRET/VAT)
- ✅ Export dans le format d'origine

## 💡 Astuces

1. **Contexte = Précision** : Plus vous fournissez de colonnes de contexte (pays, secteur, description), meilleure sera la précision.

2. **Vérification légale** : Si vous fournissez un SIREN/SIRET/VAT, le système vérifiera automatiquement les pages légales des sites pour confirmation.

3. **Performance** : Le traitement prend environ 2-5 secondes par entreprise. Pour 100 entreprises, comptez 3-8 minutes.

4. **Formats supportés** :
   - CSV (UTF-8, latin-1)
   - Excel (.xlsx, .xls)
   - Taille max : 50 MB

## 🎨 Interface

L'interface est divisée en 4 étapes :

1. **Upload** : Glissez-déposez votre fichier
2. **Mapping** : Vérifiez/ajustez les colonnes
3. **Enrichissement** : Suivez la progression en temps réel
4. **Téléchargement** : Récupérez votre fichier enrichi

---

**Besoin d'aide ?** Consultez [README.md](README.md) ou les logs de l'application.
