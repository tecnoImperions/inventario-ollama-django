from django.core.validators import MinValueValidator
from django.db import models


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código único")
    nombre = models.CharField(max_length=150, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, default="", verbose_name="Descripción")
    categoria = models.CharField(max_length=100, verbose_name="Categoría")
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Precio",
        validators=[MinValueValidator(0, "El precio no puede ser negativo.")],
    )
    cantidad_existente = models.IntegerField(
        default=0, verbose_name="Cantidad disponible",
        validators=[MinValueValidator(0, "La cantidad no puede ser negativa.")],
    )
    stock_minimo = models.IntegerField(
        default=5, verbose_name="Stock mínimo",
        validators=[MinValueValidator(0, "El stock mínimo no puede ser negativo.")],
    )
    estado = models.BooleanField(default=True, verbose_name="Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de registro")


    class Meta:
        db_table = "productos"
        ordering = ["categoria", "nombre"]


    def __str__(self):
        return f"{self.codigo} - {self.nombre} ({self.cantidad_existente} u.)"




class Categoria(models.Model):
    """Catalogo de categorias del inventario (CRUD independiente).

    Producto.categoria sigue siendo texto para no romper los filtros ni los
    reportes ya validados; este catalogo permite elegir de una lista, anadir
    y eliminar categorias, y se sincroniza al guardar un producto.
    """
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Categoría")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        db_table = "categorias"
        ordering = ["nombre"]
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre

    @property
    def total_productos(self):
        return Producto.objects.filter(categoria__iexact=self.nombre).count()


class ConsultaIA(models.Model):
    pregunta = models.TextField(verbose_name="Pregunta del usuario")
    respuesta = models.TextField(verbose_name="Respuesta de Ollama")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")


    class Meta:
        db_table = "consultas_ia"
        ordering = ["-fecha"]


    def __str__(self):
        return f"[{self.fecha.strftime('%d/%m/%Y %H:%M')}] {self.pregunta[:40]}"
