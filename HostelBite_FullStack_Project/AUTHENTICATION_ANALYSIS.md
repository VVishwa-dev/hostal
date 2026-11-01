# HostelBite Authentication Analysis

This document was created from the actual source code in the repository `VVishwa-dev/hostal` and intentionally leaves the existing project files untouched. It is a review of the implemented authentication system only.

## 1) Repository and project structure

Repository reviewed:
- `VVishwa-dev/hostal`

Application folder:
- `HostelBite_FullStack_Project/`

Key files:
- `HostelBite_FullStack_Project/app.py` — main Flask app, routes, auth logic, DB setup
- `HostelBite_FullStack_Project/README.md` — project documentation
- `HostelBite_FullStack_Project/requirements.txt` — Python dependencies
- `HostelBite_FullStack_Project/templates/login.html` — login form
- `HostelBite_FullStack_Project/templates/base.html` — shared page layout
- `HostelBite_FullStack_Project/instance/hostelbite.db` — SQLite database
- `HostelBite_FullStack_Project/static/css/style.css` — styles

## 2) What the project actually is

This project is a Flask-based hostel mess portal with:
- student login
- admin login
- menu display
- votes and results
- admin operations

It is not a modern production authentication system with registration, OAuth, API tokens, or JWT.

## 3) Authentication components

### 3.1 Database schema for users

Actual file and function:
- `HostelBite_FullStack_Project/app.py`
- `init_db()`

```python
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('student','admin')),
  display_name TEXT NOT NULL
);
```

What this means:
- each user has an auto-incrementing id
- username must be unique
- password is stored as a hash string, not plain text
- role is constrained to `student` or `admin`
- display name is stored separately

### 3.2 Demo users created automatically

```python
seed_users = [
  ("student1", "student123", "student", "Demo Student"),
  ("student2", "student123", "student", "Demo Student Two"),
  ("admin", "admin123", "admin", "Mess Manager")
]
for username, password, role, display_name in seed_users:
    db.execute("INSERT OR IGNORE INTO users(username,password_hash,role,display_name) VALUES(?,?,?,?)",
               (username, generate_password_hash(password), role, display_name))
```

This code is in `init_db()` and creates default demo accounts on first run.

Important note:
- The project does not have a signup/registration page.
- It seeds users directly in the database at startup.
- This is fine for a demo, but not a realistic user registration system.

### 3.3 Password hashing

Actual imports:
```python
from werkzeug.security import generate_password_hash, check_password_hash
```

This is the actual password protection mechanism used:
- `generate_password_hash()` turns a password into a hash before storage
- `check_password_hash()` checks the entered password against the stored hash

This is more secure than storing plain text passwords, but it is a simple demo-grade implementation.

### 3.4 Login route

Actual route:
```python
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        with connect() as db:
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.update(user_id=user["id"], username=user["username"], role=user["role"], display_name=user["display_name"])
            return redirect(url_for("menu"))
        flash("Username or password is incorrect.", "error")
    return render_template("login.html")
```

In simple words:
- user submits login form
- app reads username and password
- app fetches the matching user from SQLite
- app verifies the password against the stored hash
- if valid, it stores login state in Flask session

### 3.5 Protected routes and middleware

Actual middleware:
```python
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper
```

```python
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Only hostel management can perform that action.", "error")
            return redirect(url_for("menu"))
        return fn(*args, **kwargs)
    return wrapper
```

These functions are used as decorators on protected routes, such as:
- `/menu`
- `/results`
- `/admin`
- `/api/results`

### 3.6 Session-based auth (not JWT)

Actual config:
```python
app = Flask(__name__)
app.secret_key = os.environ.get("HOSTELBITE_SECRET", "change-this-demo-secret-before-deployment")
```

And on successful login:
```python
session.update(user_id=user["id"], username=user["username"], role=user["role"], display_name=user["display_name"])
```

This is a Flask session authentication model, not JWT-based authentication.

There is no:
- bearer token issuance
- refresh token flow
- JWT verification
- Authorization header parsing
- token expiration code

### 3.7 Logout

Actual route:
```python
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
```

This removes session data and sends the user away from auth pages.

## 4) Authentication request flow

### Step-by-step flow

1. User opens the app and visits `/login`.
2. The browser renders the login form from `templates/login.html`.
3. User enters username and password.
4. The browser sends them as an HTTP POST request.
5. Backend receives `request.form.get("username")` and `request.form.get("password")`.
6. App queries SQLite for the matching user record.
7. It calls `check_password_hash(user["password_hash"], password)`.
8. If the hash matches, the app calls `session.update(...)`.
9. Flask stores the session in a browser-managed cookie/session state.
10. The user is redirected to the protected page, typically `/menu`.
11. Protected routes check `session.get("user_id")`.
12. Admin routes additionally check `session.get("role") == "admin"`.
13. On logout, `session.clear()` is called.

## 5) Credentials and token handling

### 5.1 Where passwords are stored
The passwords are stored in the SQLite DB at:
- `HostelBite_FullStack_Project/instance/hostelbite.db`

Specifically in the `users` table using the field `password_hash`.

### 5.2 How passwords are protected
The app uses Werkzeug password hashing:
- `generate_password_hash()` when creating demo users
- `check_password_hash()` during login

This protects plaintext password values from being easily readable if someone inspects the database.

### 5.3 JWT or token use
This app does not use JWT.

There is no:
- `jwt.encode()`
- `jwt.decode()`
- `Authorization: Bearer ...`
- refresh token
- access token expiry logic

### 5.4 Where tokens are stored on the client
There is no token-based auth implementation, so no JWT storage occurs.

The app relies on Flask session cookies instead.

### 5.5 Secret management and environment variables
Actual code:
```python
app.secret_key = os.environ.get("HOSTELBITE_SECRET", "change-this-demo-secret-before-deployment")
```

This is a weak production practice because:
- it falls back to a hardcoded value if the environment variable is missing
- the fallback key is visible in source code
- this would be unsafe for a real deployment

### 5.6 Logout and expiration
Logout works by clearing the session:
```python
session.clear()
```

There is no explicit session expiry configuration and no token expiration logic, because JWT is not used.

## 6) Documentation comparison

README claims:
- project uses hashed passwords
- there are student/admin roles
- demo users exist

Actual code confirms this.

However, the README is missing or incomplete in several important areas:

- no registration flow is documented
- no password policy is described
- no session timeout described
- no production deployment guidance beyond changing the secret key
- no SSR or CSRF explanation
- no mention that the app uses a local SQLite file in the project
- no mention that debug mode is enabled in the main executable block
- no mention that demo credentials are embedded in code and docs

This means the documentation is partially accurate but not complete for a real-world authentication system.

## 7) Security review and vulnerabilities

### Findings

1. Hardcoded fallback secret key
   - `app.secret_key = os.environ.get("HOSTELBITE_SECRET", "change-this-demo-secret-before-deployment")`
   - if no environment variable is set, the app uses a public-looking hardcoded secret

2. Demo credentials in code and README
   - the app seeds default accounts directly in the database
   - this is acceptable for a local demo, but not secure for production

3. Local SQLite database inside the project
   - `instance/hostelbite.db`
   - sensitive user data is stored in a file in the repo/project directory

4. No user registration page
   - there is no real sign-up process
   - new users cannot be created through the app

5. No password strength enforcement
   - there is no validation for password complexity or length

6. No rate limiting or account lockout
   - repeated login attempts are not throttled

7. Debug mode enabled
   ```python
   if __name__ == "__main__":
       app.run(debug=True)
   ```
   - debug mode should be disabled in production

8. No explicit secure cookies or HTTPS guidance
   - no `SESSION_COOKIE_SECURE` or `SESSION_COOKIE_HTTPONLY` configuration is shown

9. No CSRF token protection is visible
   - form submissions are not clearly protected against cross-site request forgery

10. No token expiration / session timeout
   - the app does not implement a proper security timeout strategy

## 8) Final deliverables

### Authentication architecture overview
This project uses a simple Flask-session authentication model.
- Flask app handles requests
- SQLite stores user records and password hashes
- role-based access restricts student vs admin functionality
- session data tracks the logged-in user
- routes use decorators to enforce auth checks

### Component-by-component explanation
- Frontend: HTML templates in `templates/`
- Backend: `app.py`
- Database: SQLite file in `instance/`
- Auth logic: `login()`, `login_required()`, `admin_required()`, `logout()`
- User model: `users` table with `username`, `password_hash`, `role`, `display_name`

### Step-by-step request flow
- user enters credentials
- request hits `/login`
- app looks up the user in SQLite
- password hash is checked
- session is populated
- app redirects to protected route
- route checks session
- admin route checks role
- logout clears session

### Credentials and token handling
- Passwords are hashed before storage.
- No JWT is used.
- Session cookie is used instead of a token string.
- Secret key is weakly managed by environment variable fallback.

### Security findings
- weak secret fallback
- local DB storage
- demo credentials baked into app
- no registration or password rules
- no timeout or secure cookie config
- debug mode enabled
- no token-based access control or proper session hardening

### Beginner-friendly summary
This project is a good beginner example of Flask authentication, but it is not a production-safe authentication system. It stores password hashes instead of plaintext, uses a login form and session to control access, and checks whether a user is logged in before allowing access to private pages. However, it lacks proper security controls such as strong secret management, secure cookie settings, admin/user registration, session timeout, and production deployment protection.

## 9) Final conclusion

The repository implements a basic session-based login system for a hostel mess portal. It authenticates users by checking a stored password hash and placing the user state into a Flask session. It enforces access control using decorator-based checks for login and admin-only routes.

However, the app is best described as a demo-grade authentication implementation, not a production-grade authentication system. The biggest issues are the hardcoded secret fallback, the local SQLite DB, the lack of registration and password rules, and the absence of modern security practices.

The existing project files were intentionally not modified or overwritten, as requested.

---

Created for review from the repository code only. This document does not contain any secret values beyond the project’s documented demo accounts names, which are not reproduced here in full.

## Exact source references
- `HostelBite_FullStack_Project/app.py`
- `HostelBite_FullStack_Project/README.md`
- `HostelBite_FullStack_Project/templates/login.html`
- `HostelBite_FullStack_Project/templates/base.html`
- `HostelBite_FullStack_Project/instance/hostelbite.db`

The final source of truth is the repository itself.
