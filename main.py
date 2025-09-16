from flask import Flask, render_template_string, request, make_response, send_file
import sqlite3
import qrcode
import io
from datetime import datetime
import pytz
from uuid import uuid4
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
import openpyxl

app = Flask(__name__)

# === Configuración de la base de datos ===
def init_db():
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE,
            date TEXT,
            hour TEXT,
            redeemed INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === Ruta para generar un ticket ===
@app.route("/")
def index():
    cookie = request.cookies.get("ticket_generated")
    if cookie:
        return "<h2 style='color:red'>⚠️ Ya generaste un ticket hoy. Intenta mañana.</h2>"

    ticket_id = str(uuid4())
    tz = pytz.timezone("America/Santiago")
    fecha = datetime.now(tz)
    fecha_str = fecha.strftime("%Y-%m-%d")
    hora_str = fecha.strftime("%H:%M")

    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tickets (uuid, date, hour, redeemed) VALUES (?, ?, ?, ?)",
                   (ticket_id, fecha_str, hora_str, 0))
    conn.commit()
    conn.close()

    html = f"""
    <html>
    <head>
        <style>
            body {{background-color: black; color: white; font-family: 'Arial', sans-serif;
                  display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0;}}
            .ticket {{background: #111; border: 2px dashed white; border-radius: 15px; padding: 20px; text-align: center; max-width: 300px;}}
            h1 {{font-size: 22px; margin-bottom: 10px;}}
            p {{font-size: 14px; margin: 5px 0;}}
            img {{margin: 15px 0; width: 200px; height: 200px;}}
            .note {{margin-top: 15px; font-size: 12px; color: #ccc;}}
        </style>
    </head>
    <body>
        <div class="ticket">
            <h1>🎟️ Ticket válido</h1>
            <p><b>Fecha:</b> {fecha_str}</p>
            <p><b>Hora:</b> {hora_str}</p>
            <img src="/ticket_qr/{ticket_id}" alt="QR Code">
            <p class="note">Pide cualquier wea pa comer y exige una cerveza gratis,<br> tienes una hora pa cobrarlo 🍺</p>
        </div>
    </body>
    </html>
    """
    resp = make_response(html)
    resp.set_cookie("ticket_generated", "1", max_age=60*60*24)
    return resp

# === Endpoint para servir la imagen QR ===
@app.route("/ticket_qr/<ticket_id>")
def ticket_qr(ticket_id):
    ticket_url = f"https://tickets-cerveza.onrender.com/redeem/{ticket_id}"
    img = qrcode.make(ticket_url)
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")

# === Ruta para canjear un ticket ===
@app.route("/redeem/<ticket_id>")
def redeem(ticket_id):
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT redeemed, date, hour FROM tickets WHERE uuid = ?", (ticket_id,))
    result = cursor.fetchone()

    if not result:
        return "<h2 style='color:red'>❌ Ticket inválido</h2>"

    redeemed, fecha, hora = result

    if redeemed == 1:
        return "<h2 style='color:orange'>⚠️ Este ticket ya fue canjeado</h2>"

    cursor.execute("UPDATE tickets SET redeemed = 1 WHERE uuid = ?", (ticket_id,))
    conn.commit()
    conn.close()

    return f"""
    <h2 style='color:green'>✅ Ticket válido</h2>
    <p>Fecha: {fecha}</p>
    <p>Hora: {hora}</p>
    <p>Ticket ID: {ticket_id}</p>
    """

# === Ruta de estadísticas ===
@app.route("/stats")
def stats():
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT date, hour, redeemed FROM tickets ORDER BY date, hour")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "<h2 style='color:white'>No hay tickets generados aún</h2>"

    counts_total = defaultdict(int)
    counts_redeemed = defaultdict(int)
    counts_not_redeemed = defaultdict(int)

    for date, hour, redeemed in rows:
        key = f"{date} {hour}"
        counts_total[key] += 1
        if redeemed:
            counts_redeemed[key] += 1
        else:
            counts_not_redeemed[key] += 1

    labels = sorted(counts_total.keys())
    total_vals = [int(counts_total.get(label,0)) for label in labels]
    redeemed_vals = [int(counts_redeemed.get(label,0)) for label in labels]
    not_redeemed_vals = [int(counts_not_redeemed.get(label,0)) for label in labels]

    # Gráfico de barras apiladas
    plt.figure(figsize=(14,6))
    plt.bar(labels, not_redeemed_vals, label="No canjeados", color="orange")
    plt.bar(labels, redeemed_vals, bottom=not_redeemed_vals, label="Canjeados", color="green")
    plt.title("Tickets por fecha y hora (Canjeados / No Canjeados)")
    plt.xticks(rotation=90, fontsize=8)
    plt.ylabel("Cantidad de tickets")
    plt.legend()
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    graph_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close()

    html = f"""
    <html>
    <head>
        <style>
            body {{background: #000; color: #fff; text-align:center; font-family:Arial,sans-serif;}}
            h1 {{margin:20px;}}
            img {{max-width: 100%; border:2px solid #fff; border-radius:10px;}}
            a {{display:inline-block; margin-top:20px; padding:10px 20px; background:#fff; color:#000; text-decoration:none; border-radius:5px; font-weight:bold;}}
        </style>
    </head>
    <body>
        <h1>📊 Estadísticas de Tickets</h1>
        <img src="data:image/png;base64,{graph_b64}">
        <br>
        <a href="/download_excel">⬇ Descargar historial en Excel</a>
    </body>
    </html>
    """
    return render_template_string(html)

# === Descargar historial en Excel ===
@app.route("/download_excel")
def download_excel():
    conn = sqlite3.connect("tickets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, uuid, date, hour, redeemed FROM tickets ORDER BY date, hour")
    rows = cursor.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"

    headers = ["ID","UUID","Fecha","Hora","Canjeado"]
    ws.append(headers)

    for row in rows:
        ws.append(row)

    # Guardar en memoria
    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(
        file_stream,
        as_attachment=True,
        download_name="tickets.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

