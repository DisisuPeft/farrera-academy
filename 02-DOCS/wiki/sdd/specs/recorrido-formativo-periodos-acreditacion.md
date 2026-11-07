---
type: spec
title: Spec — Periodos, inscripción como unidad de participación y acreditación centralizada
description: WHAT y WHY para introducir imparticiones/periodos, convertir la inscripción en la unidad real de participación, e implementar la acreditación de competencias como servicio transaccional centralizado en el backend.
tags: [sdd, spec]
timestamp: 2026-11-07T20:00:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
status: draft
---

# Spec — Periodos, inscripción como unidad de participación y acreditación centralizada

> Slug: `recorrido-formativo-periodos-acreditacion` · Status: draft · Created: 2026-11-07
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
- **Administrador**: gestiona cursos, crea/cierra periodos de impartición, puede corregir manualmente datos de inscripción cuando sea necesario. El colaborador nunca puede fijar directamente la finalización o el nivel acreditado de su propia inscripción. Si el administrador puede forzar una finalización excepcional por una vía distinta al cumplimiento normal de requisitos es, deliberadamente, una pregunta abierta — ver "Points to clarify".
- **El propio backend**: es la autoridad que decide cuándo una inscripción se considera finalizada y cuándo corresponde acreditar una competencia — ya no el colaborador reportándolo él mismo.

## What the user can do

- Un administrador puede crear un nuevo periodo de impartición para un curso existente, con una fecha de inicio y, opcionalmente, una de fin, y puede cerrarlo.
- Un colaborador puede inscribirse a un curso únicamente dentro de un periodo vigente (abierto) de ese curso; no puede inscribirse dos veces al mismo periodo, pero sí puede inscribirse a un periodo distinto del mismo curso aunque ya haya completado uno anterior.
- Un colaborador interactúa con el contenido (avanza en temas, responde bloques, presenta evaluaciones) dentro del contexto de una inscripción concreta; toda esa evidencia queda asociada a esa inscripción, no solo a su identidad.
- Un colaborador **no puede** marcar directamente su propia inscripción como finalizada, ni fijar su calificación final, ni otorgarse un nivel de competencia — estas acciones las determina el backend a partir de la evidencia real registrada.
- Un administrador puede consultar, para cualquier colaborador, todas sus participaciones históricas en un mismo curso (una por periodo), cada una con su propia evidencia, sin que una participación sobrescriba o se mezcle con otra.

## What result they get

- Al crear una inscripción sin especificar un periodo vigente del curso (porque no existe uno abierto, o porque ya tiene una inscripción activa en ese periodo), la operación es rechazada con una respuesta que identifica cuál de las dos condiciones falló — nunca un error genérico de base de datos.
- Al completar válidamente todo lo requerido de una inscripción (progreso de todos los temas del curso + resultados de evaluación aprobatorios, según el curso lo tenga configurado), esa inscripción queda marcada como finalizada exactamente una vez, con una marca de tiempo, y si el curso acredita una competencia, el nivel del colaborador en esa competencia queda actualizado a más tardar en la misma operación — nunca requiere un paso manual adicional ni un segundo guardado.
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

## Points to clarify

- **suposición tomada** — `Periodo` (impartición) tiene fecha de inicio obligatoria, fecha de fin opcional, y un estado abierto/cerrado explícito. *Base:* respuesta del usuario en la ronda de preguntas de esta fase. *Riesgo:* si en la práctica los periodos no tienen fin planeado de antemano (p. ej. "cohorte continua"), el campo fecha_fin nullable ya lo cubre; si se necesita más de dos estados (p. ej. "programado" antes de abrir), este modelo de dos estados quedaría corto — revisar en `plan`.
- **suposición tomada** — `Inscripcion.periodo` es obligatorio (NOT NULL) desde esta spec en adelante; no se preserva ningún dato de prueba existente que no tenga periodo. *Base:* respuesta explícita del usuario (datos de desarrollo son descartables). *Riesgo:* ninguno relevante si efectivamente se recrea la base de desarrollo antes de aplicar el esquema nuevo — a confirmar como paso operativo en `plan`.
- **suposición tomada** — el FK directo a `colaborador` se elimina de `ProgresoTema`, `ResultadoEvaluacion` y `ContenidoBloqueRespuesta`, derivándose siempre vía `inscripcion.colaborador`. *Base:* respuesta explícita del usuario, alineada con el principio de la constitución de no duplicar información derivable sin justificación de rendimiento/auditoría. *Riesgo:* toda consulta existente que filtre estos modelos por `colaborador` directo debe migrarse a filtrar por `inscripcion__colaborador` — impacto de código a mapear en `plan`, no solo de modelo.
- **pregunta abierta** — ¿qué constituye exactamente "cumplir lo requerido" para que el servicio de finalización marque una inscripción como completada automáticamente, en ausencia de cualquier gating granular (que quedó fuera de alcance)? Candidatos observados en el código actual: progreso registrado en todos los `Tema` del curso, y/o un `ResultadoEvaluacion` aprobatorio para cada `Evaluacion` asociada. Necesito que el usuario confirme la regla exacta antes de que `plan` la traduzca a lógica concreta.
- **pregunta abierta** — cuando un curso no tiene ninguna `Evaluacion` asociada (solo contenido informativo), ¿la finalización depende solo del progreso de temas, o requiere una acción explícita adicional (p. ej. que el colaborador la marque como "revisada", aunque el campo que la respalda ya no sea editable arbitrariamente)?
- **pregunta abierta** — ¿puede un administrador alguna vez forzar manualmente la finalización de una inscripción (p. ej. por una excepción operativa), o la finalización es exclusivamente automática y cualquier excepción requiere un proceso fuera de este sistema?
- **decisión diferida** — el diseño de una bitácora de niveles de competencia otorgados históricamente (no solo el nivel vigente) queda fuera de este ciclo, tal como ya lo marcaba la auditoría previa.
- **área no formulable** — cómo interactuará exactamente el futuro gating granular (bloque obligatorio, video, desbloqueo secuencial) con la regla de finalización automática que esta spec define ahora; se sabe que habrá que revisar esa regla cuando llegue esa spec posterior, pero no se puede formular la pregunta precisa todavía porque esa spec no existe.
