from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProcesoAdmisionViewSet,
    ProgramaEstudioViewSet,
    PostulanteViewSet,
    RequisitoExpedienteViewSet,
    consulta_publica_dni,
    dashboard_metricas,
)

router = DefaultRouter()
router.register(r'procesos', ProcesoAdmisionViewSet, basename='proceso')
router.register(r'programas', ProgramaEstudioViewSet, basename='programa')
router.register(r'postulantes', PostulanteViewSet, basename='postulante')
router.register(r'requisitos', RequisitoExpedienteViewSet, basename='requisito')

urlpatterns = [
    path('', include(router.urls)),
    path('consulta/<str:dni>/', consulta_publica_dni, name='consulta-publica'),
    path('dashboard/metricas/', dashboard_metricas, name='dashboard-metricas'),
]