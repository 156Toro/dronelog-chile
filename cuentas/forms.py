from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction

from .models import Empresa, Rol, Usuario


class IngresoForm(AuthenticationForm):
    username = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={"autofocus": True}))

    def clean_username(self):
        return self.cleaned_data["username"].lower()


class EmpresaConAdminForm(forms.ModelForm):
    """HU-01: el administrador de plataforma crea la empresa y su primer administrador."""

    admin_nombre = forms.CharField(label="Nombre del administrador", max_length=150)
    admin_email = forms.EmailField(label="Correo del administrador")
    admin_password = forms.CharField(label="Contraseña inicial", widget=forms.PasswordInput, min_length=8)

    class Meta:
        model = Empresa
        fields = ["nombre", "rut"]

    def clean_admin_email(self):
        email = self.cleaned_data["admin_email"].lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Ya existe un usuario con ese correo.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        empresa = super().save()
        Usuario.objects.create_user(
            email=self.cleaned_data["admin_email"], password=self.cleaned_data["admin_password"],
            first_name=self.cleaned_data["admin_nombre"], empresa=empresa,
            rol=Rol.objects.get(codigo=Rol.ADMIN_EMPRESA))
        return empresa


class UsuarioForm(forms.ModelForm):
    """HU-03: el administrador de empresa crea usuarios de su empresa con un rol."""

    password = forms.CharField(label="Contraseña inicial", widget=forms.PasswordInput, min_length=8, required=False,
                               help_text="Obligatoria al crear. Déjela vacía para no cambiarla.")

    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "rol", "is_active"]
        labels = {"first_name": "Nombre", "last_name": "Apellido", "is_active": "Activo"}

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa
        # un administrador de empresa no puede crear administradores de plataforma
        self.fields["rol"].queryset = Rol.objects.exclude(codigo=Rol.ADMIN_PLATAFORMA)

    def clean_email(self):
        return self.cleaned_data["email"].lower()

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.instance.pk and not password:
            raise forms.ValidationError("Indique una contraseña inicial.")
        return password

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.empresa = self.empresa
        if self.cleaned_data.get("password"):
            usuario.set_password(self.cleaned_data["password"])
        if commit:
            usuario.save()
        return usuario
