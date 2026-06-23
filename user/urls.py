from django.urls import path, include
from .views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    LogoutView,
    ProfileView
)
from .view import UserViewSet, IsSuperUser, RoleModelViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r"usuarios", UserViewSet, basename="usuario")
router.register(r"roles", RoleModelViewSet, basename="role")

urlpatterns = [
    path("auth/sign/", CustomTokenObtainPairView.as_view()),
    path("auth/refresh/", CustomTokenRefreshView.as_view()),
    path("auth/verify/", CustomTokenVerifyView.as_view()),
    path("logout/", LogoutView.as_view()),
    path('user/me/', ProfileView.as_view()),
    
    path('auth/roles/', IsSuperUser.as_view(), name="get"),

    path('sistema/', include(router.urls))
]
