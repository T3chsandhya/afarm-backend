# AFARM API (backend)

FastAPI + PostgreSQL ecommerce API for AFARM.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/init_db.py
uvicorn app.main:app --reload --port 8000
```

## Environment

| File | Purpose |
|------|---------|
| `.env.example` | Local development template |
| `.env.production.example` | AWS / production template — copy to `.env` on the server |
| `.env` | **Gitignored** — your real secrets |

## AWS — `afarm.khulega.online`

One-time: **[deploy/aws/README.md](deploy/aws/README.md)**  
Ongoing: **`git push origin main`** → GitHub Actions deploys to EC2.

## GitHub

Push **this folder only** as the `afarm-backend` repository (not the parent `AFARM` monorepo root).