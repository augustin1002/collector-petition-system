from flask import Flask, render_template, request, redirect, session, Response, url_for
import sqlite3, csv, os, smtplib
from io import StringIO
from datetime import datetime
from email.message import EmailMessage
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "collector_secret_key")


# ================= ENV =================
ACCOUNT_SID   = os.getenv("ACCOUNT_SID")
AUTH_TOKEN    = os.getenv("AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")
ADMIN_MOBILE  = os.getenv("ADMIN_MOBILE")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


# ================= DATABASE =================
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ================= EMAIL FUNCTION =================
def send_email(pid, name, mobile, place, dept, problem):

    if not EMAIL_USER:
        return

    try:
        msg = EmailMessage()
        msg["Subject"] = f"New Petition Received - ID {pid}"
        msg["From"] = EMAIL_USER
        msg["To"] = EMAIL_USER

        msg.set_content(f"""
NEW PETITION RECEIVED

ID          : {pid}
Name        : {name}
Mobile      : {mobile}
Place       : {place}
Department  : {dept}

Problem:
{problem}

Status : Pending
        """)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print("✅ EMAIL SENT")

    except Exception as e:
        print("❌ EMAIL ERROR:", e)


# ================= SMS FUNCTION =================
def send_sms(message):

    if not ACCOUNT_SID:
        return

    try:
        client = Client(ACCOUNT_SID, AUTH_TOKEN)

        client.messages.create(
            body=message,
            from_=TWILIO_NUMBER,
            to=ADMIN_MOBILE
        )

        print("✅ SMS SENT")

    except Exception as e:
        print("❌ SMS ERROR:", e)


# ================= PETITION PAGE =================
@app.route("/", methods=["GET", "POST"])
def petition():

    if request.method == "POST":

        created_date = datetime.now().strftime("%Y-%m-%d")

        name  = request.form["name"]
        mobile = request.form["mobile"]
        place = request.form["place"]
        dept  = request.form["department"]
        problem = request.form["problem"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO petitions
            (name, mobile, place, department, problem, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'Pending', ?)
        """, (name, mobile, place, dept, problem, created_date))

        conn.commit()
        pid = cur.lastrowid
        conn.close()

        # 📧 EMAIL
        send_email(pid, name, mobile, place, dept, problem)

        # 📱 SMS
        send_sms(f"New Petition\nID:{pid}\nName:{name}")

        return render_template("success.html", ID=pid)

    return render_template("petition.html")


# ================= TRACK =================
@app.route("/track", methods=["GET", "POST"])
def track():

    petition = None

    if request.method == "POST":
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM petitions WHERE id=?", (request.form["pid"],))
        petition = cur.fetchone()
        conn.close()

    return render_template("track.html", petition=petition)


# ================= ADMIN LOGIN =================
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        if request.form["username"] == "admin" and request.form["password"] == "Admin@123":
            session["role"] = "admin"

        elif request.form["username"] == "officer" and request.form["password"] == "officer123":
            session["role"] = "officer"

        else:
            return "Invalid Login"

        return redirect("/admin_dashboard")

    return render_template("admin_login.html")


# ================= DASHBOARD =================
@app.route("/admin_dashboard")
def admin_dashboard():

    if "role" not in session:
        return redirect("/admin_login")

    conn = get_db()
    cur = conn.cursor()

    petitions = cur.execute("SELECT * FROM petitions ORDER BY id DESC").fetchall()

    total = cur.execute("SELECT COUNT(*) FROM petitions").fetchone()[0]
    pending = cur.execute("SELECT COUNT(*) FROM petitions WHERE status='Pending'").fetchone()[0]
    progress = cur.execute("SELECT COUNT(*) FROM petitions WHERE status='In Progress'").fetchone()[0]
    solved = cur.execute("SELECT COUNT(*) FROM petitions WHERE status='Solved'").fetchone()[0]

    dept_data = cur.execute("""
        SELECT department, COUNT(*)
        FROM petitions
        GROUP BY department
    """).fetchall()

    departments = [row[0] for row in dept_data]
    dept_counts = [row[1] for row in dept_data]

    conn.close()

    return render_template("admin_dashboard.html",
                           petitions=petitions,
                           total=total,
                           pending=pending,
                           progress=progress,
                           solved=solved,
                           departments=departments,
                           dept_counts=dept_counts,
                           role=session["role"])


# ================= UPDATE STATUS =================
@app.route("/update/<int:pid>/<status>")
def update_status(pid, status):

    if "role" not in session:
        return redirect("/admin_login")

    status = status.replace("_", " ")

    conn = get_db()
    conn.execute("UPDATE petitions SET status=? WHERE id=?", (status, pid))
    conn.commit()
    conn.close()

    # 📱 SMS ON STATUS CHANGE
    send_sms(f"Petition Update\nID:{pid}\nStatus:{status}")

    return redirect("/admin_dashboard")


# ================= EXPORT CSV =================
@app.route("/export_csv")
def export_csv():

    if "role" not in session:
        return redirect("/admin_login")

    conn = get_db()
    cur = conn.cursor()
    data = cur.execute("SELECT * FROM petitions").fetchall()
    conn.close()

    si = StringIO()
    writer = csv.writer(si)

    writer.writerow(["ID","Name","Mobile","Place","Department","Problem","Status","Date"])

    for row in data:
        writer.writerow(tuple(row))

    return Response(si.getvalue(),
                    mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=petitions_report.csv"})


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/admin_login")


if __name__ == "__main__":
    app.run(debug=True)
