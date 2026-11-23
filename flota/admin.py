from django.contrib import admin

from .models import Aeronave, Bateria, Piloto

admin.site.register([Piloto, Aeronave, Bateria])
