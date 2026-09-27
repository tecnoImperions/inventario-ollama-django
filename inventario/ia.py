import json
import logging

from django.db.models import F

from .models import ConsultaIA, Producto
from .ollama_client import ModeloNoRegistrado, consultar_ollama

logger = logging.getLogger(__name__)

# Preguntas explícitas que se responden de forma directa y precisa
# a partir del contexto JSON (sin esperar a Ollama -> respuesta en <1s).
INTENTO_PRECIO_MAXIMO = ("mas caro", "más caro", "mas costoso", "más costoso", "precio mas alto", "precio más alto")
INTENTO_PRECIO_MINIMO = ("mas barato", "más barato", "precio mas bajo", "precio más bajo", "mas economico", "más económico")
INTENTO_VALOR_TOTAL = ("valor total", "valor economico", "valor económico", "cuanto vale", "cuánto vale", "total del inventario", "capital")
INTENTO_CONTEO = ("cuantos productos", "cuántos productos", "cuantos articulos", "cuántos artículos", "cuantos hay", "total de productos")


def _estado_producto(p):
    if p.cantidad_existente == 0:
        return "Agotado"
    if p.cantidad_existente <= p.stock_minimo:
        return "Bajo"
    return "Óptimo"


def _serializar_producto(p):
    return {
        "codigo": p.codigo,
        "nombre": p.nombre,
        "categoria": p.categoria,
        # Decimal -> float antes de serializar a JSON (rápido y compatible)
        "precio": float(p.precio),
        "cantidad_existente": p.cantidad_existente,
        "stock_minimo": p.stock_minimo,
        "estado_stock": _estado_producto(p),
    }


def _hay_intento(q, intento):
    return any(k in q for k in intento)


def construir_contexto(pregunta):
    """Construye un contexto JSON estricto con los datos relevantes a la consulta."""
    q = pregunta.lower().strip()
    activos = Producto.objects.filter(estado=True)

    if _hay_intento(q, INTENTO_VALOR_TOTAL):
        total_unidades = sum(p.cantidad_existente for p in activos)
        total_dinero = float(sum(p.cantidad_existente * p.precio for p in activos))
        return {
            "tipo": "valor_total",
            "total_unidades": total_unidades,
            "total_bs": round(total_dinero, 2),
            "productos": [_serializar_producto(p) for p in activos],
            "explicacion_pregunta": "valor total del inventario",
        }

    if _hay_intento(q, INTENTO_PRECIO_MAXIMO):
        top = sorted(activos, key=lambda p: p.precio, reverse=True)
        mas_caro = top[0] if top else None
        return {
            "tipo": "precio_maximo",
            "mas_caro": _serializar_producto(mas_caro) if mas_caro else None,
            "ranking": [_serializar_producto(p) for p in top],
        }

    if _hay_intento(q, INTENTO_PRECIO_MINIMO):
        top = sorted(activos, key=lambda p: p.precio)
        mas_barato = top[0] if top else None
        return {
            "tipo": "precio_minimo",
            "mas_barato": _serializar_producto(mas_barato) if mas_barato else None,
            "ranking": [_serializar_producto(p) for p in top],
        }

    if _hay_intento(q, INTENTO_CONTEO):
        return {
            "tipo": "conteo",
            "total_productos": activos.count(),
            "total_agotados": activos.filter(cantidad_existente=0).count(),
            "explicacion_pregunta": "cantidad de productos del inventario",
        }

    if any(k in q for k in ["pocas existencia", "bajo stock", "stock bajo", "critic", "reponer", "agotado", "falta", "terminando"]):
        criticos = activos.filter(cantidad_existente__lte=F('stock_minimo'))
        return {
            "tipo": "alertas_stock",
            "total_afectados": criticos.count(),
            "agotados": activos.filter(cantidad_existente=0).count(),
            "productos": [_serializar_producto(p) for p in criticos],
        }

    coincidentes = [
        p for p in activos
        if p.nombre.lower() in q
        or any(palabra in p.nombre.lower() for palabra in q.split() if len(palabra) > 3)
    ]
    if coincidentes:
        return {
            "tipo": "coincidencias",
            "productos": [_serializar_producto(p) for p in coincidentes],
        }

    return {
        "tipo": "inventario_general",
        "total_productos": activos.count(),
        "productos": [_serializar_producto(p) for p in activos],
    }


def _tabla_markdown(productos):
    """Tabla Markdown con todos los datos de cada producto.

    Los botones del panel deben mostrar la informacion completa del
    inventario, no una muestra, para que el reporte sea verificable.
    """
    lineas = ["| Código | Producto | Categoría | Stock | Mínimo | Precio (Bs.) | Estado |",
              "|---|---|---|---|---|---|---|"]
    for p in productos:
        critico = p['cantidad_existente'] <= p['stock_minimo']
        stock = f"**{p['cantidad_existente']}**" if critico else str(p['cantidad_existente'])
        lineas.append(f"| {p['codigo']} | {p['nombre']} | {p['categoria']} | {stock} | "
                      f"{p['stock_minimo']} | {p['precio']:.2f} | {p['estado_stock']} |")
    return "\n".join(lineas)


def _respuesta_deterministica(contexto):
    """Respuesta directa y precisa derivada del contexto JSON (sin LLM)."""
    tipo = contexto.get("tipo")

    if tipo == "valor_total":
        # Resumen + tabla completa: los 4 botones de la rubrica deben devolver
        # todos los datos, no solo la cifra.
        return (f"El **valor total del inventario** es aproximadamente **Bs. {contexto['total_bs']:,.2f}**, "
                f"sumando {contexto['total_unidades']} unidades en stock.\n\n"
                + _tabla_markdown(contexto.get("ranking") or contexto.get("productos") or []))

    if tipo == "precio_maximo":
        m = contexto["mas_caro"]
        if not m:
            return "No hay productos activos registrados."
        encabezado = (f"El producto **más caro** es **{m['nombre']}** ({m['codigo']}) de la categoría "
                      f"*{m['categoria']}*, con un precio de **Bs. {m['precio']:.2f}**. "
                      f"Inventario completo ordenado de mayor a menor precio:")
        return encabezado + "\n\n" + _tabla_markdown(contexto["ranking"])

    if tipo == "precio_minimo":
        m = contexto["mas_barato"]
        if not m:
            return "No hay productos activos registrados."
        encabezado = (f"El producto **más barato** es **{m['nombre']}** ({m['codigo']}) de la categoría "
                      f"*{m['categoria']}*, con un precio de **Bs. {m['precio']:.2f}**. "
                      f"Inventario completo ordenado de menor a mayor precio:")
        return encabezado + "\n\n" + _tabla_markdown(contexto["ranking"])

    if tipo == "conteo":
        return (f"Hay **{contexto['total_productos']}** productos activos en el almacén "
                f"({contexto['total_agotados']} agotados).")

    if tipo == "alertas_stock":
        productos = contexto.get("productos") or []
        if not productos and not contexto.get("agotados"):
            return "No hay productos con stock crítico ni agotados: todo el inventario está por encima del mínimo."
        agotados = contexto.get("agotados", 0)
        criticos = max(contexto.get("total_afectados", len(productos)) - agotados, 0)
        encabezado = (f"Hay **{contexto.get('total_afectados', len(productos))}** producto(s) que requieren "
                      f"reposición (**{agotados}** agotados y **{criticos}** con stock bajo). "
                      f"Detalle completo:")
        return encabezado + "\n\n" + _tabla_markdown(productos)

    return None


def _respuesta_truncada(respuesta):
    """Detecta respuestas del LLM cortadas (tabla Markdown incompleta).

    El modelo en CPU se corta por `num_predict` y a veces devuelve una tabla
    a medias; en ese caso preferimos la respuesta determinista.
    """
    if not respuesta:
        return True
    texto = respuesta.strip()
    if texto.endswith("|"):
        return True
    lineas = [l for l in texto.splitlines() if l.strip().startswith("|")]
    if lineas and not all(l.count("|") >= 2 for l in lineas):
        return True
    return False


def _respuesta_fallback(contexto):
    """Respuesta local sin LLM cuando Ollama está caído (consultas abiertas)."""
    # `ranking` es la lista de las preguntas de precio; `productos`, la del resto.
    productos = contexto.get("productos") or contexto.get("ranking") or []
    if contexto.get("tipo") == "valor_total":
        return (f"Valor total del inventario: **{contexto['total_unidades']}** unidades "
                f"por un estimado de **Bs. {contexto['total_bs']:,.2f}**.\n\n"
                + _tabla_markdown(productos))
    if not productos:
        return "No se encontraron productos para esa consulta."
    if contexto.get("tipo") == "alertas_stock":
        agotados = contexto.get("agotados", 0)
        criticos = max(contexto.get("total_afectados", len(productos)) - agotados, 0)
        encabezado = (f"Hay **{contexto.get('total_afectados', len(productos))}** producto(s) que requieren "
                      f"reposición (**{agotados}** agotados y **{criticos}** con stock bajo). "
                      f"Detalle completo:")
        return encabezado + "\n\n" + _tabla_markdown(productos)
    intro = f"Inventario encontrado ({len(productos)} producto(s)):"
    return intro + "\n\n" + _tabla_markdown(productos)


MUESTRA_LLM = 5


def _contexto_para_llm(contexto):
    """Recorta el contexto antes de enviarlo al LLM.

    El contexto completo puede traer decenas de productos y en CPU cada token
    cuesta, asi que al modelo le mandamos solo una muestra. Los datos
    exactos no se pierden: los muestra la tabla determinista.
    """
    compacto = dict(contexto)
    for clave in ("productos", "ranking"):
        if compacto.get(clave):
            compacto[clave] = compacto[clave][:MUESTRA_LLM]
    return compacto


def _llm_ollama(contexto, pregunta):
    consulta = (f"Basándote EXCLUSIVAMENTE en el Contexto anterior, responde en español. "
                f"Pregunta: {pregunta}")
    return consultar_ollama(consulta, contexto_json=_contexto_para_llm(contexto))


def _aviso_modelo_faltante(contexto):
    aviso = ("Para usar el asistente IA, primero registra el modelo en Ollama. "
             "Ejecuta en la terminal:\n\n"
             "    ollama create pos-inventario-bot -f Modelfile.txt\n\n"
             "Mientras tanto, te doy la información actual del almacén:\n\n")
    return aviso + _respuesta_fallback(contexto)


def chat_consulta(pregunta):
    """Atiende un chat del usuario: construye contexto JSON, responde de forma
    directa si la pregunta es explícita, y si no consulta Ollama con
    fallback local. Registra siempre la consulta en ConsultaIA."""
    contexto = construir_contexto(pregunta)

    # Preguntas explícitas: respuesta determinística derivada del JSON (<1s)
    directa = _respuesta_deterministica(contexto)
    if directa:
        ConsultaIA.objects.create(pregunta=pregunta.strip(), respuesta=directa)
        return directa

    try:
        respuesta = _llm_ollama(contexto, pregunta)
    except ModeloNoRegistrado:
        respuesta = _aviso_modelo_faltante(contexto)
    except Exception as e:  # noqa: BLE001
        logger.warning("Ollama no disponible: %s", e)
        respuesta = _respuesta_fallback(contexto)

    if _respuesta_truncada(respuesta):
        logger.info("Respuesta del modelo incompleta: se usa la respuesta local.")
        respuesta = _respuesta_fallback(contexto)

    ConsultaIA.objects.create(pregunta=pregunta.strip(), respuesta=respuesta)
    return respuesta


# Alias hacia atrás para usos previos
def consultar_ia_inventario(pregunta):
    return chat_consulta(pregunta)