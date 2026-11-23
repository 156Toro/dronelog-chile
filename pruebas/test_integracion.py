"""Pruebas de integración: recorren HTTP → vistas/API → servicios → base de datos."""
import time
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from cuentas.models import Empresa, Rol, Usuario
from flota.models import Aeronave, Bateria, Piloto
from operaciones import dji
from operaciones.models import Operacion, RegistroVuelo

from .utilidades import CLAVE, Escenario, archivo_txt, lector_demo

LECTOR = "operaciones.ingesta.dji.leer_registro"


class IngresoTest(TestCase):
    """HU-02: inicio y cierre de sesión con correo y contraseña."""

    def setUp(self):
        self.e = Escenario()

    def test_ingreso_correcto_y_salida(self):
        r = self.client.post(reverse("login"), {"username": "ADMIN@a.cl", "password": CLAVE})
        self.assertRedirects(r, reverse("inicio"))
        self.client.post(reverse("logout"))
        self.assertRedirects(self.client.get(reverse("inicio")), f"{reverse('login')}?next=/")

    def test_clave_incorrecta(self):
        r = self.client.post(reverse("login"), {"username": "admin@a.cl", "password": "mala"})
        self.assertContains(r, "Correo o contraseña incorrectos")

    def test_usuario_inactivo_no_ingresa(self):
        self.e.admin_a.is_active = False
        self.e.admin_a.save()
        self.assertFalse(self.client.login(email="admin@a.cl", password=CLAVE))


class EmpresasTest(TestCase):
    """HU-01: el administrador de plataforma registra empresas y su administrador."""

    def setUp(self):
        self.e = Escenario()

    def test_crea_empresa_con_administrador(self):
        self.client.force_login(self.e.plataforma)
        r = self.client.post(reverse("empresa_crear"), {
            "nombre": "Aéreo Norte SpA", "rut": "78111222-3", "admin_nombre": "Ana",
            "admin_email": "ana@norte.cl", "admin_password": "ClaveNorte2026"})
        self.assertRedirects(r, reverse("empresas"))
        admin = Usuario.objects.get(email="ana@norte.cl")
        self.assertEqual(admin.empresa.nombre, "Aéreo Norte SpA")
        self.assertEqual(admin.rol.codigo, Rol.ADMIN_EMPRESA)
        self.assertTrue(self.client.login(email="ana@norte.cl", password="ClaveNorte2026"))

    def test_correo_repetido_no_crea_nada(self):
        self.client.force_login(self.e.plataforma)
        self.client.post(reverse("empresa_crear"), {
            "nombre": "Otra", "rut": "1-9", "admin_nombre": "X", "admin_email": "admin@a.cl",
            "admin_password": "ClaveNorte2026"})
        self.assertFalse(Empresa.objects.filter(nombre="Otra").exists())

    def test_admin_de_empresa_no_accede(self):
        self.client.force_login(self.e.admin_a)
        self.assertEqual(self.client.get(reverse("empresas")).status_code, 403)


class UsuariosTest(TestCase):
    """HU-03 y HU-04: usuarios con rol y aislamiento por empresa."""

    def setUp(self):
        self.e = Escenario()
        self.client.force_login(self.e.admin_a)

    def test_crea_usuario_con_rol_en_su_empresa(self):
        self.client.post(reverse("usuario_crear"), {
            "first_name": "Nuevo", "last_name": "Piloto", "email": "nuevo@a.cl",
            "rol": Rol.objects.get(codigo=Rol.PILOTO).pk, "is_active": "on", "password": "ClaveNueva2026"})
        u = Usuario.objects.get(email="nuevo@a.cl")
        self.assertEqual((u.empresa, u.rol.codigo), (self.e.a, Rol.PILOTO))

    def test_no_puede_crear_admin_de_plataforma(self):
        r = self.client.post(reverse("usuario_crear"), {
            "first_name": "X", "email": "x@a.cl", "rol": Rol.objects.get(codigo=Rol.ADMIN_PLATAFORMA).pk,
            "password": "ClaveNueva2026"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email="x@a.cl").exists())

    def test_solo_ve_usuarios_de_su_empresa(self):
        r = self.client.get(reverse("usuarios"))
        self.assertContains(r, "piloto@a.cl")
        self.assertNotContains(r, "piloto@b.cl")

    def test_no_puede_editar_usuario_de_otra_empresa(self):
        self.assertEqual(self.client.get(reverse("usuario_editar", args=[self.e.piloto_b.pk])).status_code, 404)

    def test_piloto_no_gestiona_usuarios(self):
        self.client.force_login(self.e.piloto_a)
        self.assertEqual(self.client.get(reverse("usuarios")).status_code, 403)


class FlotaTest(TestCase):
    """HU-05, HU-06, HU-07: pilotos, aeronaves y baterías por empresa."""

    def setUp(self):
        self.e = Escenario()
        self.client.force_login(self.e.admin_a)

    def test_registra_piloto_con_credencial_dgac(self):
        self.client.post(reverse("pilotos_crear"), {
            "nombre": "Carla Rojas", "rut": "15.111.222-3", "credencial_dgac": "DGAC-0099",
            "vencimiento_credencial": "2027-06-30", "activo": "on"})
        p = Piloto.objects.get(nombre="Carla Rojas")
        self.assertEqual((p.empresa, p.rut, p.credencial_dgac), (self.e.a, "15111222-3", "DGAC-0099"))

    def test_rut_de_piloto_no_se_repite_en_la_empresa(self):
        r = self.client.post(reverse("pilotos_crear"), {
            "nombre": "Duplicado", "rut": "12345678-5", "credencial_dgac": "X", "vencimiento_credencial": "2027-01-01"})
        self.assertContains(r, "Ya existe un piloto con ese RUT")

    def test_registra_aeronave_y_serie_queda_normalizada(self):
        self.client.post(reverse("aeronaves_crear"), {"nombre": "T02", "modelo": "Matrice 30T",
                                                      "numero_serie": " 1zn bk7 ", "activa": "on"})
        self.assertTrue(Aeronave.objects.filter(empresa=self.e.a, numero_serie="1ZN BK7").exists())

    def test_serie_de_aeronave_es_unica(self):
        r = self.client.post(reverse("aeronaves_crear"), {"nombre": "X", "modelo": "X",
                                                          "numero_serie": "1581f45tb21br1ae"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Aeronave.objects.count(), 1)

    def test_registra_bateria_de_una_aeronave(self):
        self.client.post(reverse("baterias_crear"), {"numero_serie": "BAT-002", "aeronave": self.e.aeronave.pk,
                                                     "activa": "on"})
        self.assertEqual(Bateria.objects.get(numero_serie="BAT-002").aeronave, self.e.aeronave)

    def test_no_ve_ni_edita_flota_de_otra_empresa(self):
        ajena = Aeronave.objects.create(empresa=self.e.b, nombre="Ajena", modelo="X", numero_serie="AJENA-1")
        self.assertNotContains(self.client.get(reverse("aeronaves")), "AJENA-1")
        self.assertEqual(self.client.get(reverse("aeronaves_editar", args=[ajena.pk])).status_code, 404)

    def test_visualizador_no_modifica_la_flota(self):
        self.client.force_login(self.e.visual_a)
        self.assertEqual(self.client.get(reverse("aeronaves_crear")).status_code, 403)


class ConLectorDemo(TestCase):
    """Reemplaza la llamada al binario DJI por la salida real guardada de un vuelo."""

    def _parchar(self):
        parche = mock.patch(LECTOR, side_effect=lector_demo)
        self.addCleanup(parche.stop)
        return parche.start()


class EnvioRegistroAPITest(ConLectorDemo):
    """HU-08 a HU-11: el cliente de sincronización envía el registro y se crea la operación."""

    def setUp(self):
        self.lector = self._parchar()
        self.e = Escenario()
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {self.e.token(self.e.piloto_a)}")
        self.url = reverse("api_registros")

    def enviar(self, archivo=None):
        return self.api.post(self.url, {"archivo": archivo or archivo_txt()}, format="multipart")

    def test_envio_crea_la_operacion_automaticamente(self):
        r = self.enviar()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["estado"], "procesado")
        op = Operacion.objects.get()
        self.assertEqual(op.empresa, self.e.a)
        self.assertEqual(op.piloto, self.e.ficha_piloto)          # piloto: quien envía
        self.assertEqual(op.aeronave, self.e.aeronave)            # HU-10: reconocida por serie
        self.assertEqual(op.bateria, self.e.bateria)              # HU-10
        self.assertEqual(op.duracion_s, 57.8)
        self.assertTrue(op.eventos.exists())
        self.e.bateria.refresh_from_db()
        self.assertEqual(self.e.bateria.ciclos, 1)
        self.assertTrue(Path(op.registro.archivo.path).exists())  # el archivo original se conserva

    def test_mismo_archivo_dos_veces_se_rechaza(self):
        self.enviar()
        r = self.enviar()
        self.assertEqual(r.status_code, 409)
        self.assertIn("ya fue recibido", r.data["detalle"])
        self.assertEqual(Operacion.objects.count(), 1)

    def test_mismo_archivo_en_otra_empresa_no_es_duplicado(self):
        self.enviar()
        Aeronave.objects.filter(pk=self.e.aeronave.pk).update(empresa=self.e.b)
        api_b = APIClient()
        api_b.credentials(HTTP_AUTHORIZATION=f"Token {self.e.token(self.e.piloto_b)}")
        r = api_b.post(self.url, {"archivo": archivo_txt()}, format="multipart")
        self.assertEqual(r.status_code, 201)

    def test_extension_no_permitida(self):
        r = self.enviar(archivo_txt(nombre="foto.jpg"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(RegistroVuelo.objects.count(), 0)

    def test_archivo_que_no_es_dji_queda_rechazado_con_motivo(self):
        self.lector.side_effect = dji.ArchivoInvalido("El archivo no es un registro de vuelo DJI válido.")
        r = self.enviar()
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.data["estado"], "rechazado")
        self.assertIn("no es un registro de vuelo DJI", r.data["motivo_rechazo"])
        self.assertEqual(Operacion.objects.count(), 0)

    def test_aeronave_no_registrada_y_reenvio(self):
        self.e.aeronave.delete()
        r = self.enviar()
        self.assertEqual(r.status_code, 422)
        self.assertIn("no está registrada en la flota", r.data["motivo_rechazo"])
        Aeronave.objects.create(empresa=self.e.a, nombre="T01", modelo="Mavic 3", numero_serie="1581F45TB21BR1AE")
        self.assertEqual(self.enviar().status_code, 201)        # un rechazado se puede reenviar
        self.assertEqual(RegistroVuelo.objects.count(), 1)

    def test_bateria_no_registrada_genera_advertencia(self):
        self.e.bateria.delete()
        self.assertEqual(self.enviar().status_code, 201)
        self.assertTrue(Operacion.objects.get().eventos.filter(mensaje__contains="no está registrada").exists())

    def test_sin_token_no_se_acepta(self):
        self.assertEqual(APIClient().post(self.url, {"archivo": archivo_txt()}, format="multipart").status_code, 401)

    def test_visualizador_no_puede_enviar(self):
        self.api.credentials(HTTP_AUTHORIZATION=f"Token {self.e.token(self.e.visual_a)}")
        self.assertEqual(self.enviar().status_code, 403)

    def test_obtener_token_con_correo_y_clave(self):
        r = APIClient().post(reverse("api_token"), {"username": "piloto@a.cl", "password": CLAVE})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["token"]), 40)

    def test_piloto_solo_lista_sus_registros_y_admin_los_de_la_empresa(self):
        self.enviar()
        otro = APIClient()
        otro.credentials(HTTP_AUTHORIZATION=f"Token {self.e.token(self.e.admin_b)}")
        self.assertEqual(otro.get(self.url).data, [])                         # HU-04
        self.assertEqual(otro.get(reverse("api_registro_detalle", args=[RegistroVuelo.objects.get().pk])).status_code, 404)
        admin = APIClient()
        admin.credentials(HTTP_AUTHORIZATION=f"Token {self.e.token(self.e.admin_a)}")
        self.assertEqual(len(admin.get(self.url).data), 1)

    def test_rnf_procesa_un_registro_en_menos_de_5_segundos(self):
        inicio = time.perf_counter()
        self.enviar()
        self.assertLess(time.perf_counter() - inicio, 5)


class PantallaRegistrosTest(ConLectorDemo):
    """HU-11: el administrador ve en la web los registros recibidos y por qué se rechazó alguno."""

    def setUp(self):
        self.lector = self._parchar()
        self.e = Escenario()
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Token {self.e.token(self.e.piloto_a)}")
        api.post(reverse("api_registros"), {"archivo": archivo_txt()}, format="multipart")
        self.e.aeronave.delete()
        api.post(reverse("api_registros"), {"archivo": archivo_txt(b"otro vuelo")}, format="multipart")
        self.client.force_login(self.e.admin_a)

    def test_lista_procesados_y_rechazados(self):
        r = self.client.get(reverse("registros"))
        self.assertContains(r, "Procesado")
        self.assertContains(r, "no está registrada en la flota")

    def test_filtra_por_estado(self):
        r = self.client.get(reverse("registros") + "?estado=rechazado")
        self.assertEqual(len(r.context["object_list"]), 1)

    def test_detalle_muestra_la_operacion(self):
        r = self.client.get(reverse("registro_detalle", args=[RegistroVuelo.objects.get(estado="procesado").pk]))
        self.assertContains(r, "Operación creada automáticamente")
        self.assertContains(r, "0 min 58 s")

    def test_otra_empresa_no_ve_el_registro(self):
        self.client.force_login(self.e.admin_b)
        pk = RegistroVuelo.objects.first().pk
        self.assertEqual(self.client.get(reverse("registro_detalle", args=[pk])).status_code, 404)


class LectorRealTest(TestCase):
    """Integración con el binario dji-parser compilado (se omite si no está instalado)."""

    def setUp(self):
        if not Path(settings.DJI_PARSER_BIN).exists():
            self.skipTest("dji-parser no está compilado en este ambiente")

    def test_archivo_que_no_es_dji(self):
        ruta = Path(settings.MEDIA_ROOT) / "falso.txt"
        ruta.write_bytes(b"esto no es un registro DJI")
        with self.assertRaises(dji.ArchivoInvalido):
            dji.leer_registro(ruta)


class SaludTest(TestCase):
    def test_salud(self):
        self.assertEqual(self.client.get(reverse("salud")).json()["estado"], "ok")
