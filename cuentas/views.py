from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.db.models import Count
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView
from rest_framework.authtoken.models import Token

from operaciones.models import Operacion, RegistroVuelo

from .forms import EmpresaConAdminForm, IngresoForm, UsuarioForm
from .models import Empresa, Rol, Usuario
from .permisos import EmpresaMixin, RolRequeridoMixin

TODOS = (Rol.ADMIN_PLATAFORMA, Rol.ADMIN_EMPRESA, Rol.PILOTO, Rol.VISUALIZADOR)


class Ingreso(LoginView):
    template_name = "cuentas/ingreso.html"
    authentication_form = IngresoForm
    redirect_authenticated_user = True


class Inicio(RolRequeridoMixin, TemplateView):
    roles = TODOS
    template_name = "cuentas/inicio.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        u = self.request.user
        if u.es_admin_plataforma:
            ctx["empresas"] = Empresa.objects.annotate(n_usuarios=Count("usuarios")).count()
        else:
            ctx["registros"] = RegistroVuelo.objects.filter(empresa=u.empresa)
            ctx["operaciones"] = Operacion.objects.filter(empresa=u.empresa).count()
            ctx["ultimos"] = ctx["registros"].select_related("operacion")[:5]
        return ctx


class EmpresaLista(RolRequeridoMixin, ListView):
    roles = (Rol.ADMIN_PLATAFORMA,)
    model = Empresa
    template_name = "cuentas/empresas.html"

    def get_queryset(self):
        return Empresa.objects.annotate(n_usuarios=Count("usuarios", distinct=True),
                                        n_operaciones=Count("operaciones", distinct=True))


class EmpresaCrear(RolRequeridoMixin, CreateView):
    roles = (Rol.ADMIN_PLATAFORMA,)
    form_class = EmpresaConAdminForm
    template_name = "formulario.html"
    success_url = reverse_lazy("empresas")
    extra_context = {"titulo": "Nueva empresa"}

    def form_valid(self, form):
        messages.success(self.request, "Empresa y administrador creados.")
        return super().form_valid(form)


class UsuarioLista(EmpresaMixin, ListView):
    roles = (Rol.ADMIN_EMPRESA,)
    model = Usuario
    template_name = "cuentas/usuarios.html"


class UsuarioCrear(EmpresaMixin, CreateView):
    roles = (Rol.ADMIN_EMPRESA,)
    model = Usuario
    form_class = UsuarioForm
    template_name = "formulario.html"
    success_url = reverse_lazy("usuarios")
    extra_context = {"titulo": "Nuevo usuario"}


class UsuarioEditar(EmpresaMixin, UpdateView):
    roles = (Rol.ADMIN_EMPRESA,)
    model = Usuario
    form_class = UsuarioForm
    template_name = "formulario.html"
    success_url = reverse_lazy("usuarios")
    extra_context = {"titulo": "Editar usuario"}


class TokenSincronizacion(RolRequeridoMixin, TemplateView):
    """Muestra el token que usa el cliente de sincronización del control DJI (HU-08)."""

    roles = (Rol.PILOTO, Rol.ADMIN_EMPRESA)
    template_name = "cuentas/token.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["token"], _ = Token.objects.get_or_create(user=self.request.user)
        return ctx

    def post(self, request, *args, **kwargs):
        Token.objects.filter(user=request.user).delete()
        messages.success(request, "Se generó un token nuevo. Actualícelo en el cliente de sincronización.")
        return self.get(request, *args, **kwargs)
