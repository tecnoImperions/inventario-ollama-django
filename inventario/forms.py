from django import forms

from .models import Producto


class CategoriaForm(forms.Form):
    """Valida el nombre de una categoria del catalogo (alta y edicion)."""

    nombre = forms.CharField(max_length=100)

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre de la categoría es obligatorio.")
        if len(nombre) > 100:
            raise forms.ValidationError("Máximo 100 caracteres.")
        return nombre


class ProductoForm(forms.ModelForm):
    """Formulario oficial de Producto (RF-01 a RF-05).

    Valida en el frontend del servidor:
      - Código único (case-insensitive).
      - Precio, cantidad_existente y stock_minimo NO negativos.
    """

    class Meta:
        model = Producto
        fields = [
            "codigo", "nombre", "descripcion", "categoria",
            "precio", "cantidad_existente", "stock_minimo", "estado",
        ]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo", "").strip()
        if not codigo:
            raise forms.ValidationError("El código único es obligatorio.")
        conflictos = Producto.objects.filter(codigo__iexact=codigo)
        if self.instance.pk:
            conflictos = conflictos.exclude(pk=self.instance.pk)
        if conflictos.exists():
            raise forms.ValidationError("Ya existe un producto con ese código único.")
        return codigo

    def clean_nombre(self):
        nombre = self.cleaned_data.get("nombre", "").strip()
        if not nombre:
            raise forms.ValidationError("El nombre es obligatorio.")
        return nombre

    def clean_categoria(self):
        categoria = self.cleaned_data.get("categoria", "").strip()
        if not categoria:
            raise forms.ValidationError("La categoría es obligatoria.")
        return categoria

    def clean_precio(self):
        precio = self.cleaned_data.get("precio")
        if precio is not None and precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio

    def clean_cantidad_existente(self):
        cantidad = self.cleaned_data.get("cantidad_existente")
        if cantidad is not None and cantidad < 0:
            raise forms.ValidationError("La cantidad no puede ser negativa.")
        return cantidad

    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get("stock_minimo")
        if stock_minimo is not None and stock_minimo < 0:
            raise forms.ValidationError("El stock mínimo no puede ser negativo.")
        return stock_minimo