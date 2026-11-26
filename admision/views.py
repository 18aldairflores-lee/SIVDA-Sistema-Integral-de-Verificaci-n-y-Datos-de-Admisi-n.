from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import (
    ProcesoAdmision,
    ProgramaEstudio,
    Postulante,
    RequisitoExpediente,
    HistorialAuditoria,
)
from .serializers import (
    ProcesoAdmisionSerializer,
    ProgramaEstudioSerializer,
    PostulanteSerializer,
    RequisitoExpedienteSerializer,
    ConsultaPublicaPostulanteSerializer,
)


class ProcesoAdmisionViewSet(viewsets.ModelViewSet):
    queryset = ProcesoAdmision.objects.all()
    serializer_class = ProcesoAdmisionSerializer


class ProgramaEstudioViewSet(viewsets.ModelViewSet):
    queryset = ProgramaEstudio.objects.all()
    serializer_class = ProgramaEstudioSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class PostulanteViewSet(viewsets.ModelViewSet):
    queryset = Postulante.objects.select_related('proceso', 'programa').prefetch_related('requisitos', 'auditorias')
    serializer_class = PostulanteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q')
        estado = self.request.query_params.get('estado')
        programa = self.request.query_params.get('programa')

        if q:
            qs = qs.filter(
                Q(dni__icontains=q) |
                Q(nombres__icontains=q) |
                Q(apellidos__icontains=q) |
                Q(codigo_verificacion__icontains=q)
            )
        if estado:
            qs = qs.filter(estado_general=estado)
        if programa:
            qs = qs.filter(programa_id=programa)
        return qs

    def perform_create(self, serializer):
        postulante = serializer.save()
        HistorialAuditoria.objects.create(
            postulante=postulante,
            usuario=self.request.user if self.request.user.is_authenticated else None,
            accion='REGISTRO_POSTULANTE',
            detalle=f'Inscripción registrada en {postulante.programa.nombre} ({postulante.modalidad}).'
        )

    @action(detail=True, methods=['patch'], url_path='calificar')
    def calificar(self, request, pk=None):
        """Registra puntaje y condición final (INGRESO / NO_INGRESO)."""
        postulante = self.get_object()
        puntaje = request.data.get('puntaje')
        estado_final = request.data.get('estado_general')

        if puntaje is None or estado_final not in ['INGRESO', 'NO_INGRESO']:
            return Response(
                {'error': 'Debe enviar puntaje válido y estado_general (INGRESO o NO_INGRESO).'},
                status=status.HTTP_400_BAD_REQUEST
            )

        postulante.puntaje = puntaje
        postulante.estado_general = estado_final
        postulante.save(update_fields=['puntaje', 'estado_general'])

        HistorialAuditoria.objects.create(
            postulante=postulante,
            usuario=request.user,
            accion='CALIFICACION_EXAMEN',
            detalle=f'Puntaje asignado: {puntaje}. Condición final: {postulante.get_estado_general_display()}.'
        )
        return Response(PostulanteSerializer(postulante).data)


class RequisitoExpedienteViewSet(viewsets.ModelViewSet):
    queryset = RequisitoExpediente.objects.select_related('postulante', 'verificado_por')
    serializer_class = RequisitoExpedienteSerializer

    @action(detail=True, methods=['patch'], url_path='verificar')
    def verificar(self, request, pk=None):
        """Actualiza el semáforo de un documento y recalcula el estado general del postulante."""
        requisito = self.get_object()
        nuevo_estado = request.data.get('estado')
        observacion = request.data.get('observacion', '')
        numero_referencia = request.data.get('numero_referencia', requisito.numero_referencia)

        if nuevo_estado not in ['PENDIENTE', 'OBSERVADO', 'VERIFICADO']:
            return Response(
                {'error': 'Estado inválido. Use PENDIENTE, OBSERVADO o VERIFICADO.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        requisito.estado = nuevo_estado
        requisito.observacion = observacion
        requisito.numero_referencia = numero_referencia
        requisito.verificado_por = request.user
        requisito.save()

        # Recalcular estado general del expediente
        requisito.postulante.recalcular_estado_expediente()

        # Registrar auditoría trazable
        HistorialAuditoria.objects.create(
            postulante=requisito.postulante,
            usuario=request.user,
            accion=f'DOC_{nuevo_estado}',
            detalle=f'{requisito.get_tipo_documento_display()} marcado como {nuevo_estado}. '
                    f'{("Obs: " + observacion) if observacion else "Sin observaciones."}'
        )

        return Response({
            'requisito': RequisitoExpedienteSerializer(requisito).data,
            'estado_general_postulante': requisito.postulante.estado_general,
            'estado_general_display': requisito.postulante.get_estado_general_display(),
        })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def consulta_publica_dni(request, dni):
    """Consulta transparente por DNI o código de verificación (sin requerir login)."""
    postulante = Postulante.objects.select_related('proceso', 'programa').prefetch_related(
        'requisitos', 'auditorias'
    ).filter(Q(dni=dni) | Q(codigo_verificacion__iexact=dni)).first()

    if not postulante:
        return Response(
            {'error': 'No se encontró ningún postulante con ese DNI o código de verificación.'},
            status=status.HTTP_404_NOT_FOUND
        )
    return Response(ConsultaPublicaPostulanteSerializer(postulante).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_metricas(request):
    """Métricas en vivo para el panel de la comisión de admisión."""
    total = Postulante.objects.count()
    por_estado = Postulante.objects.values('estado_general').annotate(cantidad=Count('id'))
    estados_dict = {item['estado_general']: item['cantidad'] for item in por_estado}

    por_programa = list(
        ProgramaEstudio.objects.annotate(inscritos=Count('postulantes')).values(
            'codigo', 'nombre', 'vacantes', 'inscritos'
        )
    )

    return Response({
        'total_postulantes': total,
        'pendientes': estados_dict.get('PENDIENTE', 0),
        'observados': estados_dict.get('OBSERVADO', 0),
        'aptos': estados_dict.get('APTO', 0),
        'ingresantes': estados_dict.get('INGRESO', 0),
        'no_ingresantes': estados_dict.get('NO_INGRESO', 0),
        'por_programa': por_programa,
    })