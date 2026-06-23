from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.core.cache import cache

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('Los usuarios deben tener un email valido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El super usuario debe contar con is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El super usuario debe contar con is_superuser=True.")

        return self.create_user(email, password, **extra_fields)