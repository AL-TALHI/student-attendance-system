
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)

DB_FILE = 'attendance.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE,
                 password TEXT,
                 role TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 student_id INTEGER,
                 date TEXT,
                 status TEXT,
                 FOREIGN KEY(student_id) REFERENCES students(id))''')
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES ('admin', '1234', 'admin')")
    students = ['أحمد', 'سارة', 'محمد', 'ليلى', 'علي']
    for student in students:
        c.execute("INSERT OR IGNORE INTO students (name) VALUES (?)", (student,))
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            role = user[0]
            return redirect(url_for('dashboard', role=role))
        else:
            return "خطأ في تسجيل الدخول"
    return render_template('login.html')

@app.route('/dashboard/<role>')
def dashboard(role):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM students")
    students = c.fetchall()
    conn.close()
    return render_template('dashboard.html', students=students, role=role)

@app.route('/add_student', methods=['POST'])
def add_student():
    name = request.form['name']
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO students (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/attendance/<int:student_id>/<status>')
def mark_attendance(student_id, status):
    date = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)", (student_id, date, status))
    conn.commit()
    conn.close()
    return redirect(request.referrer)

@app.route('/reports')
def reports():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name FROM students")
    students = c.fetchall()
    report_data = []
    for student in students:
        student_id, name = student
        c.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='حاضر'", (student_id,))
        present_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='غائب'", (student_id,))
        absent_count = c.fetchone()[0]
        report_data.append({'name': name, 'present': present_count, 'absent': absent_count})
    conn.close()
    return render_template('reports.html', report_data=report_data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
