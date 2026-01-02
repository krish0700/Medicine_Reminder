from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "esp32_secret_key"

# ---------------- FILE UPLOAD ----------------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            name TEXT,
            mobile TEXT,
            email TEXT,
            weight TEXT,
            gender TEXT,
            photo TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------- INDEX / LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid username or password"

    return render_template("index.html", error=error)

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            conn = sqlite3.connect("users.db")
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (username, password) VALUES (?,?)",
                (username, password)
            )
            conn.commit()
            conn.close()

            session["user"] = username
            return redirect(url_for("profile"))

        except:
            error = "Username already exists"

    return render_template("register.html", error=error)

# ---------------- PROFILE (EDIT) ----------------
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        photo = request.files.get("photo")
        filename = None

        if photo and photo.filename != "":
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        conn = sqlite3.connect("users.db")
        cur = conn.cursor()

        if filename:
            cur.execute("""
                UPDATE users SET
                name=?, mobile=?, email=?, weight=?, gender=?, photo=?
                WHERE username=?
            """, (
                request.form["name"],
                request.form["mobile"],
                request.form["email"],
                request.form["weight"],
                request.form["gender"],
                filename,
                session["user"]
            ))
        else:
            cur.execute("""
                UPDATE users SET
                name=?, mobile=?, email=?, weight=?, gender=?
                WHERE username=?
            """, (
                request.form["name"],
                request.form["mobile"],
                request.form["email"],
                request.form["weight"],
                request.form["gender"],
                session["user"]
            ))

        conn.commit()
        conn.close()
        return redirect(url_for("profile2"))

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT name, mobile, email, weight, gender, photo
        FROM users WHERE username=?
    """, (session["user"],))
    row = cur.fetchone()
    conn.close()

    user = {
        "name": row[0] or "",
        "mobile": row[1] or "",
        "email": row[2] or "",
        "weight": row[3] or "",
        "gender": row[4] or "",
        "photo": row[5] or ""
    }

    return render_template("profile.html", user=user)

# ---------------- PROFILE VIEW ----------------
@app.route("/profile2")
def profile2():
    if "user" not in session:
        return redirect(url_for("index"))

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("""
        SELECT name, mobile, email, weight, gender, photo
        FROM users WHERE username=?
    """, (session["user"],))
    row = cur.fetchone()
    conn.close()

    user = {
        "full_name": row[0] if row[0] else session["user"],
        "mobile": row[1] or "",
        "email": row[2] or "",
        "weight": row[3] or "",
        "gender": row[4] or "",
        "photo": "/static/uploads/" + row[5] if row[5] else "/static/default.jpg"
    }

    return render_template("profile2.html", user=user)

# ---------------- DASHBOARD (UPDATED) ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        esp_ip = request.form.get("esp_ip")
        if esp_ip:
            return redirect(f"http://{esp_ip}")

    # 🔽 FETCH USER PHOTO
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT photo FROM users WHERE username=?", (session["user"],))
    row = cur.fetchone()
    conn.close()

    user_photo = row[0] if row and row[0] else None

    return render_template(
        "dashboard.html",
        user=session["user"],
        user_photo="/static/uploads/" + user_photo if user_photo else "/static/default.jpg"
    )

# ---------------- DELETE ACCOUNT ----------------
@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user" not in session:
        return redirect(url_for("index"))

    conn = sqlite3.connect("users.db")
    cur = conn.cursor()

    cur.execute("SELECT photo FROM users WHERE username=?", (session["user"],))
    photo = cur.fetchone()

    if photo and photo[0]:
        path = os.path.join(app.config["UPLOAD_FOLDER"], photo[0])
        if os.path.exists(path):
            os.remove(path)

    cur.execute("DELETE FROM users WHERE username=?", (session["user"],))
    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for("index"))

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
