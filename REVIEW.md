# REVIEW.md — farrera-academy

What the reviewer reads first. Specific to this repo; ratified alongside `02-DOCS/wiki/sdd/constitution.md` v1.0.0.

## What failure looks like here

- A new or changed `unique_together`/FK/`on_delete` that is not proven against a real `IntegrityError`/`ProtectedError` in a test (constitution principle 8).
- A cross-tenant or cross-role data leak — a colaborador reading another colaborador's data, or another `Empresa`'s course content, via a missing `_scope_por_empresa` check or a missing `HasRoleWithRoles` check.
- A server-computed/authoritative field (`es_correcta`, `completado_at`, final grade, accredited competency level) made writable by the colaborador through a serializer.
- A signal or save path that reprocesses an already-settled fact — the exact bug class found in `competencias/signals.py` (acreditación disparada por cualquier `save()` con `completado_at` ya poblado, no solo por la transición real).
- A model base class mismatch (`BaseModel` fields assumed on a `Base`/`BaseFileEntity` row, or vice versa) — already happened once in this project.
- A migration assumed safe on MySQL without checking MySQL actually supports the constraint as written (conditional unique indexes are the known trap here).
- A cross-table invariant (progreso belongs to the inscripción's curso, respuesta's opción belongs to its bloque, etc.) enforced only in `serializer.validate()`/`model.clean()` and not by a tested service-layer check — those methods don't run on every write path in Django.

## Paths to skip

- `*/migrations/*.py` — reviewed for the constraint they encode, not line-by-line style.
- `common/management/commands/seed_*.py` — dev/test data generators, not production logic.
- `**/__pycache__/`, `*.pyc` — never reviewed, should never have been tracked (pre-existing repo hygiene issue, out of scope to fix here unless asked).
- `core/events.py` — dead code, not wired into `INSTALLED_APPS`; flag once if touched, otherwise skip.

## Nit cap

Report at most **3** nits per review; the rest are dropped. Lead the summary with blockers.

## Always-human paths

These never merge on an agent's approval alone — tier 2 in `rsc risk`, human sign-off required:

- Any migration (`*/migrations/*.py` additions) that changes a constraint, not just adds a nullable field.
- `competencias/signals.py` and anything else wired to competency accreditation.
- `school_admin/settings.py` and anything touching `DEFAULT_AUTHENTICATION_CLASSES`/`DEFAULT_PERMISSION_CLASSES`.
- `.claude/settings.json`, `.rsc/sello-config.json`, and this file.

Mirror this list into `.rsc/sello-config.json` under `risk.raise` so `rsc risk` enforces it mechanically, not just advises it.

## Summary format

Every review summary opens with a count: `"N findings: X blocker(s), Y nit(s)"` — before anything else.
