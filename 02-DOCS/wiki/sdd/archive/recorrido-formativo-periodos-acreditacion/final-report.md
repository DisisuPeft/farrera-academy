---
type: archive
title: Final report — recorrido-formativo-periodos-acreditacion
description: What shipped, why, the landing decision, and links to every proof artifact.
tags: [sdd, archive]
timestamp: 2026-11-11T23:30:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
---

# Final report — recorrido-formativo-periodos-acreditacion

## What this is

The ASDD (Agent Spec-Driven Development) cycle for the feature **"recorrido formativo, periodos y
acreditación"** is complete through closing review. This document is the explainer for the person
who will commit and land the work — not a record of a commit that already happened, because
**nothing in this feature has been committed**. The user's standing instruction for this whole
cycle was explicit: *"no hagas commits, yo los realizo."* Every git action below is a
recommendation with the exact command, never something this session ran.

## What the change does (behavior, not files)

Before this feature, a colaborador's enrollment (`Inscripcion`) was tied only to a `Curso`: they
could never re-take a course, progress/evidence was keyed directly to `colaborador` (impossible to
tell apart two enrollments to the same course), and competency accreditation fired from an
untestable Django signal with no safeguard against re-triggering or downgrading an already-granted
level.

After this feature:

- A `Curso` can have multiple **`Periodo`s** (enrollment windows: open/closed, with a start date).
  A colaborador enrolls into a specific `Periodo`, not just a `Curso` — so re-enrolling in a later
  period of the same course creates an independent, separately-tracked `Inscripcion`.
- Progress (`ProgresoTema`), evaluation results (`ResultadoEvaluacion`) and bloque answers
  (`ContenidoBloqueRespuesta`) are now keyed to the specific `Inscripcion`, not to the colaborador
  directly — so two enrollments to the same course never mix their evidence.
- Finalization is automatic and centralized: `FinalizacionService` checks the real completion
  criterion (all temas progressed + all evaluations passed, or just all temas if the course has
  none) and, in the same operation, hands off to `AcreditacionService` for competency accreditation
  — replacing a signal-based path that could silently re-fire or downgrade an already-granted level.
- An admin-only **`forzar`** action lets an Administrador finalize an enrollment that doesn't meet
  the normal criterion, through the exact same centralized service — same observable result as an
  automatic finalization, same audit trail.
- A colaborador can never set `completado_at`, a grade, or a competency level directly — every
  write path that matters is server-computed or routed through the services above.
- Closing a `Periodo` blocks only *new* enrollments to it; enrollments already inside it keep
  progressing and can still finalize normally.

Full behavioral contract: `02-DOCS/wiki/sdd/specs/recorrido-formativo-periodos-acreditacion.md`
(20 acceptance criteria).

## Why

Implements `02-DOCS/wiki/sdd/specs/recorrido-formativo-periodos-acreditacion.md`. The prior design
could not represent "the colaborador retook this course later" at all, and competency accreditation
ran from a signal with no defense against double-firing or downgrading a level a colaborador had
already earned — both real risks for a system whose output (accreditation) feeds HR/compliance
decisions.

## Testing

- **138 → 146 tests, all green** (`python manage.py test`, full project suite — not just this
  feature's tests). `manage.py check`: clean. No pending migrations.
- **42/42 task done-checks** verified with evidence — see
  `02-DOCS/wiki/sdd/verifications/recorrido-formativo-periodos-acreditacion-2026-11-11.md`.
- **20/20 spec acceptance criteria** mapped to a test that would catch their regression — same
  verification record, AC-by-AC table.
- **Closing review: APPROVE** (tier 2, three-refuter panel) — see
  `02-DOCS/wiki/sdd/reviews/recorrido-formativo-periodos-acreditacion.md`. Found and fixed, before
  this report, **2 real blockers no per-task review had caught**:
  1. A cross-tenant authorization gap — any Administrador of any company could read and forcibly
     finalize + accredit another company's colaborador's enrollment. Fixed: tenant scoping
     (`_scope_por_empresa`) now applied to the three admin viewsets that were missing it.
  2. An admin PATCH path that let `completado_at` be set directly, bypassing the centralized
     finalization service entirely. Fixed: the field (and `curso`) are now read-only on that
     serializer.
  Plus one should-fix (a deactivated tema could permanently block finalization) — fixed.
- Every fix above has its own TDD red→green test and was independently re-verified in a second
  review round (mutation-tested, reverted without residue, confirmed no new defect).

### What these checks would NOT catch

- **`ruff` (lint/format) did not run** — not installed in this environment. The constitution
  mandates it; style of the new code was reviewed by eye (by the per-task and closing reviewers),
  not by a linter.
- **No dependency/security audit tool ran** (no `pip-audit` or equivalent configured for this
  stack in this registry).
- **No line-coverage threshold was enforced.** 146/146 tests passing proves the tests that exist
  don't fail — it does not prove every new line is exercised by a test. The per-task and closing
  adversarial reviews (which did run, including live mutation testing of specific invariants) are
  the real mitigation for that gap, not a coverage number.
- **No production-scale migration dry run.** The migrations applied clean against the test
  database and in every task that introduced them, but were never run against a copy of the real
  production data. Recommend a dry run (or a staging apply) before this reaches production,
  particularly for `capacitacion/migrations/0009_inscripcion_periodo.py` (adds a `NOT NULL` FK)
  and `0010`–`0012` (change `unique_together`, remove columns).
- **One security question was left open, deliberately not fixed**: colaborador-facing course
  discovery (`/api/capacitacion/ver/cursos/`, `/mis-cursos/`, self-enrollment) applies no
  empresa/tenant scoping, even though `Curso.empresa` exists for exactly that purpose on the admin
  side. This is **not** a defect this feature introduced and **not** covered by any of its 20
  acceptance criteria — it surfaced because the closing review's security lens checked the
  empresa-scoping dimension broadly. Flagged for a human decision on whether and where to address
  it; does not block this feature.

## Risk

**Tier 2** (`npx @ericrisco/rsc risk` on the feature's actual file set: migrations + a
`competencias-signal`-class file). Human approval required before landing, per the computed tier
— this report does not substitute for that approval.

Classes touched: `migrations` (5 new Django migrations — one adds a `NOT NULL` FK, two remove
columns), `default` (services/serializers/views/tests), `competencias-signal` (deletion of
`competencias/signals.py`, replaced by an explicit service call).

Decision queue: **none** — no task or finding was ever parked; everything found was fixed and
re-verified. Review-after entries: **none** — nothing proceeded on an un-confirmed assumption.

## How to revert

Nothing has been committed, so there is nothing to `git revert` yet. Once committed:

- A straightforward `git revert <commit-sha>` (or, if squashed into one commit, revert that one)
  undoes the code. The migrations this feature adds are reversible with standard Django tooling
  (`python manage.py migrate capacitacion <previous-migration-name>`) — confirmed reversible in
  this environment via `migrate --plan` during the closing verify.
- A revert does **not** undo any `CompetenciaColaborador` records already accredited by
  `AcreditacionService` while this code was live, or any `Periodo`/`Inscripcion` rows already
  created — those are real data, not schema, and reverting code does not retroactively un-happen
  them. If a revert is needed after this has been live with real user activity, that data question
  needs a human decision, not an automatic rollback.

## Landing decision

**Not yet made — this is the human's call, per standing instruction.** This repository's
convention for this session has been direct, unbranched work on `main` (no feature branch was
opened), so the usual "merge a branch" / "open a PR" framing doesn't apply as-is. See the
companion note in `progress/recorrido-formativo-periodos-acreditacion.md` for the three options
adapted to that reality, and the suggested commit message(s) — none of which this session ran.

## Links

- Spec: `02-DOCS/wiki/sdd/specs/recorrido-formativo-periodos-acreditacion.md`
- Plan + tasks: `02-DOCS/wiki/sdd/plans/recorrido-formativo-periodos-acreditacion.md`
- Analysis (pre-implementation gate): `02-DOCS/wiki/sdd/analysis/recorrido-formativo-periodos-acreditacion.md`
- Progress (per-task ledger, append-only): `02-DOCS/wiki/sdd/progress/recorrido-formativo-periodos-acreditacion.md`
- Decisions log: `02-DOCS/wiki/sdd/decisions.md`
- Verification record (closing `verify`): `02-DOCS/wiki/sdd/verifications/recorrido-formativo-periodos-acreditacion-2026-11-11.md`
- Closing review record: `02-DOCS/wiki/sdd/reviews/recorrido-formativo-periodos-acreditacion.md`
