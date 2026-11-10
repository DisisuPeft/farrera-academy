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
