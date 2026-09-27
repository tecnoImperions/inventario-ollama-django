from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Sum

from .forms import CategoriaForm, ProductoForm
from .ia import chat_consulta
from .models import ConsultaIA, Categoria, Producto
from .reportes import generar_reporte


@csrf_exempt
def panel_inventario(request):
    if request.method == "POST":
        pregunta = request.POST.get("pregunta", "").strip()
        if not pregunta:
            return JsonResponse({"error": "Por favor escribe una consulta."}, status=400)
        return JsonResponse({"respuesta": chat_consulta(pregunta)})

    mostrar_inactivos = request.GET.get("mostrar") == "inactivos"
    if mostrar_inactivos:
        productos = Producto.objects.all().order_by("categoria", "nombre")
    else:
        productos = Producto.objects.filter(estado=True).order_by("categoria", "nombre")
    activos_qs = Producto.objects.filter(estado=True)
    total_articulos = activos_qs.count()
    criticos_count = activos_qs.filter(
        cantidad_existente__lte=F('stock_minimo'), cantidad_existente__gt=0
    ).count()
    agotados_count = activos_qs.filter(cantidad_existente=0).count()
    total_stock = activos_qs.aggregate(total=Sum('cantidad_existente'))['total'] or 0
    valor_total = sum(p.cantidad_existente * p.precio for p in activos_qs)

    categorias = Producto.objects.filter(estado=True).values_list("categoria", flat=True).distinct().order_by("categoria")

    # Catalogo completo (incluye categorias sin productos) para el combo del
    # formulario y el panel de administracion de categorias.
    catalogo = Categoria.objects.all()
    context = {
        "productos": productos,
        "categorias": categorias,
        "catalogo": catalogo,
        "mostrar_inactivos": mostrar_inactivos,
        "total_inactivos": Producto.objects.filter(estado=False).count(),
        "total_articulos": total_articulos,
        "criticos_count": criticos_count,
        "agotados_count": agotados_count,
        "total_stock": total_stock,
        "valor_total": f"{valor_total:,.2f}",
    }
    return render(request, "inventario/index.html", context)

@csrf_exempt
def chat_ia(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    pregunta = request.POST.get("pregunta", "").strip()
    if not pregunta:
        return JsonResponse({"error": "Por favor escribe una consulta."}, status=400)
    return JsonResponse({"ok": True, "respuesta": chat_consulta(pregunta)})


@csrf_exempt
def reporte_view(request):
    if request.method != "GET":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    tipo = request.GET.get("tipo", "").strip()
    categoria = request.GET.get("categoria", "").strip() or None
    try:
        return JsonResponse({"ok": True, "reporte": generar_reporte(tipo, categoria)})
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def guardar_producto(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    # Validación centralizada en ProductoForm (RF-01 a RF-05):
    # código único, obligatorios y números NO negativos.
    prod_id = request.POST.get("id")
    producto = get_object_or_404(Producto, id=prod_id) if prod_id else None
    form = ProductoForm(request.POST, instance=producto)
    if not form.is_valid():
        return JsonResponse({"error": "; ".join(
            f"{campo}: {mensajes[0]}" for campo, mensajes in form.errors.items()
        )}, status=400)

    form.save()
    # Sincroniza el catalogo: si la categoria es nueva, queda registrada para
    # poder elegirla luego en el combo sin volver a escribirla.
    Categoria.objects.get_or_create(nombre=form.cleaned_data["categoria"].strip())
    return JsonResponse({"ok": True, "status": "ok"})


# ---------- Categorias (CRUD del catalogo) ----------

@csrf_exempt
def listar_categorias(request):
    categorias = [
        {
            "id": c.id,
            "nombre": c.nombre,
            "total_productos": Producto.objects.filter(categoria__iexact=c.nombre).count(),
        }
        for c in Categoria.objects.all()
    ]
    return JsonResponse({"ok": True, "categorias": categorias})


@csrf_exempt
def guardar_categoria(request):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    form = CategoriaForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": "; ".join(
            f"{campo}: {mensajes[0]}" for campo, mensajes in form.errors.items()
        )}, status=400)

    nombre = form.cleaned_data["nombre"]
    cat_id = request.POST.get("id")
    if cat_id:
        categoria = get_object_or_404(Categoria, id=cat_id)
        if Categoria.objects.filter(nombre__iexact=nombre).exclude(id=cat_id).exists():
            return JsonResponse({"error": "Ya existe una categoría con ese nombre."}, status=400)
        anterior = categoria.nombre
        categoria.nombre = nombre
        categoria.save()
        # Los productos que usaban el nombre anterior siguen apuntando al texto.
        Producto.objects.filter(categoria__iexact=anterior).update(categoria=nombre)
        return JsonResponse({"ok": True, "id": categoria.id, "nombre": categoria.nombre})

    if Categoria.objects.filter(nombre__iexact=nombre).exists():
        return JsonResponse({"error": "Esa categoría ya existe."}, status=400)
    categoria = Categoria.objects.create(nombre=nombre)
    return JsonResponse({"ok": True, "id": categoria.id, "nombre": categoria.nombre})


@csrf_exempt
def eliminar_categoria(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)

    categoria = get_object_or_404(Categoria, pk=pk)
    en_uso = Producto.objects.filter(categoria__iexact=categoria.nombre).count()
    if en_uso:
        return JsonResponse({
            "error": f"No se puede eliminar '{categoria.nombre}': {en_uso} producto(s) la están usando."
        }, status=400)
    nombre = categoria.nombre
    categoria.delete()
    return JsonResponse({"ok": True, "eliminado": nombre})


@csrf_exempt
def eliminar_producto(request, pk):
    """Borrado fisico y borrado logico (RF-04).

    - modo=logico  -> desactiva el producto (estado=False) sin borrar la fila.
    - modo=fisico  -> elimina la fila de la base de datos.
    Por defecto se usa el borrado logico, que es el seguro para un POS.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    producto = get_object_or_404(Producto, pk=pk)
    modo = (request.POST.get("modo") or "logico").strip().lower()

    if modo == "fisico":
        producto.delete()
        return JsonResponse({"ok": True, "modo": "fisico", "status": "ok"})

    if modo != "logico":
        return JsonResponse({"error": "Modo inválido. Usa 'logico' o 'fisico'."}, status=400)

    producto.estado = False
    producto.save(update_fields=["estado"])
    return JsonResponse({"ok": True, "modo": "logico", "status": "ok"})


@csrf_exempt
def ajustar_stock(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    operacion = request.POST.get("operacion", "").strip()
    if operacion not in ("sumar", "restar"):
        return JsonResponse({"error": "Operación inválida. Usa 'sumar' o 'restar'."}, status=400)
    producto = get_object_or_404(Producto, pk=pk)
    if operacion == "sumar":
        producto.cantidad_existente += 1
    else:
        if producto.cantidad_existente <= 0:
            return JsonResponse({"error": f"'{producto.nombre}' ya tiene stock cero."}, status=400)
        producto.cantidad_existente -= 1
    producto.save()
    return JsonResponse({
        "ok": True,
        "cantidad_existente": producto.cantidad_existente,
        "critico": producto.cantidad_existente <= producto.stock_minimo,
        "agotado": producto.cantidad_existente == 0,
    })


@csrf_exempt
def historial_consultas(request):
    consultas = ConsultaIA.objects.all()[:20]
    datos = [
        {
            "pregunta": c.pregunta,
            "respuesta": c.respuesta,
            "fecha": c.fecha.strftime("%d/%m/%Y %H:%M"),
        }
        for c in consultas
    ]
    return JsonResponse({"ok": True, "consultas": datos})