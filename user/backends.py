from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission


class RolePermissionBackend(ModelBackend):
    """
    Backend que modifica completamente group 
    y obtiene permisos exclusivamente de role.
    Respeta is_superuser como bypass total.
    """

    def get_user_permissions(self, user_obj, obj=None):
        """Obtiene permisos desde los roles del usuario"""
        
        # 1. Superuser tiene TODOS los permisos
        if user_obj.is_superuser:
            from django.contrib.auth.models import Permission
            return set(
                f"{p.content_type.app_label}.{p.codename}" 
                for p in Permission.objects.select_related('content_type')
            )
        
        # 2. Usuario inactivo o no autenticado = sin permisos
        if not user_obj.is_active or not user_obj.is_authenticated:
            return set()
        
        # 3. Obtiene permisos desde roles
        permisos = set()
        for role in user_obj.roles.all():
            for perm in role.permission.all():
                permisos.add(f"{perm.content_type.app_label}.{perm.codename}")
        
        return permisos
    
    def get_group_permissions(self, user_obj, obj=None):
        """
        Django siempre pregunta por groups.
        Groups se usa para giros, no para permisos.
        """
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        """Retorna todos los permisos del usuario"""
        
        # 1. Superuser bypass
        if user_obj.is_superuser:
            from django.contrib.auth.models import Permission
            return set(
                f"{p.content_type.app_label}.{p.codename}" 
                for p in Permission.objects.select_related('content_type')
            )
        
        # 2. Usuario inactivo = sin permisos
        if not user_obj.is_active or not user_obj.is_authenticated:
            return set()
        
        # 3. Obtiene permisos desde roles
        return self.get_user_permissions(user_obj)

    def has_perm(self, user_obj, perm, obj=None):
        """Verifica si el usuario tiene un permiso específico"""
        
        # 1. Superuser siempre tiene todos los permisos
        if user_obj.is_superuser:
            return True
        
        # 2. Usuario inactivo = no tiene permisos
        if not user_obj.is_active or not user_obj.is_authenticated:
            return False
        
        # 3. Verifica en los permisos del usuario
        return perm in self.get_all_permissions(user_obj)