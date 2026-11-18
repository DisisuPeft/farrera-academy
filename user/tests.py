from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from capacitacion.tests.base import hacer_usuario
from sistema.models import Dependencia, Empresa
from user.backends import RolePermissionBackend
from user.models import Role, UserCustomize


class RolePermissionBackendStatusTests(TestCase):
    """`status` es la fuente de verdad para autorización, no `is_active`
    (que se deja fijo en True por diseño — ver decisions.md). Desactivar a
    un colaborador vía `status=0` debe quitarle los permisos en vivo,
    incluso si `is_active` nunca se tocó."""

    def setUp(self):
        self.backend = RolePermissionBackend()
        empresa = Empresa.objects.create(razon_social='Empresa', slug='empresa-backend-test')
        dependencia = Dependencia.objects.create(nombre='Dependencia', empresa=empresa)
        content_type = ContentType.objects.get_for_model(Role)
        self.permiso = Permission.objects.create(
            name='Permiso de prueba', codename='permiso_prueba_backend', content_type=content_type,
        )
        self.role = Role.objects.create(nombre='RoleBackendTest', nivel_acceso=10)
        self.role.permission.add(self.permiso)
        self.user = hacer_usuario(dependencia)
        self.user.roles.add(self.role)

    def test_usuario_con_status_activo_y_is_active_true_mantiene_permisos(self):
        self.assertTrue(self.user.is_active)
        self.assertEqual(self.user.status, 1)

        permisos = self.backend.get_all_permissions(self.user)

        self.assertIn('user.permiso_prueba_backend', permisos)

    def test_usuario_con_status_desactivado_pierde_permisos_aunque_is_active_siga_true(self):
        self.user.status = 0
        self.user.save(update_fields=['status'])
        self.assertTrue(self.user.is_active)

        self.assertEqual(self.backend.get_user_permissions(self.user), set())
        self.assertEqual(self.backend.get_all_permissions(self.user), set())
        self.assertFalse(self.backend.has_perm(self.user, 'cualquier.permiso'))

    def test_superuser_mantiene_permisos_incluso_con_status_desactivado(self):
        self.user.is_superuser = True
        self.user.status = 0
        self.user.save(update_fields=['is_superuser', 'status'])

        self.assertTrue(self.backend.has_perm(self.user, 'cualquier.permiso'))
