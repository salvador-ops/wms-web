from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "super_secret_key_123"

# 📁 Ruta correcta en Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventario.db")

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    con = get_db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventario (
        sku TEXT PRIMARY KEY,
        producto TEXT,
        ubicacion TEXT,
        stock INTEGER,
        minimo INTEGER DEFAULT 0
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

    # SOLO crear admin si no existe (NO borrar)
    cur.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (username, password) VALUES (?,?)",
            ("admin", "1234")
        )

    con.commit()
    con.close()

# 🔥 SOLO UNA VEZ AL INICIAR
init_db()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
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

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- PROTECCIÓN ----------------
def protegido():
    return "user" in session

# ---------------- HOME ----------------
@app.route("/")
def index():
    if not protegido():
        return redirect("/login")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM inventario")
    data = cur.fetchall()
    con.close()

    return render_template("index.html", data=data)

# ---------------- AGREGAR ----------------
@app.route("/agregar", methods=["POST"])
def agregar():
    if not protegido():
        return redirect("/login")

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
    if not protegido():
        return redirect("/login")

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM inventario")
    total_productos = cur.fetchone()[0]

    cur.execute("SELECT SUM(stock) FROM inventario")
    total_stock = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM inventario WHERE stock <= minimo")
    bajos = cur.fetchone()[0]

    con.close()

    return render_template("dashboard.html",
        total_productos=total_productos,
        total_stock=total_stock,
        bajos=bajos)

# ---------------- API ----------------
@app.route("/api/inventario")
def api():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM inventario")
    data = cur.fetchall()
    con.close()

    return jsonify(data)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)