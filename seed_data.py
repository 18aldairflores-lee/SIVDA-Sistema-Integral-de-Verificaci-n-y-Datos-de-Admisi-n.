import os
import django
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from admision.models import (
    ProcesoAdmision,
    ProgramaEstudio,
    Postulante,
    RequisitoExpediente,
    HistorialAuditoria,
)

# 1. Usuarios (contraseñas encriptadas con bcrypt)
admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@hsivda.edu.pe', 'is_staff': True, 'is_superuser': True})
admin_user.set_password('Admin2026*')
admin_user.save()

verificador, _ = User.objects.get_or_create(username='verificador1', defaults={'email': 'verificador@hsivda.edu.pe', 'is_staff': True})
verificador.set_password('Verificador2026*')
verificador.save()

# 2. Proceso de Admisión
proceso, _ = ProcesoAdmision.objects.get_or_create(
    periodo='2026-II',
    defaults={
        'nombre': 'Proceso de Admisión Ordinario 2026-II',
        'fecha_inicio': date(2026, 10, 1),
        'fecha_examen': date(2026, 12, 15),
        'activo': True,
    }
)

# 3. Programas de Estudio
programas_data = [
    ('ACC', 'Administración de Centros de Cómputo', 40),
    ('DSI', 'Desarrollo de Sistemas de Información', 35),
    ('CON', 'Contabilidad', 30),
    ('ENF', 'Enfermería Técnica', 35),
]
programas = {}
for codigo, nombre, vacantes in programas_data:
    prog, _ = ProgramaEstudio.objects.get_or_create(codigo=codigo, defaults={'nombre': nombre, 'vacantes': vacantes})
    programas[codigo] = prog

# 4. Postulantes de prueba
postulantes_data = [
    ('74125896', 'Carlos Enrique', 'Quispe Mamani', 'carlos.quispe@gmail.com', '951234567', 'ACC', 'ORDINARIO', 'APTO'),
    ('75236984', 'María Fernanda', 'Condori Flores', 'maria.condori@gmail.com', '952345678', 'DSI', 'EXONERADO', 'OBSERVADO'),
    ('76347812', 'Luis Alberto', 'Choque Apaza', 'luis.choque@gmail.com', '953456789', 'ACC', 'ORDINARIO', 'PENDIENTE'),
    ('77458923', 'Lucía Valeria', 'Pari Ticona', 'lucia.pari@gmail.com', '954567890', 'ENF', 'ORDINARIO', 'INGRESO'),
    ('78569034', 'Diego Armando', 'Ramos Calisaya', 'diego.ramos@gmail.com', '955678901', 'CON', 'TRASLADO', 'OBSERVADO'),
    ('79670145', 'Sofía Alejandra', 'Vargas Cutipa', 'sofia.vargas@gmail.com', '956789012', 'DSI', 'ORDINARIO', 'APTO'),
]

for dni, nombres, apellidos, email, tel, prog_cod, mod, estado_obj in postulantes_data:
    post, created = Postulante.objects.get_or_create(
        dni=dni,
        defaults={
            'nombres': nombres,
            'apellidos': apellidos,
            'email': email,
            'telefono': tel,
            'proceso': proceso,
            'programa': programas[prog_cod],
            'modalidad': mod,
            'puntaje': 84.50 if estado_obj == 'INGRESO' else None,
            'estado_general': estado_obj,
        }
    )
    if created:
        for cod_doc, _ in RequisitoExpediente.TIPOS_DOCUMENTO:
            est_doc = 'PENDIENTE'
            obs = ''
            if estado_obj in ['APTO', 'INGRESO']:
                est_doc = 'VERIFICADO'
            elif estado_obj == 'OBSERVADO' and cod_doc == 'VOUCHER':
                est_doc = 'OBSERVADO'
                obs = 'Imagen borrosa del número de operación bancaria.'
            elif estado_obj == 'OBSERVADO' and cod_doc == 'DNI':
                est_doc = 'VERIFICADO'

            RequisitoExpediente.objects.create(
                postulante=post,
                tipo_documento=cod_doc,
                numero_referencia=f'OP-{dni[-4:]}' if cod_doc == 'VOUCHER' else '',
                estado=est_doc,
                observacion=obs,
                verificado_por=verificador if est_doc != 'PENDIENTE' else None,
            )

        HistorialAuditoria.objects.create(
            postulante=post,
            usuario=verificador,
            accion='CARGA_INICIAL',
            detalle=f'Expediente inicializado con estado {estado_obj}.'
        )

print("Datos de prueba cargados correctamente.")
print("Usuario admin: admin / Admin2026*")
print("Usuario verificador: verificador1 / Verificador2026*")