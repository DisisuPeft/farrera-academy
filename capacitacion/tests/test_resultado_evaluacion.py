from datetime import date

from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from catalogos.models import TipoEvaluacion
from capacitacion.models import Evaluacion, Inscripcion, Periodo, ResultadoEvaluacion
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase


class ResultadoEvaluacionInscripcionTests(CapacitacionTestBase):
    """T010: ResultadoEvaluacion gana `inscripcion` (FK PROTECT NOT NULL),
    pierde `colaborador` directo. Sin `unique_together` nueva — múltiples
    intentos por inscripción siguen siendo comportamiento existente intencional."""

    def setUp(self):
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion
        self.tipo_evaluacion = TipoEvaluacion.objects.create(nombre='Módulo', codigo='modulo-test')
        self.evaluacion = Evaluacion.objects.create(
            titulo='Evaluación 1', tipo=self.tipo_evaluacion, modulo=self.modulo_a,
        )

    def test_colaborador_ya_no_existe_como_campo_directo(self):
        with self.assertRaises(FieldDoesNotExist):
            ResultadoEvaluacion._meta.get_field('colaborador')

    def test_crear_resultado_requiere_inscripcion(self):
        resultado = ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion, correctas=3, total=5,
        )
        self.assertEqual(resultado.inscripcion, self.inscripcion)

    def test_inscripcion_es_obligatoria(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ResultadoEvaluacion.objects.create(inscripcion=None, evaluacion=self.evaluacion)

    def test_permite_multiples_intentos_por_inscripcion(self):
        primero = ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion, correctas=2, total=5,
        )
        segundo = ResultadoEvaluacion.objects.create(
            inscripcion=self.inscripcion, evaluacion=self.evaluacion, correctas=4, total=5,
        )
        self.assertNotEqual(primero.pk, segundo.pk)
        self.assertEqual(
            ResultadoEvaluacion.objects.filter(inscripcion=self.inscripcion, evaluacion=self.evaluacion).count(), 2,
        )

    def test_no_se_puede_borrar_una_inscripcion_con_resultado(self):
        ResultadoEvaluacion.objects.create(inscripcion=self.inscripcion, evaluacion=self.evaluacion)
        with self.assertRaises(ProtectedError):
            self.inscripcion.delete()
