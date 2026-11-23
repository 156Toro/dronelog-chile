from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Empresa, Rol, Usuario

admin.site.register(Empresa)
admin.site.register(Rol)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ["email"]
    list_display = ["email", "first_name", "empresa", "rol", "is_active"]
    fieldsets = ((None, {"fields": ("email", "password", "first_name", "last_name", "empresa", "rol",
                                     "is_active", "is_staff", "is_superuser")}),)
    add_fieldsets = ((None, {"fields": ("email", "password1", "password2", "empresa", "rol")}),)
