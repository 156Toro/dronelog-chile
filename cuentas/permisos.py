"""Control de acceso por rol y aislamiento de datos por empresa (HU-03, HU-04)."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from .models import Rol


class RolRequeridoMixin(LoginRequiredMixin):
    """Vista disponible solo para los roles indicados en `roles`."""

    roles = ()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.tiene_rol(*self.roles):
            raise PermissionDenied("Su rol no tiene acceso a esta sección.")
        return super().dispatch(request, *args, **kwargs)


class EmpresaMixin(RolRequeridoMixin):
    """Limita toda consulta a la empresa del usuario: nadie ve datos de otra empresa."""

    def get_queryset(self):
        return super().get_queryset().filter(empresa=self.request.user.empresa)

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["empresa"] = self.request.user.empresa
        return kwargs


class PuedeEnviarRegistros(BasePermission):
    """API: envían registros los pilotos y los administradores de una empresa."""

    message = "Su rol no puede enviar registros de vuelo."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.empresa_id and u.tiene_rol(Rol.PILOTO, Rol.ADMIN_EMPRESA))
