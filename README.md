# SecureBank — Banking Web Application

A full-stack banking web application built with **Python Flask**, **Bootstrap 5**, and **SQLite**.

---

## Project Structure

```
banking-workshop/
├── BACKEND/
│   ├── app.py          # Flask entry point + all routes
│   ├── auth.py         # Login helpers + @login_required decorator
│   ├── account.py      # Deposit / withdrawal service layer
│   ├── models.py       # Customer + Transaction data classes
│   ├── database.py     # SQLite connection, schema init, seed data
│   └── bank.db         # Auto-created on first run
├── FRONTEND/
│   ├── templates/
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── deposit.html
│   │   ├── withdraw.html
│   │   ├── 404.html
│   │   └── 500.html
│   └── static/
│       └── style.css
├── tests/
│   ├── conftest.py          # pytest path setup
│   ├── test_unit.py         # 21 unit tests
│   └── test_integration.py  # 31 integration tests
├── requirements.txt
├── IMPLEMENTATION_PLAN.md
└── STEP_BY_STEP_IMPLEMENTATION_GUIDE.md
```

---

## Quick Start

### 1. Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the application

```bash
python BACKEND/app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## Demo Accounts

| Username  | Password      | Starting Balance |
|-----------|---------------|-----------------|
| `alice`   | `password123` | $5,000.00       |
| `bob`     | `password123` | $3,250.50       |
| `charlie` | `password123` | $750.00         |

---

## Run Tests

```bash
python -m pytest tests/ -v
```

Expected output: **52 passed**

---

## Features

- **Secure login** — passwords stored as bcrypt hashes (Werkzeug)
- **Session management** — server-signed cookies; session cleared on logout
- **Route guards** — all protected pages redirect unauthenticated users to `/login`
- **Deposit & Withdraw** — atomic DB transactions; balance can never go negative
- **Input validation** — empty / non-numeric / zero / negative amounts are rejected with clear messages
- **Username enumeration protection** — login failures always return the same generic message
- **Post-Redirect-Get** — all successful POSTs redirect to prevent form re-submission
- **Transaction history** — last 10 transactions shown on the dashboard
- **Responsive UI** — Bootstrap 5 grid works on mobile and desktop
- **Custom error pages** — 404 and 500 handlers return styled pages (no stack traces)

---

## Production Notes

- Set `FLASK_SECRET_KEY` environment variable to a random 32+ character string
- Use **Gunicorn** (Linux) or **Waitress** (Windows) instead of the Flask dev server
- Place behind an **Nginx** reverse proxy for HTTPS termination and static file serving
- Set `debug=False` (or remove the `debug=True` flag entirely)
