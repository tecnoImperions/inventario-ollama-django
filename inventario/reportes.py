import logging

from django.db.models import F, Sum

from .models import ConsultaIA, Producto
from .ollama_client import consultar_ollama

logger = logging.getLogger(__name__)


def _estado_producto(p):
    if p.cantidad_existente == 0:
        return "Agotado"
    if p.cantidad_existente <= p.stock_minimo:
        return "Bajo"
    return "Óptimo"


def _tabla_markdown(productos):
    lineas = ["| Código | Producto | Categoría | Stock | Precio (Bs.) | Estado |",
              "|---|---|---|---|---|---|"]
    for p in productos:
        stock = f"**{p.cantidad_existente}**" if p.cantidad_existente <= p.stock_minimo else str(p.cantidad_existente)
        lineas.append(f"| {p.codigo} | {p.nombre} | {p.categoria} | {stock} | {p.precio:.2f} | {_estado_producto(p)} |")
    return "\n".join(lineas)


def _resumen_para_ia(titulo, contenido):
    """Resume el reporte para el LLM sin volcarle la tabla Markdown completa.

    Si le mandamos la tabla completa, el modelo la copia en vez de explicarla
    (y se corta a media palabra por el limite de tokens), asi que le pasamos
    solo la cantidad de filas.
    """
    filas = [l for l in (contenido or "").splitlines()
             if l.strip().startswith("|") and "---" not in l]
    cantidad = max(len(filas) - 1, 0)
    if cantidad:
        return f"El reporte '{titulo}' es una tabla con {cantidad} filas de productos del almacen."
    return (contenido or titulo).strip()[:400]


def _explicacion_ollama(titulo, contenido):
    try:
        # Contexto compacto (muestra acotada) para acelerar la generación local.
        resumen = _resumen_para_ia(titulo, contenido)
        explicacion = consultar_ollama(
            f"Escribe 1 o 2 frases en español que expliquen este reporte de inventario. "
            f"No uses tablas, listas ni cabeceras. {resumen}",
            contexto_json={"tipo_reporte": titulo, "datos_del_reporte": resumen},
            options={"temperature": 0.1, "top_k": 10, "top_p": 0.9, "num_predict": 60, "num_ctx": 512},
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("Ollama no disponible para el reporte '%s': %s", titulo, e)
        explicacion = None
    # Descartamos tablas o respuestas cortadas: el modelo no aporta valor ahi.
    if not explicacion or "|" in explicacion or not explicacion.strip().endswith((".", "!", "?")):
        if explicacion:
            logger.info("Explicacion del modelo descartada para el reporte '%s'.", titulo)
        return "Reporte generado con los datos actuales del almacén (motor de IA no disponible)."
    return explicacion


def _finalizar(titulo, cuerpo, pregunta):
    explicacion = _explicacion_ollama(titulo, cuerpo)
    reporte = f"### Reporte: {titulo}\n\n{cuerpo}\n\n**Análisis IA:** {explicacion}"
    ConsultaIA.objects.create(pregunta=pregunta, respuesta=reporte)
    return reporte


def reporte_todos():
    productos = Producto.objects.filter(estado=True)
    titulo = "Todos los productos"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, "Reporte: todos los productos")


def reporte_mas_caro():
    productos = Producto.objects.filter(estado=True).order_by("-precio")[:5]
    titulo = "Productos más caros (Top 5)"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, "Reporte: productos más caros")


def reporte_mas_barato():
    productos = Producto.objects.filter(estado=True).order_by("precio")[:5]
    titulo = "Productos más baratos (Top 5)"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, "Reporte: productos más baratos")


def reporte_pocas_existencias():
    productos = Producto.objects.filter(estado=True, cantidad_existente__gt=0, cantidad_existente__lte=F('stock_minimo'))
    titulo = "Productos con pocas existencias"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, "Reporte: productos con pocas existencias")


def reporte_agotados():
    productos = Producto.objects.filter(estado=True, cantidad_existente=0)
    titulo = "Productos agotados (stock cero)"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, "Reporte: productos agotados")


def reporte_por_categoria(categoria=None):
    productos = Producto.objects.filter(estado=True)
    if categoria:
        productos = productos.filter(categoria__iexact=categoria)
    productos = productos.order_by("categoria", "nombre")
    titulo = f"Inventario por categoría: {categoria}" if categoria else "Inventario por categoría"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, f"Reporte: inventario por categoría {categoria or ''}".strip())


def reporte_valor_total():
    activos = Producto.objects.filter(estado=True)
    total_unidades = activos.aggregate(total=Sum('cantidad_existente'))['total'] or 0
    total_dinero = sum(p.cantidad_existente * p.precio for p in activos)
    total_productos = activos.count()
    titulo = "Valor total del inventario"
    cuerpo = (f"- Productos activos: **{total_productos}**\n"
              f"- Unidades en stock: **{total_unidades}**\n"
              f"- Valor económico estimado: **Bs. {total_dinero:,.2f}**")
    return _finalizar(titulo, cuerpo, "Reporte: valor total del inventario")


def reporte_mayor_cantidad():
    productos = Producto.objects.filter(estado=True).order_by("-cantidad_existente")[:5]
    titulo = "Productos con mayor cantidad en stock (Top 5)"
    cuerpo = _tabla_markdown(productos)
    return _finalizar(titulo, cuerpo, "Reporte: productos con mayor cantidad en stock")


REPORTES = {
    "todos": reporte_todos,
    "mas_caro": reporte_mas_caro,
    "mas_barato": reporte_mas_barato,
    "pocas_existencias": reporte_pocas_existencias,
    "agotados": reporte_agotados,
    "por_categoria": reporte_por_categoria,
    "valor_total": reporte_valor_total,
    "mayor_cantidad": reporte_mayor_cantidad,
}


def generar_reporte(tipo, categoria=None):
    """Patrón Strategy: selecciona en tiempo de ejecución el algoritmo de
    reporte correspondiente al tipo solicitado (más caro, agotados, etc.)."""
    if tipo not in REPORTES:
        raise ValueError(f"Reporte desconocido: {tipo}")
    if tipo == "por_categoria":
        return reporte_por_categoria(categoria)
    return REPORTES[tipo]()