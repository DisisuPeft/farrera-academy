# Revisión de decisiones — concurrencia, historial y publicación

Responde punto por punto a la crítica sobre `docs/AUDITORIA_AUTOGUARDADO_CONCURRENCIA.md`. **No se
tocó código en este documento** — solo diagnóstico y decisión técnica, con evidencia nueva
obtenida corriendo contra la base real (no especulación). Este documento **revisa y reemplaza**
las conclusiones de Fase 3 (historial) y Fase 5 (concurrencia) del documento anterior, y precisa el
hallazgo de publicación.

---

## 1. Concurrencia optimista — cambio de recomendación: `revision` (entero) + ETag/If-Match, NO timestamp

### Evidencia que invalida mi propuesta anterior

Probé empíricamente el patrón que ya usa `_reordenar_en_lote` (`obj.save(update_fields=['orden'])`)
contra un `ContenidoBloque` real:

```
actualizado_at antes:                                    2026-11-07 05:27:18.189304+00:00
actualizado_at después de save(update_fields=['orden']):  2026-11-07 05:27:18.189304+00:00
¿se movió el timestamp?                                   False
```

**`auto_now=True` no se dispara si el campo no está en `update_fields`.** Mi propuesta anterior de
usar `actualizado_at` como token de concurrencia está rota por el propio código existente: cualquier
`save(update_fields=[...])` que no incluya explícitamente el campo de timestamp lo deja
congelado — exactamente el patrón que usa el reorder hoy. Dos problemas adicionales, independientes
de este bug:

- **`If-Unmodified-Since` (RFC 7231/7232) tiene resolución de 1 segundo** — es un `HTTP-date`, no
  admite microsegundos. Dos PATCH del mismo bloque dentro del mismo segundo (plausible con
  autoguardado por debounce corto, o dos admins haciendo clic casi a la vez) no se podrían
  distinguir con ese header, aunque la base de datos sí tenga precisión de microsegundos.
- Comparar timestamps como string exacto entre un `Date` de JavaScript serializado y un
  `DateTimeField` de Django es frágil (formatos `Z` vs `+00:00`, truncamiento de decimales
  distinto entre clientes).

### Decisión: contador entero `revision` + `ETag`/`If-Match` (estándar HTTP, no header custom)

El estándar HTTP correcto para esto **ya existe y es `ETag` + `If-Match`** (RFC 7232 §3.1) — es
literalmente el mecanismo que la especificación recomienda para "evitar perder actualizaciones"
cuando se tiene un validador fuerte disponible (que sí tenemos: un entero). `Last-Modified` /
`If-Unmodified-Since` está pensado para validadores débiles basados en tiempo, no para esto. Por
eso la recomendación cambia de header custom a header estándar.

**Campo nuevo**: `revision = models.PositiveIntegerField(default=1)`, agregado — no a `BaseModel`
(blast radius innecesario sobre modelos no relacionados con el constructor) — sino directamente a
los 7 modelos que participan en edición concurrente: `Curso`, `Modulo`, `Tema`, `ContenidoBloque`,
`ContenidoBloqueItem`, `ContenidoBloqueOpcion`, y `ContenidoBloqueArchivo` (este último vía
`BaseFileEntity`, que no hereda `BaseModel`, así que necesita el campo por separado igual que ya
necesita su propia definición de `activo`/`creado_at` — ver nota ya documentada en el contrato).
`ContenidoBloqueRespuesta` queda fuera: es inmutable por diseño (sin `PATCH`), no tiene con qué
colisionar.

### Comportamiento exacto

- **Respuesta** (`GET`/`POST`/`PATCH`): header `ETag: "5"` + también el campo `"revision": 5` en el
  body JSON (duplicado deliberado: el header es lo HTTP-correcto, el campo en el body es porque un
  cliente Next.js leyendo `response.headers.get('ETag')` en cada fetch es más fricción que leer
  `data.revision` del JSON que ya está parseando).
- **Request condicional**: `PATCH` con header `If-Match: "5"`.
  - Si `revision` actual en BD == 5 → aplica el cambio, incrementa `revision` a 6, responde `200`
    con el nuevo `ETag`/`revision`.
  - Si no coincide → **`412 Precondition Failed`** (no `409` — RFC 7232 §3.1 es explícito: ante un
    `If-Match` que no calza, el servidor "MUST NOT perform the requested method and MUST return a
    412"). Body: `{"detail": "El recurso fue modificado por otro usuario.", "revision_actual": 6}`.
  - Si el recurso ya no existe → `404` (más claro para el cliente que forzar un 412 sobre algo
    inexistente).
  - `If-Match: "*"` (comodín del RFC) soportado de forma trivial si se quiere "aplicar solo si el
    recurso todavía existe, sin importar la revisión" — no es necesario para v1, queda documentado
    por si se necesita.
- **Sin `If-Match` en el request**: comportamiento actual sin cambios (sobrescribe sin verificar).
  Esto es clave para no romper clientes existentes — el header es opcional en el rollout inicial;
  se puede exigir más adelante (`428 Precondition Required` si falta) una vez que el frontend
  migre, como paso posterior, no ahora.

### Atomicidad de la verificación + escritura

La comparación y el incremento **deben** ocurrir dentro de la misma transacción con bloqueo de
fila, no como dos pasos separados:

```python
with transaction.atomic():
    obj = Modelo.objects.select_for_update().get(pk=pk)
    if if_match is not None and if_match != f'"{obj.revision}"':
        raise PreconditionFailed(revision_actual=obj.revision)
    # aplicar los campos del PATCH + obj.revision += 1 + obj.save(...)
```

El `select_for_update()` cierra la ventana de carrera: mientras una transacción tiene la fila
bloqueda verificando/escribiendo, cualquier otra que intente lo mismo sobre la misma fila espera a
que la primera termine — ya no compiten a ciegas.

### Autoguardado frecuente

No genera falsos conflictos para el **mismo** editor: cada respuesta exitosa le devuelve la
`revision` nueva, que usa en el siguiente autoguardado. Solo se dispara un `412` cuando la escritura
que llega al servidor **no** es la más reciente que el servidor conoce — exactamente la semántica
que se busca, sin fricción para el caso normal de un solo editor tecleando.

### Reordenamiento — revisión estructural separada de la revisión de contenido

El reorder no es un recurso único, es una operación sobre un **grupo**. Usar `If-Match` sobre cada
fila individual del grupo no tiene sentido (serían N valores en un solo request). La solución:
revisión **estructural** a nivel del padre que agrupa, distinta de la revisión de **contenido** de
cada hijo:

| Campo nuevo | Modelo | Se incrementa cuando... |
|---|---|---|
| `Tema.bloques_revision` | `Tema` | se crea, borra o reordena un `ContenidoBloque` bajo ese tema |
| `ContenidoBloque.items_revision` | `ContenidoBloque` | se crea, borra o reordena un `ContenidoBloqueItem` |
| `ContenidoBloque.archivos_revision` | `ContenidoBloque` | ídem para `ContenidoBloqueArchivo` |
| `ContenidoBloque.opciones_revision` | `ContenidoBloque` | ídem para `ContenidoBloqueOpcion` |

**No** se tocan al editar un campo propio del hijo (ej. `PATCH` al `texto` de un ítem no cambia
`items_revision`, porque el *conjunto/orden* de ítems no cambió) — mantenerlas ortogonales evita
falsos conflictos entre dos editores que tocan cosas distintas del mismo bloque.

`PATCH .../reordenar/` pasa a exigir (opcionalmente, mismo criterio de compatibilidad que arriba)
`If-Match` contra la revisión estructural del padre:

```
PATCH /api/capacitacion/bloques/reordenar/
Headers: If-Match: "12"      (Tema.bloques_revision que el cliente tiene)
Body: { "tema": 14, "orden": [...] }
```

Dentro de la transacción: `select_for_update()` sobre el `Tema` (lock del padre, serializa dos
reorders concurrentes del mismo grupo) **y** sobre las filas hijas afectadas (ya ocurre
implícitamente vía los `UPDATE` del paso intermedio actual, se hace explícito para claridad). Si el
`If-Match` no coincide con `bloques_revision` actual → `412`, nada se aplica. Si coincide: aplica el
reorder, incrementa `bloques_revision` en 1, y además incrementa el `revision` individual de cada
`ContenidoBloque` cuyo `orden` cambió (porque `orden` es parte de su propio estado).

Esto resuelve exactamente la distinción que se pidió: **revisión de recurso individual** (edición de
contenido) vs. **revisión estructural** (el conjunto/orden de hijos cambió), con el mismo mecanismo
HTTP estándar (`ETag`/`If-Match`) aplicado a ambos niveles.

### Coste de migración

7 campos `revision` + 4 campos de revisión estructural = 7 migraciones aditivas,
`default=1`/`default=0`, sin backfill de datos (el default ya es válido para filas existentes),
reversibles (`DROP COLUMN`). Riesgo bajo.

---

## 2. Historial y restauración — se descarta "borrar y recrear desde snapshot"

Acepto el rechazo: borrar+recrear pierde identificadores, rompe cualquier FK externa (en particular
`ContenidoBloqueRespuesta.bloque`/`.opcion_seleccionada`, que son `PROTECT`), y por diseño no es
compatible con contenido que ya tiene actividad de alumnos. Pivote completo de estrategia.

### Tres conceptos distintos (el prompt tenía razón en exigir que no se mezclen)

| Concepto | Alcance temporal | Dónde vive | Requiere backend nuevo |
|---|---|---|---|
| Deshacer/rehacer | Sesión de edición activa | Next.js (pila en memoria) | **Sí, parcialmente** — ver §3: deshacer algo ya persistido necesita soft-delete |
| Papelera (recuperar un borrado) | Corto/medio plazo, un elemento a la vez | Django (adoptar `SoftDeleteModel`, ya existe en el proyecto) | Sí — mínimo |
| Historial de revisiones | Largo plazo, cambios estructurales del Tema a través del tiempo | Django (bitácora de operaciones) | Sí — mayor alcance, posponible |

### Prerrequisito que resuelve ambos niveles a la vez: adoptar `SoftDeleteModel` (ya existe, ya se usa en el proyecto)

`common/models.py::SoftDeleteModel` ya está en el código y ya lo usan `Departamento`, `Puesto`,
`Competencia`, `CompetenciaCurso`, `CompetenciaPuesto`, `RutaAprendizaje` — **no se duplica nada,
se reutiliza el mismo patrón**, incluyendo `sistema/views.py::_BaseSoftDeleteViewSet` (filtra
`deleted_at__isnull=True`, sobreescribe `destroy()` para soft-delete) como base para los nuevos
ViewSets.

Adoptarlo en `ContenidoBloque`, `ContenidoBloqueItem`, `ContenidoBloqueArchivo`,
`ContenidoBloqueOpcion` (y, por simetría, `Tema`/`Modulo` si se quiere recuperar un tema completo
borrado) cambia la naturaleza del problema:

- **`DELETE` deja de ser físico** — pasa a marcar `deleted_at`/`deleted_by` (el método `delete()` de
  `SoftDeleteModel` ya hace exactamente esto).
- **`restore()` ya existe en el modelo base** — revierte `deleted_at`/`deleted_by` a `None`. Cero
  código nuevo para la mecánica de restaurar un elemento individual, solo exponerlo como una acción
  de ViewSet (mismo patrón `@action` que ya se usa para `reordenar`).
- **El archivo físico deja de borrarse al eliminar** — `BaseFileEntity.delete()` hoy hace
  `os.remove(self.file.path)` incondicionalmente; con `SoftDeleteModel`, el método `delete()`
  heredado de `SoftDeleteModel` nunca llama al `delete()` físico de `BaseFileEntity` (solo guarda
  `deleted_at`), así que el archivo permanece en disco hasta que alguien llame explícitamente
  `hard_delete()` (también ya definido en `SoftDeleteModel`) — por ejemplo, una tarea de limpieza
  tras expirar la retención.
- **El `PROTECT` de `ContenidoBloqueRespuesta` deja de ser un obstáculo** — un soft-delete nunca
  intenta borrar la fila físicamente, así que nunca choca contra el `ProtectedError` que hoy
  bloquea borrar un bloque con respuestas reales (lo viví de primera mano limpiando datos de
  prueba). **Esto es lo que vuelve segura cualquier restauración, tenga o no actividad de
  alumnos** — ver política abajo.

**Pitfall técnico a documentar** (para que no se filtre un elemento "borrado" de vuelta sin querer):
los serializers anidados (`bloque_items`, `archivos`, `opciones` dentro de `ContenidoBloqueSerializer`)
usan el manager por defecto de la relación (`related_name`), que **no pasa por el `get_queryset()`
del ViewSet**. Si se adopta soft-delete, hay que filtrar también a nivel de *manager* del modelo
(un manager por defecto que excluya `deleted_at__isnull=False`), no solo en las vistas — si no, un
ítem "borrado" seguiría apareciendo en la respuesta anidada del bloque padre.

### Política de restauración — dos casos, mismo mecanismo seguro

Con soft-delete adoptado, "restaurar a un punto anterior" deja de requerir borrar nada
físicamente: es una operación de **diff**, no de **reemplazo**:

- Filas que existen hoy pero no existían en el punto histórico → se marcan `deleted_at` (soft
  delete, no se tocan sus relaciones).
- Filas que existían en el punto histórico pero están borradas hoy → `restore()`.
- Filas cuyo contenido cambió → `PATCH` dirigido solo a esa fila con los valores históricos.

Esto preserva **todos** los identificadores y relaciones de lo que sigue existiendo — exactamente
lo que se pidió.

- **Política A — Tema sin actividad de alumnos** (sin `ContenidoBloqueRespuesta`/`ProgresoTema`/
  `ResultadoEvaluacion` apuntando a nada bajo ese tema): restauración automática, sin fricción
  adicional — el diff es seguro por construcción.
- **Política B — Tema con actividad histórica**: **mismo mecanismo técnico** (nunca hard-delete),
  pero el frontend debe mostrar una advertencia explícita antes de confirmar ("este tema tiene N
  respuestas de alumnos sobre bloques evaluativos que quedarán ocultos, no borrados, al
  restaurar") y la operación queda registrada en la bitácora (quién restauró, cuándo, a qué punto).
  No se bloquea — se vuelve segura por diseño y solo se añade fricción informativa.

**Concurrencia durante la restauración**: la restauración es en sí una operación estructural sobre
el `Tema` → debe tomar `select_for_update()` sobre el tema y sus bloques, y verificar `If-Match`
contra `Tema.bloques_revision` (mecanismo de §1) antes de aplicar — si alguien edita el tema entre
que el admin abrió el historial y confirmó la restauración, debe fallar con `412` igual que
cualquier otra escritura condicionada, no sobrescribir silenciosamente.

### La bitácora en sí (motor del historial — queda posponible, pero el diseño ya no tiene el defecto anterior)

Modelo de **operaciones**, no de snapshots completos (evita el "snapshot por cada tecla" que el
prompt pide evitar, y evita el problema de restaurar por reemplazo):

```
TemaRevision:
  tema (FK)
  tipo_operacion: bloque_creado | bloque_editado | bloque_borrado | bloque_restaurado |
                  bloques_reordenados | item_creado | item_editado | ... (mismo patrón por nivel)
  objeto_tipo / objeto_id   -- qué fila fue afectada
  payload_antes (JSON, nullable)
  payload_despues (JSON, nullable)
  actor (FK user)
  creado_at
```

Se escribe server-side dentro de los mismos `perform_create`/`perform_update`/`destroy`/
`_reordenar_en_lote` que ya existen — una fila por operación relevante (no por tecla), disparada
por el backend, no por el frontend. Retención sugerida: 90 días o N operaciones por tema, lo que
ocurra primero.

**Prioridad**: el prerrequisito (adoptar `SoftDeleteModel`) es **recomendable, no indispensable**
para cerrar el constructor — pero es barato (reutiliza código existente) y destraba tanto la
papelera como el deshacer-de-persistido (§3). La bitácora completa de historial sigue siendo
**posponible**.

---

## 3. Autoguardado y deshacer — garantías explícitas por escenario

| Escenario | ¿Resuelto hoy? | Garantía necesaria | ¿Quién la da? |
|---|---|---|---|
| Eliminar un bloque y deshacer **después de persistir** | ❌ No — hoy el `DELETE` es físico; recrear vía `POST` genera un **id nuevo**, rompiendo cualquier referencia al original (incluida la cascada completa de `bloque_items`/`archivos`/`opciones` ya perdida) | Preservar el mismo id al deshacer | **Django**, vía `restore()` de §2 (no es posible resolverlo solo en el frontend) |
| Eliminar un archivo y deshacer | ❌ No — además el archivo físico ya fue borrado del disco (`BaseFileEntity.delete()`), irrecuperable pase lo que pase el frontend | No borrar el archivo físico al eliminar | **Django**, vía soft-delete (el archivo permanece hasta `hard_delete()` explícito) |
| Reordenar y revertir | ✅ Seguro hoy, **mejora con §1** | Que el reorder no "resucite" un orden inválido si otro editor insertó/borró algo en medio | Hoy: nadie lo garantiza. Con `If-Match` sobre `bloques_revision`: **Django** |
| Editar mientras hay una solicitud pendiente (mismo cliente) | Responsabilidad del cliente | Backend aplica en el orden real de llegada, atómico por fila (ya ocurre) | **Next.js** debe cancelar/serializar solicitudes en vuelo (`AbortController` o cola) — no es resoluble del lado del servidor para una sola conexión |
| Respuestas de guardado fuera de orden | ❌ No hay forma de detectarlo hoy | Un valor monótonamente creciente en cada respuesta, para que el cliente descarte una respuesta "vieja" que llega tarde | **Django** da el dato (`revision` de §1); **Next.js** aplica la regla ("si `revision` recibida < `revision` que ya tengo, descarto") |
| Reintentar una creación tras timeout | ✅ Parcial — ya funciona para hijos ordenados vía `unique_together`, no para `Curso`/`Modulo`/`Tema` | Rechazo determinista si el recurso ya se había creado | **Django** (ya lo da donde hay `unique_together`); **Next.js** debe reintentar con el mismo `orden` y, ante `400`, hacer `GET` de confirmación en vez de reintentar a ciegas |

No doy por resuelto el deshacer de operaciones persistidas solo porque el frontend pueda reemitir
la solicitud inversa — como muestra la tabla, dos de los seis escenarios (borrar bloque / borrar
archivo, ambos "deshacer tras persistir") **requieren** el prerrequisito de soft-delete de §2 para
ser seguros; sin él, el frontend no tiene ninguna solicitud inversa que preserve identidad y
relaciones.

---

## 4. Publicación de contenido — hallazgo re-verificado con datos reales, propuesta revisada (más estrecha de lo que sugería originalmente)

### Qué estados existen

`CatalogStatus` hoy tiene (en los datos de esta base): `borrador`, `publicado`, `archivado` —
confirmado por consulta directa, no es un catálogo cerrado por código (es datos, administrable vía
`/api/catalogos/status/`), así que cualquier corrección debe filtrar por `codigo='publicado'`
explícitamente, no asumir que "todo lo que no es borrador" es seguro de mostrar.

### Qué endpoints exponen contenido no publicado hoy

`CursoColaboradorViewSet`, `MisCursosViewSet` (`capacitacion/views_colaborador.py::_base_cursos_qs`)
filtran solo `activo=True` — exponen cursos en cualquier `status`. `ModuloColaboradorViewSet`,
`TemaColaboradorViewSet`, `ContenidoBloqueColaboradorViewSet` no filtran por `status` del curso en
absoluto (solo por `activo=True` del propio módulo/tema/bloque) — alcanzables directamente por
`?curso=`/`?modulo=`/`?tema=` sin pasar antes por el listado de cursos.

### Impacto real sobre cursos existentes — medido, no asumido

Corrí la consulta contra los datos reales de esta base antes de proponer nada:

```
Cursos por status: archivado=2, publicado=4

Cursos NO publicados con actividad real de alumnos:
  Atención al cliente (archivado): inscripciones=6  progreso_temas=25  resultados=4
  Introducción a Python (archivado): inscripciones=10  progreso_temas=40  resultados=4
```

**Esto cambia la recomendación.** Un filtro ciego `status='publicado'` en todos los endpoints de
colaborador sacaría de circulación, de inmediato, dos cursos con 16 inscripciones y 65 registros de
progreso reales — alumnos a mitad de curso perderían acceso a contenido en el que ya tienen avance.
"Archivado" en este dominio significa "ya no se ofrece a gente nueva", no "nadie debe poder verlo
nunca más".

### Propuesta mínima y segura (revisada)

Dos reglas distintas según el tipo de endpoint, no un filtro único:

1. **Endpoints de descubrimiento** (`CursoColaboradorViewSet` — catálogo completo;
   `MisCursosViewSet` — recomendados por competencias del puesto): filtrar
   `status__codigo='publicado'`. Un curso en borrador o archivado deja de aparecer para
   alguien que **todavía no está inscrito** — correcto, nadie nuevo debería poder "descubrir" o
   inscribirse en ninguno de los dos.
2. **Endpoints de contenido ya en curso** (`ModuloColaboradorViewSet`, `TemaColaboradorViewSet`,
   `ContenidoBloqueColaboradorViewSet`, alcanzados por id explícito): filtrar **solo**
   `status__codigo='borrador'` (bloquear borrador específicamente, nunca tuvo alumnos reales
   porque nunca estuvo en el listado de descubrimiento, así que no hay nadie a quien se le quite
   acceso). **No** filtrar `archivado` aquí — así un alumno ya inscrito conserva acceso a su
   contenido aunque el curso ya no se ofrezca a gente nueva.
3. `MisInscripcionesViewSet`/progreso: sin cambios — ya están scoped a `colaborador=request.user`,
   no necesitan filtro de `status` (un alumno siempre debe poder ver su propio historial de
   inscripción, publicado o no).

### ¿Editar contenido publicado afecta inmediatamente al alumno?

Sí, confirmado — no existe ninguna separación entre "versión publicada" y "borrador de trabajo" a
nivel de contenido (solo existe la etiqueta `status` sobre el `Curso` completo, no versionado por
bloque). Cualquier `PATCH` a un bloque de un curso "publicado" es visible para los alumnos
inscritos en su siguiente `GET`, sin demora. **Esto es una decisión de producto pendiente, no algo
que esta corrección resuelva**: si se necesita que los alumnos sigan viendo una versión congelada
mientras se edita, eso requiere el motor de revisiones de §2 aplicado también a "snapshot
publicado vs. borrador de trabajo" — alcance mayor, deliberadamente fuera de esta corrección
mínima.

**Prioridad**: 🟡 media, como en la auditoría anterior — pero ahora con alcance preciso (regla 1 y 2
por separado) en vez de un filtro uniforme que habría roto cursos reales.

---

## 5. Elementos anidados — coordinación con autoguardado/concurrencia (sin cambiar la arquitectura de endpoints independientes)

Se conserva exactamente como está: bloque padre vía `/bloques/`, hijos vía
`/bloque-items/`, `/bloque-archivos/`, `/bloque-opciones/` — anidados **solo en lectura** en la
respuesta del padre. Lo único que se agrega es la contabilidad de revisión de §1:

- `PATCH` a un hijo (ej. `texto` de un ítem) → incrementa **solo** el `revision` propio del ítem.
  No toca `ContenidoBloque.items_revision` (el conjunto/orden no cambió).
- `POST`/`DELETE`/`reordenar` sobre hijos → incrementa `items_revision`/`archivos_revision`/
  `opciones_revision` del bloque padre (el conjunto u orden sí cambió), además del `revision`
  propio de cada fila tocada en el caso de reorder.
- Un `GET` del bloque padre, al traer los hijos anidados, puede incluir también las revisiones
  estructurales (`items_revision`, etc.) en el payload — así el frontend puede detectar "¿cambió
  la lista de hijos desde la última vez que la cargué?" sin tener que comparar arrays completos,
  simplemente comparando un entero.

No se introduce escritura anidada (crear bloque + hijos en una sola llamada): se mantiene la
secuencia ya documentada en el contrato (`POST` bloque → `POST` hijos referenciando su id) — la
contabilidad de revisión no cambia esa secuencia, solo se adjunta a las operaciones que ya existen.

---

## 6. Catálogo dinámico — metadatos suficientes para los 15 tipos de contenido/estructura

Los dos tipos evaluativos (`opcion-multiple`, `verdadero-falso`) **no se tocan** en este análisis,
tal como se indicó.

Revisando `config`/`capacidades`/`validacion_schema` actuales contra lo pedido:

| Metadato pedido | Estado | Acción |
|---|---|---|
| Valores predeterminados | 🟡 Parcial — solo `texto-elemento-dinamico` declara `config.defaults` | Recomendable: completar `defaults` en tipos con un valor sensato implícito (ej. `aviso-destacado` → `{"variante": "info"}`). Solo datos (JSON), sin migración. |
| Capacidades | ✅ Suficiente | Ninguna |
| Relaciones (qué hijo usa cada tipo) | ✅ Suficiente (`config.items`/`archivos`) | Ninguna |
| Cardinalidad de relaciones (mínimos/máximos) | ❌ No declarada | Recomendable: `config.items_min`/`items_max` opcional para tipos con restricciones reales (ej. mínimo 1 tarjeta). Metadato, no bloqueante. |
| Variantes | ✅ Suficiente (`variante_valores` donde aplica) | Ninguna |
| Validación | ❌ `validacion_schema` es `null` en los 15 tipos — no hay ninguna validación real basada en schema hoy | Posponible: poblar JSON Schema por tipo + hook de validación en el serializer. Trabajo no trivial, no indispensable para cerrar el constructor. |
| Versión de esquema por instancia | ❌ Solo a nivel de catálogo (ya señalado en la auditoría anterior) | Recomendable, igual que antes. |

Ninguna referencia a componentes React dentro de Django — confirmado, no se encontró ni se propone
nada en esa dirección.

---

## 7. Entrega solicitada

### 1. Decisión técnica de concurrencia
`revision` entero por fila + `ETag`/`If-Match` (estándar HTTP) + `select_for_update()` dentro de la
misma transacción que verifica y escribe. Revisión estructural separada (`*_revision` en el padre)
para operaciones sobre colecciones de hijos (crear/borrar/reordenar). Se descarta el timestamp
(`actualizado_at`) por el bug de `update_fields` demostrado arriba y por la resolución de 1s de
`If-Unmodified-Since`. **Indispensable.**

### 2. Estrategia de historial y restauración
Adoptar `SoftDeleteModel` (ya existente, ya usado en el proyecto) en los modelos de contenido como
prerrequisito — vuelve segura cualquier restauración (diff-based, nunca hard-delete) sin importar
si hay actividad de alumnos. Restauración con dos políticas (sin actividad = automática; con
actividad = con advertencia explícita), nunca por reemplazo. Bitácora de operaciones (no snapshots)
como motor de historial completo. **Prerrequisito (soft-delete): recomendable. Motor de historial
completo: posponible.**

### 3. Garantías de autoguardado y deshacer
Ver tabla de §3. Resumen: atomicidad por fila y rechazo determinista de duplicados ya los da Django
hoy; deshacer-tras-persistir (bloque/archivo) **requiere** el prerrequisito de soft-delete;
descartar respuestas fuera de orden requiere el `revision` de §1 más una regla de cliente en
Next.js; serializar solicitudes en vuelo es responsabilidad exclusiva de Next.js.

### 4. Corrección de exposición de borradores
Dos reglas distintas (no un filtro uniforme): `publicado` únicamente en endpoints de descubrimiento;
solo bloquear `borrador` (no `archivado`) en endpoints de contenido ya en curso, para no romper el
acceso de alumnos ya inscritos en cursos archivados — medido con datos reales de esta base
(2 cursos archivados, 16 inscripciones, 65 registros de progreso que se habrían roto con un filtro
ciego). **Indispensable, con el alcance preciso de §4, no el filtro amplio propuesto originalmente.**

### 5. Contrato de integración actualizado para Next.js
Deltas sobre `docs/CONTRATO_BLOQUES_FRONTEND.md` (no implementados todavía):
- Todo recurso editable responde `ETag`/`revision` en el body.
- `PATCH`/`DELETE` aceptan `If-Match` opcional; `412` con `revision_actual` si no coincide.
- `PATCH .../reordenar/` acepta `If-Match` contra la revisión estructural del padre.
- Regla de cliente: descartar cualquier respuesta cuyo `revision` sea menor al ya aplicado
  localmente.
- Regla de reintento: ante timeout en creación, reintentar con el mismo `orden`; si llega `400` por
  `unique_together`, hacer `GET` de confirmación en vez de reintentar a ciegas.
- Modo previsualización: prohibido llamar a cualquier endpoint `/mis-*` (sin cambios respecto a la
  auditoría anterior).
- Regla de publicación: el frontend debe esperar `404`/ausencia de un curso en `borrador` desde
  endpoints de descubrimiento, pero seguir pudiendo cargar contenido de cursos `archivado` si el
  usuario ya estaba inscrito.

### 6. Modelos, serializers, ViewSets y migraciones afectados

| Cambio | Archivos |
|---|---|
| `revision` en `Curso`/`Modulo`/`Tema`/`ContenidoBloque`/`Item`/`Opcion`/`Archivo` | `capacitacion/models/curso.py` + 1 migración |
| `bloques_revision` en `Tema`; `items_revision`/`archivos_revision`/`opciones_revision` en `ContenidoBloque` | `capacitacion/models/curso.py` + 1 migración |
| Mixin de concurrencia optimista (`perform_update`, chequeo `If-Match`) | nuevo `capacitacion/concurrency.py` (o similar), aplicado en `capacitacion/views.py` |
| `select_for_update()` en `_reordenar_en_lote` + verificación `If-Match` estructural | `capacitacion/views.py` |
| Adopción de `SoftDeleteModel` en `ContenidoBloque`/`Item`/`Archivo`/`Opcion` | `capacitacion/models/curso.py` + migración (cambia la clase base) |
| Manager por defecto que excluya soft-deleted en relaciones anidadas | `capacitacion/models/curso.py` |
| Acciones `restaurar`/`papelera` en ViewSets admin | `capacitacion/views.py`, reutilizando patrón de `sistema/views.py::_BaseSoftDeleteViewSet` |
| Filtro `status` en endpoints colaborador (regla 1 y 2 de §4) | `capacitacion/views_colaborador.py` |
| Serializers: incluir `revision`/`*_revision` en los campos expuestos | `capacitacion/serializers/curso.py`, `capacitacion/serializers/colaborador.py` |
| (Posponible) `TemaRevision` — bitácora | nuevo modelo + migración + ViewSet de solo lectura |
| (Posponible) `validacion_schema` poblado + hook de validación | `common/management/commands/seed_tipos_bloque.py`, serializer de `ContenidoBloque` |

### 7. Plan de implementación ordenado por riesgo

| Orden | Cambio | Riesgo | Depende de |
|---|---|---|---|
| 1 | Filtro de publicación con el alcance preciso de §4 | Bajo (medido contra datos reales, sin romper cursos con actividad) | Nada |
| 2 | Campos `revision`/`*_revision` + mixin de concurrencia + `select_for_update` | Bajo (aditivo, opcional vía `If-Match`) | Nada |
| 3 | Adopción de `SoftDeleteModel` en modelos de contenido + manager que filtre en anidados | Medio (cambia la clase base de 4 modelos, revisar cascadas y managers) | Nada, pero habilita 4 y 5 |
| 4 | Acciones de papelera/restaurar + deshacer-tras-persistir en el frontend | Bajo | Paso 3 |
| 5 | Bitácora de historial (`TemaRevision`) + restauración con política A/B | Medio (lógica de diff-restore no trivial) | Pasos 2 y 3 |
| 6 | `validacion_schema` + hook de validación | Bajo, pero trabajo no trivial | Nada, independiente del resto |

Pasos 1 y 2 son independientes entre sí y pueden ir en paralelo. Paso 3 es el habilitador de todo
el bloque de historial/papelera — vale la pena priorizarlo antes que 4/5 aunque no sea
"indispensable" en sí mismo, porque es barato (reutiliza `SoftDeleteModel` ya existente) y
desbloquea dos capacidades pedidas (papelera y deshacer-tras-persistir) con una sola migración.

### 8. Pruebas necesarias por cambio

| Cambio | Pruebas |
|---|---|
| Concurrencia optimista | `PATCH` con `If-Match` correcto aplica y sube `revision`; con `If-Match` desactualizado devuelve `412` sin aplicar cambios; sin `If-Match` mantiene comportamiento actual; dos `PATCH` concurrentes (simulados con `threading`/transacciones separadas) — uno gana, el otro recibe `412`, nunca ambos aplican |
| Reorder con revisión estructural | Reorder con `If-Match` correcto sube `bloques_revision` y el `revision` de cada fila tocada; con `If-Match` desactualizado, `412` sin tocar nada; dos reorders concurrentes del mismo tema — uno espera al otro (verificar con `select_for_update` + transacciones solapadas) |
| Soft-delete | `DELETE` no borra la fila físicamente (`deleted_at` se setea); no aparece en listados ni en anidados tras borrar; `restore()` la recupera con el mismo id y relaciones intactas; archivo físico permanece en disco tras soft-delete de `ContenidoBloqueArchivo`; `hard_delete()` sí lo borra |
| Restauración (si se implementa bitácora) | Política A (sin actividad): restaura automáticamente, ids preservados; Política B (con actividad): requiere confirmación, preserva `ContenidoBloqueRespuesta` existentes sin tocarlas; restauración concurrente con una edición en vivo → `412` |
| Publicación | Curso en `borrador` no aparece en `/ver/cursos/` ni `/mis-cursos/`; curso `archivado` tampoco aparece ahí; pero un colaborador YA inscrito en un curso `archivado` sigue viendo `/ver/modulos/`, `/ver/temas/`, `/ver/bloques/` de ese curso; un colaborador NO inscrito no puede acceder a `/ver/temas/?modulo=<id de un borrador>` directamente por id |
| Elementos anidados | `PATCH` a un ítem no cambia `items_revision` del bloque padre; `POST`/`DELETE`/reorder de un ítem sí la cambia |

---

## Clasificación final

**Indispensable**: concurrencia optimista (§1), corrección de publicación con el alcance preciso
de §4.

**Recomendable**: adopción de `SoftDeleteModel` como prerrequisito de papelera/deshacer-persistido
(§2/§3), metadatos de catálogo faltantes (§6: `defaults`, cardinalidad), `version_esquema` por
instancia.

**Posponible**: bitácora completa de historial con restauración por política A/B, `validacion_schema`
poblado + validación real basada en schema.

**No se implementó nada en este documento.** Queda a la espera de validación de estas decisiones
antes de tocar código, tal como se pidió.
