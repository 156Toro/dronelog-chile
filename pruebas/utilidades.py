"""Datos comunes para las pruebas."""
import json
from datetime import date
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.authtoken.models import Token

from cuentas.models import Empresa, Rol, Usuario
from flota.models import Aeronave, Bateria, Piloto

DEMO = Path(__file__).resolve().parent.parent / "operaciones" / "datos_demo" / "vuelo_mavic3.json"
CLAVE = "ClaveSegura2026"


def datos_vuelo():
    """Salida real de dji-parser para un vuelo de prueba (DJI Mavic 3, 24-10-2026)."""
    return json.loads(DEMO.read_text(encoding="utf-8"))


def lector_demo(ruta):
    return datos_vuelo()


def archivo_txt(contenido=b"FlightRecord de prueba", nombre="DJIFlightRecord_2026-10-24.txt"):
    return SimpleUploadedFile(nombre, contenido, content_type="text/plain")


def rol(codigo):
    return Rol.objects.get(codigo=codigo)


def crear_usuario(email, codigo, empresa=None):
    return Usuario.objects.create_user(email=email, password=CLAVE, rol=rol(codigo), empresa=empresa,
                                       first_name=email.split("@")[0])


class Escenario:
    """Dos empresas con sus usuarios y la flota de la empresa A."""

    def __init__(self):
        self.a = Empresa.objects.create(nombre="Vigilance SpA", rut="76123456-7")
        self.b = Empresa.objects.create(nombre="Drones del Sur SpA", rut="77987654-3")
        self.plataforma = crear_usuario("plataforma@dronelog.cl", Rol.ADMIN_PLATAFORMA)
        self.admin_a = crear_usuario("admin@a.cl", Rol.ADMIN_EMPRESA, self.a)
        self.piloto_a = crear_usuario("piloto@a.cl", Rol.PILOTO, self.a)
        self.visual_a = crear_usuario("cliente@a.cl", Rol.VISUALIZADOR, self.a)
        self.admin_b = crear_usuario("admin@b.cl", Rol.ADMIN_EMPRESA, self.b)
        self.piloto_b = crear_usuario("piloto@b.cl", Rol.PILOTO, self.b)
        self.ficha_piloto = Piloto.objects.create(
            empresa=self.a, usuario=self.piloto_a, nombre="Piloto A", rut="12345678-5",
            credencial_dgac="DGAC-0001", vencimiento_credencial=date(2027, 12, 31))
        self.aeronave = Aeronave.objects.create(empresa=self.a, nombre="Mavic 3 T01", modelo="DJI Mavic 3",
                                                numero_serie="1581F45TB21BR1AE")
        self.bateria = Bateria.objects.create(empresa=self.a, aeronave=self.aeronave, numero_serie="4ERPJBSDA055RA")

    @staticmethod
    def token(usuario):
        return Token.objects.create(user=usuario).key
