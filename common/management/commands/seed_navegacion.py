from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction

from sistema.models import Modulo, Pestania

MODULOS = [
    {
        "uuid": "801114f4-fcf2-4663-ab41-660da7d29c96",
        "href": "/dashboard/capacitacion",
        "bgColor": "#ffffff",
        "textColor": "#000000",
        "icon": "book-open-text",
        "icon_path": "",
        "nombre": "Capactiación",
        "orden": 1,
        "slug": "capacitacion",
        "desc": "Gestiona cursos",
        "pestanias": [
            {
                "uuid": "95825e4b-09df-42c5-98be-8b75db1f66f6",
                "nombre": "Cursos",
                "href": "/dashboard/capacitacion/cursos",
                "icon": "",
                "icon_path": "",
                "orden": 1,
            },
            {
                "uuid": "eddd7988-0320-4bd8-b422-659274a03a87",
                "nombre": "Rutas de Aprendizaje",
                "href": "/dashboard/capacitacion/rutas-aprendizaje",
                "icon": "",
                "icon_path": "",
                "orden": 1,
            },
            {
                "uuid": "84823b46-4f26-437e-af06-20861fabb4c3",
                "nombre": "Competencias",
                "href": "/dashboard/capacitacion/competencias",
                "icon": "",
                "icon_path": "",
                "orden": 2,
            },
        ],
    },
    {
        "uuid": "96286794-60ca-4088-a554-67814cc35211",
        "href": "/dashboard/configuracion",
        "bgColor": "#ffffff",
        "textColor": "#000000",
        "icon": "settings",
        "icon_path": "",
        "nombre": "Configuración",
        "orden": 4,
        "slug": "configuracion",
        "desc": "Gestiona los parámetros del sistema",
        "pestanias": [
            {
                "uuid": "c9aea66f-a243-4c14-9b5c-6ac99bc1850d",
                "nombre": "Empresas",
                "href": "/dashboard/configuracion/empresas",
                "icon": "",
                "icon_path": "",
                "orden": 1,
                "permisos": [("sistema", "ver_empresa")],
            },
            {
                "uuid": "2437fa39-639a-49b9-aa90-2023c6ac0aef",
                "nombre": "Modulos",
                "href": "/dashboard/configuracion/modulos",
                "icon": "",
                "icon_path": "",
                "orden": 2,
                "permisos": [("sistema", "ver_modulo")],
            },
            {
                "uuid": "2c8e0b9d-7717-433b-a151-542c435db9b1",
                "nombre": "Pestañas",
                "href": "/dashboard/configuracion/pestanias",
                "icon": "",
                "icon_path": "",
                "orden": 3,
                "permisos": [("sistema", "ver_pestania")],
            },
            {
                "uuid": "b77bedff-baa4-4e77-a39d-2f0638245ddf",
                "nombre": "Catálogos de cursos",
                "href": "/dashboard/configuracion/catalogos-cursos",
                "icon": "",
                "icon_path": "",
                "orden": 4,
                "permisos": [
                    ("catalogos", "ver_catalogstatus"),
                    ("catalogos", "ver_tipobloquecontenido"),
                    ("catalogos", "ver_tipetema"),
                    ("catalogos", "ver_tipoevaluacion"),
                ],
            },
            {
                "uuid": "de86739a-5a0f-4c63-b920-961847d0fcc0",
                "nombre": "Departamentos",
                "href": "/dashboard/configuracion/departamentos",
                "icon": "",
                "icon_path": "",
                "orden": 5,
                "permisos": [("sistema", "ver_departamento")],
            },
            {
                "uuid": "adae2cb9-0d8e-46d7-ac66-bdcc08b4cdd4",
                "nombre": "Agencias",
                "href": "/dashboard/configuracion/dependencias",
                "icon": "",
                "icon_path": "",
                "orden": 6,
                "permisos": [("sistema", "ver_dependencia")],
            },
            {
                "uuid": "77d0ccd2-5fe8-4cc6-9542-4ea62b499dfa",
                "nombre": "Nivel de competencia",
                "href": "/dashboard/configuracion/niveles-competencia",
                "icon": "",
                "icon_path": "",
                "orden": 7,
                "permisos": [("catalogos", "ver_nivelcompetencia")],
            },
            {
                "uuid": "e60194c1-1928-45d3-aa17-d7e63f1be802",
                "nombre": "Puestos",
                "href": "/dashboard/configuracion/puestos",
                "icon": "",
                "icon_path": "",
                "orden": 8,
                "permisos": [("sistema", "ver_puesto")],
            },
            {
                "uuid": "32cb1123-46c0-4653-ba9f-5623fa381ed5",
                "nombre": "Roles",
                "href": "/dashboard/configuracion/roles",
                "icon": "",
                "icon_path": "",
                "orden": 9,
                "permisos": [("user", "ver_rol")],
            },
            {
                "uuid": "cb1302a2-9e2d-4d5c-b978-a11ee02de8d3",
                "nombre": "Usuarios",
                "href": "/dashboard/configuracion/usuarios",
                "icon": "",
                "icon_path": "",
                "orden": 10,
                "permisos": [("user", "ver_usuario")],
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Crea/actualiza los módulos y pestañas de navegación usados por el frontend, respetando sus UUID."

    @transaction.atomic
    def handle(self, *args, **options):
        permisos_admin = set()

        for modulo_data in MODULOS:
            pestanias_data = modulo_data.pop("pestanias")
            modulo, created = Modulo.objects.update_or_create(
                uuid=modulo_data["uuid"],
                defaults={k: v for k, v in modulo_data.items() if k != "uuid"},
            )
            self.stdout.write(f"{'Creado' if created else 'Actualizado'} módulo: {modulo.nombre}")

            for pestania_data in pestanias_data:
                permisos_codenames = pestania_data.pop("permisos", [])
                pestania, created = Pestania.objects.update_or_create(
                    uuid=pestania_data["uuid"],
                    defaults={**{k: v for k, v in pestania_data.items() if k != "uuid"}, "modulo": modulo},
                )
                self.stdout.write(f"  {'Creada' if created else 'Actualizada'} pestaña: {pestania.nombre}")

                permisos = []
                for app_label, codename in permisos_codenames:
                    try:
                        permiso = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(
                            f"    Permiso {app_label}.{codename} no existe (¿faltó migrar?), se omite."
                        ))
                        continue
                    permisos.append(permiso)
                    permisos_admin.add(permiso.id)

                pestania.permission.set(permisos)

        self._asignar_permisos_administrador(permisos_admin)
        self.stdout.write(self.style.SUCCESS("Navegación (módulos y pestañas) sincronizada correctamente."))

    def _asignar_permisos_administrador(self, permiso_ids):
        from user.models import Role

        role, created = Role.objects.get_or_create(nombre="Administrador", defaults={"nivel_acceso": 100})
        role.permission.add(*Permission.objects.filter(id__in=permiso_ids))
        self.stdout.write(
            f"{'Creado' if created else 'Actualizado'} rol Administrador con "
            f"{role.permission.count()} permisos (menú de Configuración)."
        )
