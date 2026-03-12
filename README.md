# 🥗 NutriAI — AI-Powered Diet Planner & Health Analysis Platform

A production-ready MVP web application that analyzes a user's health, lifestyle, and daily habits to generate a personalized diet plan using scientific formulas and AI.

---

## ✨ Features

- **10-Section Health Questionnaire** — Covers personal info, goals, diet preference, meal habits, activity, sleep, stress, work schedule, meal timing, and hydration
- **Scientific Health Metrics** — Auto-calculates BMI, BMR (Mifflin-St Jeor), TDEE, and goal-adjusted daily calories
- **AI Diet Plan Generation** — Uses Google Gemini or OpenAI GPT to create a personalized 7-day Indian meal plan with macros
- **Health Score Analysis** — Evaluates 8+ lifestyle factors and provides insights and warnings
- **Progress Dashboard** — Track weight over time with Chart.js visualizations
- **Mobile-First Design** — Beautiful, responsive UI with botanical emerald aesthetic
- **Graceful Fallback** — Works without API keys using a built-in fallback diet plan

---

## 🗂️ Project Structure

```
project-root/
├── app.py                  # Main Flask application
├── config.py               # Configuration & environment variables
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── README.md               # This file
│
├── models/
│   ├── user_model.py       # User database operations
│   ├── diet_plan_model.py  # Diet plan database operations
│   └── progress_model.py   # Progress tracking operations
│
├── services/
│   ├── diet_calculator.py  # BMI, BMR, TDEE calculations
│   ├── ai_diet_generator.py # AI diet plan generation (Gemini/OpenAI)
│   └── health_analyzer.py  # Health score and insights
│
├── templates/
│   ├── base.html           # Base template with nav/footer
│   ├── index.html          # Landing page
│   ├── questionnaire.html  # Multi-step questionnaire form
│   ├── results.html        # Personalized results page
│   └── dashboard.html      # Progress tracking dashboard
│
├── static/
│   ├── css/style.css       # Complete custom stylesheet
│   ├── js/script.js        # Frontend JavaScript
│   └── images/             # Image assets
│
└── database/
    └── health_diet_app.db  # SQLite database (auto-created)
```

---

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo-url>
cd ai-diet-planner

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run the Application

```bash
python app.py
```

Visit `http://localhost:5000`

---

## 🔑 API Key Setup

### Google Gemini (Recommended — Free Tier Available)
1. Go to https://makersuite.google.com/app/apikey
2. Create a new API key
3. Add to `.env`: `GEMINI_API_KEY=your-key-here`
4. Set `AI_PROVIDER=gemini`

### OpenAI (Alternative)
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Add to `.env`: `OPENAI_API_KEY=your-key-here`
4. Set `AI_PROVIDER=openai`

> **No API key?** The app works without one using a built-in fallback diet plan.

---

## 🧮 Health Calculations

| Formula | Description |
|---------|-------------|
| **BMI** | `weight / (height_m)²` |
| **BMR (Male)** | `10×weight + 6.25×height − 5×age + 5` |
| **BMR (Female)** | `10×weight + 6.25×height − 5×age − 161` |
| **TDEE** | `BMR × activity multiplier (1.2–1.9)` |
| **Weight Loss** | `TDEE − 500 kcal` |
| **Muscle Gain** | `TDEE + 300 kcal` |
| **Maintenance** | `TDEE` |

---

## 🗄️ Database Schema

### `users` table
Stores all questionnaire responses and user profile data.

### `diet_plans` table
Stores calculated metrics and AI-generated meal plan JSON.

### `progress` table
Stores weight entries over time for progress tracking.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/questionnaire` | Questionnaire form |
| `POST` | `/analyze` | Process form & generate plan |
| `GET` | `/results/<user_id>/<plan_id>` | Results page |
| `GET` | `/dashboard/<user_id>` | Progress dashboard |
| `POST` | `/api/progress/add` | Log weight entry |
| `POST` | `/api/bmi-check` | Quick BMI calculation |

---

## 🌐 Deployment

### Render (Recommended)

1. Push code to GitHub
2. Create new Web Service on render.com
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Add environment variables in Render dashboard
6. Deploy!

### Railway

```bash
railway init
railway up
```
Add environment variables in Railway dashboard.

### AWS (EC2)

```bash
sudo apt update && sudo apt install python3-pip nginx -y
pip install -r requirements.txt
gunicorn -w 4 -b 0.0.0.0:8000 app:app
# Configure nginx as reverse proxy
```

---

## 🛡️ Security Features

- Environment variables for all API keys
- SQLite parameterized queries (SQL injection protection)
- Input validation on all form fields
- Secret key for Flask sessions
- No sensitive data logged

---

## 🔧 Optional Advanced Features

To implement these features, extend the respective service files:

- 📸 **Food Photo Calorie Detection** — Use Gemini Vision API in `ai_diet_generator.py`
- 🛒 **AI Grocery List Generator** — Add `/api/grocery-list` endpoint
- 💧 **Daily Water Tracker** — Add `water_log` table and dashboard widget
- 👣 **Step Goal Tracker** — Add `step_log` table and Chart.js graph
- 🔄 **Meal Replacement Suggestions** — Add swap button on meal cards

---

## 📦 Tech Stack

- **Backend**: Python, Flask 3.0
- **Frontend**: HTML5, CSS3, Bootstrap 5, Chart.js
- **Database**: SQLite (upgrade to PostgreSQL for production)
- **AI**: Google Gemini 1.5 Flash / OpenAI GPT-3.5
- **Charts**: Chart.js 4.4

---

## 📄 License

MIT License — Free to use, modify, and distribute.
