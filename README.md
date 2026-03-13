# Silasya × Shoumitra — AI Lead Finder
### Python + Flask + MySQL | Full Team App

---

## What This App Does
- AI searches Google, LinkedIn, Instagram, Facebook, IndiaMART, Alibaba, Etsy, Fab India and more
- Finds real leads for **Silasya (B2C)** and **Shoumitra (B2B exports)**
- Saves all leads to a shared **MySQL database** — your whole team sees the same leads
- Generate **AI outreach scripts** for every platform (WhatsApp, Instagram, Facebook, LinkedIn, Email)
- Full **CRM** — update lead status, filter, search, export to CSV

---

## Step-by-Step Setup (VS Code)

### Step 1 — Install Requirements

Make sure you have these installed:
- Python 3.10+ → https://python.org/downloads
- MySQL 8.0+ → https://dev.mysql.com/downloads/mysql
- MySQL Workbench (optional, easier to manage DB) → https://dev.mysql.com/downloads/workbench

---

### Step 2 — Open Project in VS Code

```
Open VS Code → File → Open Folder → Select "silasya-app" folder
```

---

### Step 3 — Create Virtual Environment

Open VS Code Terminal (Ctrl + ` ) and run:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install all packages
pip install -r requirements.txt
```

---

### Step 4 — Setup MySQL Database

Option A — Using MySQL command line:
```bash
mysql -u root -p < setup_db.sql
```

Option B — Using MySQL Workbench:
1. Open MySQL Workbench
2. Connect to your local server
3. File → Open SQL Script → select `setup_db.sql`
4. Click the lightning bolt (Execute) button

---

### Step 5 — Create Your .env File

Copy the example file:
```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Then open `.env` in VS Code and fill in your details:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_actual_mysql_password_here
DB_NAME=silasya_leads

ANTHROPIC_API_KEY=sk-ant-api...your_key_here

FLASK_SECRET_KEY=silasya-secret-change-this-2025
FLASK_DEBUG=True
PORT=5000
```

> Get your Anthropic API key from: https://console.anthropic.com

---

### Step 6 — Run the App

```bash
python app.py
```

You will see:
```
🚀 Starting Silasya & Shoumitra Lead Finder...
📦 Initializing database...
✅ Database initialized successfully
✅ App running at http://localhost:5000
📋 Share with team: http://YOUR_IP:5000
```

Open browser → http://localhost:5000

---

## Sharing With Your Team

### Option A — Same WiFi Network (Easiest)

1. Find your computer's IP address:
   - Windows: Open CMD → type `ipconfig` → look for "IPv4 Address" e.g. `192.168.1.5`
   - Mac: System Settings → WiFi → Details → IP Address

2. Share this link with your team:
   ```
   http://192.168.1.5:5000
   ```
   Anyone on the same WiFi can open this and use the app!

### Option B — Deploy to a Server (For Remote Teams)

Free options:
- **Railway.app** → https://railway.app (easiest, free tier)
- **Render.com** → https://render.com (free tier)
- **PythonAnywhere** → https://pythonanywhere.com

For Railway:
1. Push code to GitHub
2. Go to railway.app → New Project → Deploy from GitHub
3. Add environment variables in Railway dashboard
4. Add a MySQL database service in Railway
5. Your app gets a public URL like `silasya-leads.railway.app`

---

## Project Structure

```
silasya-app/
├── app.py              ← Main Flask application (all backend logic)
├── requirements.txt    ← Python packages to install
├── setup_db.sql        ← Run this once to create MySQL tables
├── .env.example        ← Copy this to .env and fill in your details
├── .env                ← Your secret config (never share this!)
├── templates/
│   └── index.html      ← The full frontend UI
└── static/             ← (for CSS/JS files if needed later)
```

---

## API Endpoints (for developers)

| Method | URL | What it does |
|--------|-----|--------------|
| GET | `/api/status` | Check if DB is connected |
| GET | `/api/stats` | Get lead counts and stats |
| GET | `/api/leads` | Get all leads (filterable) |
| POST | `/api/leads` | Save one lead |
| POST | `/api/leads/bulk` | Save multiple leads |
| PUT | `/api/leads/:id` | Update lead status/notes |
| DELETE | `/api/leads/:id` | Delete a lead |
| POST | `/api/search` | Run AI lead search |
| POST | `/api/outreach/:id` | Generate AI outreach scripts |
| GET | `/api/team` | Get team members |
| POST | `/api/team` | Add team member |
| GET | `/api/export/csv` | Download all leads as CSV |

---

## Troubleshooting

**"mysql.connector error"** → Check DB_PASSWORD in .env is correct

**"anthropic.AuthenticationError"** → Check ANTHROPIC_API_KEY in .env

**"Address already in use"** → Change PORT=5001 in .env

**Team can't connect** → Make sure firewall allows port 5000. On Windows: search "Windows Firewall" → Allow an app → add Python

---

## Tech Stack
- **Backend**: Python 3 + Flask
- **Database**: MySQL 8
- **AI**: Anthropic Claude (claude-sonnet-4)
- **Frontend**: Vanilla HTML/CSS/JS (no framework needed)
