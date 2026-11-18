from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from capacitacion.models import Inscripcion, Periodo
from capacitacion.tests.base import CapacitacionTestBase, hacer_usuario


class PeriodoModelTests(CapacitacionTestBase):
    def test_crear_periodo_abierto_con_fecha_inicio(self):
        periodo = Periodo.objects.create(
            curso=self.curso_a,
            nombre='Primera convocatoria',
            fecha_inicio=date(2026, 1, 1),
            estado=Periodo.Estado.ABIERTO,
        )
        self.assertEqual(periodo.curso, self.curso_a)
        self.assertIsNone(periodo.fecha_fin)
        self.assertEqual(periodo.estado, Periodo.Estado.ABIERTO)

    def test_fecha_inicio_es_obligatoria(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Periodo.objects.create(
                    curso=self.curso_a,
                    nombre='Sin fecha',
                    fecha_inicio=None,
                    estado=Periodo.Estado.ABIERTO,
                )

    def test_estado_por_defecto_es_abierto(self):
        periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Por defecto', fecha_inicio=date(2026, 1, 1),
        )
        self.assertEqual(periodo.estado, Periodo.Estado.ABIERTO)

    def test_no_se_puede_borrar_un_curso_con_periodos(self):
        Periodo.objects.create(
            curso=self.curso_a, nombre='Con periodo', fecha_inicio=date(2026, 1, 1),
        )
        with self.assertRaises(ProtectedError):
            self.curso_a.delete()

    def test_periodo_puede_marcarse_cerrado(self):
        periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Cerrado', fecha_inicio=date(2026, 1, 1),
            estado=Periodo.Estado.CERRADO,
        )
        periodo.refresh_from_db()
        self.assertEqual(periodo.estado, Periodo.Estado.CERRADO)


class InscripcionPeriodoFieldTests(CapacitacionTestBase):
    """T002: Inscripcion gana `periodo` (NOT NULL, PROTECT), conserva `curso`,
    unique_together pasa a (colaborador, periodo)."""

    def setUp(self):
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )

    def test_periodo_es_obligatorio(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Inscripcion.objects.create(
                    colaborador=self.colaborador, curso=self.curso_a, periodo=None,
                )

    def test_curso_sigue_existiendo_como_columna_real(self):
        inscripcion = Inscripcion.objects.create(
            colaborador=self.colaborador, curso=self.curso_a, periodo=self.periodo,
        )
        self.assertEqual(inscripcion.curso, self.curso_a)
        self.assertEqual(inscripcion.periodo, self.periodo)

    def test_unicidad_es_por_colaborador_y_periodo_no_por_curso(self):
        Inscripcion.objects.create(
            colaborador=self.colaborador, curso=self.curso_a, periodo=self.periodo,
        )
        otro_periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 2, 1),
        )
        # Mismo colaborador + mismo curso, pero periodo distinto: debe permitirse
        # (esto es justo lo que unique_together=(colaborador,curso) bloqueaba antes).
        segunda = Inscripcion.objects.create(
            colaborador=self.colaborador, curso=self.curso_a, periodo=otro_periodo,
        )
        self.assertNotEqual(segunda.periodo_id, self.periodo.id)

    def test_no_se_puede_duplicar_inscripcion_al_mismo_periodo(self):
        Inscripcion.objects.create(
            colaborador=self.colaborador, curso=self.curso_a, periodo=self.periodo,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Inscripcion.objects.create(
                    colaborador=self.colaborador, curso=self.curso_a, periodo=self.periodo,
                )

    def test_dos_colaboradores_distintos_pueden_inscribirse_al_mismo_periodo(self):
        otro_colaborador = hacer_usuario(self.dependencia_a)
        Inscripcion.objects.create(
            colaborador=self.colaborador, curso=self.curso_a, periodo=self.periodo,
        )
        segunda = Inscripcion.objects.create(
            colaborador=otro_colaborador, curso=self.curso_a, periodo=self.periodo,
        )
        self.assertEqual(segunda.periodo_id, self.periodo.id)

    def test_no_se_puede_borrar_un_periodo_con_inscripciones(self):
        Inscripcion.objects.create(
            colaborador=self.colaborador, curso=self.curso_a, periodo=self.periodo,
        )
        with self.assertRaises(ProtectedError):
            self.periodo.delete()
