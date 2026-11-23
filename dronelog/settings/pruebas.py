"""Ambiente de pruebas: lo usan `manage.py test` y GitHub Actions (PostgreSQL de servicio)."""
from .base import *  # noqa: F401,F403
import tempfile

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # acelera las pruebas
MEDIA_ROOT = tempfile.mkdtemp(prefix="dronelog-pruebas-")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
