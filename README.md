# 🌍 Earth Intelligence
Live Natural Hazard Monitor

> **AI-powered multi-hazard satellite environmental monitoring system** — real-time tracking of wildfires, floods, earthquakes, cyclones, landslides, and heatwaves.

---

## ⚡ Quick Start (Windows)

```bat
start.bat
```

Then open **http://localhost:8000** in your browser.

---

## 🛠️ Manual Setup

```powershell
# 1. Go into backend
cd backend

# 2. Create & activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🔑 Environment Variables

Edit `backend\.env`:

| Variable | Default | Description |
|---|---|---|
| `NASA_FIRMS_KEY` | `DEMO_KEY` | Free key from [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/api/) |
| `LLM_PROVIDER` | `ollama` | `groq` / `openai` / `ollama` |
| `GROQ_API_KEY` | _(empty)_ | Free key from [console.groq.com](https://console.groq.com) |
| `OPENAI_API_KEY` | _(empty)_ | From [platform.openai.com](https://platform.openai.com) |
| `OLLAMA_MODEL` | `llama3.1:latest` | Local model name |

> **Minimum to run:** No changes needed — `DEMO_KEY` is pre-set for fire data. App works out of the box.

---

## 🌐 URLs

| URL | Description |
|-----|-------------|
| `http://localhost:8000` | 🗺️ Main Dashboard |
| `http://localhost:8000/docs` | 📖 Swagger API Docs |
| `http://localhost:8000/api/health` | ❤️ Health Check |

---

## 📁 Structure

```
eic-fixed/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings from .env
│   ├── schemas.py           # Pydantic models
│   ├── requirements.txt     # Python packages
│   ├── .env                 # Your secrets (never commit)
│   ├── routers/             # API route handlers
│   └── services/            # Data fetching & AI logic
├── frontend/
│   ├── index.html           # Dashboard UI
│   ├── app.js               # Map & frontend logic
│   └── style.css            # Styles
├── .gitignore
└── start.bat                # One-click Windows launcher
```

---

## 🤖 LLM Options

### Groq (Free, Recommended)
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key
```

### Ollama (Local, No Internet)
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:latest
```
Install Ollama → https://ollama.com, then run `ollama pull llama3.1`

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Activate venv: `venv\Scripts\activate` |
| Port 8000 in use | Use `--port 8001` |
| No fire data | Check `NASA_FIRMS_KEY` in `.env` |
| AI chat broken | Verify `LLM_PROVIDER` + key in `.env` |
| Ollama not working | Run `ollama serve` first |
