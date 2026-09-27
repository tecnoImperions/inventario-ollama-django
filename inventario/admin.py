from django.contrib import admin

from .models import ConsultaIA, Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "categoria", "precio", "cantidad_existente", "stock_minimo", "estado")
    list_filter = ("categoria", "estado")
    search_fields = ("codigo", "nombre", "categoria")


@admin.register(ConsultaIA)
class ConsultaIAAdmin(admin.ModelAdmin):
    list_display = ("pregunta", "fecha")
    readonly_fields = ("pregunta", "respuesta", "fecha")