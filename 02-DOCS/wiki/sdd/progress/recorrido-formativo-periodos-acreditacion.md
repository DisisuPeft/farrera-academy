# Progress — recorrido-formativo-periodos-acreditacion

Append-only. No se reescriben entradas pasadas; correcciones se agregan como entradas nuevas.

**Nota de proceso:** el usuario pidió no comitear por mi cuenta ("No hagas commits, yo los realizo") — cada entrada deja el estado de archivos tal cual para que el usuario decida cuándo comitear. El riesgo (`rsc risk`) se calcula contra el diff sin comitear (working tree vs. HEAD), no contra un sha de tarea.

## T001 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_periodos` falló con `ImportError: cannot import name 'Periodo'` (razón correcta: el modelo no existía)
- green: mismo comando, 3 pruebas iniciales en verde tras crear el modelo + migración
- triangulación (tras panel de revisión): se agregaron 2 pruebas más — `ProtectedError` al borrar un `Curso` con `Periodo`s, y `estado=CERRADO` persiste correctamente
- files: `capacitacion/models/curso.py`, `capacitacion/models/__init__.py`, `capacitacion/migrations/0008_periodo.py`, `capacitacion/tests/test_periodos.py`
- risk: tier 2 (`migrations`) — confirmado con `npx @ericrisco/rsc risk`, panel de 3 refutadores
- review: 3 reportados (correctness: 0, security: 0, tests: 1 should-fix + 2 question) → 1 should-fix confirmado (falta prueba de `PROTECT` en `curso`) → corregido en esta misma tarea; 2 question de baja severidad (CERRADO nunca ejercitado, `related_name` nunca ejercitado) aceptadas como cobertura que tareas posteriores (T003+) ejercitarán naturalmente, no bloquean
- controls: tests ✅ (5/5 verde) · build ✅ (`migrate` aplica limpio, `system check` sin issues) · security: sin hallazgos del refutador (no hay endpoint todavía) · traceability ✅ (AC1, AC2, AC17 fundacional)
- decision: sin bloqueos — fix aplicado y registrado aquí, no requirió decision queue

## T002 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_periodos.InscripcionPeriodoFieldTests` falló con `TypeError: Inscripcion() got unexpected keyword arguments: 'periodo'` (razón correcta)
- green: agregado `Inscripcion.periodo` (PROTECT, NOT NULL), `curso` conservado, `unique_together` → `(colaborador, periodo)`; migración `0009_inscripcion_periodo`
- **paso operativo no planeado, autorizado por el usuario:** la migración no podía generarse porque había 50 filas de `Inscripcion` (seed/fake) en la BD de dev. Pregunté y el usuario autorizó borrarlas. Se borraron vía SQL crudo (incluyendo anular `competencias_competenciacolaborador.origen_id` primero, por el FK) — confirmado por el panel de seguridad que esto no cambia ninguna decisión de autorización computada, solo deja `origen_curso_titulo=None` en filas sintéticas ya borradas.
- triangulación (tras panel): se agregó prueba de que dos colaboradores distintos sí pueden inscribirse al mismo periodo (el mutante `unique_together=[('periodo',)]` sobrevivía sin ella)
- files: `capacitacion/models/progreso.py`, `capacitacion/migrations/0009_inscripcion_periodo.py`, `capacitacion/tests/test_periodos.py`
- risk: tier 2 (`migrations`) — panel de 3 refutadores
- review: correctness 1 should-fix (comentario sobreafirmaba una invariante que T004 todavía no construye — corregido a describir el estado real) → fixed; security 0 blocker/should-fix, pero señaló que `MisInscripcionesViewSet`/`InscripcionViewSet` van a devolver 500 hasta T032 (ventana transicional ya prevista por la secuenciación del plan, no un hallazgo de seguridad — aceptada, no se corrige fuera de orden); tests 1 should-fix confirmado y corregido (ver arriba)
- controls: tests ✅ (49/49 del suite completo de `capacitacion`, sin regresiones) · build ✅ (migración aplica limpio) · security: sin bloqueos · traceability ✅ (AC2, AC3, AC4, AC11)
- decision: la rotura transicional de los endpoints de inscripción hasta T032 queda aceptada y registrada aquí, no en la decision queue (no es `blocking`: no detiene tareas independientes ni requiere aprobación humana aparte — ya estaba prevista en la secuenciación del plan)
