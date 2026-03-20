# NutriAI — AI-Powered Diet Planner

Personalised 7-day diet plans powered by Google Gemini AI, based on Harvard Healthy Eating Plate + UK Eatwell Guide.

## 🚀 Deploy to Render (5 minutes)

### Option A — render.yaml (recommended)
1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → **Blueprint**
3. Connect your GitHub repo
4. Render auto-creates the app + PostgreSQL database
5. Set environment variables:
   - `GEMINI_API_KEY` — from [aistudio.google.com](https://aistudio.google.com)
   - `ADMIN_PASSWORD` — choose a strong password
   - `SITE_URL` — your Render URL

### Option B — Manual
1. New Web Service → connect GitHub repo
2. Build: `pip install -r requirements.txt`
3. Start: `gunicorn app:app --workers 2 --timeout 120`
4. Add PostgreSQL database from Render dashboard
5. Set env vars (DATABASE_URL is auto-set)

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key |
| `SECRET_KEY` | ✅ | Auto-generated or set manually |
| `DATABASE_URL` | ✅ | Auto-set by Render PostgreSQL |
| `ADMIN_USERNAME` | optional | Default: `admin` |
| `ADMIN_PASSWORD` | ✅ | Set a strong password |
| `SITE_URL` | optional | For sitemap/OG tags |

## 🛡️ Admin Panel

`/admin/login` — username: `admin`, password: set via `ADMIN_PASSWORD` env var

## ✨ Features

- **13-section health questionnaire** — body, medical, diet, sleep, stress, activity, digestion
- **Strict diet enforcement** — veg/vegan plans safety-validated, AI output rejected if violated
- **Medical-aware plans** — diabetes, PCOS, thyroid, hypertension, cholesterol, and 10 more
- **Food diary** — log meals daily, track calories/macros vs plan target
- **Progress tracking** — weight chart with goal line
- **User accounts** — save and manage multiple health profiles
- **Admin dashboard** — full user data, charts, plan details
- **PostgreSQL + SQLite** — PostgreSQL on Render, SQLite locally
- **SEO ready** — meta tags, OG tags, sitemap.xml, robots.txt
- **PWA** — installable on mobile, keep-alive ping
