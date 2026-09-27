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
            "explicacion_pregunta": "valor total del inventario",
        }

    if _hay_intento(q, INTENTO_PRECIO_MAXIMO):
        top = sorted(activos, key=lambda p: p.precio, reverse=True)
        mas_caro = top[0] if top else None
        return {
            "tipo": "precio_maximo",
            "mas_caro": _serializar_producto(mas_caro) if mas_caro else None,
            "ranking": [_serializar_producto(p) for p in top[:5]],
        }

    if _hay_intento(q, INTENTO_PRECIO_MINIMO):
        top = sorted(activos, key=lambda p: p.precio)
        mas_barato = top[0] if top else None
        return {
            "tipo": "precio_minimo",
            "mas_barato": _serializar_producto(mas_barato) if mas_barato else None,
            "ranking": [_serializar_producto(p) for p in top[:5]],
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
        lista = list(criticos[:5])
        return {
            "tipo": "alertas_stock",
            "total_afectados": criticos.count(),
            "agotados": activos.filter(cantidad_existente=0).count(),
            "productos": [_serializar_producto(p) for p in lista],
        }

    coincidentes = [
        p for p in activos
        if p.nombre.lower() in q
        or any(palabra in p.nombre.lower() for palabra in q.split() if len(palabra) > 3)
    ]
    if coincidentes:
        return {
            "tipo": "coincidencias",
            "productos": [_serializar_producto(p) for p in coincidentes[:5]],
        }

    return {
        "tipo": "inventario_general",
        "total_productos": activos.count(),
        "productos": [_serializar_producto(p) for p in activos[:5]],
    }


def _tabla_desde_json(productos):
    lineas = ["| Producto | Stock | Precio | Estado |",
              "|---|---|---|---|"]
    for p in productos:
        stock = f"**{p['cantidad_existente']}**" if p['cantidad_existente'] <= p['stock_minimo'] else str(p['cantidad_existente'])
        lineas.append(f"| {p['nombre']} | {stock} | Bs. {p['precio']:.2f} | {p['estado_stock']} |")
    return "\n".join(lineas)


def _respuesta_deterministica(contexto):
    """Respuesta directa y precisa derivada del contexto JSON (sin LLM)."""
    tipo = contexto.get("tipo")

    if tipo == "valor_total":
        return (f"El **valor total del inventario** es aproximadamente **Bs. {contexto['total_bs']:,.2f}**, "
                f"sumando {contexto['total_unidades']} unidades en stock.")

    if tipo == "precio_maximo":
        m = contexto["mas_caro"]
        if not m:
            return "No hay productos activos registrados."
        ranking = _tabla_desde_json(contexto["ranking"])
        return (f"El producto **más caro** es **{m['nombre']}** ({m['codigo']}) de la categoría "
                f"*{m['categoria']}*, con un precio de **Bs. {m['precio']:.2f}**.\n\nRanking de precios:\n{ranking}")

    if tipo == "precio_minimo":
        m = contexto["mas_barato"]
        if not m:
            return "No hay productos activos registrados."
        ranking = _tabla_desde_json(contexto["ranking"])
        return (f"El producto **más barato** es **{m['nombre']}** ({m['codigo']}) de la categoría "
                f"*{m['categoria']}*, con un precio de **Bs. {m['precio']:.2f}**.\n\nRanking de precios:\n{ranking}")

    if tipo == "conteo":
        return (f"Hay **{contexto['total_productos']}** productos activos en el almacén "
                f"({contexto['total_agotados']} agotados).")

    return None


def _respuesta_fallback(contexto):
    """Respuesta local sin LLM cuando Ollama está caído (consultas abiertas)."""
    productos = contexto.get("productos") or []
    if contexto.get("tipo") == "valor_total":
        return (f"Valor total del inventario: **{contexto['total_unidades']}** unidades "
                f"por un estimado de **Bs. {contexto['total_bs']:,.2f}**.")
    if not productos:
        return "No se encontraron productos para esa consulta."
    if contexto.get("tipo") == "alertas_stock":
        intro = f"Hay **{len(productos)}** producto(s) con stock bajo o agotado:"
    else:
        intro = f"Muestra de **{contexto.get('total_productos') or len(productos)}** producto(s):"
    return intro + "\n" + _tabla_desde_json(productos)


def _llm_ollama(contexto, pregunta):
    consulta = (f"Basándote EXCLUSIVAMENTE en el Contexto anterior, responde en español. "
                f"Pregunta: {pregunta}")
    return consultar_ollama(consulta, contexto_json=contexto)


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

    if not respuesta:
        respuesta = _respuesta_fallback(contexto)

    ConsultaIA.objects.create(pregunta=pregunta.strip(), respuesta=respuesta)
    return respuesta


# Alias hacia atrás para usos previos
def consultar_ia_inventario(pregunta):
    return chat_consulta(pregunta)