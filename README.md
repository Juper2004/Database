# Employee Management System — Setup Guide

## Why "Failed to fetch" happens
The `index.html` frontend makes API calls to `http://localhost:8000`.  
This means **the FastAPI backend server must be running on your computer** before the UI works.  
Opening `index.html` alone in a browser is not enough.

---

## Quick Start (Windows / Mac / Linux)

### 1. Install Python dependencies
Open a terminal in the project folder and run:
```bash
pip install fastapi uvicorn
python -m pip install uvicorn fastapi
```

### 2. Seed the database (first time only)
```bash
python seed.py
```
This creates `ems.db` with sample departments, employees, leave requests, and payroll records.

### 3. Start the server
```bash
uvicorn server:app --reload
python -m uvicorn server:app --reload
```
You should see:
```
INFO:  Uvicorn running on http://127.0.0.1:8000
```

### 4. Open the app
Visit **http://localhost:8000** in your browser.  
(Do NOT open `index.html` directly as a file — use the URL above.)

---

## File Structure
```
ems/
├── server.py     ← FastAPI backend (run this)
├── db.py         ← SQLite database layer
├── seed.py       ← Demo data seeder
├── index.html    ← Frontend UI
└── ems.db        ← SQLite database (auto-created)
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Failed to fetch` | Server not running | Run `uvicorn server:app --reload` |
| `ModuleNotFoundError: fastapi` | Dependencies missing | Run `pip install fastapi uvicorn` |
| `Address already in use` | Port 8000 taken | Run `uvicorn server:app --port 8001` and change `API` in `index.html` to `http://localhost:8001` |
| Empty department dropdown | No data seeded | Run `python seed.py` |
