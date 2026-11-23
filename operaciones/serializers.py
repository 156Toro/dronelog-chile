from rest_framework import serializers

from .models import Operacion, RegistroVuelo


class OperacionResumenSerializer(serializers.ModelSerializer):
    aeronave = serializers.StringRelatedField()
    piloto = serializers.StringRelatedField()

    class Meta:
        model = Operacion
        fields = ["id", "inicio", "fin", "duracion_s", "distancia_m", "altura_max_m", "aeronave", "piloto",
                  "serie_bateria", "lugar"]


class RegistroVueloSerializer(serializers.ModelSerializer):
    operacion = OperacionResumenSerializer(read_only=True)
    enviado_por = serializers.StringRelatedField()

    class Meta:
        model = RegistroVuelo
        fields = ["id", "nombre_original", "tamano_bytes", "huella_sha256", "version_formato", "estado",
                  "motivo_rechazo", "recibido_en", "procesado_en", "enviado_por", "operacion"]


class EnvioRegistroSerializer(serializers.Serializer):
    archivo = serializers.FileField(help_text="FlightRecord_*.txt de DJI Fly")
