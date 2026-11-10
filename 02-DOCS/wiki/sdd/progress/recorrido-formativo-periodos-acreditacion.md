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

## T003/T004 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_inscripcion_service` falló con `ModuleNotFoundError: No module named 'capacitacion.services'` (razón correcta: el servicio no existía)
- green: creado `capacitacion/services/inscripcion_service.py` con `InscripcionService.crear(colaborador, periodo)`; 2 pruebas iniciales en verde
- triangulación: se agregó `test_curso_queda_copiado_del_periodo` (confirma `curso` auto-copiado de `periodo.curso` y `completado_at is None`)
- files: `capacitacion/services/__init__.py`, `capacitacion/services/inscripcion_service.py`, `capacitacion/tests/test_inscripcion_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — 1 revisor fresh-context (`refuter-correctness`)
- review: 1 should-fix confirmado — `except IntegrityError` sin acotar podía enmascarar una violación de FK real como `InscripcionDuplicada`; corregido re-verificando que exista la fila (colaborador, periodo) antes de devolver ese resultado, re-lanzando en cualquier otro caso
- **hallazgo real durante la corrección (no previsto por el revisor):** aplicar la verificación justo después de capturar `IntegrityError`, sin aislar el `create()` en su propio `transaction.atomic()` anidado (savepoint), rompió con `TransactionManagementError` al ejecutar la consulta de verificación — reproducido corriendo la suite real contra MySQL, no inferido. Corregido envolviendo el `create()` en un `atomic()` anidado; ver `decisions.md` para el detalle y por qué aplica a los servicios futuros (`EvidenciaService`, `FinalizacionService`)
- controls: tests ✅ (71/71 del proyecto completo, sin regresiones) · build ✅ (`system check` sin issues) · security: sin hallazgos del refutador · traceability ✅ (AC1, AC2, AC17)
- decision: should-fix corregido y registrado en `decisions.md` (incluye el hallazgo operativo de la corrección) — sin bloqueos

## T005/T006 — 2026-11-10
- status: complete
- red: no hubo rojo real — `ConcurrenciaTest` (dos hilos reales, `TransactionTestCase`) pasó verde desde el primer intento contra la implementación ya existente de T004 (`select_for_update` + manejo de `IntegrityError` ya cubrían la invariante)
- verificación de que la prueba no era vacía: mutante 1 (quitar `select_for_update()`) — sigue verde 8/8 (el índice único de MySQL ya serializa el `INSERT`); confirma que `select_for_update` protege una invariante distinta (lectura consistente de `periodo.estado`), no esta
- green: T006 fue un no-op de código (la implementación de T004 ya satisface la invariante de concurrencia probada por T005)
- files: `capacitacion/tests/test_inscripcion_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — 1 revisor fresh-context (`refuter-tests`)
- review: 1 should-fix confirmado por el revisor con un segundo mutante (quitar el `try/except IntegrityError` completo) que el propio builder no había probado — un hilo que lanza una excepción no capturada no agrega resultado a la lista compartida, reduciendo la muestra de 2 a 1 y dejando pasar `len(exitosos)==1` por la razón equivocada
- triangulación (fix): se agregó `self.assertEqual(len(resultados), 2, ...)` antes de contar los exitosos; verificado empíricamente que con esta aserción el mutante 2 ahora falla 3/3 corridas y la implementación real sigue pasando
- controls: tests ✅ (72/72 del proyecto completo, sin regresiones) · build ✅ · security: sin hallazgos del refutador · traceability ✅ (AC11)
- decision: should-fix corregido y verificado con mutación real; registrado en `decisions.md` — sin bloqueos

## T009 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_progreso_tema` falló con `TypeError: ProgresoTema() got unexpected keyword arguments: 'inscripcion'` (razón correcta)
- **paso operativo no planeado, autorizado por el usuario:** 179 filas de seed de `ProgresoTema` (sin FK que las referencie) bloqueaban la migración NOT NULL; mismo patrón que T002. Intento por shell bloqueado por el clasificador de modo automático; usuario autorizó el borrado explícitamente vía pregunta
- **hallazgo operativo durante la migración:** el orden de operaciones autogenerado por `makemigrations` (`AlterUniqueTogether` antes de `AddField`) rompía con `FieldDoesNotExist`; corregido reordenando a `AddField → AlterUniqueTogether → RemoveField`; ver `decisions.md` para el detalle y por qué aplica a futuras migraciones similares (T010, T011)
- green: `ProgresoTema` gana `inscripcion` (PROTECT, NOT NULL), pierde `colaborador`, `unique_together` → `(inscripcion, tema)`; migración `0010_alter_progresotema_unique_together_and_more`; 5 pruebas en verde
- files: `capacitacion/models/progreso.py`, `capacitacion/migrations/0010_alter_progresotema_unique_together_and_more.py`, `capacitacion/tests/test_progreso_tema.py`
- risk: tier 2 (`migrations`, confirmado con `npx @ericrisco/rsc risk`) — panel de 3 refutadores
- review: correctness 0 hallazgos (verificó el orden de la migración contra una BD de test genuinamente fresca, no solo la BD de dev ya parchada); security 0 hallazgos (sin cambio de autorización; `related_name='progresos_tema'` no tiene consumidor todavía); tests 1 `nit` no bloqueante (una prueba por sí sola no distingue "renombrado" de "reemplazado por inscripcion", pero las otras 4 del mismo archivo ya cubren eso) — sin fixes requeridos
- controls: tests ✅ (78/78 del proyecto completo, sin regresiones, verificado también contra BD de test fresca) · build ✅ (`migrate` aplica limpio en dev y en test) · security: sin hallazgos · traceability ✅ (AC4, AC8)
- decision: sin bloqueos; rotura transicional ya aceptada (mismos 4 sitios que leen `ProgresoTema.colaborador` directamente — `views.py`, `serializers/colaborador.py`, `seed_fake_data.py`, `serializers/progreso.py` — seguirán rotos hasta T011/T032-34, ya previsto en la secuenciación del plan)

## T007/T008 — 2026-11-10
- status: complete
- red: no hubo rojo real — `RepeticionTest` pasó verde desde el primer intento contra la implementación ya existente de T004 (cada `Inscripcion` es una fila independiente por `(colaborador, periodo)`)
- verificación de que la prueba no era vacía: mutante propio (reusar una `Inscripcion` existente del mismo `curso` en vez de crear una nueva) — atrapado (`assertNotEqual` falla, `1 == 1`); el panel de revisión probó además 2 mutantes adicionales no intentados por el builder (resetear `completado_at` de la hermana; dedup por `curso` en vez de `periodo`) — ambos atrapados también
- green: T008 fue un no-op de código (la implementación ya satisface la independencia de filas probada por T007)
- files: `capacitacion/tests/test_inscripcion_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — 1 revisor fresh-context (`refuter-tests`)
- review: sin should-fix ni bloqueos; 1 hallazgo `question` (no es defecto): AC3 también exige "progreso no se mezcla", y `RepeticionTest` solo prueba independencia a nivel de fila `Inscripcion` — `ProgresoTema`/`ResultadoEvaluacion` todavía no tienen FK a `Inscripcion` (eso es T009/T010), así que esa mitad de AC3 queda correctamente diferida, no omitida por descuido. Registrado como nota de trazabilidad: AC3 no debe marcarse "cubierto por completo" hasta que T009/T010 (y su batería de pruebas correspondiente) aporten la prueba de no-mezcla de evidencia
- controls: tests ✅ (73/73 del proyecto completo, sin regresiones) · build ✅ · security: sin hallazgos del refutador · traceability ⚠️ parcial y documentada (ver nota arriba — AC3 cubierto solo en su mitad "fila independiente")
- decision: sin bloqueos; nota de trazabilidad registrada aquí para que T009/T010 cierren la mitad pendiente de AC3
