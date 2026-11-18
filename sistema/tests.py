from django.contrib.auth.models import Permission
from django.test import TestCase

from capacitacion.tests.base import hacer_usuario
from sistema.models import Empresa, Dependencia, Modulo, Pestania
from user.models import Role


class NavegacionPermisosTests(TestCase):
    """modulos_accesibles()/pestanias_accesibles(): una pestaña sin permiso
    asociado es pública; una con permiso solo la ve quien lo tenga via su Role."""

    @classmethod
    def setUpTestData(cls):
        cls.empresa = Empresa.objects.create(razon_social='E', slug='e-nav-test')
        cls.dependencia = Dependencia.objects.create(nombre='D', empresa=cls.empresa)

        cls.modulo = Modulo.objects.create(nombre='Configuración', orden=1)
        cls.perm_ver_pestania = Permission.objects.get(content_type__app_label='sistema', codename='ver_pestania')

        cls.pestania_publica = Pestania.objects.create(nombre='Pública', modulo=cls.modulo, orden=1)
        cls.pestania_restringida = Pestania.objects.create(nombre='Restringida', modulo=cls.modulo, orden=2)
        cls.pestania_restringida.permission.add(cls.perm_ver_pestania)

        cls.role_con_permiso = Role.objects.create(nombre='ConPermiso')
        cls.role_con_permiso.permission.add(cls.perm_ver_pestania)

        cls.sin_rol = hacer_usuario(cls.dependencia)
        cls.con_rol = hacer_usuario(cls.dependencia)
        cls.con_rol.roles.add(cls.role_con_permiso)
        cls.superuser = hacer_usuario(cls.dependencia, es_superuser=True)

    def test_pestania_sin_permiso_es_visible_para_cualquiera(self):
        pestanias = self.sin_rol.pestanias_accesibles(self.modulo.uuid)
        nombres = [p.nombre for p in pestanias]
        self.assertIn('Pública', nombres)

    def test_pestania_con_permiso_oculta_a_quien_no_lo_tiene(self):
        pestanias = self.sin_rol.pestanias_accesibles(self.modulo.uuid)
        nombres = [p.nombre for p in pestanias]
        self.assertNotIn('Restringida', nombres)

    def test_pestania_con_permiso_visible_para_quien_lo_tiene_via_role(self):
        pestanias = self.con_rol.pestanias_accesibles(self.modulo.uuid)
        nombres = [p.nombre for p in pestanias]
        self.assertIn('Restringida', nombres)

    def test_superuser_ve_todo_sin_importar_permisos(self):
        pestanias = self.superuser.pestanias_accesibles(self.modulo.uuid)
        nombres = [p.nombre for p in pestanias]
        self.assertIn('Restringida', nombres)

    def test_modulo_sin_pestanias_visibles_no_aparece_en_modulos_accesibles(self):
        modulo_oculto = Modulo.objects.create(nombre='Oculto total', orden=2)
        perm_ajeno = Permission.objects.get(content_type__app_label='sistema', codename='ver_modulo')
        pestania_oculta = Pestania.objects.create(nombre='Nadie la ve', modulo=modulo_oculto, orden=1)
        pestania_oculta.permission.add(perm_ajeno)

        nombres = [m.nombre for m in self.sin_rol.modulos_accesibles()]
        self.assertNotIn('Oculto total', nombres)

    def test_pestania_inactiva_no_aparece(self):
        self.pestania_publica.status = 0
        self.pestania_publica.save(update_fields=['status'])
        nombres = [p.nombre for p in self.sin_rol.pestanias_accesibles(self.modulo.uuid)]
        self.assertNotIn('Pública', nombres)


class ModuloPestaniaPermisosModeloTests(TestCase):
    """Modulo/Pestania ahora tienen permisos custom propios (ver/agregar/editar/eliminar),
    requisito para poder engancharlos al menú de Configuración."""

    def test_modulo_tiene_los_4_permisos_crud(self):
        codenames = set(
            Permission.objects.filter(content_type__app_label='sistema', codename__endswith='_modulo')
            .values_list('codename', flat=True)
        )
        self.assertEqual(codenames, {'ver_modulo', 'agregar_modulo', 'editar_modulo', 'eliminar_modulo'})

    def test_pestania_tiene_los_4_permisos_crud(self):
        codenames = set(
            Permission.objects.filter(content_type__app_label='sistema', codename__endswith='_pestania')
            .values_list('codename', flat=True)
        )
        self.assertEqual(codenames, {'ver_pestania', 'agregar_pestania', 'editar_pestania', 'eliminar_pestania'})
