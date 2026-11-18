# CODEBASE-MAP.md — farrera-academy

## Stack
- **Language/framework:** Python 3.12, Django 5.1.3 + Django REST Framework 3.15.2.
- **Auth:** `djangorestframework-simplejwt` 5.3.1, wrapped in a custom `CustomJWTAuthentication` (see Entry points).
- **DB:** MySQL in all real environments (`mysqlclient`), `psycopg2-binary` present but unused (no Postgres config found) — likely leftover/optional.
- **Static/serving:** `whitenoise`, `gunicorn` for prod.
- **Other notable deps:** `django-cors-headers`, `Faker` (dev-only, used by seed commands), `Pillow` (image fields), `Brotli`.
- **Package manager:** plain `pip` + `requirements.txt` (no poetry/pipenv lockfile).
- **Run:** `python manage.py runserver` (dev), `gunicorn` (prod, no Procfile/compose found in repo root — check deploy target before assuming one).
- **Settings:** `school_admin/settings.py` is **gitignored** (`.gitignore` excludes it per commit `1a12a21`) — every environment, including local dev, must regenerate/restore it manually. This is the single most common onboarding trap for this repo.

## Entry points
- WSGI/ASGI root: `school_admin/urls.py` — mounts six app URLconfs under a flat `/api/` prefix (no versioning):
  - `user.urls` → `/api/auth/*`, `/api/user/me/`, `/api/sistema/usuarios|roles`
  - `catalogos.urls` → `/api/catalogos/*` (lookup tables: generos, estados, localidades, status, tipos-bloque, tipos-tema, tipos-evaluacion, niveles-competencia)
  - `sistema.urls` → `/api/sistema/*` (empresas, dependencias, modulos, pestanias, departamentos, puestos) + sidebar/permissions endpoints
  - `competencias.urls` → `/api/competencias/*`
  - `capacitacion.urls` → `/api/capacitacion/*` — by far the largest surface, split into three parallel routers (admin / `mis-*` self-service / `ver/*` read-only for colaboradores)
- **Auth entry:** `user/views.py::CustomTokenObtainPairView` (`/api/auth/sign/`) issues JWTs; `user/authenticate.py` (or similar) defines `CustomJWTAuthentication`, set as `DEFAULT_AUTHENTICATION_CLASSES` in `school_admin/settings.py:65-69`.
- **Permission entry:** `DEFAULT_PERMISSION_CLASSES` in settings + a custom `HasRoleWithRoles([...])` permission class checked per-viewset — role-based (`Role.nombre`), **not** Django's built-in `Permission`/`has_perm`.
- **Pagination entry:** `common/pagination.py::DynamicPageNumberPagination` is the project-wide default; any list endpoint supports `?pagination=false|0|no` to disable paging (built for catalog/lookup endpoints consumed by frontend dropdowns).
- **Admin commands (non-HTTP entry points):** `common/management/commands/` — `seed_fake_data.py`, `seed_navegacion.py`, `seed_tipos_bloque.py`. These are the only way the `Modulo`/`Pestania` nav tree, the `TipoBloqueContenido` catalog, and bulk fake data get populated; there is no admin-UI equivalent.

## Request flow (traced: colaborador reads a published course's content)
`GET /api/capacitacion/ver/bloques/?tema=<id>`
1. **Transport:** `capacitacion/urls.py` → `ver_router` → `ContenidoBloqueColaboradorViewSet` (`capacitacion/views_colaborador.py`).
2. **Auth/permission:** `CustomJWTAuthentication` resolves the user from the JWT; viewset-level permission checks the user has an active `Colaborador`/role, no module-permission check here (that's the `sistema` nav-menu system, orthogonal — see Module ownership).
3. **Scoping (business logic):** `views_colaborador.py::_base_cursos_qs()` filters the course set — **currently filters only `activo=True`**, not by `status` (flagged in `docs/REVISION_CONCURRENCIA_HISTORIAL_PUBLICACION.md` as a real gap: a colaborador can read `borrador` content today). Query then walks `Curso → Modulo → Tema → ContenidoBloque`, prefetching `bloque_items`, `archivos`, `opciones`.
4. **Serialization:** `capacitacion/serializers/colaborador.py::ContenidoBloqueColaboradorSerializer` — nests item/archivo/opcion serializers, and **strips `es_correcta`** from opciones (author-only field), unlike the admin serializer in `capacitacion/serializers/curso.py`.
5. **Persistence:** MySQL via Django ORM, no raw SQL in this path.
6. **Response:** paginated JSON (or flat list if `?pagination=false`).

Side path worth knowing: **answering a question** (`POST /api/capacitacion/mis-respuestas-bloque/`) goes through `MisRespuestasBloqueViewSet` → `MiRespuestaBloqueSerializer`, which **server-computes `es_correcta`** by comparing the submitted `opcion_seleccionada` against `ContenidoBloqueOpcion.es_correcta` — the client never sends or trusts a correctness flag.

## Module ownership
| Area | Owns | Key files |
| --- | --- | --- |
| Auth/users | login, JWT, `User`/`Role` CRUD | `user/` (models, views split into `view/user_view.py` + `view/admin_view.py`, serializers, custom auth backend) |
| Navigation/permissions (menu visibility) | `Modulo`/`Pestania` tree + which `Role` sees which tab | `sistema/models.py`, `sistema/views.py` (`GetModulosUsuario`, `GetPestaniaUsuario`, `PermisosDisponiblesView`) — **separate system from DRF/role business permissions**, easy to confuse |
| Org structure | `Empresa`, `Dependencia`, `Departamento`, `Puesto` | `sistema/` |
| Catalogs (lookup tables) | countries/states, status, block types, tema types, evaluation types, competency levels | `catalogos/models/`, extensible-by-design `TipoBloqueContenido` (config/capacidades/validacion_schema JSON fields, `codigo` is the stable key — never `nombre`) |
| Course authoring (admin) | `Curso → Modulo → Tema → ContenidoBloque → {Item, Archivo, Opcion}`, nested evaluative blocks | `capacitacion/models/curso.py`, `capacitacion/views.py`, `capacitacion/serializers/curso.py` |
| Course consumption (colaborador) | self-scoped reads + progress/answers | `capacitacion/views_colaborador.py`, `capacitacion/serializers/colaborador.py` |
| Evaluations | `Evaluacion`/`Pregunta`/`OpcionPregunta`/`ResultadoEvaluacion`, kept deliberately separate from the newer embedded evaluative blocks | `capacitacion/` (evaluation-specific files) |
| Multi-tenant scoping | authorization-by-ownership across the FK chain | `capacitacion/views.py::_scope_por_empresa()` — reused helper, not duplicated per viewset |
| Bulk reorder | atomic drag-and-drop reordering of modules/temas/bloques/items/opciones | `capacitacion/views.py::_reordenar_en_lote()` — uses an offset-based temp ordering (`max_actual + 1`), **not negative numbers**, because the `orden` fields are `PositiveSmallIntegerField` |
| Competencies | `Competencia`, `NivelCompetencia`, `CompetenciaCurso`, `CompetenciaColaborador`, `RutaAprendizaje` | `competencias/` |
| Shared base models | `BaseModel` (`activo`/`creado_at`), `Base`/`BaseFileEntity` (`status`/`created_at`, auto mime/size/checksum, physically deletes files), `SoftDeleteModel` (`deleted_at`/`restore()`/`hard_delete()`) | `common/models.py` — **three different base classes with different field names**; mixing them up (e.g. in a serializer's `fields`) is a real, already-hit bug class in this repo |

## Hidden behavior
- **Signal (the one real piece of implicit/automatic behavior in the app):** `competencias/signals.py::acreditar_competencias_al_completar`, a `post_save` receiver on `capacitacion.Inscripcion`. When `completado_at` is set, it looks up `CompetenciaCurso` for that course and raises the colaborador's `CompetenciaColaborador.nivel` **if and only if** the new level's `orden` is higher than the current one (never downgrades). This is the entire "course completion → competency level" mechanism — no Celery/cron/queue involved, purely a synchronous DB-transaction-time signal. Wired up in `competencias/apps.py` (`ready()` import).
- **Dead code, not wired to anything:** `core/events.py` defines commented-out `Signal()` objects (`lead_created`, `payment_received`, etc.) under an app called `core` that is **not in `INSTALLED_APPS`**. Looks like a scaffold copied from an unrelated CRM/payments project. Safe to ignore or delete — do not assume it does anything.
- No cron, no Celery, no webhooks, no background workers found anywhere in the codebase (grep for `cron|celery|schedule|webhook|queue` returned only the signal above, the seed commands, and this dead file).
- **Env-driven branching:** standard Django `DEBUG`/`DATABASES` from `settings.py`, nothing unusual; no feature flags found.

## Hotspots
Churn ranking (file-touch count, last 12 months, excluding `__pycache__`/migrations — those dominate raw churn and are noise, not risk):
1. `capacitacion/views.py` and `capacitacion/serializers/curso.py` / `serializers/colaborador.py` — by far the most-changed real code, consistent with this being the active area of development (nested content blocks, reorder, scoping all landed here this quarter).
2. `user/views.py`, `user/serializers.py`, `user/models.py` — second cluster, auth/user management.
3. `sistema/serializers/modulos.py`, `sistema/models.py` — nav/permission wiring.
4. `competencias/*` — smaller but recently touched (the signal above).
5. Two odd repo-root files with real churn history: `university_db.sql` and `sql_reader.py` — **not part of the Django app** (no import of `sql_reader` found anywhere in app code); likely a one-off migration/import script from an earlier non-Django system. Worth confirming with whoever added them before relying on or deleting them.

Highest-risk quadrant (churn × complexity) is unambiguous: **`capacitacion/views.py`**. It's the largest file, carries the multi-tenant scoping helper, the atomic reorder helper, and most viewsets — a regression here has the widest blast radius in the project. `capacitacion/models/curso.py` is the equivalent risk on the model side (one file defines `Curso`, `Modulo`, `Tema`, `ContenidoBloque`, and four child content models with three different base-class field conventions mixed in).

## How to run
```bash
# 1. settings.py is gitignored — restore/regenerate it first (see git history for a template:
#    commit b0a49db had a working local version before it was excluded in 1a12a21)
cp school_admin/settings.py.example school_admin/settings.py   # if an example exists; otherwise recreate manually

# 2. install deps
pip install -r requirements.txt

# 3. migrate (MySQL must be running, DB `farrera_academy_local` or equivalent, user grants set up)
python manage.py migrate

# 4. seed reference data (order matters: tipos-bloque and navegacion are independent of each other,
#    but both assume migrations are already applied)
python manage.py seed_tipos_bloque
python manage.py seed_navegacion
python manage.py seed_fake_data      # optional, for realistic dev data

# 5. create a superuser if seed_fake_data didn't already (check its output — it creates one by convention)
python manage.py createsuperuser

# 6. run
python manage.py runserver

# 7. hit one real path to confirm
curl -X POST localhost:8000/api/auth/sign/ -d '{"num_colab": "...", "password": "..."}' -H 'Content-Type: application/json'
```

**Tests:** `python manage.py test` runs the full suite (57+ tests live under `capacitacion/tests/`, plus `catalogos/tests.py`, `sistema/tests.py`, `common/tests.py`). Needs a MySQL user with `CREATE DATABASE` grants for the `test_<dbname>` throwaway DB — this has bitten onboarding before (`GRANT` must be run by a DB admin, not from Django).

---
*Generated via the `codebase-onboarding` skill, breadth-first pass. Living document — fix a line the moment recon proves it wrong, don't wait for a full re-run.*
