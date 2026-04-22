from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "clave_super_secreta"

# ---------------- DB ----------------
def db():
    return sqlite3.connect("inventario.db")

def init_db():
    con = db()
    cur = con.cursor()

    # Inventario
    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventario (
        sku TEXT PRIMARY KEY,
        producto TEXT,
        ubicacion TEXT,
        stock INTEGER,
        minimo INTEGER
    )
    """)

    # Movimientos
    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        sku TEXT,
        tipo TEXT,
        cantidad INTEGER
    )
    """)

    # Usuarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    # Crear usuario admin si no existe
    cur.execute("SELECT * FROM usuarios WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO usuarios (username, password) VALUES (?,?)", ("admin", "1234"))

    con.commit()
    con.close()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["username"]
        pwd = request.form["password"]

        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM usuarios WHERE username=? AND password=?", (user,pwd))
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
    session.pop("user", None)
    return redirect("/login")

# ---------------- PROTECCIÓN ----------------
def protegido():
    if "user" not in session:
        return False
    return True

# ---------------- INVENTARIO ----------------
@app.route("/")
def index():
    if not protegido():
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM inventario")
    data = cur.fetchall()
    con.close()

    return render_template("index.html", data=data)

# ---------------- MOVIMIENTOS ----------------
@app.route("/movimiento/<tipo>", methods=["GET","POST"])
def movimiento(tipo):
    if not protegido():
        return redirect("/login")

    if request.method == "POST":
        sku = request.form["sku"]
        cantidad = int(request.form["cantidad"])

        con = db()
        cur = con.cursor()

        cur.execute("SELECT stock FROM inventario WHERE sku=?", (sku,))
        row = cur.fetchone()

        if row:
            stock = row[0]

            if tipo == "entrada":
                stock += cantidad
            elif tipo == "salida" and stock >= cantidad:
                stock -= cantidad

            cur.execute("UPDATE inventario SET stock=? WHERE sku=?", (stock, sku))
            cur.execute("INSERT INTO movimientos VALUES (NULL,?,?,?,?)",
                        (datetime.now(), sku, tipo, cantidad))

            con.commit()

        con.close()
        return redirect("/")

    return render_template("movimiento.html", tipo=tipo)

# ---------------- HISTORIAL ----------------
@app.route("/historial")
def historial():
    if not protegido():
        return redirect("/login")

    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM movimientos ORDER BY fecha DESC")
    data = cur.fetchall()
    con.close()

    return render_template("historial.html", data=data)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if not protegido():
        return redirect("/login")

    con = db()
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

# ---------------- AGREGAR PRODUCTO ----------------
@app.route("/agregar", methods=["POST"])
def agregar():
    if not protegido():
        return redirect("/login")

    con = db()
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

# ---------------- EXPORTAR EXCEL ----------------
@app.route("/exportar")
def exportar():
    if not protegido():
        return redirect("/login")

    con = db()
    df = pd.read_sql_query("SELECT * FROM inventario", con)
    con.close()

    df.to_excel("inventario.xlsx", index=False)

    return "✅ Excel generado"

# ---------------- API ----------------
@app.route("/api/inventario")
def api_inventario():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT * FROM inventario")
    data = cur.fetchall()
    con.close()

    return jsonify(data)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)