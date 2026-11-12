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

## 2026-11-10 — Plan revised: `Inscripcion.curso` reinstated, coexists with `periodo`

**Reversal of the prior same-day decision** ("curso removed in favor of deriving via periodo.curso"). User explicitly asked to keep both FKs coexisting and to evaluate the real blast radius of divergence before deciding.

**What changed the decision:** a grep-verified (not hypothetical) inventory of the actual codebase found 7 real sites reading `Inscripcion.curso` directly for business logic, several of them bypassing any serializer entirely (a signal, two view methods, a serializer `source=` on a different model) — a computed read-only serializer field would not have served any of them. Two of the seven are pre-existing real bugs this feature would otherwise aggravate: `MiPerfilCompetenciasView` (competencias/views.py:177) silently collapses two inscripciones to the same curso into one dict entry, and `MiInscripcionRutaPerfil` (competencias/views.py:286-303) treats "ever enrolled in this curso" as done and creates `Inscripcion` rows via `curso` alone with no `periodo` at all.

**Decision:** keep `curso` as a real, coexisting FK column on `Inscripcion`. It is never independently writable by any caller — only `InscripcionService` writes it, always copied from `periodo.curso` at the same time `periodo` is set. The invariant holds by construction (single write path), proven by a test, not by a database constraint (MySQL cannot express a cross-table column equality).

**Three behavior decisions made alongside this** (user approved the recommended option in each):
- `MiPerfilCompetenciasView`: show the most recent inscripción per curso (by `periodo.fecha_inicio`/`inscrito_at` descending), never an iteration-order artifact.
- `MiInscripcionRutaPerfil`: auto-enroll via `InscripcionService` into the most recently opened periodo of the next curso; fail explicitly if none is open — never auto-create a periodo.
- `get_inscrito`/`get_progreso` (capacitacion/serializers/colaborador.py): compute against the colaborador's most recent inscripción to that curso, not the union of all of them.

**Deferred:** the pre-existing absence of `_scope_por_empresa` on `InscripcionViewSet`/`ProgresoTemaViewSet`/`ResultadoEvaluacionViewSet` — not caused by this feature, logged as a finding for a separate future scoping/security spec, not fixed in this cycle.

Plan updated in place (§0, §2, §4, §6, §7). Next: `tasks`.

## 2026-11-10 — Tasks appended to the plan

40 tasks (T001-T040), TDD-shaped (test-then-impl pairs for every behavioral unit), each traced to a spec acceptance criterion (17 total, all covered both ways — no untraced task, no uncovered criterion) or to a plan §4 remediation item. Risk forecast per task group verified with `npx @ericrisco/rsc risk <paths>` (not guessed): migrations and model changes (T001, T002, T009, T010, T011) and anything touching `competencias/signals.py` (T024, T025) come back tier 2 — 7 of 40 tasks, each needing the three-refuter panel and human approval at `implement`. Everything else is tier 1. Suggested delivery: `ask-on-risk` (well over the 400-line review budget in `config.yaml`, and the tier-2 tasks must each pause for review before their dependents continue).

Two genuine disjoint-file parallel-safe pairs found during slicing (T011 vs. T009/T010 — different model file; T037/T038 vs. the competencias/views.py group T033-036 — different file); everything else left sequential by default per the "when in doubt, leave blank" rule, since several plan-stage "parallelizable" guesses turned out to share a file once the actual files were identified (ProgresoTema and ResultadoEvaluacion both live in `capacitacion/models/progreso.py`, not separate files as the plan's §6 sequencing had loosely implied).

Next: `analyze` — cross-check constitution ↔ spec ↔ plan ↔ tasks before `implement`.

## 2026-11-10 — Analyze: first pass BLOCKED (1 HIGH, 3 MEDIUM), fixes applied, re-run PASS

First pass found 1 HIGH (the 3 behavior-fix tasks T033-T038 changed real observable API behavior, decided explicitly with the user, but never entered the spec — only `decisions.md` and the plan) and 3 MEDIUM (AC10's "calificación final" unnamed field; T027/T032 missing Interfaces blocks for context-isolated implementers; `competencias/tests.py` is a single module today but T024/T033 done-checks assumed a `competencias/tests/` package).

Fixes applied in place: spec gained 3 new acceptance criteria (AC18-AC20) plus a `## Clarifications` entry citing this log as their origin; plan §4 now names `ResultadoEvaluacion.correctas`/`.total` as the AC10 field; T027 and T032 gained Interfaces blocks; new task T041 (convert `competencias/tests.py` to a package) inserted with T024/T033 updated to depend on it. Spec gate: PASS (20 ACs now). Re-ran `analyze`: GATE: PASS, 20/20 criteria covered both ways, zero findings.

Next: `implement`.

## 2026-11-10 — T002: dev DB `Inscripcion` rows deleted to unblock migration

Context: adding `Inscripcion.periodo` as NOT NULL couldn't generate a migration while 50 pre-existing (fake/seed) `Inscripcion` rows existed in the dev MySQL database — Django's autodetector has no way to backfill a real value for them. Options: (a) delete the disposable rows and proceed, (b) recreate the whole dev DB from scratch. User chose (a). Executed via raw SQL (nulling `competencias_competenciacolaborador.origen_id` first to clear its FK to `Inscripcion`, then deleting all `capacitacion_inscripcion` rows) since the ORM model already referenced the not-yet-created `periodo_id` column. Verified by the T002 security-lens reviewer that nulling `origen_id` changes no computed authorization decision — it only blanks a display field on synthetic rows that no longer exist. Confirms Global Constraints' assumption (dev data disposable) was exercised, not just theoretical.

## 2026-11-10 — T004: `IntegrityError` catch needs a nested atomic (savepoint)

Context: the tier-1 reviewer flagged that a bare `except IntegrityError` inside `InscripcionService.crear` could mask a real FK violation as an ordinary "ya inscrito" result. Fix: narrow the catch to re-check whether an `Inscripcion(colaborador, periodo)` row actually exists before returning `InscripcionDuplicada()`, re-raising otherwise.

**What that fix broke on first try:** adding the existence-check query right after catching `IntegrityError`, without first putting the failing `create()` in its own nested `transaction.atomic()` (a savepoint), raised `django.db.transaction.TransactionManagementError: An error occurred in the current transaction. You can't execute queries until the end of the 'atomic' block.` — this is MySQL/Django's real behavior (not SQLite's more forgiving one), confirmed by actually running the test suite, not inferred. Wrapping the `create()` call in its own `with transaction.atomic():` (nested inside the outer one that holds the `select_for_update` lock) creates a savepoint; Django rolls back to it automatically on the `IntegrityError`, leaving the outer transaction usable for the follow-up existence check.

**Why this matters beyond this one task:** any future service in this plan (`EvidenciaService`, `FinalizacionService`) that catches an `IntegrityError` and needs to query afterward in the same request must use the same nested-atomic/savepoint pattern — a bare `except` inside a single un-nested `atomic()` works by accident only as long as nothing queries the DB again before the block exits.

## 2026-11-10 — T005/T006: la prueba de concurrencia nunca estuvo en rojo contra la implementación real

Contexto: T005 pedía escribir una prueba de concurrencia real (dos hilos, conexiones de BD separadas) que falle contra el servicio actual; T006 pedía ajustar `InscripcionService.crear` hasta que esa prueba quedara verde. La prueba (`ConcurrenciaTest`, `capacitacion/tests/test_inscripcion_service.py`) pasó verde desde el primer intento contra la implementación de T004 — nunca estuvo en rojo.

**Verificación de que la prueba no era teatro:** mutando temporalmente el servicio para quitar `select_for_update()`, la prueba seguía en verde (8/8 corridas) — el índice único de MySQL sobre `(colaborador_id, periodo_id)` ya serializa los dos `INSERT` y el manejo de `IntegrityError` ya existente convierte al perdedor en `InscripcionDuplicada()` correctamente. Esto confirma que `select_for_update()` protege una invariante distinta (lectura consistente de `periodo.estado` bajo cierre concurrente), no la unicidad de la inscripción, que ya la garantiza la restricción de BD.

**Hallazgo real del panel de revisión (no detectado por esta primera verificación):** el revisor (`refuter-tests`) probó un segundo mutante — quitar por completo el bloque `try/except IntegrityError` — y encontró que la prueba **seguía en verde**, porque un hilo que lanza una excepción no capturada simplemente nunca agrega su resultado a la lista compartida (la excepción es absorbida por el manejador de excepciones del hilo de Python, `join()` no la repropaga), reduciendo la muestra de 2 a 1 resultado y dejando pasar la aserción `len(exitosos) == 1` por la razón equivocada. Corregido agregando `self.assertEqual(len(resultados), 2, ...)` antes de contar los exitosos. Verificado empíricamente: con esa aserción, el mismo mutante (sin `except IntegrityError`) ahora falla 3/3 corridas; la implementación real sigue pasando (suite completa 72/72).

**Por qué esto importa más allá de esta tarea:** cualquier prueba de concurrencia con hilos en este plan debe verificar explícitamente que todos los hilos lanzados efectivamente devolvieron un resultado (no solo contar los resultados "exitosos" de los que sobrevivieron) — un hilo que muere en silencio reduce la muestra en vez de fallar la prueba.

## 2026-11-10 — T009: orden de operaciones en la migración de `ProgresoTema` y 179 filas de seed borradas

Contexto: agregar `ProgresoTema.inscripcion` (FK PROTECT NOT NULL) y quitar `colaborador` requería borrar 179 filas de seed preexistentes (sin FK que las referencie, sin dato de inscripción posible para backfill) — mismo patrón ya aplicado en T002, ahora ya establecido como convención del proyecto (Global Constraints). El intento de borrado por shell fue bloqueado por el clasificador de modo automático; se pidió confirmación explícita al usuario, quien autorizó el borrado.

**Orden de operaciones de la migración generada automáticamente estaba roto:** `makemigrations` generó `AlterUniqueTogether` (con los nombres nuevos) ANTES de `AddField`, lo que falla con `FieldDoesNotExist` porque el campo `inscripcion` todavía no existe en ese punto. Corregido reordenando a: `AddField(inscripcion)` → `AlterUniqueTogether(nuevo={('inscripcion','tema')})` → `RemoveField(colaborador)` — en ese punto ambas columnas (`colaborador_id` vieja, `inscripcion_id` nueva) coexisten, así que Django puede calcular correctamente los índices compuestos viejo/nuevo sin error. Verificado aplicando limpio tanto en una BD de test fresca como en la BD de dev real.

**Por qué esto importa más allá de esta tarea:** cuando `makemigrations` combina un cambio de `unique_together` con un `AddField`/`RemoveField` sobre los mismos campos, el orden que autogenera no siempre es seguro — hay que revisar y, si es necesario, reordenar a mano: el campo nuevo debe existir antes de que `AlterUniqueTogether` lo use, y el campo viejo debe seguir existiendo mientras `AlterUniqueTogether` todavía necesita calcular el índice compuesto que lo incluye.

Panel de 3 refutadores (tier 2, clase `migrations`): correctness 0 hallazgos (verificó independientemente que el orden de operaciones aplica limpio en una BD genuinamente fresca, no solo en la BD de dev ya parchada a mano); security 0 hallazgos (sin cambio de decisión de autorización, sin ruta de fuga vía `related_name='progresos_tema'` — no hay código que lo recorra todavía); tests 1 `nit` (no bloqueante) — `test_colaborador_ya_no_existe_como_campo_directo` por sí sola solo prueba que el string `'colaborador'` ya no resuelve, no que `inscripcion` lo reemplazó correctamente, pero las otras 4 pruebas del mismo archivo ya cubren eso vía despacho de kwargs. Sin fixes requeridos. 78/78 verde en todo el proyecto.

## 2026-11-10 — T011: `ContenidoBloqueRespuesta` rompe una suite ya existente, no solo consumidores sin cobertura

Contexto: mismo patrón que T009/T010 (`inscripcion` FK PROTECT NOT NULL, quitar `colaborador`), pero sin filas de seed que borrar (tabla ya estaba vacía) y sin interacción con `unique_together`, así que la migración autogenerada (`RemoveField(colaborador)` → `AddField(inscripcion)`) aplicó limpia sin reordenar. La diferencia real frente a T009/T010: `capacitacion/tests/test_respuestas_bloque.py` ya existía y ejercía el camino completo vista→serializer→modelo para este modelo específico, cosa que no pasaba con `ProgresoTema`/`ResultadoEvaluacion`. Al quitar `colaborador` del modelo, 5 de esas pruebas (antes verdes) ahora fallan con `TypeError`, porque `views_colaborador.py`/`serializers/colaborador.py` todavía llaman `ContenidoBloqueRespuesta.objects.create(colaborador=...)`.

**Decisión:** aceptar esta regresión como transicional, NO corregirla dentro de T011. El propio plan ya anticipó este riesgo exacto en su tabla de riesgos ("Eliminar el `colaborador` FK directo... rompe silenciosamente consultas existentes...") y asignó su mitigación a una tarea posterior (T032, reconectar `views.py`/`views_colaborador.py` a los servicios). Corregir `views_colaborador.py`/`serializers/colaborador.py` ahora sería scope creep de una tarea de esquema.

**Por qué es seguro dejarlo así:** el panel de 3 refutadores verificó independientemente (no solo leyendo el diff, sino ejecutando la suite real) que la ruptura es *fail-closed* — `TypeError`/`FieldError`, nunca una respuesta silenciosamente incorrecta o una fuga entre colaboradores. No es la misma clase de bug que "un colaborador ve el progreso de otro"; es "la función todavía no está reconectada y lo dice claramente".

**Por qué esto importa más allá de esta tarea:** T032 debe incluir explícitamente `test_respuestas_bloque.py` en su verificación de "suite completa verde" — las 5 pruebas ahí deben volver a pasar como parte del done-check de T032, no antes.

Panel de 3 refutadores (tier 2, clase `migrations`): correctness 0 hallazgos (confirmó orden de migración seguro, `PROTECT` correcto en modelo y migración, tabla vacía al generar el default); security 0 hallazgos (confirmó fail-closed en los 2 call-sites transicionales, sin fuga vía `related_name='respuestas_bloque'`, `es_correcta` intacto); tests 1 `nit` (no bloqueante, idéntico al de T009/T010 y confirmado explícitamente como no empeorado por esta tarea) — `test_colaborador_ya_no_existe_como_campo_directo` no distingue "campo quitado" de "campo renombrado a otro nombre" (probado con un mutante real: agregar un segundo FK `colaborador_legacy` nullable deja las 5 pruebas en verde). Sin fixes requeridos. 83/88 verde en todo el proyecto — las 5 fallas son la regresión transicional ya descrita, no hallazgos nuevos.

## 2026-11-10 — T012/T013: resolución de "inscripción activa" debe ser por curso, no por la inscripción más reciente del colaborador en general

Contexto: la primera implementación de `EvidenciaService._resolver_inscripcion_activa(colaborador)` resolvía la inscripción más reciente del colaborador **sin filtrar por curso** — es decir, "la última inscripción que hizo, sea del curso que sea" — y luego comparaba el curso de esa inscripción contra el curso del `tema` recibido, devolviendo `ContenidoAjeno()` si no coincidían. El test de T012 (una sola inscripción en el fixture) no podía distinguir esto de la resolución correcta y pasó en verde con la implementación incorrecta.

**Hallazgo del panel (bloqueante):** el plan (`§3 Interfaces`, contrato de `EvidenciaService.registrar_progreso`) especifica la precondición exacta como "existe una Inscripcion no finalizada de ese colaborador cuyo periodo.curso == tema.modulo.curso" — es decir, la resolución debe ser por curso, no por fecha más reciente sin más. Con la implementación original, un colaborador con una inscripción activa y legítima al curso A (abierta, en progreso) que luego se inscribe a un curso B distinto, perdería la capacidad de seguir registrando progreso en el curso A: `_resolver_inscripcion_activa` devolvía la inscripción al curso B (la más reciente por fecha) y el cruce contra el curso del tema de A fallaba, rechazando contenido legítimo con `ContenidoAjeno()`.

**Decisión:** `_resolver_inscripcion_activa(colaborador, curso)` ahora recibe el curso del contenido y filtra directamente por `(colaborador, curso, completado_at__isnull=True)`, tomando la más reciente por `inscrito_at` si hay varias (caso AC3/AC16: mismo curso, periodos distintos). Si esa consulta no encuentra nada, se distingue el motivo del rechazo con una segunda consulta: si el colaborador tiene **alguna** inscripción activa (a cualquier curso) → `ContenidoAjeno()` (el contenido es ajeno a lo que está cursando); si no tiene ninguna → `InscripcionNoEncontrada()`.

**Por qué esto importa más allá de esta tarea:** cualquier resolución de "la inscripción actual/activa de un colaborador" en este plan (`FinalizacionService`, reconexión de vistas en T032) debe filtrar explícitamente por el curso del contenido referenciado — nunca asumir que "la más reciente del colaborador, sin más" identifica la inscripción correcta, porque el modelo de negocio permite inscripciones concurrentes a cursos distintos.

**Caso límite identificado pero no corregido (no bloqueante):** un colaborador con una inscripción YA FINALIZADA al curso exacto del contenido, más una inscripción activa a otro curso distinto, recibe `ContenidoAjeno()` en vez de algo como "ya completaste este curso" — la etiqueta es imprecisa pero el efecto (rechazo) es correcto, y hoy no hay ningún caller que distinga entre los dos tipos de sentinel (el servicio todavía no está conectado a ninguna vista). Se deja así; si en T032 algún caller necesita distinguir estos casos, se revisita entonces.

Panel inicial (tier 1, 1 revisor `refuter-correctness`): 1 `blocker` (el descrito arriba) + 1 `should-fix` (el test de T012 no podía distinguir la resolución correcta de la incorrecta, por tener una sola inscripción en el fixture). Fix aplicado + prueba de triangulación nueva (`test_resuelve_por_curso_no_por_inscripcion_mas_reciente`, dos inscripciones activas a cursos distintos) que se probó mutando el resolver de vuelta al comportamiento bugueado — el mutante hace fallar exactamente esa prueba nueva. Ronda 2 (mismo revisor): 0 hallazgos nuevos, confirmó con su propio mutante independiente que el cierre es real, y que la suite completa no tiene regresiones más allá de las 5 fallas ya aceptadas de T011.

## 2026-11-11 — T018/T019: un curso sin ningún tema finaliza vacuamente sin evidencia

Contexto: `FinalizacionService._criterio_cumplido` comprobaba "todos los temas del curso tienen `ProgresoTema`" comparando dos conjuntos (temas del curso vs. temas con progreso de esa inscripción). Para un curso con cero temas, ambos conjuntos son el conjunto vacío — la comprobación se cumple vacuamente.

**Hallazgo del panel (should-fix):** una inscripción a un curso sin ningún módulo/tema (nada en el modelo lo impide — ni `Curso`, ni `Periodo`, ni `InscripcionService.crear` exigen contenido mínimo) finaliza en la primera llamada a `reevaluar()`, sin ninguna evidencia real registrada. Reproducido en vivo por el revisor con una prueba de sondeo (creó el curso vacío, la inscripción real, llamó `reevaluar` una vez, `completado_at` quedó asignado de inmediato).

**Decisión:** agregar una guarda explícita — si el curso no tiene ningún tema, el criterio nunca se cumple (`return False`), en vez de dejar que la comparación de conjuntos lo decida vacuamente. Un curso sin contenido no puede finalizar por el camino automático; si alguna vez hiciera falta cerrarlo, es un caso para la finalización excepcional de un administrador (T027), no para este criterio.

**Por qué esto importa más allá de esta tarea:** cualquier criterio futuro de este plan que compare "conjunto esperado" contra "conjunto cumplido" (por ejemplo, si T020/T021 agregan lógica similar para evaluaciones) debe guardarse explícitamente contra el conjunto esperado vacío — una comparación de igualdad de conjuntos nunca distingue por sí sola "cumplido" de "no hay nada que cumplir".

Panel inicial (tier 1, 1 revisor `refuter-correctness`): 1 `should-fix` (el descrito arriba; también hizo un barrido exhaustivo de la comparación float-vs-Decimal del umbral de aprobación buscando una divergencia con la aritmética racional exacta — 2 millones de pruebas aleatorias más un barrido completo, sin encontrar ninguna, así que no lo reportó como hallazgo). Fix aplicado (guarda `if not temas_curso.exists(): return False`) + prueba nueva (`test_no_finaliza_un_curso_sin_ningun_tema`) verificada con un mutante que reproduce exactamente el bug original. Ronda 2 (mismo revisor): 0 hallazgos, confirmó además que `ProgresoTema.tema` es `on_delete=PROTECT` (así que el escenario "temas borrados bajo una inscripción con progreso" ya es imposible por esquema, no solo improbable), y que la suite completa no tiene regresiones más allá de las 5 fallas ya aceptadas de T011.

## 2026-11-11 — T041: `competencias/tests.py` nunca existió, la premisa del plan estaba obsoleta

Contexto: T041 pedía "convertir `competencias/tests.py` en el paquete `competencias/tests/`, migrando las pruebas existentes... sin perder cobertura" — resolviendo un hallazgo MEDIUM de `analyze`. Al llegar a esta tarea (como prerrequisito de T024, que necesita poder agregar `competencias/tests/test_acreditacion_regression.py`), se comprobó que `competencias/tests.py` **no existe en el repositorio** (ni en el working tree, ni en ningún commit de `HEAD`) — `python manage.py test competencias` ya corría "0 tests" antes de tocar nada.

**Decisión:** tratar T041 como trivial — no hay nada que migrar. Se creó directamente `competencias/tests/__init__.py` (paquete vacío), siguiendo el mismo patrón de `capacitacion/tests/`. El done-check ("`python manage.py test competencias` sigue verde tras la migración; `competencias/tests.py` ya no existe, `competencias/tests/__init__.py` sí") se cumple literalmente: 0 tests antes, 0 tests después, sin pérdida de cobertura porque no había ninguna que perder.

**Por qué esto importa más allá de esta tarea:** el hallazgo de `analyze` que generó T041 se basó en un estado del repositorio que ya no coincide con la realidad (probablemente el archivo se eliminó o nunca se creó en algún punto entre el `analyze` y este momento del `implement`). No se trata como contradicción bloqueante porque no hay conflicto de diseño ni pérdida de información — es una tarea que simplemente ya estaba resuelta por omisión. Sirve de recordatorio: el estado real del árbol de trabajo (`git status`, `ls`) siempre gana sobre lo que un documento de fases anteriores asumía, consistente con la propia guía del `implement` sobre resume/recovery.

## 2026-11-11 — T025: faltaba una prueba que probara "nunca retrocede" al extraer `AcreditacionService`

Contexto: al extraer `AcreditacionService.acreditar` desde el `post_save` de `competencias/signals.py` (ahora eliminado) se preservó literalmente la comparación `cc.nivel.orden > registro.nivel.orden` (estrictamente mayor — solo sube, nunca baja), tal como ya documentaba el comentario original del signal. Pero ninguna prueba del repositorio ejercía ese caso: mutar la comparación a `!=` (permitiendo también degradar) dejaba toda la suite de `competencias` en verde.

**Decisión:** agregar `test_acreditar_nunca_baja_un_nivel_ya_otorgado` — un colaborador con nivel 3 ya otorgado por otra competencia, una nueva acreditación que mapearía a nivel 2, y se verifica que el nivel se queda en 3. Verificado con el mutante exacto que el panel probó (`>` → `!=`) — el mutante ahora sí rompe esta prueba.

**Por qué esto importa más allá de esta tarea:** cualquier invariante mencionada solo en un comentario/docstring ("solo sube, nunca retrocede") y nunca ejercida por una prueba es, en la práctica, una invariante no garantizada — un refactor futuro de `AcreditacionService` podría romperla silenciosamente sin que ningún test lo note. Esta es la misma clase de hallazgo que motivó la auditoría original (AC7): una garantía de negocio sobre niveles de competencia que dependía de la lectura humana del código, no de una prueba ejecutable.

Panel inicial (tier 2 real — confirmado por `rsc risk` al eliminar `competencias/signals.py`, elevado en `.rsc/sello-config.json` como clase `competencias-signal`): correctness 0 hallazgos (confirmó extracción fidedigna de la lógica, orden transaccional correcto, `AcreditacionService.acreditar` con un único call-site de producción, sin residuo del signal eliminado — no pudo ejecutar la suite en su propio sandbox por un problema de BD de test no relacionado con este diff, compensado por mi propia ejecución exitosa); security 0 hallazgos (confirmó que la vulnerabilidad de confianza original — subir de nivel por un simple resave — queda cerrada, protección "nunca retrocede" preservada, sin segundo call-site que la reabra, sin fuga de datos); tests 1 `should-fix` (el descrito arriba). Fix aplicado y verificado con el mutante exacto del revisor. 100/105 verde en el proyecto — las 5 fallas restantes son la regresión ya aceptada de T011/T032.

## 2026-11-11 — T032: cierre de toda la rotura transicional acumulada desde T009/T010/T011; 2 gaps preexistentes encontrados y anotados (no corregidos, no causados por este diff)

Contexto: T032 reconecta `capacitacion/views.py` y `views_colaborador.py` a `InscripcionService`/`EvidenciaService`/`FinalizacionService.forzar` en vez de la creación directa de modelos. Esta era la última pieza para cerrar la rotura transicional documentada desde T009 — después de este cambio, **la suite completa del proyecto pasó de 125/130 (5 fallas ya conocidas) a 130/130, por primera vez en todo este ciclo de implementación**.

**Trabajo adicional descubierto y resuelto dentro del mismo alcance:**
1. `EvidenciaService.registrar_progreso`/`registrar_respuesta_bloque` nunca invocaban `FinalizacionService.reevaluar(inscripcion)` después de guardar — una postcondición del plan §3 que quedó pendiente desde T013 porque `FinalizacionService` todavía no existía en ese momento (se creó en T019). Corregido agregando la invocación a los tres métodos `registrar_*`.
2. `EvidenciaService.registrar_resultado_evaluacion` nunca se implementó (quedó como pregunta abierta desde T013, sin tarea explícita en la tabla). Implementado ahora, siguiendo el mismo patrón de validación cruzada que `registrar_progreso`/`registrar_respuesta_bloque`.
3. Los serializers/vistas admin (`capacitacion/serializers/progreso.py`, `capacitacion/views.py`) también referenciaban `colaborador` directo sobre `ProgresoTema`/`ResultadoEvaluacion` (crasheaban al construirse, no solo al escribir) — corregidos a `inscripcion`/`inscripcion__colaborador`, antes de que ningún test los hubiera ejercido jamás.
4. `get_inscrito`/`get_progreso` (`capacitacion/serializers/colaborador.py`) también crasheaban por el mismo motivo — corregido el crash (cambio mínimo `colaborador=user` → `inscripcion__colaborador=user`), preservando intencionalmente la semántica "unión de todas las inscripciones" que **T037/T038 tienen planeado corregir** a "solo la inscripción más reciente" — no se adelantó ese cambio aquí para no pisar el trabajo ya planeado de esas tareas.

**2 gaps preexistentes encontrados por el panel de seguridad, confirmados como NO causados por este diff (verificado con `git show HEAD` byte a byte contra el código antes de T032) — anotados, no corregidos:**
- `MiResultadoEvaluacionSerializer.validate()` solo compara el conjunto de IDs de preguntas respondidas contra las requeridas, no la cuenta ni duplicados — un colaborador podría enviar respuestas duplicadas a una pregunta ya correcta para inflar `correctas` por encima del número real de preguntas distintas contestadas bien, lo cual alimenta directamente el criterio de finalización automática. Esta lógica ya existía exactamente igual (movida, no creada, por T032) en el `create()` que se removió del serializer.
- `MiInscripcionSerializer.curso` sigue siendo escribible por `PATCH /mis-inscripciones/{id}/` — un colaborador podría reasignar el curso de su propia inscripción sin pasar por `InscripcionService`, evadiendo el chequeo de periodo abierto. Preexistente, ya identificado en la revisión de T028/T029, y es exactamente lo que **T039** tiene planeado cerrar.

**Por qué esto importa más allá de esta tarea:** ambos gaps están fuera del trace de AC de T032 (AC1, AC2, AC8, AC9, AC10) y no se corrigieron aquí para no mezclar alcance — el primero no tiene tarea asignada todavía en la tabla (candidato a revisar al llegar a T040, cierre de todos los done-checks); el segundo ya es el objetivo explícito de T039.

## 2026-11-11 — T040 (cierre): se corrige el gap de `MiResultadoEvaluacionSerializer.validate()` anotado desde T032

Contexto: al llegar a T040 (cierre del proyecto) se revisaron explícitamente los gaps diferidos anotados en entradas previas. El segundo (curso escribible) ya lo cerró T039. Este es el primero: `validate()` comparaba `{r['pregunta'].id for r in respuestas}` (un `set`, que deduplica) contra el conjunto de preguntas de la evaluación — así que enviar una respuesta duplicada a una pregunta YA incluida (ej. responder P1 dos veces y P2 una vez, para una evaluación de 2 preguntas) pasaba la validación intacta (`{P1,P2} == {P1,P2}`), pero `MisResultadosViewSet.create` suma `es_correcta` sobre la lista cruda sin deduplicar — `correctas` podía superar `total` (puntaje >100%), inflando directamente el criterio de finalización automática (`FinalizacionService._criterio_cumplido`).

Decisión: se agregó un chequeo de duplicados (`len(lista) != len(set(lista))`) ANTES del chequeo de completitud, rechazando la petición completa con 400 si hay cualquier pregunta respondida más de una vez — nunca deduplicando en silencio.

Por qué: el revisor confirmó que el modelo `Pregunta`/`OpcionPregunta` no tiene ningún tipo de pregunta "multi-select" que legítimamente necesite más de una opción por pregunta — así que rechazar de plano no bloquea ningún caso de uso real, y es más seguro que intentar adivinar cuál de las respuestas duplicadas es la "buena". Revisor también confirmó que no existe el mismo patrón set-vs-lista en ningún otro punto del código que reciba una lista cruda del cliente (los otros dos usos de `set()` similares operan sobre datos ya restringidos por la base de datos, no sobre input directo).

## 2026-11-11 — Revisión de cierre (closing review): 2 bloqueadores + 1 should-fix encontrados y corregidos antes de `ship`

Contexto: la revisión de cierre (ASDD stage 5, panel completo de 3 refutadores — correctness, security, tests — por tier 2) lee toda la rama contra el spec, no las revisiones por tarea. Encontró 2 bloqueadores reales que ninguna revisión por tarea había detectado porque cada una miraba solo su propio diff, nunca el conjunto:

**Bloqueador 1 (seguridad, encontrado por el lente de seguridad, confirmado en vivo contra las fixtures `admin_a`/`admin_b`/`empresa_a`/`empresa_b` del propio repo):** `InscripcionViewSet`, `ProgresoTemaViewSet` y `ResultadoEvaluacionViewSet` (`capacitacion/views.py`) nunca aplicaban `_scope_por_empresa` — el helper de aislamiento multi-empresa que SÍ se agregó, en este mismo diff, a sus 7 hermanos (`CursoViewSet`, `ModuloViewSet`, `TemaViewSet`, `ContenidoBloque*ViewSet`). `_BaseAdminViewSet.permission_classes` solo chequea el rol (`Administrador`), nunca la empresa. Un Administrador de CUALQUIER empresa podía ver, y forzar la finalización + acreditación de, la inscripción de un colaborador de OTRA empresa — vía el mismo endpoint `forzar` que T026/T027 ya habían probado exhaustivamente, pero solo contra su propia empresa.

Por qué nadie lo vio antes: cada tarea (T026/T027 para `forzar`, T032 para la reconexión de `ProgresoTemaViewSet`/`ResultadoEvaluacionViewSet`) revisó su propio diff contra su propio done-check — ninguna comparó su vista contra las 7 hermanas que SÍ llevaban `_scope_por_empresa`, porque esas 7 pertenecían a una iniciativa de scoping distinta (empresa/multi-tenant) que corrió en paralelo dentro del mismo periodo de trabajo pero no está documentada en el spec de `recorrido-formativo-periodos-acreditacion` — es exactamente el tipo de hallazgo que una revisión de cierre existe para atrapar: piezas que individualmente están bien pero que nunca se compararon entre sí.

Decisión: se agregó `_scope_por_empresa(qs, user, 'curso')` / `'inscripcion__curso'` a las tres vistas, idéntico al patrón ya usado en sus 7 hermanas. 5 tests nuevos en `capacitacion/tests/test_empresa_scoping.py::InscripcionScopingTests`.

**Bloqueador 2 (correctness, encontrado por el lente de correctness):** el `InscripcionSerializer` admin (`capacitacion/serializers/progreso.py`) dejaba `completado_at` y `curso` escribibles por PATCH — un Administrador podía fijar `completado_at` directamente, evadiendo `FinalizacionService`/`AcreditacionService` por completo. Esto contradice textualmente la Clarification #3 de la spec: el administrador fuerza finalización "siempre a través del mismo servicio centralizado e idempotente — nunca editando completado_at u otro campo de estado directamente". También permitía divergir `curso` de `periodo.curso` sin ningún chequeo (el mismo riesgo que T039 ya había cerrado para el lado colaborador, pero nunca para el admin).

Decisión: se agregaron `curso` y `completado_at` a `read_only_fields`. 2 tests nuevos en `InscripcionCamposDeSoloLecturaAdminTests` (mismo archivo).

**Should-fix (correctness):** `FinalizacionService._criterio_cumplido` no filtraba `Tema` por `activo=True`, a diferencia de los serializers de progreso del colaborador (que sí lo hacen) — desactivar un tema DESPUÉS de que un colaborador ya completó todo lo visible podía dejar el curso sin poder finalizar nunca, mientras la UI del colaborador seguía mostrando 100%. Corregido agregando `activo=True` al filtro. 1 test nuevo (`test_tema_desactivado_no_bloquea_la_finalizacion`).

Un cuarto hallazgo (posible fallo de idempotencia en `reevaluar()`, doble timestamp) fue reportado por el lente de correctness con baja confianza — el propio revisor atribuyó la falla a corrupción de su base de datos de pruebas por ejecuciones repetidas, no al código. Se descartó: 5 corridas limpias consecutivas de `test_finalizacion_service` sin ninguna falla.

Una nota de seguridad de menor severidad (`question`, no bloqueante): el descubrimiento/auto-inscripción de cursos del lado colaborador (`CursoColaboradorViewSet`, `MisCursosViewSet`, `MisInscripcionesViewSet.create`) no aplica ningún scoping de empresa, a pesar de que `Curso.empresa` existe específicamente para eso del lado admin. Se deja registrada para que el humano decida si está en alcance de algún spec — ninguno de los 20 criterios de aceptación de `recorrido-formativo-periodos-acreditacion` la cubre, y la iniciativa de empresa-scoping es un esfuerzo paralelo no documentado en este spec.

Verificación de las 3 correcciones: ronda 2 del loop de revisión, un verificador fresh-context confirmó cada fix cierra su hallazgo (con sus propias mutaciones, revertidas sin residuo) y no introduce ningún defecto nuevo. Suite completa: 146/146 verde (138 + 8 tests nuevos), `manage.py check` limpio. Veredicto de cierre: APPROVE.

## 2026-11-11 — `status` como única fuente de verdad de autorización; `is_active` queda fijo en `True` por diseño (fuera del ciclo `recorrido-formativo-periodos-acreditacion`)

Contexto: debuggeando un 500 en `/api/auth/sign/` se encontraron dos problemas separados, no relacionados con la feature de periodos:

1. **Bug real en `UserSerializer.update()`** (`user/serializers.py:104`): el chequeo de longitud mínima de password era `len(password) > 6` (rechazaba silenciosamente passwords de exactamente 6 caracteres sin avisar — el endpoint devolvía 200 "editado con éxito" pero nunca llamaba `set_password()`). El usuario lo corrigió directamente a `>= 6`.
2. **`is_active` (de `AbstractUser`) y `status` (de `common.models.Base`) son dos campos de "activo" independientes** que nunca se sincronizan. `is_active` nunca se asigna en ningún punto de este código (confirmado por grep completo del proyecto) — queda siempre en su default `True`. Pero `is_active` sí es chequeado por el núcleo de Django (`ModelBackend.authenticate()`, bloquea login) y por SimpleJWT (`JWTAuthentication.get_user()`, bloquea cada request autenticado) — ambos fuera de este código, no editables sin reescribir librerías de terceros. `user/backends.py` (`RolePermissionBackend`) sí era código propio y sí chequeaba `is_active` en sus 3 métodos de permisos.

Decisión (instrucción explícita del usuario): **no tocar `is_active`** — queda fijo en `True` para siempre, vestigial. **`status` es la única fuente de verdad** de autorización de negocio. Se cambiaron los 3 chequeos de `user/backends.py` (`get_user_permissions`, `get_all_permissions`, `has_perm`) de `not user_obj.is_active` a `user_obj.status == 0`.

Por qué: reescribir el chequeo de `is_active` dentro de Django/SimpleJWT es invasivo y frágil (afecta además el panel de admin si algún día se usa) — mucho mayor riesgo que mantener `is_active` como un campo que simplemente nunca se toca. `status` ya era la fuente de verdad para el login (`CustomTokenObtainPairSerializer` ya lo chequeaba); extenderlo a los permisos cierra la inconsistencia sin tocar código de terceros.

Tests: `user/tests.py::RolePermissionBackendStatusTests` (3 tests) — confirmado con mutación real (revertir el chequeo a `is_active` reproduce el fallo del test antes de la corrección, con un permiso real asignado al rol para que el test no dé falso-verde con un rol vacío). Suite completa: 149/149 verde.

## 2026-11-12 — El progreso visual del colaborador exige "aprobado", no solo "intentado" (fuera del ciclo `recorrido-formativo-periodos-acreditacion`)

Contexto: el usuario preguntó si el backend permite avanzar de módulo, reintentar una evaluación o hacer la evaluación final sin haber aprobado las anteriores. Investigación confirmó que sí — no hay (ni debe haber, por decisión explícita del usuario) ningún bloqueo de secuencia: el colaborador puede navegar y reintentar libremente, y el criterio real de acreditación (`FinalizacionService._criterio_cumplido`) ya exige aprobar, no solo intentar, antes de marcar `completado_at`.

Pero se encontró una divergencia real: `CursoColaboradorSerializer.get_progreso` y `ModuloColaboradorSerializer.get_progreso` (`capacitacion/serializers/colaborador.py`) marcaban una evaluación como "completada" en la barra de progreso visual del colaborador por la mera **existencia** de un `ResultadoEvaluacion` (`.exists()` / `.distinct().count()`), sin mirar si `correctas/total` alcanzaba `evaluacion.puntaje_minimo`. Un colaborador que reprobaba un examen ya veía su progreso avanzar como si lo hubiera aprobado — la UI podía mostrar 100% sin que el curso pudiera acreditarse nunca, rompiendo la auditoría (el usuario: "siento que sería crucial ya que rompe de cierta forma una auditoría").

Decisión: se alineó el progreso visual con el mismo criterio de aprobación que ya usa `FinalizacionService` — se agregó el helper `_hay_intento_aprobado(resultados)` en `capacitacion/serializers/colaborador.py` y se usó en ambos métodos `get_progreso` (curso y módulo), reemplazando los chequeos de mera existencia por "al menos un intento con `correctas/total*100 >= puntaje_minimo`".

Por qué: dos nociones distintas de "completo" (intentado vs. aprobado) convivían en el mismo sistema sin que nada las reconciliara — la UI y la acreditación real podían divergir indefinidamente. Alinear la UI al criterio de acreditación, en vez de relajar la acreditación al criterio de la UI, porque el criterio de acreditación es el que importa para auditoría/cumplimiento.

Tests: `capacitacion/tests/test_progreso_requiere_aprobado.py` (3 tests nuevos, TDD rojo→verde: confirmado rojo por la razón correcta antes del fix — un intento reprobado hacía `completados=1` en vez de `0`). Suite completa: 152/152 verde, sin regresiones.

## 2026-11-12 — Límite de intentos por evaluación, configurable por evaluación, default 3 (fuera del ciclo `recorrido-formativo-periodos-acreditacion`)

Contexto: siguiendo de la pregunta anterior, se confirmó que el backend no limitaba los reintentos de una evaluación — solo el frontend lo bloqueaba visualmente. El usuario pidió hacerlo configurable, con 3 como default actual.

Decisión de diseño (no preguntada explícitamente, pero sin ambigüedad real dado el patrón ya existente): el límite se configura **por evaluación**, no como un setting global — igual que `puntaje_minimo` ya es por evaluación, no global. Se agregó `Evaluacion.intentos_maximos` (`PositiveSmallIntegerField`, default 3, migración `0013_evaluacion_intentos_maximos`), expuesto en `EvaluacionSerializer` (admin) para que cualquier evaluación pueda tener su propio límite.

Aplicación: `EvidenciaService.registrar_resultado_evaluacion` (`capacitacion/services/evidencia_service.py`) ahora cuenta los intentos ya registrados (`ResultadoEvaluacion.objects.filter(inscripcion=inscripcion, evaluacion=evaluacion).count()`) y devuelve un nuevo sentinel `IntentosAgotados()` si `intentos_usados >= evaluacion.intentos_maximos`, en vez de crear el resultado. `MisResultadosViewSet.create` (`capacitacion/views_colaborador.py`) lo traduce a `400` con `detail` explicando que se agotaron los intentos — mismo patrón que `InscripcionNoEncontrada`/`ContenidoAjeno` ya usaban.

Por qué por-evaluación y no global: el modelo ya tiene el precedente exacto (`puntaje_minimo`) para "cada evaluación decide su propia regla"; un setting global sería menos flexible y rompería esa consistencia sin que nadie lo pidiera.

Nota: `test_resultado_evaluacion.py::test_permite_multiples_intentos_por_inscripcion` sigue verde sin cambios — crea `ResultadoEvaluacion` directo vía ORM (sin pasar por `EvidenciaService`), así que el límite nuevo, que vive en la capa de servicio/vista (no una constraint de BD), no lo afecta. Es intencional: la regla de negocio protege el endpoint público, no inserciones internas/administrativas directas.

Tests: `capacitacion/tests/test_intentos_maximos_evaluacion.py` (4 tests nuevos: default=3, límite configurado respetado, 400 end-to-end vía el endpoint real, límite más alto permite más reintentos). Suite completa: 156/156 verde, sin regresiones.

## 2026-11-12 — `ContenidoBloque.embed_url`: campo propio para embeds tipo Canva (fuera del ciclo `recorrido-formativo-periodos-acreditacion`)

Contexto: el usuario preguntó si el LMS puede soportar un "hipervínculo de Canva similar a otro LMS" — resultó ser el embed de Canva ("Compartir → Insertar en un sitio web", pensado para un `<iframe>`), no un link normal.

Decisión de diseño: se agregó `ContenidoBloque.embed_url` (`CharField(max_length=500, blank=True)`, migración `0014_contenidobloque_embed_url`) como campo **separado** de `video_url`/`imagen_url`, en vez de reutilizar `video_url`. Por qué: `video_url` ya tiene semántica propia (el frontend probablemente lo trata como reproductor de video); mezclar un embed de Canva ahí obligaría al frontend a adivinar el tipo de contenido por el dominio de la URL. Un campo propio, combinado con un nuevo tipo en el catálogo `TipoBloqueContenido` (ej. `codigo='embed'`), le da al frontend una señal explícita (`tipo_codigo == 'embed'`) de que debe renderizar un `<iframe>` en vez de `<video>`/`<img>`.

Alcance de lo implementado: solo el campo y su exposición en ambos serializers (`ContenidoBloqueSerializer` admin, `ContenidoBloqueColaboradorSerializer` colaborador). **No** se creó la fila del catálogo `TipoBloqueContenido` con `codigo='embed'` — esos tipos se gestionan como datos en runtime vía `/api/catalogos/tipos-bloque/` (no hay migraciones de datos para catálogos en este proyecto, confirmado por `grep` de `RunPython` en `catalogos/migrations/`), así que es el administrador quien debe crear esa fila desde el panel/API, no algo que viva en código.

Tests: `capacitacion/tests/test_bloque_embed_url.py` (3 tests nuevos: admin crea bloque con `embed_url` vía API, colaborador lo ve al leer el bloque, default vacío). Suite completa: 159/159 verde, sin regresiones.
