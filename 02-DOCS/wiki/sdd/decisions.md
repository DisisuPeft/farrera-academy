# Decisions log — farrera-academy

Append-only. Every significant decision: date, options considered, why.

## 2026-11-07 — Constitution v1.0.0 ratified

**Options considered:**
- Formatter/linter: adopt ruff vs. leave unenforced.
- Test discipline for the upcoming periodos/inscripción/acreditación feature: strict TDD vs. tests-after (existing repo pattern).

**Decision:** ruff format + ruff check as the formatting/lint gate (new/changed files only, no retrofit). Strict TDD (red→green→refactor) specifically for the periodos/inscripción/acreditación feature line, with every referential-integrity rule proven by a test of the invalid case — tests-after remains acceptable for unrelated work.

**Why:** the upcoming work touches referential integrity (unique constraints, FKs, cross-table invariants) and competency accreditation directly tied to colaborador trust — the cost of an unproven constraint here is higher than in most of the existing codebase, which justifies a stricter bar for this feature line specifically rather than repo-wide.

**Also ratified:** `REVIEW.md` at project root, and `.rsc/sello-config.json` raising `competencias/signals.py`, `school_admin/settings.py`, and `REVIEW.md` itself to risk tier 2 (always-human review).
