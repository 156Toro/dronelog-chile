"""Adaptador del lector de registros DJI.

DroneLog no descifra el formato por sí mismo: invoca el binario `dji-parser`
(herramientas/dji-parser, basado en la biblioteca abierta dji-log-parser), que
pide las claves a DJI con la App Key de la empresa operadora y devuelve JSON.
"""
import json
import os
import subprocess
from datetime import datetime, timedelta

from django.conf import settings


class ErrorLectura(Exception):
    """Error al leer un registro. `mensaje` se muestra tal cual al administrador (HU-11)."""

    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


class ArchivoInvalido(ErrorLectura):
    pass


class ErrorDescifrado(ErrorLectura):
    pass


def leer_registro(ruta):
    """Ejecuta dji-parser sobre `ruta` y devuelve el JSON {version, details, frames}."""
    if not os.path.exists(settings.DJI_PARSER_BIN):
        raise ErrorLectura("El lector de registros DJI no está instalado en el servidor.")
    try:
        proceso = subprocess.run(
            [settings.DJI_PARSER_BIN, str(ruta)],
            capture_output=True, text=True, timeout=settings.DJI_PARSER_TIMEOUT,
            env={**os.environ},
        )
    except subprocess.TimeoutExpired:
        raise ErrorLectura("El registro tardó demasiado en procesarse.")
    if proceso.returncode == 2:
        raise ArchivoInvalido("El archivo no es un registro de vuelo DJI válido.")
    if proceso.returncode == 3:
        raise ErrorDescifrado(f"No se pudo descifrar el registro: {proceso.stderr.strip()}")
    if proceso.returncode != 0:
        raise ErrorLectura(f"Error del lector DJI: {proceso.stderr.strip()}")
    try:
        return json.loads(proceso.stdout)
    except json.JSONDecodeError:
        raise ErrorLectura("El lector DJI devolvió una respuesta ilegible.")


def _fecha(valor):
    if not valor:
        return None
    return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))


def _coordenada_valida(lat, lon):
    return lat is not None and lon is not None and not (abs(lat) < 1e-6 and abs(lon) < 1e-6) \
        and -90 <= lat <= 90 and -180 <= lon <= 180


def normalizar(datos):
    """Convierte la salida de dji-parser en los campos de una Operación.

    Devuelve un diccionario con: inicio, fin, duracion_s, distancia_m, altura_max_m,
    velocidad_max_ms, bateria_inicio_pct, bateria_fin_pct, latitud_inicio, longitud_inicio,
    lugar, modelo_aeronave, serie_aeronave, serie_bateria, puntos y eventos.
    """
    detalles = datos.get("details") or {}
    frames = datos.get("frames") or []
    if not frames:
        raise ArchivoInvalido("El registro no contiene datos de vuelo.")

    primero, ultimo = frames[0], frames[-1]
    recover = next((f.get("recover") for f in frames if (f.get("recover") or {}).get("aircraftSn")), {}) or {}

    inicio = _fecha(detalles.get("startTime")) or _fecha((primero.get("custom") or {}).get("dateTime"))
    if inicio is None:
        raise ArchivoInvalido("El registro no indica la hora de inicio del vuelo.")
    duracion = float(detalles.get("totalTime") or (ultimo.get("osd") or {}).get("flyTime") or 0)
    if duracion <= 0:
        raise ArchivoInvalido("El registro no contiene un vuelo (duración cero).")

    puntos, eventos, alturas, velocidades = [], [], [], []
    for f in frames:
        osd, bat, app = f.get("osd") or {}, f.get("battery") or {}, f.get("app") or {}
        segundo = float(osd.get("flyTime") or 0)
        alturas.append(float(osd.get("height") or 0))
        velocidades.append((float(osd.get("xSpeed") or 0) ** 2 + float(osd.get("ySpeed") or 0) ** 2) ** 0.5)
        lat, lon = osd.get("latitude"), osd.get("longitude")
        if _coordenada_valida(lat, lon):
            puntos.append({"segundo": segundo, "latitud": lat, "longitud": lon,
                           "altura_m": float(osd.get("height") or 0), "bateria_pct": bat.get("chargeLevel")})
        if app.get("warn"):
            eventos.append({"segundo": segundo, "tipo": "advertencia", "mensaje": app["warn"][:300]})
        if app.get("tip"):
            eventos.append({"segundo": segundo, "tipo": "aviso", "mensaje": app["tip"][:300]})

    # se reduce la trayectoria para no guardar miles de puntos por vuelo
    paso = max(1, len(puntos) // settings.DRONELOG_PUNTOS_MAX + 1) if len(puntos) > settings.DRONELOG_PUNTOS_MAX else 1
    puntos = puntos[::paso]

    lugar = ", ".join(p for p in [detalles.get("street"), detalles.get("city"), detalles.get("area")] if p)
    return {
        "inicio": inicio,
        "fin": inicio + timedelta(seconds=duracion),
        "duracion_s": round(duracion, 1),
        "distancia_m": round(float(detalles.get("totalDistance") or 0), 1),
        "altura_max_m": round(float(detalles.get("maxHeight") or max(alturas, default=0)), 1),
        "velocidad_max_ms": round(float(detalles.get("maxHorizontalSpeed") or max(velocidades, default=0)), 1),
        "bateria_inicio_pct": (primero.get("battery") or {}).get("chargeLevel"),
        "bateria_fin_pct": (ultimo.get("battery") or {}).get("chargeLevel"),
        "latitud_inicio": puntos[0]["latitud"] if puntos else None,
        "longitud_inicio": puntos[0]["longitud"] if puntos else None,
        "lugar": lugar[:200],
        "modelo_aeronave": (detalles.get("aircraftName") or recover.get("aircraftName") or "")[:80],
        "serie_aeronave": (detalles.get("aircraftSn") or recover.get("aircraftSn") or "").strip().upper(),
        "serie_bateria": (detalles.get("batterySn") or recover.get("batterySn") or "").strip().upper(),
        "puntos": puntos,
        "eventos": eventos,
    }
