# Auditoría técnica — autoguardado, historial, previsualización, concurrencia

Auditoría del backend (`capacitacion`, `catalogos`) frente a 7 capacidades requeridas por el
constructor visual: autoguardado, historial/deshacer, previsualización, concurrencia,
persistencia de anidados, catálogo dinámico, integridad. Solo diagnóstico — **no se tocó código
en esta fase**.

---

## Resumen ejecutivo

| Capacidad | Estado | Riesgo si no se toca |
|---|---|---|
| Guardado automático (PATCH parcial) | ✅ Ya funciona | — |
| Idempotencia en creación | 🟡 Parcial | Bajo — duplicados visibles y corregibles a mano |
| Historial / deshacer en sesión | ✅ Ya funciona (responsabilidad de Next.js) | — |
| Historial persistente / revisiones | ❌ No existe | Medio — sin forma de recuperar una versión anterior del contenido |
| Previsualización sin efectos secundarios | ✅ Ya es posible (100% client-side) | — |
| Concurrencia (dos editores, mismo bloque) | ❌ No existe | **Alto** — "last write wins" silencioso |
| Persistencia de elementos anidados | ✅ Ya funciona, arquitectura correcta | — |
| Catálogo dinámico de tipos | ✅ Ya funciona | — |
| Integridad referencial (borrados) | ✅ Fuerte (PROTECT en cascada) | — |
| Borrador/publicado real | ❌ No enforced | Medio — curso en "Borrador" visible para colaboradores |

Dos hallazgos concentran casi todo el trabajo pendiente: **no hay concurrencia optimista** y
**no hay historial persistente**. Todo lo demás ya está resuelto por la arquitectura actual o es
responsabilidad de Next.js.

---

## Fase 2 — Guardado automático

**Evidencia**: `ModelViewSet` de DRF llama `partial_update()` con `partial=True` automáticamente
en todo `PATCH` (comportamiento de `rest_framework.mixins.UpdateModelMixin`, no hay override en
ningún ViewSet de `capacitacion/views.py` que lo deshabilite). Verificado en
`capacitacion/tests/test_empresa_scoping.py::test_admin_de_otra_empresa_no_puede_borrar_bloque_ajeno`
y en el uso real del endpoint durante esta sesión: un `PATCH {"titulo": "x"}` nunca borra
`descripcion`, `status`, etc.

- **PATCH parcial seguro**: ✅ ya funciona, campos no enviados se preservan.
- **Validaciones que bloqueen guardados parciales**: no se encontraron — ninguno de los
  serializers (`ContenidoBloqueSerializer`, `ModuloSerializer`, `TemaSerializer`, etc.) tiene
  `validate()` a nivel de objeto que exija campos cruzados en un PATCH parcial, salvo
  `Evaluacion.clean()` (curso XOR módulo), que no aplica a bloques.
- **Atomicidad**: cada `PATCH`/`POST`/`DELETE` individual ya es atómico (una sola fila, una sola
  sentencia SQL envuelta por Django). El único caso multi-fila es el reorder en lote, que **ya**
  usa `transaction.atomic()` (`capacitacion/views.py::_reordenar_en_lote`).
- **Idempotencia en creación**: 🟡 parcial.
  - Para hijos ordenados (`ContenidoBloqueItem`, `ContenidoBloqueArchivo`, `ContenidoBloqueOpcion`,
    `ContenidoBloque` mismo vía `unique_together(tema, orden)` / `unique_together(bloque, orden)`):
    un reintento de red que reenvíe el mismo `orden` falla con `400` en vez de duplicar
    silenciosamente — protección natural ya presente.
  - Para `Curso` (sin unicidad en `titulo`): un doble-POST por timeout de red sí crea dos cursos
    idénticos. Bajo impacto (visible y borrable a mano), pero es un gap real.
- **Estados de guardando/guardado/error**: la API ya expone todo lo necesario (`200`/`201` en
  éxito, `400` con body `{"campo": ["mensaje"]}` en validación fallida) — es responsabilidad de
  Next.js mapear eso a estados de UI, no requiere nada nuevo del backend.

**Conclusión**: el contrato actual **ya soporta autoguardado con debounce** desde Next.js sin
cambios. Documentado en la sección "Cómo debe consumirlo Next.js" más abajo.

---

## Fase 3 — Historial de cambios y deshacer

**Evidencia**: `grep` de `simple-history`/`reversion`/`auditlog` en `requirements.txt` → nada.
`SoftDeleteModel` (`common/models.py`) existe y lo usan `Departamento`, `Puesto`, `Competencia`,
`CompetenciaCurso`, `CompetenciaPuesto`, `RutaAprendizaje` — **pero NO** `Curso`, `Modulo`, `Tema`,
`ContenidoBloque`, `ContenidoBloqueItem`, `ContenidoBloqueArchivo`, `ContenidoBloqueOpcion` (todos
heredan `BaseModel`, que no tiene soft-delete). Confirmado también de forma práctica: al intentar
borrar un `ContenidoBloque` con una `ContenidoBloqueRespuesta` asociada, Django lanza
`ProtectedError` en vez de permitir el borrado (lo viví literalmente limpiando datos de prueba en
la sesión anterior) — es decir, **no hay soft-delete, el borrado de contenido de autoría es físico
e irreversible**, y además `BaseFileEntity.delete()` (usado por `ContenidoBloqueArchivo`) borra el
archivo del disco en el mismo paso.

### Nivel A — Deshacer/rehacer durante la edición

No requiere nada del backend. El frontend mantiene su pila de acciones (texto tecleado, bloque
movido, ítem borrado) **en memoria/estado local**, y solo persiste contra el backend cuando el
usuario confirma o cuando dispara el autoguardado. Las operaciones actuales (`PATCH` idempotente,
`DELETE` con reindexado automático, reorder en lote atómico) son perfectamente compatibles: un
"deshacer" de frontend simplemente vuelve a emitir las llamadas inversas (recrear lo borrado,
reordenar de vuelta, etc.).

### Nivel B — Historial persistente

❌ No existe ningún mecanismo. Para no sobre-ingenierizar (el prompt pide explícitamente no hacer
snapshot por cada tecla), la recomendación es:

- Agregar un modelo de revisión **a nivel de `Tema`** (no por bloque individual) que capture un
  snapshot serializado (JSON, usando `ContenidoBloqueSerializer` existente sobre todos los bloques
  del tema) en puntos de guardado explícitos: al publicar, o cada N minutos de edición activa
  (controlado por el frontend, que decide cuándo "vale la pena" un punto de restauración).
- Campos mínimos: `tema`, `creado_por`, `creado_at`, `snapshot` (JSON), sin campo "versión" per se
  — el historial es una lista ordenada por `creado_at`.
- Restaurar = reemplazar el árbol de bloques del tema con el contenido del snapshot, dentro de una
  transacción atómica (borrar bloques actuales del tema + recrearlos desde el JSON). Como
  `ContenidoBloqueRespuesta`/`ContenidoBloqueOpcion` usan `PROTECT` hacia `ContenidoBloque`, restaurar
  un tema que ya tiene respuestas de alumnos sobre sus bloques evaluativos **fallaría** con el
  comportamiento actual — hay que decidir explícitamente la política (¿se bloquea la restauración,
  o se migran las respuestas al nuevo bloque equivalente?). Esto es una decisión de producto, no
  técnica, y debe resolverse antes de implementar el Nivel B.
- Retención: sugerido 20-30 revisiones por tema o 90 días, lo que ocurra primero (barato en
  almacenamiento porque es JSON de texto, no archivos).

**Prioridad**: Nivel A ya está resuelto (frontend). Nivel B es una mejora recomendada, no
indispensable para cerrar el constructor — puede posponerse a una iteración siguiente.

---

## Fase 4 — Previsualización del alumno

**Evidencia clave**: el serializer admin (`ContenidoBloqueSerializer`) ya anida `opciones` **con**
`es_correcta` en la misma respuesta que usa el editor para construir el bloque
(`capacitacion/serializers/curso.py`). Es decir, cuando un administrador abre el editor de un
tema, **ya tiene en el cliente todo el contenido necesario para simular la experiencia completa**
del alumno, incluyendo qué opción es correcta — sin necesidad de ninguna llamada adicional al
backend.

- Los endpoints de progreso real (`/mis-inscripciones/`, `/mis-progresos/`, `/mis-resultados/`,
  `/mis-respuestas-bloque/`) están completamente aislados de los endpoints admin — usan
  `request.user` como el colaborador que escribe, no hay forma de que una llamada a
  `/api/capacitacion/bloques/` (admin) dispare un efecto secundario sobre esas tablas.
- El único riesgo real es **operacional, no de arquitectura**: si el frontend, para "simular" un
  clic en una opción durante la previsualización, llamara por error a
  `POST /api/capacitacion/mis-respuestas-bloque/` usando la sesión del propio administrador (que
  también es un `UserCustomize` autenticable como colaborador), **sí crearía un intento real** en
  la base de datos, contaminando datos de uso real con pruebas del autor. No hay nada en el backend
  que distinga "este request es una previsualización" de "este es un intento real" porque
  identidad de admin y de colaborador es la misma tabla de usuario.
- No hay estados de publicación enforced (`CatalogStatus` en `Curso.status` es solo una etiqueta;
  ver Fase 7/hallazgo de integridad más abajo) — así que un admin ya puede consultar contenido en
  cualquier estado vía los endpoints admin sin restricción, lo cual es correcto para autoría.

**Conclusión — la opción preferida del prompt ya es viable sin cambios**: la previsualización se
resuelve 100% en el frontend, renderizando con los datos ya autorizados del editor
(`ContenidoBloqueSerializer`), sin llamar nunca a los endpoints de progreso/intentos reales. La
única "implementación" necesaria es una **regla de contrato**, no de código: *el modo
previsualización del frontend tiene prohibido llamar a cualquier endpoint bajo
`/mis-inscripciones/`, `/mis-progresos/`, `/mis-resultados/` o `/mis-respuestas-bloque/`*. Se deja
documentado en la sección de contrato actualizado.

---

## Fase 5 — Control de concurrencia

**Evidencia**: `grep` de `select_for_update`, `F()`, `ETag`, `If-Match` en todo `capacitacion` y
`catalogos` → cero resultados. `BaseModel` (heredado por `Curso`/`Modulo`/`Tema`/`ContenidoBloque`/
`ContenidoBloqueItem`/`ContenidoBloqueArchivo`/`ContenidoBloqueOpcion`) solo tiene `creado_at`,
`actualizado_at` (`auto_now=True`), `activo` — ningún campo de versión.

- El reorder en lote (`_reordenar_en_lote`) es atómico **dentro de una sola operación** (mueve N
  filas sin inconsistencia entre sí), pero **no protege contra dos reorders concurrentes del mismo
  tema**: si Admin A reordena mientras Admin B también reordena el mismo tema, ambas transacciones
  aplican su propio orden final sin detectar al otro — el último `COMMIT` gana, silenciosamente.
  Esto es exactamente lo que el prompt advierte no confundir: atomicidad de una operación ≠
  prevención de conflictos entre operaciones distintas.
- Un `PATCH` simple de `texto` en un bloque, hecho por dos admins casi al mismo tiempo, sufre el
  clásico *lost update*: el segundo `PATCH` sobrescribe el primero sin que nadie se entere, porque
  no hay ninguna verificación de que el recurso siga en el estado que el segundo editor cree que
  tiene.

**Buena noticia**: `actualizado_at` (`auto_now=True`) **ya existe en todos los modelos relevantes**
— es la pieza que falta exponer y verificar, no un campo nuevo que agregar.

### Propuesta mínima (concurrencia optimista basada en timestamp, no un campo `version` nuevo)

1. Exponer `actualizado_at` en la respuesta de cada recurso editable (`Curso`, `Modulo`, `Tema`,
   `ContenidoBloque`, `ContenidoBloqueItem`, `ContenidoBloqueArchivo`, `ContenidoBloqueOpcion`) — ya
   está expuesto en casi todos salvo que haya que confirmarlo campo por campo.
2. El frontend guarda el `actualizado_at` recibido al cargar el recurso.
3. Al hacer `PATCH`, lo reenvía como header `If-Unmatch-Since: <actualizado_at recibido>` (o un
   campo `ultima_version_vista` en el body — header es más limpio porque no contamina el payload
   del recurso).
4. El backend, antes de aplicar el `PATCH`, compara ese valor contra el `actualizado_at` actual en
   base de datos **dentro de una transacción con `select_for_update()`** sobre esa fila:
   - Si coincide: aplica el cambio (que naturalmente actualiza `actualizado_at` de nuevo).
   - Si no coincide: responde `409 Conflict` con body
     `{"detail": "El recurso fue modificado por otro usuario.", "actualizado_at_actual": "...", "actualizado_por": "..."}`
     sin aplicar el cambio.
5. Esto se implementa como **un mixin reutilizable** (`OptimisticConcurrencyMixin` sobre
   `perform_update`), aplicado a los ViewSets de `Curso`/`Modulo`/`Tema`/`ContenidoBloque`/
   `ContenidoBloqueItem`/`ContenidoBloqueArchivo`/`ContenidoBloqueOpcion` — no hay que tocar cada
   uno manualmente.
6. Para el reorder en lote, la misma idea aplica a nivel de grupo: aceptar opcionalmente un
   `actualizado_at` esperado del *padre* (el `Tema`/`Bloque` que agrupa), y usar
   `select_for_update()` sobre las filas del grupo durante el reorder (hoy no lo usa, ver
   `_reordenar_en_lote`) para que un segundo reorder concurrente quede bloqueado hasta que el
   primero termine, en vez de competir sin orden.

**Por qué esto y no un campo `version` entero nuevo**: usar el timestamp ya existente evita una
migración de datos para backfillear un contador en todas las filas existentes, y evita duplicar
información (`actualizado_at` ya cumple semánticamente el mismo rol que un `version` incremental
para este propósito). Es la "extensión pequeña" que pide el prompt, no una reescritura.

**Prioridad**: 🔴 alta — es el único hallazgo que puede corromper trabajo real de un editor sin que
nadie se entere.

---

## Fase 6 — Persistencia de elementos anidados

**Confirmado**: la arquitectura actual (bloque padre vía `/bloques/`, hijos vía endpoints
independientes `/bloque-items/`, `/bloque-archivos/`, `/bloque-opciones/`, todos anidados
*solo en lectura* dentro de la respuesta del bloque) ya es sólida y **se preserva** — coincide con
la instrucción explícita del prompt de no tocarla sin justificación técnica, y no encontré ninguna.

### Cómo debe coordinar Next.js (contrato de secuencia, no cambia nada del backend)

Para un bloque nuevo con hijos (ej. `texto-tarjetas` con 3 tarjetas):

```
1. POST /api/capacitacion/bloques/                → crea el bloque padre, obtiene {id}
2. POST /api/capacitacion/bloque-items/ (x3)       → crea cada tarjeta referenciando el {id} del paso 1
3. (opcional) PATCH /api/capacitacion/bloque-items/reordenar/  → si el usuario reordena antes de terminar
```

Para editar contenido existente:

```
PATCH /api/capacitacion/bloques/<id>/              → edita texto/variante del padre (autoguardado)
PATCH /api/capacitacion/bloque-items/<item_id>/    → edita un ítem puntual (autoguardado independiente)
DELETE /api/capacitacion/bloque-items/<item_id>/   → el backend reindexa automáticamente los `orden` restantes
```

Resincronización: tras cualquier operación sobre hijos, el frontend puede optar por **no** volver a
pedir el bloque completo — ya tiene la respuesta de cada operación individual. Si necesita
refrescar todo (ej. tras un error), `GET /api/capacitacion/bloques/<id>/` devuelve el bloque con
`bloque_items`/`archivos`/`opciones` ya anidados y actualizados, en una sola llamada.

**¿Necesita soporte transaccional adicional (crear bloque + items en una sola llamada)?**
No se recomienda. El riesgo de que el paso 1 tenga éxito y el paso 2 falle a medias es bajo
impacto (un bloque con menos tarjetas de las esperadas, visualmente detectable y corregible
agregando las que falten) — no es corrupción de datos, es contenido incompleto editable. Introducir
escritura anidada atómica aquí es la complejidad que el prompt pide evitar cuando no se justifica.

---

## Fase 7 — Catálogo dinámico de tipos

Ya documentado en profundidad en `docs/CONTRATO_BLOQUES_FRONTEND.md` §2. Resumen de lo verificado
en esta auditoría:

- **`codigo`**: `SlugField(unique=True)` heredado de `BaseCatalogo` — unicidad garantizada a nivel
  de base de datos, no solo por convención.
- **Compatibilidad con bloques antiguos**: cada `TipoBloqueContenido` tiene `version_esquema`
  (`PositiveSmallIntegerField`, default `1`). Hoy **ningún** `ContenidoBloque` individual guarda
  con qué versión de esquema fue creado — el campo vive en el catálogo, no en la instancia. Esto es
  suficiente mientras no haya habido ningún cambio de esquema real todavía (todos están en v1), pero
  en el momento en que se suba la versión de un tipo (ej. se agregan campos nuevos a
  `texto-tarjetas`), **las instancias viejas no tendrán forma de saber con qué versión fueron
  creadas**. Recomendación (mejora, no indispensable ahora): agregar `version_esquema` también en
  `ContenidoBloque` (copiado del tipo al crear la instancia), para que el frontend pueda detectar
  "este bloque fue creado con una versión de esquema anterior" y decidir si migrarlo o advertir.
- **17 tipos en catálogo, 15 de contenido/estructura + 2 evaluativos** (`opcion-multiple`,
  `verdadero-falso`) — confirmado, no se tocaron ni deshabilitaron en esta auditoría.
- El catálogo ya es suficiente para que Next.js construya biblioteca + formularios + seleccione
  renderizador por `tipo_codigo`, sin necesitar metadatos adicionales para los tipos actuales.

---

## Hallazgo adicional de integridad (fuera del alcance explícito, pero relevante a Fase 4)

`CursoColaboradorViewSet`/`MisCursosViewSet` (`capacitacion/views_colaborador.py`, función
`_base_cursos_qs`) filtran solo por `activo=True`, **no por `status`** — un curso en estado
"Borrador" (`CatalogStatus.codigo == "borrador"`) es visible para cualquier colaborador igual que
uno "Publicado". Esto ya se había identificado en una auditoría anterior de esta misma iniciativa
y sigue sin corregirse. No es parte de las 7 capacidades pedidas directamente, pero sí responde a
la pregunta de Fase 4 "¿existen estados de publicación [enforced]?" → no. Se incluye en la matriz
como ítem de prioridad media.

---

# Entregable A — Matriz de auditoría

| Capacidad | Estado actual | Evidencia | Riesgo | Recomendación | Prioridad | Archivos afectados |
|---|---|---|---|---|---|---|
| PATCH parcial preserva campos | ✅ Implementado | `UpdateModelMixin.partial_update` sin override | — | Ninguna | — | — |
| Idempotencia en hijos ordenados | ✅ Implementado (efecto colateral de diseño) | `unique_together` en `ContenidoBloque`/`Item`/`Archivo`/`Opcion` | Bajo | Documentar como contrato | Baja | `capacitacion/models/curso.py` |
| Idempotencia en `Curso`/`Modulo`/`Tema` | 🟡 Parcial | Sin unique constraint relevante | Bajo | Opcional: idempotency key en frontend | Baja | `capacitacion/models/curso.py` |
| Deshacer en sesión | ✅ Responsabilidad de Next.js, backend compatible | Operaciones ya idempotentes/atómicas | — | Documentar contrato | — | — |
| Historial persistente / revisiones | ❌ No existe | Sin `simple-history`, sin modelo de revisión | Media | Modelo `TemaRevision` con snapshot JSON en puntos de guardado | Media (posponible) | nuevo modelo en `capacitacion` |
| Soft-delete de contenido | ❌ No existe (hard delete + `PROTECT` donde hay datos reales) | `BaseModel` sin soft-delete; `BaseFileEntity.delete()` borra archivo físico | Media | Evaluar `SoftDeleteModel` en `ContenidoBloque`/`Item`/`Archivo` si se requiere "papelera" | Media (posponible) | `capacitacion/models/curso.py` |
| Previsualización sin efectos secundarios | ✅ Ya posible 100% client-side | `ContenidoBloqueSerializer` admin ya incluye todo, incl. `es_correcta` | Baja (solo si el frontend llama mal el endpoint) | Regla de contrato: prohibir llamadas a endpoints `/mis-*` en modo preview | Alta (es solo documentación) | `docs/CONTRATO_BLOQUES_FRONTEND.md` |
| Estados de publicación enforced | ❌ No existe | `_base_cursos_qs` solo filtra `activo=True` | Media | Agregar filtro `status__codigo='publicado'` en endpoints colaborador | Media | `capacitacion/views_colaborador.py` |
| Concurrencia optimista (PATCH simple) | ❌ No existe | Sin `select_for_update`, sin verificación de versión | **Alta** | Mixin `actualizado_at` + `If-Unmodified-Since` + `select_for_update` + `409` | **Alta** | `capacitacion/views.py` (todos los ViewSets admin) |
| Concurrencia en reorder en lote | 🟡 Atómico intra-operación, no inter-operación | `_reordenar_en_lote` sin `select_for_update` | Media | Agregar `select_for_update()` sobre el grupo dentro de la transacción | Alta | `capacitacion/views.py::_reordenar_en_lote` |
| Persistencia de elementos anidados | ✅ Arquitectura correcta, sin cambios | Endpoints independientes + anidado de solo lectura | — | Documentar secuencia de coordinación | Baja (solo doc) | `docs/CONTRATO_BLOQUES_FRONTEND.md` |
| Integridad referencial en borrados | ✅ Fuerte | `PROTECT` en `ContenidoBloqueRespuesta`, `Inscripcion`, `ProgresoTema`, `ResultadoEvaluacion` — verificado en pruebas reales | — | Ninguna | — | — |
| Catálogo dinámico — `codigo` estable | ✅ Implementado | `SlugField(unique=True)` | — | Ninguna | — | — |
| Catálogo dinámico — versión por instancia | ❌ No existe (solo a nivel de tipo) | `version_esquema` solo en `TipoBloqueContenido` | Baja mientras no cambie ningún esquema | Copiar `version_esquema` al crear la instancia | Baja (posponible) | `capacitacion/models/curso.py` |

---

# Entregable B — Propuesta de arquitectura (qué vive dónde)

**En Django (fuente de verdad, sin cambios de responsabilidad):**
- Persistencia, orden, integridad referencial, catálogo de tipos, permisos/scoping por empresa,
  cálculo server-side de corrección de respuestas — todo esto ya vive correctamente en el backend
  y así debe seguir.
- Nuevo (Fase 5): verificación de concurrencia optimista en `perform_update` — es lógica de
  integridad de datos, pertenece al backend.
- Nuevo (opcional, Fase 3 Nivel B): modelo de revisión/snapshot — persistencia, pertenece al
  backend.

**En Next.js (sin requerir nada nuevo del backend):**
- Pila de deshacer/rehacer en memoria durante la sesión de edición (Fase 3 Nivel A).
- Debounce del autoguardado (cuándo disparar el `PATCH`, no si el `PATCH` es seguro — ya lo es).
- Renderizado de la previsualización completa a partir de los datos admin ya cargados, sin tocar
  endpoints de progreso (Fase 4).
- Manejo de `409 Conflict` cuando se implemente concurrencia optimista: mostrar al usuario "este
  contenido cambió, ¿recargar o sobrescribir?" — decisión de UX, no de datos.
- Registro de componentes React por `tipo_codigo` (ya contemplado en el contrato anterior, el
  catálogo nunca debe guardar JSX/componentes).

---

# Entregable C — Cambios mínimos necesarios

### Correcciones indispensables (antes de cerrar el backend)
1. **Concurrencia optimista** en los ViewSets admin de `Curso`/`Modulo`/`Tema`/`ContenidoBloque`/
   `ContenidoBloqueItem`/`ContenidoBloqueArchivo`/`ContenidoBloqueOpcion` — mixin reutilizable sobre
   `actualizado_at`, sin campo nuevo.
2. **`select_for_update()`** dentro de `_reordenar_en_lote` para que dos reorders concurrentes del
   mismo grupo no compitan sin control.

### Mejoras recomendadas (siguiente iteración, no bloquean el cierre)
3. Filtrar `status__codigo='publicado'` en endpoints de colaborador (hallazgo de integridad,
   relacionado con Fase 4/7 pero no pedido explícitamente en esta auditoría).
4. `version_esquema` copiado a nivel de instancia en `ContenidoBloque`.
5. Idempotency key opcional para creación de `Curso`/`Modulo`/`Tema` (bajo impacto, no urgente).

### Funcionalidades que pueden posponerse
6. Historial persistente (Fase 3 Nivel B) — requiere antes una decisión de producto sobre qué pasa
   al restaurar un tema con respuestas de alumnos ya registradas.
7. Soft-delete de contenido de autoría (papelera/recuperar bloques borrados) — hoy el borrado es
   físico; si se requiere "recuperar", es prerequisito del punto 6 en la práctica (un snapshot
   sirve también como papelera).

---

# Entregable D — Contrato actualizado (deltas sobre `CONTRATO_BLOQUES_FRONTEND.md`)

Estos cambios **no están implementados todavía** — se documentan aquí como el contrato objetivo
una vez aplicados los cambios indispensables del Entregable C.

### Concurrencia optimista

Todo `GET` de un recurso editable ya incluye `actualizado_at`. Al editar:

```
PATCH /api/capacitacion/bloques/<id>/
Headers: If-Unmodified-Since: 2026-11-07T10:15:00.000Z   (el actualizado_at que el cliente tiene)
Body: { "texto": "nuevo contenido" }
```

Respuestas:

- `200` — se aplicó, el body incluye el nuevo `actualizado_at`.
- `409 Conflict` — alguien más editó el recurso primero:

```json
{
  "detail": "El recurso fue modificado por otro usuario.",
  "actualizado_at_actual": "2026-11-07T10:16:42.000Z"
}
```

Si el cliente **no** manda `If-Unmodified-Since`, se mantiene el comportamiento actual
(sobrescribe sin verificar) — así no rompe a ningún consumidor existente mientras el frontend migra.

### Previsualización (regla de contrato, sin endpoint nuevo)

El modo previsualización de Next.js debe:
- Usar únicamente los endpoints admin (`/api/capacitacion/bloques/`, etc.), que ya incluyen
  `es_correcta` en `opciones`.
- **Nunca** llamar a `/api/capacitacion/mis-inscripciones/`, `/mis-progresos/`, `/mis-resultados/`
  ni `/mis-respuestas-bloque/` durante una sesión de previsualización, bajo ninguna circunstancia.
- Simular la interacción (seleccionar una opción, ver si es correcta) completamente en el cliente,
  ocultando `es_correcta` en la UI hasta que el usuario "responda" dentro de la simulación.

### Reorder con bloqueo de fila

`PATCH .../reordenar/` pasa a tomar `select_for_update()` sobre las filas del grupo durante la
transacción — comportamiento transparente para el cliente (mismo request/response), solo cambia
que un segundo reorder concurrente del mismo grupo espera a que el primero termine en vez de
competir.

---

# Entregable E — Plan de implementación

| Fase | Contenido | Depende de | Riesgo técnico |
|---|---|---|---|
| 1 | Mixin de concurrencia optimista + `select_for_update` en reorder | Ninguna | Bajo — aditivo, no rompe clientes sin `If-Unmodified-Since` |
| 2 | Filtro `status='publicado'` en endpoints colaborador | Ninguna | Medio — verificar que no rompa cursos ya en producción sin `status` correcto |
| 3 | `version_esquema` a nivel de instancia | Ninguna | Bajo — migración aditiva |
| 4 | Decisión de producto: política de restauración de historial vs. respuestas de alumnos | — | — (bloqueante para Fase 5) |
| 5 | Modelo de revisión por `Tema` + endpoint de listado/restauración | Fase 4 | Medio — transacción de restauración debe manejar el `PROTECT` de `ContenidoBloqueRespuesta` |
| 6 | Soft-delete de contenido de autoría (si Fase 5 lo requiere como papelera) | Fase 5 | Medio — migración de `BaseModel` a `SoftDeleteModel` en varios modelos, revisar cascadas |

Fases 1-3 son independientes entre sí y pueden ir en paralelo. Fases 4-6 son una iniciativa
separada (historial), explícitamente posponible según el Entregable C.
