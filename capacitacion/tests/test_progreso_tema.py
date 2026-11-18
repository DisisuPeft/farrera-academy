from datetime import date

from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from capacitacion.models import Inscripcion, Periodo, ProgresoTema
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class ProgresoTemaInscripcionTests(CapacitacionTestBase):
    """T009: ProgresoTema gana `inscripcion` (FK PROTECT NOT NULL), pierde
    `colaborador` directo, unique_together pasa a (inscripcion, tema)."""

    def setUp(self):
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_colaborador_ya_no_existe_como_campo_directo(self):
        with self.assertRaises(FieldDoesNotExist):
            ProgresoTema._meta.get_field('colaborador')

    def test_crear_progreso_requiere_inscripcion(self):
        progreso = ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        self.assertEqual(progreso.inscripcion, self.inscripcion)

    def test_inscripcion_es_obligatoria(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProgresoTema.objects.create(inscripcion=None, tema=self.tema_a)

    def test_unicidad_es_por_inscripcion_y_tema_no_por_colaborador(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)

    def test_no_se_puede_borrar_una_inscripcion_con_progreso(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        with self.assertRaises(ProtectedError):
            self.inscripcion.delete()
