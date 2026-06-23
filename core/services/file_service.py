# services/file_service.py
import os
import uuid
from django.core.files.storage import default_storage
from django.conf import settings
from pathlib import Path


class FileStorageService:
    """
    Servicio para manejar operaciones de archivos
    Similar a un @Service en Spring
    """
    
    @staticmethod
    def save_file(file_obj, relative_path, custom_name=None):
        """
        Guarda un archivo en el storage
        
        Args:
            file_obj: Archivo de Django (request.FILES['file'])
            relative_path: Ruta relativa donde guardar
            custom_name: Nombre personalizado (opcional)
        
        Returns:
            dict: Información del archivo guardado
        """
        # Generar nombre único si no se proporciona
        if not custom_name:
            ext = Path(file_obj.name).suffix
            custom_name = f"{uuid.uuid4().hex}{ext}"
        
        # Ruta completa
        full_path = os.path.join(relative_path, custom_name)
        
        # Guardar físicamente
        default_storage.save(full_path, file_obj)
        
        return {
            'storage_name': custom_name,
            'original_name': file_obj.name,
            'path': relative_path,
            'full_path': full_path,
            'size': file_obj.size,
            'mime_type': file_obj.content_type
        }
    
    @staticmethod
    def delete_file(full_path):
        """Elimina un archivo del storage"""
        if default_storage.exists(full_path):
            default_storage.delete(full_path)
            return True
        return False
    
    @staticmethod
    def get_file_url(full_path):
        """Obtiene URL para acceder al archivo"""
        # Depende de tu configuración
        if hasattr(settings, 'USE_S3') and settings.USE_S3:
            # Para S3
            import boto3
            s3_client = boto3.client('s3')
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': full_path
                },
                ExpiresIn=3600  # URL válida por 1 hora
            )
            return url
        else:
            # Para almacenamiento local
            return default_storage.url(full_path)