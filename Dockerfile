# Use an official Python runtime as a parent image
FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Traer el binario oficial de uv directamente desde su imagen distroless
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Crear un directorio de trabajo para la aplicación
WORKDIR /app

# Optimizar el comportamiento de uv y python en Docker
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copiar especificaciones de dependencias primero para aprovechar el caché de Docker
COPY pyproject.toml uv.lock ./

# Sincronizar dependencias
RUN uv sync --frozen --no-dev

# Copiar el código fuente de tu aplicación Flask
COPY . .

# Agregar el entorno virtual generado por uv directamente al PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# Exponer el puerto de producción
EXPOSE 5000

# Lanzar la aplicación Flask usando Gunicorn
# - workers: número de procesos de trabajo en paralelo (núcleos de CPU * 2 + 1)
# - threads: número de hilos por proceso de trabajo en 2
# - worker-class gthread: usar hilos en lugar de procesos para manejar múltiples solicitudes
# - bind: dirección y puerto donde escuchar
# - keep-alive: tiempo de espera para mantener las conexiones vivas
CMD ["gunicorn", "--workers", "4", "--threads", "2", "--worker-class", "gthread", "--bind", "0.0.0.0:5000", "--keep-alive", "5", "pjecz_hercules_beta_flask.app:create_app()"]
