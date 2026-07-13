from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from user.authenticate import CustomJWTAuthentication
from user.permission import HasRoleWithRoles

from competencias.models import (
    Competencia, CompetenciaCurso, CompetenciaPuesto,
    RutaAprendizaje, RutaAprendizajeCurso, CompetenciaColaborador,
)
from capacitacion.models import Inscripcion
from competencias.serializers import (
    CompetenciaSerializer,
    CompetenciaCursoSerializer,
    CompetenciaPuestoSerializer,
    RutaAprendizajeSerializer,
    RutaAprendizajeCursoSerializer,
    CompetenciaColaboradorSerializer,
)


class _BaseAdminViewSet(ModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated, HasRoleWithRoles(['Administrador'])]


class _BaseSoftDeleteViewSet(_BaseAdminViewSet):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete(user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompetenciaViewSet(_BaseSoftDeleteViewSet):
    queryset = Competencia.objects.all()
    serializer_class = CompetenciaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        codigo = self.request.query_params.get('codigo')
        if codigo:
            qs = qs.filter(codigo=codigo)
        return qs


class CompetenciaCursoViewSet(_BaseSoftDeleteViewSet):
    queryset = CompetenciaCurso.objects.select_related(
        'competencia', 'curso', 'nivel'
    ).all()
    serializer_class = CompetenciaCursoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        competencia = self.request.query_params.get('competencia')
        curso = self.request.query_params.get('curso')
        if competencia:
            qs = qs.filter(competencia_id=competencia)
        if curso:
            qs = qs.filter(curso_id=curso)
        return qs


class CompetenciaPuestoViewSet(_BaseSoftDeleteViewSet):
    queryset = CompetenciaPuesto.objects.select_related(
        'competencia', 'puesto', 'nivel'
    ).all()
    serializer_class = CompetenciaPuestoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        competencia = self.request.query_params.get('competencia')
        puesto = self.request.query_params.get('puesto')
        if competencia:
            qs = qs.filter(competencia_id=competencia)
        if puesto:
            qs = qs.filter(puesto_id=puesto)
        return qs


class RutaAprendizajeViewSet(_BaseSoftDeleteViewSet):
    queryset = RutaAprendizaje.objects.select_related(
        'competencia', 'nivel_objetivo'
    ).prefetch_related('ruta_cursos__curso').all()
    serializer_class = RutaAprendizajeSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        competencia = self.request.query_params.get('competencia')
        if competencia:
            qs = qs.filter(competencia_id=competencia)
        return qs


class RutaAprendizajeCursoViewSet(_BaseAdminViewSet):
    queryset = RutaAprendizajeCurso.objects.select_related('ruta', 'curso').all()
    serializer_class = RutaAprendizajeCursoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        ruta = self.request.query_params.get('ruta')
        if ruta:
            qs = qs.filter(ruta_id=ruta)
        return qs


class CompetenciaColaboradorViewSet(_BaseAdminViewSet):
    queryset = CompetenciaColaborador.objects.select_related(
        'colaborador', 'competencia', 'nivel', 'origen__curso'
    ).all()
    serializer_class = CompetenciaColaboradorSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        colaborador = self.request.query_params.get('colaborador')
        competencia = self.request.query_params.get('competencia')
        try:
            if colaborador:
                qs = qs.filter(colaborador__num_colab=int(colaborador))
        except (ValueError, TypeError):
            pass
        try:
            if competencia:
                qs = qs.filter(competencia_id=int(competencia))
        except (ValueError, TypeError):
            pass
        return qs


class MiPerfilCompetenciasView(APIView):
    """
    Devuelve el gap analysis del colaborador autenticado:
    por cada competencia que exige su puesto, muestra su nivel actual,
    la brecha y las rutas de aprendizaje recomendadas para cerrarla.
    """
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if not user.puesto_id:
            return Response(
                {'detail': 'El usuario no tiene un puesto asignado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        requeridas = (
            CompetenciaPuesto.objects
            .filter(puesto=user.puesto, activo=True, deleted_at__isnull=True)
            .select_related('competencia', 'nivel')
        )

        niveles_actuales = {
            cc.competencia_id: cc
            for cc in CompetenciaColaborador.objects.filter(
                colaborador=user,
                competencia_id__in=requeridas.values_list('competencia_id', flat=True),
            ).select_related('nivel')
        }

        rutas_por_competencia = {}
        for ruta in RutaAprendizaje.objects.filter(
            competencia_id__in=requeridas.values_list('competencia_id', flat=True),
            activo=True,
            deleted_at__isnull=True,
        ).select_related('nivel_objetivo').prefetch_related('ruta_cursos__curso'):
            rutas_por_competencia.setdefault(ruta.competencia_id, []).append(ruta)

        # Dict curso_id → inscripcion para saber cuáles tiene el usuario (completas o no)
        inscripciones_map = {
            i.curso_id: i
            for i in request.user.capacitacion_inscripcion_set.all()
        }

        resultado = []
        for cp in requeridas:
            actual = niveles_actuales.get(cp.competencia_id)
            nivel_actual_orden = actual.nivel.orden if actual else 0
            brecha = cp.nivel.orden - nivel_actual_orden

            rutas = rutas_por_competencia.get(cp.competencia_id, [])
            rutas_serializadas = []
            for ruta in rutas:
                cursos_ruta = []
                for rc in sorted(ruta.ruta_cursos.all(), key=lambda x: x.orden):
                    inscripcion = inscripciones_map.get(rc.curso_id)
                    cursos_ruta.append({
                        'id': rc.id,
                        'orden': rc.orden,
                        'curso_id': rc.curso_id,
                        'curso_titulo': rc.curso.titulo,
                        'inscripcion_id': inscripcion.id if inscripcion else None,
                        'completado': bool(inscripcion and inscripcion.completado_at),
                        'estado': None,
                    })

                curso_actual_id = None
                for c in cursos_ruta:
                    if c['completado']:
                        c['estado'] = 'completado'
                    elif curso_actual_id is None:
                        c['estado'] = 'en_curso'
                        curso_actual_id = c['curso_id']
                    else:
                        c['estado'] = 'pendiente'

                total = len(cursos_ruta)
                completados = sum(1 for c in cursos_ruta if c['completado'])
                iniciada = any(c['inscripcion_id'] for c in cursos_ruta)
                terminada = curso_actual_id is None and total > 0
                rutas_serializadas.append({
                    'id': ruta.id,
                    'nombre': ruta.nombre,
                    'nivel_objetivo_id': ruta.nivel_objetivo_id,
                    'nivel_objetivo_nombre': ruta.nivel_objetivo.nombre,
                    'nivel_objetivo_orden': ruta.nivel_objetivo.orden,
                    'curso_actual_id': curso_actual_id,
                    'iniciada': iniciada,
                    'terminada': terminada,
                    'progreso': {
                        'total': total,
                        'completados': completados,
                        'porcentaje': int(completados / total * 100) if total else 0,
                    },
                    'cursos': cursos_ruta,
                })

            resultado.append({
                'competencia_id': cp.competencia_id,
                'competencia_nombre': cp.competencia.nombre,
                'competencia_codigo': cp.competencia.codigo,
                'competencia_icono': cp.competencia.icono,
                'competencia_color': cp.competencia.color,
                'nivel_requerido_id': cp.nivel_id,
                'nivel_requerido_nombre': cp.nivel.nombre,
                'nivel_requerido_orden': cp.nivel.orden,
                'nivel_actual_id': actual.nivel_id if actual else None,
                'nivel_actual_nombre': actual.nivel.nombre if actual else None,
                'nivel_actual_orden': nivel_actual_orden,
                'brecha': brecha,
                'completada': brecha <= 0,
                'rutas_recomendadas': rutas_serializadas,
            })

        return Response(resultado)



class MiInscripcionRutaPerfil(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ruta_id = request.data.get('ruta_id')
        if not ruta_id:
            return Response(
                {'detail': 'Se requiere ruta_id.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ruta = RutaAprendizaje.objects.prefetch_related('ruta_cursos__curso').get(
                pk=ruta_id, activo=True, deleted_at__isnull=True,
            )
        except RutaAprendizaje.DoesNotExist:
            return Response(
                {'detail': 'Ruta no encontrada.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        cursos_en_ruta = ruta.ruta_cursos.select_related('curso').order_by('orden')
        if not cursos_en_ruta.exists():
            return Response(
                {'detail': 'La ruta no tiene cursos asignados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inscritos = set(
            request.user.capacitacion_inscripcion_set
            .filter(curso_id__in=cursos_en_ruta.values_list('curso_id', flat=True))
            .values_list('curso_id', flat=True)
        )

        siguiente = next(
            (rc for rc in cursos_en_ruta if rc.curso_id not in inscritos),
            None,
        )

        if siguiente is None:
            return Response(
                {'detail': 'Ya estás inscrito en todos los cursos de esta ruta.'},
                status=status.HTTP_200_OK,
            )

        inscripcion, creada = Inscripcion.objects.get_or_create(
            colaborador=request.user,
            curso=siguiente.curso,
        )

        return Response(
            {
                'creada': creada,
                'inscripcion_id': inscripcion.id,
                'curso_id': siguiente.curso_id,
                'curso_titulo': siguiente.curso.titulo,
                'orden': siguiente.orden,
            },
            status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK,
        )