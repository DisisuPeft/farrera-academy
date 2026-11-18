from datetime import date

from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from capacitacion.models import (
    ContenidoBloque, ContenidoBloqueOpcion, ContenidoBloqueRespuesta, Inscripcion, Periodo,
)
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class ContenidoBloqueRespuestaInscripcionTests(CapacitacionTestBase):
    """T011: ContenidoBloqueRespuesta gana `inscripcion` (FK PROTECT NOT NULL),
    pierde `colaborador` directo. Sin `unique_together` nueva — múltiples
    intentos por inscripción siguen siendo comportamiento existente."""

    def setUp(self):
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion
        self.bloque = ContenidoBloque.objects.create(tema=self.tema_a, tipo=self.tipo_opcion_multiple)
        self.opcion = ContenidoBloqueOpcion.objects.create(bloque=self.bloque, texto='Opción 1', es_correcta=True)

    def test_colaborador_ya_no_existe_como_campo_directo(self):
        with self.assertRaises(FieldDoesNotExist):
            ContenidoBloqueRespuesta._meta.get_field('colaborador')

    def test_crear_respuesta_requiere_inscripcion(self):
        respuesta = ContenidoBloqueRespuesta.objects.create(
            inscripcion=self.inscripcion, bloque=self.bloque, opcion_seleccionada=self.opcion, es_correcta=True,
        )
        self.assertEqual(respuesta.inscripcion, self.inscripcion)

    def test_inscripcion_es_obligatoria(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ContenidoBloqueRespuesta.objects.create(
                    inscripcion=None, bloque=self.bloque, opcion_seleccionada=self.opcion, es_correcta=True,
                )

    def test_permite_multiples_intentos_por_inscripcion(self):
        primero = ContenidoBloqueRespuesta.objects.create(
            inscripcion=self.inscripcion, bloque=self.bloque, opcion_seleccionada=self.opcion, es_correcta=True,
        )
        segundo = ContenidoBloqueRespuesta.objects.create(
            inscripcion=self.inscripcion, bloque=self.bloque, opcion_seleccionada=self.opcion, es_correcta=True,
        )
        self.assertNotEqual(primero.pk, segundo.pk)
        self.assertEqual(
            ContenidoBloqueRespuesta.objects.filter(inscripcion=self.inscripcion, bloque=self.bloque).count(), 2,
        )

    def test_no_se_puede_borrar_una_inscripcion_con_respuesta(self):
        ContenidoBloqueRespuesta.objects.create(
            inscripcion=self.inscripcion, bloque=self.bloque, opcion_seleccionada=self.opcion, es_correcta=True,
        )
        with self.assertRaises(ProtectedError):
            self.inscripcion.delete()
