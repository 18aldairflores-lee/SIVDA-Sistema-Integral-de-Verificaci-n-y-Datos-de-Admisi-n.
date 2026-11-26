from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    ProcesoAdmision,
    ProgramaEstudio,
    Postulante,
    RequisitoExpediente,
    HistorialAuditoria,
)


class ProcesoAdmisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcesoAdmision
        fields = '__all__'


class ProgramaEstudioSerializer(serializers.ModelSerializer):
    total_postulantes = serializers.IntegerField(source='postulantes.count', read_only=True)

    class Meta:
        model = ProgramaEstudio
        fields = ['id', 'codigo', 'nombre', 'vacantes', 'total_postulantes']


class RequisitoExpedienteSerializer(serializers.ModelSerializer):
    tipo_documento_display = serializers.CharField(source='get_tipo_documento_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    verificado_por_username = serializers.CharField(source='verificado_por.username', read_only=True, default=None)

    class Meta:
        model = RequisitoExpediente
        fields = [
            'id', 'postulante', 'tipo_documento', 'tipo_documento_display',
            'numero_referencia', 'estado', 'estado_display', 'observacion',
            'verificado_por', 'verificado_por_username', 'fecha_actualizacion'
        ]
        read_only_fields = ['verificado_por', 'fecha_actualizacion']


class HistorialAuditoriaSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True, default='Sistema')

    class Meta:
        model = HistorialAuditoria
        fields = ['id', 'postulante', 'usuario_username', 'accion', 'detalle', 'fecha']


class PostulanteSerializer(serializers.ModelSerializer):
    programa_nombre = serializers.CharField(source='programa.nombre', read_only=True)
    proceso_periodo = serializers.CharField(source='proceso.periodo', read_only=True)
    estado_general_display = serializers.CharField(source='get_estado_general_display', read_only=True)
    modalidad_display = serializers.CharField(source='get_modalidad_display', read_only=True)
    requisitos = RequisitoExpedienteSerializer(many=True, read_only=True)
    auditorias = HistorialAuditoriaSerializer(many=True, read_only=True)

    class Meta:
        model = Postulante
        fields = [
            'id', 'codigo_verificacion', 'dni', 'nombres', 'apellidos',
            'email', 'telefono', 'proceso', 'proceso_periodo',
            'programa', 'programa_nombre', 'modalidad', 'modalidad_display',
            'estado_general', 'estado_general_display', 'puntaje',
            'fecha_registro', 'requisitos', 'auditorias'
        ]
        read_only_fields = ['codigo_verificacion', 'fecha_registro']

    def create(self, validated_data):
        postulante = super().create(validated_data)
        # Crear automáticamente los 5 requisitos obligatorios en estado PENDIENTE
        for codigo_doc, _ in RequisitoExpediente.TIPOS_DOCUMENTO:
            RequisitoExpediente.objects.create(
                postulante=postulante,
                tipo_documento=codigo_doc,
                estado='PENDIENTE'
            )
        return postulante


class ConsultaPublicaPostulanteSerializer(serializers.ModelSerializer):
    programa_nombre = serializers.CharField(source='programa.nombre', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)
    estado_general_display = serializers.CharField(source='get_estado_general_display', read_only=True)
    requisitos = RequisitoExpedienteSerializer(many=True, read_only=True)
    auditorias = HistorialAuditoriaSerializer(many=True, read_only=True)

    class Meta:
        model = Postulante
        fields = [
            'codigo_verificacion', 'dni', 'nombres', 'apellidos',
            'proceso_nombre', 'programa_nombre', 'modalidad',
            'estado_general', 'estado_general_display', 'puntaje',
            'fecha_registro', 'requisitos', 'auditorias'
        ]