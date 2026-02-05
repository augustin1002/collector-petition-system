from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import smtplib
import os
from email.message import EmailMessage
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "secret123"

# ========== ENV VARIABLES ==========
ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
ADMIN_MOBILE  = os.getenv("ADMIN_MOBILE")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# ================= EMAIL FUNCTION =================
def send_admin_email(pid, name, mobile, place, department, problem):
    msg = EmailMessage()
    msg["Subject"] = f"New Petition Received | ID {pid}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER   # admin email

    msg.set_content(f"""
COLLECTOR OFFICE - NEW PETITION

Petition ID : {pid}
Name        : {name}
Mobile      : {mobile}
Place       : {place}
Department  : {department}

Problem:
{problem}

Status: Pending
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

# ================= SMS FUNCTION =================
def send_admin_sms(message):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.messages.create(
        body=message,
        from_=TWILIO_NUMBER,
        to=ADMIN_MOBILE
    )

# ================= PETITION FORM =================
@app.route("/", methods=["GET", "POST"])
def petition():
    if request.method == "POST":
        name = request.form["name"]
        mobile = request.form["mobile"]
        place = request.form["place"]
        department = request.form["department"]
        problem = request.form["problem"]

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO petitions (name, mobile, place, department, problem, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
        """, (name, mobile, place, department, problem))

        pid = cur.lastrowid
        conn.commit()
        conn.close()

        send_admin_email(pid, name, mobile, place, department, problem)
        send_admin_sms(
            f"New Petition\nID:{pid}\nName:{name}\nPlace:{place}\nDept:{department}"
        )

        return render_template("success.html", pid=pid)

    return render_template("petition.html")

# ================= TRACK =================
@app.route("/track", methods=["GET", "POST"])
def track():
    petition = None
    if request.method == "POST":
        pid = request.form["pid"]
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()
        cur.execute("SELECT * FROM petitions WHERE id=?", (pid,))
        petition = cur.fetchone()
        conn.close()

    return render_template("track.html", petition=petition)

# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin":
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid Login"

    return render_template("admin_login.html")

# ================= ADMIN DASHBOARD =================
@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM petitions")
    data = cur.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", petitions=data)

# ================= UPDATE STATUS =================
@app.route("/update/<int:pid>/<status>")
def update_status(pid, status):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    status = status.replace("_", " ")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("UPDATE petitions SET status=? WHERE id=?", (status, pid))
    conn.commit()
    conn.close()

    send_admin_sms(
        f"Petition Update\nID:{pid}\nStatus:{status}"
    )

    return redirect(url_for("admin_dashboard"))

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(debug=True)
