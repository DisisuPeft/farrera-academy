from datetime import date

from catalogos.models import NivelCompetencia
from capacitacion.models import Inscripcion, Periodo, ProgresoTema
from capacitacion.services.finalizacion_service import FinalizacionService
from capacitacion.services.inscripcion_service import InscripcionService
from capacitacion.tests.base import CapacitacionTestBase
from competencias.models import CompetenciaColaborador
from competencias.models.competencia import Competencia, CompetenciaCurso


class AcreditacionNoSeReevaluaAlGuardarHistoricoTests(CapacitacionTestBase):
    """T024 — reproduce el hallazgo de la auditoría: una inscripción ya
    finalizada y acreditada a nivel 2 NO debe subir de nivel si, después,
    cambia la configuración de CompetenciaCurso y algo vuelve a guardar esa
    inscripción histórica (sin pasar por el servicio de finalización). El
    nivel otorgado debe quedar fijo en el momento de la acreditación (AC7)."""

    def setUp(self):
        self.nivel_2 = NivelCompetencia.objects.create(nombre='Nivel 2', codigo='nivel-2', orden=2)
        self.nivel_3 = NivelCompetencia.objects.create(nombre='Nivel 3', codigo='nivel-3', orden=3)
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

        ProgresoTema.objects.create(inscripcion=self.inscripcion, tema=self.tema_a)
        finalizada = FinalizacionService.reevaluar(self.inscripcion)
        self.assertIsNotNone(finalizada.completado_at)
        self.inscripcion.refresh_from_db()
        self.assertIsNotNone(self.inscripcion.completado_at)

        self.registro = CompetenciaColaborador.objects.get(
            colaborador=self.colaborador, competencia=self.competencia,
        )
        self.assertEqual(self.registro.nivel, self.nivel_2)

    def test_nivel_no_sube_al_resavear_la_inscripcion_historica_tras_subir_el_nivel_del_curso(self):
        self.competencia_curso.nivel = self.nivel_3
        self.competencia_curso.save(update_fields=['nivel'])

        self.inscripcion.save()

        self.registro.refresh_from_db()
        self.assertEqual(self.registro.nivel, self.nivel_2)
