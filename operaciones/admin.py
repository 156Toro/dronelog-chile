from django.contrib import admin

from .models import EventoVuelo, Operacion, PuntoTrayectoria, RegistroVuelo

admin.site.register([RegistroVuelo, Operacion, PuntoTrayectoria, EventoVuelo])
