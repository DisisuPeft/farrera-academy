---
type: review
title: Closing review — recorrido-formativo-periodos-acreditacion
description: Tier-2 three-refuter closing review against the full 20-criterion spec; 2 blockers + 1 should-fix found, fixed, and verified in round 2.
tags: [sdd, review, closing]
timestamp: 2026-11-11T23:10:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
source_state: 6a460f0 (dirty — uncommitted, by design; user commits manually)
---

# Closing review — recorrido-formativo-periodos-acreditacion

ASDD stage 5, once, before `ship`: the whole feature read adversarially against the spec's 20
acceptance criteria — not the per-task reviews, which already ran (one fresh-context reviewer per
tier-1 task, three refuters per tier-2 task) and are recorded in
`02-DOCS/wiki/sdd/progress/recorrido-formativo-periodos-acreditacion.md`.

## Risk tier

`npx @ericrisco/rsc risk` on the feature's actual file set (42 files: migrations, models, services,
serializers, views, tests — excluding unrelated harness/doc churn accumulated in the same working
tree) → **tier 2** (`migrations` class + `competencias-signal` class). Full three-refuter panel
required; human approval required at ship.

## Round 1 — three refuters in parallel, fresh context, blind

Each refuter got exactly four inputs: the task contract, the approved spec (20 ACs), the exact
source state (commit + dirty tree note), and the entry point (`manage.py test`). None saw this
conversation, the per-task reviews, or each other's report.

| Lens | Verdict | Findings |
| --- | --- | --- |
| correctness | CHANGES REQUESTED | 1 blocker, 2 should-fix (1 later dismissed, unreproduced) |
| security | CHANGES REQUESTED | 1 blocker, 1 should-fix, 1 question (non-blocking) |
| tests | APPROVE | 0 — ran 5 real mutations against the trickiest invariants, all caught |

### Consolidated findings (after my own verification against the code — not just trusting the reports)

1. **[blocker, security] CONFIRMED** — `InscripcionViewSet`/`ProgresoTemaViewSet`/`ResultadoEvaluacionViewSet`
   (`capacitacion/views.py`) never applied `_scope_por_empresa`, unlike all 7 sibling admin viewsets
   added in this same diff. Any Administrador (role-gated only, not tenant-gated) could read and
   forcibly finalize + accredit another company's colaborador's inscripción. Verified live by the
   security lens against the repo's own `admin_a`/`admin_b`/`empresa_a`/`empresa_b` fixtures;
   independently confirmed by me via `git diff` (the helper itself is wholly new in this diff,
   applied to 7 viewsets, omitted from these 3).

2. **[blocker, correctness] CONFIRMED** — admin `InscripcionSerializer`
   (`capacitacion/serializers/progreso.py`) left `completado_at` and `curso` writable via PATCH,
   letting an Administrador bypass `FinalizacionService`/`AcreditacionService` entirely and
   contradicting the spec's Clarification #3 verbatim ("nunca editando completado_at... directamente").
   Confirmed by direct code read: only `inscrito_at`/`creado_at`/`actualizado_at` were read-only.

3. **[should-fix, correctness] CONFIRMED** — `FinalizacionService._criterio_cumplido` didn't filter
   `Tema` by `activo=True`, unlike the colaborador-facing progress serializers (which do) — a
   deactivated tema could permanently block finalization while the colaborador's UI showed 100%.
   Confirmed by direct code read.

4. **[should-fix, correctness] DISMISSED** — a possible idempotency double-timestamp failure the
   correctness lens saw once and could not reproduce, explicitly attributing it to its own repeated
   test runs corrupting the MySQL test database (not to the code). Dismissal evidence: 5 consecutive
   clean runs of `capacitacion.tests.test_finalizacion_service` with no failure, by me, in a fresh
   shell.

5. **[question, security] non-blocking, out of this spec's scope** — colaborador-facing course
   discovery/enrollment (`CursoColaboradorViewSet`, `MisCursosViewSet`, `MisInscripcionesViewSet.create`)
   applies no empresa scoping, despite `Curso.empresa` existing for exactly that purpose on the admin
   side. The security lens itself flagged this as a question, not an assertion of defect: none of
   the spec's 20 acceptance criteria mention `empresa`/multi-tenancy, and the empresa-scoping
   initiative visible in this same diff is a separate, undocumented-in-this-spec effort. Left for
   the human to decide whether and where it should be addressed — not blocking this feature's ship.

## Fixes applied (same session, before round 2)

- `capacitacion/views.py` — added `_scope_por_empresa(qs, self.request.user, 'curso' | 'inscripcion__curso')`
  to the three viewsets' `get_queryset()`.
- `capacitacion/serializers/progreso.py` — added `curso`, `completado_at` to `InscripcionSerializer.read_only_fields`.
- `capacitacion/services/finalizacion_service.py` — added `activo=True` to the `Tema` filter in `_criterio_cumplido`.
- New tests: `capacitacion/tests/test_empresa_scoping.py` (`InscripcionScopingTests`,
  `InscripcionCamposDeSoloLecturaAdminTests`, 7 tests), `capacitacion/tests/test_finalizacion_service.py`
  (1 test). Full suite: 138 → **146/146 green**.

## Round 2 — verification of the fixes, fresh context (`finding-verifier`)

Verified fix-by-fix, not re-litigating whether the originals were real:

- **Fix 1**: FK chains traced independently (`Inscripcion.curso` direct FK; `ProgresoTema`/`ResultadoEvaluacion`
  → `inscripcion__curso`) — correct. Mutation (removed the scoping line) → both new scoping tests
  failed as expected; restored, zero residue. No over-blocking: same-empresa admin still succeeds.
  Null-empresa ("global curso") path unaffected — `_scope_por_empresa` is generic over the FK prefix,
  not special-cased for `Curso`.
- **Fix 2**: only caller of `InscripcionSerializer` is `InscripcionViewSet`; no create-path regression
  (Inscripcion creation only ever happens via the colaborador-facing service, never via this admin
  ViewSet's POST in any test or code path). Mutation (reverted `read_only_fields`) → both new tests
  failed as expected; restored, zero residue.
  - **Fix 3**: mutation (removed `activo=True`) → the new test failed as expected; restored, zero
  residue. Confirmed should-fix severity is correct (narrow blast radius, no auth/data-leak dimension).
- **No new defect** introduced by any of the three fixes.

Full suite re-confirmed independently by the round-2 verifier: 146/146, `manage.py check` clean.

## Acceptance criteria — re-confirmed post-fix

The fixes touch no behavior covered by the spec's 20 ACs (they close gaps in the *admin* surface,
which the spec's ACs don't separately enumerate beyond AC10's colaborador-side self-finalization
rule and Clarification #3's "always via the service" rule for admins — both of which the fixes now
actually satisfy for the admin surface too, closing a gap the original per-task implementation of
AC10/AC15 left open). See `02-DOCS/wiki/sdd/verifications/recorrido-formativo-periodos-acreditacion-2026-11-11.md`
for the full AC-by-AC mapping, still valid; re-run after the fixes confirms no regression (146/146).

## Verdict: APPROVE

Both blockers fixed and independently re-verified; the should-fix fixed; the one dismissed finding
has contrary evidence on record; the one open question is explicitly non-blocking and flagged for
the human, not for this feature's gate. Ready for `ship`. Human approval required before merge —
tier 2, per the computed risk.
