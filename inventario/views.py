from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Sum

from .forms import ProductoForm
from .ia import chat_consulta
from .models import ConsultaIA, Producto
from .reportes import generar_reporte


@csrf_exempt
def panel_inventario(request):
    if request.method == "POST":
        pregunta = request.POST.get("pregunta", "").strip()
        if not pregunta:
            return JsonResponse({"error": "Por favor escribe una consulta."}, status=400)
        return JsonResponse({"respuesta": chat_consulta(pregunta)})

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

    context = {
        "productos": productos,
        "categorias": categorias,
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
    return JsonResponse({"ok": True, "status": "ok"})


@csrf_exempt
def eliminar_producto(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Método no permitido"}, status=405)
    producto = get_object_or_404(Producto, pk=pk)
    producto.delete()
    return JsonResponse({"ok": True, "status": "ok"})


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