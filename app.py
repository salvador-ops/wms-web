from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventario.db")

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def ensure_db():
    con = get_db()
    cur = con.cursor()

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

    # crear admin si no existe
    cur.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username,password) VALUES (?,?)", ("admin","1234"))

    con.commit()
    con.close()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    ensure_db()

    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        con = get_db()
        cur = con.cursor()

        cur.execute("SELECT * FROM usuarios WHERE username=? AND password=?", (user,pwd))
        data = cur.fetchone()
        con.close()

        if data:
            session["user"] = user
            return redirect("/")
        else:
            return "❌ Usuario incorrecto"

    return render_template("login.html")

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

# ---------------- AGREGAR PRODUCTO ----------------
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

# ---------------- MOVIMIENTOS ----------------
@app.route("/movimiento/<tipo>", methods=["POST"])
def movimiento(tipo):
    if "user" not in session:
        return redirect("/login")

    ensure_db()

    sku = request.form["sku"]
    cantidad = int(request.form["cantidad"])

    con = get_db()
    cur = con.cursor()

    cur.execute("SELECT stock FROM inventario WHERE sku=?", (sku,))
    row = cur.fetchone()

    if not row:
        con.close()
        return "❌ SKU no existe"

    stock = row[0]

    if tipo == "entrada":
        stock += cantidad

    elif tipo == "salida":
        if cantidad > stock:
            con.close()
            return "❌ Stock insuficiente"
        stock -= cantidad

    cur.execute("UPDATE inventario SET stock=? WHERE sku=?", (stock, sku))

    cur.execute("INSERT INTO movimientos (fecha, sku, tipo, cantidad) VALUES (?,?,?,?)",
                (datetime.now(), sku, tipo, cantidad))

    con.commit()
    con.close()

    return redirect("/")

# ---------------- HISTORIAL ----------------
@app.route("/historial")
def historial():
    if "user" not in session:
        return redirect("/login")

    ensure_db()

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM movimientos ORDER BY fecha DESC")
    data = cur.fetchall()
    con.close()

    return render_template("historial.html", data=data)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)