"""URL configuration for config project."""
from django.contrib import admin
from django.urls import path
from inventario import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.panel_inventario, name='panel'),
    path('api/chat/', views.chat_ia, name='chat_ia'),
    path('api/reporte/', views.reporte_view, name='reporte'),
    path('api/producto/guardar/', views.guardar_producto, name='guardar_producto'),
    path('api/producto/<int:pk>/eliminar/', views.eliminar_producto, name='eliminar_producto'),
    path('api/producto/<int:pk>/ajustar_stock/', views.ajustar_stock, name='ajustar_stock'),
    path('api/historial/', views.historial_consultas, name='historial_consultas'),
]