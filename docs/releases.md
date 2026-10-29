# Versionado y releases (release-please)

El monorepo usa [release-please](https://github.com/googleapis/release-please) para calcular la versión, escribir el `CHANGELOG.md` y publicar las releases de GitHub **a partir de los mensajes de commit**.

Todo el repositorio comparte **una sola versión**, con tags `vX.Y.Z`. La versión actual está en `version.txt`.

## Cómo funciona

```
commits en main             release-please (GitHub Actions, en cada push a main)
feat: ...  ─┐
fix:  ...  ─┼──────────►  abre o actualiza el PR "chore(main): release 1.1.0"
docs: ...  ─┘             con la versión nueva y el CHANGELOG
                                   │
                         mergeas el PR de release
                                   ▼
                          tag v1.1.0 + GitHub Release + CHANGELOG.md en main
```

1. Trabajas como siempre, pero con mensajes de commit **convencionales** (ver abajo).
2. En cada push a `main`, el workflow `.github/workflows/release-please.yml` revisa los commits nuevos. Si hay alguno que genera release (`feat`, `fix`, `perf`...), abre o actualiza un PR de release.
3. Cuando quieras publicar, **mergeas ese PR**. release-please crea el tag, la GitHub Release y actualiza el `CHANGELOG.md`.

Al hacer una release, la versión se actualiza sola en:

| Archivo | Qué cambia |
|---|---|
| `version.txt` | versión del monorepo |
| `.release-please-manifest.json` | última versión publicada |
| `CHANGELOG.md` | notas de la release (se crea con la primera) |
| `services/api-autos/app/main.py` | `version=` de FastAPI (se ve en `/docs`) |
| `services/api-usuarios/app/main.py` | `version=` de FastAPI |
| `libs/auth-jwt/pyproject.toml` | `[project] version` |
| `apps/web/package.json` | `version` del frontend |

**No edites estas versiones a mano.** Las líneas de `main.py` llevan el comentario `# x-release-please-version`, que es la marca que release-please busca para reemplazarlas.

## Conventional Commits

Formato: `tipo(scope opcional): descripción en español, en minúscula y sin punto final`

| Tipo | Cuándo | Efecto en la versión | En el CHANGELOG |
|---|---|---|---|
| `feat` | funcionalidad nueva | menor: 1.0.0 → **1.1.0** | Nuevas Funcionalidades |
| `fix` | corrección de un error | parche: 1.0.0 → **1.0.1** | Correcciones de Errores |
| `perf` | mejora de rendimiento | parche | Mejoras de Rendimiento |
| `revert` | revertir un commit | parche | Reversiones |
| `docs` | solo documentación | ninguno* | Documentación |
| `refactor` | cambio interno sin cambiar comportamiento | ninguno* | Refactorización |
| `test`, `build`, `ci`, `chore` | pruebas, Docker o dependencias, workflows, mantenimiento | ninguno | (oculto) |

\* No abren una release por sí solos, pero aparecen en el CHANGELOG si la release la abrió otro commit.

**Cambios incompatibles** (versión mayor, 1.x → **2.0.0**): añade `!` después del tipo, o un pie `BREAKING CHANGE:` en el cuerpo del commit.

```
feat(api-usuarios)!: el login devuelve también un refresh token

BREAKING CHANGE: la respuesta de /auth/login cambia de formato.
```

**Scopes** (opcionales): indican qué parte del monorepo cambia. Son `api-autos`, `api-usuarios`, `auth-jwt`, `web`, `docs` y `monorepo`. Además, `main` lo usa el propio release-please en su PR.

Ejemplos:

```
feat(api-autos): filtrar autos por rango de fechas
fix(api-usuarios): devolver 404 al editar un usuario eliminado
docs: explicar cómo rotar JWT_SECRET_KEY
build(auth-jwt): actualizar pyjwt a 2.11
ci: cachear la instalación de dependencias
```

## Cómo integrar los cambios en `main`

**Opción recomendada: PR con squash merge.**
- El título del PR se convierte en el único commit en `main`, así que el **título** debe ser convencional.
- El workflow `.github/workflows/pr-title.yml` **genera el título desde el nombre de la rama** si el que tiene el PR no es convencional, y lo valida. Si no puede generarlo ni el título es válido, el check falla (ver la sección siguiente).

**Opción con merge local** (`git merge --no-ff feature/x` y `git push`):
- release-please lee los commits de la rama, que deben ser convencionales.
- Los commits `Merge branch '...'` se ignoran.
- En este caso no hay PR, así que no actúa la validación automática: revisa tú los mensajes.

## Nombres de rama y título automático del PR

Nombra las ramas con el formato **`tipo/scope/descripcion`**. El scope es opcional:

| Rama | Título que genera el workflow |
|---|---|
| `feat/api-autos/filtro-por-fechas` | `feat(api-autos): filtro por fechas` |
| `fix/web/cookie_segura` | `fix(web): cookie segura` |
| `fix/login-lento` | `fix: login lento` |
| `docs/guia-de-despliegue` | `docs: guia de despliegue` |
| `feature/config` | `feat: config` (alias) |

- **Tipos**: los de Conventional Commits (tabla de arriba). Alias admitidos: `feature` → `feat`, `hotfix` y `bugfix` → `fix`, `doc` → `docs`.
- **Scope**: si la rama tiene 3 segmentos o más, el segundo debe ser un scope válido: `api-autos`, `api-usuarios`, `auth-jwt`, `web`, `docs`, `monorepo` o `main`.
- **Descripción**: el resto de la rama; los `-` y `_` se convierten en espacios.

Al abrir o actualizar un PR, el workflow `pr-title`:
1. **Respeta el título** si ya es convencional. Así puedes escribir uno más descriptivo a mano, por ejemplo con tildes, que en la rama no conviene usar.
2. Si no lo es, **lo reemplaza** por el generado desde la rama. Verás el cambio en el PR y un resumen en la ejecución del workflow.
3. Si la rama tampoco sigue el formato (por ejemplo `mi-rama` o `feat/scope-inventado/x`), el check **falla** y explica el motivo. Para arreglarlo, renombra la rama o edita el título a mano, y el check se vuelve a ejecutar solo.

**Cambios incompatibles** (versión mayor): la rama no puede expresar el `!`. Edita el título a mano, por ejemplo `feat(api-autos)!: nuevo formato de filtros`. Como ya es convencional, el workflow lo respeta.

El PR que abre release-please (`chore(main): release X.Y.Z`) no se renombra; solo se valida.

Los tipos, scopes y alias viven en `.github/workflows/pr-title.yml`. Si añades un servicio, app o librería al monorepo, agrega su scope ahí.

**Limitación**: en un PR desde un *fork*, el token de GitHub Actions es de solo lectura y no puede cambiar el título. El check falla indicando el título que debes poner a mano.

## Ajustes necesarios en GitHub (una sola vez)

Hay que hacerlos a mano en la web del repositorio (`antojmz/api-autos`):

1. **Settings → Actions → General → Workflow permissions**:
   - Marca **Read and write permissions**.
   - Marca **Allow GitHub Actions to create and approve pull requests**.
   - Sin esto, el workflow falla con *"GitHub Actions is not permitted to create or approve pull requests"*.
2. Recomendado: **Settings → General → Pull Requests** → activa *Allow squash merging* y elige *Default to pull request title*.

## Detalles y limitaciones

- **Punto de partida**: `bootstrap-sha` en `release-please-config.json` apunta al `main` anterior a la llegada de release-please. Los commits previos, que no son convencionales, no se analizan ni aparecen en el CHANGELOG. La primera release partirá de `1.0.0`.
- Los PR que crea release-please con el `GITHUB_TOKEN` **no disparan otros workflows**, una protección de GitHub. Hoy no afecta porque no hay CI de tests. Si en el futuro hace falta, hay que usar un token personal (PAT) en `release-please.yml`.
- La versión es común a todo el repositorio: un `fix` en `api-autos` también sube la versión que muestra `api-usuarios`. Si algún día cada servicio necesita su propia versión, release-please admite un paquete por carpeta en `release-please-config.json`.
