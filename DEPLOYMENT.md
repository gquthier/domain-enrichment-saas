# 🚀 Guide de Déploiement en Production

Ce guide vous aidera à déployer l'application Domain Enrichment SaaS en production.

## 📋 Table des Matières

1. [Prérequis](#prérequis)
2. [Options de Déploiement](#options-de-déploiement)
3. [Déploiement avec Docker](#déploiement-avec-docker)
4. [Déploiement sur Cloud](#déploiement-sur-cloud)
5. [Configuration de Production](#configuration-de-production)
6. [Monitoring et Logs](#monitoring-et-logs)
7. [Sécurité](#sécurité)

---

## Prérequis

### Obligatoire
- **Python 3.11+** ou **Docker**
- **Clés API**:
  - [OpenAI API Key](https://platform.openai.com/api-keys) (GPT-4)
  - [Serper API Key](https://serper.dev/) (Google Search)
- **Domaine** avec DNS configuré (recommandé)
- **Certificat SSL** (Let's Encrypt recommandé)

### Optionnel
- **Redis** pour persistance des jobs (sinon en mémoire)
- **Reverse proxy** (Nginx, Caddy)

---

## Options de Déploiement

### 1. 🐳 Docker (Recommandé)
- Simple et rapide
- Isolation complète
- Portable

### 2. ☁️ Cloud Platforms
- **Railway**: Déploiement en 1 clic
- **Render**: Free tier disponible
- **Fly.io**: Edge deployment
- **AWS/GCP/Azure**: Pour grande échelle

### 3. 🖥️ VPS/Serveur Dédié
- DigitalOcean, Linode, Hetzner
- Contrôle total

---

## Déploiement avec Docker

### 1. Cloner le Repository

```bash
git clone https://github.com/votre-username/name-to-domain.git
cd name-to-domain
```

### 2. Configurer les Variables d'Environnement

```bash
cp .env.example .env
nano .env  # Éditer avec vos clés API
```

Mettez à jour :
```env
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...
DEBUG=False
```

### 3. Build et Lancement

```bash
# Build l'image
docker-compose build

# Lancer en production
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

### 4. Accéder à l'Application

```
http://votre-serveur-ip:8000
```

### 5. Configuration Nginx (Optionnel)

```nginx
server {
    listen 80;
    server_name votre-domaine.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Puis :
```bash
# Installer certbot pour SSL
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d votre-domaine.com
```

---

## Déploiement sur Railway

### 1. Créer un Compte
Allez sur [railway.app](https://railway.app)

### 2. Nouveau Projet
```bash
# Installer Railway CLI
npm install -g @railway/cli

# Login
railway login

# Déployer
railway init
railway up
```

### 3. Configurer les Variables
Dans le dashboard Railway :
- `OPENAI_API_KEY`
- `SERPER_API_KEY`
- `APP_PORT=8000`

### 4. Domaine Personnalisé
Settings → Domains → Add Custom Domain

---

## Déploiement sur Render

### 1. Créer `render.yaml`

```yaml
services:
  - type: web
    name: domain-enrichment
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: OPENAI_API_KEY
        sync: false
      - key: SERPER_API_KEY
        sync: false
      - key: DEBUG
        value: False
```

### 2. Connecter le Repo GitHub

1. Allez sur [render.com](https://render.com)
2. New → Web Service
3. Connectez votre repo GitHub
4. Configurez les variables d'environnement

---

## Configuration de Production

### 1. Sécurité

**Désactiver le mode Debug**
```env
DEBUG=False
```

**Limiter les uploads**
```env
MAX_UPLOAD_SIZE=52428800  # 50MB
```

**Rate Limiting** (à implémenter)
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)
```

### 2. Persistance des Jobs

**Option A: Redis (Recommandé)**
```bash
# Installer Redis
docker run -d -p 6379:6379 redis:alpine

# Mettre à jour .env
REDIS_HOST=localhost
```

**Option B: Base de données**
- Implémenter une couche de persistance avec PostgreSQL

### 3. Performances

**Ajuster les limites**
```env
SERP_MAX_RPS=50           # Requêtes Serper par seconde
OPENAI_CONCURRENCY=24     # Requêtes OpenAI simultanées
SERP_CONCURRENCY=100      # Requêtes Serper simultanées
```

---

## Monitoring et Logs

### 1. Logs Docker

```bash
# Voir tous les logs
docker-compose logs -f

# Logs de l'API uniquement
docker-compose logs -f api

# Dernières 100 lignes
docker-compose logs --tail=100
```

### 2. Monitoring avec Prometheus + Grafana

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### 3. Alertes par Email

Configuration SMTP dans `.env` :
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=votre-email@gmail.com
SMTP_PASSWORD=votre-mot-de-passe
ADMIN_EMAIL=admin@votre-domaine.com
```

---

## Sécurité

### 1. HTTPS Obligatoire

**Avec Let's Encrypt**
```bash
sudo certbot --nginx -d votre-domaine.com
```

### 2. Firewall

```bash
# Autoriser seulement HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

### 3. Authentification (À Implémenter)

Ajoutez un système d'authentification :
- OAuth2
- JWT tokens
- API Keys par utilisateur

### 4. CORS Restrictif

Dans `backend/main.py` :
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://votre-domaine.com"],  # Pas "*"
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## Maintenance

### Backup

```bash
# Backup des données
docker-compose exec api tar -czf /backup/data.tar.gz /app/data

# Backup de la base de données (si Redis)
docker-compose exec redis redis-cli SAVE
```

### Mise à Jour

```bash
# Pull nouvelle version
git pull origin main

# Rebuild
docker-compose build

# Redémarrer sans downtime
docker-compose up -d --no-deps api
```

### Logs Rotation

```bash
# Configurer logrotate
sudo nano /etc/logrotate.d/domain-enrichment
```

```
/var/log/domain-enrichment/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```

---

## Troubleshooting

### Port déjà utilisé
```bash
lsof -i :8000
kill -9 <PID>
```

### Mémoire insuffisante
```bash
# Augmenter la limite Docker
docker-compose up -d --memory=2g
```

### Jobs perdus au redémarrage
- Implémenter Redis pour la persistance
- Ou utiliser une base de données

---

## Support

- **Issues**: [GitHub Issues](https://github.com/votre-username/name-to-domain/issues)
- **Documentation**: [README.md](README.md)
- **Contact**: votre-email@example.com

---

## Checklist de Production

- [ ] Variables d'environnement configurées
- [ ] `DEBUG=False`
- [ ] HTTPS activé (certificat SSL)
- [ ] Firewall configuré
- [ ] Monitoring en place
- [ ] Backups automatisés
- [ ] Logs rotation configurée
- [ ] Rate limiting activé
- [ ] CORS restrictif
- [ ] Domaine personnalisé configuré

---

**Prêt pour la production !** 🎉
