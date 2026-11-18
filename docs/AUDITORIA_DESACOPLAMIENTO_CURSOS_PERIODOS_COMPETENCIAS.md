# Auditoría de desacoplamiento — cursos, periodos, inscripciones y competencias

**Alcance de este documento:** análisis de código existente únicamente. No se modificó código, no se generaron migraciones, no se crearon modelos. Todo lo afirmado está respaldado por lectura directa de archivos citados por ruta/clase/línea. Donde el código no permite confirmar algo, se marca explícitamente como **riesgo potencial** o **decisión de producto pendiente**, nunca como hecho.

Leyenda usada en todo el documento:
- 🟢 **Confirmado por código** — verificado leyendo el archivo citado.
- 🟡 **Riesgo potencial** — reproducible a partir del código, pero depende de una secuencia de eventos que no está garantizado que ocurra en producción.
- 🔵 **Decisión de producto pendiente** — el código no decide esto; requiere una elección del equipo.

---

## 1. Mapa real de relaciones actuales

```
Curso (capacitacion/models/curso.py:6)
 ├─ status → catalogos.CatalogStatus         [PROTECT]
 ├─ empresa → sistema.Empresa                [PROTECT, null=True]
 ├─ creado_por → User                        [SET_NULL, null=True]
 ├─ modulos → Modulo                         [related_name, hijo CASCADE]
 ├─ inscripciones → Inscripcion              [related_name, hijo PROTECT]
 ├─ evaluaciones → Evaluacion                 [related_name, hijo CASCADE]
 ├─ competencia_cursos → CompetenciaCurso    [related_name, hijo PROTECT]
 └─ ruta_cursos → RutaAprendizajeCurso       [related_name, hijo PROTECT]

Modulo (curso.py:51) --CASCADE--> Curso
 ├─ temas → Tema                             [CASCADE]
 └─ evaluaciones → Evaluacion                [CASCADE, null=True]

Tema (curso.py:75) --CASCADE--> Modulo
 ├─ tipo → catalogos.TipeTema                [PROTECT]
 ├─ bloques → ContenidoBloque                [CASCADE]
 └─ progresos → ProgresoTema                 [related_name, hijo PROTECT]

ContenidoBloque (curso.py:101) --CASCADE--> Tema
 ├─ tipo → catalogos.TipoBloqueContenido     [PROTECT]
 ├─ bloque_items → ContenidoBloqueItem       [CASCADE]
 ├─ archivos → ContenidoBloqueArchivo        [CASCADE]
 ├─ opciones → ContenidoBloqueOpcion         [CASCADE]
 └─ respuestas → ContenidoBloqueRespuesta    [related_name, hijo PROTECT]

ContenidoBloqueOpcion (curso.py:199) --CASCADE--> ContenidoBloque
 └─ respuestas → ContenidoBloqueRespuesta    [related_name, hijo PROTECT]

Inscripcion (capacitacion/models/progreso.py:6)
 ├─ colaborador → User                       [PROTECT]
 ├─ curso → Curso                            [PROTECT]
 └─ unique_together = [('colaborador', 'curso')]   ← ver §3.1

ProgresoTema (progreso.py:35)
 ├─ colaborador → User                       [PROTECT]
 ├─ tema → Tema                              [PROTECT]
 ├─ SIN FK a Inscripcion
 └─ unique_together = [('colaborador', 'tema')]

ResultadoEvaluacion (progreso.py:59)
 ├─ colaborador → User                       [PROTECT]
 ├─ evaluacion → Evaluacion                  [PROTECT]
 ├─ SIN FK a Inscripcion
 └─ sin unique_together (múltiples resultados posibles, sin distinguir intento)

ContenidoBloqueRespuesta (curso.py:227)
 ├─ colaborador → User                       [PROTECT]
 ├─ bloque → ContenidoBloque                 [PROTECT]
 ├─ opcion_seleccionada → ContenidoBloqueOpcion [PROTECT]
 ├─ SIN FK a Inscripcion
 └─ sin unique_together

CompetenciaCurso (competencias/models/competencia.py:28)
 ├─ competencia → Competencia                [PROTECT]
 ├─ curso → Curso                            [PROTECT]
 ├─ nivel → catalogos.NivelCompetencia       [PROTECT]
 └─ unique_together = [('competencia', 'curso')]   ← un curso, un nivel, por competencia

CompetenciaColaborador (competencias/models/colaborador.py:6)
 ├─ colaborador → User                       [PROTECT]
 ├─ competencia → Competencia                [PROTECT]
 ├─ nivel → catalogos.NivelCompetencia       [PROTECT]
 ├─ origen → Inscripcion                     [SET_NULL, null=True]  ← única traza hacia atrás
 └─ unique_together = [('colaborador', 'competencia')]  ← UNA fila por colaborador+competencia

CompetenciaPuesto (competencia.py:66)
 ├─ competencia → Competencia                [PROTECT]
 ├─ puesto → sistema.Puesto                  [PROTECT]
 ├─ nivel → catalogos.NivelCompetencia       [PROTECT]
 └─ unique_together = [('competencia', 'puesto')]

NivelCompetencia (catalogos/models/competencias.py:4, hereda BaseCatalogo)
 └─ orden = PositiveSmallIntegerField(default=0)   ← comparación de "mayor nivel", libre, sin unicidad
```

**Ninguna entidad de tipo periodo/campaña/convocatoria/generación/asignación/impartición existe en el código.** 🟢 Verificado por `grep -rniE "periodo|campaña|convocatoria|generacion|impartici"` sobre todo `.py` del proyecto (excluyendo migraciones y cachés): cero resultados.

---

## 2. Diagnóstico de inscripción y desempeño (respuestas a las 10 preguntas de §3)

**1. ¿Puede un colaborador inscribirse más de una vez en el mismo curso?**
🟢 No. `Inscripcion.Meta.unique_together = [('colaborador', 'curso')]` (`progreso.py:24`) lo impide a nivel de base de datos. Un segundo `POST` a `/mis-inscripciones/` o `/capacitacion/inscripciones/` con el mismo par produce `IntegrityError` (500) salvo que el código llamante use `get_or_create` — que es justo lo que hace `MiInscripcionRutaPerfil.post` (`competencias/views.py:301`), devolviendo la inscripción existente en vez de crear una nueva.

**2. ¿Existe alguna restricción de unicidad que lo impida?**
🟢 Sí, la misma del punto 1. Es la restricción raíz que bloquea el Caso F (repetición) completo.

**3. ¿El progreso está asociado a una inscripción específica o solamente a colaborador y contenido?**
🟢 Solo a colaborador y contenido. `ProgresoTema` (`progreso.py:35-56`) tiene FK a `colaborador` y `tema`, sin FK a `Inscripcion`. Mismo patrón en `ResultadoEvaluacion` (`progreso.py:59-81`) y en `ContenidoBloqueRespuesta` (`curso.py:227-258`).

**4. ¿Las evaluaciones y respuestas pueden distinguir participaciones diferentes?**
🟢 No. Ninguno de los tres modelos de evidencia (`ProgresoTema`, `ResultadoEvaluacion`, `ContenidoBloqueRespuesta`) tiene FK a `Inscripcion` ni a ningún identificador de "intento" o "ejecución". Si hoy fuera posible repetir un curso (no lo es, ver punto 1), no habría forma de saber a cuál de las dos pasadas pertenece un resultado.

**5. ¿Qué ocurre si un colaborador repite un curso?**
🟢 Hoy, estructuralmente, no puede: el segundo intento de crear la `Inscripcion` falla por la restricción de unicidad. La única vía de "repetir" sería que un administrador reabra la inscripción existente (editar `completado_at` a `null` vía `InscripcionViewSet`, que es un `ModelViewSet` completo sin restricción adicional — `capacitacion/views.py:433`), pero eso reutiliza la misma fila: no crea una segunda participación, reescribe la única que existe.

**6. ¿Se sobrescribe el resultado anterior?**
🟡 Depende del modelo:
- `ProgresoTema`: unique_together(`colaborador`,`tema`) — un segundo `POST` para el mismo tema falla por `IntegrityError`, no sobrescribe silenciosamente (riesgo potencial de 500 no controlado, no de sobrescritura).
- `ResultadoEvaluacion`: sin unicidad — un reintento de la misma evaluación simplemente **inserta una fila nueva**, acumulando resultados sin reemplazar el anterior ni marcar cuál es el vigente.
- `ContenidoBloqueRespuesta`: igual que `ResultadoEvaluacion`, sin unicidad, acumula (es el comportamiento documentado a propósito: "cada envío es un intento nuevo", comentario en `views_colaborador.py:97`).
- `CompetenciaColaborador`: **sí se sobrescribe** por diseño — `unique_together('colaborador','competencia')` garantiza una sola fila vigente; el signal reemplaza `nivel` y `origen` en el lugar (`competencias/signals.py:39-41`).

**7. ¿Es posible consultar el desempeño histórico de una participación finalizada?**
🟢 Parcialmente. Como no hay repetición posible (punto 1), hoy "la" participación es la única fila de `Inscripcion` que existe para ese par colaborador-curso, y sus `ProgresoTema`/`ResultadoEvaluacion` relacionados se consultan filtrando por colaborador+tema/evaluación (no hay forma más fina). Para `CompetenciaColaborador`, el campo `origen` (`colaborador.py:21-26`) permite saber **qué inscripción fue la última en otorgar o subir el nivel actual** — pero no conserva un registro de niveles otorgados previamente si luego subieron: al sobrescribirse `nivel`/`origen`, el nivel anterior no queda en ningún lado.

**8. ¿Qué relaciones dependen directamente de un contenido editable?**
🟢 `ProgresoTema.tema` (PROTECT), `ContenidoBloqueRespuesta.bloque` y `.opcion_seleccionada` (ambos PROTECT), `ResultadoEvaluacion.evaluacion` (PROTECT). Los cuatro apuntan directamente a filas que un administrador puede editar en cualquier momento desde el constructor visual (`Tema`, `ContenidoBloque`, `ContenidoBloqueOpcion`, `Evaluacion` son todos editables vía los ViewSets de `capacitacion/views.py`).

**9. ¿Qué sucedería si ese contenido se modifica o elimina?**
- **Se modifica (UPDATE):** 🟢 el cambio es inmediato y retroactivo en apariencia — no existe ningún mecanismo de versionado de contenido (`Tema`/`ContenidoBloque`/`ContenidoBloqueOpcion` heredan de `BaseModel`, que no tiene campos de versión; confirmado leyendo `common/models.py` y `curso.py` completos). El puntaje ya registrado en `ResultadoEvaluacion.correctas/total` o en `ContenidoBloqueRespuesta.es_correcta` **sí sobrevive** porque son valores server-computed almacenados en la fila del intento, no recalculados — pero el *contenido que el colaborador efectivamente vio* (texto de la pregunta, de las opciones) no se conserva en ningún lado. Si después se audita esa respuesta, solo se puede ver la pregunta tal como está *hoy*, no como estaba cuando se respondió.
- **Se elimina (DELETE):** 🟢 bloqueado por diseño mientras exista evidencia. Un intento de `DELETE` sobre un `ContenidoBloque` con `ContenidoBloqueRespuesta` asociadas falla con `ProtectedError` (comportamiento ya reproducido empíricamente en este proyecto durante la limpieza de tests, según el historial de esta sesión). Lo mismo aplica en cascada: borrar un `Tema` intenta cascadear a sus `ContenidoBloque`, y si alguno tiene respuestas protegidas, la operación completa falla.

**10. ¿Qué efectos tendría introducir una entidad de periodo o campaña?**
Ver comparación de alternativas en §4. En síntesis: ninguno de los modelos existentes impide agregar una entidad de periodo de forma aditiva (FK nueva, nullable, sin tocar las relaciones ya descritas), siempre que se mantenga **fuera** del árbol `Curso→Modulo→Tema→ContenidoBloque` (que debe seguir representando *el contenido*, no la ejecución).

---

## 3. Auditoría de la señal de acreditación — riesgo de reprocesamiento

### 3.1 Lectura exacta de la señal

`competencias/signals.py:5-41`, registrada en `competencias/apps.py::ready()`:

```python
@receiver(post_save, sender='capacitacion.Inscripcion')
def acreditar_competencias_al_completar(sender, instance, **kwargs):
    if not instance.completado_at:
        return
    ...
    for cc in competencia_cursos:   # CompetenciaCurso.objects.filter(curso=instance.curso, activo=True)
        registro = CompetenciaColaborador.objects.filter(colaborador=..., competencia=cc.competencia).first()
        if registro is None:
            CompetenciaColaborador.objects.create(..., nivel=cc.nivel, origen=instance)
        elif cc.nivel.orden > registro.nivel.orden:
            registro.nivel = cc.nivel
            registro.origen = instance
            registro.save(update_fields=['nivel', 'origen', 'actualizado_at'])
```

**Punto crítico, confirmado por código:** la condición de disparo es `if not instance.completado_at: return` — es decir, se ejecuta en **cada `save()`** de cualquier `Inscripcion` cuyo `completado_at` esté poblado, sin comparar contra el valor anterior ni verificar que se trate de una transición `None → valor`. Django no distingue "primera vez que se completa" de "se volvió a guardar y ya estaba completada".

### 3.2 Reproducción del escenario del prompt

> Curso A acredita nivel 2 → colaborador completa y obtiene nivel 2 → admin cambia `CompetenciaCurso` de A a nivel 3 → se vuelve a guardar la inscripción histórica.

Trazando el código paso a paso:

1. Colaborador completa curso A. `Inscripcion.completado_at` se puebla (vía `PATCH /mis-inscripciones/{id}/`, campo escribible — ver §3.4). Signal corre, crea/actualiza `CompetenciaColaborador` con `nivel=2`, `origen=<esa inscripcion>`.
2. Admin edita `CompetenciaCurso` (curso=A) de `nivel=2` a `nivel=3` vía `CompetenciaCursoViewSet` (`competencias/views.py:52`, `ModelViewSet` completo, `PATCH` permitido). **Esto por sí solo no dispara nada** — el signal está en `Inscripcion`, no en `CompetenciaCurso`. Hasta aquí, no hay riesgo.
3. Si en cualquier momento posterior algo ejecuta `.save()` sobre esa misma `Inscripcion` (ejemplos reales y alcanzables vía API hoy: un admin hace `PATCH /capacitacion/inscripciones/{id}/` para corregir cualquier otro campo del serializer — `activo`, o reenviar el mismo `completado_at`; o el propio colaborador reenvía `PATCH /mis-inscripciones/{id}/` con el mismo valor), el `post_save` vuelve a correr. `completado_at` sigue poblado → la condición de guarda no detiene nada → se vuelve a consultar `CompetenciaCurso` (ahora nivel 3) → `3 > 2` → **se sube el nivel del colaborador a 3 sin que haya realizado ninguna nueva formación.**

🟢 **Confirmado por código: el riesgo existe tal como lo describe el prompt**, y no requiere ninguna acción maliciosa — basta con cualquier `save()` incidental sobre una `Inscripcion` ya completada, mientras la configuración de `CompetenciaCurso` haya cambiado entretanto.

### 3.3 Preguntas adicionales de §4

- **¿Existe evidencia persistente del nivel otorgado?** 🟡 Solo del *último* nivel otorgado. `CompetenciaColaborador` tiene `unique_together('colaborador','competencia')` — es una sola fila que se sobreescribe (`nivel`, `origen`) cada vez que sube. No hay bitácora de niveles anteriores.
- **¿Puede identificarse qué inscripción originó una acreditación?** 🟢 Sí, pero solo la más reciente: `CompetenciaColaborador.origen` (FK a `Inscripcion`, `SET_NULL`). Si el nivel subió dos veces, `origen` apunta a la inscripción que causó la *última* subida, no a la que causó la primera.
- **¿Cambiar o eliminar una relación `CompetenciaCurso` afecta la interpretación histórica?** 🟢 Cambiarla no reescribe nada por sí sola (ver paso 2 arriba), pero crea la condición para que un `save()` posterior sí reescriba el nivel del colaborador de forma retroactivamente incorrecta (§3.2). Eliminarla (`CompetenciaCurso` es `BaseModel + SoftDeleteModel`, así que "eliminar" vía la API es soft-delete — `_BaseSoftDeleteViewSet.destroy`, `competencias/views.py:34`) solo saca la fila del `filter(activo=True)` del signal hacia adelante; no toca `CompetenciaColaborador` ya otorgado.
- **¿`CompetenciaColaborador` funciona como estado acumulado o como registro histórico?** 🟢 Exclusivamente como **estado acumulado actual**. No es, ni pretende ser, un historial — el propio `unique_together` lo impide estructuralmente.
- **¿Qué ocurre cuando cambian los niveles requeridos por un puesto?** 🟢 `CompetenciaPuesto` se edita independientemente; `MiPerfilCompetenciasView` (`competencias/views.py:135`) calcula la brecha (`brecha = cp.nivel.orden - nivel_actual_orden`) **en tiempo de consulta**, siempre contra el requisito vigente — correcto y ya resuelve el Caso E sin cambios: el desempeño histórico (`CompetenciaColaborador.nivel`) no se altera por un cambio de requisito, solo cambia si el colaborador "cumple" o no al recalcular la brecha.

**No confundir: el nivel históricamente acreditado (`CompetenciaColaborador.nivel`, que persiste) y el cumplimiento actual del puesto (`brecha <= 0`, que se recalcula en cada request) ya están correctamente separados en el código para el caso de *puestos*.** El problema de §3.2 es distinto: no es que el requisito cambie, es que la **fuente que otorgó el nivel** (`CompetenciaCurso`) cambia y el signal no distingue "nueva formación" de "resave accidental".

### 3.4 Confirmación de que `completado_at` es autoreportable sin validación

🟢 `MiInscripcionSerializer` (`capacitacion/serializers/colaborador.py:11-17`): `fields = ('id', 'curso', 'curso_titulo', 'inscrito_at', 'completado_at', 'activo')`, `read_only_fields = ('inscrito_at', 'activo')`. **`completado_at` NO está en `read_only_fields`** — el colaborador puede `PATCH /mis-inscripciones/{id}/` con cualquier fecha y marcarse a sí mismo como completado, sin que el servidor valide que haya `ProgresoTema` para todos los `Tema` del curso ni que haya aprobado ninguna `Evaluacion`. Esto es ortogonal al problema de periodos, pero **agrava** el riesgo de §3.2: cada vez que esto ocurre, la señal se ejecuta de nuevo.

### 3.5 Corrección mínima propuesta (no implementada)

El riesgo no está en la intención de la señal (acreditar al completar), sino en que usa **presencia de valor** como proxy de **evento de completar**. La corrección mínima que resuelve esto sin tocar la lógica de comparación de niveles (que el prompt pide no reemplazar sin justificar — y aquí no hace falta reemplazarla, solo *cuándo* se dispara):

> Disparar la acreditación únicamente en la transición `completado_at: None → valor`, no en cualquier `save()` donde ya esté poblado. Esto se puede lograr sin un modelo nuevo, comparando contra el valor previo en un `pre_save`/`post_save` combinado (patrón `update_fields` o lectura de `Inscripcion.objects.get(pk=...).completado_at` antes del save, o — más simple y explícito — moviendo el disparo de la acreditación de un signal implícito a una llamada explícita en el único punto donde el código actual pone `completado_at` por primera vez.

Esto es una propuesta de dirección, no una implementación — queda sujeta a validación del usuario antes de tocar código, igual que el resto de este documento.

---

## 4. Evaluación del desacoplamiento — alternativas A/B/C

### Alternativa A — Reforzar inscripción y evidencia, sin entidad nueva

**Cambios que requeriría:** quitar o redefinir `unique_together('colaborador','curso')` en `Inscripcion`; añadir FK (nullable) de `Inscripcion` en `ProgresoTema` y `ResultadoEvaluacion` para atribuir cada evidencia a una participación concreta.

- **Ventajas:** no introduce ningún concepto nuevo; el modelo mental del equipo no cambia.
- **Limitaciones reales:**
  - Para permitir repetición pero bloquear dos inscripciones *abiertas* simultáneas al mismo curso, se necesitaría una restricción única condicional (`UniqueConstraint(condition=Q(completado_at__isnull=True))`). 🟡 Riesgo técnico: Django documenta que las restricciones únicas condicionales dependen del soporte del motor de base de datos — MySQL (el motor de este proyecto, confirmado en `requirements.txt`: `mysqlclient`) no soporta índices únicos parciales de forma nativa antes de version reciente con sintaxis distinta a la que Django genera para Postgres/SQLite; validar esto con una prueba real antes de asumir que funciona, no esta documentado como garantizado.
  - No da un lugar natural para responder "qué ejecuciones distintas existen de este curso" — solo da filas repetidas de `Inscripcion` sin ningún agrupador conceptual.
- **Compatibilidad con datos existentes:** alta — todo lo nuevo es aditivo (FKs nullable), salvo el cambio de unicidad en `Inscripcion`, que no afecta filas existentes (todas cumplen la restricción actual, que es más estricta).

### Alternativa B — Periodo/Impartición entre curso e inscripción

**Cambios que requeriría:** nueva entidad (p. ej. `PeriodoCapacitacion` o `ImparticionCurso`) con FK a `Curso`; `Inscripcion` gana FK (nullable, para compatibilidad retroactiva) a esa entidad; `unique_together` se traslada de `('colaborador','curso')` a `('colaborador','periodo')`.

- **Ventajas:**
  - Resuelve el Caso F de forma natural: dos periodos distintos del mismo curso ya son, por construcción, dos relaciones distintas — sin pelear con restricciones condicionales de MySQL.
  - Da un lugar conceptual real a "distinguir ejecuciones del mismo curso", que es exactamente lo que pide la §5 del prompt, sin forzarlo dentro de `Inscripcion`.
  - **No toca la señal de competencias.** El signal sigue escuchando `post_save` sobre `Inscripcion` sin cambios estructurales — solo ahora cada `Inscripcion` cuelga de un periodo en vez de directamente del curso. Esto respeta la restricción explícita de no reemplazar la lógica de competencias.
  - Migración segura: FK nueva nullable en `Inscripcion`, entidad nueva sin dependencias previas — no reescribe filas existentes, pueden quedar con `periodo=None` indefinidamente si no se requiere backfill.
- **Limitaciones:** añade un concepto nuevo que el equipo debe aprender a usar correctamente (cuándo crear un periodo nuevo vs. reutilizar uno abierto) — es una decisión de producto, no solo técnica.
- **Compatibilidad:** alta, igual razón que arriba (aditivo).

### Alternativa C — Periodo + asignación de materiales por periodo

Igual que B, más una tabla intermedia que asigna subconjuntos de `Modulo`/`Tema`/`ContenidoBloque` a cada periodo.

- **Ventajas:** permitiría que distintas ejecuciones del mismo curso tengan distinto material habilitado.
- **Limitaciones:** 🔵 no hay ninguna evidencia en el código ni en los documentos previos de que esto sea un requisito actual — el prompt mismo advierte "no debe convertirse en una copia completa del curso" y "no amplíes innecesariamente el alcance". El árbol `Curso→Modulo→Tema→ContenidoBloque` ya es la fuente única del contenido; una tabla de asignación por periodo duplicaría esa responsabilidad sin que exista hoy un caso de uso que lo demande. Es la alternativa de mayor complejidad real (nueva tabla intermedia + lógica de resolución "qué material ve este colaborador en este periodo" en cada endpoint de lectura de colaborador) para un problema no demostrado.

### Recomendación

**Alternativa B**, sin la capa de asignación de materiales de C. Es la más simple que resuelve lo demostrado (Caso F, "distinguir ejecuciones") sin tocar la señal de competencias ni tensionar los límites conocidos de MySQL con restricciones condicionales, y sin construir una capacidad (material por periodo) para la que no hay evidencia de necesidad.

---

## 5. Contenido educativo y evolución (§6 del prompt)

El código actual **no distingue** estos conceptos — los trata todos como una sola cosa: el estado actual de la fila.

| Concepto | ¿Existe en el código? | Evidencia |
| --- | --- | --- |
| Identidad del recurso | 🟢 Sí — el `id` de cada fila (`Tema`, `ContenidoBloque`, etc.) | PK estándar de Django |
| Estado actual del contenido | 🟢 Sí — es lo único que hay | Los campos de cada modelo reflejan siempre el valor vigente |
| Historial técnico de modificaciones | 🔴 No existe | `BaseModel` (`common/models.py`) no tiene campos de versión ni bitácora; confirmado, es exactamente el "Nivel B — Historial persistente" que `docs/AUDITORIA_AUTOGUARDADO_CONCURRENCIA.md` (línea 86) ya marcó como pendiente y que `docs/REVISION_CONCURRENCIA_HISTORIAL_PUBLICACION.md` (línea 225) deja posponible, diseñado como bitácora de operaciones, no snapshots completos |
| Función pedagógica del recurso | 🔵 Decisión de producto | No hay campo que distinga "esto es una corrección menor" de "esto cambia el objetivo pedagógico" — el prompt mismo (Caso B vs. Caso C) asume que esta distinción la hace un humano, no el sistema |
| Evidencia histórica del desempeño | 🟡 Parcial | El *resultado numérico* sobrevive (`ResultadoEvaluacion.correctas/total`, `ContenidoBloqueRespuesta.es_correcta` son server-computed y quedan fijos en la fila del intento), pero el *contenido que el colaborador vio* no se conserva — si la pregunta o las opciones cambian después, no hay forma de reconstruir qué leyó exactamente |

**No se duplican cursos/módulos/temas/bloques completos en ningún escenario actual** — correcto, no hay ningún mecanismo de copia en el código, ni se propone aquí crear uno sin justificación.

---

## 6. Impacto sobre el constructor visual (§7 del prompt)

Cruzando contra las decisiones vigentes de `docs/REVISION_CONCURRENCIA_HISTORIAL_PUBLICACION.md` (ninguna implementada todavía — confirmado: `Tema`/`ContenidoBloque`/etc. siguen heredando solo `BaseModel`/`BaseFileEntity`, sin `revision` ni `SoftDeleteModel`, verificado leyendo `capacitacion/models/curso.py` completo en esta misma auditoría):

| Decisión previa | ¿La toca el desacoplamiento propuesto? | Conclusión |
| --- | --- | --- |
| `revision` entero + `ETag`/`If-Match` por recurso (§1 de la revisión previa) | No | Es una propiedad de cada fila de contenido (`Tema`, `ContenidoBloque`, etc.), ortogonal a si existe o no un `Periodo`. Se mantiene sin cambios. |
| Revisiones estructurales por colección (§1) | No | Misma razón — vive en el árbol de contenido, no en inscripción/periodo. |
| Soft-delete + restauración por diff (§2) | No | Resuelve "qué pasa si borro un bloque", no "qué pasa si repito un curso". Sin relación. Se mantiene. |
| Separación publicado/borrador (§4, dos reglas de filtrado) | No, pero queda igual de pendiente | Ese gap (`_base_cursos_qs()` en `views_colaborador.py:119-125` solo filtra `activo=True`, no por `status`) sigue sin corregirse — no lo introduce ni lo agrava la alternativa B, pero tampoco lo resuelve. Sigue siendo trabajo pendiente independiente. |
| Historial completo como posponible (§2, bitácora) | Parcialmente relacionado | Si se adopta B, la bitácora de operaciones eventualmente podría registrar "se abrió un nuevo periodo" como un tipo de evento más — pero esto es un desarrollo futuro, no una dependencia dura hoy. |

**Ninguna decisión previa necesita modificarse por la introducción de un periodo.** El alcance del constructor visual (edición de contenido) no se ampl ía: Alternativa B vive estrictamente en la capa de inscripción/participación, no en la capa de autoría de contenido.

---

## 7. Pruebas de los 6 escenarios — comportamiento real actual, no deseado

| Caso | Comportamiento real HOY (confirmado por código) | Prueba automatizada que falta |
| --- | --- | --- |
| **A — Formación completada, luego se actualizan materiales** | 🟢 El desempeño (`ResultadoEvaluacion`, `ContenidoBloqueRespuesta`) y la acreditación (`CompetenciaColaborador`) no se recalculan automáticamente por editar contenido — ningún signal escucha `post_save` de `Tema`/`ContenidoBloque`. Se conservan intactos. | Test que edita un `ContenidoBloque` después de que existan `ContenidoBloqueRespuesta` sobre él y verifica que estas no cambian. |
| **B — Actualización menor (no cambia nivel ni objetivos)** | 🟢 No se exige nada automáticamente — no existe ningún mecanismo que fuerce una nueva capacitación; el sistema es pasivo en este punto (ni bien ni mal, simplemente no reacciona). | No aplica una prueba de "no reacción" per se — más relevante es confirmar que editar contenido no dispara el signal de competencias (que solo escucha `Inscripcion`, ya confirmado por lectura directa del registrador). |
| **C — Actualización sustancial, requiere nueva participación** | 🔴 Hoy **no es posible** sin Alternativa B (o A): la unicidad de `Inscripcion` lo bloquea estructuralmente (§2, pregunta 1). | Test que intenta crear una segunda `Inscripcion` para el mismo colaborador+curso y confirma el `IntegrityError` actual (documentando el gap antes de cerrarlo). |
| **D — Cambio de nivel acreditado (2→3) sin nueva formación** | 🟡 **Riesgo confirmado, no mitigado** — ver §3.2. Si se re-guarda la inscripción histórica, el colaborador sube de nivel sin acción propia. | Test que reproduce exactamente la secuencia de §3.2: completar con nivel 2, cambiar `CompetenciaCurso` a nivel 3, volver a `save()` la `Inscripcion`, y afirmar que el nivel **no debería subir** (test que hoy fallaría, documentando el bug antes de corregirlo). |
| **E — Cambio de requisitos del puesto** | 🟢 Ya correcto — `MiPerfilCompetenciasView` recalcula la brecha en cada consulta contra el requisito vigente, sin tocar `CompetenciaColaborador.nivel` histórico (§3.3). | Test que cambia `CompetenciaPuesto.nivel` y confirma que `CompetenciaColaborador` no cambia, pero `brecha` sí. |
| **F — Repetición del mismo curso en dos periodos** | 🔴 No es posible hoy (mismo bloqueo que el Caso C). | Pendiente de Alternativa B: test que crea dos `Inscripcion` para el mismo colaborador+curso bajo dos periodos distintos y confirma que cada una conserva su propio `ProgresoTema`/`ResultadoEvaluacion` sin mezclarse. |

---

## 8. Plan incremental de implementación

**Nada de esto está implementado. Es una propuesta ordenada por riesgo, pendiente de validación.**

### Indispensable
1. Corregir el disparo de la señal de acreditación (§3.5) para que solo reaccione a la transición real `None → valor`, no a cualquier `save()` con el campo ya poblado. Es el único hallazgo de esta auditoría que representa un bug activo con capacidad de otorgar niveles de competencia incorrectos hoy mismo, sin requerir ningún cambio de modelo.
2. Decidir (🔵 producto) si `completado_at` debe seguir siendo autoreportable sin validación por el colaborador (§3.4), dado que alimenta directamente la acreditación de competencias.

### Recomendable
3. Alternativa B: introducir `PeriodoCapacitacion`/`ImparticionCurso` + FK nullable en `Inscripcion`, migrando la unicidad de `('colaborador','curso')` a `('colaborador','periodo')`.
4. Añadir FK nullable de `Inscripcion` en `ProgresoTema` y `ResultadoEvaluacion` para que la evidencia quede atribuida a una participación concreta (prerequisito real para que el Caso F tenga sentido: sin esto, dos periodos del mismo curso compartirían progreso por la unicidad `('colaborador','tema')` de `ProgresoTema`, que **también** habría que revisar si se adopta B — riesgo no mencionado explícitamente en el prompt pero detectado en esta lectura: hoy, aunque se resuelva la unicidad de `Inscripcion`, `ProgresoTema.unique_together('colaborador','tema')` seguiría bloqueando que el mismo colaborador complete el mismo tema dos veces en dos periodos distintos, salvo que también se le añada el periodo/inscripción a su clave de unicidad).
5. Bitácora ligera que registre, como mínimo, cada acreditación otorgada por el signal (no solo el estado final) — complementa, no reemplaza, `CompetenciaColaborador`.

### Posponible
6. Alternativa C (asignación de materiales por periodo) — sin evidencia de necesidad actual.
7. Distinción formal entre "actualización menor" y "sustancial" de contenido (Casos B/C) como campo de producto, más allá de la decisión humana implícita de crear o no un nuevo periodo.
8. Versionado pedagógico completo del contenido (fuera de alcance explícito del prompt).

---

## 9. Riesgos e impacto sobre datos históricos

- La corrección del punto 1 (indispensable) es **puramente de comportamiento del signal**, no requiere migración ni toca datos existentes.
- La Alternativa B es aditiva: FK nueva nullable, ninguna fila existente se reescribe, pueden convivir inscripciones antiguas con `periodo=None` indefinidamente.
- Cambiar la unicidad de `Inscripcion` de `('colaborador','curso')` a `('colaborador','periodo')` es seguro para los datos existentes (la restricción nueva es menos estricta que la actual, nunca puede violarla retroactivamente), pero **debe hacerse junto con la migración de datos que asigne un periodo "legado" a todas las inscripciones existentes** si se quiere mantener `periodo` como no-nulo a futuro — de lo contrario queda como campo opcional indefinidamente, lo cual es válido pero es una decisión de producto, no solo técnica.

---

**No se implementó ni modificó nada de código, no se generaron migraciones ni modelos. Este documento es únicamente el análisis solicitado, a la espera de validación de las decisiones antes de tocar código.**
