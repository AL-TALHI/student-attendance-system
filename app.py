
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
from datetime import date, datetime
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)
app.secret_key = "secret123"
DB_PATH = "attendance.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')
    # students
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        class_name TEXT,
        student_number TEXT UNIQUE,
        active INTEGER DEFAULT 1
    )''')
    # attendance
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        note TEXT,
        created_at TEXT DEFAULT (DATETIME('now')),
        FOREIGN KEY(student_id) REFERENCES students(id)
    )''')
    # default admin
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', 'admin123', 'admin'))
    # sample students if empty
    c.execute("SELECT id FROM students LIMIT 1")
    if not c.fetchone():
        sample = [
            ('أحمد محمد','Grade 1','S001'),
            ('سارة خالد','Grade 1','S002'),
            ('محمد علي','Grade 1','S003'),
        ]
        for name, cls, num in sample:
            c.execute("INSERT INTO students (name, class_name, student_number) VALUES (?, ?, ?)", (name, cls, num))
    conn.commit()
    conn.close()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

if not os.path.exists(DB_PATH):
    init_db()

# login
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        conn = get_conn()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password)).fetchone()
        conn.close()
        if user:
            role = user['role']
            return redirect(url_for('dashboard', role=role))
        flash('اسم المستخدم أو كلمة المرور خاطئة')
    return render_template('login.html')

# dashboard - shows students and link to attendance page
@app.route('/dashboard')
def dashboard():
    role = request.args.get('role','teacher')
    conn = get_conn()
    students = conn.execute("SELECT * FROM students WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return render_template('dashboard.html', students=students, role=role)

# attendance page (GET show, POST submit)
@app.route('/attendance', methods=['GET','POST'])
def attendance():
    conn = get_conn()
    if request.method == 'POST':
        today = request.form.get('date', date.today().isoformat())
        for key, val in request.form.items():
            if key in ['date','note_all']:
                continue
            try:
                sid = int(key)
            except:
                continue
            status = val
            note = request.form.get(f'note_{sid}','')
            conn.execute("INSERT INTO attendance (student_id, date, status, note) VALUES (?, ?, ?, ?)",
                         (sid, today, status, note))
        conn.commit()
        conn.close()
        flash('تم تسجيل الحضور بنجاح')
        return redirect(url_for('dashboard'))
    else:
        students = conn.execute("SELECT * FROM students WHERE active=1 ORDER BY name").fetchall()
        conn.close()
        return render_template('attendance.html', students=students, today=date.today().isoformat())

# reports view
@app.route('/reports', methods=['GET','POST'])
def reports():
    conn = get_conn()
    start = request.args.get('start','')
    end = request.args.get('end','')
    student_id = request.args.get('student','')
    query = """SELECT a.id, a.date, s.name, a.status, a.note FROM attendance a
               JOIN students s ON a.student_id = s.id WHERE 1=1 """
    params = []
    if start:
        query += " AND date(a.date) >= date(?) "
        params.append(start)
    if end:
        query += " AND date(a.date) <= date(?) "
        params.append(end)
    if student_id:
        query += " AND s.id = ? "
        params.append(student_id)
    query += " ORDER BY a.date DESC"
    records = conn.execute(query, params).fetchall()
    students = conn.execute("SELECT id, name FROM students WHERE active=1 ORDER BY name").fetchall()
    conn.close()
    return render_template('reports.html', records=records, students=students, start=start, end=end, student_id=student_id)

# download PDF of current filtered report
@app.route('/download_pdf')
def download_pdf():
    start = request.args.get('start','')
    end = request.args.get('end','')
    student_id = request.args.get('student','')
    conn = get_conn()
    query = """SELECT a.date, s.name, a.status, a.note FROM attendance a
               JOIN students s ON a.student_id = s.id WHERE 1=1 """
    params = []
    if start:
        query += " AND date(a.date) >= date(?) "
        params.append(start)
    if end:
        query += " AND date(a.date) <= date(?) "
        params.append(end)
    if student_id:
        query += " AND s.id = ? "
        params.append(student_id)
    query += " ORDER BY a.date DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    # create PDF using FPDF (fpdf2)
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    try:
        pdf.add_page()
        # use default font; for Arabic display you'll need a TTF font registered - keeping simple for now
        pdf.set_font('Arial', size=12)
        pdf.cell(0, 8, txt='تقرير الحضور', ln=1, align='C')
        pdf.ln(4)
        pdf.set_font('Arial', size=10)
        for r in rows:
            line = f"{r['date']}  -  {r['name']}  -  {r['status']}"
            pdf.cell(0, 7, txt=line, ln=1, align='R')
        bio = BytesIO()
        pdf.output(bio)
        bio.seek(0)
        return send_file(bio, download_name='attendance_report.pdf', as_attachment=True)
    except Exception as e:
        return f"PDF error: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
