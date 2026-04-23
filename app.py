from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventario.db")

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def ensure_db():
    con = get_db()
    cur = con.cursor()

    # 👇 CREA TODO SIEMPRE (CLAVE)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventario (
        sku TEXT PRIMARY KEY,
        producto TEXT,
        ubicacion TEXT,
        stock INTEGER,
        minimo INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        sku TEXT,
        tipo TEXT,
        cantidad INTEGER
    )
    """)

    # 👇 CREA ADMIN SIEMPRE SI NO EXISTE
    cur.execute("SELECT * FROM usuarios WHERE username=?", ("admin",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (username, password) VALUES (?,?)",
            ("admin", "1234")
        )

    con.commit()
    con.close()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    ensure_db()  # 🔥 AQUÍ ESTÁ LA CLAVE

    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        con = get_db()
        cur = con.cursor()

        cur.execute(
            "SELECT * FROM usuarios WHERE username=? AND password=?",
            (user, pwd)
        )
        data = cur.fetchone()
        con.close()

        if data:
            session["user"] = user
            return redirect("/")
        else:
            return "❌ Usuario o contraseña incorrectos"

    return render_template("login.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- HOME ----------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")

    ensure_db()

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM inventario")
    data = cur.fetchall()
    con.close()

    return render_template("index.html", data=data)

# ---------------- AGREGAR ----------------
@app.route("/agregar", methods=["POST"])
def agregar():
    if "user" not in session:
        return redirect("/login")

    ensure_db()

    con = get_db()
    cur = con.cursor()

    cur.execute("INSERT INTO inventario VALUES (?,?,?,?,?)", (
        request.form["sku"],
        request.form["producto"],
        request.form["ubicacion"],
        int(request.form["stock"]),
        int(request.form["minimo"])
    ))

    con.commit()
    con.close()

    return redirect("/")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    ensure_db()

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM inventario")
    total = cur.fetchone()[0]

    cur.execute("SELECT SUM(stock) FROM inventario")
    stock = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM inventario WHERE stock <= minimo")
    bajos = cur.fetchone()[0]

    con.close()

    return f"Productos: {total} | Stock: {stock} | Bajo stock: {bajos}"

# ---------------- API ----------------
@app.route("/api/inventario")
def api():
    ensure_db()

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM inventario")
    data = cur.fetchall()
    con.close()

    return jsonify(data)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)