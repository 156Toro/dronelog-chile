"""API REST v1. El cliente de sincronización del control DJI envía aquí cada registro (HU-08)."""
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from cuentas.models import Rol
from cuentas.permisos import PuedeEnviarRegistros

from .ingesta import ArchivoNoPermitido, RegistroDuplicado, recibir_registro
from .models import RegistroVuelo
from .serializers import EnvioRegistroSerializer, RegistroVueloSerializer


class RegistroListaCrear(generics.ListCreateAPIView):
    """GET: registros de la empresa (el piloto ve solo los suyos). POST: envía un registro DJI."""

    permission_classes = [PuedeEnviarRegistros]
    parser_classes = [MultiPartParser]
    serializer_class = RegistroVueloSerializer

    def get_queryset(self):
        qs = RegistroVuelo.objects.filter(empresa=self.request.user.empresa).select_related("operacion")
        if self.request.user.tiene_rol(Rol.PILOTO):
            qs = qs.filter(enviado_por=self.request.user)
        return qs

    def create(self, request, *args, **kwargs):
        envio = EnvioRegistroSerializer(data=request.data)
        envio.is_valid(raise_exception=True)
        try:
            registro = recibir_registro(request.user, envio.validated_data["archivo"])
        except RegistroDuplicado as e:
            return Response({"detalle": e.mensaje, "registro": e.registro.pk}, status=status.HTTP_409_CONFLICT)
        except ArchivoNoPermitido as e:
            return Response({"detalle": e.mensaje}, status=status.HTTP_400_BAD_REQUEST)
        codigo = status.HTTP_201_CREATED if registro.estado == RegistroVuelo.PROCESADO \
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response(RegistroVueloSerializer(registro).data, status=codigo)


class RegistroDetalle(generics.RetrieveAPIView):
    permission_classes = [PuedeEnviarRegistros]
    serializer_class = RegistroVueloSerializer

    def get_queryset(self):
        return RegistroVuelo.objects.filter(empresa=self.request.user.empresa)
