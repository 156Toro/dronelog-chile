# Trazabilidad requerimiento → código → prueba · v0.5.0

Cada historia de usuario del Sprint 1 (Incremento 2) indica dónde se implementa y qué prueba la verifica.
Las pruebas están en `pruebas/test_unitarias.py` (U) y `pruebas/test_integracion.py` (I).

| HU | Requerimiento | Implementación | Pruebas |
|---|---|---|---|
| HU-01 | El administrador de plataforma registra una empresa y su administrador | `cuentas/forms.py` · `EmpresaConAdminForm.save`; `cuentas/views.py` · `EmpresaCrear`, `EmpresaLista` | I · `EmpresasTest` (3) |
| HU-02 | Iniciar y cerrar sesión con correo y contraseña | `cuentas/models.py` · `Usuario` (`USERNAME_FIELD = "email"`), `UsuarioManager`; `cuentas/forms.py` · `IngresoForm`; `dronelog/urls.py` · `login`, `logout` | I · `IngresoTest` (3); U · `UsuarioTest` |
| HU-03 | El administrador de empresa crea usuarios con un rol | `cuentas/models.py` · `Rol`; `cuentas/migrations/0002_roles.py`; `cuentas/forms.py` · `UsuarioForm`; `cuentas/views.py` · `UsuarioCrear`, `UsuarioEditar` | U · `RolesTest`; I · `UsuariosTest.test_crea_usuario_con_rol_en_su_empresa`, `test_no_puede_crear_admin_de_plataforma`, `test_piloto_no_gestiona_usuarios` |
| HU-04 | Cada usuario ve solo la información de su empresa | `cuentas/permisos.py` · `EmpresaMixin.get_queryset`, `RolRequeridoMixin`; `operaciones/api.py` · `RegistroListaCrear.get_queryset` | I · `UsuariosTest.test_solo_ve_usuarios_de_su_empresa`, `test_no_puede_editar_usuario_de_otra_empresa`; `FlotaTest.test_no_ve_ni_edita_flota_de_otra_empresa`; `EnvioRegistroAPITest.test_piloto_solo_lista_sus_registros_y_admin_los_de_la_empresa`; `PantallaRegistrosTest.test_otra_empresa_no_ve_el_registro` |
| HU-05 | Registrar pilotos y su credencial DGAC | `flota/models.py` · `Piloto`; `flota/forms.py` · `PilotoForm`; `flota/views.py` · `vistas_crud` | I · `FlotaTest.test_registra_piloto_con_credencial_dgac`, `test_rut_de_piloto_no_se_repite_en_la_empresa` |
| HU-06 | Registrar aeronaves con su número de serie | `flota/models.py` · `Aeronave.save`; `flota/forms.py` · `AeronaveForm` | U · `AeronaveTest`; I · `FlotaTest.test_registra_aeronave_y_serie_queda_normalizada`, `test_serie_de_aeronave_es_unica` |
| HU-07 | Registrar las baterías de cada aeronave | `flota/models.py` · `Bateria`; `flota/forms.py` · `BateriaForm`; `operaciones/ingesta.py` · `_crear_operacion` (suma ciclos) | I · `FlotaTest.test_registra_bateria_de_una_aeronave`; `EnvioRegistroAPITest.test_envio_crea_la_operacion_automaticamente` (ciclos) |
| HU-08 | El registro DJI Fly se envía solo al terminar el vuelo | `cliente_sync/sync.py` · `revisar`, `enviar`; `operaciones/api.py` · `RegistroListaCrear.create`; `cuentas/views.py` · `TokenSincronizacion` | I · `EnvioRegistroAPITest.test_envio_crea_la_operacion_automaticamente`, `test_sin_token_no_se_acepta`, `test_visualizador_no_puede_enviar`, `test_obtener_token_con_correo_y_clave` |
| HU-09 | Se descifra el archivo y se crea la operación automáticamente | `herramientas/dji-parser/src/main.rs`; `operaciones/dji.py` · `leer_registro`, `normalizar`; `operaciones/ingesta.py` · `procesar_registro`, `_crear_operacion` | U · `NormalizarTest` (6), `LectorDJITest` (5); I · `EnvioRegistroAPITest.test_envio_crea_la_operacion_automaticamente`; `LectorRealTest` (binario real) |
| HU-10 | La aeronave y la batería se reconocen por número de serie | `operaciones/ingesta.py` · `_crear_operacion` | I · `EnvioRegistroAPITest.test_envio_crea_la_operacion_automaticamente`, `test_aeronave_no_registrada_y_reenvio`, `test_bateria_no_registrada_genera_advertencia` |
| HU-11 | Aviso claro si un archivo es inválido o ya fue recibido | `operaciones/ingesta.py` · `calcular_huella`, `recibir_registro`, `RegistroDuplicado`; `operaciones/models.py` · restricción `registro_unico_por_empresa`; `operaciones/views.py` · `RegistroLista`, `RegistroDetalle` | U · `HuellaTest`; I · `EnvioRegistroAPITest.test_mismo_archivo_dos_veces_se_rechaza`, `test_extension_no_permitida`, `test_archivo_que_no_es_dji_queda_rechazado_con_motivo`; `PantallaRegistrosTest` (4) |

## Requisitos no funcionales verificados

| RNF (ISO/IEC 25010) | Verificación |
|---|---|
| Seguridad: confidencialidad entre empresas | Pruebas de HU-04: las consultas de otra empresa responden 404 |
| Seguridad: autenticación | Contraseñas con hash (`UsuarioTest`), API solo con token (`test_sin_token_no_se_acepta`), HTTPS obligatorio en producción (`settings/produccion.py`) |
| Seguridad: control de acceso por rol | Respuestas 403 para roles sin permiso (`test_admin_de_empresa_no_accede`, `test_visualizador_no_puede_enviar`, `test_visualizador_no_modifica_la_flota`) |
| Eficiencia: procesa un registro en menos de 5 s | `test_rnf_procesa_un_registro_en_menos_de_5_segundos` |
| Integridad: un vuelo no se registra dos veces | Huella SHA-256 única por empresa (`test_mismo_archivo_dos_veces_se_rechaza`) |
| Mantenibilidad: cobertura de pruebas ≥ 80 % | `coverage report` en GitHub Actions: 96 % |
