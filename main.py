from flask import Flask, render_template_string, request, make_response, send_file
import sqlite3
import qrcode
import io
import base64
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict
import openpyxl

app = Flask(__name__)

# Crear tabla si no existe
def init_db():
    conn = sqlite3.connect("tickets.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tickets
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ip TEXT,
                  user_agent TEXT,
                  date TEXT,
                  hour TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Página principal: generar ticket
@app.route("/")
def index():
    user_ip = request.remote_addr
    user_agent = request.headers.get("User-Agent")

    # Revisar cookie
    if request.cookies.get("ticket_claimed") == "yes":
        return "<h3>Ya generaste un ticket hoy. Vuelve mañana 🍻</h3>"

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    hour_str = now.strftime("%H:00")

    # Guardar ticket en DB
    conn = sqlite3.connect("tickets.db")
    c = conn.cursor()
    c.execute("INSERT INTO tickets (ip, user_agent, date, hour) VALUES (?, ?, ?, ?)",
              (user_ip, user_agent, date_str, hour_str))
    conn.commit()
    conn.close()

    # Generar QR
    qr_data = f"Ticket válido - {date_str} {hour_str}"
    img = qrcode.make(qr_data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # HTML estilizado
    html = f"""
    <html>
    <head>
        <style>
            body {{
                background-color: #000;
                color: #fff;
                font-family: 'Arial', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }}
            .ticket {{
                background: #111;
                border: 2px solid #fff;
                border-radius: 15px;
                padding: 20px;
                text-align: center;
                width: 320px;
                box-shadow: 0px 0px 15px rgba(255,255,255,0.3);
            }}
            h1 {{
                font-size: 20px;
                margin-bottom: 15px;
            }}
            img {{
                margin: 15px 0;
                width: 200px;
                height: 200px;
            }}
            p {{
                font-size: 14px;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <h1>🎟 Tu Ticket</h1>
            <img src="data:image/png;base64,{qr_b64}" />
            <p><b>Fecha:</b> {date_str}</p>
            <p><b>Hora:</b> {hour_str}</p>
            <p>Pide cualquier wea pa comer y exige una <b>cerveza gratis</b>, tienes <b>1 hora</b> pa cobrarlo 🍺</p>
        </div>
    </body>
    </html>
    """
    resp = make_response(render_template_string(html))
    resp.set_cookie("ticket_claimed", "yes", max_age=24*60*60)  # 24 horas
    return resp

# Estadísticas con gráfico
@app.route("/stats")
def stats():
    conn = sqlite3.connect("tickets.db")
    c = conn.cursor()
    c.execute("SELECT date, hour FROM tickets ORDER BY date, hour")
    rows = c.fetchall()
    conn.close()

    # Contar tickets por combinación fecha+hora
    counts = defaultdict(int)
    for date, hour in rows:
        key = f"{date} {hour}"
        counts[key] += 1

    labels = list(counts.keys())
    values = list(counts.values())

    # Gráfico único
    plt.figure(figsize=(14, 6))
    plt.bar(labels, values)
    plt.title("Tickets generados por fecha y hora")
    plt.xticks(rotation=90, fontsize=8)
    plt.ylabel("Cantidad de tickets")
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
            body {{
                background: #000;
                color: #fff;
                text-align: center;
                font-family: Arial, sans-serif;
            }}
            h1 {{
                margin: 20px;
            }}
            img {{
                max-width: 100%;
                border: 2px solid #fff;
                border-radius: 10px;
            }}
            a {{
                display: inline-block;
                margin-top: 20px;
                padding: 10px 20px;
                background: #fff;
                color: #000;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
            }}
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

# Descargar historial en Excel
@app.route("/download_excel")
def download_excel():
    conn = sqlite3.connect("tickets.db")
    c = conn.cursor()
    c.execute("SELECT id, ip, user_agent, date, hour FROM tickets ORDER BY date, hour")
    rows = c.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"

    # Encabezados
    headers = ["ID", "IP", "User Agent", "Fecha", "Hora"]
    ws.append(headers)

    # Datos ordenados
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
