import random
import string
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from faker import Faker

from catalogos.models import (
    Genero,
    EstadoPais,
    Localidad,
    CatalogStatus,
    TipoBloqueContenido,
    TipeTema,
    TipoEvaluacion,
    NivelCompetencia,
)
from sistema.models import Empresa, Dependencia, Departamento, Puesto
from user.models import UserCustomize, Role
from capacitacion.models.curso import Curso, Modulo as ModuloCurso, Tema, ContenidoBloque
from capacitacion.models.evaluacion import Evaluacion, Pregunta, OpcionPregunta
from capacitacion.models.progreso import Inscripcion, ProgresoTema, ResultadoEvaluacion
from competencias.models.competencia import Competencia, CompetenciaCurso, CompetenciaPuesto
from competencias.models.colaborador import CompetenciaColaborador
from competencias.models.ruta import RutaAprendizaje, RutaAprendizajeCurso

fake = Faker("es_MX")


def rand_digits(n):
    return "".join(random.choices(string.digits, k=n))


def rand_letters(n):
    return "".join(random.choices(string.ascii_uppercase, k=n))


def unique_curp(seen):
    while True:
        value = (rand_letters(4) + rand_digits(6) + rand_letters(6) + rand_digits(2))[:18]
        if value not in seen:
            seen.add(value)
            return value


def unique_rfc(seen):
    while True:
        value = (rand_letters(4) + rand_digits(6) + rand_letters(3))[:13]
        if value not in seen:
            seen.add(value)
            return value


class Command(BaseCommand):
    help = "Puebla la base de datos con datos falsos a partir de los modelos y crea un superusuario."

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true", help="Borra los datos previos de los modelos poblados antes de generar nuevos.")

    def handle(self, *args, **options):
        if options["flush"]:
            self.flush_data()

        with transaction.atomic():
            catalogos = self.seed_catalogos()
            empresa, dependencias = self.seed_sistema()
            departamentos, puestos = self.seed_organizacion()
            roles = self.seed_roles()
            usuarios = self.seed_usuarios(catalogos, dependencias, puestos, roles)
            self.seed_superusuario(dependencias)
            competencias = self.seed_competencias()
            cursos = self.seed_cursos(catalogos)
            self.seed_competencia_curso(competencias, cursos, catalogos["nivel_competencia"])
            self.seed_competencia_puesto(competencias, puestos, catalogos["nivel_competencia"])
            self.seed_rutas(competencias, cursos, catalogos["nivel_competencia"])
            self.seed_evaluaciones(cursos, catalogos["tipo_evaluacion"])
            self.seed_progreso(usuarios, cursos)

        self.stdout.write(self.style.SUCCESS("Datos falsos generados correctamente."))

    # ------------------------------------------------------------------
    def flush_data(self):
        self.stdout.write("Eliminando datos previos...")
        models_in_order = [
            ResultadoEvaluacion, ProgresoTema, Inscripcion,
            CompetenciaColaborador, RutaAprendizajeCurso, RutaAprendizaje,
            CompetenciaPuesto, CompetenciaCurso, Competencia,
            OpcionPregunta, Pregunta, Evaluacion,
            ContenidoBloque, Tema, ModuloCurso, Curso,
            Puesto, Departamento,
            UserCustomize, Role,
            Dependencia, Empresa,
            NivelCompetencia, TipoEvaluacion, TipeTema, TipoBloqueContenido, CatalogStatus,
            Localidad, EstadoPais, Genero,
        ]
        for model in models_in_order:
            model.objects.all().delete()

    # ------------------------------------------------------------------
    def seed_catalogos(self):
        self.stdout.write("Catálogos...")
        generos = [Genero.objects.get_or_create(nombre=n)[0] for n in ["Masculino", "Femenino", "Otro"]]

        paises_data = [
            ("Ciudad de México", [("Benito Juárez", "BJ"), ("Coyoacán", "COY"), ("Tlalpan", "TLP")]),
            ("Jalisco", [("Guadalajara", "GDL"), ("Zapopan", "ZAP")]),
            ("Nuevo León", [("Monterrey", "MTY"), ("San Pedro", "SPGG")]),
        ]
        localidades = []
        for nombre_estado, ciudades in paises_data:
            estado, _ = EstadoPais.objects.get_or_create(name=nombre_estado)
            for nombre_ciudad, clave in ciudades:
                loc, _ = Localidad.objects.get_or_create(country=estado, name=nombre_ciudad, clave=clave)
                localidades.append(loc)

        def crear_catalogo(model, items):
            objs = []
            for orden, (nombre, codigo) in enumerate(items):
                obj, _ = model.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden})
                objs.append(obj)
            return objs

        catalog_status = crear_catalogo(CatalogStatus, [
            ("Borrador", "borrador"), ("Publicado", "publicado"), ("Archivado", "archivado"),
        ])
        tipo_bloque = crear_catalogo(TipoBloqueContenido, [
            ("Texto con imagen", "texto-imagen"),
            ("Texto con video", "texto-video"),
            ("Texto con elemento dinámico", "texto-elemento-dinamico"),
            ("Texto con presentación y paneles", "texto-presentacion-paneles"),
            ("Texto con presentación", "texto-presentacion"),
            ("Texto con paneles", "texto-paneles"),
            ("Texto con tarjetas", "texto-tarjetas"),
        ])
        tipo_tema = crear_catalogo(TipeTema, [
            ("Lectura", "lectura"), ("Video", "video"), ("Actividad", "actividad"),
        ])
        tipo_evaluacion = crear_catalogo(TipoEvaluacion, [
            ("Módulo", "modulo"), ("Final", "final"),
        ])
        nivel_competencia = crear_catalogo(NivelCompetencia, [
            ("Introduce", "introduce"), ("Refuerza", "refuerza"), ("Desarrolla", "desarrolla"),
            ("Requerida", "requerida"), ("Deseable", "deseable"), ("Complementaria", "complementaria"),
        ])
        # orden ascendente según nivel de dominio para que el signal de competencias funcione bien
        for i, nc in enumerate(nivel_competencia):
            nc.orden = i
            nc.save(update_fields=["orden"])

        return {
            "genero": generos,
            "localidad": localidades,
            "catalog_status": catalog_status,
            "tipo_bloque": tipo_bloque,
            "tipo_tema": tipo_tema,
            "tipo_evaluacion": tipo_evaluacion,
            "nivel_competencia": nivel_competencia,
        }

    # ------------------------------------------------------------------
    def seed_sistema(self):
        self.stdout.write("Empresa y dependencias...")
        empresa, _ = Empresa.objects.get_or_create(
            razon_social="Farrera Academy S.A. de C.V.",
            defaults={
                "slug": "farrera-academy",
                "sitio_web": "https://farrera-academy.example.com",
                "telefono": "5555555555",
                "email_contacto": "contacto@farrera-academy.example.com",
                "direccion": fake.address(),
                "rfc": "FAR920101ABC",
            },
        )
        nombres_dependencia = ["Dirección General", "Recursos Humanos", "Tecnología", "Operaciones"]
        dependencias = []
        for nombre in nombres_dependencia:
            dep, _ = Dependencia.objects.get_or_create(
                nombre=nombre,
                empresa=empresa,
                defaults={
                    "telefono": fake.phone_number()[:20],
                    "email_contacto": fake.company_email(),
                    "direccion": fake.address(),
                },
            )
            dependencias.append(dep)
        return empresa, dependencias

    # ------------------------------------------------------------------
    def seed_organizacion(self):
        self.stdout.write("Departamentos y puestos...")
        departamentos_data = {
            "Recursos Humanos": ["Reclutador", "Generalista de RH", "Jefe de RH"],
            "Tecnología": ["Desarrollador", "QA", "Líder Técnico"],
            "Capacitación": ["Instructor", "Coordinador de Capacitación"],
            "Operaciones": ["Analista de Operaciones", "Supervisor"],
        }
        departamentos = []
        puestos = []
        for nombre_depto, puestos_nombres in departamentos_data.items():
            depto, _ = Departamento.objects.get_or_create(
                nombre=nombre_depto,
                codigo=fake.unique.slug(),
                defaults={"descripcion": fake.sentence()},
            )
            departamentos.append(depto)
            for nombre_puesto in puestos_nombres:
                puesto, _ = Puesto.objects.get_or_create(
                    departamento=depto,
                    codigo=fake.unique.slug(),
                    defaults={"nombre": nombre_puesto, "descripcion": fake.sentence()},
                )
                puestos.append(puesto)
        return departamentos, puestos

    # ------------------------------------------------------------------
    def seed_roles(self):
        self.stdout.write("Roles...")
        roles = []
        for nombre, nivel in [("Administrador", 100), ("Capacitador", 50), ("Colaborador", 10)]:
            role, _ = Role.objects.get_or_create(nombre=nombre, defaults={"nivel_acceso": nivel})
            roles.append(role)
        return roles

    # ------------------------------------------------------------------
    def seed_usuarios(self, catalogos, dependencias, puestos, roles, cantidad=25):
        self.stdout.write("Usuarios colaboradores...")
        curps_usadas = set(UserCustomize.objects.values_list("curp", flat=True))
        rfcs_usados = set(UserCustomize.objects.values_list("rfc", flat=True))
        num_colabs_usados = set(UserCustomize.objects.values_list("num_colab", flat=True))

        usuarios = []
        for _ in range(cantidad):
            num_colab = int(rand_digits(5))
            while num_colab in num_colabs_usados:
                num_colab = int(rand_digits(5))
            num_colabs_usados.add(num_colab)

            nombre = fake.first_name()
            apellido_paterno = fake.last_name()
            apellido_materno = fake.last_name()
            email = f"{nombre}.{apellido_paterno}.{num_colab}@farrera-academy.example.com".lower()

            usuario = UserCustomize.objects.create_user(
                email=email,
                password="colaborador123",
                num_colab=num_colab,
                nombre=nombre,
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                genero=random.choice(catalogos["genero"]),
                fecha_nacimiento=fake.date_of_birth(minimum_age=18, maximum_age=60),
                telefono=fake.phone_number()[:15],
                puesto=random.choice(puestos),
                curp=unique_curp(curps_usadas),
                rfc=unique_rfc(rfcs_usados),
                fecha_alta=fake.date_between(start_date="-5y", end_date="today"),
                dependencia=random.choice(dependencias),
            )
            usuario.roles.add(random.choice(roles))
            usuarios.append(usuario)
        return usuarios

    # ------------------------------------------------------------------
    def seed_superusuario(self, dependencias):
        num_colab = 15947
        if UserCustomize.objects.filter(num_colab=num_colab).exists():
            self.stdout.write(self.style.WARNING(f"El usuario con num_colab={num_colab} ya existe, se omite."))
            return

        self.stdout.write(f"Creando superusuario num_colab={num_colab}...")
        curps_usadas = set(UserCustomize.objects.values_list("curp", flat=True))
        rfcs_usados = set(UserCustomize.objects.values_list("rfc", flat=True))

        UserCustomize.objects.create_superuser(
            email="daniel.superuser@farrera-academy.example.com",
            password="daniel123",
            num_colab=num_colab,
            nombre="Daniel",
            apellido_paterno="Superusuario",
            apellido_materno="",
            curp=unique_curp(curps_usadas),
            rfc=unique_rfc(rfcs_usados),
            fecha_alta=timezone.now().date(),
            dependencia=dependencias[0],
        )

    # ------------------------------------------------------------------
    def seed_competencias(self, cantidad=8):
        self.stdout.write("Competencias...")
        nombres = [
            "Comunicación efectiva", "Trabajo en equipo", "Liderazgo", "Resolución de problemas",
            "Atención al cliente", "Manejo de Excel", "Programación en Python", "Gestión del tiempo",
        ][:cantidad]
        competencias = []
        for nombre in nombres:
            comp, _ = Competencia.objects.get_or_create(
                codigo=fake.unique.slug(),
                defaults={
                    "nombre": nombre,
                    "descripcion": fake.sentence(),
                    "icono": "star",
                    "color": fake.hex_color(),
                },
            )
            competencias.append(comp)
        return competencias

    # ------------------------------------------------------------------
    def seed_cursos(self, catalogos, cantidad=6):
        self.stdout.write("Cursos, módulos, temas y bloques...")
        titulos = [
            "Inducción a la empresa", "Seguridad e higiene", "Atención al cliente",
            "Excel intermedio", "Liderazgo de equipos", "Introducción a Python",
        ][:cantidad]
        cursos = []
        for titulo in titulos:
            curso = Curso.objects.create(
                titulo=titulo,
                descripcion=fake.paragraph(nb_sentences=5),
                duracion_horas=random.choice([4, 8, 12, 20]),
                status=random.choice(catalogos["catalog_status"]),
            )
            cursos.append(curso)

            for m_orden in range(1, random.randint(2, 4)):
                modulo = ModuloCurso.objects.create(
                    curso=curso,
                    titulo=f"Módulo {m_orden}: {fake.sentence(nb_words=4)}",
                    descripcion=fake.sentence(),
                    orden=m_orden,
                    horas_teoricas=random.choice([1, 2, 3]),
                    horas_practicas=random.choice([0, 1, 2]),
                    tiene_evaluacion=True,
                )
                for t_orden in range(1, random.randint(2, 4)):
                    tema = Tema.objects.create(
                        modulo=modulo,
                        titulo=fake.sentence(nb_words=5),
                        duracion_estimada=f"{random.randint(10, 45)} min",
                        tipo=random.choice(catalogos["tipo_tema"]),
                        orden=t_orden,
                    )
                    for b_orden in range(1, random.randint(2, 4)):
                        tipo_bloque = random.choice(catalogos["tipo_bloque"])
                        extra = {}
                        if tipo_bloque.codigo == "texto-video":
                            extra["video_url"] = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
                        elif tipo_bloque.codigo in ("texto-tarjetas", "texto-elemento-dinamico"):
                            extra["items"] = [fake.sentence(nb_words=4) for _ in range(3)]
                        elif tipo_bloque.codigo in ("texto-paneles", "texto-presentacion-paneles"):
                            extra["filas"] = [[fake.word(), fake.word()] for _ in range(3)]
                        ContenidoBloque.objects.create(
                            tema=tema,
                            tipo=tipo_bloque,
                            orden=b_orden,
                            texto=fake.paragraph(nb_sentences=3),
                            **extra,
                        )
        return cursos

    # ------------------------------------------------------------------
    def seed_competencia_curso(self, competencias, cursos, niveles):
        self.stdout.write("Competencias por curso...")
        for curso in cursos:
            for competencia in random.sample(competencias, k=random.randint(1, 3)):
                CompetenciaCurso.objects.get_or_create(
                    competencia=competencia,
                    curso=curso,
                    defaults={"nivel": random.choice(niveles)},
                )

    # ------------------------------------------------------------------
    def seed_competencia_puesto(self, competencias, puestos, niveles):
        self.stdout.write("Competencias por puesto...")
        for puesto in puestos:
            for competencia in random.sample(competencias, k=random.randint(1, 2)):
                CompetenciaPuesto.objects.get_or_create(
                    competencia=competencia,
                    puesto=puesto,
                    defaults={"nivel": random.choice(niveles)},
                )

    # ------------------------------------------------------------------
    def seed_rutas(self, competencias, cursos, niveles, cantidad=3):
        self.stdout.write("Rutas de aprendizaje...")
        for i in range(cantidad):
            competencia = random.choice(competencias)
            ruta = RutaAprendizaje.objects.create(
                nombre=f"Ruta {fake.word().capitalize()} {i + 1}",
                descripcion=fake.sentence(),
                competencia=competencia,
                nivel_objetivo=random.choice(niveles),
            )
            seleccionados = random.sample(cursos, k=min(3, len(cursos)))
            for orden, curso in enumerate(seleccionados, start=1):
                RutaAprendizajeCurso.objects.create(ruta=ruta, curso=curso, orden=orden)

    # ------------------------------------------------------------------
    def seed_evaluaciones(self, cursos, tipos_evaluacion):
        self.stdout.write("Evaluaciones, preguntas y opciones...")
        for curso in cursos:
            evaluacion = Evaluacion.objects.create(
                titulo=f"Evaluación final — {curso.titulo}",
                tipo=random.choice(tipos_evaluacion),
                puntaje_minimo=70,
                curso=curso,
            )
            for p_orden in range(1, random.randint(3, 6)):
                pregunta = Pregunta.objects.create(
                    evaluacion=evaluacion,
                    texto=fake.sentence() + "?",
                    orden=p_orden,
                )
                correcta_idx = random.randint(0, 3)
                for o_orden in range(4):
                    OpcionPregunta.objects.create(
                        pregunta=pregunta,
                        texto=fake.sentence(nb_words=4),
                        orden=o_orden,
                        es_correcta=(o_orden == correcta_idx),
                    )

            for modulo in curso.modulos.filter(tiene_evaluacion=True):
                evaluacion_modulo = Evaluacion.objects.create(
                    titulo=f"Evaluación — {modulo.titulo}",
                    tipo=random.choice(tipos_evaluacion),
                    puntaje_minimo=70,
                    modulo=modulo,
                )
                for p_orden in range(1, random.randint(2, 4)):
                    pregunta = Pregunta.objects.create(
                        evaluacion=evaluacion_modulo,
                        texto=fake.sentence() + "?",
                        orden=p_orden,
                    )
                    correcta_idx = random.randint(0, 3)
                    for o_orden in range(4):
                        OpcionPregunta.objects.create(
                            pregunta=pregunta,
                            texto=fake.sentence(nb_words=4),
                            orden=o_orden,
                            es_correcta=(o_orden == correcta_idx),
                        )

    # ------------------------------------------------------------------
    def seed_progreso(self, usuarios, cursos):
        self.stdout.write("Inscripciones, progreso y resultados...")
        for usuario in usuarios:
            for curso in random.sample(cursos, k=random.randint(1, min(3, len(cursos)))):
                completado = random.random() < 0.6
                inscripcion = Inscripcion.objects.create(
                    colaborador=usuario,
                    curso=curso,
                    completado_at=timezone.now() - timedelta(days=random.randint(0, 60)) if completado else None,
                )

                temas = Tema.objects.filter(modulo__curso=curso)
                for tema in temas:
                    if random.random() < 0.7:
                        ProgresoTema.objects.get_or_create(colaborador=usuario, tema=tema)

                for evaluacion in curso.evaluaciones.all():
                    if random.random() < 0.5:
                        total = evaluacion.preguntas.count() or 1
                        correctas = random.randint(0, total)
                        ResultadoEvaluacion.objects.create(
                            colaborador=usuario,
                            evaluacion=evaluacion,
                            correctas=correctas,
                            total=total,
                        )
                del inscripcion
