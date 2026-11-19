# AFARM on AWS EC2 — `afarm.khulega.online`

One-time setup below. After that, **each release is only**:

```bash
git push origin main
```

GitHub Actions SSHs into the server, `git pull`, reinstall deps if needed, restart (frontend also rebuilds).

## Layout (does not touch other sites)

```text
/srv/afarm/
  afarm-backend/    ← GitHub: afarm-backend
  afarm-frontend/   ← GitHub: afarm-frontend
```

Ports: **8100** (API), **3100** (Next.js) — only nginx is public.

DNS: see **[route53-afarm.md](./route53-afarm.md)** — `afarm.khulega.online` + `api.afarm.khulega.online` → EC2 IP.

---

## One-time setup

### 0. On khulega-online (you are SSH’d in)

After first clone: `bash /srv/afarm/afarm-backend/deploy/aws/preflight.sh` (checks RAM, nginx, node, existing ports).

Amazon Linux 2023 packages (if something is missing):

```bash
sudo dnf install -y git python3.11 python3.11-pip postgresql15-server postgresql15 nginx
# Node 18+ (use nvm or nodesource if dnf node is too old):
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo dnf install -y nodejs
```

Instance details: **[INSTANCE-khulega-online.md](./INSTANCE-khulega-online.md)**.

### 1. Route 53

A records for `afarm.khulega.online` and `api.afarm.khulega.online` → your EC2 IP.

### 2. Clone repos on EC2

```bash
sudo mkdir -p /srv/afarm && sudo chown $USER:$USER /srv/afarm
cd /srv/afarm
git clone git@github.com:YOUR_USER/afarm-backend.git afarm-backend
git clone git@github.com:YOUR_USER/afarm-frontend.git afarm-frontend
chmod +x afarm-backend/deploy/aws/deploy-backend.sh
chmod +x afarm-frontend/deploy/aws/deploy-frontend.sh
```

Use SSH deploy keys or HTTPS + PAT so the server can `git fetch` (same keys as GitHub Actions user is fine).

### 3. PostgreSQL (database `afarm` only)

```bash
sudo -u postgres psql -f /srv/afarm/afarm-backend/deploy/aws/create-afarm-db.sql
# edit passwords in the file first
```

```bash
cd /srv/afarm/afarm-backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.production.example .env
nano .env   # passwords, JWT, Shiprocket, etc.
python scripts/init_db.py
```

### 4. Frontend env (stays on server; never in git)

```bash
cd /srv/afarm/afarm-frontend
cp .env.production.example .env.production
nano .env.production
npm ci && npm run build
```

### 5. systemd

```bash
sudo cp /srv/afarm/afarm-backend/deploy/aws/systemd-afarm-backend.service.example /etc/systemd/system/afarm-backend.service
sudo cp /srv/afarm/afarm-backend/deploy/aws/systemd-afarm-frontend.service.example /etc/systemd/system/afarm-frontend.service
# Edit User= and paths if not ubuntu / /srv/afarm
sudo systemctl daemon-reload
sudo systemctl enable --now afarm-backend afarm-frontend
```

### 6. Passwordless restart for deploy user (required for GitHub Actions)

```bash
sudo visudo -f /etc/sudoers.d/afarm-deploy
```

```text
ec2-user ALL=(ALL) NOPASSWD: /bin/systemctl restart afarm-backend, /bin/systemctl restart afarm-frontend
```

On **khulega-online** use **`ec2-user`** (see `INSTANCE-khulega-online.md`).

### 7. Nginx + SSL

```bash
sudo cp /srv/afarm/afarm-backend/deploy/aws/nginx-afarm.conf.example /etc/nginx/sites-available/afarm
sudo ln -sf /etc/nginx/sites-available/afarm /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d afarm.khulega.online -d api.afarm.khulega.online
```

### 8. GitHub Actions (both repos)

In **afarm-backend** and **afarm-frontend** → Settings → Secrets and variables → Actions:

| Secret | Value |
|--------|--------|
| `SSH_HOST` | EC2 public IP or hostname |
| `SSH_USER` | `ec2-user` on khulega-online |
| `SSH_PRIVATE_KEY` | Private key for that user (full PEM, including `BEGIN` lines) |
| `SSH_PORT` | Optional; omit if 22 |

Add the matching **public** key to `~/.ssh/authorized_keys` on the EC2.

Workflows: `.github/workflows/deploy.yml` in each repo (already in the codebase).

---

## Day-to-day deploy

| Change | Command |
|--------|---------|
| Backend | `git push origin main` → Actions runs `deploy/aws/deploy-backend.sh` |
| Frontend | `git push origin main` → pull, `npm ci`, `npm run build`, restart |

`.env` / `.env.production` on the server are **not** overwritten by git.

### Manual deploy (optional)

```bash
ssh ec2-user@13.207.119.202 'cd /srv/afarm/afarm-backend && bash deploy/aws/deploy-backend.sh'
ssh ec2-user@13.207.119.202 'cd /srv/afarm/afarm-frontend && bash deploy/aws/deploy-frontend.sh'
```

---

## Uploads (local disk)

Product/category/banner images are stored under `afarm-backend/uploads/` (WebP-compressed).  
They are served at `https://api.afarm.khulega.online/uploads/...`. Back up this folder with your deploy routine — it is not in git.

---

## Checklist

- [ ] Route 53 A records
- [ ] DB `afarm` + backend `.env` + `init_db.py`
- [ ] Frontend `.env.production` + first build
- [ ] systemd + nginx + certbot
- [ ] GitHub secrets on **both** repos
- [ ] Test push to `main`