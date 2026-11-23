from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from cuentas.models import Rol
from cuentas.permisos import EmpresaMixin

from .forms import AeronaveForm, BateriaForm, PilotoForm
from .models import Aeronave, Bateria, Piloto


def vistas_crud(modelo, form, nombre, plural, columnas, titulo_lista=None):
    """Crea las vistas listar/crear/editar de un recurso de la flota, siempre filtradas por empresa."""
    base = {"roles": (Rol.ADMIN_EMPRESA,), "model": modelo}
    extra = {"nombre": nombre, "plural": plural, "columnas": columnas, "url_base": plural.lower(), "titulo_lista": titulo_lista or plural}
    lista = type(f"{modelo.__name__}Lista", (EmpresaMixin, ListView),
                 {**base, "template_name": "flota/lista.html", "extra_context": extra})
    editar_base = {**base, "form_class": form, "template_name": "formulario.html",
                   "success_url": reverse_lazy(extra["url_base"])}
    crear = type(f"{modelo.__name__}Crear", (EmpresaMixin, CreateView),
                 {**editar_base, "extra_context": {"titulo": f"Registrar {nombre.lower()}"}})
    editar = type(f"{modelo.__name__}Editar", (EmpresaMixin, UpdateView),
                  {**editar_base, "extra_context": {"titulo": f"Editar {nombre.lower()}"}})
    return lista, crear, editar


PilotoLista, PilotoCrear, PilotoEditar = vistas_crud(
    Piloto, PilotoForm, "Piloto", "Pilotos",
    [("nombre", "Nombre"), ("rut", "RUT"), ("credencial_dgac", "Credencial DGAC"),
     ("vencimiento_credencial", "Vence"), ("usuario", "Usuario"), ("activo", "Activo")])
AeronaveLista, AeronaveCrear, AeronaveEditar = vistas_crud(
    Aeronave, AeronaveForm, "Aeronave", "Aeronaves",
    [("nombre", "Nombre"), ("modelo", "Modelo"), ("numero_serie", "N.º de serie"), ("activa", "Activa")])
BateriaLista, BateriaCrear, BateriaEditar = vistas_crud(
    Bateria, BateriaForm, "Batería", "Baterias",
    [("numero_serie", "N.º de serie"), ("aeronave", "Aeronave"), ("ciclos", "Ciclos"), ("activa", "Activa")], "Baterías")
