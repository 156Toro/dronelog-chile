from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.http import JsonResponse
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from cuentas import views as c
from flota import views as f
from operaciones import api, views as o


def salud(request):
    return JsonResponse({"estado": "ok", "version": settings.VERSION})


urlpatterns = [
    path("", c.Inicio.as_view(), name="inicio"),
    path("ingresar/", c.Ingreso.as_view(), name="login"),
    path("salir/", LogoutView.as_view(), name="logout"),
    path("empresas/", c.EmpresaLista.as_view(), name="empresas"),
    path("empresas/nueva/", c.EmpresaCrear.as_view(), name="empresa_crear"),
    path("usuarios/", c.UsuarioLista.as_view(), name="usuarios"),
    path("usuarios/nuevo/", c.UsuarioCrear.as_view(), name="usuario_crear"),
    path("usuarios/<int:pk>/", c.UsuarioEditar.as_view(), name="usuario_editar"),
    path("sincronizacion/", c.TokenSincronizacion.as_view(), name="token"),
    path("pilotos/", f.PilotoLista.as_view(), name="pilotos"),
    path("pilotos/nuevo/", f.PilotoCrear.as_view(), name="pilotos_crear"),
    path("pilotos/<int:pk>/", f.PilotoEditar.as_view(), name="pilotos_editar"),
    path("aeronaves/", f.AeronaveLista.as_view(), name="aeronaves"),
    path("aeronaves/nueva/", f.AeronaveCrear.as_view(), name="aeronaves_crear"),
    path("aeronaves/<int:pk>/", f.AeronaveEditar.as_view(), name="aeronaves_editar"),
    path("baterias/", f.BateriaLista.as_view(), name="baterias"),
    path("baterias/nueva/", f.BateriaCrear.as_view(), name="baterias_crear"),
    path("baterias/<int:pk>/", f.BateriaEditar.as_view(), name="baterias_editar"),
    path("registros/", o.RegistroLista.as_view(), name="registros"),
    path("registros/<int:pk>/", o.RegistroDetalle.as_view(), name="registro_detalle"),
    path("api/v1/token/", obtain_auth_token, name="api_token"),
    path("api/v1/registros/", api.RegistroListaCrear.as_view(), name="api_registros"),
    path("api/v1/registros/<int:pk>/", api.RegistroDetalle.as_view(), name="api_registro_detalle"),
    path("salud/", salud, name="salud"),
    path("admin/", admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
