# common/utils/files.py
import hashlib
import os
from datetime import datetime


def generate_storage_name(original_filename, user_id=None):
    """
    Genera un nombre único para almacenamiento
    
    Equivalente a lo que harías en Java para evitar colisiones
    """
    # Extraer extensión
    name, ext = os.path.splitext(original_filename)
    ext = ext.lower()
    
    # Generar hash único
    unique_str = f"{original_filename}_{user_id or ''}_{datetime.now().timestamp()}"
    hash_md5 = hashlib.md5(unique_str.encode()).hexdigest()[:8]
    
    # Slug del nombre original (sin extensión)
    from django.utils.text import slugify
    slug_name = slugify(name)[:50]  # Limitar longitud
    
    # Nombre final: slug-hash.ext
    return f"{slug_name}-{hash_md5}{ext}"


def determine_file_type(mime_type, filename):
    """
    Determina el tipo de archivo basado en MIME type y extensión
    """
    # Mapeo de MIME types a tipos
    mime_mapping = {
        'image/': 'image',
        'video/': 'video',
        'audio/': 'audio',
        'application/pdf': 'document',
        'application/msword': 'document',
        'application/vnd.openxmlformats': 'document',
        'application/zip': 'archive',
        'application/x-rar-compressed': 'archive',
    }
    
    # Verificar por prefijos de MIME type
    for prefix, file_type in mime_mapping.items():
        if mime_type.startswith(prefix):
            return file_type
    
    # Por extensión como fallback
    ext = os.path.splitext(filename)[1].lower()
    extension_mapping = {
        '.jpg': 'image', '.jpeg': 'image', '.png': 'image',
        '.gif': 'image', '.bmp': 'image', '.svg': 'image',
        '.mp4': 'video', '.avi': 'video', '.mov': 'video',
        '.mp3': 'audio', '.wav': 'audio', '.ogg': 'audio',
        '.pdf': 'document', '.doc': 'document', '.docx': 'document',
        '.xls': 'document', '.xlsx': 'document', '.ppt': 'document',
        '.pptx': 'document', '.txt': 'document',
        '.zip': 'archive', '.rar': 'archive', '.7z': 'archive',
    }
    
    return extension_mapping.get(ext, 'other')