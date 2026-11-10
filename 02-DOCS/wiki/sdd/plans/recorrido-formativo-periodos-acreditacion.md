---
type: plan
title: Plan — Periodos, inscripción como unidad de participación y acreditación centralizada
description: Plan técnico (contratos, modelos, flujos) para introducir Periodo/Impartición, convertir Inscripcion en unidad de participación, y centralizar la finalización/acreditación en un servicio transaccional.
tags: [sdd, plan]
timestamp: 2026-11-10T00:00:00Z
topic: sdd
slug: recorrido-formativo-periodos-acreditacion
status: draft
---

# Plan — Periodos, inscripción como unidad de participación y acreditación centralizada

> Spec: [../specs/recorrido-formativo-periodos-acreditacion.md](../specs/recorrido-formativo-periodos-acreditacion.md) · Constitution: [../constitution.md](../constitution.md) · Status: draft
> Last updated: 2026-11-10

## 0. Global Constraints

- **Motor de base de datos:** MySQL. Ninguna restricción propuesta aquí usa un índice único condicional (constitution §1.2); todas las unicidades son índices completos estándar.
- **Datos de prueba:** descartables. Las migraciones de este plan NO incluyen backfill de datos existentes — se asume que la base de desarrollo se recrea antes de aplicar el esquema nuevo (spec, "suposición tomada").
- **`on_delete`:** toda FK nueva hacia `Inscripcion` desde evidencia de aprendizaje es `PROTECT` (constitution §3.10). Toda FK de `Inscripcion`/`ProgresoTema`/`ResultadoEvaluacion`/`ContenidoBloqueRespuesta` hacia `Curso`/`Tema`/`Evaluacion`/`ContenidoBloque` sigue siendo `PROTECT` como ya estaba.
- **Campos server-computed nunca escribibles por colaborador:** `completado_at`, calificación final, nivel acreditado — ya exigido por constitution §3.11.
- **TDD estricto para esta feature:** cada regla de integridad nueva lleva una prueba que reproduce el caso inválido real (constitution §2.7-2.8).
- **FK directa a colaborador eliminada** de `ProgresoTema`, `ResultadoEvaluacion`, `ContenidoBloqueRespuesta` — se deriva vía `inscripcion.colaborador` (spec, suposición tomada, validada en `clarify`).
- **`Inscripcion.periodo` es obligatorio (NOT NULL)** desde este esquema en adelante (spec, suposición tomada, validada en `clarify`).
- **`Inscripcion.curso` COEXISTE con `Inscripcion.periodo`** (revisión de plan, 2026-11-10): ambas FKs son columnas reales. `curso` nunca es escribible por ningún cliente de la API ni por ningún caller directo — solo `InscripcionService` lo escribe, siempre copiándolo de `periodo.curso` en el mismo momento en que fija `periodo`. La invariante `inscripcion.curso == inscripcion.periodo.curso` se garantiza por construcción (un solo punto de escritura), no por un constraint de base de datos (MySQL no puede expresar una igualdad entre columnas de dos tablas distintas) — y se prueba explícitamente (constitution §12).
- **No se introduce ningún mecanismo de cola/tarea en segundo plano** (no existe Celery ni ningún worker en este proyecto — confirmado en `CODEBASE-MAP.md` §Hidden behavior); toda re-evaluación de finalización ocurre de forma síncrona dentro de la misma request que registra la última evidencia.
- **Sin gitmoji, sin atribución de IA en commits** (constitution §3.14, §4.16).

## 1. Context & constraints

- Acceptance criteria que fijan el diseño: spec §Acceptance (inscripción solo en periodo abierto; no duplicar inscripción al mismo periodo; repetir curso en periodo distinto no mezcla evidencia; finalización automática exacta con y sin evaluaciones; finalización nunca se repite; cambiar `CompetenciaCurso` no reacredita retroactivamente; progreso/respuesta ajenos al curso de la inscripción se rechazan; colaborador no puede autofinalizarse; concurrencia en creación de inscripción; finalización manual excepcional vía el mismo servicio; cerrar periodo no fuerza desenlace de inscripciones abiertas).
- Constitution en juego: §1.2 (MySQL, sin índices condicionales), §3.9-3.12 (bases de modelo, PROTECT, campos server-computed, invariantes en BD + servicio transaccional), §2.7-2.8 (TDD estricto, prueba del caso inválido).
- Qué debe respetar (spec §What it must respect): la comparación "solo sube, nunca baja" de `CompetenciaColaborador.nivel` NO se toca; el recálculo de brecha de `MiPerfilCompetenciasView` sigue igual; las decisiones del constructor visual (revision/ETag, soft-delete, publicación) viven en otra capa y no se tocan.
- Fuera de alcance (spec §Non-goals) que este diseño NO debe tocar: gating granular (bloque obligatorio, video, desbloqueo secuencial), nuevas reglas de calificación/ponderación, asignación de materiales por periodo, backfill de datos de prueba, UI de administración de periodos, bitácora histórica completa de niveles.

## 2. Architecture

```text
[ Colaborador / Admin (API) ]
         |
         v
[ InscripcionService ]  --crea--> [ Inscripcion ] --pertenece a--> [ Periodo ] --pertenece a--> [ Curso ]
         |
         v (al registrar evidencia)
[ EvidenciaService ]  --valida consistencia cruzada--> [ ProgresoTema | ResultadoEvaluacion | ContenidoBloqueRespuesta ]
         |
         v (tras cada escritura de evidencia)
[ FinalizacionService ] --si se cumple el criterio o se fuerza--> marca Inscripcion.completado_at
         |
         v (si corresponde)
[ competencias.AcreditacionService ] --sube nivel si aplica--> [ CompetenciaColaborador ]
```

- **`Periodo`** (interno, nuevo modelo en `capacitacion`) — agrupa inscripciones de un curso dentro de una ventana temporal con estado abierto/cerrado. Responsabilidad única: ser el agrupador de ejecuciones de un curso.
- **`InscripcionService`** (interno, nuevo) — única puerta de entrada para crear una `Inscripcion`: valida que el periodo esté abierto y que no exista ya una inscripción de ese colaborador a ese periodo, de forma atómica.
- **`EvidenciaService`** (interno, nuevo) — única puerta de entrada para registrar `ProgresoTema`/`ResultadoEvaluacion`/`ContenidoBloqueRespuesta`: resuelve la inscripción activa del colaborador para el curso del contenido referenciado, valida que ese contenido pertenezca al curso de esa inscripción, y tras guardar, invoca a `FinalizacionService` para re-evaluar si la inscripción ya se completó.
- **`FinalizacionService`** (interno, nuevo, en `capacitacion`) — único punto de autoridad para marcar una inscripción como finalizada, automática o forzada por un administrador. Idempotente: si la inscripción ya está finalizada, no hace nada observable. Al finalizar, invoca a la acreditación de competencias dentro de la misma transacción. **Sustituye por completo** al signal `post_save` actual de `competencias/signals.py`.
- **`competencias.AcreditacionService`** (interno, ya existe como lógica dentro del signal — se extrae a una función explícita, sin cambiar su comparación de niveles) — dado un curso ya finalizado por un colaborador, sube su `CompetenciaColaborador.nivel` si corresponde. Se llama una sola vez, desde dentro de `FinalizacionService`, nunca desde un signal reactivo.
- **Modelos existentes modificados** (internos): `Inscripcion`, `ProgresoTema`, `ResultadoEvaluacion`, `ContenidoBloqueRespuesta` — ver §4.

**Top architectural decision (revisada 2026-11-10):** `Inscripcion` mantiene **ambas** FKs — `curso` y `periodo` — como columnas reales coexistentes, en vez de derivar `curso` solo en el serializer. **Por qué el cambio de postura:** un inventario exhaustivo del código real (no hipotético) encontró **7 sitios** que hoy leen `Inscripcion.curso` directamente para lógica de negocio real — acreditación de competencias (`competencias/signals.py:21`), visualización de nivel acreditado (`competencias/serializers.py:69`), perfil de competencias (`competencias/views.py:177`), inscripción automática por ruta de aprendizaje (`competencias/views.py:286-303`), y cálculo de progreso/estado de inscripción del colaborador (`capacitacion/serializers/colaborador.py:155-176`). Derivar `curso` solo como propiedad de serializer habría dejado sin servir exactamente a los callers que no pasan por un serializer (el signal, la vista de perfil, la vista de ruta de aprendizaje) — todos ellos acceden al modelo directamente, no a su representación serializada. Mantener la columna real resuelve esto sin reescribir esos cinco sitios en este mismo ciclo. **Cómo se evita la divergencia que esto reabre:** `curso` nunca es escribible de forma independiente — ver Global Constraints — así que la invariante se sostiene por construcción del único punto de escritura (`InscripcionService`), no por disciplina de cada caller.

## 3. Interfaces & contracts

```text
InscripcionService.crear(colaborador: User, periodo: Periodo) -> Inscripcion | PeriodoNoAbierto | InscripcionDuplicada
  - invariante: transaccional, usa bloqueo de fila (select_for_update) sobre el periodo durante la validación + creación
  - invariante: a lo sumo una Inscripcion por (colaborador, periodo) incluso bajo solicitudes concurrentes
  - precondición: periodo.estado == abierto
  - postcondición: Inscripcion.completado_at es None; Inscripcion.periodo == periodo

EvidenciaService.registrar_progreso(colaborador: User, tema: Tema, **campos) -> ProgresoTema | InscripcionNoEncontrada | ContenidoAjeno
  - precondición: existe una Inscripcion no finalizada de ese colaborador cuyo periodo.curso == tema.modulo.curso
  - postcondición: el ProgresoTema queda atribuido a esa Inscripcion; se invoca FinalizacionService.reevaluar(inscripcion) después de guardar
  - análogo para registrar_resultado_evaluacion(colaborador, evaluacion, **campos) y registrar_respuesta_bloque(colaborador, bloque, opcion, **campos), cada uno validando que evaluacion/bloque pertenezca al curso de la inscripción activa

FinalizacionService.reevaluar(inscripcion: Inscripcion) -> Inscripcion
  - invariante: idempotente — si inscripcion.completado_at ya tiene valor, no hace nada y lo retorna sin cambios
  - invariante: transaccional con select_for_update sobre la Inscripcion antes de leer/escribir completado_at
  - postcondición: si progreso completo en todos los Tema del curso Y (sin evaluaciones O resultado aprobatorio en cada una), completado_at queda fijado y se invoca AcreditacionService.acreditar(inscripcion) dentro de la misma transacción

FinalizacionService.forzar(inscripcion: Inscripcion, actor: User) -> Inscripcion | YaFinalizada
  - precondición: actor es Administrador
  - invariante: misma idempotencia y misma transacción que reevaluar(); registra quién forzó la finalización
  - postcondición: idéntica a una finalización automática (completado_at, acreditación si corresponde)

AcreditacionService.acreditar(inscripcion: Inscripcion) -> None
  - precondición: inscripcion.completado_at tiene valor (llamado solo desde dentro de FinalizacionService)
  - invariante: no cambia la comparación existente "solo sube si nivel.orden es mayor" (sin modificar)
  - postcondición: CompetenciaColaborador actualizado si CompetenciaCurso.nivel.orden > nivel actual del colaborador en esa competencia
```

## 4. Data model & flow

**Entidades**

- **`Periodo`** (nuevo, `BaseModel`) — `curso` (FK a `Curso`, PROTECT), `nombre`, `fecha_inicio` (obligatoria), `fecha_fin` (nullable), `estado` (choices: abierto/cerrado). Relación inversa: `curso.periodos`.
- **`Inscripcion`** (modificado) — gana `periodo` (FK a `Periodo`, PROTECT, NOT NULL); **conserva** `curso` (FK existente, PROTECT) — escrito únicamente por `InscripcionService`, nunca por un cliente de la API ni por ningún otro caller; `unique_together` pasa de `(colaborador, curso)` a `(colaborador, periodo)`.
- **`ProgresoTema`** (modificado) — gana `inscripcion` (FK a `Inscripcion`, PROTECT, NOT NULL); pierde `colaborador` directo; `unique_together` pasa de `(colaborador, tema)` a `(inscripcion, tema)`.
- **`ResultadoEvaluacion`** (modificado) — gana `inscripcion` (FK, PROTECT, NOT NULL); pierde `colaborador` directo; sin `unique_together` nueva (se mantienen múltiples intentos por inscripción, comportamiento ya existente e intencional).
- **`ContenidoBloqueRespuesta`** (modificado) — gana `inscripcion` (FK, PROTECT, NOT NULL); pierde `colaborador` directo; sin `unique_together` nueva (mismo motivo).
- **`CompetenciaCurso` / `CompetenciaColaborador` / `NivelCompetencia`** — sin cambios de esquema; solo cambia quién las invoca (`AcreditacionService` en vez del signal).

**Flujo principal** (spec: finalización automática con evaluaciones)

1. Colaborador llama a `InscripcionService.crear` dentro de un periodo abierto → se crea `Inscripcion(completado_at=None)`.
2. Colaborador avanza: cada llamada de progreso/respuesta/resultado pasa por `EvidenciaService`, que resuelve la inscripción activa, valida pertenencia al curso, guarda, y llama a `FinalizacionService.reevaluar`.
3. En la última llamada que completa el requisito, `reevaluar` detecta que se cumple el criterio, fija `completado_at`, y llama a `AcreditacionService.acreditar` — todo dentro de una sola transacción.
4. Cualquier llamada posterior a `reevaluar` sobre esa misma inscripción es un no-op observable.

- **Límites de consistencia:** la finalización + acreditación son atómicas entre sí (una sola transacción). La creación de evidencia y la re-evaluación de finalización ocurren en la misma request/transacción que el guardado que la dispara.

**Inventario de sitios que leen `Inscripcion.curso` directamente** (grep-verificado contra el código real, no hipotético) y su remediación decidida:

| Sitio | Qué asume hoy | Remediación decidida |
| --- | --- | --- |
| `competencias/signals.py:21` (pasa a ser `AcreditacionService`) | `CompetenciaCurso.objects.filter(curso=instance.curso, ...)` | Seguro una vez que `curso` esté sincronizado por construcción (Global Constraints) — sin cambio de lógica, solo prueba de sincronía. |
| `competencias/serializers.py:69` | `source='origen.curso.titulo'` | Igual — seguro por la misma garantía de sincronía. |
| `competencias/views.py:177` (`MiPerfilCompetenciasView`) | Diccionario `{curso_id: inscripcion}` que pisa silenciosamente una inscripción con otra si hay dos para el mismo curso | **Decidido:** mostrar la inscripción más reciente por curso (orden por `periodo.fecha_inicio`/`inscrito_at` descendente), nunca una arbitraria por orden de iteración. |
| `competencias/views.py:286-291, 303` (`MiInscripcionRutaPerfil`) | Trata "alguna vez inscrito a este curso" como completado; `get_or_create(colaborador=..., curso=...)` sin periodo | **Decidido:** la auto-inscripción por ruta de aprendizaje busca el periodo abierto más reciente de ese curso y se inscribe ahí vía `InscripcionService`; si no hay ninguno abierto, falla explícitamente — no crea un periodo por su cuenta. |
| `capacitacion/serializers/colaborador.py:155` (`get_inscrito`) | `exists()` sobre todas las inscripciones al curso, sin distinguir periodo | Se alinea con la misma noción de "inscripción más reciente" que `MiPerfilCompetenciasView`. |
| `capacitacion/serializers/colaborador.py:161-176` (`get_progreso`) | Suma progreso de TODAS las inscripciones al mismo curso en un solo porcentaje | **Decidido (consecuencia del punto anterior):** se calcula sobre la inscripción más reciente del colaborador a ese curso, no sobre la unión de todas. |
| `capacitacion/views.py:433-445` (`InscripcionViewSet`) + ausencia de `_scope_por_empresa` en `InscripcionViewSet`/`ProgresoTemaViewSet`/`ResultadoEvaluacionViewSet` | Filtro por `curso_id` de query param; sin aislamiento multi-empresa | **Diferido, fuera de este ciclo** (gap preexistente, no causado por esta feature) — se registra como hallazgo para una spec de scoping/seguridad separada, no se corrige aquí. |

- **Impacto de migración:** tabla nueva (`Periodo`); columna nueva NOT NULL (`Inscripcion.periodo`, `ProgresoTema.inscripcion`, `ResultadoEvaluacion.inscripcion`, `ContenidoBloqueRespuesta.inscripcion`); columnas eliminadas (`Inscripcion.curso`, `ProgresoTema.colaborador`, `ResultadoEvaluacion.colaborador`, `ContenidoBloqueRespuesta.colaborador`); cambio de `unique_together` en `Inscripcion` y `ProgresoTema`. **Sin backfill** — se asume base de desarrollo recreada antes de aplicar (Global Constraints).

## 5. Testing strategy

| Acceptance criterion (spec) | Nivel | Qué prueba | Qué simula |
| --- | --- | --- | --- |
| Inscripción rechazada sin periodo abierto | unit/integration | `InscripcionService.crear` devuelve `PeriodoNoAbierto` | Periodo real cerrado en BD, sin mocks |
| Inscripción duplicada al mismo periodo rechazada | integration | segunda llamada falla por `IntegrityError` capturado y traducido | BD real (MySQL), nada simulado — es justo lo que hay que probar contra el motor real |
| Repetir curso en periodo distinto crea inscripción independiente | integration | dos `Inscripcion` distintas, progreso no se mezcla | BD real |
| Progreso/resultado de dos inscripciones no se contaminan | integration | consultas filtradas por inscripción devuelven conjuntos disjuntos | BD real |
| Finalización automática exacta (con y sin evaluaciones) | unit | `FinalizacionService.reevaluar` fija `completado_at` exactamente cuando el criterio se cumple, no antes | Inscripción + progreso/resultados construidos en memoria/fixture, AcreditacionService real (no mockeado, es justo el seam a probar) |
| Finalización no se repite tras guardado incidental | unit | segunda llamada a `reevaluar` es no-op observable | — |
| Cambiar `CompetenciaCurso` no reacredita retroactivamente | **regression — reproduce el bug original** | se repite exactamente la secuencia del hallazgo de la auditoría (completar con nivel 2, subir `CompetenciaCurso` a nivel 3, volver a tocar la inscripción) y se afirma que el nivel permanece en 2 | BD real |
| Progreso/respuesta de contenido ajeno al curso de la inscripción rechazados | unit | `EvidenciaService` devuelve `ContenidoAjeno` | — |
| Colaborador no puede autofinalizarse ni fijar nivel | integration (API) | `PATCH` del colaborador sobre esos campos es ignorado/rechazado | Cliente DRF real, autenticado como colaborador |
| Concurrencia en creación de inscripción | integration | dos threads/transacciones concurrentes, como máximo una tiene éxito | BD real con `select_for_update` — **este es el único criterio que exige concurrencia real, no secuencial**, porque es precisamente lo que puede fallar solo bajo carrera real |
| Finalización manual excepcional por admin | unit/integration (API) | `FinalizacionService.forzar` produce el mismo resultado observable que una automática | — |
| Cerrar periodo no fuerza desenlace de inscripciones abiertas | integration | tras cerrar, progreso sigue aceptándose y la inscripción puede finalizar | BD real |

- **Línea del e2e:** no se añade e2e nuevo en este plan — las pruebas de integración contra MySQL real (vía `APIClient`/`TestCase`, como ya hace el resto del proyecto) son suficientes porque no hay frontend en este repositorio que probar end-to-end.
- **Lo que debe ser real, nunca mockeado:** el motor MySQL para toda prueba de restricción de unicidad/concurrencia (constitution §2.8: la prueba debe reproducir el `IntegrityError` real, no una suposición sobre si el constraint "debería" funcionar); la comparación de niveles de `AcreditacionService` en la prueba de finalización (es el seam que la auditoría demostró que estaba roto).

## 6. Sequencing & dependencies

1. Modelo `Periodo` + migración — depende de: ninguno — serial
2. `Inscripcion`: agregar `periodo` (NOT NULL), quitar `curso` almacenado, cambiar `unique_together`, exponer `curso` calculado en el serializer — depende de: #1 — serial
3. `InscripcionService` (crear, con bloqueo + traducción de `IntegrityError`) — depende de: #2 — serial
4. `ProgresoTema`: agregar `inscripcion`, quitar `colaborador`, cambiar `unique_together` — depende de: #2 — parallelizable con #5, #6
5. `ResultadoEvaluacion`: agregar `inscripcion`, quitar `colaborador` — depende de: #2 — parallelizable con #4, #6
6. `ContenidoBloqueRespuesta`: agregar `inscripcion`, quitar `colaborador` — depende de: #2 — parallelizable con #4, #5
7. `EvidenciaService` (resolución de inscripción activa + validación cruzada para los tres tipos de evidencia) — depende de: #4, #5, #6 — serial
8. `FinalizacionService.reevaluar` (criterio de finalización, idempotencia, transacción) — depende de: #7 — serial
9. Extraer `AcreditacionService` desde `competencias/signals.py`, eliminar el receptor `post_save`, conectar desde `FinalizacionService` — depende de: #8 — serial
10. `FinalizacionService.forzar` + endpoint administrativo de finalización excepcional — depende de: #9 — serial
11. Reconectar vistas/serializers existentes (`capacitacion/views.py`, `views_colaborador.py`) a los nuevos servicios en vez de a la creación directa de modelos — depende de: #3, #7, #10 — serial
12. Corregir `MiPerfilCompetenciasView` (competencias/views.py:177) para elegir la inscripción más reciente por curso en vez de colapsar por orden de iteración — depende de: #2, #3 — parallelizable con #13, #14
13. Corregir `MiInscripcionRutaPerfil` (competencias/views.py:286-303) para auto-inscribir vía `InscripcionService` en el periodo abierto más reciente del curso, fallando explícitamente si no hay ninguno — depende de: #3 — parallelizable con #12, #14
14. Corregir `get_inscrito`/`get_progreso` (capacitacion/serializers/colaborador.py:155-176) para operar sobre la inscripción más reciente del colaborador a ese curso, no sobre la unión de todas — depende de: #7 — parallelizable con #12, #13
15. Batería de pruebas de integridad y de regresión (tabla §5), incluyendo una prueba por cada sitio del inventario §4 que ahora depende de la sincronía `curso`/`periodo.curso` — intercalada con cada paso bajo TDD estricto (constitution §2.7), no es un paso final separado

- Candidatos paralelos reales: #4, #5, #6 (archivos y modelos disjuntos, sin estado compartido) — fan-out vía `../parallel/SKILL.md` si se desea.
- Restricción de orden dura: #9 debe ocurrir solo después de #8, porque `FinalizacionService` tiene que existir antes de poder moverle la lógica de acreditación encima — hacerlo al revés deja una ventana donde la acreditación no se dispara desde ningún lado.

## 7. Risks & open decisions

**Risks**

| Risk | Trigger | Impact | Mitigation / spike |
| --- | --- | --- | --- |
| Eliminar el `colaborador` FK directo de `ProgresoTema`/`ResultadoEvaluacion`/`ContenidoBloqueRespuesta` rompe silenciosamente consultas existentes que filtran por ese campo | `implement` olvida actualizar una vista/serializer que hace `filter(colaborador=request.user)` directamente sobre esos modelos | Un colaborador deja de ver su propio progreso/resultados (regresión funcional, no solo de esquema) | Tarea #11 incluye grep exhaustivo de `colaborador=` sobre estos tres modelos en `views_colaborador.py` antes de cerrarse; prueba de regresión por cada vista afectada |
| `Inscripcion.curso` y `Inscripcion.periodo.curso` divergen porque algo distinto de `InscripcionService` escribe `curso` | Un nuevo endpoint, un fixture de test, o un script de datos crea/actualiza una `Inscripcion` pasando por el ORM directo en vez del servicio | Los 7 sitios del inventario §4 (acreditación, perfil, auto-inscripción por ruta, progreso) producen resultados silenciosamente incorrectos — sin excepción, sin log | `curso` se excluye de `fields` escribibles en todo serializer de `Inscripcion` (solo lectura); prueba explícita que intenta crear una `Inscripcion` con `curso` y `periodo.curso` distintos y confirma que es rechazada o que `curso` es ignorado y sobrescrito por el valor correcto |
| Las correcciones de `MiPerfilCompetenciasView`/`MiInscripcionRutaPerfil`/`get_progreso` (tareas #12-14) cambian comportamiento ya observable hoy (p. ej. un colaborador que hoy ve "ya completado" en una ruta de aprendizaje) | Un colaborador con inscripciones múltiples al mismo curso, antes y después de este cambio | El resultado observable de estas 3 vistas cambia para usuarios con datos preexistentes — aceptado porque los datos de desarrollo son descartables (Global Constraints), pero a tener en cuenta si esto migra a un entorno con datos reales | Ya cubierto por Global Constraints (datos de prueba descartables); si en el futuro hay datos reales, este riesgo debe reevaluarse antes de aplicar |
| Dos requests concurrentes intentan finalizar la misma inscripción al mismo tiempo (p. ej. dos escrituras de evidencia casi simultáneas) | Carga real de usuarios, no solo un test secuencial | Doble ejecución de `AcreditacionService` si la idempotencia falla bajo carrera | `select_for_update` sobre la fila de `Inscripcion` dentro de `reevaluar`/`forzar`, probado con una prueba de concurrencia real (tabla §5) |
| Migraciones que eliminan columnas NOT NULL sin backfill fallan si la base de desarrollo no se recrea primero | Alguien aplica las migraciones sobre una base con datos de prueba antiguos | Migración falla a mitad de camino, estado inconsistente | Paso operativo explícito antes de aplicar: recrear/limpiar la base de desarrollo (Global Constraints) — documentarlo en la tarea de migración, no asumirlo implícito |

**Open decisions**

Ninguna decisión arquitectónica queda genuinamente abierta para este plan — las dos áreas no resueltas de la spec (bitácora histórica de niveles, interacción con gating granular futuro) son explícitamente posponibles y no bloquean este diseño.
