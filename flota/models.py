"""Pilotos, aeronaves y baterías de cada empresa (HU-05, HU-06, HU-07)."""
from django.conf import settings
from django.db import models

from cuentas.models import Empresa


class Piloto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="pilotos")
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="piloto")
    nombre = models.CharField(max_length=120)
    rut = models.CharField("RUT", max_length=12)
    credencial_dgac = models.CharField("credencial DGAC", max_length=30)
    vencimiento_credencial = models.DateField("vencimiento de la credencial")
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["empresa", "rut"], name="piloto_rut_unico_por_empresa")]

    def __str__(self):
        return self.nombre


class Aeronave(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="aeronaves")
    nombre = models.CharField(max_length=80, help_text="Nombre interno, por ejemplo 'Mavic 3 T01'")
    modelo = models.CharField(max_length=80)
    numero_serie = models.CharField("número de serie", max_length=40, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def save(self, *args, **kwargs):
        self.numero_serie = self.numero_serie.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.numero_serie})"


class Bateria(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="baterias")
    aeronave = models.ForeignKey(Aeronave, null=True, blank=True, on_delete=models.SET_NULL, related_name="baterias")
    numero_serie = models.CharField("número de serie", max_length=40, unique=True)
    ciclos = models.PositiveIntegerField(default=0, help_text="Vuelos registrados con esta batería")
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["numero_serie"]
        verbose_name = "batería"

    def save(self, *args, **kwargs):
        self.numero_serie = self.numero_serie.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.numero_serie
