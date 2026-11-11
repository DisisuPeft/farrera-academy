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

## T010 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_resultado_evaluacion` falló con `TypeError: ResultadoEvaluacion() got unexpected keyword arguments: 'inscripcion'` (razón correcta)
- **paso operativo autorizado por el usuario:** 25 filas de seed de `ResultadoEvaluacion` (sin FK que las referencie) borradas antes de generar la migración — mismo patrón ya establecido en T002/T009
- green: `ResultadoEvaluacion` gana `inscripcion` (PROTECT, NOT NULL), pierde `colaborador`; sin `unique_together` nueva (múltiples intentos por inscripción siguen permitidos); migración `0011_remove_resultadoevaluacion_colaborador_and_more` (orden `RemoveField`→`AddField`, sin la restricción de coexistencia de T009 porque aquí no hay cambio de `unique_together`); 5 pruebas en verde
- files: `capacitacion/models/progreso.py`, `capacitacion/migrations/0011_remove_resultadoevaluacion_colaborador_and_more.py`, `capacitacion/tests/test_resultado_evaluacion.py`
- risk: tier 2 (`migrations`, confirmado con `npx @ericrisco/rsc risk`) — panel de 3 refutadores
- review: correctness 0 hallazgos (confirmó que el orden de operaciones no es sensible aquí, a diferencia de T009, por ausencia de `unique_together`); security 0 hallazgos (sin cambio de autorización; `related_name='resultados_evaluacion'` sin consumidor; `correctas`/`total` siguen siendo server-computed, sin tocar); tests 0 hallazgos — probó 3 mutantes reales contra MySQL (`PROTECT→CASCADE`, agregar `unique_together`, FK renombrado-pero-no-reemplazado) y los 3 quedaron atrapados por las pruebas existentes — sin fixes requeridos
- controls: tests ✅ (83/83 del proyecto completo, sin regresiones, verificado contra BD de test fresca) · build ✅ (`migrate` aplica limpio en dev y en test) · security: sin hallazgos · traceability ✅ (AC4)
- decision: sin bloqueos; rotura transicional ya aceptada (mismos sitios que leen `ResultadoEvaluacion.colaborador` directamente seguirán rotos hasta T011/T032-34, ya previsto en la secuenciación del plan)

## T011 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_bloque_respuesta` falló con `TypeError: ContenidoBloqueRespuesta() got unexpected keyword arguments: 'inscripcion'` (razón correcta)
- paso operativo: tabla `ContenidoBloqueRespuesta` ya estaba vacía (0 filas) — no hizo falta borrar seed, a diferencia de T009/T010
- green: `ContenidoBloqueRespuesta` gana `inscripcion` (PROTECT, NOT NULL), pierde `colaborador`; sin `unique_together` nueva; migración `0012_remove_contenidobloquerespuesta_colaborador_and_more` (orden `RemoveField`→`AddField`, sin restricción de coexistencia porque no hay cambio de `unique_together`, igual que T010); 5 pruebas en verde
- files: `capacitacion/models/curso.py`, `capacitacion/migrations/0012_remove_contenidobloquerespuesta_colaborador_and_more.py`, `capacitacion/tests/test_bloque_respuesta.py`
- risk: tier 2 (`migrations`, confirmado con `npx @ericrisco/rsc risk`) — panel de 3 refutadores
- review: correctness 0 hallazgos (confirmó orden de migración seguro, `PROTECT` correcto en modelo y migración, descartó una falsa alarma transitoria de `makemigrations --check` por bytecode viejo); security 0 hallazgos (confirmó que los 2 call-sites transicionales — `views_colaborador.py`, `serializers/colaborador.py` — fallan cerrado, `TypeError`/`FieldError`, nunca dato incorrecto o fuga entre colaboradores; `es_correcta` intacto); tests 1 `nit` no bloqueante, idéntico al de T009/T010 y confirmado explícitamente como no empeorado (probado con mutante real: agregar un segundo FK `colaborador_legacy` deja las 5 pruebas en verde) — sin fixes requeridos
- controls: tests ⚠️ 83/88 del proyecto completo — 5 fallas conocidas y esperadas en `capacitacion/tests/test_respuestas_bloque.py` (suite preexistente que sí cubría el camino vista→serializer→modelo para este modelo, a diferencia de T009/T010); confirmadas fail-closed por el panel, su arreglo está explícitamente diferido a T032 (ver decisions.md) · build ✅ (`migrate`/`check` aplican limpio) · security: sin hallazgos · traceability ✅ (AC9)
- decision: sin bloqueos; regresión transicional documentada y aceptada en decisions.md — T032 debe incluir `test_respuestas_bloque.py` en su done-check de "suite completa verde"

## T012/T013 — 2026-11-10
- status: complete
- red: `python manage.py test capacitacion.tests.test_evidencia_service` falló con `AssertionError` — devolvía un `ProgresoTema` real en vez de `ContenidoAjeno()` (resolución de inscripción existía pero sin validación cruzada todavía; razón correcta, no un crash de import)
- green (T013, intento 1): `EvidenciaService.registrar_progreso(colaborador, tema, **campos)` — resuelve "inscripción activa" como la más reciente del colaborador (sin filtrar por curso) y cruza su curso contra `tema.modulo.curso`
- **hallazgo bloqueante del panel, corregido en el mismo ciclo:** la resolución "más reciente sin filtrar por curso" diverge de la precondición exacta del plan (`periodo.curso == tema.modulo.curso`) y rechaza progreso legítimo cuando el colaborador tiene una inscripción activa más nueva a OTRO curso — ver decisions.md para el escenario completo y el fix (`_resolver_inscripcion_activa(colaborador, curso)` ahora filtra por curso directamente; distingue `ContenidoAjeno` de `InscripcionNoEncontrada` con una segunda consulta de existencia)
- green (fix): prueba de triangulación nueva (`test_resuelve_por_curso_no_por_inscripcion_mas_reciente`) agregada y verificada contra un mutante real que reproduce el bug original — el mutante hace fallar exactamente esa prueba; revertido, verde de nuevo
- files: `capacitacion/services/evidencia_service.py`, `capacitacion/tests/test_evidencia_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk` sobre los archivos propios de la tarea, no el diff acumulado del repo) — 1 revisor fresh-context (`refuter-correctness`)
- review: ronda 1 — 1 `blocker` (resolución por curso) + 1 `should-fix` (test no distinguía los dos comportamientos); ronda 2 — 0 hallazgos, cierre verificado con mutante independiente del propio revisor
- controls: tests ✅ (90 tests del proyecto completo, 85 verdes — las mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`, sin fallas nuevas) · build ✅ · security: no aplica a este tier (1 revisor, lente correctness) · traceability ✅ (AC8)
- decision: fix aplicado y registrado en decisions.md (no se parqueó — convergencia en ronda 2, sin contradicción con una decisión previa); alcance de `registrar_resultado_evaluacion`/`registrar_respuesta_bloque` (análogos descritos en el plan §3) diferido correctamente a sus propias tareas con prueba roja primero (T014/T015 para `registrar_respuesta_bloque`; `registrar_resultado_evaluacion` queda sin tarea explícita en la tabla — nota para revisar si falta al llegar a T040)

## T014/T015 — 2026-11-11
- status: complete
- red: `python manage.py test capacitacion.tests.test_evidencia_service.EvidenciaServiceRegistrarRespuestaBloqueTests` falló con `AttributeError: type object 'EvidenciaService' has no attribute 'registrar_respuesta_bloque'` (razón correcta — el método no existía todavía)
- green: `EvidenciaService.registrar_respuesta_bloque(colaborador, bloque, opcion, **campos)` — valida primero que `opcion.bloque_id == bloque.id` (rechaza con `ContenidoAjeno()` si no), luego reutiliza la misma resolución de inscripción activa por curso ya corregida en T012/T013 (`_resolver_inscripcion_activa(colaborador, bloque.tema.modulo.curso)`); `es_correcta` se calcula en el servidor desde `opcion.es_correcta`, nunca desde `**campos`
- triangulación: prueba adicional (`test_acepta_opcion_que_si_pertenece_al_bloque_y_calcula_es_correcta_en_servidor`) agregada junto con la de rechazo, para no repetir el mismo gap de vacuidad que el panel encontró en T012 — ambas pruebas verdes desde el primer intento (sin rondas de fix)
- files: `capacitacion/services/evidencia_service.py`, `capacitacion/tests/test_evidencia_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk` sobre los archivos propios de la tarea) — 1 revisor fresh-context (`refuter-correctness`)
- review: 0 hallazgos (confirmó que la resolución por curso del fix anterior se reutiliza correctamente, que `**campos` no puede sobrescribir `es_correcta`, que el recorrido `bloque.tema.modulo.curso` es seguro, y que ambas pruebas nuevas no son vacías); 1 `question` no bloqueante sobre el orden de validación (opción-ajena se evalúa antes de resolver la inscripción, así que sin inscripción activa + opción ajena devuelve `ContenidoAjeno` en vez de `InscripcionNoEncontrada`) — sin caller todavía, no hay comportamiento observable divergente hoy; queda anotado para revisar en T032 si algún caller llega a distinguir estos dos sentinels
- controls: tests ✅ (92 tests del proyecto, 87 verdes — mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`, sin fallas nuevas) · build ✅ · security: no aplica a este tier · traceability ✅ (AC9)
- decision: sin bloqueos; sin fixes requeridos

## T016/T017 — 2026-11-11
- status: complete
- red: no hubo rojo real — `test_progreso_de_la_primera_inscripcion_no_se_altera_al_registrar_en_la_segunda` pasó verde desde el primer intento contra la implementación ya existente de `EvidenciaService.registrar_progreso` (T012/T013), ya que la resolución por curso+más-reciente ya producía el comportamiento correcto para dos inscripciones activas al mismo curso
- verificación de que la prueba no era vacía: mutante propio (invertir el orden de `_resolver_inscripcion_activa` a ascendente) — atrapado, pero vía `IntegrityError` de la restricción única `(inscripcion, tema)`, no vía una aserción propia; el panel de revisión señaló esto como evidencia incompleta y probó 2 mutantes adicionales no intentados por el builder: memoización/caché de la inscripción resuelta (atrapado también por el mismo `IntegrityError`) y "reemplazar en vez de agregar" (borrar el `ProgresoTema` de la otra inscripción antes de crear uno nuevo) — este último sí fue atrapado por una aserción propia de la prueba (`count() == 1` sobre `inscripcion_1`), confirmando que la mitad final de la prueba (independencia consultable) no es peso muerto
- green: T017 fue un no-op de código (la implementación ya satisface la independencia de progreso probada por T016)
- files: `capacitacion/tests/test_evidencia_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — 1 revisor fresh-context (`refuter-tests`)
- review: 0 hallazgos; nota de calidad de evidencia no bloqueante (el mutante propio del builder probaba la restricción de BD, no las aserciones de la prueba — el panel cerró la brecha con su propio mutante)
- controls: tests ✅ (93 tests del proyecto, 88 verdes — mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`) · build ✅ · security: no aplica a este tier · traceability ✅ (AC4)
- decision: sin bloqueos; sin fixes requeridos

## T018/T019 — 2026-11-11
- status: complete
- red: `python manage.py test capacitacion.tests.test_finalizacion_service` falló con `AssertionError: unexpectedly None` (`FinalizacionService.reevaluar` era un no-op stub; razón correcta)
- green (intento 1): `FinalizacionService.reevaluar(inscripcion)` — transaccional, `select_for_update()` sobre la `Inscripcion`, idempotente (si `completado_at` ya tiene valor, retorna sin cambios); criterio: todos los `Tema` del curso tienen `ProgresoTema` de esa inscripción Y toda `Evaluacion` asociada (por `curso` o por `modulo__curso`) tiene al menos un `ResultadoEvaluacion` aprobatorio (`correctas/total*100 >= puntaje_minimo`)
- **hallazgo should-fix del panel, corregido en el mismo ciclo:** un curso sin ningún tema cumplía el criterio vacuamente (conjunto vacío == conjunto vacío) y finalizaba sin evidencia real — ver decisions.md para el escenario completo y el fix (`if not temas_curso.exists(): return False`)
- green (fix): prueba nueva (`test_no_finaliza_un_curso_sin_ningun_tema`) agregada y verificada contra un mutante que reproduce el bug original; revertido, verde de nuevo
- files: `capacitacion/services/finalizacion_service.py`, `capacitacion/tests/test_finalizacion_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk` sobre los archivos propios de la tarea) — 1 revisor fresh-context (`refuter-correctness`)
- review: ronda 1 — 1 `should-fix` (curso sin temas); ronda 2 — 0 hallazgos, confirmó además que `ProgresoTema.tema` es `on_delete=PROTECT` (el escenario "temas borrados con progreso existente" es imposible por esquema, no solo improbable)
- controls: tests ✅ (96 tests del proyecto, 91 verdes — mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`, sin fallas nuevas) · build ✅ · security: no aplica a este tier · traceability ✅ (AC12, AC14)
- decision: fix aplicado y registrado en decisions.md; nota de alcance — esta implementación todavía NO invoca ninguna acreditación explícita (`AcreditacionService` no existe hasta T025); el `post_save` de `competencias/signals.py` sigue activo sin cambios y se dispara igual vía `inscripcion.save(update_fields=['completado_at'])`, comportamiento transicional ya aceptado y documentado en el plan — T025 reconecta esto

## T020/T021 — 2026-11-11
- status: complete
- red: no hubo rojo real — ambas pruebas pasaron verde desde el primer intento contra la implementación ya existente de `FinalizacionService._criterio_cumplido` (T018/T019): cuando `evaluaciones_curso` está vacío, el `for` simplemente no itera y la función retorna `True` si los temas están completos — exactamente el comportamiento que pide AC13
- verificación de que las pruebas no eran vacías: mutante propio (`if not evaluaciones_curso.exists(): return False`, forzando incorrectamente a requerir al menos una evaluación) — atrapó `test_finaliza_con_solo_progreso_completo_si_el_curso_no_tiene_evaluaciones`; el panel de revisión probó un mutante distinto (anular el `return False` del chequeo de temas completos) y confirmó que `test_no_finaliza_si_falta_progreso_de_algun_tema_aunque_no_haya_evaluaciones` lo atrapa, y que esta segunda prueba es la ÚNICA en todo el archivo que cubre la combinación "sin evaluaciones + temas incompletos" (al borrarla, ese mutante sobrevive sin que ninguna otra prueba lo note)
- green: T021 fue un no-op de código (la implementación ya satisface AC13)
- files: `capacitacion/tests/test_finalizacion_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — 1 revisor fresh-context (`refuter-tests`)
- review: 0 hallazgos; 2 preguntas no bloqueantes anotadas por el panel (cobertura separada de `curso=` vs `modulo__curso=` cuando ambos están ausentes; re-llamar `reevaluar` sin evaluaciones sobre una inscripción ya finalizada) — ninguna requiere acción en esta tarea
- controls: tests ✅ (98 tests del proyecto, 93 verdes — mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`) · build ✅ · security: no aplica a este tier · traceability ✅ (AC13)
- decision: sin bloqueos; sin fixes requeridos

## T022/T023 — 2026-11-11
- status: complete
- red: no hubo rojo real inicialmente — ambas pruebas pasaron verde desde el primer intento contra la implementación ya existente (`if inscripcion.completado_at is not None: return inscripcion`, ya presente desde T019)
- verificación de que las pruebas no eran vacías: mutante propio (quitar la guarda de idempotencia por completo) — descubrió que la primera prueba (que borra el progreso antes de la segunda llamada) NO atrapa ese mutante, porque sin la guarda el criterio se re-evalúa, sale falso, y no escribe nada igual; agregué una segunda prueba más fuerte (`test_reevaluar_no_reescribe_completado_at_aunque_el_criterio_siga_cumplido`, criterio sigue cumplido en la segunda llamada) que sí atrapa el mutante — dos timestamps de microsegundo distinto. El panel reprodujo esto de forma independiente y probó un segundo mutante (invertir la condición de la guarda) — atrapado también, pero de forma trivial (rompe el `setUp`)
- green: T023 fue casi un no-op de código (la guarda ya existía); el único cambio real fue agregar la prueba que faltaba y corregir el docstring de la primera para no reclamar que prueba la guarda cuando en realidad prueba una propiedad adyacente ("una vez finalizada, no se des-finaliza aunque la evidencia se rompa después")
- files: `capacitacion/tests/test_finalizacion_service.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — 1 revisor fresh-context (`refuter-tests`)
- review: 2 `nit` no bloqueantes — (1) el docstring de la primera prueba reclamaba probar la idempotencia de AC6 sin hacerlo realmente (corregido en esta misma ronda); (2) pregunta teórica sobre precisión de timestamp en comparaciones de microsegundos, sin repro concreto, descartada como riesgo pre-existente y compartido por cualquier aserción de `timezone.now()` en el proyecto
- controls: tests ✅ (100 tests del proyecto, 95 verdes — mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`) · build ✅ · security: no aplica a este tier · traceability ✅ (AC6)
- decision: fix trivial de documentación aplicado y registrado aquí (no ameritó entrada separada en decisions.md — es un ajuste de claridad, no una decisión de diseño)

## T041 — 2026-11-11
- status: complete
- hallazgo: `competencias/tests.py` no existe en el repositorio (ni en el working tree ni en ningún commit de `HEAD`) — la premisa del plan (migrar pruebas existentes) estaba obsoleta; ver decisions.md
- green: creado `competencias/tests/__init__.py` (paquete vacío), siguiendo el patrón de `capacitacion/tests/`
- files: `competencias/tests/__init__.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk`) — cambio trivial, sin lógica, revisado junto con T024 (ver abajo) por ser su prerrequisito directo
- controls: tests ✅ (`python manage.py test competencias` sigue en "0 tests", sin pérdida de cobertura porque no había ninguna) · build ✅
- decision: registrada en decisions.md — tarea resuelta por omisión, sin conflicto de diseño

## T024 — 2026-11-11
- status: complete
- red: `python manage.py test competencias.tests.test_acreditacion_regression` falla con `AssertionError: <NivelCompetencia: Nivel 3 (nivel-3)> != <NivelCompetencia: Nivel 2 (nivel-2)>` — reproduce el hallazgo real de la auditoría (el `post_save` de `competencias/signals.py` re-evalúa y sube de nivel al re-guardar una inscripción histórica, sin pasar por el servicio de finalización)
- **bug propio detectado y corregido durante la escritura de la prueba:** `FinalizacionService.reevaluar()` retorna una instancia re-obtenida de la BD, no muta el objeto recibido — sin un `self.inscripcion.refresh_from_db()` en `setUp`, el `self.inscripcion.save()` posterior sobrescribía `completado_at` de vuelta a `None` con el valor obsoleto en memoria, haciendo que la guarda del signal (`if not instance.completado_at: return`) evitara el bug por completo y la prueba pasara en verde por la razón equivocada. Corregido agregando el `refresh_from_db()`.
- files: `competencias/tests/test_acreditacion_regression.py`
- risk: tier 1 (confirmado con `npx @ericrisco/rsc risk` sobre los archivos propios de la tarea — el forecast del plan era tier 2 porque anticipaba el cambio a `competencias/signals.py`, pero T024 solo agrega una prueba; esa tarea tier-2 real es T025, que sí modifica el signal)
- review: 0 hallazgos — el revisor verificó de forma independiente la corrección del bug de staleness, confirmó que el signal está realmente conectado (no simulado/evitado), y corrió su propio contra-mutante (una forma plausible del fix real de T025) para confirmar que la prueba pasa en verde por la razón correcta una vez arreglado el bug real — no por un artefacto incidental
- controls: tests ✅ (101 tests del proyecto, 95 verdes — 1 falla esperada y correcta de esta misma prueba de regresión + las mismas 5 fallas ya conocidas y aceptadas de T011/`test_respuestas_bloque.py`) · build ✅ · security: no aplica a este tier · traceability ✅ (AC7)
- decision: sin bloqueos; esta prueba se deja intencionalmente en rojo — su corrección es el done-check de T025, no de esta tarea
