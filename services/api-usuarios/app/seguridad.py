"""
seguridad.py — Hash y verificación de contraseñas.

Regla de oro (OWASP): las contraseñas NUNCA se guardan en texto plano ni con
cifrado reversible. Se guarda un HASH lento y con "sal" aleatoria:
  - Lento: probar millones de contraseñas por fuerza bruta resulta carísimo.
  - Con sal: dos usuarios con la misma contraseña tienen hashes distintos, y
    no sirven tablas precalculadas ("rainbow tables").

Usamos Argon2id (ganador de la Password Hashing Competition y primera opción
de OWASP) a través de `pwdlib`, la librería que recomienda la documentación de
FastAPI. `PasswordHash.recommended()` elige Argon2id con parámetros seguros.
"""

from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()

# Hash de una contraseña ficticia, calculado una sola vez al arrancar.
# Se usa en el login cuando el usuario NO existe: verificamos contra este hash
# para que la respuesta tarde lo mismo exista o no el usuario. Si no, un
# atacante podría averiguar qué usuarios existen midiendo el tiempo.
_HASH_FICTICIO = _hasher.hash("contraseña-ficticia-solo-para-igualar-tiempos")


def hashear_password(password: str) -> str:
    """Devuelve el hash Argon2id (incluye algoritmo, parámetros y sal)."""
    return _hasher.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña con su hash (en tiempo constante)."""
    return _hasher.verify(password, password_hash)


def simular_verificacion(password: str) -> None:
    """Gasta el mismo tiempo que una verificación real (ver _HASH_FICTICIO)."""
    _hasher.verify(password, _HASH_FICTICIO)
