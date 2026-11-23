# Etapa 1: compila el lector de registros DJI (Rust)
FROM rust:1-slim AS lector
WORKDIR /src
COPY herramientas/dji-parser/ .
RUN cargo build --release

# Etapa 2: aplicación Django
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=dronelog.settings.produccion \
    DJI_PARSER_BIN=/usr/local/bin/dji-parser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=lector /src/target/release/dji-parser /usr/local/bin/dji-parser
RUN DJANGO_SECRET_KEY=solo-para-collectstatic python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py cargar_demo && gunicorn dronelog.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
