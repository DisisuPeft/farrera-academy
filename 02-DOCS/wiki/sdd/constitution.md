---
type: constitution
title: farrera-academy — Constitution
description: The non-negotiable principles every rsc-sdd phase obeys.
tags: [sdd, constitution]
timestamp: 2026-11-07T19:10:00Z
topic: sdd
version: v1.0.0
---

# farrera-academy — Constitution

> Version: v1.0.0 · Ratified: 2026-11-07 · Last amended: 2026-11-07
> The non-negotiable principles every rsc-sdd phase obeys. Stack mechanics live in
> `02-DOCS/wiki/stack/*` (none written yet); this file ratifies the principle and links detail as it appears.

## 1. Stack canon

1. Python 3.12 on Django 5.1.3 + Django REST Framework 3.15.2. Pinned in `requirements.txt`.
2. MySQL is the only supported database engine (`mysqlclient`). Any constraint proposed in a plan must be verified to actually hold on MySQL — not assumed from Postgres/SQLite docs (e.g. conditional unique indexes are not portable; `AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md` §4 already flagged this).
3. Auth is a custom JWT stack (`CustomJWTAuthentication` + `djangorestframework-simplejwt`), not session-based. Authorization is role-based via `HasRoleWithRoles([...])` checking `Role.nombre` — this is a separate system from the `sistema` app's menu-visibility permissions (Django `Permission` on `Modulo`/`Pestania`); the two are never to be conflated in code or in review.
4. Apps and their boundaries are fixed: `user` (auth/users), `sistema` (org structure + nav/menu permissions), `catalogos` (lookup/catalog tables), `capacitacion` (course authoring + consumption), `competencias` (competency accreditation), `common` (shared base models + management commands). A new concept is placed in the app that already owns its closest relative, not a new app, unless a plan argues otherwise.

## 2. Quality bar

5. New and touched code is formatted and lint-clean with `ruff format` + `ruff check` (zero warnings on changed files). Not retrofitted onto the existing codebase — applies going forward from this constitution's ratification date.
6. No strict static type checker is mandated (none exists today; not introduced as part of this work unless a future amendment says so).
7. **Tests gate the merge, TDD, for any task touching the periodos/inscripción/acreditación feature line:** red → green → refactor, one task at a time. Every referential-integrity rule introduced or changed (`unique_together`, `on_delete`, a cross-table invariant) ships with at least one test that proves it rejects the invalid case, not only that the valid case passes. For work outside that feature line, the existing repo pattern (write code, then the test battery for the increment) still applies — this principle does not retroactively demand TDD for unrelated changes.
8. A migration that changes a constraint (unique_together, on_delete, a new FK) is never merged without a test in the same task that exercises the constraint against a real `IntegrityError`/`ProtectedError`, not just a passing happy path.

## 3. Conventions

9. Model base classes are used as already defined in `common/models.py` and never mixed: `BaseModel` (`activo`/`creado_at`/`actualizado_at`) for ordinary content rows, `Base`/`BaseFileEntity` (`status`/`created_at`) for file-backed entities, `SoftDeleteModel` (`deleted_at`/`restore()`/`hard_delete()`) where soft-delete is the decided recovery mechanism. A serializer's `fields` tuple must match the actual base class of its model — this exact bug class has already occurred once in this project.
10. A foreign key toward recorded student evidence (progress, answers, results, accreditation) defaults to `on_delete=PROTECT` unless a plan explicitly argues for `CASCADE`/`SET_NULL` and states why evidence loss is acceptable there.
11. Server-computed fields that determine correctness, completion, or accreditation (`es_correcta`, `completado_at` once the planned fix lands, final grades, accredited levels) are never writable by the colaborador directly through a serializer — they are set by backend logic, not accepted as client input. This is a direct response to the confirmed gap in `AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md` §3.4.
12. Invariants that a single table's constraints can express (uniqueness, not-null, FK) are enforced at the database level, not only in `serializer.validate()` or `model.clean()`. Invariants spanning multiple tables/models are enforced by a transactional service function and proven by a test — never by application-layer convention alone.
13. Tests live under `<app>/tests/` (a package, following the pattern already established in `capacitacion/tests/`) using Django `TestCase` + DRF `APIClient`/`APIRequestFactory`.
14. Commit messages are plain, no gitmoji (`.rsc/.no-gitmoji` is intentional and stays unless the user reverses it).

## 4. Branching & shipping

15. Work lands directly on `main`; no branch, no PR gate required for this project (ratified at onboarding, `--workflow main`). `rsc risk` tier 2 changes (migrations, auth, secrets) still get the full review discipline from ASDD even without a PR to attach it to — the review and its verdict are recorded in `02-DOCS/wiki/sdd/reviews/` regardless of merge mechanism.
16. **Git authorship is the human's.** No `Co-Authored-By` an AI, no "generated with" footer in commits or PRs — already enforced in `.claude/settings.json` (`attribution.commit`/`attribution.pr` empty) and confirmed by explicit user instruction in this session.

## 5. Security & privacy floor

17. No secret is ever committed. `school_admin/settings.py` stays gitignored; local setup is documented, never a committed file with real credentials.
18. Authorization checks (`HasRoleWithRoles`, multi-tenant `_scope_por_empresa` scoping) are never bypassed for convenience in a colaborador-facing endpoint; a cross-tenant or cross-role data leak is always treated as a blocker finding, never a nit.

## 6. UX / accessibility floor

Not applicable — this project is a backend API with no UI of its own (consumed by a separate Next.js frontend out of this repo's scope).

## 7. Performance budgets

Not set — no named latency/throughput budget exists today. Not introduced speculatively; revisit if a concrete problem appears.

## 8. Knowledge & decisions

19. Every significant architectural decision (a model added, a constraint changed, an alternative chosen over another) is appended to `02-DOCS/wiki/sdd/decisions.md` with date, options considered, and why. The two prior audit documents in `docs/` (`AUDITORIA_AUTOGUARDADO_CONCURRENCIA.md`, `REVISION_CONCURRENCIA_HISTORIAL_PUBLICACION.md`, `AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md`) are treated as already-recorded prior decisions that later specs must respect or explicitly amend, not silently contradict.

## Definition of Done (the merge bar `verify` runs against)

A change ships only when ALL hold:

- [ ] `ruff format` + `ruff check` clean on changed files (principle 5).
- [ ] No type-checker gate exists; skip (principle 6).
- [ ] TDD followed for the periodos/inscripción/acreditación feature line; every new/changed integrity constraint has a test proving the invalid case fails (principles 7-8).
- [ ] Model base classes and `on_delete` policy followed (principles 9-10).
- [ ] No server-computed/authoritative field made colaborador-writable (principle 11).
- [ ] Single-table invariants enforced in the DB; cross-table invariants enforced in a tested transactional service (principle 12).
- [ ] Tests under `<app>/tests/`, Django `TestCase` + DRF client (principle 13).
- [ ] Commit message has no gitmoji, no AI attribution trailer, authored by the human (principles 14, 16).
- [ ] No secret committed; authorization/scoping checks intact (principles 17-18).
- [ ] Significant decisions logged in `decisions.md` (principle 19).

## Amendment log (append-only)

| Date | Version | Change | Why |
|------|---------|--------|-----|
| 2026-11-07 | v1.0.0 | Ratified initial constitution from the onboarding draft plus the interview answers (ruff as formatter/lint gate; strict TDD for the periodos/inscripción/acreditación feature line). | Project kickoff for ASDD; the upcoming work touches referential integrity and competency accreditation, so the quality bar needed to be explicit before `specify`. |
