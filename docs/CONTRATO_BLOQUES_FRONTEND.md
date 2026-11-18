# Contrato de datos y API — Constructor de bloques (Farrera Academy)

Referencia para el frontend (Next.js) que consume la API de `capacitacion`/`catalogos`.
Cubre: catálogo extensible de tipos de bloque, jerarquía Curso→Módulo→Tema→Bloque,
el contrato de cada tipo de bloque, reorder en lote, subida de archivos, y el flujo
de bloques evaluativos embebidos.

Todas las rutas van bajo el prefijo `/api/`. Autenticación: JWT (`Authorization: Bearer <token>`
o cookie `access`, según `CustomJWTAuthentication`). Dos familias de endpoints:

- **Admin** (`/api/capacitacion/...`): requieren rol `Administrador` (o superusuario). CRUD completo.
- **Colaborador** (`/api/capacitacion/ver/...` y `/api/capacitacion/mis-*`): cualquier autenticado,
  solo lectura de contenido + escritura de su propio progreso/intentos.

---

## 1. Paginación

Todos los listados paginan por default (`PageNumberPagination`, `PAGE_SIZE=10`):

```json
{ "count": 42, "next": "http://.../?page=2", "previous": null, "results": [ ... ] }
```

Para traer todo de una vez (catálogos para llenar selects, listas de módulos/temas pequeñas, etc.):

```
GET /api/catalogos/tipos-bloque/?pagination=false
```

Devuelve el array plano, sin envoltorio. Acepta `false`, `0` o `no` (case-insensitive); cualquier
otro valor o ausencia del parámetro pagina normalmente.

---

## 2. Catálogo de tipos de bloque — la fuente de verdad

**No hardcodear un switch de tipos en el frontend.** El catálogo describe cada tipo con los campos
que necesita, para que agregar un tipo nuevo no requiera un release del frontend salvo que
necesite un componente visual nuevo.

```
GET /api/catalogos/tipos-bloque/?pagination=false
```

```json
[
  {
    "id": 7,
    "nombre": "Texto con tarjetas",
    "codigo": "texto-tarjetas",
    "icono": "", "color": "", "orden": 6, "activo": true,
    "creado_at": "...", "actualizado_at": "...",
    "categoria": "contenido",
    "descripcion": "Grilla de tarjetas, cada una con título, texto breve e imagen de fondo.",
    "config": { "campos": ["texto"], "items": "bloque_items" },
    "validacion_schema": null,
    "capacidades": ["soporta_items", "soporta_imagen_por_item"],
    "version_esquema": 1
  }
]
```

| Campo | Uso en frontend |
|---|---|
| `codigo` | **Llave estable** para el switch/render — nunca usar `nombre` (es editable, no estable). |
| `categoria` | Una de: `contenido`, `exploracion`, `practica`, `evaluacion`, `reflexion_colaboracion`, `estructura_navegacion`. Útil para agrupar el picker de bloques en el editor. |
| `config.campos` | Qué campos planos de `ContenidoBloque` usa este tipo (`texto`, `variante`, `video_url`, etc.). |
| `config.items` / `config.archivos` / `config.opciones` | Si el tipo usa la relación anidada `bloque_items`, `archivos` u `opciones` respectivamente. |
| `config.items_campos` | Qué campos de cada `ContenidoBloqueItem` son relevantes para este tipo (ver tabla §5). |
| `config.variante_valores` | Valores válidos de `variante` para ese tipo (ej. `aviso-destacado`). |
| `capacidades` | Flags simples sin parsear schema (`soporta_imagen`, `carrusel`, `autoevaluable`, etc.). |
| `validacion_schema` | JSON Schema opcional (hoy `null` en todos los tipos — reservado para validación fuerte a futuro). |
| `version_esquema` | Sube si cambia la forma esperada del contenido de ese tipo. Guardar junto con el bloque si se quiere detectar contenido con esquema viejo. |

### Tabla completa de tipos activos (15)

| `codigo` | categoría | campos planos | relación usada | capacidades clave |
|---|---|---|---|---|
| `texto-imagen` | contenido | `texto`, `imagen_url`/`imagen_archivo` | — | `soporta_imagen` |
| `texto-video` | contenido | `texto`, `video_url`/`video_archivo` | — | `soporta_video`, `soporta_streaming` |
| `texto-elemento-dinamico` | contenido | `texto`, `imagen_url`/`imagen_archivo`, `variante="dinamico"` | — | `soporta_imagen`, `interactivo` (lightbox) |
| `texto-presentacion` | contenido | `texto` | `bloque_items` (diapositivas) | `carrusel` |
| `texto-paneles` | contenido | `texto` | `bloque_items` (paneles) | `carrusel` |
| `texto-presentacion-paneles` | contenido | `texto` | `bloque_items` (paneles superpuestos) | `carrusel` |
| `texto-tarjetas` | contenido | `texto` | `bloque_items` (tarjetas) | — |
| `texto-galeria` | contenido | `texto` | `bloque_items` (imagen por ítem) | `carrusel` |
| `texto-audio` | contenido | `texto` | `archivos` | `soporta_archivo_audio` |
| `texto-documento` | contenido | `texto` | `archivos` | `descargable` |
| `acordeon` | exploración | `texto` | `bloque_items` (`titulo`=encabezado, `texto`=contenido) | `colapsable` |
| `tarjetas-giratorias` | exploración | `texto` | `bloque_items` (`titulo`+imagen=frente, `texto`=reverso) | `interactivo` |
| `aviso-destacado` | estructura y navegación | `texto`, `variante` ∈ {`info`,`exito`,`advertencia`,`error`} | — | `requiere_variante` |
| `separador` | estructura y navegación | ninguno | — | — (puramente visual) |
| `objetivos-aprendizaje` | estructura y navegación | `texto` | `bloque_items` (`titulo`=cada objetivo) | — |
| `opcion-multiple` | evaluación | `texto` (enunciado) | `opciones` | `autoevaluable` |
| `verdadero-falso` | evaluación | `texto` (enunciado) | `opciones` (2 fijas) | `autoevaluable` |

> No construyas un `if/else` por `codigo`; agrupa por `config.items`/`archivos`/`opciones` +
> `config.campos` y vas a cubrir tipos nuevos sin tocar código la mayoría de las veces.

---

## 3. Jerarquía de contenido

```
Curso ──< Modulo ──< Tema ──< ContenidoBloque ──< ContenidoBloqueItem
                                               ├─< ContenidoBloqueArchivo
                                               └─< ContenidoBloqueOpcion ──< ContenidoBloqueRespuesta (colaborador)
```

### Endpoints admin (CRUD completo, rol Administrador)

| Recurso | Base URL |
|---|---|
| Cursos | `/api/capacitacion/cursos/` |
| Módulos | `/api/capacitacion/modulos/?curso=<id>` |
| Temas | `/api/capacitacion/temas/?modulo=<id>` |
| Bloques | `/api/capacitacion/bloques/?tema=<id>` |
| Ítems de bloque | `/api/capacitacion/bloque-items/?bloque=<id>` |
| Archivos de bloque | `/api/capacitacion/bloque-archivos/?bloque=<id>` |
| Opciones de bloque evaluativo | `/api/capacitacion/bloque-opciones/?bloque=<id>` |

Borrar un Módulo/Tema/Bloque/Item/Archivo/Opción **cierra el hueco de orden automáticamente**
(los hermanos posteriores se recorren `-1`). No hace falta recalcular el orden tras un `DELETE`.

### Endpoints de lectura para colaborador (`/api/capacitacion/ver/...`)

| Recurso | Base URL |
|---|---|
| Cursos (catálogo completo activo) | `/api/capacitacion/ver/cursos/` |
| Mis cursos (según competencias del puesto) | `/api/capacitacion/mis-cursos/` |
| Módulos | `/api/capacitacion/ver/modulos/?curso=<id>` |
| Temas | `/api/capacitacion/ver/temas/?modulo=<id>` |
| Bloques | `/api/capacitacion/ver/bloques/?tema=<id>` |

---

## 4. `ContenidoBloque` — contrato completo

### Respuesta admin (`GET/POST/PATCH /api/capacitacion/bloques/`)

```json
{
  "id": 59,
  "tema": 14,
  "tipo": 7,
  "tipo_nombre": "Texto con tarjetas",
  "tipo_codigo": "texto-tarjetas",
  "orden": 3,
  "texto": "Conceptos básicos de Marketing Digital",
  "variante": "",
  "items": null,
  "filas": null,
  "video_url": "",
  "video_archivo": null,
  "imagen_url": "",
  "imagen_archivo": null,
  "bloque_items": [
    { "id": 1, "bloque": 59, "orden": 1, "titulo": "SEO", "texto": "...", "imagen_url": "", "imagen_archivo": "/media/...", "items": null, "activo": true, "creado_at": "...", "actualizado_at": "..." }
  ],
  "archivos": [],
  "opciones": [],
  "activo": true, "creado_at": "...", "actualizado_at": "..."
}
```

- `tipo` (escritura) es el **id** de `TipoBloqueContenido`; `tipo_codigo`/`tipo_nombre` son de solo
  lectura, resueltos por el backend.
- `bloque_items`, `archivos`, `opciones` vienen **anidados de gratis** en la misma respuesta — no
  hace falta un segundo `GET` para pintar un bloque de tipo `texto-tarjetas`/`acordeon`/etc.
- Campos legacy JSON (`items`, `filas`) siguen existiendo por compatibilidad con bloques antiguos,
  pero los tipos nuevos (desde `texto-presentacion-paneles` en adelante) usan `bloque_items`, no
  estos campos.

### Respuesta colaborador (`GET /api/capacitacion/ver/bloques/`)

Mismo contrato, sin `tipo` (id), sin `es_correcta` en `opciones`, con `video_stream_url` resuelto:

```json
{
  "id": 59, "tema": 14, "tipo_nombre": "...", "tipo_codigo": "texto-tarjetas",
  "orden": 3, "texto": "...", "variante": "",
  "items": null, "filas": null, "video_url": "", "video_stream_url": null,
  "imagen_url": "", "imagen_archivo": null,
  "bloque_items": [...], "archivos": [...], "opciones": [{ "id": 1, "orden": 1, "texto": "4" }]
}
```

`video_stream_url` solo viene poblado si `video_archivo` existe; apunta a
`GET /api/capacitacion/stream/<bloque_id>/` (requiere el mismo JWT, sirve el archivo vía
`X-Accel-Redirect` en producción).

---

## 5. `ContenidoBloqueItem` — tarjetas, paneles, diapositivas, acordeón, galería, objetivos

```
GET/POST/PATCH/DELETE /api/capacitacion/bloque-items/?bloque=<id>
PATCH /api/capacitacion/bloque-items/reordenar/
```

```json
{ "id": 1, "bloque": 59, "orden": 1, "titulo": "SEO", "texto": "...", "imagen_url": "", "imagen_archivo": null, "items": null }
```

Un solo modelo genérico cubre 8 tipos distintos — el **significado** de cada campo depende de
`config.items_campos` del tipo (tabla §2):

| Tipo de bloque | `titulo` | `texto` | `imagen_*` | `items` (JSON libre) |
|---|---|---|---|---|
| `texto-tarjetas`/`texto-paneles`/`texto-presentacion`/`texto-presentacion-paneles`/`texto-galeria` | título de la tarjeta/panel | texto breve | imagen de la tarjeta | — |
| `acordeon` | encabezado colapsable | contenido que se revela | (no se usa) | — |
| `tarjetas-giratorias` | frente de la tarjeta | reverso (se revela al voltear) | frente de la tarjeta | — |
| `objetivos-aprendizaje` | el objetivo en sí | (no se usa) | (no se usa) | — |
| `texto-paneles` (caso con datos tabulares, ej. lista de agencias de un panel) | título del panel | (no se usa) | imagen del panel | lista libre, ej. `["Tuxtla Gutiérrez, Chiapas", ...]` |

`items` es JSON sin estructura fija — úsalo solo cuando el tipo lo pida explícitamente (ningún
`config` actual declara `items` como obligatorio; es terreno libre para casos como el panel de
ubicaciones de agencias del mockup original).

---

## 6. `ContenidoBloqueArchivo` — audio y documento

Reutiliza `BaseFileEntity` del backend: el servidor autodetecta `mime_type`, `file_type`, `size` y
`checksum` al subir. **Importante**: este modelo usa `status`/`created_at`, no `activo`/`creado_at`
como el resto (es la única excepción en todo el árbol de capacitación).

```
POST /api/capacitacion/bloque-archivos/        (multipart/form-data)
GET/PATCH/DELETE /api/capacitacion/bloque-archivos/<id>/
PATCH /api/capacitacion/bloque-archivos/reordenar/
```

Subida (multipart):

```
bloque: 59
orden: 1
file: <binary>
description: "Manual del colaborador"   (opcional)
```

Respuesta:

```json
{
  "id": 3, "bloque": 59, "orden": 1,
  "file": "/media/capacitacion/archivos/.../manual.pdf",
  "original_name": "manual.pdf", "mime_type": "application/pdf",
  "size": 48213, "size_formatted": "47.1 KB",
  "file_type": "document", "description": "Manual del colaborador",
  "checksum": "a1b2c3...", "status": 1, "created_at": "..."
}
```

`original_name`, `mime_type`, `size`, `size_formatted`, `file_type`, `checksum` son **read-only**
(calculados por el servidor). `file_type` es uno de: `document`, `image`, `video`, `audio`,
`spreadsheet`, `presentation`, `archive`, `other`. La vista colaborador
(`bloque_items`→`archivos` dentro del bloque) expone los mismos campos excepto `checksum`/`status`.

---

## 7. Bloques evaluativos embebidos (`opcion-multiple` / `verdadero-falso`)

**No es el sistema formal de `Evaluacion`** (ese sigue existiendo para evaluación de módulo/curso
con puntaje mínimo, en `/api/capacitacion/evaluaciones/`). Esto es una pregunta rápida suelta
dentro de una lección — misma idea, mecanismo más liviano.

### Autoría (admin)

```
GET/POST/PATCH/DELETE /api/capacitacion/bloque-opciones/?bloque=<id>
PATCH /api/capacitacion/bloque-opciones/reordenar/
```

```json
{ "id": 1, "bloque": 59, "orden": 1, "texto": "4", "es_correcta": true, "activo": true, "creado_at": "...", "actualizado_at": "..." }
```

`es_correcta` **solo existe en este endpoint admin**. El bloque padre (`texto` = el enunciado de la
pregunta) se crea/edita normalmente vía `/api/capacitacion/bloques/` con `tipo` = id de
`opcion-multiple`/`verdadero-falso`.

### Lo que ve el colaborador

Dentro de `GET /api/capacitacion/ver/bloques/`, el bloque trae `opciones` **sin** `es_correcta`:

```json
"opciones": [{ "id": 1, "orden": 1, "texto": "4" }, { "id": 2, "orden": 2, "texto": "5" }]
```

### Responder

```
POST /api/capacitacion/mis-respuestas-bloque/
Body: { "bloque": 59, "opcion_seleccionada": 1 }
```

```json
{
  "id": 10, "bloque": 59, "bloque_texto": "¿2+2?",
  "opcion_seleccionada": 1, "es_correcta": true,
  "respondido_at": "...", "activo": true
}
```

- `es_correcta` se calcula **en el servidor** a partir de `opcion_seleccionada.es_correcta` — aunque
  el cliente lo mande en el payload, se ignora.
- Si `opcion_seleccionada` no pertenece a `bloque`: `400` con
  `{"opcion_seleccionada": "Esa opción no pertenece al bloque indicado."}`.
- No hay `PATCH`: cada envío es un intento nuevo e inmutable (`405` si se intenta editar).
- `GET /api/capacitacion/mis-respuestas-bloque/` devuelve solo los intentos del usuario autenticado
  (paginado, igual que el resto).

---

## 8. Reordenamiento en lote

Mismo patrón para **bloques, ítems, archivos y opciones** — una sola llamada, transacción
atómica (todo o nada):

| Recurso | Endpoint | Campo de agrupación en el body |
|---|---|---|
| Bloques | `PATCH /api/capacitacion/bloques/reordenar/` | `"tema": <id>` |
| Ítems | `PATCH /api/capacitacion/bloque-items/reordenar/` | `"bloque": <id>` |
| Archivos | `PATCH /api/capacitacion/bloque-archivos/reordenar/` | `"bloque": <id>` |
| Opciones | `PATCH /api/capacitacion/bloque-opciones/reordenar/` | `"bloque": <id>` |

Body:

```json
{ "tema": 14, "orden": [{ "id": 101, "orden": 1 }, { "id": 98, "orden": 2 }, { "id": 99, "orden": 3 }] }
```

Éxito (`200`): devuelve la lista completa ya reordenada del grupo (mismo shape que el `list`
normal) — úsala para resincronizar el estado local sin otro `GET`.

Errores (`400`), sin aplicar ningún cambio:

- Falta `tema`/`bloque` en el body.
- `orden` vacío o mal formado.
- Ids repetidos dentro de `orden`.
- Valores de `orden` repetidos.
- Algún id no existe o **no pertenece a ese grupo** (ej. un bloque de otro tema).

---

## 9. Autorización — qué puede ver/editar cada rol

| Rol | Alcance |
|---|---|
| Superusuario | Todo, sin restricción. |
| Administrador (empresa X) | Solo cursos de su propia `empresa` (vía `dependencia.empresa` del usuario) + cursos "globales" (`empresa=null`). Se propaga en cascada a Módulo→Tema→Bloque→Item/Archivo/Opción. |
| Colaborador | Solo lectura de contenido activo + escritura de su propio progreso/intentos. |

Implicaciones para el frontend:

- Un curso/módulo/tema/bloque **fuera del alcance de la empresa del usuario devuelve `404`**, no
  `403` — el backend no revela que existe. No distingas "no autorizado" de "no existe" en la UI
  para estos casos.
- `Curso.empresa` y `Curso.creado_por` son **de solo lectura para el frontend**: el backend los
  asigna automáticamente al crear (`empresa` = la del usuario autenticado) y los protege en update
  (no se puede "mover" un curso a otra empresa mandándolo en el payload, el backend lo ignora).
- Esto solo aplica a los endpoints **admin**. Los endpoints de colaborador (`/ver/`, `/mis-*`) no
  filtran por empresa — ven el catálogo completo de cursos activos, filtrado por competencias del
  puesto en `/mis-cursos/`.

---

## 10. Resumen rápido de endpoints nuevos (esta iniciativa)

```
GET    /api/catalogos/tipos-bloque/?pagination=false   -- catálogo extensible (categoria/config/capacidades)

GET    /api/capacitacion/bloque-items/?bloque=<id>
POST   /api/capacitacion/bloque-items/
PATCH  /api/capacitacion/bloque-items/<id>/
DELETE /api/capacitacion/bloque-items/<id>/
PATCH  /api/capacitacion/bloque-items/reordenar/

GET    /api/capacitacion/bloque-archivos/?bloque=<id>
POST   /api/capacitacion/bloque-archivos/              (multipart)
DELETE /api/capacitacion/bloque-archivos/<id>/
PATCH  /api/capacitacion/bloque-archivos/reordenar/

GET    /api/capacitacion/bloque-opciones/?bloque=<id>   -- admin, incluye es_correcta
POST   /api/capacitacion/bloque-opciones/
PATCH  /api/capacitacion/bloque-opciones/<id>/
DELETE /api/capacitacion/bloque-opciones/<id>/
PATCH  /api/capacitacion/bloque-opciones/reordenar/

GET    /api/capacitacion/mis-respuestas-bloque/         -- colaborador, propias respuestas
POST   /api/capacitacion/mis-respuestas-bloque/          { bloque, opcion_seleccionada }

PATCH  /api/capacitacion/bloques/reordenar/
```

---

## Changelog de este contrato

- v1 (2026-11-07): catálogo extensible, `ContenidoBloqueItem`/`Archivo`/`Opcion`/`Respuesta`,
  reorder en lote para bloques/items/archivos/opciones, scoping por empresa en endpoints admin,
  15 tipos de bloque activos.
