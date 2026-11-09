"""
Generadores de contraseñas
"""

import random
import re
import secrets
import string
import time

from hashids import Hashids

from pjecz_hercules_beta_flask.config.settings import get_settings

settings = get_settings()


def generar_api_key(id: int, email: str, random_length: int = 24) -> str:
    """Generar API key a partir de un ID, un e-mail y una cadena aleatoria"""
    aleatorio = "".join(random.sample(string.ascii_letters + string.digits, k=random_length))
    hash_email = Hashids(salt=email, min_length=8).encode(1)
    hash_id = Hashids(salt=settings.SALT, min_length=8).encode(id)
    return f"{hash_id}.{hash_email}.{aleatorio}"


def generar_api_key_aplicacion(clave: str, random_bytes: int = 48) -> str:
    """Generar API key para una aplicación con un prefijo derivado de su clave y una cadena aleatoria segura"""
    prefijo = re.sub(r"[^a-z0-9]+", "", str(clave).lower())[:16]
    aleatorio = secrets.token_urlsafe(random_bytes)
    if prefijo == "":
        return aleatorio[:128]
    return f"{prefijo}.{aleatorio}"[:128]


def generar_contrasena(largo=16):
    """Generar contraseña con minúsculas, mayúsculas, dígitos y signos"""
    minusculas = string.ascii_lowercase
    mayusculas = string.ascii_uppercase
    digitos = string.digits
    simbolos = string.punctuation
    todos = minusculas + mayusculas + digitos + simbolos
    temp = random.sample(todos, largo)
    return "".join(temp)


def generar_aleatorio(largo=16):
    """Generar cadena de texto aleatorio con minúsculas, mayúsculas y dígitos"""
    minusculas = string.ascii_lowercase
    mayusculas = string.ascii_uppercase
    digitos = string.digits
    todos = minusculas + mayusculas + digitos
    temp = random.sample(todos, largo)
    return "".join(temp)


def generar_identificador(largo: int = 16) -> str:
    """Generar identificador con el tiempo actual y algo aleatorio, con letras en mayúsculas y dígitos"""
    timestamp_unique = str(int(time.time() * 1000))
    random_characters = "".join(random.sample(string.ascii_uppercase + string.digits, k=largo))
    return f"{timestamp_unique}{random_characters}"[:largo]
