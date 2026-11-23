"""Servicio de ingesta: recibe un registro DJI, lo descifra y crea la operación (HU-08 a HU-11)."""
import hashlib

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from flota.models import Aeronave, Bateria

from . import dji
from .models import EventoVuelo, Operacion, PuntoTrayectoria, RegistroVuelo


class RegistroDuplicado(Exception):
    def __init__(self, registro):
        super().__init__("Este registro de vuelo ya fue recibido.")
        self.registro = registro
        self.mensaje = (f"Este registro ya fue recibido el {timezone.localtime(registro.recibido_en):%d-%m-%Y %H:%M} "
                        f"y no se registrará dos veces.")


class ArchivoNoPermitido(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


def calcular_huella(archivo):
    sha = hashlib.sha256()
    for bloque in archivo.chunks():
        sha.update(bloque)
    archivo.seek(0)
    return sha.hexdigest()


def recibir_registro(usuario, archivo, lector=None):
    """Guarda el archivo recibido y lo procesa. Devuelve el RegistroVuelo (procesado o rechazado).

    Lanza RegistroDuplicado si la empresa ya tiene ese mismo archivo procesado.
    """
    if not archivo.name.lower().endswith(".txt"):
        raise ArchivoNoPermitido("Solo se aceptan registros DJI Fly con extensión .txt.")
    if archivo.size > settings.DRONELOG_MAX_ARCHIVO_MB * 1024 * 1024:
        raise ArchivoNoPermitido(f"El archivo supera los {settings.DRONELOG_MAX_ARCHIVO_MB} MB.")

    huella = calcular_huella(archivo)
    existente = RegistroVuelo.objects.filter(empresa=usuario.empresa, huella_sha256=huella).first()
    if existente and existente.estado != RegistroVuelo.RECHAZADO:
        raise RegistroDuplicado(existente)
    if existente:  # un registro rechazado se puede volver a enviar (por ejemplo, tras registrar la aeronave)
        existente.archivo.delete(save=False)
        existente.delete()

    registro = RegistroVuelo(empresa=usuario.empresa, enviado_por=usuario, nombre_original=archivo.name[:255],
                             tamano_bytes=archivo.size, huella_sha256=huella)
    registro.archivo.save(archivo.name, archivo, save=True)
    procesar_registro(registro, lector)
    return registro


def procesar_registro(registro, lector=None):
    """Descifra el registro y crea la operación. Si algo falla, deja el motivo en el registro."""
    try:
        datos = (lector or dji.leer_registro)(registro.archivo.path)
        vuelo = dji.normalizar(datos)
        with transaction.atomic():
            _crear_operacion(registro, vuelo)
            registro.version_formato = datos.get("version")
            registro.estado = RegistroVuelo.PROCESADO
            registro.motivo_rechazo = ""
            registro.procesado_en = timezone.now()
            registro.save()
    except (dji.ErrorLectura, ErrorFlota) as error:
        registro.estado = RegistroVuelo.RECHAZADO
        registro.motivo_rechazo = error.mensaje
        registro.procesado_en = timezone.now()
        registro.save()
    return registro


class ErrorFlota(Exception):
    def __init__(self, mensaje):
        super().__init__(mensaje)
        self.mensaje = mensaje


def _crear_operacion(registro, vuelo):
    empresa = registro.empresa
    # HU-10: la aeronave y la batería se reconocen por su número de serie
    aeronave = Aeronave.objects.filter(empresa=empresa, numero_serie=vuelo["serie_aeronave"]).first()
    if aeronave is None:
        raise ErrorFlota(f"La aeronave con número de serie {vuelo['serie_aeronave'] or '(sin serie)'} "
                         f"no está registrada en la flota de {empresa}. Regístrela y vuelva a enviar el archivo.")
    bateria = Bateria.objects.filter(empresa=empresa, numero_serie=vuelo["serie_bateria"]).first() \
        if vuelo["serie_bateria"] else None
    piloto = getattr(registro.enviado_por, "piloto", None)

    campos = {k: v for k, v in vuelo.items() if k not in ("puntos", "eventos")}
    operacion = Operacion.objects.create(empresa=empresa, registro=registro, aeronave=aeronave,
                                         bateria=bateria, piloto=piloto, **campos)
    PuntoTrayectoria.objects.bulk_create(PuntoTrayectoria(operacion=operacion, **p) for p in vuelo["puntos"])
    eventos = list(vuelo["eventos"])
    if vuelo["serie_bateria"] and bateria is None:
        eventos.append({"segundo": 0, "tipo": EventoVuelo.ADVERTENCIA,
                        "mensaje": f"La batería {vuelo['serie_bateria']} no está registrada en la flota."})
    EventoVuelo.objects.bulk_create(EventoVuelo(operacion=operacion, **e) for e in eventos)
    if bateria:
        Bateria.objects.filter(pk=bateria.pk).update(ciclos=bateria.ciclos + 1)
    return operacion
