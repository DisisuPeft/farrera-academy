---
type: analysis
title: Analysis — Periodos, inscripción como unidad de participación y acreditación centralizada
description: Cruce de consistencia entre constitución, spec, plan y tareas antes de implementar.
tags: [sdd, analysis]
timestamp: 2026-11-10T00:00:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
---

# Analysis — Periodos, inscripción, acreditación centralizada

> Constitución: [../constitution.md](../constitution.md) v1.0.0 · Spec: [../specs/recorrido-formativo-periodos-acreditacion.md](../specs/recorrido-formativo-periodos-acreditacion.md) (clarified) · Plan+Tasks: [../plans/recorrido-formativo-periodos-acreditacion.md](../plans/recorrido-formativo-periodos-acreditacion.md)

## GATE: BLOCKED — 1 HIGH, 3 MEDIUM, 0 CRITICAL, 0 LOW

Ningún principio de la constitución se viola. El bloqueo es por **1 hallazgo HIGH** (deriva de alcance real: tres correcciones de comportamiento decididas durante la revisión del plan nunca se horneraron de vuelta en la spec) y 3 MEDIUM que conviene resolver antes de `implement` para no dejarle ambigüedad a un implementador con contexto aislado.

## Mapa de cobertura (spec → plan → tareas)

| REQ-ID | Requisito de la spec (resumen) | Sección del plan | Tarea(s) | Estado |
| --- | --- | --- | --- | --- |
| AC1 | Rechazar inscripción sin periodo abierto | §3 InscripcionService | T003, T004 | covered |
| AC2 | Rechazar inscripción duplicada al mismo periodo | §3 InscripcionService | T003, T004 | covered |
| AC3 | Repetir curso en periodo distinto no altera la anterior | §6 paso 3 | T007, T008 | covered |
| AC4 | Progreso de dos inscripciones no se mezcla | §4 Entidades | T009-T011, T013, T016, T017 | covered |
| AC5 | Finalización + acreditación en la misma operación | §2-3 FinalizacionService | T019, T025 | covered |
| AC6 | Finalización no se repite tras guardado incidental | §3 FinalizacionService.reevaluar | T022, T023 | covered |
| AC7 | Cambiar `CompetenciaCurso` no reacredita retroactivamente | §7 (regresión de la auditoría) | T024, T025 | covered |
| AC8 | Progreso de tema ajeno al curso rechazado | §3 EvidenciaService | T012, T013 | covered |
| AC9 | Respuesta con opción ajena al bloque rechazada | §3 EvidenciaService | T014, T015 | covered |
| AC10 | Colaborador no fija finalización/calificación/nivel | §0 Global Constraints | T028, T029 | **AMBIGUOUS** (ver hallazgo #2) |
| AC11 | Concurrencia real en creación de inscripción | §3 invariante `select_for_update` | T005, T006 | covered |
| AC12 | Finalización automática exacta con evaluaciones | §3 FinalizacionService.reevaluar | T018, T019 | covered |
| AC13 | Curso sin evaluaciones: progreso completo basta | §3 FinalizacionService.reevaluar | T020, T021 | covered |
| AC14 | Progreso completo sin evaluación aprobada → no finaliza | §3 FinalizacionService.reevaluar | T018, T019 | covered |
| AC15 | Finalización manual excepcional vía el mismo servicio | §3 FinalizacionService.forzar | T026, T027 | covered |
| AC16 | Cerrar periodo no fuerza desenlace de inscripciones abiertas | §6 paso final | T030, T031 | covered |
| AC17 | Periodo cerrado rechaza nueva inscripción | §3 InscripcionService | T003, T004, T030, T031 | covered |
| — | `MiPerfilCompetenciasView` muestra inscripción más reciente | §4 remediación (no es un AC de la spec) | T033, T034 | **DRIFT** (ver hallazgo #1) |
| — | `MiInscripcionRutaPerfil` usa periodo abierto más reciente | §4 remediación (no es un AC de la spec) | T035, T036 | **DRIFT** (ver hallazgo #1) |
| — | `get_inscrito`/`get_progreso` sobre inscripción más reciente | §4 remediación (no es un AC de la spec) | T037, T038 | **DRIFT** (ver hallazgo #1) |

Las 17 acceptance criteria de la spec están cubiertas en ambos sentidos (ninguna sin tarea, ninguna tarea de las trazadas a un AC sin criterio detrás). Las tres filas DRIFT son exactamente las que la tabla muestra: trabajo real, decidido explícitamente con el usuario, pero que vive solo en el plan y en `decisions.md` — nunca entró a la spec como requisito.

## Hallazgos

| # | Severidad | Tipo | Artefacto A | Artefacto B | Conflicto | Resolver en |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **HIGH** | DRIFT | Plan §4 (tabla de remediación) y Tasks T033-T038 | Spec — Goals / Acceptance criteria | Las tres correcciones de comportamiento (`MiPerfilCompetenciasView`, `MiInscripcionRutaPerfil`, `get_inscrito`/`get_progreso`) cambian comportamiento observable real de la API — exactamente el tipo de cosa que la spec existe para fijar como contrato — pero se decidieron en la conversación de revisión del plan y solo quedaron registradas en `decisions.md` y en el plan. La spec, que es la fuente de verdad de requisitos, no las menciona en ningún lado. | `specify`/`clarify` — hornear estas 3 decisiones como Acceptance Criteria explícitos (o como entradas de "What it must respect"), citando `decisions.md` como su origen, antes de que `implement` las construya sin respaldo en la spec. |
| 2 | MEDIUM | AMBIGUOUS | Spec — AC10 ("calificación final") | Plan §4 Entidades / Tasks T028-T029 | AC10 prohíbe que el colaborador fije "la calificación final", pero ni la spec ni el plan nombran qué campo concreto es eso. `ResultadoEvaluacion.correctas/total` son server-computed por el código ya existente (confirmado en sesiones previas), pero el plan nunca lo dice explícitamente ni T028/T029 lo prueban por su nombre — solo prueban `completado_at` y nivel de forma genérica. | `plan` — nombrar el campo exacto en §4 Entidades, o confirmar explícitamente que AC10 en esa cláusula ya está satisfecha por código existente y no requiere trabajo nuevo, ajustando el done-check de T028 para probarlo por su nombre real. |
| 3 | MEDIUM | AMBIGUOUS (carrier completeness) | Tasks T027, T032 | Plan §3 Interfaces & contracts | `FinalizacionService.forzar` y la reconexión de vistas (T032) consumen contratos definidos en tareas anteriores (T019, T025, T004, T013), pero T027 y T032 no llevan su propio bloque **Interfaces** con las firmas exactas que un implementador de contexto aislado necesitaría — solo lo tienen T004, T013, T019, T025. | `tasks` — agregar bloques Interfaces (`Consumes`/`Produces`) a T027 y T032 antes de que `implement` los despache a un subagente que no ve el resto del plan. |
| 4 | MEDIUM | CONTRADICTION (técnica, no de producto) | Tasks T024, T033 (done-check: `competencias.tests.test_acreditacion_regression`, `competencias.tests.test_mi_perfil_competencias`) | Estado real del repo: `competencias/tests.py` es un único módulo, no un paquete | Constitution §3.13 exige que las pruebas vivan en `<app>/tests/` como paquete, siguiendo el patrón de `capacitacion/tests/` — pero `competencias` hoy es un archivo plano (`competencias/tests.py`), y Python no permite que coexistan `competencias/tests.py` y `competencias/tests/` con el mismo nombre. Los done-checks de T024/T033 asumen rutas de paquete que no existen todavía. | `tasks` — agregar una tarea explícita (antes de T024) que convierta `competencias/tests.py` en el paquete `competencias/tests/`, migrando las pruebas existentes, o ajustar los done-checks de T024/T033 para apuntar al módulo plano si se decide no migrarlo en este ciclo. |

## Routing recomendado

- **`clarify`** (hallazgo #1, HIGH) — es el único bloqueante real. Hornear las 3 correcciones de comportamiento como Acceptance Criteria/What-it-must-respect explícitos en la spec, citando `decisions.md`. Sin esto, `implement` construiría comportamiento de usuario real sin que exista un contrato de spec que lo respalde ni que `verify` pueda citar.
- **`plan`** (hallazgo #2) — una línea: nombrar el campo concreto detrás de "calificación final" en §4 Entidades, o declarar explícitamente que ya está cubierto por código existente.
- **`tasks`** (hallazgos #3 y #4) — agregar los 2 bloques Interfaces faltantes, y una tarea (o ajuste de ruta) para el paquete de tests de `competencias`.

Ninguno de los tres MEDIUM necesita volver a `specify`/`plan` desde cero — son ediciones puntuales. El HIGH tampoco requiere repetir todo `clarify`: es una sola ronda corta sobre un punto ya decidido, solo falta transcribirlo.

## Resultado

```json result-envelope
{
  "status": "blocked",
  "executive_summary": "Constitución respetada en su totalidad. 1 hallazgo HIGH (3 correcciones de comportamiento decididas en plan/decisions.md nunca entraron a la spec) y 3 MEDIUM (campo de AC10 sin nombrar, 2 tareas sin bloque Interfaces, estructura de tests de competencias incompatible con los done-checks). Las 17 acceptance criteria de la spec están cubiertas en ambos sentidos.",
  "artifact": "02-DOCS/wiki/sdd/analysis/recorrido-formativo-periodos-acreditacion.md",
  "next_recommended": "clarify",
  "risk": "medium",
  "skill_resolution": {
    "used": ["analyze"],
    "missing": [],
    "fallback": [],
    "compact_rules": ["Report only, resolve nothing.", "Drift is drift even when well-reasoned and user-approved elsewhere."]
  },
  "evidence": ["coverage map built, 17/17 ACs covered", "3 drift items identified against spec Goals/Acceptance", "2 missing Interfaces blocks named", "test package layout contradiction named with exact file"]
}
```
