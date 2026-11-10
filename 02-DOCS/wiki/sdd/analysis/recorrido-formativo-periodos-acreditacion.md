---
type: analysis
title: Analysis — Periodos, inscripción como unidad de participación y acreditación centralizada
description: Cruce de consistencia entre constitución, spec, plan y tareas antes de implementar (re-ejecutado tras resolver los 4 hallazgos de la primera pasada).
tags: [sdd, analysis]
timestamp: 2026-11-10T01:00:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
---

# Analysis — Periodos, inscripción, acreditación centralizada (re-ejecutado)

> Constitución: [../constitution.md](../constitution.md) v1.0.0 · Spec: [../specs/recorrido-formativo-periodos-acreditacion.md](../specs/recorrido-formativo-periodos-acreditacion.md) (clarified, 20 acceptance criteria) · Plan+Tasks: [../plans/recorrido-formativo-periodos-acreditacion.md](../plans/recorrido-formativo-periodos-acreditacion.md) (41 tareas)

## GATE: PASS — 0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW

Los 4 hallazgos de la primera pasada quedaron resueltos:

1. **HIGH (drift)** — las 3 correcciones de comportamiento quedaron horneadas en la spec como 3 acceptance criteria nuevos (AC18-AC20) y un bloque `## Clarifications` que cita el origen de la decisión.
2. **MEDIUM (AC10 sin campo nombrado)** — plan §4 Entidades ahora nombra `ResultadoEvaluacion.correctas`/`.total` explícitamente y ajusta el alcance esperado de T028.
3. **MEDIUM (Interfaces faltantes)** — T027 y T032 ya llevan su bloque Interfaces con firmas exactas.
4. **MEDIUM (paquete de tests de `competencias`)** — nueva tarea T041 convierte `competencias/tests.py` en paquete antes de que T024/T033 lo usen; sus `Depends-on` se actualizaron.

## Mapa de cobertura (spec → plan → tareas)

| REQ-ID | Requisito de la spec (resumen) | Tarea(s) | Estado |
| --- | --- | --- | --- |
| AC1 | Rechazar inscripción sin periodo abierto | T003, T004 | covered |
| AC2 | Rechazar inscripción duplicada al mismo periodo | T003, T004 | covered |
| AC3 | Repetir curso en periodo distinto no altera la anterior | T007, T008 | covered |
| AC4 | Progreso de dos inscripciones no se mezcla | T009-T011, T013, T016, T017 | covered |
| AC5 | Finalización + acreditación en la misma operación | T019, T025 | covered |
| AC6 | Finalización no se repite tras guardado incidental | T022, T023 | covered |
| AC7 | Cambiar `CompetenciaCurso` no reacredita retroactivamente | T024, T025, T041 | covered |
| AC8 | Progreso de tema ajeno al curso rechazado | T012, T013 | covered |
| AC9 | Respuesta con opción ajena al bloque rechazada | T014, T015 | covered |
| AC10 | Colaborador no fija finalización/calificación/nivel (campo nombrado: `ResultadoEvaluacion.correctas`/`.total`) | T028, T029 | covered |
| AC11 | Concurrencia real en creación de inscripción | T005, T006 | covered |
| AC12 | Finalización automática exacta con evaluaciones | T018, T019 | covered |
| AC13 | Curso sin evaluaciones: progreso completo basta | T020, T021 | covered |
| AC14 | Progreso completo sin evaluación aprobada → no finaliza | T018, T019 | covered |
| AC15 | Finalización manual excepcional vía el mismo servicio | T026, T027 | covered |
| AC16 | Cerrar periodo no fuerza desenlace de inscripciones abiertas | T030, T031 | covered |
| AC17 | Periodo cerrado rechaza nueva inscripción | T003, T004, T030, T031 | covered |
| AC18 | Perfil de competencias muestra inscripción más reciente por curso | T033, T034, T041 | covered |
| AC19 | Auto-inscripción por ruta usa el periodo abierto más reciente, falla si no hay ninguno | T035, T036 | covered |
| AC20 | `get_inscrito`/`get_progreso` sobre la inscripción más reciente, no la unión | T037, T038 | covered |

20/20 acceptance criteria cubiertas en ambos sentidos. T041 (conversión del paquete de tests) y las tareas de cierre (T039 invariante `curso`/`periodo.curso`, T040 cierre general) no requieren un AC propio — son higiene técnica interna ya justificada en plan §7 (riesgos), no drift: no introducen comportamiento observable nuevo.

## Hallazgos

Ninguno. Las seis comprobaciones (cumplimiento constitucional, cobertura, deriva, contradicción, duplicación, ambigüedad/carrier completeness) no encontraron nada pendiente en esta segunda pasada.

## Resultado

```json result-envelope
{
  "status": "complete",
  "executive_summary": "Segunda pasada tras resolver los 4 hallazgos de la primera: GATE: PASS. 20/20 acceptance criteria cubiertas en ambos sentidos, sin deriva, sin ambigüedad de carrier, sin contradicciones.",
  "artifact": "02-DOCS/wiki/sdd/analysis/recorrido-formativo-periodos-acreditacion.md",
  "next_recommended": "implement",
  "risk": "low",
  "skill_resolution": {
    "used": ["analyze"],
    "missing": [],
    "fallback": [],
    "compact_rules": ["Report only, resolve nothing.", "Re-run after fixes before declaring PASS."]
  },
  "evidence": ["20/20 ACs covered both ways", "0 findings remaining", "spec/plan/tasks re-read after edits"]
}
```
