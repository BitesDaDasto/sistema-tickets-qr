from flask import Flask, request
from datetime import datetime
import qrcode
import io
import base64
import csv
import os
from collections import Counter

app = Flask(__name__)
TICKETS = []

@app.route('/')
def generar_ticket():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ticket_id = len(TICKETS) + 1
    TICKETS.append({'id': ticket_id, 'fecha': now})

    # Guardar en archivo CSV
    archivo_csv = "tickets.csv"
    nuevo_archivo = not os.path.exists(archivo_csv)
    with open(archivo_csv, mode="a", newline="") as archivo:
        writer = csv.writer(archivo)
        if nuevo_archivo:
            writer.writerow(["ID", "Fecha y hora"])
        writer.writerow([ticket_id, now])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ticket #{ticket_id}</title>
    </head>
    <body>
        <h1>🎟️ Ticket #{ticket_id}</h1>
        <p>Fecha y hora: {now}</p>
        <p><a href="/qr">Volver al QR</a></p>
    </body>
    </html>
    """
    return html

@app.route('/qr')
def mostrar_qr():
    url = request.host_url
    qr = qrcode.make(url)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>QR Code</title>
    </head>
    <body>
        <h2>Escanea este código QR para obtener tu ticket</h2>
        <img src="data:image/png;base64,{img_str}" alt="Código QR">
        <p>Este QR apunta a: <a href="{url}">{url}</a></p>
    </body>
    </html>
    """
    return html

@app.route('/stats')
def ver_estadisticas():
    fechas = []

    try:
        with open("tickets.csv", mode="r") as archivo:
            lector = csv.reader(archivo)
            next(lector)  # Saltar encabezado
            for fila in lector:
                fecha_completa = fila[1]
                fecha_sola = fecha_completa.split(" ")[0]
                fechas.append(fecha_sola)

        conteo = Counter(fechas)
        html = "<h1>📊 Tickets generados por día</h1><ul>"
        for fecha, cantidad in conteo.items():
            html += f"<li>{fecha}: {cantidad} ticket(s)</li>"
        html += "</ul>"
        return html

    except FileNotFoundError:
        return "<p>No hay tickets aún.</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
