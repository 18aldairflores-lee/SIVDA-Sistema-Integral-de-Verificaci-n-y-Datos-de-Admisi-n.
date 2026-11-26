import uuid
from django.db import models
from django.contrib.auth.models import User


def generar_codigo_verificacion():
    return f"HSIVDA-{uuid.uuid4().hex[:8].upper()}"


class ProcesoAdmision(models.Model):
    nombre = models.CharField(max_length=120)
    periodo = models.CharField(max_length=20, unique=True)  # Ej: 2026-II
    fecha_inicio = models.DateField()
    fecha_examen = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Proceso de Admisión"
        verbose_name_plural = "Procesos de Admisión"

    def __str__(self):
        return f"{self.nombre} ({self.periodo})"


class ProgramaEstudio(models.Model):
    codigo = models.CharField(max_length=15, unique=True)
    nombre = models.CharField(max_length=120)
    vacantes = models.PositiveIntegerField(default=30)

    class Meta:
        verbose_name = "Programa de Estudio"
        verbose_name_plural = "Programas de Estudio"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Postulante(models.Model):
    MODALIDADES = [
        ('ORDINARIO', 'Ordinario'),
        ('EXONERADO', 'Exonerado (Primeros Puestos / Deportista)'),
        ('TRASLADO', 'Traslado Externo'),
    ]
    ESTADOS_GENERALES = [
        ('PENDIENTE', 'Pendiente de Verificación'),
        ('OBSERVADO', 'Con Observaciones'),
        ('APTO', 'Apto para Examen'),
        ('INGRESO', 'Ingresó'),
        ('NO_INGRESO', 'No Ingresó'),
    ]

    codigo_verificacion = models.CharField(
        max_length=20,
        unique=True,
        default=generar_codigo_verificacion,
        editable=False
    )
    dni = models.CharField(max_length=8, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    email = models.EmailField()
    telefono = models.CharField(max_length=15)
    proceso = models.ForeignKey(ProcesoAdmision, on_delete=models.PROTECT, related_name='postulantes')
    programa = models.ForeignKey(ProgramaEstudio, on_delete=models.PROTECT, related_name='postulantes')
    modalidad = models.CharField(max_length=20, choices=MODALIDADES, default='ORDINARIO')
    estado_general = models.CharField(max_length=20, choices=ESTADOS_GENERALES, default='PENDIENTE')
    puntaje = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.dni} - {self.apellidos}, {self.nombres}"

    def recalcular_estado_expediente(self):
        """Actualiza automáticamente el estado general según el semáforo de requisitos."""
        if self.estado_general in ['INGRESO', 'NO_INGRESO']:
            return
        requisitos = self.requisitos.all()
        if not requisitos.exists():
            self.estado_general = 'PENDIENTE'
        elif requisitos.filter(estado='OBSERVADO').exists():
            self.estado_general = 'OBSERVADO'
        elif requisitos.filter(estado='VERIFICADO').count() == requisitos.count():
            self.estado_general = 'APTO'
        else:
            self.estado_general = 'PENDIENTE'
        self.save(update_fields=['estado_general'])


class RequisitoExpediente(models.Model):
    TIPOS_DOCUMENTO = [
        ('DNI', 'Copia de DNI'),
        ('CERTIFICADO', 'Certificado de Estudios'),
        ('PARTIDA', 'Partida de Nacimiento'),
        ('VOUCHER', 'Voucher de Pago de Admisión'),
        ('FOTO', 'Fotografía Digital'),
    ]
    ESTADOS_DOC = [
        ('PENDIENTE', 'Pendiente'),
        ('OBSERVADO', 'Observado'),
        ('VERIFICADO', 'Verificado'),
    ]

    postulante = models.ForeignKey(Postulante, on_delete=models.CASCADE, related_name='requisitos')
    tipo_documento = models.CharField(max_length=20, choices=TIPOS_DOCUMENTO)
    numero_referencia = models.CharField(max_length=60, blank=True, help_text="Ej: Nro. de operación o folio")
    estado = models.CharField(max_length=15, choices=ESTADOS_DOC, default='PENDIENTE')
    observacion = models.TextField(blank=True)
    verificado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('postulante', 'tipo_documento')

    def __str__(self):
        return f"{self.postulante.dni} - {self.get_tipo_documento_display()} ({self.estado})"


class HistorialAuditoria(models.Model):
    postulante = models.ForeignKey(Postulante, on_delete=models.CASCADE, related_name='auditorias')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=60)
    detalle = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"[{self.fecha:%Y-%m-%d %H:%M}] {self.postulante.dni} - {self.accion}"