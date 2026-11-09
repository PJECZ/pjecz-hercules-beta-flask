# SPEC 01 — Administración de aplicaciones externas (app_aplicaciones)

> **Estado:** Implementado
> **Depende de:** ninguna
> **Fecha:** 2026-11-05
> **Objetivo:** Agregar tres blueprints (`app_aplicaciones`, `app_aplicaciones_roles`, `app_aplicaciones_bitacoras`) para administrar las aplicaciones externas que consultan y entregan información a la plataforma, sus roles con nivel y la consulta de su bitácora de operaciones.

## Por qué existe esta spec

Hoy las llaves de API viven en `usuarios` (`api_key`, `api_key_expiracion`, `api_key_cuota_diaria`) y en `dgt_plataformas`.
Las aplicaciones que se conectan a la plataforma necesitan su propia identidad, con cuotas, expiración y roles independientes de un usuario humano.
Esta spec solo construye la **administración web**; quien valide las peticiones con estos datos se diseña aparte.

## Alcance

**Dentro:**

- Blueprint `app_aplicaciones` con CRUD completo: `datatable_json`, `list_active`, `list_inactive`, `detail`, `new`, `edit`, `delete`, `recover`.
- Generación y limpieza de `api_key` desde el detalle de la aplicación, con modal, días de expiración (90 por defecto) y registro en `Bitacora`, igual que en `usuarios`.
- Nueva función `generar_api_key_aplicacion(clave)` en `lib/pwgen.py`.
- Blueprint `app_aplicaciones_roles` para relacionar una aplicación con uno o más roles y un nivel de 1 a 4.
- En el detalle de la aplicación: datatable de sus roles con botón para alternar estatus A/B, y botón "Agregar rol" con select de rol y radio de nivel.
- Blueprint `app_aplicaciones_bitacoras` de solo consulta: lista general, vista detalle, y datatable dentro del detalle de la aplicación.
- Modelos SQLAlchemy de las tres tablas, con clave primaria UUID.
- Registro de los tres blueprints en `main.py` en orden alfabético.
- Relación inversa `app_aplicaciones_roles` en el modelo `Rol`.
- Actualizar la tabla de blueprints existentes en `Claude.md` con el prefijo `app_`.

**Fuera de alcance (para specs futuras):**

- Autenticación de peticiones entrantes por `api_key` (decorador, middleware o API aparte).
- Aplicación de `cuota_diaria` y `cuota_por_hora` en tiempo de ejecución.
- Escritura de registros en `app_aplicaciones_bitacoras` (lo hará el componente que valide las peticiones).
- Mostrar en `roles/detail` las aplicaciones que tienen ese rol.
- Alta de los módulos en la tabla `modulos` por seed o CLI.
- Depuración o retención de registros viejos de la bitácora.
- Gráficas o tableros de uso por aplicación.

## Modelo de datos

Ubicación: `src/pjecz_hercules_beta_flask/blueprints/<modulo>/models.py`.
Las tres clases heredan de `database.Model` y `UniversalMixin` (que aporta `estatus`, `creado`, `modificado`, `save()`, `delete()`, `recover()`).

```python
# app_aplicaciones/models.py
class AppAplicacion(database.Model, UniversalMixin):
    __tablename__ = "app_aplicaciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    clave: Mapped[str] = mapped_column(String(16), unique=True)
    descripcion: Mapped[str] = mapped_column(String(256))
    cuota_diaria: Mapped[int] = mapped_column(default=1000)
    cuota_por_hora: Mapped[int] = mapped_column(default=100)

    # Columnas que NO deben ser expuestas
    api_key: Mapped[Optional[str]] = mapped_column(String(128))
    expiracion: Mapped[Optional[datetime]]

    # Hijos
    app_aplicaciones_roles: Mapped[list["AppAplicacionRol"]] = relationship(back_populates="app_aplicacion")
    app_aplicaciones_bitacoras: Mapped[list["AppAplicacionBitacora"]] = relationship(back_populates="app_aplicacion")

    # @property api_key_oculta -> primeros 4 caracteres + "*" * 12 (igual que DgtPlataforma)
```

```python
# app_aplicaciones_roles/models.py
class AppAplicacionRol(database.Model, UniversalMixin):
    NIVELES = {
        1: "VER",
        2: "VER y MODIFICAR",
        3: "VER, MODIFICAR y CREAR",
        4: "ADMINISTRAR",
    }

    __tablename__ = "app_aplicaciones_roles"
    __table_args__ = (UniqueConstraint("app_aplicacion_id", "rol_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    app_aplicacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_aplicaciones.id"))
    app_aplicacion: Mapped["AppAplicacion"] = relationship(back_populates="app_aplicaciones_roles")
    rol_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    rol: Mapped["Rol"] = relationship(back_populates="app_aplicaciones_roles")

    nivel: Mapped[int]

    # @property nivel_descrito -> NIVELES[self.nivel]
```

```python
# app_aplicaciones_bitacoras/models.py
class AppAplicacionBitacora(database.Model, UniversalMixin):
    PETICIONES = {"GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH", "DELETE": "DELETE"}

    __tablename__ = "app_aplicaciones_bitacoras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    app_aplicacion_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_aplicaciones.id"), index=True)
    app_aplicacion: Mapped["AppAplicacion"] = relationship(back_populates="app_aplicaciones_bitacoras")

    ruta: Mapped[str] = mapped_column(String(512))
    peticion: Mapped[str] = mapped_column(Enum(*PETICIONES, name="app_aplicaciones_bitacoras_peticiones", native_enum=False), index=True)
    respuesta_estado: Mapped[int] = mapped_column(index=True)
    respuesta_mensaje: Mapped[str] = mapped_column(String(256), default="")

    # @property es_exitosa -> respuesta_estado < 400
```

Cambio en un modelo existente:

```python
# roles/models.py — agregar en Hijos
app_aplicaciones_roles: Mapped[list["AppAplicacionRol"]] = relationship(back_populates="rol")
```

Convenciones:

- `MODULO` en cada `views.py`: `"APP APLICACIONES"`, `"APP APLICACIONES ROLES"`, `"APP APLICACIONES BITACORAS"`.
- `clave` se limpia con `safe_clave(..., max_len=16)`: mayúsculas, dígitos y guiones.
- `cuota_diaria` y `cuota_por_hora` son enteros obligatorios mayores o iguales a 0; `0` significa sin acceso.
- `api_key` y `expiracion` no se capturan en el formulario CRUD; solo se cambian con la acción de generar o limpiar.
- Al limpiar: `api_key = ""` y `expiracion = datetime(2000, 1, 1)`, igual que en `usuarios`.
- `api_key` nunca se entrega completa en `datatable_json`; se usa `api_key_oculta`.

## Plan de implementación

1. **Modelo `AppAplicacion`.** Crear `blueprints/app_aplicaciones/__init__.py` y `models.py`. Prueba: la aplicación arranca con `python3 appserver.py` y la tabla se crea en la base de datos de desarrollo.
2. **Formulario y vistas CRUD de `app_aplicaciones`.** Crear `forms.py` (`AppAplicacionForm` con `clave`, `descripcion`, `cuota_diaria`, `cuota_por_hora`, `guardar`) y `views.py` con las ocho rutas estándar, siguiendo `dgt_plataformas`. Registrar en `main.py` en orden alfabético. Prueba: crear, editar, eliminar y recuperar una aplicación.
3. **Plantillas de `app_aplicaciones`.** Crear `templates/app_aplicaciones/list.jinja2`, `detail.jinja2`, `new.jinja2`, `edit.jinja2` usando los macros existentes. Prueba: las cuatro vistas renderizan sin errores.
4. **Generador de API key.** Agregar `generar_api_key_aplicacion(clave: str) -> str` en `lib/pwgen.py`: prefijo derivado de la clave más `secrets.token_urlsafe`. No modificar `generar_api_key`. Prueba: llamar la función dos veces con la misma clave devuelve cadenas distintas de 128 caracteres o menos.
5. **Acción generar/limpiar API key.** Agregar en `app_aplicaciones/views.py` la ruta `api_key_request_json/<app_aplicacion_id>` (POST, `Permiso.ADMINISTRAR`) con acciones `new` (recibe `days`, 90 por defecto) y `clean`, registrando en `Bitacora`. Agregar el modal y los botones en `detail.jinja2`, tomando como base `usuarios`. Prueba: generar muestra la llave y la expiración; limpiar las deja vacías.
6. **Modelo `AppAplicacionRol`.** Crear `blueprints/app_aplicaciones_roles/__init__.py` y `models.py`, y agregar la relación inversa en `roles/models.py`. Prueba: la aplicación arranca y la tabla existe con la restricción única.
7. **Vistas de `app_aplicaciones_roles`.** Crear `forms.py` (`AppAplicacionRolWithAppAplicacionForm` con `rol` SelectField y `nivel` RadioField 1–4) y `views.py` con `datatable_json`, `list_active`, `list_inactive`, `detail`, `new_with_app_aplicacion`, `edit`, `delete`, `recover` y `toggle_estatus_json`. Si la pareja aplicación–rol ya existe, `new_with_app_aplicacion` actualiza el nivel y la reactiva en lugar de duplicar. Registrar en `main.py`. Prueba: agregar un rol, agregarlo de nuevo con otro nivel y ver un solo registro con el nivel nuevo.
8. **Plantillas de `app_aplicaciones_roles`.** Crear `list.jinja2`, `detail.jinja2`, `new_with_app_aplicacion.jinja2`, `edit.jinja2`. Prueba: las vistas renderizan.
9. **Roles en el detalle de la aplicación.** En `app_aplicaciones/detail.jinja2` agregar el datatable de roles (rol, nivel, botón toggle) y el botón "Agregar rol", siguiendo el patrón de `usuarios_roles` en `roles/detail.jinja2`. Prueba: el botón toggle cambia A↔B sin recargar la página.
10. **Modelo `AppAplicacionBitacora`.** Crear `blueprints/app_aplicaciones_bitacoras/__init__.py` y `models.py`. Prueba: la tabla se crea.
11. **Vistas de `app_aplicaciones_bitacoras`.** Crear `views.py` con `datatable_json` (filtros por `app_aplicacion_id`, `peticion`, `respuesta_estado`), `list_active` y `detail`, sin formularios ni rutas de escritura. Crear `list.jinja2` y `detail.jinja2`. Registrar en `main.py`. Prueba: con registros insertados a mano en la base de datos, la lista y el detalle los muestran.
12. **Bitácora en el detalle de la aplicación.** En `app_aplicaciones/detail.jinja2` agregar un datatable de sus bitácoras usando `app_aplicaciones_bitacoras.datatable_json` filtrado por `app_aplicacion_id`, visible solo si `current_user.can_view("APP APLICACIONES BITACORAS")`. Prueba: solo aparecen los registros de esa aplicación.
13. **Documentación.** Agregar la fila del prefijo `app_` en la tabla "Blueprints existentes" de `Claude.md`.

## Criterios de aceptación

- [ ] `python3 appserver.py` arranca sin errores con los tres blueprints registrados.
- [ ] Existen las tablas `app_aplicaciones`, `app_aplicaciones_roles` y `app_aplicaciones_bitacoras` con clave primaria UUID.
- [ ] Tras dar de alta los módulos `APP APLICACIONES`, `APP APLICACIONES ROLES` y `APP APLICACIONES BITACORAS` en Módulos y asignarles permisos, un usuario con nivel ADMINISTRAR ve las tres listas.
- [ ] Un usuario sin permiso sobre `APP APLICACIONES` recibe acceso denegado en `/app_aplicaciones`.
- [ ] Al crear una aplicación con clave `mi app 1`, se guarda como `MI-APP-1`.
- [ ] Crear una segunda aplicación con una clave existente muestra un mensaje de error y no se guarda.
- [ ] Una cuota negativa es rechazada por el formulario.
- [ ] El formulario de nuevo y edición no tiene campos `api_key` ni `expiracion`.
- [ ] El botón "Generar" crea un `api_key` nuevo y fija `expiracion` a hoy más los días indicados (90 por defecto).
- [ ] El botón "Limpiar" deja `api_key` vacío y `expiracion` en 2000-01-01.
- [ ] Generar y limpiar dejan un registro en `Bitacora` con el módulo `APP APLICACIONES`.
- [ ] La lista de aplicaciones muestra `api_key` oculto (4 caracteres + asteriscos), nunca completo.
- [ ] Eliminar una aplicación la pasa a estatus B y aparece en la lista de inactivos; recuperarla la regresa a A.
- [ ] Desde el detalle de una aplicación se agrega un rol con nivel 1, 2, 3 o 4; el nivel 0 no aparece como opción.
- [ ] Agregar de nuevo un rol ya relacionado actualiza su nivel y su estatus a A, sin crear un segundo registro.
- [ ] El botón toggle del datatable de roles cambia el estatus entre A y B y la fila refleja el cambio sin recargar.
- [ ] `app_aplicaciones_bitacoras` no tiene rutas de creación, edición ni eliminación.
- [ ] La lista de bitácoras se puede filtrar por aplicación, petición y estado de respuesta.
- [ ] El detalle de una aplicación muestra solo las bitácoras de esa aplicación.
- [ ] `Claude.md` incluye el prefijo `app_` en la tabla de blueprints.

## Decisiones

- **Sí:** solo administración web. La validación de `api_key`, las cuotas y la escritura de bitácoras van en otra spec o proyecto.
- **Sí:** clave primaria UUID en las tres tablas. Sigue el patrón reciente de `dgt_*` y no expone IDs secuenciales.
- **No:** clave primaria entera como `permisos` o `usuarios_roles`.
- **Sí:** `api_key` generada por el sistema con modal generar/limpiar, como en `usuarios`.
- **No:** capturar `api_key` a mano como en `dgt_plataformas`. Evita llaves débiles.
- **Sí:** nueva función `generar_api_key_aplicacion(clave)`. `generar_api_key` exige un `id` entero y un e-mail, que una aplicación con UUID no tiene.
- **No:** modificar `generar_api_key`. La usan `usuarios` y no se quiere arriesgar ese flujo.
- **Sí:** cuotas obligatorias, enteros ≥ 0, con valores por defecto 1000 diaria y 100 por hora; `0` = sin acceso.
- **No:** cuotas opcionales donde NULL signifique ilimitado. Introduce ambigüedad.
- **Sí:** niveles 1 a 4. Para "ninguno" se desactiva la relación (estatus B).
- **No:** nivel 0 (NINGUNO), aunque aparecía en la descripción inicial. Duplicaba el significado del estatus B.
- **Sí:** restricción única `(app_aplicacion_id, rol_id)`; agregar una pareja existente actualiza nivel y reactiva, como `permisos.new_with_rol`.
- **Sí:** administrar roles desde el detalle de la aplicación.
- **No:** mostrar aplicaciones en `roles/detail`. Se puede agregar después.
- **Sí:** `peticion` como `Enum` con `native_enum=False`, igual que `bitacoras_apis`, agregando `PATCH`.
- **Sí:** `respuesta_estado` entero; el éxito se deduce de `respuesta_estado < 400`.
- **No:** columna booleana `respuesta_exitosa`. Sería redundante con el código de estado.
- **Sí:** bitácora con lista general, vista detalle y datatable en el detalle de la aplicación.
- **Sí:** `clave` con `safe_clave`, única, máximo 16 caracteres; `descripcion` String(256).
- **Sí:** alta manual de los módulos en la web. No se modifican seeds ni CLI.
- **Sí:** el nombre del módulo es `app_aplicaciones`; `app_apliaciones` en la descripción inicial fue un error de dedo.

## Riesgos

| Riesgo | Mitigación |
| ------ | ---------- |
| `api_key` guardada en texto plano en la base de datos | Mismo criterio que `usuarios.api_key`. Nunca se expone completa en listas ni JSON de datatables. Cifrar o usar hash queda para la spec de autenticación. |
| La bitácora crece sin límite cuando la API empiece a escribir | Índices en `app_aplicacion_id`, `peticion` y `respuesta_estado`. La retención va en otra spec. |
| Los módulos no se dan de alta en `modulos` y las vistas fallan con acceso denegado | Está documentado como criterio de aceptación; es un paso manual previo a probar. |
| Sin datos reales, las vistas de bitácora no se pueden probar | Insertar registros de prueba a mano en la base de datos de desarrollo. |

## Lo que **no** está en esta spec

- Autenticación de peticiones por `api_key`.
- Aplicación de cuotas diaria y por hora.
- Escritura de registros en la bitácora.
- Aplicaciones visibles desde `roles/detail`.
- Seeds o comandos CLI para los módulos.
- Retención de la bitácora y tableros de uso.

Cada uno de esos temas, si se implementa, va en su propia spec.
