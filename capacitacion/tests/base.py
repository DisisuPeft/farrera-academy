import itertools

from django.test import TestCase

from catalogos.models import CatalogStatus, TipeTema, TipoBloqueContenido
from catalogos.models.capacitacion import CategoriaPedagogica
from capacitacion.models import Curso, Modulo, Tema
from sistema.models import Empresa, Dependencia, Departamento, Puesto
from user.models import UserCustomize, Role

_contador = itertools.count(900000)


def hacer_usuario(dependencia, es_superuser=False, **extra):
    n = next(_contador)
    defaults = dict(
        num_colab=n,
        nombre='Test',
        apellido_paterno='User',
        apellido_materno='',
        curp=f'TEST{n}CURPXXXXXXX'[:18],
        rfc=f'TST{n}RFC'[:13],
        fecha_alta='2024-01-01',
        dependencia=dependencia,
    )
    defaults.update(extra)
    if es_superuser:
        return UserCustomize.objects.create_superuser(
            email=f'super{n}@test.local', password='testpass123', **defaults,
        )
    return UserCustomize.objects.create_user(
        email=f'user{n}@test.local', password='testpass123', **defaults,
    )


class CapacitacionTestBase(TestCase):
    """Fixtures comunes: 2 empresas/dependencias, catálogos mínimos, un curso con
    estructura completa (módulo→tema), y usuarios (superuser, admin de cada
    empresa, colaborador)."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa_a = Empresa.objects.create(razon_social='Empresa A', slug='empresa-a')
        cls.empresa_b = Empresa.objects.create(razon_social='Empresa B', slug='empresa-b')
        cls.dependencia_a = Dependencia.objects.create(nombre='Dependencia A', empresa=cls.empresa_a)
        cls.dependencia_b = Dependencia.objects.create(nombre='Dependencia B', empresa=cls.empresa_b)

        cls.departamento = Departamento.objects.create(nombre='Depto', codigo='depto-test')
        cls.puesto = Puesto.objects.create(departamento=cls.departamento, nombre='Puesto', codigo='puesto-test')

        cls.status_publicado = CatalogStatus.objects.create(nombre='Publicado', codigo='publicado-test')
        cls.tipo_tema = TipeTema.objects.create(nombre='Lectura', codigo='lectura-test')

        cls.tipo_texto = TipoBloqueContenido.objects.create(
            nombre='Texto con imagen', codigo='texto-imagen-test',
            categoria=CategoriaPedagogica.CONTENIDO,
        )
        cls.tipo_opcion_multiple = TipoBloqueContenido.objects.create(
            nombre='Opción múltiple', codigo='opcion-multiple-test',
            categoria=CategoriaPedagogica.EVALUACION,
        )

        cls.admin_role = Role.objects.create(nombre='Administrador', nivel_acceso=100)

        cls.superuser = hacer_usuario(cls.dependencia_a, es_superuser=True)
        cls.admin_a = hacer_usuario(cls.dependencia_a)
        cls.admin_a.roles.add(cls.admin_role)
        cls.admin_b = hacer_usuario(cls.dependencia_b)
        cls.admin_b.roles.add(cls.admin_role)
        cls.colaborador = hacer_usuario(cls.dependencia_a)

        cls.curso_a = Curso.objects.create(
            titulo='Curso de A', status=cls.status_publicado, empresa=cls.empresa_a,
        )
        cls.modulo_a = Modulo.objects.create(curso=cls.curso_a, titulo='Módulo 1', orden=1)
        cls.tema_a = Tema.objects.create(modulo=cls.modulo_a, titulo='Tema 1', tipo=cls.tipo_tema, orden=1)
