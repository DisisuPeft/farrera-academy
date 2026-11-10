# Decisions log — farrera-academy

Append-only. Every significant decision: date, options considered, why.

## 2026-11-07 — Constitution v1.0.0 ratified

**Options considered:**
- Formatter/linter: adopt ruff vs. leave unenforced.
- Test discipline for the upcoming periodos/inscripción/acreditación feature: strict TDD vs. tests-after (existing repo pattern).

**Decision:** ruff format + ruff check as the formatting/lint gate (new/changed files only, no retrofit). Strict TDD (red→green→refactor) specifically for the periodos/inscripción/acreditación feature line, with every referential-integrity rule proven by a test of the invalid case — tests-after remains acceptable for unrelated work.

**Why:** the upcoming work touches referential integrity (unique constraints, FKs, cross-table invariants) and competency accreditation directly tied to colaborador trust — the cost of an unproven constraint here is higher than in most of the existing codebase, which justifies a stricter bar for this feature line specifically rather than repo-wide.

**Also ratified:** `REVIEW.md` at project root, and `.rsc/sello-config.json` raising `competencias/signals.py`, `school_admin/settings.py`, and `REVIEW.md` itself to risk tier 2 (always-human review).

## 2026-11-07 — Spec scope split: periodos/acreditación vs. gating granular

**Options considered:** build the full user prompt in one spec (periodos + inscripción + acreditación + bloque obligatorio + video requerido + desbloqueo secuencial) vs. split into two specs.

**Decision:** split. This spec (`recorrido-formativo-periodos-acreditacion`) covers periodos/imparticiones, inscripción como unidad de participación, integridad referencial, y el servicio de acreditación centralizado. Gating granular (bloque obligatorio, reproducción de video requerida, desbloqueo secuencial de temas/módulos) is explicitly out of scope, deferred to a future spec.

**Why:** none of the three gating mechanisms exist today in any model field (confirmed by code reading); bundling them triples the real scope of an already non-trivial schema restructuring, and the prior audit (`docs/AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md`) explicitly warned against scope expansion without demonstrated need. User approved the split explicitly during `specify`'s frontier round.

## 2026-11-07 — Three model-design decisions for the periodos/acreditación spec

**Options considered and decided (user approved the recommended option in each):**
- `Inscripcion.periodo`: NOT NULL from this point forward (not nullable) — dev data is disposable, no backward-compat backfill needed.
- `ProgresoTema`/`ResultadoEvaluacion`/`ContenidoBloqueRespuesta`: drop the direct `colaborador` FK, derive via `inscripcion.colaborador` — avoids storing derivable information redundantly (constitution principle 12).
- `Periodo`: carries start date (required), end date (nullable), and an explicit open/closed state — needed for the inscription service to know whether a period accepts new inscriptions.

**Why:** recorded here so `plan` inherits them as settled constraints, not open questions; full rationale and risk notes are in the spec's "Points to clarify" (typed as `suposición tomada`).

## 2026-11-10 — Spec `recorrido-formativo-periodos-acreditacion` approved by user

User reviewed the written spec (after a fresh-eyes review found and the author fixed one real contradiction between "Users & context" and "Points to clarify" regarding admin-forced finalization) and gave explicit approval ("Apruebo") to proceed. Spec gate: PASS, 8 typed open points remain for `clarify`. Next: `clarify` resolves the 3 `pregunta abierta` entries before `plan`.

## 2026-11-10 — Spec `recorrido-formativo-periodos-acreditacion` clarified

`clarify` walked the gap checklist and found one additional gap `specify` missed: what happens to unfinished inscripciones when their periodo is closed. Resolved 4 questions with the user (one round, each recommendation accepted):
1. Finalización automática con evaluaciones = progreso en todos los Tema + ResultadoEvaluacion aprobatorio en cada Evaluacion.
2. Curso sin evaluaciones = progreso completo de temas basta.
3. Finalización manual excepcional por admin = sí, vía el mismo servicio centralizado (nunca editando el campo directamente).
4. Cerrar un periodo = solo bloquea nuevas inscripciones; las existentes siguen y pueden finalizar normalmente.

All 3 `suposición tomada` from `specify` validated unchanged. Baked into the spec body (new acceptance criteria, `## Clarifications` log, corrected `Users & context`). Status moved `draft` → `clarified`. Spec gate: PASS, 2 open points remain (both intentionally deferred: historial de niveles, interacción con gating granular futuro — neither blocks `plan`). Next: `plan`.

## 2026-11-10 — Plan written: `Inscripcion.curso` removed in favor of deriving via `periodo.curso`

**Options considered:** keep both `Inscripcion.curso` (direct FK) and `Inscripcion.periodo` (cross-validated against each other, as the original audit phrased it) vs. drop the direct `curso` FK entirely and derive it from `periodo.curso`.

**Decision:** drop it. `curso` is exposed as a computed read-only field in the `Inscripcion` serializer so the external API shape (including whatever the frontend already reads) does not change observably.

**Why:** constitution principle 12 forbids storing derivable information without a performance/audit justification, and keeping both fields would have reintroduced exactly the cross-table consistency check ("inscripción debe pertenecer a una impartición del mismo curso que referencia") that the prior audit flagged as a source of potential drift — removing the duplicate field makes that inconsistency structurally impossible instead of something to validate. This is a `plan`-level (HOW) decision, not a reopening of anything the spec (WHAT) decided.

Plan written to `02-DOCS/wiki/sdd/plans/recorrido-formativo-periodos-acreditacion.md`. No open architectural decisions remain blocking.

**Isolation offered and declined.** `plan`'s protocol treats worktree isolation as non-optional when work lands on `main` — asked explicitly given this change's scope (chained migrations, field removals). User chose to keep the already-ratified main-direct policy (constitution §4.15) without exception for this feature. Proceeding straight to `tasks` → `implement` on `main`.
