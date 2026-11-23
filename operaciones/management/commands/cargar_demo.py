"""Carga datos de demostración: empresa Vigilance SpA, sus usuarios, su flota y un vuelo real procesado."""
import json
import os
from datetime import date
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from cuentas.models import Empresa, Rol, Usuario
from flota.models import Aeronave, Bateria, Piloto
from operaciones.ingesta import procesar_registro
from operaciones.models import RegistroVuelo

DEMO = Path(__file__).resolve().parents[2] / "datos_demo" / "vuelo_mavic3.json"


class Command(BaseCommand):
    help = "Crea datos de demostración (idempotente)."

    @transaction.atomic
    def handle(self, *args, **opciones):
        clave = os.environ.get("DRONELOG_DEMO_PASSWORD", "DroneLog2026!")
        rol = {r.codigo: r for r in Rol.objects.all()}

        def usuario(email, nombre, codigo, empresa=None):
            u, creado = Usuario.objects.get_or_create(
                email=email, defaults={"first_name": nombre, "rol": rol[codigo], "empresa": empresa,
                                       "is_staff": codigo == Rol.ADMIN_PLATAFORMA,
                                       "is_superuser": codigo == Rol.ADMIN_PLATAFORMA})
            if creado:
                u.set_password(clave)
                u.save()
            return u

        usuario("plataforma@dronelog.cl", "Administración DroneLog", Rol.ADMIN_PLATAFORMA)
        vig, _ = Empresa.objects.get_or_create(nombre="Vigilance SpA", defaults={"rut": "76123456-7"})
        usuario("admin@vigilance.cl", "Jefatura Vigilance", Rol.ADMIN_EMPRESA, vig)
        piloto_u = usuario("piloto@vigilance.cl", "Piloto Vigilance", Rol.PILOTO, vig)
        usuario("cliente@vigilance.cl", "Cliente minero", Rol.VISUALIZADOR, vig)
        otra, _ = Empresa.objects.get_or_create(nombre="Drones del Sur SpA", defaults={"rut": "77987654-3"})
        usuario("admin@dronesdelsur.cl", "Jefatura Drones del Sur", Rol.ADMIN_EMPRESA, otra)

        Piloto.objects.get_or_create(empresa=vig, rut="12345678-5", defaults={
            "nombre": "Piloto Vigilance", "usuario": piloto_u, "credencial_dgac": "DGAC-RPAS-0001",
            "vencimiento_credencial": date(2027, 12, 31)})
        nave, _ = Aeronave.objects.get_or_create(numero_serie="1581F45TB21BR1AE", defaults={
            "empresa": vig, "nombre": "Mavic 3 T01", "modelo": "DJI Mavic 3"})
        Bateria.objects.get_or_create(numero_serie="4ERPJBSDA055RA", defaults={"empresa": vig, "aeronave": nave})

        datos = json.loads(DEMO.read_text(encoding="utf-8"))
        huella = "demo-" + "0" * 59
        if not RegistroVuelo.objects.filter(empresa=vig, huella_sha256=huella).exists():
            registro = RegistroVuelo(empresa=vig, enviado_por=piloto_u, nombre_original="DJIFlightRecord_2026-10-24_[00-13-20].txt",
                                     tamano_bytes=DEMO.stat().st_size, huella_sha256=huella)
            registro.archivo.save("demo.txt", ContentFile(b"registro de demostracion"), save=True)
            procesar_registro(registro, lector=lambda ruta: datos)
        self.stdout.write(self.style.SUCCESS(f"Datos de demostración listos. Contraseña de los usuarios: {clave}"))
