# Notas de la versión · DroneLog Chile

## v0.5.0 · Incremento 2 (Sprint 1) · Hito H3, Entrega 2

**Fecha:** 23-11-2026 · **Rama:** `main` · **Etiqueta:** `v0.5.0`

### Línea base

Esta versión forma la línea base del Hito H3. Quedan bajo control de configuración:

| Elemento | Versión | Ubicación |
|---|---|---|
| Código fuente de la aplicación | v0.5.0 | `cuentas/`, `flota/`, `operaciones/`, `dronelog/` |
| Lector de registros DJI | 0.1.0 | `herramientas/dji-parser/` |
| Cliente de sincronización | 0.5.0 | `cliente_sync/sync.py` |
| Modelo de datos (migraciones) | 0001–0002 | `*/migrations/` |
| Pruebas unitarias y de integración | 52 casos | `pruebas/` |
| Configuración por ambiente | v0.5.0 | `dronelog/settings/`, `Dockerfile`, `render.yaml`, `.github/workflows/ci.yml` |
| Documentación técnica | v0.5.0 | `README.md`, `docs/` |

### Funcionalidades nuevas (11 historias, 45 puntos)

- **HU-01** Alta de empresas con su administrador, por el administrador de plataforma.
- **HU-02** Ingreso y salida con correo y contraseña.
- **HU-03** Usuarios con uno de cuatro roles: administrador de plataforma, administrador de empresa, piloto y visualizador.
- **HU-04** Aislamiento total de datos por empresa, en la web y en la API.
- **HU-05 a HU-07** Registro de pilotos (credencial DGAC), aeronaves (número de serie) y baterías (ciclos).
- **HU-08** API REST `POST /api/v1/registros/` con token, y cliente de sincronización que envía cada registro sin intervención del piloto.
- **HU-09** Descifrado del FlightRecord con `dji-parser` y creación automática de la operación, su trayectoria y sus avisos.
- **HU-10** Reconocimiento de la aeronave y la batería por número de serie; los ciclos de la batería se suman solos.
- **HU-11** Pantalla «Registros DJI recibidos» con el estado y el motivo de cada rechazo; un mismo archivo no se registra dos veces.

### Calidad

- 52 pruebas (16 unitarias y 36 de integración), todas aprobadas; cobertura de 96 %.
- El pipeline de GitHub Actions corre las pruebas sobre PostgreSQL 16 en cada push.

### Ambientes

| Ambiente | Estado |
|---|---|
| Desarrollo | Instalación local con `runserver` (ver `docs/INSTALACION.md`) |
| Pruebas | GitHub Actions, workflow «Pruebas» |
| Producción | Render, contenedor Docker + PostgreSQL, `https://dronelog-chile.onrender.com` |

### Limitaciones conocidas

- Los archivos originales se guardan en el disco del contenedor; en el plan gratuito de Render se pierden al
  redesplegar (los datos del vuelo quedan en PostgreSQL). Se resuelve con almacenamiento de objetos en producción real.
- El procesamiento es sincrónico dentro de la petición; basta para el volumen del prototipo.
- El listado de operaciones, el detalle con mapa, el panel y los reportes corresponden al Incremento 3 (HU-12 a HU-20).

### Próxima versión

v1.0.0 · Incremento 3 (Sprints 2 y 3) · Hito H4, Entrega 3.
