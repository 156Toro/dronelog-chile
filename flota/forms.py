from django import forms

from .models import Aeronave, Bateria, Piloto


class EmpresaForm(forms.ModelForm):
    """Formulario que recibe la empresa del usuario para filtrar las opciones."""

    def __init__(self, *args, empresa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.empresa = empresa


class PilotoForm(EmpresaForm):
    class Meta:
        model = Piloto
        fields = ["nombre", "rut", "credencial_dgac", "vencimiento_credencial", "usuario", "activo"]
        widgets = {"vencimiento_credencial": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
        help_texts = {"usuario": "Cuenta con la que el piloto envía sus registros."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = self.empresa.usuarios.filter(rol__codigo="piloto") if self.empresa else None

    def clean_rut(self):
        rut = self.cleaned_data["rut"].replace(".", "").upper()
        qs = Piloto.objects.filter(empresa=self.empresa, rut=rut).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un piloto con ese RUT en su empresa.")
        return rut


class AeronaveForm(EmpresaForm):
    class Meta:
        model = Aeronave
        fields = ["nombre", "modelo", "numero_serie", "activa"]

    def clean_numero_serie(self):
        return self.cleaned_data["numero_serie"].strip().upper()


class BateriaForm(EmpresaForm):
    class Meta:
        model = Bateria
        fields = ["numero_serie", "aeronave", "activa"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["aeronave"].queryset = self.empresa.aeronaves.all() if self.empresa else None

    def clean_numero_serie(self):
        return self.cleaned_data["numero_serie"].strip().upper()
