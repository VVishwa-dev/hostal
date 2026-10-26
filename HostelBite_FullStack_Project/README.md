# HostelBite Full-Stack Mess Portal

A Flask + SQLite project with a single website and role-based access for students and hostel management.

## What happens to votes?
Votes are saved in `instance/hostelbite.db`, a local SQLite database. Because every account in this running app reads the same database, students and management see the same vote totals and charts. Unlike the old browser-only demo, votes are not stored only in localStorage.

## Features
- Student and admin sign-in with hashed passwords.
- Students can view the menu, vote for a day swap, and vote to request review/removal of a food item.
- One vote per account per day per category (one swap vote and one food-review vote for each day).
- Shared results page with bar charts and a pie chart, available to every signed-in user.
- Management-only admin page to edit any day's meals, swap two days, publish notices, inspect vote totals, and clear demo votes.
- After a management swap, a notice is published automatically, e.g. “Hello guys! Based on the student voting results, the Monday and Friday menus have been swapped.”
- SQLite database is created automatically on first run.

## Run it
### Windows
1. Install Python 3.10 or newer.
2. Extract this ZIP.
3. Double-click `run_windows.bat`.
4. When Flask starts, open `http://127.0.0.1:5000` in your browser.

### Mac
1. Install Python 3.10 or newer.
2. Extract the ZIP.
3. Open Terminal in this folder and run:
   ```bash
   chmod +x run_mac_linux.sh
   ./run_mac_linux.sh
   ```
4. Open `http://127.0.0.1:5000`.

You can also run manually:
```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

## Demo credentials
- Student: `student1` / `student123`
- Second student: `student2` / `student123`
- Hostel management: `admin` / `admin123`

These are demo accounts for testing. Change passwords and the Flask secret key before real deployment.

## How to test majority / charts
1. Sign in as `student1` and submit a swap vote or food-review vote.
2. Sign out and sign in as `student2`; cast another vote for the same request.
3. Open **Vote results** from the navigation. The charts and detailed table show the shared database counts.
4. Sign in as `admin` and open **Management**. Compare requests, then decide whether to swap/edit the menu.
5. After a swap, students see the published notice on the menu page.

Important: the app displays vote totals and leading requests, but management makes the final decision. A swap is not automatically executed from a student vote. A production deployment should add CSRF protection, rate limiting, password-change flows, stronger secret configuration, and hosting on a shared server so every device reaches the same app and database. The included local server is intended for a demo on one computer; multiple devices need a reachable hosted server or local network configuration.
