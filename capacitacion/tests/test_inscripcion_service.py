import threading
from datetime import date

from django.db import connection
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from django.utils import timezone

from catalogos.models import CatalogStatus
from capacitacion.models import Curso, Inscripcion, Periodo
from capacitacion.services.inscripcion_service import (
    InscripcionDuplicada,
    InscripcionService,
    PeriodoNoAbierto,
)
from capacitacion.tests.base import CapacitacionTestBase, hacer_usuario
from sistema.models import Dependencia, Empresa


class InscripcionServiceCrearTests(CapacitacionTestBase):
    def setUp(self):
        self.periodo_abierto = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria abierta', fecha_inicio=date(2026, 1, 1),
            estado=Periodo.Estado.ABIERTO,
        )
        self.periodo_cerrado = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria cerrada', fecha_inicio=date(2025, 1, 1),
            estado=Periodo.Estado.CERRADO,
        )

    def test_rechaza_periodo_cerrado(self):
        resultado = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_cerrado)
        self.assertIsInstance(resultado, PeriodoNoAbierto)
        self.assertFalse(Inscripcion.objects.filter(colaborador=self.colaborador).exists())

    def test_rechaza_duplicado_al_mismo_periodo(self):
        primera = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_abierto)
        self.assertIsInstance(primera, Inscripcion)

        segunda = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_abierto)
        self.assertIsInstance(segunda, InscripcionDuplicada)
        self.assertEqual(Inscripcion.objects.filter(colaborador=self.colaborador).count(), 1)

    def test_curso_queda_copiado_del_periodo(self):
        inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_abierto)
        self.assertIsInstance(inscripcion, Inscripcion)
        self.assertEqual(inscripcion.curso_id, self.periodo_abierto.curso_id)
        self.assertIsNone(inscripcion.completado_at)


class ConcurrenciaTest(TransactionTestCase):
    """T005: dos hilos reales (conexiones de BD separadas) intentan crear la
    misma Inscripcion (colaborador, periodo) a la vez. Como máximo una debe
    tener éxito — esto exige bloqueo real (select_for_update), no solo un
    chequeo secuencial de existencia."""

    def setUp(self):
        self.empresa = Empresa.objects.create(razon_social='Empresa Concurrencia', slug='empresa-concurrencia')
        self.dependencia = Dependencia.objects.create(nombre='Dependencia Concurrencia', empresa=self.empresa)
        self.status_publicado = CatalogStatus.objects.create(
            nombre='Publicado', codigo='publicado-concurrencia',
        )
        self.colaborador = hacer_usuario(self.dependencia)
        self.curso = Curso.objects.create(
            titulo='Curso Concurrencia', status=self.status_publicado, empresa=self.empresa,
        )
        self.periodo = Periodo.objects.create(
            curso=self.curso, nombre='Convocatoria concurrencia', fecha_inicio=date(2026, 1, 1),
        )

    def test_como_maximo_una_inscripcion_exitosa_bajo_concurrencia_real(self):
        resultados = []
        barrera = threading.Barrier(2)

        def intentar():
            try:
                barrera.wait(timeout=5)
                resultado = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo)
                resultados.append(resultado)
            finally:
                connection.close()

        hilos = [threading.Thread(target=intentar) for _ in range(2)]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()

        self.assertEqual(
            len(resultados), 2,
            'un hilo no llegó a devolver resultado: crear() debe absorber la '
            'IntegrityError de la carrera y devolver InscripcionDuplicada(), '
            'nunca dejar que una excepción se propague fuera del hilo',
        )
        exitosos = [r for r in resultados if isinstance(r, Inscripcion)]
        self.assertEqual(len(exitosos), 1)
        self.assertEqual(
            Inscripcion.objects.filter(colaborador=self.colaborador, periodo=self.periodo).count(), 1,
        )


class RepeticionTest(CapacitacionTestBase):
    """T007: repetir el mismo curso en un periodo distinto crea una Inscripcion
    independiente — no altera ni se mezcla con la primera."""

    def setUp(self):
        self.periodo_1 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 1', fecha_inicio=date(2026, 1, 1),
        )
        self.periodo_2 = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria 2', fecha_inicio=date(2026, 6, 1),
        )

    def test_segunda_inscripcion_a_periodo_distinto_no_altera_la_primera(self):
        primera = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_1)
        self.assertIsInstance(primera, Inscripcion)
        primera.completado_at = timezone.now()
        primera.save(update_fields=['completado_at'])

        segunda = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_2)
        self.assertIsInstance(segunda, Inscripcion)
        self.assertNotEqual(segunda.pk, primera.pk)
        self.assertIsNone(segunda.completado_at)

        primera.refresh_from_db()
        self.assertIsNotNone(primera.completado_at)
        self.assertEqual(primera.periodo_id, self.periodo_1.id)

        self.assertEqual(
            Inscripcion.objects.filter(colaborador=self.colaborador, curso=self.curso_a).count(), 2,
        )


class InvarianteCursoTest(CapacitacionTestBase):
    """T039: `Inscripcion.curso` es de solo lectura en todo serializer y
    siempre coincide con `periodo.curso` tras crear/actualizar vía
    `InscripcionService` (plan §7, riesgo de divergencia)."""

    def setUp(self):
        self.curso_b = Curso.objects.create(
            titulo='Curso de B', status=self.status_publicado, empresa=self.empresa_a,
        )
        self.periodo_a = Periodo.objects.create(
            curso=self.curso_a, nombre='Convocatoria A', fecha_inicio=date(2026, 1, 1),
            estado=Periodo.Estado.ABIERTO,
        )
        self.inscripcion = InscripcionService.crear(colaborador=self.colaborador, periodo=self.periodo_a)
        self.assertIsInstance(self.inscripcion, Inscripcion)

    def test_curso_queda_copiado_del_periodo_tras_crear(self):
        self.assertEqual(self.inscripcion.curso_id, self.periodo_a.curso_id)

    def test_patch_curso_distinto_al_de_periodo_es_ignorado(self):
        client = APIClient()
        client.force_authenticate(self.colaborador)

        resp = client.patch(
            f'/api/capacitacion/mis-inscripciones/{self.inscripcion.id}/',
            {'curso': self.curso_b.id},
            format='json',
        )
        self.assertIn(resp.status_code, (200, 400))

        self.inscripcion.refresh_from_db()
        self.assertEqual(self.inscripcion.curso_id, self.periodo_a.curso_id)
        self.assertNotEqual(self.inscripcion.curso_id, self.curso_b.id)
