# ─────────────────────────────────────────────────────────────
#  Student Portal Web App (Flask + MySQL)
#  ------------------------------------------------------------
#  Features
#  • User registration / login (admin, teacher, student)
#  • Study‑material upload / view / download / delete (admin/teacher)
#  • Attendance: mark today, edit any date, role‑aware history view
# ─────────────────────────────────────────────────────────────

from flask import (
    Flask, render_template, request, redirect, session, flash,
    send_from_directory, abort
)
import mysql.connector
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os

# ───────── Flask App Config ─────────
app = Flask(__name__)
app.secret_key = "secret123"  # TODO: replace in production

UPLOAD_FOLDER = "uploads"
ALLOWED_EXT = {"pdf", "docx", "pptx", "xlsx", "csv"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ───────── MySQL Connection Details ─────────
DB_OPTS = dict(host="127.0.0.1", user="root", password="root")
DB_NAME = "student_portal"

# ───────── Database Initialisation ─────────

def initialize_database() -> None:
    """Create DB + tables if they don't exist."""
    db = mysql.connector.connect(**DB_OPTS)
    cur = db.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
    cur.execute(f"USE {DB_NAME}")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            student_identifier VARCHAR(30) UNIQUE NULL,
            role ENUM('admin','teacher','student') NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject_id INT,
            title VARCHAR(200),
            description TEXT,
            filename VARCHAR(300),
            uploaded_by INT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL,
            FOREIGN KEY (uploaded_by) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT NOT NULL,
            date DATE NOT NULL,
            status ENUM('present','absent') NOT NULL,
            marked_by INT,
            UNIQUE KEY uniq_student_date (student_id, date),
            FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (marked_by) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )

    db.commit()
    cur.close()
    db.close()


initialize_database()

# ───────── Helper Functions ─────────

def get_db():
    """Fresh connection for each call (simple)."""
    return mysql.connector.connect(database=DB_NAME, **DB_OPTS)


def query(sql: str, params: tuple = (), fetchone: bool = False, commit: bool = False):
    """Convenience wrapper around SELECT / INSERT / UPDATE."""
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    data = cur.fetchone() if fetchone else cur.fetchall()
    if commit:
        conn.commit()
    cur.close()
    conn.close()
    return data


def allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def get_all_students(limit: int = 30):
    return query(
        "SELECT id, name FROM users WHERE role='student' ORDER BY name LIMIT %s",
        (limit,)
    )

# ───────── Auth Routes ─────────
@app.route("/")
def home():
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = request.form
        name = form["name"].strip()
        email = form["email"].lower()
        password_hash = generate_password_hash(form["password"])
        role = form["role"]
        sid = form.get("student_identifier") if role == "student" else None

        if query("SELECT 1 FROM users WHERE email=%s", (email,), fetchone=True):
            flash("Email already registered", "warning")
            return redirect("/register")

        if role == "student" and not sid:
            flash("Student ID required for students", "warning")
            return redirect("/register")

        query(
            "INSERT INTO users (name, email, password, student_identifier, role) VALUES (%s,%s,%s,%s,%s)",
            (name, email, password_hash, sid, role), commit=True,
        )
        flash("Registration successful. Please log in.", "success")
        return redirect("/login")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].lower()
        pw = request.form["password"]
        user = query("SELECT * FROM users WHERE email=%s", (email,), fetchone=True)
        if user and check_password_hash(user["password"], pw):
            session.update(
                {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"],
                    "student_identifier": user.get("student_identifier"),
                }
            )
            return redirect("/dashboard")
        flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ───────── Dashboard ─────────
@app.route("/dashboard")
def dashboard():
    if "id" not in session:
        return redirect("/login")
    return render_template("dashboard.html", name=session["name"], role=session["role"])


# ───────── Study Materials ─────────
@app.route("/materials")
def materials():
    mats = query(
        """SELECT m.*, u.name AS uploader
           FROM materials m
           LEFT JOIN users u ON m.uploaded_by = u.id
           ORDER BY m.uploaded_at DESC"""
    )
    return render_template("materials.html", mats=mats, role=session.get("role"))


@app.route("/materials/upload", methods=["GET", "POST"])
def upload_material():
    if session.get("role") not in ("admin", "teacher"):
        flash("Unauthorized", "danger")
        return redirect("/materials")

    if request.method == "POST":
        title = request.form["title"].strip()
        desc = request.form["description"].strip()
        file = request.files.get("file")
        if not file or not allowed(file.filename):
            flash("Invalid file", "warning")
            return redirect(request.url)

        fname = datetime.now().strftime("%Y%m%d%H%M%S_") + secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, fname))
        query(
            "INSERT INTO materials (title, description, filename, uploaded_by) VALUES (%s,%s,%s,%s)",
            (title, desc, fname, session["id"]), commit=True,
        )
        flash("Material uploaded", "success")
        return redirect("/materials")

    return render_template("upload_material.html")


@app.route("/materials/<int:mid>/view")
def view_material(mid):
    mat = query("SELECT * FROM materials WHERE id=%s", (mid,), fetchone=True)
    if not mat:
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, mat["filename"], as_attachment=False)


@app.route("/materials/<int:mid>/download")
def download_material(mid):
    mat = query("SELECT * FROM materials WHERE id=%s", (mid,), fetchone=True)
    if not mat:
        abort(404)
    return send_from_directory(UPLOAD_FOLDER, mat["filename"], as_attachment=True)


@app.route("/materials/<int:mid>/delete", methods=["POST"])
def delete_material(mid):
    if session.get("role") not in ("admin", "teacher"):
        abort(403)
    mat = query("SELECT * FROM materials WHERE id=%s", (mid,), fetchone=True)
    if mat:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, mat["filename"]))
        except FileNotFoundError:
            pass
        query("DELETE FROM materials WHERE id=%s", (mid,), commit=True)
        flash("Deleted", "success")
    return redirect("/materials")

# ───────── Attendance Routes ─────────
@app.route("/mark-attendance", methods=["GET", "POST"])
def mark_attendance():
    if session.get("role") not in ("teacher", "admin"):
        return redirect("/dashboard")

    students = get_all_students()
    today = date.today()
    db = get_db()
    cur = db.cursor(dictionary=True)

    if request.method == "POST":
        teacher_id = session["id"]
        for stu in students:
            sid = stu["id"]
            status = request.form.get(f"attendance_{sid}")  # present/absent
            if status:
                cur.execute(
                    """
                    INSERT INTO attendance (student_id, date, status, marked_by)
                    VALUES (%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status), marked_by=VALUES(marked_by)
                    """,
                    (sid, today, status, teacher_id),
                )
        db.commit()
        cur.close()
        flash("Attendance saved!", "success")
        return redirect("/mark-attendance")

    # GET → existing marks to pre-select
    cur.execute("SELECT student_id, status FROM attendance WHERE date=%s", (today,))
    existing = {row["student_id"]: row["status"] for row in cur.fetchall()}
    cur.close()

    return render_template("attendance.html", students=students, existing=existing, selected_date=today)


@app.route("/edit-attendance", methods=["GET", "POST"])
def edit_attendance():
    if session.get("role") not in ("teacher", "admin"):
        return redirect("/dashboard")

    selected_date = request.args.get("date") or date.today().isoformat()
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Student list with status for selected_date
    cur.execute(
        """
        SELECT u.id, u.name, a.status
        FROM users u
        LEFT JOIN attendance a ON u.id = a.student_id AND a.date = %s
        WHERE u.role='student'
        ORDER BY u.name
        """,
        (selected_date,),
    )
    students = cur.fetchall()

    if request.method == "POST":
        teacher_id = session["id"]
        for stu in students:
            sid = stu["id"]
            status = request.form.get(f"attendance_{sid}")
            if status:
                cur.execute(
                    """
                    INSERT INTO attendance (student_id, date, status, marked_by)
                    VALUES (%s,%s,%s,%s)
                    ON DUPLICATE KEY UPDATE status=VALUES(status), marked_by=VALUES(marked_by)
                    """,
                    (sid, selected_date, status, teacher_id),
                )
        db.commit()
        cur.close()
        flash("Attendance updated!", "success")
        return redirect(f"/edit-attendance?date={selected_date}")

    cur.close()
    return render_template("edit_attendance.html", students=students, selected_date=selected_date)


@app.route("/attendance-history")
def attendance_history():
    role = session.get("role")
    uid = session.get("id")
    if not role:
        return redirect("/login")

    if role == "student":
        records = query(
            "SELECT date, status FROM attendance WHERE student_id=%s ORDER BY date DESC",
            (uid,),
        )
    else:
        records = query(
            """
            SELECT a.date, u.name, a.status
            FROM attendance a
            JOIN users u ON u.id = a.student_id
            ORDER BY a.date DESC, u.name
            """
        )

    return render_template("attendance_history.html", records=records, role=role)


# Convenience redirect so old link still works
@app.route("/my_attendance")
def my_attendance():
    return redirect("/attendance-history")

# ───────── Main ─────────
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
