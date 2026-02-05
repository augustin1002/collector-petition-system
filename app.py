from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import smtplib
from email.message import EmailMessage
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "secret123"

# ================= TWILIO CONFIG (ADMIN ONLY) =================
ACCOUNT_SID = "AC4a15ec5fa370a84b6bf351ee031e7531"
AUTH_TOKEN = "b52e024aa0c2626a051ae3ba7dd2697d"
TWILIO_NUMBER = "+17169954855"
ADMIN_MOBILE = "+918870493566"   # VERIFIED ADMIN NUMBER ONLY

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ================= EMAIL FUNCTION =================
def send_admin_email(pid, name, mobile, place, department, problem):
    sender_email = "johnaugustinarul@gmail.com"
    sender_password = "phnccavuayodiwbc"
    admin_email = "augustinarulraja@gmail.com"

    msg = EmailMessage()
    msg["Subject"] = f"New Petition Received | ID {pid}"
    msg["From"] = sender_email
    msg["To"] = admin_email

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
        server.login(sender_email, sender_password)
        server.send_message(msg)

# ================= SMS FUNCTION (ADMIN ONLY) =================
def send_admin_sms(message):
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

        # Notify ADMIN ONLY
        send_admin_email(pid, name, mobile, place, department, problem)
        send_admin_sms(
            f"New Petition Received\nID: {pid}\nName: {name}\nPlace: {place}\nDept: {department}"
        )

        return render_template("success.html", pid=pid)

    return render_template("petition.html")

# ================= TRACK PETITION =================
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

    # Notify ADMIN ONLY
    send_admin_sms(
        f"Petition Update\nID: {pid}\nNew Status: {status}"
    )

    return redirect(url_for("admin_dashboard"))

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(debug=True)
