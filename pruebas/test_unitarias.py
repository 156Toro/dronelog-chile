"""Pruebas unitarias: funciones y modelos aislados, sin HTTP."""
import io
import subprocess
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from cuentas.models import Rol, Usuario
from flota.models import Aeronave
from operaciones import dji
from operaciones.ingesta import calcular_huella

from .utilidades import crear_usuario, datos_vuelo


class RolesTest(TestCase):
    def test_existen_los_cuatro_roles(self):
        """HU-03: la migración crea los cuatro roles del sistema."""
        self.assertEqual(set(Rol.objects.values_list("codigo", flat=True)),
                         {"admin_plataforma", "admin_empresa", "piloto", "visualizador"})


class UsuarioTest(TestCase):
    def test_correo_se_guarda_en_minusculas_y_clave_cifrada(self):
        """HU-02 / RNF seguridad: el correo se normaliza y la contraseña nunca se guarda en claro."""
        u = crear_usuario("Piloto@Vigilance.CL", Rol.PILOTO)
        self.assertEqual(u.email, "piloto@vigilance.cl")
        self.assertNotIn("ClaveSegura2026", u.password)
        self.assertTrue(u.check_password("ClaveSegura2026"))

    def test_superusuario_es_admin_de_plataforma(self):
        u = Usuario.objects.create_superuser(email="root@dronelog.cl", password="x" * 10)
        self.assertTrue(u.es_admin_plataforma)


class AeronaveTest(TestCase):
    def test_numero_de_serie_se_normaliza(self):
        """HU-06: la serie se guarda sin espacios y en mayúsculas para reconocerla después."""
        from cuentas.models import Empresa
        e = Empresa.objects.create(nombre="X", rut="1-9")
        a = Aeronave.objects.create(empresa=e, nombre="T01", modelo="Mavic 3", numero_serie=" 1581f45tb21br1ae ")
        self.assertEqual(a.numero_serie, "1581F45TB21BR1AE")


class NormalizarTest(SimpleTestCase):
    """HU-09 / HU-10: conversión de la salida del lector DJI a una operación."""

    def test_vuelo_real(self):
        v = dji.normalizar(datos_vuelo())
        self.assertEqual(v["duracion_s"], 57.8)
        self.assertEqual(v["serie_aeronave"], "1581F45TB21BR1AE")
        self.assertEqual(v["serie_bateria"], "4ERPJBSDA055RA")
        self.assertEqual(v["bateria_inicio_pct"], 28)
        self.assertEqual(v["modelo_aeronave"], "DJI Mavic 3 cursos")
        self.assertEqual((v["fin"] - v["inicio"]).total_seconds(), 57.8)

    def test_descarta_coordenadas_sin_gps(self):
        """El vuelo de prueba fue bajo techo (0 satélites): no se guardan puntos en (0, 0)."""
        self.assertEqual(dji.normalizar(datos_vuelo())["puntos"], [])

    def test_guarda_puntos_con_gps_valido(self):
        datos = datos_vuelo()
        for i, f in enumerate(datos["frames"]):
            f["osd"]["latitude"], f["osd"]["longitude"] = -33.45 + i * 1e-5, -70.66
        v = dji.normalizar(datos)
        self.assertEqual(len(v["puntos"]), len(datos["frames"]))
        self.assertAlmostEqual(v["latitud_inicio"], -33.45)

    def test_sin_frames_es_invalido(self):
        with self.assertRaises(dji.ArchivoInvalido):
            dji.normalizar({"details": {}, "frames": []})

    def test_duracion_cero_es_invalida(self):
        datos = datos_vuelo()
        datos["details"]["totalTime"] = 0
        for f in datos["frames"]:
            f["osd"]["flyTime"] = 0
        with self.assertRaises(dji.ArchivoInvalido):
            dji.normalizar(datos)

    def test_registra_avisos_del_vuelo(self):
        eventos = dji.normalizar(datos_vuelo())["eventos"]
        self.assertTrue(any("EngineStart" in e["mensaje"] for e in eventos))


class LectorDJITest(SimpleTestCase):
    """HU-09 / HU-11: traducción de los códigos de salida de dji-parser."""

    def _ejecutar(self, codigo, stdout="", stderr=""):
        resultado = subprocess.CompletedProcess([], codigo, stdout=stdout, stderr=stderr)
        with mock.patch("operaciones.dji.os.path.exists", return_value=True), \
                mock.patch("operaciones.dji.subprocess.run", return_value=resultado):
            return dji.leer_registro("/tmp/x.txt")

    def test_salida_correcta(self):
        self.assertEqual(self._ejecutar(0, '{"version": 14, "frames": []}')["version"], 14)

    def test_archivo_no_dji(self):
        with self.assertRaises(dji.ArchivoInvalido):
            self._ejecutar(2, stderr="invalid")

    def test_no_se_puede_descifrar(self):
        with self.assertRaisesMessage(dji.ErrorDescifrado, "falta la variable DJI_API_KEY"):
            self._ejecutar(3, stderr="falta la variable DJI_API_KEY")

    def test_respuesta_ilegible(self):
        with self.assertRaises(dji.ErrorLectura):
            self._ejecutar(0, "no es json")

    @override_settings(DJI_PARSER_BIN="/no/existe")
    def test_lector_no_instalado(self):
        with self.assertRaisesMessage(dji.ErrorLectura, "no está instalado"):
            dji.leer_registro("/tmp/x.txt")


class HuellaTest(SimpleTestCase):
    def test_huella_sha256_es_estable(self):
        """HU-11: dos envíos del mismo archivo producen la misma huella."""
        a = SimpleUploadedFile("a.txt", b"contenido")
        b = SimpleUploadedFile("b.txt", b"contenido")
        self.assertEqual(calcular_huella(a), calcular_huella(b))
        self.assertEqual(len(calcular_huella(a)), 64)
        self.assertNotEqual(calcular_huella(a), calcular_huella(SimpleUploadedFile("c.txt", b"otro")))
