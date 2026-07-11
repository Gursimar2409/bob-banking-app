# Banking Web Application — Implementation Plan

---

## 1. Solution Overview

### Objective
Build a secure, browser-based banking web application that allows customers to log in, view their account balance, and perform basic fund transactions (deposit and withdrawal), with a clean dashboard as the central hub.

### Scope
| In Scope | Out of Scope |
|---|---|
| Customer login / logout | User self-registration |
| Dashboard landing page | Multi-factor authentication |
| View account balance | Inter-bank or wire transfers |
| Deposit funds | Loan or credit features |
| Withdraw funds | Admin / back-office portal |
| Session management | External payment gateway integration |

### Users
- **Retail Customer** — the sole actor; authenticates and performs account operations via the browser.

### Functional Requirements
1. A customer can log in using a username and password.
2. After login the customer is redirected to a personal dashboard.
3. The dashboard prominently displays the current account balance.
4. The customer can deposit a positive amount; the balance updates immediately.
5. The customer can withdraw a positive amount up to the available balance; the balance updates immediately.
6. The customer can log out, which ends the session and returns them to the login page.
7. Unauthenticated requests to protected pages redirect to the login page.

### Non-Functional Requirements
- **Security** — passwords stored as hashed values; session tokens managed server-side.
- **Usability** — responsive UI that works on desktop and mobile via Bootstrap.
- **Simplicity** — single-file SQLite database; no external services required.
- **Maintainability** — clear separation between frontend templates and backend logic.
- **Performance** — all operations complete within a single HTTP request/response cycle; no background jobs needed at this scale.

### Assumptions
- A small, fixed set of customer accounts is pre-seeded into the database.
- SQLite is sufficient; no concurrent write contention is expected.
- The application runs on a single server process (Flask development server or a lightweight WSGI host).
- HTTPS termination is handled by the deployment environment, not the application itself.
- No email or SMS verification is required.

---

## 2. High-Level Architecture

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                        BROWSER                           │
│  ┌─────────────────────────────────────────────────────┐ │
│  │   HTML Pages rendered by Jinja2 + Bootstrap CSS     │ │
│  │   (login, dashboard, deposit, withdraw)             │ │
│  └──────────────┬──────────────────────────────────────┘ │
└─────────────────┼────────────────────────────────────────┘
                  │  HTTP (GET / POST)
                  ▼
┌──────────────────────────────────────────────────────────┐
│                    BACKEND  (Flask)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Auth Module │  │  Dashboard   │  │  Transaction  │  │
│  │  /login      │  │  /dashboard  │  │  /deposit     │  │
│  │  /logout     │  │              │  │  /withdraw    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         └─────────────────┴──────────────────┘           │
│                           │  SQLAlchemy / sqlite3         │
└───────────────────────────┼──────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────┐
│                   DATABASE  (SQLite)                     │
│   bank.db  ── customers table ── transactions table      │
└──────────────────────────────────────────────────────────┘
```

### Frontend → Backend → Database Interaction
- The **frontend** is pure server-rendered HTML; Bootstrap provides layout and styling. No JavaScript framework is involved.
- The **backend** (Flask) owns all business logic. It serves rendered HTML templates and accepts HTML form submissions.
- The **database** (SQLite) is accessed exclusively through the backend; the browser never communicates with it directly.

### Request Lifecycle
1. Browser sends an HTTP request (GET to load a page, POST to submit a form).
2. Flask routes the request to the appropriate view function.
3. The view function reads from or writes to SQLite as needed.
4. Flask renders a Jinja2 template with the result data.
5. The rendered HTML page is returned to the browser.

---

## 3. Component Design

### Frontend Responsibilities (`FRONTEND/`)
- Provide HTML templates for every page: login, dashboard, deposit, withdraw.
- Use Bootstrap grid and components for a responsive, consistent look.
- Display server-provided data (balance, messages) injected via Jinja2 template variables.
- Submit user input (credentials, amounts) via standard HTML forms (`method="POST"`).
- Show inline feedback messages (success / error) passed back from the backend.

### Backend Responsibilities (`BACKEND/`)
- Define URL routes and map them to view functions.
- Validate and sanitise all incoming form data.
- Authenticate users: compare submitted password hash against stored hash.
- Manage user sessions: set session on login, clear on logout, guard protected routes.
- Execute account operations: read balance, apply deposit, apply withdrawal with balance check.
- Pass result context to templates for rendering.
- Return appropriate HTTP redirects after successful POST actions (PRG pattern).

### Database Responsibilities
- Persist customer account records (identity, credentials, balance).
- Persist a log of completed transactions (type, amount, timestamp).
- Enforce data integrity constraints at the storage level (e.g., balance cannot go negative).
- Provide a single `bank.db` file co-located with the backend for easy portability.

---

## 4. Folder Structure

```
banking-app/
│
├── FRONTEND/                  # All browser-facing assets
│   ├── templates/             # Jinja2 HTML templates served by Flask
│   │   ├── login.html         # Login form page
│   │   ├── dashboard.html     # Post-login landing page with balance
│   │   ├── deposit.html       # Deposit funds form
│   │   └── withdraw.html      # Withdraw funds form
│   └── static/                # Static assets (CSS overrides, images)
│       └── style.css          # Optional custom styles on top of Bootstrap
│
├── BACKEND/                   # All server-side Python code
│   ├── app.py                 # Flask application entry point; route definitions
│   ├── auth.py                # Authentication helpers (hash check, session guard)
│   ├── account.py             # Account query and mutation logic
│   ├── models.py              # Database model definitions
│   ├── database.py            # DB connection initialisation and seed helper
│   └── bank.db                # SQLite database file (auto-created on first run)
│
├── requirements.txt           # Python dependencies (Flask, etc.)
└── IMPLEMENTATION_PLAN.md     # This document
```

| Folder / File | Responsibility |
|---|---|
| `FRONTEND/templates/` | Server-rendered page layouts, no business logic |
| `FRONTEND/static/` | CSS and images loaded directly by the browser |
| `BACKEND/app.py` | Application wiring: routes, Flask config, session setup |
| `BACKEND/auth.py` | Login validation, session creation/destruction, route guard decorator |
| `BACKEND/account.py` | Balance retrieval, deposit and withdrawal business rules |
| `BACKEND/models.py` | Data model classes / table definitions |
| `BACKEND/database.py` | DB initialisation, connection helper, seed data |
| `BACKEND/bank.db` | Persistent SQLite data file |

---

## 5. Module Breakdown

### Authentication Module
**Goal:** Control who can access the application and for how long.

- **Login flow** — Accept username + password, verify credentials against the database, create a server-side session, redirect to the dashboard.
- **Logout flow** — Invalidate the current session, redirect to the login page.
- **Route guard** — A reusable decorator (or helper) that checks for a valid session before every protected route; redirects to login if absent.
- **Password storage** — Passwords are stored as hashed values (e.g., bcrypt or Werkzeug's `generate_password_hash`); plain-text passwords are never stored.

### Dashboard Module
**Goal:** Give the customer an at-a-glance view of their account upon login.

- Renders a welcome page personalised with the customer's name.
- Displays the current account balance fetched from the database.
- Provides navigation links/buttons to Deposit, Withdraw, and Logout.
- Acts as the default redirect destination after a successful login.

### Account Management Module
**Goal:** Expose account data to the rest of the application in a controlled way.

- Provides a function to retrieve the current balance for a given customer.
- Provides a function to retrieve a recent transaction history summary (count / list).
- Serves as the single point through which the dashboard and transaction modules read account state.

### Transactions Module
**Goal:** Process fund movements and maintain an auditable record.

- **Deposit** — Accepts a positive amount, adds it to the balance, records a `DEPOSIT` transaction entry, returns updated balance.
- **Withdrawal** — Accepts a positive amount, checks sufficient funds, deducts from balance, records a `WITHDRAWAL` transaction entry, returns updated balance. Rejects if the amount exceeds the balance.
- **Validation** — Both operations reject zero or negative amounts and non-numeric input before touching the database.
- **Feedback** — Returns a success or descriptive error message that the backend passes to the template for display.

---

## 6. Implementation Roadmap

### Development Phases

#### Phase 1 — Project Scaffolding
**Intent:** Establish the skeleton that all subsequent work builds on.
- Create folder structure (`FRONTEND/`, `BACKEND/`).
- Install and configure Flask; create a minimal `app.py` with a health-check route.
- Initialise SQLite database and define the `customers` and `transactions` tables.
- Seed one test customer account.
- Verify the app starts without errors.

**Dependencies:** None.  
**Effort:** Low.

---

#### Phase 2 — Authentication
**Intent:** Allow customers to prove their identity and protect all other routes.
- Implement the login page template.
- Implement login POST handler: credential lookup, hash comparison, session creation.
- Implement logout route: session teardown + redirect.
- Implement the `@login_required` route guard.
- Verify that accessing `/dashboard` without a session redirects to `/login`.

**Dependencies:** Phase 1 (database and app skeleton must exist).  
**Effort:** Medium.

---

#### Phase 3 — Dashboard
**Intent:** Provide the authenticated landing page with balance visibility.
- Implement the dashboard template with Bootstrap layout.
- Implement the `/dashboard` route (guarded): fetch and display customer name and balance.
- Add navigation controls for Deposit, Withdraw, and Logout.

**Dependencies:** Phase 2 (session guard must work).  
**Effort:** Low.

---

#### Phase 4 — Transactions (Deposit & Withdraw)
**Intent:** Enable the core banking operations.
- Implement deposit template and POST handler: validate amount, update balance, record transaction.
- Implement withdraw template and POST handler: validate amount, check funds, update balance, record transaction.
- Display success/error feedback inline on the form page.
- Redirect to dashboard with updated balance after success.

**Dependencies:** Phase 3 (dashboard must exist as the post-transaction target).  
**Effort:** Medium.

---

#### Phase 5 — UI Polish & End-to-End Testing
**Intent:** Ensure the full user journey works and looks consistent.
- Apply Bootstrap styling consistently across all pages.
- Add responsive layout checks (mobile viewport).
- Walk through the complete user journey: login → dashboard → deposit → withdraw → logout.
- Verify edge cases: wrong password, insufficient funds, invalid amount input.
- Fix any integration issues discovered.

**Dependencies:** Phases 1–4 complete.  
**Effort:** Low–Medium.

---

### Dependency Map

```
Phase 1 (Scaffold)
    └──► Phase 2 (Auth)
              └──► Phase 3 (Dashboard)
                        └──► Phase 4 (Transactions)
                                   └──► Phase 5 (Polish & Test)
```

---

*This document is a planning artefact only. It does not contain database schema definitions, SQL scripts, API contracts, or detailed implementation code.*
