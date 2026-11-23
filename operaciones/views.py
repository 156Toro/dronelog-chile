from django.views.generic import DetailView, ListView

from cuentas.models import Rol
from cuentas.permisos import EmpresaMixin

from .models import RegistroVuelo


class RegistroLista(EmpresaMixin, ListView):
    """Pantalla M2: registros DJI recibidos y su estado (HU-11)."""

    roles = (Rol.ADMIN_EMPRESA, Rol.PILOTO)
    model = RegistroVuelo
    template_name = "operaciones/registros.html"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset().select_related("enviado_por", "operacion__aeronave")
        if self.request.user.tiene_rol(Rol.PILOTO):
            qs = qs.filter(enviado_por=self.request.user)
        estado = self.request.GET.get("estado")
        return qs.filter(estado=estado) if estado else qs


class RegistroDetalle(EmpresaMixin, DetailView):
    roles = (Rol.ADMIN_EMPRESA, Rol.PILOTO)
    model = RegistroVuelo
    template_name = "operaciones/registro_detalle.html"

    def get_queryset(self):
        qs = super().get_queryset().select_related("operacion__aeronave", "operacion__bateria", "operacion__piloto")
        if self.request.user.tiene_rol(Rol.PILOTO):
            qs = qs.filter(enviado_por=self.request.user)
        return qs
