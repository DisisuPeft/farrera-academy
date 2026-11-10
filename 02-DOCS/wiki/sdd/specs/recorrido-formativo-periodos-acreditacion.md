---
type: spec
title: Spec — Periodos, inscripción como unidad de participación y acreditación centralizada
description: WHAT y WHY para introducir imparticiones/periodos, convertir la inscripción en la unidad real de participación, e implementar la acreditación de competencias como servicio transaccional centralizado en el backend.
tags: [sdd, spec]
timestamp: 2026-11-07T20:00:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
status: clarified
---

# Spec — Periodos, inscripción como unidad de participación y acreditación centralizada

> Slug: `recorrido-formativo-periodos-acreditacion` · Status: clarified (approved by user 2026-11-10; 4 open points resolved in `clarify` same day) · Created: 2026-11-07
> Inherits: [constitution](../constitution.md) v1.0.0

## Problem & why

Hoy un colaborador no puede repetir un curso: `Inscripcion` tiene una restricción de unicidad por colaborador+curso que lo bloquea estructuralmente. Cuando la organización necesita que alguien recurse una formación (una actualización sustancial del contenido, una recertificación periódica), no hay forma de registrarlo sin reescribir la única inscripción existente — perdiendo el progreso, los resultados y la trazabilidad de la participación anterior.

Además, la acreditación de competencias se dispara hoy por un signal reactivo que reacciona a "¿`completado_at` tiene valor?" en cualquier guardado de `Inscripcion`, no a "¿el colaborador acaba de completar el curso?". Esto significa que un guardado incidental sobre una inscripción ya completada — después de que un administrador cambie qué nivel otorga el curso — puede subir el nivel de competencia de un colaborador sin que haya hecho ninguna formación nueva. Confirmado y reproducido en `docs/AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md` §3.

Finalmente, la evidencia de aprendizaje (progreso por tema, resultados de evaluación, respuestas a bloques) está hoy atada solo a colaborador+contenido, nunca a una participación concreta — así que incluso si se permitiera repetir un curso, no habría forma de distinguir a qué pasada pertenece cada dato.

## Cost of not building it

Sin esto, la organización no puede registrar recapacitaciones ni recertificaciones periódicas de ningún curso — un requisito operativo real de un LMS corporativo de desarrollo de competencias. Y mientras exista el riesgo de reacreditación descrito arriba, cualquier edición administrativa futura de qué nivel otorga un curso es una fecha-bomba: la próxima vez que algo guarde una inscripción histórica de ese curso, algún colaborador puede subir de nivel sin mérito, silenciosamente, sin ningún log que lo explique.

## The cheapest alternative

Se evaluó no introducir una entidad de periodo/impartición y en su lugar solo relajar la restricción de unicidad de `Inscripcion` (permitir múltiples filas colaborador+curso sin agruparlas). Esto resuelve la repetición, pero no resuelve "distinguir ejecuciones" de forma consultable (no hay ningún agrupador al que preguntarle "qué colaboradores participaron en esta convocatoria"), y en MySQL no hay forma portable de expresar "solo una inscripción *abierta* a la vez por colaborador+curso" sin un índice único condicional, que MySQL no soporta de forma nativa como lo hacen Postgres/SQLite. Ver comparación completa de alternativas en `docs/AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md` §4 (Alternativa A vs B vs C) — se descartó A por esta razón y C por falta de evidencia de necesidad.

## Goals

- Un curso puede tener múltiples imparticiones/periodos, y cada periodo agrupa las inscripciones que ocurren dentro de él.
- Un colaborador puede repetir un curso en un periodo distinto, conservando intacta la participación anterior (progreso, resultados, respuestas, acreditación ya otorgada).
- Toda evidencia de aprendizaje queda atribuida inequívocamente a una inscripción concreta, nunca solo a colaborador+contenido.
- La finalización de una inscripción y la acreditación de competencias que de ahí se deriva ocurren una sola vez por finalización real, a través de un único punto de autoridad en el backend — nunca por un guardado incidental ni por una entrada directa del colaborador.
- Las relaciones cruzadas entre inscripción, periodo, curso, progreso, evaluación y respuesta son consistentes entre sí y esa consistencia se puede verificar, no solo asumir.
- El esquema resultante es el correcto a largo plazo; no se sacrifica su limpieza por preservar datos de prueba actuales (son descartables).

## Non-goals / out of scope

- **Gating granular de contenido** — ningún mecanismo de "bloque obligatorio", "reproducción de video requerida" ni "desbloqueo secuencial de temas/módulos" se introduce en este ciclo. Ninguno de los tres existe hoy en el modelo (confirmado por lectura de código) y cada uno es un subsistema con sus propios campos y lógica. Queda para una spec posterior, una vez que la base de este ciclo esté construida y probada. (Decisión explícita del usuario en este ciclo de specify.)
- **Aprobación automática de evaluaciones como gate de finalización con reglas nuevas de calificación** — la finalización automática de esta spec usa la evidencia que ya existe o que esta spec añade (progreso por tema + resultados de evaluación ya existentes dentro de la inscripción); no se diseñan nuevas reglas de calificación o ponderación.
- **Asignación de materiales distintos por periodo** (Alternativa C de la auditoría previa) — sin evidencia de necesidad actual; no se construye.
- **Migración/backfill de datos de prueba existentes** — son descartables por instrucción explícita del usuario; no se diseña ningún proceso de backfill complejo. Se puede recrear/limpiar la base de desarrollo.
- **Interfaz de administración para crear/cerrar periodos manualmente desde un panel visual** — fuera de alcance de esta spec de backend; se expone como API, el frontend decide cómo lo presenta.
- **Historial completo (bitácora de cada nivel de competencia otorgado en el pasado)** — sigue posponible, tal como ya lo marcaba la auditoría previa. Esta spec solo corrige *cuándo* se dispara la acreditación, no construye un historial de niveles.

## Users & context

- **Colaborador**: un empleado de Grupo Farrera inscrito en formación. Puede necesitar recursar un curso (recapacitación, recertificación) sin perder la evidencia de su participación anterior.
- **Administrador**: gestiona cursos, crea/cierra periodos de impartición, puede corregir manualmente datos de inscripción cuando sea necesario, y puede forzar una finalización excepcional fuera del cumplimiento normal de progreso/evaluaciones — siempre a través del mismo servicio centralizado de finalización, nunca editando directamente el estado de finalización o el nivel acreditado (ver Clarificación 2026-11-10 #3). El colaborador nunca puede fijar directamente la finalización, la calificación final ni el nivel acreditado de su propia inscripción.
- **El propio backend**: es la autoridad que decide cuándo una inscripción se considera finalizada y cuándo corresponde acreditar una competencia — ya no el colaborador reportándolo él mismo.

## What the user can do

- Un administrador puede crear un nuevo periodo de impartición para un curso existente, con una fecha de inicio y, opcionalmente, una de fin, y puede cerrarlo.
- Un colaborador puede inscribirse a un curso únicamente dentro de un periodo vigente (abierto) de ese curso; no puede inscribirse dos veces al mismo periodo, pero sí puede inscribirse a un periodo distinto del mismo curso aunque ya haya completado uno anterior.
- Un colaborador interactúa con el contenido (avanza en temas, responde bloques, presenta evaluaciones) dentro del contexto de una inscripción concreta; toda esa evidencia queda asociada a esa inscripción, no solo a su identidad.
- Un colaborador **no puede** marcar directamente su propia inscripción como finalizada, ni fijar su calificación final, ni otorgarse un nivel de competencia — estas acciones las determina el backend a partir de la evidencia real registrada.
- Un administrador puede consultar, para cualquier colaborador, todas sus participaciones históricas en un mismo curso (una por periodo), cada una con su propia evidencia, sin que una participación sobrescriba o se mezcle con otra.

## What result they get

- Al crear una inscripción sin especificar un periodo vigente del curso (porque no existe uno abierto, o porque ya tiene una inscripción activa en ese periodo), la operación es rechazada con una respuesta que identifica cuál de las dos condiciones falló — nunca un error genérico de base de datos.
- Al completar válidamente todo lo requerido de una inscripción — progreso registrado en todos los `Tema` del curso, y además un `ResultadoEvaluacion` aprobatorio para cada `Evaluacion` asociada si el curso tiene alguna — esa inscripción queda marcada como finalizada exactamente una vez, con una marca de tiempo, y si el curso acredita una competencia, el nivel del colaborador en esa competencia queda actualizado a más tardar en la misma operación — nunca requiere un paso manual adicional ni un segundo guardado. Un curso sin ninguna evaluación asociada se finaliza solo con el progreso completo de todos sus temas.
- Un administrador puede forzar la finalización excepcional de una inscripción que no cumple el criterio normal, invocando el mismo servicio centralizado — nunca editando el campo de finalización directamente — de forma que la operación quede igual de auditada e idempotente que una finalización automática.
- Cerrar un periodo bloquea únicamente nuevas inscripciones a él; las inscripciones ya existentes dentro de ese periodo siguen avanzando y pueden finalizar normalmente después del cierre.
- Repetir una acción que ya finalizó una inscripción (reenviar la misma señal de finalización, o que algo vuelva a guardar la inscripción ya finalizada) no vuelve a ejecutar la acreditación ni cambia el nivel otorgado — el resultado observable es idéntico al de la primera vez.
- Consultar las inscripciones de un colaborador en un curso con dos periodos distintos muestra dos registros independientes, cada uno con su propio progreso y resultados, sin que uno contamine al otro.

## What it must respect

- El mecanismo de comparación "solo sube, nunca baja" de `CompetenciaColaborador.nivel` contra `NivelCompetencia.orden`, ya documentado y correcto, se conserva sin cambios — esta spec corrige *cuándo* se dispara la acreditación, no la lógica de comparación de niveles (instrucción explícita del usuario: no reemplazar la lógica de competencias sin justificar una limitación concreta, y aquí no la hay).
- El recálculo de brecha de un puesto contra el nivel acreditado de un colaborador (`MiPerfilCompetenciasView`), que ya recalcula correctamente en tiempo de consulta contra el requisito vigente sin alterar el nivel histórico, sigue funcionando igual.
- Las decisiones ya tomadas para el constructor visual de contenido (revisión por recurso + `ETag`/`If-Match`, soft-delete y restauración por diff, separación publicado/borrador) — documentadas en `docs/REVISION_CONCURRENCIA_HISTORIAL_PUBLICACION.md` y aún no implementadas en código — no se ven alteradas por este trabajo; viven en una capa distinta (autoría de contenido, no inscripción/participación), confirmado en `docs/AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md` §6.
- Las restricciones `PROTECT` existentes hacia evidencia real de alumnos (progreso, resultados, respuestas) se mantienen — ninguna evidencia de aprendizaje se vuelve borrable en cascada como efecto secundario de este trabajo.
- Las dos reglas de filtrado de publicación (`publicado` para descubrimiento, bloquear solo `borrador` no `archivado` para lectura de contenido ya en curso) siguen pendientes de implementación independiente; esta spec no las resuelve ni las agrava.

## How it proves it

- Cada regla de integridad referencial nueva o cambiada (unicidad de inscripción por periodo, las FKs nuevas hacia inscripción, los `on_delete` elegidos) se demuestra con una prueba automatizada que reproduce el caso inválido real contra MySQL y confirma que es rechazado — no solo que el caso válido pasa.
- El escenario de riesgo de reacreditación (curso sube de nivel, se vuelve a guardar una inscripción histórica) se demuestra con una prueba automatizada que reproduce exactamente esa secuencia y confirma que el nivel del colaborador **no** cambia.
- Cada uno de los Casos A-F descritos en la auditoría previa (`docs/AUDITORIA_DESACOPLAMIENTO_CURSOS_PERIODOS_COMPETENCIAS.md` §7) se convierte en al menos una prueba automatizada que fija el comportamiento correcto, reemplazando la descripción de "comportamiento real actual" por "comportamiento correcto verificado".
- La evidencia de cada prueba (comando ejecutado, resultado) queda registrada en el archivo de verificación de esta spec al cierre del ciclo (`02-DOCS/wiki/sdd/verifications/`), no solo afirmada en el chat.

## Behaviour

- **Camino principal:** un administrador abre un periodo para un curso → un colaborador se inscribe en ese periodo → interactúa con el contenido generando progreso/respuestas/resultados atribuidos a esa inscripción → al cumplir lo requerido, el backend finaliza la inscripción y, si corresponde, acredita la competencia asociada, en una sola operación consistente.
- **Caso borde — repetición:** el mismo colaborador se inscribe a un periodo posterior del mismo curso; su participación anterior permanece intacta y separada; la nueva inscripción empieza sin progreso previo.
- **Caso borde — guardado repetido tras finalización:** cualquier operación posterior que toque una inscripción ya finalizada no repite la finalización ni la acreditación; el estado observable no cambia.
- **Caso borde — cambio de configuración de competencia después de finalizar:** si se cambia qué nivel otorga un curso después de que un colaborador ya lo completó, el nivel ya otorgado a ese colaborador no cambia por ese solo hecho.
- **Caso de error — inscripción sin periodo vigente:** rechazada, con el motivo identificable (no hay periodo abierto / ya existe inscripción activa en ese periodo).
- **Caso de error — evidencia cruzada inconsistente:** un intento de registrar progreso, respuesta o resultado que no corresponde al curso/periodo real de la inscripción es rechazado, no almacenado silenciosamente.

## Acceptance criteria

- Given un curso sin ningún periodo abierto, When un colaborador intenta inscribirse, Then la inscripción es rechazada identificando la ausencia de periodo vigente.
- Given un colaborador ya inscrito en un periodo abierto de un curso, When intenta inscribirse de nuevo al mismo periodo, Then la segunda inscripción es rechazada.
- Given un colaborador que ya completó un curso en un periodo anterior, When se abre un nuevo periodo del mismo curso y se inscribe, Then la nueva inscripción se crea exitosamente y la anterior permanece sin modificarse.
- Given dos inscripciones del mismo colaborador al mismo curso en periodos distintos, When se registra progreso en la segunda, Then el progreso de la primera no se altera y ambos son consultables de forma independiente.
- Given una inscripción cuyo curso acredita nivel 2 de una competencia, When el colaborador cumple lo requerido y la inscripción se finaliza, Then `CompetenciaColaborador` queda en nivel 2 y la inscripción queda marcada como finalizada, en la misma operación.
- Given una inscripción ya finalizada, When algo vuelve a guardarla (sin pasar de nuevo por el servicio de finalización), Then el nivel de competencia del colaborador y el estado de finalización no cambian.
- Given una inscripción ya finalizada con nivel 2 otorgado, When un administrador cambia la configuración del curso para que otorgue nivel 3, And luego algo guarda de nuevo esa inscripción histórica, Then el nivel del colaborador permanece en 2.
- Given un intento de registrar progreso de un tema que no pertenece al curso de una inscripción dada, When se envía la solicitud, Then es rechazada.
- Given un intento de registrar una respuesta con una opción que no pertenece al bloque referenciado, When se envía la solicitud, Then es rechazada.
- Given un colaborador autenticado, When intenta fijar directamente la finalización, la calificación final o el nivel de competencia de su propia inscripción, Then la operación es rechazada o el campo es ignorado por el backend.
- Given dos solicitudes concurrentes que intentan crear la inscripción de un mismo colaborador al mismo periodo, When ambas se procesan, Then como máximo una tiene éxito y la restricción se cumple también bajo concurrencia real, no solo en el camino secuencial.
- Given una inscripción con progreso completo en todos los temas de su curso y resultados aprobatorios en todas sus evaluaciones, When se registra la última evidencia pendiente, Then la inscripción queda finalizada automáticamente sin ninguna acción manual adicional.
- Given una inscripción de un curso sin ninguna evaluación asociada, When el colaborador completa el progreso de todos los temas del curso, Then la inscripción queda finalizada automáticamente.
- Given una inscripción de un curso con evaluaciones, When el colaborador completa el progreso de todos los temas pero aún no aprueba alguna evaluación, Then la inscripción permanece sin finalizar.
- Given una inscripción que no cumple el criterio normal de finalización, When un administrador invoca la finalización excepcional, Then la inscripción queda finalizada igual que una finalización automática (misma marca de tiempo, misma acreditación si corresponde, mismo registro de auditoría).
- Given un periodo cerrado con una inscripción aún no finalizada dentro de él, When el colaborador sigue registrando progreso o resultados, Then esas operaciones se aceptan igual que si el periodo siguiera abierto, y la inscripción puede finalizar normalmente.
- Given un periodo cerrado, When un colaborador intenta crear una nueva inscripción a ese periodo, Then la operación es rechazada.
- Given un colaborador con dos inscripciones al mismo curso en periodos distintos, When se consulta su perfil de competencias, Then se muestra la inscripción más reciente de ese curso, nunca una elegida por orden de iteración arbitrario.
- Given una ruta de aprendizaje que avanza automáticamente a un colaborador al siguiente curso, When existe un periodo abierto para ese curso, Then lo inscribe ahí vía el mismo servicio de inscripción; When no existe ninguno abierto, Then la auto-inscripción falla explícitamente, sin crear un periodo por su cuenta.
- Given un colaborador con dos inscripciones al mismo curso en periodos distintos, When consulta si está inscrito o su porcentaje de progreso en ese curso, Then el resultado corresponde a su inscripción más reciente, nunca a la unión o suma de ambas.

## Points to clarify

Todo lo que `specify` dejó abierto (3 preguntas abiertas) y el gap adicional que `clarify` encontró (cierre de periodo) quedó resuelto y horneado en el cuerpo de la spec — ver `## Clarifications` para el registro de cada decisión y su por qué, y los criterios de aceptación nuevos que la hacen observable. Las 3 suposiciones tomadas por `specify` fueron validadas sin cambios durante `clarify` 2026-11-10 (se mantienen tal como se decidieron: `Periodo` con fecha de inicio obligatoria/fin opcional/estado; `Inscripcion.periodo` obligatorio; FK directo a `colaborador` eliminado de `ProgresoTema`/`ResultadoEvaluacion`/`ContenidoBloqueRespuesta`).

Solo quedan abiertos los dos puntos que `specify` marcó como intencionalmente fuera de este ciclo:

- **decisión diferida** — el diseño de una bitácora de niveles de competencia otorgados históricamente (no solo el nivel vigente) queda fuera de este ciclo, tal como ya lo marcaba la auditoría previa.
- **área no formulable** — cómo interactuará exactamente el futuro gating granular (bloque obligatorio, video, desbloqueo secuencial) con la regla de finalización automática que esta spec define ahora; se sabe que habrá que revisar esa regla cuando llegue esa spec posterior, pero no se puede formular la pregunta precisa todavía porque esa spec no existe.

## Clarifications

**2026-11-10**

1. **Q:** ¿Qué define la finalización automática cuando el curso tiene evaluaciones? → **Decisión:** progreso registrado en todos los `Tema` del curso Y un `ResultadoEvaluacion` aprobatorio para cada `Evaluacion` asociada. **Por qué:** usa solo evidencia que ya existe en el modelo actual, sin introducir gating nuevo (que quedó fuera de alcance).
2. **Q:** ¿Qué finaliza un curso sin ninguna evaluación asociada? → **Decisión:** progreso completo de todos sus temas basta, sin acción de confirmación adicional. **Por qué:** consistente con la regla general; no pedir una acción extra que el propio modelo no exige en ningún otro camino.
3. **Q:** ¿Puede un administrador forzar una finalización excepcional? → **Decisión:** sí, pero siempre a través del mismo servicio centralizado e idempotente — nunca editando `completado_at` u otro campo de estado directamente. **Por qué:** mantiene la auditoría y no reabre el riesgo de reacreditación fuera de control que esta spec corrige.
4. **Q:** ¿Qué pasa con las inscripciones no finalizadas cuando se cierra su periodo? (gap encontrado por `clarify`, no estaba en la spec original) → **Decisión:** cerrar un periodo solo bloquea nuevas inscripciones a él; las existentes siguen avanzando y pueden finalizar normalmente después del cierre. **Por qué:** cerrar un periodo es una decisión administrativa sobre inscripciones *futuras*, no una orden de cancelar participaciones *en curso* — forzar un desenlace inmediato sería una pérdida de evidencia no solicitada por nadie.

**2026-11-10 (horneado tras `analyze` — hallazgo HIGH #1: deriva de alcance no reflejada en la spec)**

Durante la revisión del plan técnico, el usuario pidió mantener `Inscripcion.curso` coexistiendo con `Inscripcion.periodo` (en vez de derivar `curso` solo en el serializer), y pidió evaluar hasta dónde se podía romper el sistema por esa coexistencia. Un inventario del código real encontró 3 sitios con comportamiento observable que cambia con esta feature y que el usuario decidió explícitamente — pero que nunca se habían escrito como requisito en esta spec, solo en `02-DOCS/wiki/sdd/decisions.md` y en el plan. `analyze` lo marcó como DRIFT (hallazgo #1) porque la spec es la fuente de verdad de requisitos, no el plan ni el log de decisiones. Se hornean aquí como los 3 criterios de aceptación nuevos de arriba:

5. **Q:** ¿Qué debe mostrar el perfil de competencias cuando un colaborador tiene 2+ inscripciones al mismo curso? → **Decisión:** la inscripción más reciente por curso (por `periodo.fecha_inicio`/`inscrito_at` descendente), nunca una elegida por orden de iteración arbitrario.
6. **Q:** ¿Cómo debe auto-inscribir una ruta de aprendizaje al siguiente curso, ahora que existen periodos? → **Decisión:** vía el servicio centralizado de inscripción, en el periodo abierto más reciente de ese curso; si no hay ninguno abierto, falla explícitamente — nunca crea un periodo por su cuenta.
7. **Q:** ¿Sobre qué inscripción se calcula si un colaborador "está inscrito" o su porcentaje de progreso en un curso, cuando tiene varias? → **Decisión:** sobre su inscripción más reciente a ese curso, nunca la unión o suma de todas.
