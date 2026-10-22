# pjecz-hercules-beta-flask

Versión de PRUEBA de la Plataform Web.

## Instalación

Crear entorno virtual

```bash
python -m venv .venv
```

Activar entorno virtual

```bashbash
source .venv/bin/activate  # Linux/Mac
```

Instalar dependencias

```bash
uv sync
```

Crear un archivo para las variables de entorno

```bash
cp .env.example .env
```

Crear un archivo `.bashrc` que facilite la carga de las variables de entorno y del entorno Python

```bash
# pjecz-hercules-beta-flask

if [ -f ~/.bashrc ]; then
    . ~/.bashrc
fi

if command -v figlet &> /dev/null
then
    figlet Hercules BETA Flask
else
    echo "== Hercules BETA Flask"
fi
echo

# Google Application Credentials
export GOOGLE_APPLICATION_CREDENTIALS=

if [ -f .env ]
then
    echo "-- Variables de entorno"
    export $(grep -v '^#' .env | xargs)
    # source .env && export $(sed '/^#/d' .env | cut -d= -f1)
    echo "   AUTORIDADES_PAGINA_CABECERA_URL: ${AUTORIDADES_PAGINA_CABECERA_URL}"
    echo "   AUTORIDADES_PAGINA_PIE_URL: ${AUTORIDADES_PAGINA_PIE_URL}"
    echo "   CLOUD_STORAGE_DEPOSITO: ${CLOUD_STORAGE_DEPOSITO}"
    echo "   CLOUD_STORAGE_DEPOSITO_EDICTOS: ${CLOUD_STORAGE_DEPOSITO_EDICTOS}"
    echo "   CLOUD_STORAGE_DEPOSITO_ESTRADOS: ${CLOUD_STORAGE_DEPOSITO_ESTRADOS}"
    echo "   CLOUD_STORAGE_DEPOSITO_EXHORTOS: ${CLOUD_STORAGE_DEPOSITO_EXHORTOS}"
    echo "   CLOUD_STORAGE_DEPOSITO_GLOSAS: ${CLOUD_STORAGE_DEPOSITO_GLOSAS}"
    echo "   CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS: ${CLOUD_STORAGE_DEPOSITO_LISTAS_DE_ACUERDOS}"
    echo "   CLOUD_STORAGE_DEPOSITO_OFICIOS: ${CLOUD_STORAGE_DEPOSITO_OFICIOS}"
    echo "   CLOUD_STORAGE_DEPOSITO_PERSEO: ${CLOUD_STORAGE_DEPOSITO_PERSEO}"
    echo "   CLOUD_STORAGE_DEPOSITO_REQUISICIONES: ${CLOUD_STORAGE_DEPOSITO_REQUISICIONES}"
    echo "   CLOUD_STORAGE_DEPOSITO_SENTENCIAS: ${CLOUD_STORAGE_DEPOSITO_SENTENCIAS}"
    echo "   CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA: ${CLOUD_STORAGE_DEPOSITO_VALES_GASOLINA}"
    echo "   CLOUD_STORAGE_DEPOSITO_VSP_DIGITALIZACIONES: ${CLOUD_STORAGE_DEPOSITO_VSP_DIGITALIZACIONES}"
    echo "   DB_HOST: ${DB_HOST}"
    echo "   DB_PORT: ${DB_PORT}"
    echo "   DB_NAME: ${DB_NAME}"
    echo "   DB_USER: ${DB_USER}"
    echo "   DB_PASS: ${DB_PASS}"
    echo "   DEPLOYMENT_ENVIRONMENT: ${DEPLOYMENT_ENVIRONMENT}"
    echo "   ESTADO_CLAVE: ${ESTADO_CLAVE}"
    echo "   FERNET_KEY: ${FERNET_KEY}"
    echo "   GOOGLE_APPLICATION_CREDENTIALS: ${GOOGLE_APPLICATION_CREDENTIALS}"
    echo "   HOST: ${HOST}"
    echo "   MUNICIPIO_CLAVE: ${MUNICIPIO_CLAVE}"
    echo "   REDIS_URL: ${REDIS_URL}"
    echo "   SALT: ${SALT}"
    echo "   SQLALCHEMY_DATABASE_URI: ${SQLALCHEMY_DATABASE_URI}"
    echo "   TASK_QUEUE: ${TASK_QUEUE}"
    echo "   TZ: ${TZ}"
    echo
    export PGHOST=$DB_HOST
    export PGPORT=$DB_PORT
    export PGDATABASE=$DB_NAME
    export PGUSER=$DB_USER
    export PGPASSWORD=$DB_PASS
fi

if [ -d .venv ]
then
    echo "-- Python Virtual Environment"
    source .venv/bin/activate
    echo "   $(python3 --version)"
    export PYTHONPATH=$(pwd)
    echo "   PYTHONPATH: ${PYTHONPATH}"
    echo
    echo "-- Command Line Interface"
    alias cli="python3 cli/app.py"
    echo "   cli = python3 cli/app.py"
    echo
    echo "-- Flask 127.0.0.1:5000"
    alias arrancar="flask run --port=5000"
    echo "   arrancar = flask run --port=5000"
    echo
fi
```
