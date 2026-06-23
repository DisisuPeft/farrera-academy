import os
import uuid
from django.utils.text import slugify
from datetime import datetime


def sanitize_filename(filename):
    name, ext = os.path.splitext(filename)
    # Mantener solo caracteres seguros
    clean_name = slugify(name)[:100]  # Máximo 100 caracteres
    return f"{clean_name}{ext.lower()}"


def generate_unique_filename(original_filename):
    name, ext = os.path.splitext(original_filename)
    unique_id = uuid.uuid4().hex[:12]  # 12 caracteres del UUID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{slugify(name)[:50]}_{timestamp}_{unique_id}{ext.lower()}"


# ========== FUNCIONES DE UPLOAD PATH ==========

def comprobante_validacion_path(instance, filename):
    validacion = instance.validacion
    plan_pago = validacion.plan_pago
    programa = plan_pago.campania.programa

    # Generar slug del programa
    programa_slug = slugify(programa.nombre)

    # Fecha de subida
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')

    # Nombre único
    unique_filename = generate_unique_filename(filename)

    return f"comprobantes/{programa_slug}/{year}/{month}/validacion_{validacion.id}/{unique_filename}"


def generic_upload_path(instance, filename):
    app_label = instance._meta.app_label
    model_name = instance._meta.model_name

    now = datetime.now()
    date_path = now.strftime('%Y/%m/%d')

    unique_filename = generate_unique_filename(filename)

    return f"uploads/{app_label}/{model_name}/{date_path}/{unique_filename}"