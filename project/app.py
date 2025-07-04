from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this securely

# ─── MySQL Configuration ───
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'student_portal'
mysql = MySQL(app)

# ─── File Upload Config ───
UPLOAD_FOLDER = 'static/uploads/materials'
ASSIGNMENT_FOLDER = 'static/uploads/assignments'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSIGNMENT_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ASSIGNMENT_FOLDER'] = ASSIGNMENT_FOLDER

# ─── Login Required Decorator ───

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('loggedin'):
            flash("Please login to access this page", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ─── Routes ───
@app.route('/')
@login_required
def home():
    name = session.get('name')
    return render_template('home.html', name=name)

@app.route('/login', methods=["GET", "POST"])
def login():
    if session.get('loggedin'):
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        cur.close()

        if user:
            session['loggedin'] = True
            session['user_id'] = user[0]
            session['name'] = user[1]
            session['username'] = user[3]
            session['standard'] = user[5]
            session['role'] = user[6]
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", "danger")

    return render_template('login.html')

@app.route('/register', methods=["GET", "POST"])
def register():
    if session.get('loggedin'):
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        name = request.form['name']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        standard = int(request.form['standard']) if role == 'student' else None

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO users (name, username, email, password, standard, role)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, username, email, password, standard, role))
        mysql.connection.commit()
        cur.close()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    role = session['role']
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif role == 'student':
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html')

@app.route('/teacher_dashboard')
@login_required
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher_dashboard.html')

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    return render_template('student_dashboard.html')

@app.route('/materials')
@login_required
def materials_home():
    return render_template('materials_home.html', standards=range(1, 13))

@app.route('/materials/<int:standard>')
@login_required
def materials_by_standard(standard):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM materials WHERE standard = %s ORDER BY uploaded_on DESC", (standard,))
    materials = cur.fetchall()
    cur.close()
    return render_template('materials_standard.html', materials=materials, standard=standard)

@app.route('/upload_material/<int:standard>', methods=['POST'])
@login_required
def upload_material(standard):
    if session['role'] not in ['admin', 'teacher']:
        return redirect(url_for('login'))

    title = request.form['title']
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO materials (title, filename, standard, uploaded_on) VALUES (%s, %s, %s, NOW())",
                    (title, filename, standard))
        mysql.connection.commit()
        cur.close()
        flash("Material uploaded successfully!", "success")
    return redirect(url_for('materials_by_standard', standard=standard))

@app.route('/delete_material/<int:id>/<int:standard>')
@login_required
def delete_material(id, standard):
    if session['role'] not in ['admin', 'teacher']:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT filename FROM materials WHERE id = %s", (id,))
    file = cur.fetchone()
    if file:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file['filename']))
        except:
            pass
    cur.execute("DELETE FROM materials WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Material deleted.", "info")
    return redirect(url_for('materials_by_standard', standard=standard))

@app.route('/assignments')
@login_required
def assignments_home():
    return render_template('assignments_home.html', standards=range(1, 13))

@app.route('/assignments/<int:standard>')
@login_required
def assignments_by_standard(standard):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM assignments WHERE standard = %s ORDER BY uploaded_on DESC", (standard,))
    assignments = cur.fetchall()
    cur.close()
    return render_template('assignments_list.html', assignments=assignments, standard=standard)

@app.route('/upload_assignment/<int:standard>', methods=['POST'])
@login_required
def upload_assignment(standard):
    if session['role'] not in ['admin', 'teacher']:
        return redirect(url_for('login'))

    title = request.form['title']
    file = request.files['file']
    if file and title:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['ASSIGNMENT_FOLDER'], filename))

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO assignments (title, filename, uploaded_by, standard)
            VALUES (%s, %s, %s, %s)
        """, (title, filename, session['role'], standard))
        mysql.connection.commit()
        cur.close()
        flash("Assignment uploaded successfully!", "success")
    return redirect(url_for('assignments_by_standard', standard=standard))

@app.route('/delete_assignment/<int:id>/<int:standard>')
@login_required
def delete_assignment(id, standard):
    if session['role'] not in ['admin', 'teacher']:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT filename FROM assignments WHERE id = %s", (id,))
    data = cur.fetchone()
    if data:
        file_path = os.path.join(app.config['ASSIGNMENT_FOLDER'], data['filename'])
        if os.path.exists(file_path):
            os.remove(file_path)
        cur.execute("DELETE FROM assignments WHERE id = %s", (id,))
        mysql.connection.commit()
    cur.close()
    flash("Assignment deleted.", "info")
    return redirect(url_for('assignments_by_standard', standard=standard))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/chat', methods=["GET", "POST"])
def chat():
    if request.method == "POST":
        name = request.form['name']
        message = request.form['message']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO counselor_messages (name, message) VALUES (%s, %s)", (name, message))
        mysql.connection.commit()
        cur.close()
        flash("Message sent successfully!", "success")
        return redirect(url_for('chat'))
    return render_template('chat.html')

@app.route('/attendance')
@login_required
def attendance():
    return render_template('attendance.html')

@app.route('/announcements')
@login_required
def announcements():
    return render_template('announcements.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

if __name__ == '__main__':
    app.run(debug=True)
