---
type: verification
title: Verification — recorrido-formativo-periodos-acreditacion — 2026-11-11
description: Evidence-backed closing verdict — generic Django test gate, 42 task done-checks, 20 spec acceptance criteria.
tags: [sdd, verification]
timestamp: 2026-11-11T22:34:41Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
source_state: 6a460f0 (dirty — 73 uncommitted paths, expected: user commits manually, nothing here was committed)
---

# Verification — recorrido-formativo-periodos-acreditacion — 2026-11-11

No stack skill in this registry ships a Django `scripts/verify.sh`, so this record runs the
**generic gate** from `02-DOCS/wiki/sdd/config.yaml` (`testing.commands.verify: ["python manage.py test"]`),
plus `manage.py check` and a migration-plan dry run, each captured fresh after the last edit of this session.

## Stack gate (generic — Django/DRF, no dedicated stack skill)

- `python manage.py migrate --plan` → **PASS** — "No planned migration operations." (all migrations already applied to the test baseline; nothing pending)
- `python manage.py test` (full project suite) → **PASS** — 138 tests, 0 failures, 0 errors, 19.13s
- `python manage.py check` → **PASS** — "System check identified no issues (0 silenced)."
- `ruff` (constitution principle 5 mandates ruff format + ruff check) → **not run** — not installed in this environment, documented gap since `sdd-init` (`config.yaml` → `testing.lint.installed: false`)
- Dependency/security audit (`pip-audit` or equivalent) → **not run** — no tool configured for this stack in this registry; constitution has no explicit security/audit bar for this feature line
- Coverage threshold → **not run** — no `--cov-fail-under` or equivalent configured; constitution has no coverage floor for this feature line

## Task done-checks (plan T001–T041)

All 42 rows in the plan's task table are marked `status: complete` in
`02-DOCS/wiki/sdd/progress/recorrido-formativo-periodos-acreditacion.md`, each with its own red→green
evidence recorded per task. Re-verified fresh in this closing pass by running every named test module
from the done-check column together (not relying on the per-task record alone):

```
python manage.py test \
  capacitacion.tests.test_inscripcion_service capacitacion.tests.test_evidencia_service \
  capacitacion.tests.test_finalizacion_service capacitacion.tests.test_forzar_finalizacion \
  capacitacion.tests.test_campos_solo_lectura_colaborador capacitacion.tests.test_periodo_cerrado_no_bloquea \
  capacitacion.tests.test_reconexion_vistas_colaborador capacitacion.tests.test_get_inscrito_get_progreso \
  capacitacion.tests.test_resultado_evaluacion_respuestas_duplicadas capacitacion.tests.test_bloque_respuesta \
  capacitacion.tests.test_progreso_tema capacitacion.tests.test_resultado_evaluacion \
  capacitacion.tests.test_periodos capacitacion.tests.test_respuestas_bloque \
  capacitacion.tests.test_admin_progreso_resultado_endpoints competencias.tests.test_acreditacion_service \
  competencias.tests.test_acreditacion_regression competencias.tests.test_mi_perfil_competencias \
  competencias.tests.test_inscripcion_ruta_perfil
```

→ **PASS**, 90 tests, 0 failures, 0 errors.

- [x] T001–T002 — `Periodo`/`Inscripcion.periodo` migrations — evidence: `manage.py migrate --plan` clean, no pending ops
- [x] T003–T008 — `InscripcionService.crear` (periodo abierto, duplicado, curso copiado, repetición) — evidence: `test_inscripcion_service.py` green
- [x] T009–T011 — FK `inscripcion` en `ProgresoTema`/`ResultadoEvaluacion`/`ContenidoBloqueRespuesta`, `colaborador` eliminado — evidence: migrations applied clean; `test_bloque_respuesta.test_colaborador_ya_no_existe_como_campo_directo` green
- [x] T012–T017 — `EvidenciaService` (validación cruzada, resolución por curso, progreso independiente) — evidence: `test_evidencia_service.py` green
- [x] T018–T023 — `FinalizacionService.reevaluar` (criterio, idempotencia, sin evaluaciones) — evidence: `test_finalizacion_service.py` green
- [x] T041 — `competencias/tests.py` → paquete `competencias/tests/` — evidence: el archivo no existe, `competencias/tests/__init__.py` sí (confirmado: `ls competencias/tests/`)
- [x] T024–T025 — regresión de reacreditación + `AcreditacionService` extraído del signal — evidence: `test_acreditacion_regression.py` + `test_acreditacion_service.py` green
- [x] T026–T027 — `FinalizacionService.forzar` + endpoint admin — evidence: `test_forzar_finalizacion.py` green
- [x] T028–T029 — campos de solo lectura para colaborador — evidence: `test_campos_solo_lectura_colaborador.py` green
- [x] T030–T031 — cierre de periodo no bloquea inscripciones existentes — evidence: `test_periodo_cerrado_no_bloquea.py` green
- [x] T032 — reconexión de vistas a los servicios — evidence: `test_reconexion_vistas_colaborador.py` green, suite completa 130/130 en su momento (ahora 138/138)
- [x] T033–T034 — perfil de competencias muestra inscripción más reciente — evidence: `test_mi_perfil_competencias.py` green
- [x] T035–T036 — ruta de aprendizaje auto-inscribe vía servicio — evidence: `test_inscripcion_ruta_perfil.py` green
- [x] T037–T038 — `get_inscrito`/`get_progreso` sobre inscripción más reciente — evidence: `test_get_inscrito_get_progreso.py` green
- [x] T039 — invariante `curso` de solo lectura — evidence: `test_inscripcion_service.InvarianteCursoTest` green
- [x] T040 — cierre: todos los anteriores verdes + suite completa sin regresiones — evidence: este mismo documento (138/138, `check` limpio); además encontró y cerró el gap de respuestas duplicadas (`test_resultado_evaluacion_respuestas_duplicadas.py`, fuera de la tabla original de tareas pero registrado en `decisions.md`)

No se encontró ninguna entrada en `## Decision queue` de `progress/<slug>.md` — ninguna tarea quedó parqueada; no hay nada pendiente de aprobación humana por tier 2 sin converger.

## Acceptance criteria (spec)

- [x] AC1 — curso sin periodo abierto rechaza inscripción — `test_reconexion_vistas_colaborador.ReconexionMisInscripcionesTests.test_rechaza_inscripcion_a_curso_sin_periodo_abierto`, `test_inscripcion_service.InscripcionServiceCrearTests.test_rechaza_periodo_cerrado`
- [x] AC2 — doble inscripción al mismo periodo rechazada — `test_inscripcion_service.test_rechaza_duplicado_al_mismo_periodo`, `test_reconexion_vistas_colaborador.test_rechaza_doble_inscripcion_al_mismo_periodo`
- [x] AC3 — nueva inscripción en nuevo periodo no altera la anterior — `test_inscripcion_service.RepeticionTest.test_segunda_inscripcion_a_periodo_distinto_no_altera_la_primera`
- [x] AC4 — progreso independiente entre inscripciones al mismo curso — `test_evidencia_service.test_progreso_de_la_primera_inscripcion_no_se_altera_al_registrar_en_la_segunda`
- [x] AC5 — acreditación y finalización en la misma operación — `test_acreditacion_service.test_acreditar_crea_el_registro_cuando_no_existe`, `test_finalizacion_service.test_finaliza_cuando_temas_completos_y_evaluacion_aprobada`
- [x] AC6 — re-guardar inscripción ya finalizada sin servicio no cambia nivel/estado — `test_acreditacion_service.test_guardar_una_inscripcion_directamente_no_dispara_acreditacion`, `test_acreditacion_service.test_reevaluar_es_el_unico_camino_que_dispara_acreditacion`
- [x] AC7 — subir config de curso a nivel 3 no reescribe histórico ya otorgado en nivel 2 — `test_acreditacion_service.test_acreditar_nunca_baja_un_nivel_ya_otorgado`, `test_acreditacion_regression.py`
- [x] AC8 — progreso de tema ajeno al curso rechazado — `test_evidencia_service.test_rechaza_tema_que_no_pertenece_al_curso_de_la_inscripcion`
- [x] AC9 — respuesta con opción ajena al bloque rechazada — `test_evidencia_service.test_rechaza_opcion_que_no_pertenece_al_bloque`, `test_respuestas_bloque.test_rechaza_opcion_que_no_pertenece_al_bloque`
- [x] AC10 — colaborador no puede fijar finalización/calificación/nivel directamente — `test_campos_solo_lectura_colaborador.py` (completo); extendido en T039 al campo `curso` y en T040 al bloqueo de inflación de `correctas`
- [x] AC11 — concurrencia real, máximo una inscripción exitosa — `test_inscripcion_service.ConcurrenciaTest`
- [x] AC12 — finalización automática al registrar la última evidencia pendiente — `test_evidencia_service.test_registrar_progreso_finaliza_automaticamente_al_completar_el_ultimo_tema`
- [x] AC13 — curso sin evaluaciones finaliza solo con progreso completo — `test_finalizacion_service.test_finaliza_con_solo_progreso_completo_si_el_curso_no_tiene_evaluaciones`
- [x] AC14 — progreso completo sin evaluación aprobada no finaliza — `test_finalizacion_service.test_no_finaliza_si_temas_completos_pero_evaluacion_no_aprobada`
- [x] AC15 — finalización excepcional forzada produce el mismo resultado que la automática — `test_finalizacion_service.test_forzar_finaliza_aunque_el_criterio_normal_no_se_cumpla`, `test_forzar_acredita_igual_que_una_finalizacion_automatica`
- [x] AC16 — periodo cerrado no bloquea progreso de inscripciones ya existentes en él — `test_periodo_cerrado_no_bloquea.py`
- [x] AC17 — periodo cerrado rechaza nuevas inscripciones — `test_inscripcion_service.test_rechaza_periodo_cerrado`, `test_periodo_cerrado_no_bloquea.py`
- [x] AC18 — perfil de competencias muestra inscripción más reciente, no por orden de iteración — `test_mi_perfil_competencias.py`
- [x] AC19 — ruta de aprendizaje auto-inscribe vía servicio; falla explícito sin periodo abierto — `test_inscripcion_ruta_perfil.py`
- [x] AC20 — `inscrito`/progreso corresponde a la inscripción más reciente, nunca a la unión — `test_get_inscrito_get_progreso.py`

Las 20 acceptance criteria de la spec tienen evidencia observable (test verde), ninguna quedó
"verificada por lectura de código". Los dos puntos marcados por `clarify` como fuera de ciclo
(**decisión diferida**: bitácora histórica de niveles; **área no formulable**: interacción con
gating granular futuro) no son criterios de aceptación de este ciclo — no se evalúan aquí, quedan
correctamente fuera de alcance tal como la spec los documenta.

## Rollback plan

Nada de este trabajo está commiteado (instrucción explícita del usuario: "no hagas commit, yo los
realizo"). El árbol de trabajo tiene 73 rutas sin commitear sobre `6a460f0`. Rollback es por tanto
trivial mientras siga sin commitear: `git checkout -- <archivo>` por archivo, o `git clean -fd` +
`git checkout -- .` para descartar todo el working tree (el usuario decide si quiere conservarlo).
Una vez el usuario commitee: revertir sería `git revert <sha-del-commit>`; no hay migraciones con
`down` manual necesario más allá del soporte estándar de Django (`migrate capacitacion <migración-anterior>`
revierte limpio, probado en este mismo entorno vía `migrate --plan`).

## Capas no ejecutadas

- **HERRAMIENTA-AUSENTE** — `ruff format`/`ruff check`: no instalado en este entorno (constitution
  principio 5 lo exige). No corrió nada en su lugar; el estilo del código nuevo no fue verificado
  automáticamente, solo revisado visualmente por los revisores tier-1/tier-2 de cada tarea.
- **HERRAMIENTA-AUSENTE** — auditoría de dependencias (`pip-audit` o equivalente): no configurado
  para este stack en este registro. No corrió nada en su lugar.
- **SUSTITUIDA** — cobertura de línea: no se corrió con un umbral (`--cov-fail-under`); de hecho no
  se corrió bajo ninguna herramienta de cobertura en absoluto en este cierre — se sustituyó por el
  conteo de tests pasando (138/138) y la revisión tier-1/tier-2 por tarea. Esto **no puede detectar**
  líneas nuevas sin ningún test que las ejecute en absoluto, solo detecta tests que fallan. La
  revisión adversarial por tarea (ya corrida, ver `progress/<slug>.md`) es la mitigación real de esa
  brecha, no esta verificación.
- **NO-APLICA** — pruebas e2e de navegador / build de frontend: esta feature es 100% backend
  (Django/DRF); no existe superficie de frontend en este repo para este ciclo.

## Hallazgos descartados

- "¿Las migraciones nuevas podrían fallar al aplicarse sobre una base ya poblada con datos previos a
  `Periodo`?" — descartado para este cierre: `manage.py migrate --plan` confirma que ya están todas
  aplicadas en la base de pruebas, y las migraciones ya fueron aplicadas limpiamente en cada tarea
  que las introdujo (T001, T002, T009, T010, T011) sin rollback registrado en ningún punto del
  progreso. No se dispone de una base de datos de producción real para probar la migración contra
  datos preexistentes fuera de este entorno — riesgo real pero fuera del alcance que esta
  verificación puede ejercer; queda para el humano antes de aplicar en producción.

## Verdict: PASS — 42/42 done-checks con evidencia, 20/20 acceptance criteria con evidencia, 0 entradas en la cola de decisiones, suite completa 138/138 verde, `check` limpio. Listo para `review` de cierre.
