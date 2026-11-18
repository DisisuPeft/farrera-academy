from django.core.management.base import BaseCommand
from django.db import transaction

from catalogos.models import TipoBloqueContenido
from catalogos.models.capacitacion import CategoriaPedagogica

# codigo -> (nombre, categoria, descripcion, config, capacidades)
TIPOS = {
    "texto-imagen": (
        "Texto con imagen", CategoriaPedagogica.CONTENIDO,
        "Bloque de texto acompañado de una imagen.",
        {"campos": ["texto", "imagen_url", "imagen_archivo"]},
        ["soporta_imagen"],
    ),
    "texto-video": (
        "Texto con video", CategoriaPedagogica.CONTENIDO,
        "Bloque de texto con un video embebido o subido.",
        {"campos": ["texto", "video_url", "video_archivo"]},
        ["soporta_video", "soporta_streaming"],
    ),
    "texto-elemento-dinamico": (
        "Texto con elemento dinámico", CategoriaPedagogica.CONTENIDO,
        "Imagen que se amplía en un lightbox al hacer clic (variante: 'dinamico').",
        {"campos": ["texto", "imagen_url", "imagen_archivo", "variante"], "defaults": {"variante": "dinamico"}},
        ["soporta_imagen", "interactivo"],
    ),
    "texto-presentacion-paneles": (
        "Texto con presentación y paneles", CategoriaPedagogica.CONTENIDO,
        "Carrusel de paneles superpuestos, cada uno con imagen y lista de ítems.",
        {"campos": ["texto"], "items": "bloque_items"},
        ["soporta_items", "soporta_imagen_por_item", "carrusel"],
    ),
    "texto-presentacion": (
        "Texto con presentación", CategoriaPedagogica.CONTENIDO,
        "Carrusel simple de diapositivas con imagen.",
        {"campos": ["texto"], "items": "bloque_items"},
        ["soporta_items", "soporta_imagen_por_item", "carrusel"],
    ),
    "texto-paneles": (
        "Texto con paneles", CategoriaPedagogica.CONTENIDO,
        "Carrusel de paneles con título, imagen y lista de datos libres.",
        {"campos": ["texto"], "items": "bloque_items"},
        ["soporta_items", "soporta_imagen_por_item", "carrusel"],
    ),
    "texto-tarjetas": (
        "Texto con tarjetas", CategoriaPedagogica.CONTENIDO,
        "Grilla de tarjetas, cada una con título, texto breve e imagen de fondo.",
        {"campos": ["texto"], "items": "bloque_items"},
        ["soporta_items", "soporta_imagen_por_item"],
    ),
    "texto-audio": (
        "Texto con audio", CategoriaPedagogica.CONTENIDO,
        "Bloque de texto con uno o varios archivos de audio adjuntos.",
        {"campos": ["texto"], "archivos": "archivos"},
        ["soporta_archivo_audio"],
    ),
    "texto-documento": (
        "Texto con documento", CategoriaPedagogica.CONTENIDO,
        "Bloque de texto con uno o varios documentos descargables adjuntos.",
        {"campos": ["texto"], "archivos": "archivos"},
        ["soporta_archivo_documento", "descargable"],
    ),
    "texto-galeria": (
        "Texto con galería", CategoriaPedagogica.CONTENIDO,
        "Galería de imágenes, cada una con su propio título/pie de foto opcional.",
        {"campos": ["texto"], "items": "bloque_items"},
        ["soporta_items", "soporta_imagen_por_item", "carrusel"],
    ),
    "acordeon": (
        "Acordeón", CategoriaPedagogica.EXPLORACION,
        "Lista de secciones colapsables; cada ítem es un encabezado (titulo) "
        "que al expandirse muestra su contenido (texto).",
        {"campos": ["texto"], "items": "bloque_items", "items_campos": ["titulo", "texto"]},
        ["soporta_items", "colapsable"],
    ),
    "tarjetas-giratorias": (
        "Tarjetas giratorias", CategoriaPedagogica.EXPLORACION,
        "Tarjetas con efecto flip: 'titulo' + 'imagen' van en el frente, "
        "'texto' es el contenido que se revela al voltear la tarjeta.",
        {"campos": ["texto"], "items": "bloque_items", "items_campos": ["titulo", "imagen_url", "imagen_archivo", "texto"]},
        ["soporta_items", "soporta_imagen_por_item", "interactivo"],
    ),
    "aviso-destacado": (
        "Aviso destacado", CategoriaPedagogica.ESTRUCTURA_NAVEGACION,
        "Mensaje resaltado (info/éxito/advertencia/error) usando 'variante' "
        "para indicar el estilo.",
        {"campos": ["texto", "variante"], "variante_valores": ["info", "exito", "advertencia", "error"]},
        ["requiere_variante"],
    ),
    "separador": (
        "Separador", CategoriaPedagogica.ESTRUCTURA_NAVEGACION,
        "Línea divisoria entre secciones. Puramente visual, sin contenido propio.",
        {"campos": []},
        [],
    ),
    "objetivos-aprendizaje": (
        "Objetivos de aprendizaje", CategoriaPedagogica.ESTRUCTURA_NAVEGACION,
        "Lista de objetivos del módulo/tema; cada ítem es un objetivo (titulo).",
        {"campos": ["texto"], "items": "bloque_items", "items_campos": ["titulo"]},
        ["soporta_items"],
    ),
    "opcion-multiple": (
        "Opción múltiple", CategoriaPedagogica.EVALUACION,
        "Pregunta rápida embebida en la lección, con varias opciones de "
        "respuesta ('opciones', vía /capacitacion/bloque-opciones/). Distinta "
        "del sistema formal de Evaluacion/Pregunta (evaluación de módulo/curso).",
        {"campos": ["texto"], "opciones": "opciones"},
        ["soporta_opciones", "autoevaluable", "no_requiere_calificacion_manual"],
    ),
    "verdadero-falso": (
        "Verdadero o falso", CategoriaPedagogica.EVALUACION,
        "Afirmación con dos opciones fijas (Verdadero / Falso) vía 'opciones'. "
        "Mismo mecanismo que 'opcion-multiple', con exactamente 2 opciones.",
        {"campos": ["texto"], "opciones": "opciones", "opciones_fijas": ["Verdadero", "Falso"]},
        ["soporta_opciones", "autoevaluable", "no_requiere_calificacion_manual"],
    ),
}


class Command(BaseCommand):
    help = (
        "Crea o actualiza (sin borrar) el catálogo de tipos de bloque de contenido: "
        "backfill de categoría/config/capacidades en los tipos existentes y alta de "
        "los tipos nuevos priorizados en cada incremento."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        for orden, (codigo, (nombre, categoria, descripcion, config, capacidades)) in enumerate(TIPOS.items()):
            obj, created = TipoBloqueContenido.objects.update_or_create(
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "orden": orden,
                    "categoria": categoria,
                    "descripcion": descripcion,
                    "config": config,
                    "capacidades": capacidades,
                    "version_esquema": 1,
                },
            )
            self.stdout.write(f"{'Creado' if created else 'Actualizado'}: {obj.nombre} ({obj.codigo})")

        self.stdout.write(self.style.SUCCESS("Catálogo de tipos de bloque sincronizado correctamente."))
