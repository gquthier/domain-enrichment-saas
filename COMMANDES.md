# 🚀 Commandes pour Lancer l'Application

## ✅ Commande Principale (STABLE - recommandée)

**Pour utilisation normale (jobs persistants) :**

```bash
cd /Users/gquthier/Desktop/name_to_domain
./venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Pour développement (redémarre automatiquement mais PERD les jobs) :**

```bash
cd /Users/gquthier/Desktop/name_to_domain
./venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

⚠️ **IMPORTANT** : N'utilisez PAS `--reload` pour l'enrichissement ! Les jobs sont perdus à chaque redémarrage.

Cette commande affichera **tous les logs** directement dans votre terminal, y compris :
- 📤 Uploads de fichiers
- 🆔 Génération de job_id
- 💾 Sauvegarde des fichiers
- 📊 Détection des colonnes et comptage des lignes
- 🚀 Démarrage de l'enrichissement
- ⚡ Progression en temps réel
- ✅ Succès et ❌ Erreurs

## 🛑 Arrêter l'Application

Pour arrêter l'application, appuyez sur :
```
Ctrl + C
```

dans le terminal où elle tourne.

## 🔍 Logs Enrichis

L'application affiche maintenant des logs détaillés avec emojis pour faciliter le débogage :

- 📤 **Upload** : Réception de fichiers
- 🆔 **Job ID** : Génération d'identifiant
- 💾 **Sauvegarde** : Écriture sur disque
- 📊 **Analyse** : Détection colonnes et lignes
- ✅ **Succès** : Opération réussie
- ❌ **Erreur** : Problème rencontré
- ⚠️  **Avertissement** : Attention requise
- 🚀 **Enrichissement** : Début du traitement
- 💼 **Job** : Gestion des jobs
- 📋 **Liste** : Jobs disponibles
- 🗺️  **Mapping** : Configuration colonnes
- ⚡ **Tâche** : Exécution background
- 🔍 **Contexte** : Colonnes détectées

## 📱 Accès à l'Interface

Une fois l'application lancée :
```
http://localhost:8000
```

## 🧪 Test avec Données d'Exemple

1. Lancez l'application
2. Ouvrez http://localhost:8000
3. Uploadez `example_data.csv`
4. Suivez les logs dans le terminal !

## 🔧 En Cas de Problème

### Port 8000 déjà utilisé

```bash
# Tuer le processus sur le port 8000
lsof -i :8000
kill -9 <PID>
```

### Environnement virtuel non trouvé

```bash
# Recréer l'environnement
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## 📝 Logs Détaillés

Exemple de logs que vous verrez :

```
INFO - 📤 Upload request received for file: my_companies.csv
INFO - 🆔 Generated job_id: 123e4567-e89b-12d3-a456-426614174000
INFO - 💾 File saved to: data/uploads/123e4567-e89b-12d3-a456-426614174000_my_companies.csv
INFO - 📊 CSV file: 150 rows detected
INFO - ✅ Company column detected: company name
INFO - 🔍 Context columns detected: ['country', 'sector', 'description']
INFO - 💼 Job stored in memory: 123e4567-e89b-12d3-a456-426614174000
INFO - 📋 Current jobs in memory: ['123e4567-e89b-12d3-a456-426614174000']
INFO - ✅ Upload successful for job 123e4567-e89b-12d3-a456-426614174000: 150 rows

INFO - 🚀 Enrichment request received for job_id: 123e4567-e89b-12d3-a456-426614174000
INFO - 🗺️  Column mappings: [...]
INFO - 📦 Job found - Status: uploaded, File: my_companies.csv
INFO - ✅ Job status updated to 'processing'
INFO - ⚡ Background enrichment task started for job 123e4567-e89b-12d3-a456-426614174000
```

## 🎯 Déboguer "Job not found"

Si vous voyez cette erreur, les logs montreront :
```
❌ Job not found: <job_id>
Available jobs: [<liste_des_jobs>]
```

Cela indique que le job_id envoyé par le frontend ne correspond à aucun job en mémoire.

---

**Prêt ?** Lancez la commande et surveillez les logs !
