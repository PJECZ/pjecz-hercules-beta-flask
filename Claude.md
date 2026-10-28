# CLAUDE.md — Aplicación Web Flask

Guía de contexto para Claude Code al trabajar en este proyecto.

---

## Descripción del proyecto

Aplicación web construida con **Flask** y base de datos **PostgreSQL**.
Backend en Python, orientada a ser mantenible, segura y lista para producción.
Usa Bootstrap para el frontend, con enfoque en usabilidad y profesionalismo.

---

## Stack tecnológico

| Capa         | Tecnología                          |
|--------------|-------------------------------------|
| Lenguaje     | Python 3.14                         |
| Framework    | Flask 3.1.3                         |
| Base de datos| PostgreSQL (psycopg2 / SQLAlchemy)  |
| ORM          | SQLAlchemy + Flask-SQLAlchemy       |
| Autenticación| Flask-Login                         |
| Formularios  | Flask-WTF (WTForms)                 |
| Variables de entorno | pydantic-settings (.env) + Google Secret Manager |
| Gestor de paquetes | uv (build backend `uv_build`) |
| Tareas en segundo plano | RQ + Redis                 |
| CLI          | Typer                               |
| Servidor dev | Flask built-in (debug=True)         |
| Servidor prod| Gunicorn + Google Cloud App Engine  |

---

## Estructura del proyecto

El código vive bajo `src/` (layout de paquete instalable con uv).

```
pjecz-hercules-beta-flask/
├── src/
│   └── pjecz_hercules_beta_flask/       # Paquete de la aplicación
│       ├── __init__.py
│       ├── main.py                      # Aplicación Flask: registra blueprints y extensiones
│       ├── blueprints/                  # Blueprints organizados por módulos
│       │   ├── __init__.py
│       │   └── <MODULO>/                # Módulo específico (ej. ofi_plantillas)
│       │       ├── __init__.py
│       │       ├── forms.py             # Formularios WTForms (si aplica)
│       │       ├── models.py            # Modelos SQLAlchemy
│       │       ├── tasks.py             # Tareas asíncronas RQ (si aplica)
│       │       ├── views.py             # Rutas y lógica de vistas
│       │       └── templates/<MODULO>/  # Plantillas del módulo
│       │           └── *.jinja2         # list, detail, new, edit, etc.
│       ├── cli/                         # Línea de comandos (Typer)
│       │   ├── app.py                   # Punto de entrada del CLI
│       │   └── commands/                # Un archivo por grupo de comandos (db, usuarios, modulos...)
│       ├── config/
│       │   ├── extensions.py            # database, csrf, login_manager, moment, pwd_context
│       │   ├── firebase.py
│       │   └── settings.py              # Settings (pydantic-settings) y get_secret()
│       ├── lib/                         # Librerías auxiliares (datatables, storage, folio, safe_string...)
│       ├── static/                      # css/, img/, js/
│       └── templates/                   # Plantillas globales
│           ├── layouts/                 # app, base, checkout, error, login, print
│           └── macros/                  # card, detail, flash, form, list, modals, navigation...
├── seed/                                # Datos semilla para la base de datos
├── tests/                               # Pruebas
├── appserver.py                         # Arranque local y para Gunicorn (gunicorn_app)
├── app.yaml                             # Despliegue en Google Cloud App Engine
├── .env                                 # Variables locales (NO en git)
├── .env.example                         # Plantilla de variables de entorno
├── pyproject.toml                       # Dependencias y configuración del proyecto
└── uv.lock                              # Versiones fijadas por uv
```

Las importaciones son absolutas desde el paquete, por ejemplo:

```python
from pjecz_hercules_beta_flask.blueprints.usuarios.models import Usuario
from pjecz_hercules_beta_flask.config.extensions import database
```

---

## Configuración (config/settings.py)

`get_secret()` lee de las variables de entorno cuando `PROJECT_ID` está vacío (desarrollo),
y de **Google Cloud Secret Manager** cuando está definido (producción, con prefijo `SERVICE_PREFIX`).

```python
class Settings(BaseSettings):
    """Settings"""

    # Variables de entorno
    AUTORIDADES_PAGINA_CABECERA_URL: str = get_secret("AUTORIDADES_PAGINA_CABECERA_URL")
    AUTORIDADES_PAGINA_PIE_URL: str = get_secret("AUTORIDADES_PAGINA_PIE_URL")
    CLOUD_STORAGE_DEPOSITO: str = get_secret("CLOUD_STORAGE_DEPOSITO")
    CLOUD_STORAGE_DEPOSITO_EDICTOS: str = get_secret("CLOUD_STORAGE_DEPOSITO_EDICTOS")
    # ... un CLOUD_STORAGE_DEPOSITO_* por cada módulo que sube archivos
    ESTADO_CLAVE: str = get_secret("ESTADO_CLAVE", "05")
    HOST: str = get_secret("HOST", "http://127.0.0.1:5000")
    MUNICIPIO_CLAVE: str = get_secret("MUNICIPIO_CLAVE", "030")
    PREFIX: str = get_secret("PREFIX")
    SECRET_KEY: str = get_secret("SECRET_KEY")
    SALT: str = get_secret("SALT")
    SQLALCHEMY_DATABASE_URI: str = get_secret("SQLALCHEMY_DATABASE_URI")
    TZ: str = get_secret("TZ", "America/Mexico_City")

    # Incrementar el tamaño de lo que se sube en los formularios
    MAX_CONTENT_LENGTH: int = 24 * 1024 * 1024
    MAX_FORM_MEMORY_SIZE: int = 24 * 1024 * 1024
```

> Nunca poner credenciales en código. Siempre usar variables de entorno.
> Al agregar una variable nueva, añadirla también a `.env.example`.

---

## Aplicación (main.py)

```python
app = Flask(__name__, instance_relative_config=True)
app.add_url_rule("/favicon.ico", endpoint="sistemas.favicon")
app.config.from_object(Settings())

# Registrar blueprints (en orden alfabético)
app.register_blueprint(abogados)
app.register_blueprint(arc_documentos)
# ...
app.register_blueprint(usuarios_roles)

# Inicializar extensiones
csrf.init_app(app)
database.init_app(app)
login_manager.init_app(app)
moment.init_app(app)

# Cargar el modelo de usuario para la autenticación
authentication(Usuario)
```

Usar **Blueprints** siempre. Evitar rutas sueltas en `main.py`.
Para agregar un blueprint nuevo: crear `blueprints/<modulo>/`, importar su objeto desde `views.py` en `main.py`
y registrarlo manteniendo el orden alfabético.

### Blueprints existentes

Los prefijos de tres letras agrupan los módulos por área:

| Prefijo | Área | Blueprints |
|---------|------|------------|
| `arc_`  | Archivo | arc_documentos, arc_documentos_bitacoras, arc_documentos_tipos, arc_juzgados_extintos, arc_remesas, arc_remesas_bitacoras, arc_remesas_documentos, arc_solicitudes, arc_solicitudes_bitacoras |
| `dgt_`  | Digitalización | dgt_depositos, dgt_digitalizaciones, dgt_digitalizaciones_bitacoras, dgt_entregas, dgt_entregas_bitacoras, dgt_plataformas, dgt_plataformas_autoridades, dgt_plataformas_endpoints, dgt_plataformas_endpoints_bitacoras, dgt_rutas, dgt_tipos |
| `exh_`  | Exhortos | exh_areas, exh_exhortos, exh_exhortos_archivos, exh_exhortos_partes, exh_tipos_diligencias |
| `ofi_`  | Oficios | ofi_documentos, ofi_documentos_adjuntos, ofi_documentos_destinatarios, ofi_plantillas |
| —       | Publicaciones | edictos, estrados, glosas, listas_de_acuerdos, sentencias, audiencias, redams, abogados |
| —       | Catálogos | autoridades, autoridades_funcionarios, centros_trabajos, distritos, domicilios, estados, funcionarios, funcionarios_oficinas, materias, materias_tipos_juicios, municipios, oficinas |
| —       | Soporte | soportes_categorias, soportes_tickets |
| —       | Sistema y usuarios | bitacoras, bitacoras_apis, entradas_salidas, modulos, permisos, roles, sistemas, tareas, usuarios, usuarios_roles |

---

## Ejecución

```bash
uv sync                                          # Instalar dependencias
source .bashrc                                   # Cargar .env y credenciales de Google
python3 appserver.py                             # Servidor de desarrollo
gunicorn --bind 127.0.0.1:5000 appserver:gunicorn_app   # Como en producción
pjecz-hercules-beta-flask --help                 # CLI (db, usuarios, modulos, ...)
```

Redis debe estar disponible en `REDIS_URL` para las tareas en segundo plano.

---

## Base de datos

- ORM: **SQLAlchemy** para todo acceso a datos.
- Para insertar datos, crear una instancia del modelo y llamar a `save()` (que hace `db.session.add()` y `db.session.commit()`).

```python
instancia = Modelo(
    columna_1=columna_1,
    columna_2=columna_2,
)
instancia.save()
```

- Para actualizar, modificar los atributos y luego llamar a `save()`.

```python
instancia.columna_1 = nuevo_valor
instancia.save()
```

---

## Seguridad

- `SECRET_KEY` aleatoria y larga (mínimo 32 bytes).
- CSRF habilitado con Flask-WTF en todos los formularios.
- Validar y sanitizar toda entrada del usuario con WTForms.
- Usar HTTPS en producción (Google Cloud App Engine).

---

## Convenciones de código

- Seguir **PEP 8**. Ignorar **F821** (variables no definidas) en modelos y vistas.
- La longuitud máxima de línea es 128 caracteres.
- Nombres de clases en **PascalCase** con un prefijo de tres letras (ej. `OfiPlantilla`).
- Nombres de variables y funciones en **snake_case**.
- Nombres de rutas y URLs en **snake_case**
- Blueprints por módulo, no por tipo de archivo.

---

## Lo que Claude NO debe hacer

- No ejecutar `flask run` en modo producción.
- No hacer `db.drop_all()` ni `db.create_all()` en código de producción.
- No hardcodear contraseñas, tokens ni URIs de conexión.
- No ignorar errores de base de datos sin rollback.
- No crear rutas fuera de blueprints.
