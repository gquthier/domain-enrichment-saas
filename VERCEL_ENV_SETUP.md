# 🔐 Configuration des Variables d'Environnement Vercel

## Méthode 1 : Via le Dashboard Vercel (Recommandé)

1. Allez sur votre projet Vercel
2. Cliquez sur **Settings** → **Environment Variables**
3. Ajoutez ces variables **une par une** :

### Variables à ajouter :

| Variable Name | Value | Environments |
|--------------|-------|--------------|
| `OPENAI_API_KEY` | `votre_clé_openai` | ✅ Production, ✅ Preview, ✅ Development |
| `SERPER_API_KEY` | `votre_clé_serper` | ✅ Production, ✅ Preview, ✅ Development |
| `APP_HOST` | `0.0.0.0` | ✅ Production, ✅ Preview, ✅ Development |
| `APP_PORT` | `8000` | ✅ Production, ✅ Preview, ✅ Development |
| `DEBUG` | `False` | ✅ Production, ✅ Preview, ✅ Development |

⚠️ **IMPORTANT** : Cochez TOUS les environnements pour chaque variable !

---

## Méthode 2 : Via Vercel CLI

Si vous avez Vercel CLI installé :

\`\`\`bash
# Installer Vercel CLI
npm i -g vercel

# Se connecter
vercel login

# Lier le projet
vercel link

# Ajouter les variables (une par une)
vercel env add OPENAI_API_KEY production preview development
vercel env add SERPER_API_KEY production preview development
vercel env add APP_HOST production preview development
vercel env add APP_PORT production preview development
vercel env add DEBUG production preview development
\`\`\`

---

## Méthode 3 : Import en Bloc (Copier-Coller)

Lors de la configuration initiale sur Vercel, vous pouvez copier-coller tout le contenu du fichier `.env.production` :

```
OPENAI_API_KEY=votre_clé_openai
SERPER_API_KEY=votre_clé_serper
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
```

---

## ✅ Vérification

Après avoir ajouté les variables :

1. Allez dans **Settings** → **Environment Variables**
2. Vous devriez voir 5 variables avec 3 environnements chacune
3. Cliquez sur **Redeploy** pour appliquer les changements

---

## 🔒 Sécurité

⚠️ **NE COMMITTEZ JAMAIS** les fichiers suivants :
- `.env`
- `.env.production`
- `.env.local`

Ces fichiers sont déjà dans le `.gitignore`.

---

## 📞 Support

Si les variables ne sont pas détectées après le déploiement :
1. Vérifiez qu'elles sont bien dans tous les environnements
2. Redéployez manuellement depuis le Dashboard
3. Consultez les logs de build dans Vercel
