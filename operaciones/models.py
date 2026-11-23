"""Registros DJI recibidos y operaciones creadas a partir de ellos (HU-08 a HU-11)."""
from django.conf import settings
from django.db import models

from cuentas.models import Empresa
from flota.models import Aeronave, Bateria, Piloto


def ruta_registro(instancia, nombre):
    return f"registros/{instancia.empresa_id}/{instancia.huella_sha256[:2]}/{instancia.huella_sha256}.txt"


class RegistroVuelo(models.Model):
    """Archivo FlightRecord recibido por la API. Su huella SHA-256 impide registrarlo dos veces."""

    RECIBIDO = "recibido"
    PROCESADO = "procesado"
    RECHAZADO = "rechazado"
    ESTADOS = [(RECIBIDO, "Recibido"), (PROCESADO, "Procesado"), (RECHAZADO, "Rechazado")]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="registros")
    enviado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="registros")
    archivo = models.FileField(upload_to=ruta_registro)
    nombre_original = models.CharField(max_length=255)
    tamano_bytes = models.PositiveBigIntegerField()
    huella_sha256 = models.CharField(max_length=64)
    version_formato = models.PositiveSmallIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default=RECIBIDO)
    motivo_rechazo = models.TextField(blank=True)
    recibido_en = models.DateTimeField(auto_now_add=True)
    procesado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-recibido_en"]
        verbose_name = "registro de vuelo"
        verbose_name_plural = "registros de vuelo"
        constraints = [models.UniqueConstraint(fields=["empresa", "huella_sha256"], name="registro_unico_por_empresa")]

    def __str__(self):
        return self.nombre_original


class Operacion(models.Model):
    """Vuelo creado automáticamente desde un registro DJI."""

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="operaciones")
    registro = models.OneToOneField(RegistroVuelo, on_delete=models.CASCADE, related_name="operacion")
    piloto = models.ForeignKey(Piloto, null=True, blank=True, on_delete=models.SET_NULL, related_name="operaciones")
    aeronave = models.ForeignKey(Aeronave, null=True, blank=True, on_delete=models.SET_NULL, related_name="operaciones")
    bateria = models.ForeignKey(Bateria, null=True, blank=True, on_delete=models.SET_NULL, related_name="operaciones")
    modelo_aeronave = models.CharField(max_length=80, blank=True)
    serie_aeronave = models.CharField(max_length=40, blank=True)
    serie_bateria = models.CharField(max_length=40, blank=True)
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    duracion_s = models.FloatField("duración (s)")
    distancia_m = models.FloatField("distancia (m)", default=0)
    altura_max_m = models.FloatField("altura máxima (m)", default=0)
    velocidad_max_ms = models.FloatField("velocidad horizontal máxima (m/s)", default=0)
    bateria_inicio_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    bateria_fin_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    latitud_inicio = models.FloatField(null=True, blank=True)
    longitud_inicio = models.FloatField(null=True, blank=True)
    lugar = models.CharField(max_length=200, blank=True)
    mision = models.CharField(max_length=200, blank=True)
    observaciones = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "operación"
        verbose_name_plural = "operaciones"

    def __str__(self):
        return f"Vuelo {self.inicio:%d-%m-%Y %H:%M} · {self.serie_aeronave}"

    @property
    def duracion_texto(self):
        minutos, segundos = divmod(int(round(self.duracion_s)), 60)
        return f"{minutos} min {segundos:02d} s"


class PuntoTrayectoria(models.Model):
    operacion = models.ForeignKey(Operacion, on_delete=models.CASCADE, related_name="puntos")
    segundo = models.FloatField()
    latitud = models.FloatField()
    longitud = models.FloatField()
    altura_m = models.FloatField()
    bateria_pct = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["operacion", "segundo"]
        verbose_name = "punto de trayectoria"


class EventoVuelo(models.Model):
    AVISO = "aviso"
    ADVERTENCIA = "advertencia"
    TIPOS = [(AVISO, "Aviso"), (ADVERTENCIA, "Advertencia")]

    operacion = models.ForeignKey(Operacion, on_delete=models.CASCADE, related_name="eventos")
    segundo = models.FloatField()
    tipo = models.CharField(max_length=12, choices=TIPOS)
    mensaje = models.CharField(max_length=300)

    class Meta:
        ordering = ["operacion", "segundo"]
        verbose_name = "evento de vuelo"
