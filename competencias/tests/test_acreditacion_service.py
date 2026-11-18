from datetime import date

from django.utils import timezone

from catalogos.models import NivelCompetencia
from capacitacion.models import Inscripcion, Periodo, ProgresoTema
from capacitacion.services.finalizacion_service import FinalizacionService
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from competencias.models import CompetenciaColaborador
from competencias.models.competencia import Competencia, CompetenciaCurso
from competencias.services.acreditacion_service import AcreditacionService


class AcreditacionServiceTests(CapacitacionTestBase):
    """T025: AcreditacionService.acreditar es la única puerta de entrada
    para otorgar nivel de competencia — ya no existe ningún signal que lo
    dispare al guardar una Inscripcion directamente (AC5, AC7)."""

    def setUp(self):
        self.nivel_2 = NivelCompetencia.objects.create(nombre='Nivel 2', codigo='nivel-2', orden=2)
        self.competencia = Competencia.objects.create(nombre='Competencia X', codigo='competencia-x')
        self.competencia_curso = CompetenciaCurso.objects.create(
            competencia=self.competencia, curso=self.curso_a, nivel=self.nivel_2,
        )
        self.periodo = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.inscripcion = inscripcion

    def test_guardar_una_inscripcion_directamente_no_dispara_acreditacion(self):
        """Sin pasar por FinalizacionService/AcreditacionService: solo
        guardar la Inscripcion (incluso marcándola completada a mano) no
        debe crear ningún CompetenciaColaborador — no hay signal."""
        self.inscripcion.completado_at = timezone.now()
        self.inscripcion.save()

        self.assertFalse(
            CompetenciaColaborador.objects.filter(colaborador=self.colaborador, competencia=self.competencia).exists(),
        )

    def test_acreditar_crea_el_registro_cuando_no_existe(self):
        AcreditacionService.acreditar(self.inscripcion)

        registro = CompetenciaColaborador.objects.get(colaborador=self.colaborador, competencia=self.competencia)
        self.assertEqual(registro.nivel, self.nivel_2)
        self.assertEqual(registro.origen, self.inscripcion)

    def test_reevaluar_es_el_unico_camino_que_dispara_acreditacion(self):
        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        FinalizacionService.reevaluar(self.inscripcion)

        registro = CompetenciaColaborador.objects.get(colaborador=self.colaborador, competencia=self.competencia)
        self.assertEqual(registro.nivel, self.nivel_2)

    def test_acreditar_nunca_baja_un_nivel_ya_otorgado(self):
        """Solo sube, nunca retrocede: un curso posterior que otorgue un
        nivel MENOR de la misma competencia no debe degradar el nivel ya
        ganado por el colaborador."""
        nivel_3 = NivelCompetencia.objects.create(nombre='Nivel 3', codigo='nivel-3', orden=3)
        registro = CompetenciaColaborador.objects.create(
            colaborador=self.colaborador, competencia=self.competencia, nivel=nivel_3,
        )

        AcreditacionService.acreditar(self.inscripcion)

        registro.refresh_from_db()
        self.assertEqual(registro.nivel, nivel_3)
