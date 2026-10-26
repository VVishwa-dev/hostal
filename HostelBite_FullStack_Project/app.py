from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from functools import wraps
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "hostelbite.db")
app = Flask(__name__)
app.secret_key = os.environ.get("HOSTELBITE_SECRET", "change-this-demo-secret-before-deployment")

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEALS = {
    "Monday": ["Idli, sambar & chutney", "Rice, dal, vegetables & curd", "Chapati, paneer curry"],
    "Tuesday": ["Poha & banana", "Jeera rice, chana masala", "Dosa, sambar & chutney"],
    "Wednesday": ["Upma & chutney", "Rice, rasam, poriyal", "Veg pulao & raita"],
    "Thursday": ["Masala dosa", "Rice, sambar, beans poriyal", "Chapati, mixed veg curry"],
    "Friday": ["Pongal & sambar", "Veg biryani & raita", "Rice, dal fry & salad"],
    "Saturday": ["Poori & potato masala", "Curd rice, veg fry", "Parotta & kurma"],
    "Sunday": ["Bread, jam & omelette option", "Special meals / veg thali", "Tomato rice & raita"],
}
MEAL_TYPES = ["Breakfast", "Lunch", "Dinner"]

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('student','admin')),
          display_name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS menu(
          day TEXT PRIMARY KEY, breakfast TEXT NOT NULL, lunch TEXT NOT NULL, dinner TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS votes(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          day TEXT NOT NULL, category TEXT NOT NULL CHECK(category IN ('swap','remove')),
          target_day TEXT, meal_type TEXT, meal_name TEXT, created_at TEXT NOT NULL,
          UNIQUE(user_id, day, category)
        );
        CREATE TABLE IF NOT EXISTS announcements(
          id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT NOT NULL, created_at TEXT NOT NULL,
          created_by INTEGER REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS swap_requests(
          id INTEGER PRIMARY KEY AUTOINCREMENT, day_a TEXT NOT NULL, day_b TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL
        );
        """)
        for day, items in MEALS.items():
            db.execute("INSERT OR IGNORE INTO menu(day,breakfast,lunch,dinner) VALUES(?,?,?,?)", (day,*items))
        seed_users = [
          ("student1", "student123", "student", "Demo Student"),
          ("student2", "student123", "student", "Demo Student Two"),
          ("admin", "admin123", "admin", "Mess Manager")
        ]
        for username, password, role, display_name in seed_users:
            db.execute("INSERT OR IGNORE INTO users(username,password_hash,role,display_name) VALUES(?,?,?,?)",
                       (username, generate_password_hash(password), role, display_name))
        if db.execute("SELECT COUNT(*) FROM announcements").fetchone()[0] == 0:
            db.execute("INSERT INTO announcements(message,created_at) VALUES(?,?)",
                       ("Welcome! Check the weekly menu and cast your vote.", datetime.now().isoformat(timespec="minutes")))

init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

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

@app.context_processor
def inject_user():
    return {"current_user": session.get("display_name"), "current_role": session.get("role")}

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("menu"))
    return render_template("landing.html")

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/menu")
@login_required
def menu():
    with connect() as db:
        rows = db.execute("SELECT * FROM menu ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END").fetchall()
        announcements = db.execute("SELECT * FROM announcements ORDER BY id DESC LIMIT 5").fetchall()
        votes = db.execute("SELECT day,category,COUNT(*) count FROM votes GROUP BY day,category").fetchall()
    counts = {(r["day"],r["category"]):r["count"] for r in votes}
    return render_template("menu.html", menu_rows=rows, days=DAYS, meal_types=MEAL_TYPES, announcements=announcements, counts=counts)

@app.route("/vote", methods=["POST"])
@login_required
def vote():
    if session.get("role") != "student":
        flash("Management accounts do not cast student votes.", "error")
        return redirect(url_for("menu"))
    category = request.form.get("category")
    day = request.form.get("day")
    if category not in ("swap","remove") or day not in DAYS:
        flash("Please choose a valid voting option.", "error")
        return redirect(url_for("menu"))
    target_day = request.form.get("target_day") if category == "swap" else None
    meal_type = request.form.get("meal_type") if category == "remove" else None
    meal_name = request.form.get("meal_name","").strip() if category == "remove" else None
    if category == "swap" and (target_day not in DAYS or target_day == day):
        flash("Choose two different days to request a swap.", "error")
        return redirect(url_for("menu"))
    if category == "remove" and (meal_type not in MEAL_TYPES or not meal_name):
        flash("Choose a meal type and enter the food item.", "error")
        return redirect(url_for("menu"))
    try:
        with connect() as db:
            db.execute("""INSERT INTO votes(user_id,day,category,target_day,meal_type,meal_name,created_at)
                          VALUES(?,?,?,?,?,?,?)""",
                       (session["user_id"],day,category,target_day,meal_type,meal_name,datetime.now().isoformat(timespec="minutes")))
        flash("Your vote was recorded. Results are visible to everyone signed in.", "success")
    except sqlite3.IntegrityError:
        flash("You have already voted in this category for that day. One vote per category per day is allowed.", "error")
    return redirect(url_for("results"))

@app.route("/results")
@login_required
def results():
    with connect() as db:
        rows = db.execute("SELECT day,category,target_day,meal_type,meal_name,COUNT(*) votes FROM votes GROUP BY day,category,target_day,meal_type,meal_name ORDER BY votes DESC").fetchall()
        total = db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    return render_template("results.html", results=rows, total=total, days=DAYS)

@app.route("/api/results")
@login_required
def api_results():
    with connect() as db:
        rows = db.execute("SELECT day,category,target_day,meal_type,meal_name,COUNT(*) votes FROM votes GROUP BY day,category,target_day,meal_type,meal_name ORDER BY votes DESC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/admin")
@admin_required
def admin():
    with connect() as db:
        rows = db.execute("SELECT * FROM menu ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END").fetchall()
        votes = db.execute("SELECT day,category,target_day,meal_type,meal_name,COUNT(*) votes FROM votes GROUP BY day,category,target_day,meal_type,meal_name ORDER BY votes DESC").fetchall()
        total = db.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    return render_template("admin.html", menu_rows=rows, days=DAYS, meal_types=MEAL_TYPES, results=votes, total=total)

@app.route("/admin/menu", methods=["POST"])
@admin_required
def edit_menu():
    day = request.form.get("day")
    if day not in DAYS:
        flash("Invalid day.", "error"); return redirect(url_for("admin"))
    items = [request.form.get(k,"").strip() for k in ("breakfast","lunch","dinner")]
    if not all(items):
        flash("Please fill in all three meal fields.", "error"); return redirect(url_for("admin"))
    with connect() as db:
        db.execute("UPDATE menu SET breakfast=?,lunch=?,dinner=? WHERE day=?", (*items,day))
        db.execute("INSERT INTO announcements(message,created_at,created_by) VALUES(?,?,?)",
                   (f"Menu update: {day}'s menu has been updated by hostel management.", datetime.now().isoformat(timespec="minutes"), session["user_id"]))
    flash(f"{day}'s menu updated.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/swap", methods=["POST"])
@admin_required
def admin_swap():
    a, b = request.form.get("day_a"), request.form.get("day_b")
    if a not in DAYS or b not in DAYS or a == b:
        flash("Choose two different valid days.", "error"); return redirect(url_for("admin"))
    with connect() as db:
        first = db.execute("SELECT breakfast,lunch,dinner FROM menu WHERE day=?", (a,)).fetchone()
        second = db.execute("SELECT breakfast,lunch,dinner FROM menu WHERE day=?", (b,)).fetchone()
        db.execute("UPDATE menu SET breakfast=?,lunch=?,dinner=? WHERE day=?", (*second,a))
        db.execute("UPDATE menu SET breakfast=?,lunch=?,dinner=? WHERE day=?", (*first,b))
        db.execute("INSERT INTO announcements(message,created_at,created_by) VALUES(?,?,?)",
                   (f"Hello guys! Based on the student voting results, the {a} and {b} menus have been swapped. Thank you for voting!", datetime.now().isoformat(timespec="minutes"), session["user_id"]))
    flash(f"{a} and {b} menus have been swapped and an announcement was published.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/announce", methods=["POST"])
@admin_required
def announce():
    message = request.form.get("message","").strip()
    if not message:
        flash("Please enter an announcement.", "error"); return redirect(url_for("admin"))
    with connect() as db:
        db.execute("INSERT INTO announcements(message,created_at,created_by) VALUES(?,?,?)",
                   (message, datetime.now().isoformat(timespec="minutes"), session["user_id"]))
    flash("Announcement published.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/clear-votes", methods=["POST"])
@admin_required
def clear_votes():
    with connect() as db: db.execute("DELETE FROM votes")
    flash("All voting data was cleared.", "success")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)
