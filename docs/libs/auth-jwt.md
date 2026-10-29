# Librería `auth-jwt` (`libs/auth-jwt`)

Paquete Python (`auth_jwt`) que comparten todos los servicios para **emitir** y **validar** tokens JWT. Así, todos usan exactamente las mismas reglas: algoritmo, emisor, audiencia, expiración y roles.

| Quién la usa | Para qué |
|---|---|
| `services/api-usuarios` | Emitir tokens en el login (`crear_token_acceso`) y validarlos (`decodificar_token`) |
| `services/api-autos` | Proteger rutas (`obtener_claims`, `requiere_rol`) sin llamar a `api-usuarios` |

## API

```python
from auth_jwt import (
    Rol,                 # StrEnum: Rol.ADMIN, Rol.USUARIO
    ClaimsToken,         # sub, username, rol, iat, exp, iss, aud (+ .usuario_id)
    crear_token_acceso,  # (usuario_id, username, rol) -> (token, segundos_validez)
    decodificar_token,   # (token) -> ClaimsToken | lanza TokenInvalido
    TokenInvalido,
    obtener_claims,      # dependencia FastAPI: lee "Authorization: Bearer", 401 si falla
    ClaimsDep,           # Annotated[ClaimsToken, Depends(obtener_claims)]
    requiere_rol,        # requiere_rol(Rol.ADMIN) -> dependencia que da 403
    error_401,           # HTTPException 401 con WWW-Authenticate: Bearer
    get_config_jwt,      # configuración (se valida al llamarla)
)
```

Ejemplo, en un servicio nuevo:

```python
from auth_jwt import ClaimsDep, Rol, obtener_claims, requiere_rol
from fastapi import APIRouter, Depends

# Todas las rutas del router exigen token
router = APIRouter(prefix="/cosas", dependencies=[Depends(obtener_claims)])

@router.get("")
def listar(claims: ClaimsDep):           # datos del usuario del token
    return {"hola": claims.username}

@router.delete("/{id}", dependencies=[Depends(requiere_rol(Rol.ADMIN))])
def borrar(id: int): ...
```

Recomendación: llama a `get_config_jwt()` al importar `main.py`, para que el servicio no arranque si falta la clave.

## Configuración (variables de entorno)

| Variable | Por defecto | Descripción |
|---|---|---|
| `JWT_SECRET_KEY` | (obligatoria, 32 caracteres o más) | Clave HMAC. Se define en el `.env` de la raíz y Compose la inyecta en todos los servicios |
| `JWT_ALGORITMO` | `HS256` | Único algoritmo aceptado al validar (impide `alg: none`) |
| `JWT_EMISOR` | `api-usuarios` | Claim `iss` |
| `JWT_AUDIENCIA` | `monorepo-autos` | Claim `aud` |
| `JWT_MINUTOS_EXPIRACION` | `30` | Validez del token (de 1 a 1440 minutos) |

`docker-compose.yml` solo pasa a los contenedores `JWT_SECRET_KEY` y `JWT_MINUTOS_EXPIRACION`, en el bloque común `x-servicio-python`. Para cambiar otra variable, añádela en ese bloque, de modo que todos los servicios reciban el mismo valor.

## Decisiones y límites

- **HS256 con clave compartida**: es sencillo, pero cualquier servicio que tenga la clave podría *firmar* tokens. Para producción conviene **RS256**: `api-usuarios` firma con una clave privada y los demás servicios validan con la pública.
- **Validación stateless**: `obtener_claims` no consulta ninguna BD. Un usuario desactivado conserva el acceso hasta que expira su token, y por eso los tokens duran poco. `api-usuarios` sí comprueba la BD en cada petición.
- **No hay refresh tokens ni revocación** (lista de tokens bloqueados): cuando el token expira, hay que volver a iniciar sesión.

## Cómo se instala en Docker

Los Dockerfiles se construyen con la **raíz del monorepo como contexto** (`build: {context: ., dockerfile: services/<svc>/Dockerfile}` en `docker-compose.yml`) e instalan la librería en el venv de la imagen:

```dockerfile
COPY libs/auth-jwt /tmp/libs/auth-jwt
RUN pip install --no-cache-dir /tmp/libs/auth-jwt
```

Si cambias la librería, reconstruye **todos** los servicios que la usan: `docker compose up -d --build`.
