import sqlite3
from flask import Flask, jsonify, request, g

DB = "students.db"
app = Flask(__name__)


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
            """CREATE TABLE IF NOT EXISTS students (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT NOT NULL,
                   department TEXT NOT NULL,
                   email TEXT NOT NULL UNIQUE
               )"""
        )


def clean(data, partial=False):
    """Validate JSON body. Returns (fields, error_message)."""
    if not isinstance(data, dict):
        return None, "JSON body required"
    fields = {}
    for key in ("name", "department", "email"):
        val = data.get(key)
        if val is None:
            if partial:
                continue
            return None, f"'{key}' is required"
        if not isinstance(val, str) or not val.strip():
            return None, f"'{key}' must be a non-empty string"
        fields[key] = val.strip()
    if "email" in fields and "@" not in fields["email"]:
        return None, "'email' is not valid"
    return fields, None


def find(student_id):
    return get_db().execute(
        "SELECT * FROM students WHERE id = ?", (student_id,)
    ).fetchone()


@app.get("/students")
def list_students():
    rows = get_db().execute("SELECT * FROM students ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/students/<int:student_id>")
def get_student(student_id):
    row = find(student_id)
    if row is None:
        return jsonify(error="Student not found"), 404
    return jsonify(dict(row))


@app.post("/students")
def add_student():
    fields, err = clean(request.get_json(silent=True))
    if err:
        return jsonify(error=err), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO students (name, department, email) VALUES (?, ?, ?)",
            (fields["name"], fields["department"], fields["email"]),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="A student with this email already exists"), 409
    return jsonify(dict(find(cur.lastrowid))), 201


@app.put("/students/<int:student_id>")
def update_student(student_id):
    current = find(student_id)
    if current is None:
        return jsonify(error="Student not found"), 404
    fields, err = clean(request.get_json(silent=True), partial=True)
    if err:
        return jsonify(error=err), 400
    merged = {**dict(current), **fields}
    db = get_db()
    try:
        db.execute(
            "UPDATE students SET name=?, department=?, email=? WHERE id=?",
            (merged["name"], merged["department"], merged["email"], student_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="A student with this email already exists"), 409
    return jsonify(dict(find(student_id)))


@app.delete("/students/<int:student_id>")
def delete_student(student_id):
    if find(student_id) is None:
        return jsonify(error="Student not found"), 404
    db = get_db()
    db.execute("DELETE FROM students WHERE id = ?", (student_id,))
    db.commit()
    return jsonify(message="Student deleted")


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
