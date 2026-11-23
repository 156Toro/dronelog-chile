from django.db import migrations

ROLES = [
    ("admin_plataforma", "Administrador de plataforma"),
    ("admin_empresa", "Administrador de empresa"),
    ("piloto", "Piloto"),
    ("visualizador", "Visualizador"),
]


def crear_roles(apps, schema_editor):
    Rol = apps.get_model("cuentas", "Rol")
    for codigo, nombre in ROLES:
        Rol.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre})


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0001_initial")]
    operations = [migrations.RunPython(crear_roles, migrations.RunPython.noop)]
