#!/usr/bin/env python3
"""Cliente de sincronización de DroneLog Chile (HU-08).

Vigila la carpeta FlightRecord de DJI Fly y envía a la API REST cada registro nuevo,
sin intervención del piloto. Solo usa la biblioteca estándar de Python.

Uso:
    python sync.py --api https://dronelog.onrender.com --token TOKEN --carpeta "C:/.../FlightRecord"
    python sync.py ... --una-vez     # revisa la carpeta una sola vez y termina
"""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ESTADO = Path.home() / ".dronelog_enviados.json"


def huella(ruta):
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def enviar(api, token, ruta):
    """Envía un archivo como multipart/form-data. Devuelve (código HTTP, respuesta JSON)."""
    limite = uuid.uuid4().hex
    cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"{ruta.name}\"\r\n"
              f"Content-Type: text/plain\r\n\r\n").encode() + ruta.read_bytes() + f"\r\n--{limite}--\r\n".encode()
    peticion = urllib.request.Request(
        f"{api.rstrip('/')}/api/v1/registros/", data=cuerpo, method="POST",
        headers={"Authorization": f"Token {token}", "Content-Type": f"multipart/form-data; boundary={limite}"})
    try:
        with urllib.request.urlopen(peticion, timeout=120) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def revisar(api, token, carpeta, enviados):
    for ruta in sorted(Path(carpeta).glob("*.txt")):
        h = huella(ruta)
        if h in enviados:
            continue
        try:
            codigo, respuesta = enviar(api, token, ruta)
        except OSError as e:  # sin conexión: se reintenta en la próxima revisión
            print(f"[sin conexión] {ruta.name}: {e}")
            return
        if codigo in (201, 409):
            enviados[h] = ruta.name
            print(f"[{'enviado' if codigo == 201 else 'ya recibido'}] {ruta.name}")
        elif codigo == 422:
            enviados[h] = ruta.name
            print(f"[rechazado] {ruta.name}: {respuesta.get('motivo_rechazo')}")
        else:
            print(f"[error {codigo}] {ruta.name}: {respuesta}")
    ESTADO.write_text(json.dumps(enviados, indent=1), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Envía los registros de vuelo DJI a DroneLog Chile")
    p.add_argument("--api", required=True)
    p.add_argument("--token", required=True)
    p.add_argument("--carpeta", required=True)
    p.add_argument("--intervalo", type=int, default=30, help="segundos entre revisiones")
    p.add_argument("--una-vez", action="store_true")
    a = p.parse_args()
    enviados = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    while True:
        revisar(a.api, a.token, a.carpeta, enviados)
        if a.una_vez:
            break
        time.sleep(a.intervalo)


if __name__ == "__main__":
    main()
