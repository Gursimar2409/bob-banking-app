# Banking Web Application — Step-by-Step Implementation Guide

> **Reference:** This guide follows the phased roadmap defined in `IMPLEMENTATION_PLAN.md`.  
> All instructions are written in plain English describing *what to do and why* — not full source code.

---

## Table of Contents

1. [Environment Setup](#1-environment-setup)
2. [Backend Implementation](#2-backend-implementation)
3. [Frontend Implementation](#3-frontend-implementation)
4. [Integration Steps](#4-integration-steps)
5. [Validation Rules](#5-validation-rules)
6. [Testing](#6-testing)
7. [Deployment](#7-deployment)

---

## 1. Environment Setup

### 1.1 Prerequisites
Before writing a single line of application code, confirm the following tools are available on your machine:

- **Python 3.9 or later** — the runtime for the Flask backend.
- **pip** — Python's package manager, bundled with Python.
- A terminal / command prompt with the ability to run Python commands.
- A code editor (VS Code, PyCharm, or similar).

---

### 1.2 Create the Project Folder Structure
Create the top-level project directory and the two sub-folders that map directly to the architecture:

- A `BACKEND/` folder for all Python and database files.
- A `FRONTEND/` folder with a `templates/` sub-folder (for HTML pages) and a `static/` sub-folder (for CSS and images).

This separation keeps server-side logic completely apart from browser-facing assets, which makes the project easier to navigate and maintain.

---

### 1.3 Create and Activate a Virtual Environment
A virtual environment isolates this project's Python dependencies from everything else installed on your machine. This prevents version conflicts and makes the project reproducible on another machine.

- Inside the project root, create a virtual environment using the `venv` module that ships with Python.
- Activate the environment in your terminal. On Windows use the `Scripts\activate` script; on macOS/Linux use `source bin/activate`.
- Once activated, your terminal prompt will show the environment name, confirming that all subsequent `pip install` commands apply only to this project.

---

### 1.4 Install Dependencies
With the virtual environment active, install the packages the application needs:

- **Flask** — the web framework that handles routing, request/response processing, and template rendering.
- **Werkzeug** — automatically installed with Flask; provides the password hashing utilities you will use for secure credential storage.

After installing, capture the exact package versions into a `requirements.txt` file at the project root. This file allows anyone else (or a deployment server) to reproduce the exact same environment by running a single install command against it.

---

### 1.5 Verify the Setup
Create a throwaway Python file, import Flask, and print the Flask version to confirm the installation succeeded. Then delete that file. This single check saves you from debugging missing-import errors later.

---

## 2. Backend Implementation

Work through the backend files in the order listed below. Each file has a single, clear responsibility — do not mix concerns across files.

---

### 2.1 Database Layer — `database.py`

This file is responsible for one thing: giving every other module a reliable way to talk to the SQLite database.

**What to implement:**

1. **Connection helper** — Write a function that opens a connection to `bank.db` (located in the `BACKEND/` folder) and returns it. SQLite creates the file automatically the first time a connection is opened, so no manual file creation is needed.

2. **Table initialisation** — Write a function that creates the two core tables (`customers` and `transactions`) if they do not already exist. Using "create if not exists" logic means you can safely call this function every time the app starts without wiping existing data.

3. **Seed function** — Write a function that inserts a small number of test customer records only if the customers table is currently empty. For each test customer, hash the password using Werkzeug's `generate_password_hash` before storing it — never insert a plain-text password. This seed function is called once at startup and is idempotent (safe to call multiple times).

4. **Call all three functions from a single `init_db()` entry point** so that `app.py` only needs to call one function at startup.

---

### 2.2 Data Models — `models.py`

This file defines the shape of your data as Python objects, giving the rest of the code a clean vocabulary to work with rather than dealing with raw database rows everywhere.

**What to implement:**

- Define a `Customer` class with attributes that mirror the columns in the `customers` table: a unique ID, a username, a hashed password, the account balance, and the customer's display name.
- Define a `Transaction` class with attributes mirroring the `transactions` table: a unique ID, the customer ID the transaction belongs to, the transaction type (deposit or withdrawal), the amount, and a timestamp.
- These classes do not need to connect to the database themselves — they are plain data containers. The database layer and service layer handle all queries.

---

### 2.3 Authentication Helpers — `auth.py`

This file centralises all identity and access logic so that no other file needs to know how authentication works internally.

**What to implement:**

1. **`find_customer_by_username(username)`** — Query the database for a customer record matching the given username. Return the record if found, or `None` if not. This keeps the database query in one place.

2. **`verify_password(stored_hash, submitted_password)`** — Use Werkzeug's `check_password_hash` function to compare the submitted plain-text password against the stored hash. Return `True` if they match, `False` otherwise. Never compare passwords as plain strings.

3. **`login_required` decorator** — Write a Python decorator that wraps a route function. Before executing the route, the decorator checks whether the current Flask session contains a `user_id` key. If it does, execution continues normally. If it does not, the decorator immediately redirects the request to the login page. Apply this decorator to every route that requires authentication (dashboard, deposit, withdraw, logout). This avoids copy-pasting the same session check into every route.

---

### 2.4 Account Service — `account.py`

This file is the single place where account data is read and mutated. No other file should query or update the balance directly.

**What to implement:**

1. **`get_balance(customer_id)`** — Fetch and return the current balance for the given customer from the database.

2. **`get_recent_transactions(customer_id, limit)`** — Return the most recent N transaction records for the customer, ordered from newest to oldest. The dashboard can use this to show a brief history.

3. **`apply_deposit(customer_id, amount)`** — Add the given amount to the customer's balance, then insert a new `DEPOSIT` record into the transactions table. Wrap both the balance update and the transaction insert in a single database transaction so that either both succeed or neither does — you never want a balance update without a matching transaction record.

4. **`apply_withdrawal(customer_id, amount)`** — Check whether the current balance is greater than or equal to the requested amount. If yes, deduct the amount and insert a `WITHDRAWAL` record, again inside a single database transaction. If no, raise an exception or return an error result that the calling route can use to display a "insufficient funds" message.

---

### 2.5 Flask Application Entry Point — `app.py`

This is the file that ties everything together. It creates the Flask app, registers all routes, and starts the server.

**What to implement:**

#### Application Setup
- Import Flask and create the `app` object.
- Set a `SECRET_KEY` on the app configuration. Flask uses this key to cryptographically sign the session cookie. Without it, sessions do not work. Use a long random string; never use something obvious like `"secret"`.
- Tell Flask where to find templates by pointing `template_folder` at `FRONTEND/templates/` and `static_folder` at `FRONTEND/static/`.
- Call `init_db()` from `database.py` immediately after creating the app so the database is always ready before the first request arrives.

#### Route: `GET /` — Root Redirect
- This route exists purely for convenience. When someone visits the bare root URL, redirect them to `/login`. This prevents a confusing 404 on the home page.

#### Route: `GET /login` — Show Login Page
- Check whether the user is already logged in (session has a `user_id`). If yes, redirect straight to `/dashboard` — there is no reason to show the login form to someone already authenticated.
- If not logged in, render and return the `login.html` template.

#### Route: `POST /login` — Process Login
- Extract the `username` and `password` fields from the submitted form data.
- Call `find_customer_by_username()` from `auth.py`. If no customer is found, re-render the login page with an error message saying the credentials are invalid. Do not reveal which of the two fields was wrong — this prevents username enumeration.
- Call `verify_password()` with the stored hash and submitted password. If the check fails, re-render the login page with the same generic error message.
- If both checks pass, store the customer's ID in the Flask session (`session['user_id'] = customer.id`) and redirect to `/dashboard`.

#### Route: `GET /logout` — Log Out
- Clear the session entirely using `session.clear()`.
- Redirect to `/login`.
- Apply the `@login_required` decorator so that a GET request to `/logout` from an already-logged-out browser doesn't cause an error.

#### Route: `GET /dashboard` — Dashboard
- Apply the `@login_required` decorator.
- Look up the customer record using the `user_id` stored in the session.
- Call `get_balance()` and `get_recent_transactions()` from `account.py`.
- Render `dashboard.html`, passing the customer name, current balance, and recent transactions as template variables.

#### Route: `GET /deposit` — Show Deposit Form
- Apply `@login_required`.
- Render `deposit.html` with no pre-filled data.

#### Route: `POST /deposit` — Process Deposit
- Apply `@login_required`.
- Extract the `amount` field from the form. Attempt to convert it to a float. If the conversion fails (the user typed letters), re-render the deposit form with an error message.
- Call `apply_deposit()` from `account.py`. On success, redirect to `/dashboard` (Post-Redirect-Get pattern — this prevents the browser from re-submitting the form if the user hits refresh).
- On any validation failure, re-render the form with a descriptive error message.

#### Route: `GET /withdraw` — Show Withdraw Form
- Apply `@login_required`.
- Render `withdraw.html` with no pre-filled data.

#### Route: `POST /withdraw` — Process Withdrawal
- Apply `@login_required`.
- Extract and convert the `amount` field exactly as you did for deposit.
- Call `apply_withdrawal()` from `account.py`. If it returns an insufficient-funds error, re-render the form with a clear message explaining the balance is too low.
- On success, redirect to `/dashboard`.

#### Error Handlers
- Register a handler for **404 Not Found** errors. Render a simple HTML page telling the user the page does not exist, with a link back to the dashboard or login page.
- Register a handler for **500 Internal Server Error** errors. Render a generic "something went wrong" page. Never expose a raw Python stack trace to the browser in any environment.

#### Starting the Server
- At the bottom of `app.py`, in the `if __name__ == '__main__':` guard, call `app.run()` with `debug=True` for local development. The debug flag enables auto-reload on file changes and shows detailed errors in the browser during development — it must be turned off in production.

---

### 2.6 Session Management — How It Works

Flask's session is a dictionary-like object that persists data across requests for a single user. Under the hood, Flask serialises this dictionary, signs it with the `SECRET_KEY`, and stores it in a browser cookie.

**Key rules to follow:**
- On login: write the customer's ID into the session. This is the only piece of identity data that needs to live there.
- On logout: call `session.clear()` to remove all session data. The signed cookie on the browser side becomes invalid.
- On every protected request: the `@login_required` decorator reads `session.get('user_id')`. If it returns `None` (the key is absent or the session has been cleared), the user is not authenticated.
- Never store sensitive data like the full customer object, balance, or password hash in the session. Store only the minimal identifier needed to look up the customer on each request.

---

## 3. Frontend Implementation

All HTML files live in `FRONTEND/templates/`. All pages share the same visual language through Bootstrap, so define a base structure and keep each page consistent.

---

### 3.1 Bootstrap Layout Strategy

Bootstrap is loaded from a CDN link in the `<head>` of every HTML file — no installation is needed. Every page should follow the same structural pattern:

- A `<head>` section that includes the Bootstrap CSS CDN link, the page title, and optionally a link to `style.css` for minor custom overrides.
- A `<body>` with a `<nav>` or header bar at the top, a central `<main>` content area using Bootstrap's grid (`container`, `row`, `col`), and a minimal footer.
- Form elements use Bootstrap's `form-control` class for inputs and `btn` classes for buttons, giving a consistent, polished appearance with no custom CSS needed.
- Alert boxes (Bootstrap `alert alert-success` and `alert alert-danger`) display feedback messages. These boxes should only appear when the backend passes a non-empty message variable into the template.

---

### 3.2 Login Page — `login.html`

**Purpose:** The entry point of the application. Every unauthenticated user lands here.

**Layout:**
- Centre a compact card on the screen using Bootstrap's grid. A card with a bank logo or title, a username input, a password input, and a "Login" submit button is sufficient.
- The form's `action` attribute should point to `/login` and `method` should be `POST`.
- Below the form, display the error message variable if it was passed from the backend. Use a red Bootstrap alert for errors.

**Logic guidance:**
- The username and password fields must have `name` attributes that exactly match what `app.py` reads with `request.form.get()`.
- Do not add client-side JavaScript validation — server-side validation is the authoritative check. The browser's built-in HTML5 `required` attribute is acceptable to prevent empty submissions but is not a security control.

---

### 3.3 Dashboard Page — `dashboard.html`

**Purpose:** The authenticated home screen, showing the customer's financial summary and navigation to all actions.

**Layout:**
- Display a personalised welcome heading using the customer name variable injected by Flask.
- Show the current balance prominently — use a large Bootstrap card or a `display-4` heading so it is immediately visible.
- Provide three clearly labelled action buttons: **Deposit**, **Withdraw**, and **Logout**. Each is a link styled as a Bootstrap button pointing to the corresponding route.
- Optionally, below the balance, show a small table of recent transactions (type, amount, date) using the transactions list passed from the backend. If the list is empty, show a friendly "No transactions yet" message.

**Logic guidance:**
- The page is server-rendered; there is no JavaScript needed to update the balance. Every action results in a page reload, so the balance shown is always freshly fetched from the database.

---

### 3.4 Deposit Form — `deposit.html`

**Purpose:** Allow the customer to enter and submit a deposit amount.

**Layout:**
- A centred card with a heading ("Deposit Funds"), a numeric input for the amount, a "Deposit" submit button, and a "Back to Dashboard" link.
- The form's `action` should be `/deposit` and `method` should be `POST`.
- Display a success message (green alert) or error message (red alert) if one was passed from the backend.

**Logic guidance:**
- The amount input field should use `type="number"` with `step="0.01"` and `min="0.01"` so the browser enforces basic numeric input. The server will also validate — this is just a usability aid.
- After a successful deposit, the backend redirects to the dashboard, so the deposit form itself never needs to show a "success" state — the updated balance on the dashboard serves as the confirmation.

---

### 3.5 Withdraw Form — `withdraw.html`

**Purpose:** Allow the customer to enter and submit a withdrawal amount.

**Layout and logic guidance:**
- Identical structure to `deposit.html`, but with "Withdraw Funds" as the heading and `action="/withdraw"`.
- The error message here is especially important: when the backend detects insufficient funds, it passes a clear message that this form displays. The customer must understand why their request failed before they can take corrective action.
- Optionally, display the current balance on this page (passed from the backend) so the customer can see at a glance how much they have available before they type an amount.

---

## 4. Integration Steps

### 4.1 Connect Flask to the Frontend Templates

Flask needs to know where to find templates and static files. This is configured once in `app.py` when the Flask app object is created:

- Set `template_folder` to the path of `FRONTEND/templates/`. Flask's `render_template()` function will look here for HTML files.
- Set `static_folder` to the path of `FRONTEND/static/`. Flask will automatically serve files from this folder at the `/static/` URL, so your CSS link in HTML can reference `/static/style.css`.

Verify this is working by running the app and visiting `/login`. If the page renders with Bootstrap styling, the template and static wiring is correct.

---

### 4.2 Connect Flask to SQLite

The connection between `app.py` and `bank.db` flows through `database.py`:

- `app.py` calls `init_db()` at startup, which creates the database file and tables if they don't exist.
- Every service function in `account.py` and every query in `auth.py` opens a connection via the helper in `database.py`, performs its operation, commits if it wrote data, and closes the connection.

**The key principle:** a database connection should be opened, used, and closed within a single function call. Do not hold connections open across requests. SQLite handles this cleanly at the scale of this application.

---

### 4.3 Wire Form Submissions to Backend Routes

Each HTML form needs to correctly identify the backend route that will process it:

- The form's `action` attribute is the URL path (e.g., `/login`, `/deposit`, `/withdraw`).
- The form's `method` must be `POST` for any operation that changes data.
- Every input field's `name` attribute is the key used in `request.form.get('name')` on the backend. These must match exactly — a mismatch is a common source of `None` values appearing in your route handlers.

Test each form by submitting it and checking that the correct route function receives the data and responds appropriately.

---

### 4.4 Verify the Post-Redirect-Get (PRG) Pattern

After every successful POST (login, deposit, withdrawal), the backend must redirect to a GET route rather than rendering a template directly. This is the PRG pattern and it prevents the browser from re-submitting the form when the user hits the browser's back button or refreshes.

The correct flow is:
1. Form is submitted as POST.
2. Backend processes the data.
3. On success: backend returns a `redirect()` response (HTTP 302) pointing to a GET route.
4. Browser follows the redirect and loads the target page with a GET request.
5. The page renders from fresh data.

If a route renders a template directly after a POST (instead of redirecting), add a redirect.

---

## 5. Validation Rules

Validation happens in two places: lightly in the browser (HTML5 attributes for usability) and authoritatively in the backend (Python logic for security). Never rely on browser-side validation alone.

---

### 5.1 Login Validation

| What to check | How to handle it |
|---|---|
| Username field is empty | Re-render login page with a generic "Invalid credentials" message |
| Password field is empty | Re-render login page with the same generic message |
| Username does not exist in the database | Re-render login page with the same generic message — do not say "username not found" |
| Password does not match the stored hash | Re-render login page with the same generic message — do not say "wrong password" |

**Why use the same message for all failures?** Giving different messages for "user not found" versus "wrong password" lets an attacker discover which usernames exist in your system (username enumeration). One generic message prevents this.

---

### 5.2 Balance Validation (Withdrawal)

| What to check | How to handle it |
|---|---|
| Requested amount is greater than current balance | Re-render the withdraw form with a message stating insufficient funds |
| Current balance is exactly zero | Re-render the withdraw form explaining no funds are available |

These checks happen inside `apply_withdrawal()` in `account.py`, before any database write occurs.

---

### 5.3 Deposit Amount Checks

| What to check | How to handle it |
|---|---|
| Amount field is empty | Re-render the deposit form with "Please enter an amount" |
| Amount is not a valid number | Re-render the deposit form with "Please enter a valid number" |
| Amount is zero | Re-render with "Amount must be greater than zero" |
| Amount is negative | Re-render with "Amount must be greater than zero" |

These checks happen in the `POST /deposit` route handler before calling `apply_deposit()`.

---

### 5.4 Withdrawal Amount Checks

Apply the same numeric checks as deposit, then additionally check the balance. Order matters: check that the input is a valid positive number first, then check the balance. Performing the balance check on a non-numeric value would cause an error.

| What to check | How to handle it |
|---|---|
| Empty / non-numeric / zero / negative | Same messages as deposit (check first) |
| Amount exceeds current balance | Re-render with "Insufficient funds. Your balance is $X." |

---

## 6. Testing

### 6.1 Unit Tests

Unit tests verify that individual functions work correctly in isolation, without needing a running server or a real database. Use Python's built-in `unittest` module or `pytest`.

**What to unit test:**

- **Password hashing** — Call `generate_password_hash` with a known password, then call `check_password_hash` on the result. Assert it returns `True`. Call it with the wrong password and assert `False`.

- **`apply_deposit` logic** — Create an in-memory SQLite database with a seeded test customer. Call `apply_deposit` with a valid amount. Assert the returned or fetched balance equals the original balance plus the deposit. Assert a transaction record was inserted.

- **`apply_withdrawal` logic (success path)** — Same setup. Call `apply_withdrawal` with an amount less than the balance. Assert the balance decreased correctly. Assert a transaction record was inserted.

- **`apply_withdrawal` logic (failure path)** — Call `apply_withdrawal` with an amount larger than the balance. Assert that an error is returned or an exception is raised, and that the balance in the database is unchanged.

- **Numeric validation helpers** — If you extract the "is this a valid positive number?" check into a standalone function, test it with a range of inputs: valid floats, zero, negatives, empty strings, letters, and special characters.

---

### 6.2 Integration Tests

Integration tests verify that the Flask routes, service layer, and database work correctly together end-to-end. Flask provides a `test_client()` that lets you send HTTP requests to your app in a test without running a real server.

**What to integration test:**

- **GET `/login`** — Assert the response status is 200 and the response body contains the word "Login".

- **POST `/login` with valid credentials** — Assert the response redirects (status 302) to `/dashboard`. Assert the session now contains `user_id`.

- **POST `/login` with invalid credentials** — Assert the response status is 200 (re-renders the form) and the body contains an error message.

- **GET `/dashboard` without a session** — Assert the response redirects to `/login`.

- **GET `/dashboard` with a valid session** — Assert the response is 200 and the body contains the customer's name and a balance figure.

- **POST `/deposit` with a valid amount** — Assert a redirect to `/dashboard`. Assert the balance in the database increased.

- **POST `/withdraw` with a valid amount** — Assert a redirect to `/dashboard`. Assert the balance decreased.

- **POST `/withdraw` with an amount exceeding the balance** — Assert the response is 200 (form re-renders) and the body contains an error message. Assert the balance is unchanged.

- **GET `/logout`** — Assert a redirect to `/login`. Assert the session no longer contains `user_id`.

---

### 6.3 Manual Testing Checklist

Walk through every scenario in a real browser before considering the application complete.

**Happy path (everything goes right):**
- [ ] Open the app in a browser. Confirm you are shown the login page.
- [ ] Enter valid credentials. Confirm you are redirected to the dashboard.
- [ ] Confirm the dashboard shows your name and the correct starting balance.
- [ ] Click "Deposit". Enter a valid amount (e.g., 500). Submit.
- [ ] Confirm you are redirected to the dashboard and the balance increased by 500.
- [ ] Click "Withdraw". Enter a valid amount less than the balance. Submit.
- [ ] Confirm you are redirected to the dashboard and the balance decreased correctly.
- [ ] Click "Logout". Confirm you are returned to the login page.
- [ ] Confirm that navigating directly to `/dashboard` now redirects back to `/login`.

**Error paths (things go wrong):**
- [ ] Enter a wrong password on the login page. Confirm a generic error message appears and you stay on the login page.
- [ ] Enter a non-existent username. Confirm the same generic error message (not a different one).
- [ ] On the deposit form, submit an empty amount. Confirm an error message appears.
- [ ] On the deposit form, type letters instead of a number. Confirm an error message appears.
- [ ] On the deposit form, enter zero. Confirm an error message appears.
- [ ] On the withdraw form, enter an amount larger than your balance. Confirm an "insufficient funds" message appears.
- [ ] Attempt to navigate to `/deposit` without being logged in. Confirm redirect to `/login`.
- [ ] After a successful deposit, press the browser's Back button. Confirm the form is not re-submitted (PRG pattern working).

---

## 7. Deployment

### 7.1 Run Locally

Running locally is straightforward:

1. Activate the virtual environment.
2. Navigate to the `BACKEND/` folder in your terminal.
3. Run `app.py` with `python app.py`. Flask's built-in development server will start on `http://127.0.0.1:5000` by default.
4. Open that URL in a browser.

The `debug=True` flag in `app.py` means Flask will automatically restart when you save a file change, and will display detailed error pages in the browser when an exception is raised. This is invaluable during development.

---

### 7.2 Production Considerations

Flask's built-in development server is **not suitable for production**. It is single-threaded, not hardened against malicious input, and not designed for concurrent users. For production, consider the following:

| Area | What to do |
|---|---|
| **WSGI Server** | Replace Flask's dev server with a production-grade WSGI server such as **Gunicorn** (Linux/macOS) or **Waitress** (Windows-compatible). Run the app as `gunicorn app:app` instead of `python app.py`. |
| **Debug Mode** | Set `debug=False` and read the `SECRET_KEY` from an environment variable, not hardcoded in the source file. Never commit a real secret key to version control. |
| **HTTPS** | Place the application behind a reverse proxy (Nginx or Apache) that handles TLS/SSL termination. The Flask app itself serves plain HTTP to the proxy. |
| **Database** | SQLite is fine for a single-server deployment with low traffic. If you later need concurrent writes or multi-server deployment, migrate to PostgreSQL or MySQL. |
| **Static Files** | In production, let the reverse proxy (Nginx) serve files from `FRONTEND/static/` directly rather than routing those requests through Flask. This is faster and reduces load on the Python process. |
| **Logging** | Replace `debug=True` logging with structured application logs written to a file or a log aggregation service. At minimum, log all authentication events (successful logins, failed attempts) and all transaction operations. |
| **Environment Variables** | Keep all environment-specific settings (secret key, database path, debug flag) in environment variables or a `.env` file. Never hardcode these values in source files that will be committed to version control. |

---

*This document provides plain-English implementation instructions that trace directly to the architecture and phased roadmap in `IMPLEMENTATION_PLAN.md`. It does not contain executable source code.*
