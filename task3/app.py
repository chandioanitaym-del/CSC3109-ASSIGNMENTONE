import datetime
import os
import sqlite3
from functools import wraps

import jwt
from flask import Flask, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

DB = "employees.db"
SECRET = os.environ.get("SECRET_KEY", "dev-only-change-me-please-0123456789")
app = Flask(__name__)


# ---------------------------------------------------------------- database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT NOT NULL UNIQUE,
                   password_hash TEXT NOT NULL,
                   role TEXT NOT NULL CHECK (role IN ('employee', 'admin'))
               )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS employees (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL,
                   position TEXT NOT NULL,
                   department TEXT NOT NULL,
                   email TEXT NOT NULL UNIQUE
               )"""
        )
        if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            # Demo accounts for the classroom exercise only.
            con.executemany(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                [
                    ("admin", generate_password_hash("admin123"), "admin"),
                    ("employee", generate_password_hash("emp123"), "employee"),
                ],
            )
        if con.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO employees (name, position, department, email) VALUES (?, ?, ?, ?)",
                [
                    ("Ayesha Khan", "Software Engineer", "IT", "ayesha@example.com"),
                    ("Bilal Ahmed", "Accountant", "Finance", "bilal@example.com"),
                    ("Sana Ali", "HR Officer", "HR", "sana@example.com"),
                ],
            )


# ----------------------------------------------------- auth / authorization
def login_required(fn):
    """AUTHENTICATION: who are you? Missing/bad token -> 401."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Authentication required. Log in at POST /login."), 401
        try:
            g.user = jwt.decode(header[7:], SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify(error="Token expired. Please log in again."), 401
        except jwt.InvalidTokenError:
            return jsonify(error="Invalid token."), 401
        return fn(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    """AUTHORIZATION: are you allowed? Wrong role -> 403."""

    def decorator(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            if g.user["role"] not in roles:
                return jsonify(error=f"Forbidden. Requires role: {', '.join(roles)}."), 403
            return fn(*args, **kwargs)

        return login_required(inner)

    return decorator


@app.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username, password = data.get("username"), data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify(error="username and password are required"), 400
    user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify(error="Invalid credentials"), 401
    token = jwt.encode(
        {
            "username": user["username"],
            "role": user["role"],
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
        },
        SECRET,
        algorithm="HS256",
    )
    return jsonify(token=token, role=user["role"])


# --------------------------------------------------------------- employees
def clean(data, partial=False):
    if not isinstance(data, dict):
        return None, "JSON body required"
    fields = {}
    for key in ("name", "position", "department", "email"):
        val = data.get(key)
        if val is None:
            if partial:
                continue
            return None, f"'{key}' is required"
        if not isinstance(val, str) or not val.strip():
            return None, f"'{key}' must be a non-empty string"
        fields[key] = val.strip()
    return fields, None


def find(emp_id):
    return get_db().execute("SELECT * FROM employees WHERE id = ?", (emp_id,)).fetchone()


@app.get("/employees")
@roles_required("employee", "admin")
def list_employees():
    rows = get_db().execute("SELECT * FROM employees ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/employees/<int:emp_id>")
@roles_required("employee", "admin")
def get_employee(emp_id):
    row = find(emp_id)
    if row is None:
        return jsonify(error="Employee not found"), 404
    return jsonify(dict(row))


@app.post("/employees")
@roles_required("admin")
def add_employee():
    fields, err = clean(request.get_json(silent=True))
    if err:
        return jsonify(error=err), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO employees (name, position, department, email) VALUES (?, ?, ?, ?)",
            (fields["name"], fields["position"], fields["department"], fields["email"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="An employee with this email already exists"), 409
    return jsonify(dict(find(cur.lastrowid))), 201


@app.put("/employees/<int:emp_id>")
@roles_required("admin")
def update_employee(emp_id):
    current = find(emp_id)
    if current is None:
        return jsonify(error="Employee not found"), 404
    fields, err = clean(request.get_json(silent=True), partial=True)
    if err:
        return jsonify(error=err), 400
    m = {**dict(current), **fields}
    db = get_db()
    try:
        db.execute(
            "UPDATE employees SET name=?, position=?, department=?, email=? WHERE id=?",
            (m["name"], m["position"], m["department"], m["email"], emp_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="An employee with this email already exists"), 409
    return jsonify(dict(find(emp_id)))


@app.delete("/employees/<int:emp_id>")
@roles_required("admin")
def delete_employee(emp_id):
    if find(emp_id) is None:
        return jsonify(error="Employee not found"), 404
    db = get_db()
    db.execute("DELETE FROM employees WHERE id = ?", (emp_id,))
    db.commit()
    return jsonify(message="Employee deleted")


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5002)
