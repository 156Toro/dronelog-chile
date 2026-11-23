# Instalación y ambientes · DroneLog Chile v0.5.0

DroneLog Chile se ejecuta en tres ambientes separados. Cada uno tiene su propio archivo de configuración
en `dronelog/settings/` y su propia base de datos.

| Ambiente | Dónde | Configuración | Base de datos | Para qué |
|---|---|---|---|---|
| Desarrollo | PC del desarrollador | `dronelog.settings.desarrollo` (`DEBUG=True`) | SQLite local o PostgreSQL local | Programar y probar a mano |
| Pruebas | GitHub Actions, en cada push y pull request | `dronelog.settings.pruebas` | PostgreSQL 16 de servicio, nueva en cada ejecución | Pruebas unitarias y de integración, cobertura |
| Producción | Render (contenedor Docker) | `dronelog.settings.produccion` (`DEBUG=False`, HTTPS obligatorio) | PostgreSQL administrado de Render | Uso por las empresas y demostración |

Flujo de liberación: rama de trabajo → pull request → **Pruebas** en verde → merge a `main` →
etiqueta `vX.Y.Z` → Render despliega `main` automáticamente.

## Requisitos

- Python 3.12 o superior y Git.
- Rust (solo para compilar el lector DJI en desarrollo): https://rustup.rs
- Una App Key de DJI Open API (developer.dji.com) para descifrar registros reales de la versión 13 o posterior.

## 1. Ambiente de desarrollo

```bash
git clone https://github.com/156Toro/dronelog-chile.git
cd dronelog-chile
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cargo build --release --manifest-path herramientas/dji-parser/Cargo.toml
python manage.py migrate
python manage.py cargar_demo
python manage.py runserver
```

Para descifrar registros reales, define la App Key antes de `runserver`:

```bash
export DJI_API_KEY="tu-app-key"           # PowerShell: $env:DJI_API_KEY="tu-app-key"
```

Para usar PostgreSQL local en vez de SQLite: `export DATABASE_URL=postgres://usuario:clave@localhost:5432/dronelog`.

## 2. Ambiente de pruebas

Se ejecuta solo con `.github/workflows/ci.yml` en cada push. Para correrlo en el PC:

```bash
DJANGO_SETTINGS_MODULE=dronelog.settings.pruebas coverage run manage.py test pruebas -v 2
coverage report
```

## 3. Ambiente de producción (Render)

1. Entra a https://render.com con tu cuenta de GitHub.
2. **New → Blueprint** y elige el repositorio `156Toro/dronelog-chile`. Render lee `render.yaml` y crea
   el servicio web `dronelog-chile` (Docker) y la base `dronelog-db` (PostgreSQL).
3. Cuando lo pida, ingresa las variables secretas:
   - `DJI_API_KEY`: tu App Key de DJI Open API.
   - `DRONELOG_DEMO_PASSWORD`: contraseña de los usuarios de demostración.
4. Pulsa **Apply**. El primer despliegue tarda unos 5 a 8 minutos porque compila el lector DJI.
5. Verifica `https://dronelog-chile.onrender.com/salud/`; debe responder `{"estado": "ok", "version": "0.5.0"}`.

Al iniciar, el contenedor aplica las migraciones y carga los datos de demostración (idempotente).
Si el nombre `dronelog-chile` ya está ocupado, Render asigna uno parecido (por ejemplo `dronelog-chile-xxxx.onrender.com`); la aplicación lo acepta sola mediante la variable `RENDER_EXTERNAL_HOSTNAME`. Para usar un dominio propio, agrégalo en Settings → Custom Domains y en `DJANGO_ALLOWED_HOSTS`.

Limitaciones del plan gratuito (aceptables para un prototipo): el servicio se suspende tras 15 minutos sin
uso y tarda cerca de un minuto en despertar, y la base gratuita vence a los 30 días.

## 4. Cliente de sincronización

En el equipo donde DJI Fly guarda los registros (control o PC):

```bash
python cliente_sync/sync.py --api https://dronelog-chile.onrender.com --token TU_TOKEN \
    --carpeta "RUTA/DJI/FlightRecord"
```

El token aparece en la web, en **Sincronización**. El cliente revisa la carpeta cada 30 segundos y envía
cada registro nuevo; los ya enviados se recuerdan en `~/.dronelog_enviados.json`.
