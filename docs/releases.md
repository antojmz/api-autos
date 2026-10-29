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

**Scopes** (opcionales): indican qué parte del monorepo cambia. Son `api-autos`, `api-usuarios`, `auth-jwt`, `docs` y `monorepo`. Además, `main` lo usa el propio release-please en su PR.

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
- El workflow `.github/workflows/pr-title.yml` lo valida en cada PR: si el título no sigue la convención, el check falla.

**Opción con merge local** (`git merge --no-ff feature/x` y `git push`):
- release-please lee los commits de la rama, que deben ser convencionales.
- Los commits `Merge branch '...'` se ignoran.
- En este caso no hay PR, así que no actúa la validación automática: revisa tú los mensajes.

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
