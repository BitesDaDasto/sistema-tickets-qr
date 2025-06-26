from flask import Flask, request, make_response
from datetime import datetime
import qrcode
import io
import base64
import csv
import os
import json
from pytz import timezone

app = Flask(__name__)
TICKETS = []

@app.route('/')
def generar_ticket():
    tz = timezone("Chile/Continental")
    ahora = datetime.now(tz)
    hoy = ahora.strftime("%Y-%m-%d")
    ahora_str = ahora.strftime("%Y-%m-%d %H:%M:%S")

    ultimo_ticket = request.cookies.get("ultimo_ticket")
    if ultimo_ticket == hoy:
        return """
        <html><head><title>Ya tienes un ticket</title></head>
        <body style="font-family: sans-serif; text-align: center; background: black; color: white; padding: 50px;">
        <h2>⚠️ Ya generaste un ticket hoy.</h2>
        <p>Vuelve mañana para obtener uno nuevo.</p>
        </body></html>
        """

    ticket_id = len(TICKETS) + 1
    TICKETS.append({'id': ticket_id, 'fecha': ahora_str})

    archivo_csv = "tickets.csv"
    nuevo_archivo = not os.path.exists(archivo_csv)
    with open(archivo_csv, mode="a", newline="") as archivo:
        writer = csv.writer(archivo)
        if nuevo_archivo:
            writer.writerow(["ID", "Fecha y hora"])
        writer.writerow([ticket_id, ahora_str])

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Ticket #{ticket_id}</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@500&display=swap');
            body {{
                margin: 0;
                font-family: 'Roboto Mono', monospace;
                background: #000;
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }}
            .ticket {{
                background: #111;
                border: 4px solid white;
                border-radius: 16px;
                padding: 30px 20px;
                width: 90%;
                max-width: 360px;
                box-shadow: 0 0 10px rgba(255, 255, 255, 0.1);
                position: relative;
                overflow: hidden;
            }}
            .ticket::before,
            .ticket::after {{
                content: "";
                position: absolute;
                width: 100%;
                height: 8px;
                background-image: repeating-linear-gradient(90deg, white 0, white 10px, transparent 10px, transparent 20px);
            }}
            .ticket::before {{ top: 0; }}
            .ticket::after {{ bottom: 0; }}
            h1 {{
                font-size: 28px;
                margin-bottom: 20px;
                text-align: center;
                color: #00ffcc;
            }}
            .info {{
                text-align: center;
                font-size: 16px;
                line-height: 1.4;
            }}
            .extra {{
                margin-top: 20px;
                font-size: 14px;
                text-align: center;
                color: #ccc;
            }}
        </style>
    </head>
    <body>
        <div class="ticket">
            <h1>🎟️ TICKET #{ticket_id}</h1>
            <div class="info">
                <p><strong>Fecha y hora:</strong><br>{ahora_str}</p>
                <p class="extra">Pide cualquier wea pa comer y exige una cerveza gratis, tienes una hora pa cobrarlo</p>
            </div>
        </div>
    </body>
    </html>
    """

    respuesta = make_response(html)
    respuesta.set_cookie("ultimo_ticket", hoy, max_age=86400)
    return respuesta

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
        <title>Código QR</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: 'Segoe UI', sans-serif;
                background: #000;
                color: white;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }}
            h2 {{
                margin-bottom: 20px;
                color: #00ffcc;
                text-align: center;
            }}
            img {{
                border: 6px dashed #00ffcc;
                padding: 12px;
                background: #111;
                border-radius: 12px;
            }}
            p {{
                margin-top: 20px;
                font-size: 14px;
                color: #ccc;
            }}
            a {{
                color: #00ffcc;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <h2>Escanea este código QR</h2>
        <img src="data:image/png;base64,{img_str}" alt="Código QR">
        <p>Este QR apunta a: <a href="{url}">{url}</a></p>
    </body>
    </html>
    """
    return html

@app.route('/stats')
def estadisticas():
    datos_dia = {}
    datos_hora = {}
    archivo_csv = "tickets.csv"

    if not os.path.exists(archivo_csv):
        return "<h2 style='color:white; background:black; padding:20px;'>No hay datos aún.</h2>"

    with open(archivo_csv, mode="r") as archivo:
        reader = csv.DictReader(archivo)
        for fila in reader:
            partes = fila["Fecha y hora"].split()
            if len(partes) == 2:
                fecha, hora = partes
                hora = hora[:2] + ":00"
                datos_dia[fecha] = datos_dia.get(fecha, 0) + 1
                datos_hora[hora] = datos_hora.get(hora, 0) + 1

    fechas = list(datos_dia.keys())
    conteos_dia = list(datos_dia.values())
    horas = sorted(datos_hora.keys())
    conteos_hora = [datos_hora[h] for h in horas]

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Estadísticas de Tickets</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{
                background: #000;
                color: white;
                font-family: 'Segoe UI', sans-serif;
                text-align: center;
                padding: 20px;
            }}
            canvas {{
                background: #111;
                border: 1px solid #444;
                border-radius: 12px;
                padding: 10px;
                max-width: 100%;
                margin-bottom: 40px;
            }}
        </style>
    </head>
    <body>
        <h2>📊 Tickets por Día</h2>
        <canvas id="graficoDia" width="400" height="300"></canvas>
        <h2>🕐 Tickets por Hora</h2>
        <canvas id="graficoHora" width="400" height="300"></canvas>
        <script>
            new Chart(document.getElementById('graficoDia').getContext('2d'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(fechas)},
                    datasets: [{{
                        label: 'Tickets por día',
                        data: {json.dumps(conteos_dia)},
                        backgroundColor: '#00ffcc'
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{ beginAtZero: true, ticks: {{ color: 'white' }}, grid: {{ color: '#333' }} }},
                        x: {{ ticks: {{ color: 'white' }}, grid: {{ color: '#333' }} }}
                    }},
                    plugins: {{ legend: {{ labels: {{ color: 'white' }} }} }}
                }}
            }});

            new Chart(document.getElementById('graficoHora').getContext('2d'), {{
                type: 'bar',
                data: {{
                    labels: {json.dumps(horas)},
                    datasets: [{{
                        label: 'Tickets por hora',
                        data: {json.dumps(conteos_hora)},
                        backgroundColor: '#ffaa00'
                    }}]
                }},
                options: {{
                    scales: {{
                        y: {{ beginAtZero: true, ticks: {{ color: 'white' }}, grid: {{ color: '#333' }} }},
                        x: {{ ticks: {{ color: 'white' }}, grid: {{ color: '#333' }} }}
                    }},
                    plugins: {{ legend: {{ labels: {{ color: 'white' }} }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

