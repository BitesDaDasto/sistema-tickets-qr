from flask import Flask, request
from datetime import datetime
import qrcode
import io
import base64
import csv
import os
from collections import Counter
import json
from pytz import timezone

app = Flask(__name__)
TICKETS = []

@app.route('/')
def generar_ticket():
    now = datetime.now(timezone("Chile/Continental")).strftime("%Y-%m-%d %H:%M:%S")
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
            next(lector)
            for fila in lector:
                fecha_completa = fila[1]
                fecha_sola = fecha_completa.split(" ")[0]
                fechas.append(fecha_sola)

        conteo = Counter(fechas)
        fechas_ordenadas = sorted(conteo.keys())
        cantidades = [conteo[f] for f in fechas_ordenadas]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Estadísticas de Tickets</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <h1>📊 Tickets generados por día</h1>
            <ul>
                {''.join(f'<li>{f}: {conteo[f]} ticket(s)</li>' for f in fechas_ordenadas)}
            </ul>
            <canvas id="grafico" width="600" height="300"></canvas>
            <script>
                const ctx = document.getElementById('grafico').getContext('2d');
                const chart = new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(fechas_ordenadas)},
                        datasets: [{{
                            label: 'Tickets por día',
                            data: {json.dumps(cantidades)},
                            backgroundColor: 'rgba(54, 162, 235, 0.6)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{
                        scales: {{
                            y: {{
                                beginAtZero: true
                            }}
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        return html

    except FileNotFoundError:
        return "<p>No hay tickets aún.</p>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
