"""Empresas, roles y usuarios (HU-01, HU-02, HU-03, HU-04)."""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Empresa(models.Model):
    """Cliente de la plataforma. Todo dato operacional pertenece a una empresa."""

    nombre = models.CharField(max_length=120, unique=True)
    rut = models.CharField("RUT", max_length=12, unique=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Rol(models.Model):
    """Los cuatro roles del sistema."""

    ADMIN_PLATAFORMA = "admin_plataforma"
    ADMIN_EMPRESA = "admin_empresa"
    PILOTO = "piloto"
    VISUALIZADOR = "visualizador"
    CODIGOS = [
        (ADMIN_PLATAFORMA, "Administrador de plataforma"),
        (ADMIN_EMPRESA, "Administrador de empresa"),
        (PILOTO, "Piloto"),
        (VISUALIZADOR, "Visualizador"),
    ]

    codigo = models.CharField(max_length=30, choices=CODIGOS, unique=True)
    nombre = models.CharField(max_length=60)

    class Meta:
        verbose_name_plural = "roles"

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio")
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        extra.setdefault("rol", Rol.objects.get_or_create(
            codigo=Rol.ADMIN_PLATAFORMA, defaults={"nombre": "Administrador de plataforma"})[0])
        return self._crear(email, password, **extra)


class Usuario(AbstractUser):
    """Usuario que inicia sesión con su correo. Pertenece a una empresa (salvo el admin de plataforma)."""

    username = None
    email = models.EmailField("correo", unique=True)
    empresa = models.ForeignKey(Empresa, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, related_name="usuarios")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UsuarioManager()

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.get_full_name() or self.email

    def tiene_rol(self, *codigos):
        return self.rol.codigo in codigos

    @property
    def es_admin_plataforma(self):
        return self.tiene_rol(Rol.ADMIN_PLATAFORMA)

    @property
    def es_admin_empresa(self):
        return self.tiene_rol(Rol.ADMIN_EMPRESA)
