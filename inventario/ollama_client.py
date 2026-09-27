import json
import logging

import httpx
from django.conf import settings
from django.db.models import F

from .models import Producto

logger = logging.getLogger(__name__)

# Configuración centralizada en settings.py (sobrescribible con .env):
#   OLLAMA_API_URL, OLLAMA_MODELO, OLLAMA_TIMEOUT.
# Nombre exacto del modelo registrado con: ollama create pos-inventario-bot -f Modelfile.txt
MODELO = getattr(settings, "OLLAMA_MODELO", "pos-inventario-bot")
OLLAMA_API_URL = getattr(settings, "OLLAMA_API_URL", "http://localhost:11434/api/generate")
TIMEOUT_SEGUNDOS = getattr(settings, "OLLAMA_TIMEOUT", 120)


class ModeloNoRegistrado(Exception):
    """Se lanza cuando Ollama responde 404: el modelo aún no fue creado."""
    pass


# La instruccion SYSTEM NO se envia desde Python: ya esta incrustada en el
# modelo via Modelfile.txt (unica fuente de verdad del comportamiento).


def _estado_stock(p):
    if p.cantidad_existente == 0:
        return "Agotado"
    if p.cantidad_existente <= p.stock_minimo:
        return "Bajo"
    return "Optimo"


def build_context(limite=10):
    """Consulta los modelos reales (Producto) y prepara el contexto JSON
    compacto que se entregara a Ollama junto con la pregunta del usuario."""
    activos = Producto.objects.filter(estado=True)
    productos = [
        {
            "codigo": p.codigo,
            "nombre": p.nombre,
            "categoria": p.categoria,
            "precio_bs": float(p.precio),
            "stock": p.cantidad_existente,
            "stock_minimo": p.stock_minimo,
            "estado": _estado_stock(p),
        }
        for p in activos.order_by("categoria", "nombre")[:limite]
    ]
    return {
        "total_productos_activos": activos.count(),
        "unidades_en_stock": sum(p.cantidad_existente for p in activos),
        "valor_inventario_bs": round(float(sum(p.cantidad_existente * p.precio for p in activos)), 2),
        "productos_con_stock_critico": activos.filter(
            cantidad_existente__lte=F('stock_minimo'), cantidad_existente__gt=0
        ).count(),
        "productos_agotados": activos.filter(cantidad_existente=0).count(),
        "muestra_productos": productos,
    }


def consultar_ollama(pregunta, contexto_json=None, options=None):
    """Patrón Facade: expone una única función simple ante la API REST de Ollama.

    Encapsula la construcción del payload, el timeout, la serialización del
    contexto, el manejo de errores (HTTP 404 -> ModeloNoRegistrado, resto -> None)
    y el fallback silencioso cuando el servidor local está caído.
    """
    if contexto_json is None:
        contexto_json = build_context()

    payload = {
        "model": MODELO,
        "prompt": (
            "Contexto del sistema (inventario y ventas):\n"
            f"{json.dumps(contexto_json, ensure_ascii=False, separators=(',', ':'))}\n\n"
            f"Pregunta del usuario: {pregunta}"
        ),
        "stream": False,
        "options": options or {
            "temperature": 0.1,
            "top_k": 10,
            "top_p": 0.9,
            "num_predict": 100,
            "num_ctx": 1024,
        },
    }

    try:
        with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as client:
            respuesta = client.post(OLLAMA_API_URL, json=payload)
            respuesta.raise_for_status()
            return respuesta.json().get("response", "").strip()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Modelo '%s' aún no registrado en Ollama.", MODELO)
            raise ModeloNoRegistrado(MODELO) from e
        logger.warning("Ollama respondió %s: %s", e.response.status_code, e)
        return None
    except Exception as e:  # noqa: BLE001
        logger.warning("No se pudo consultar a Ollama (%s): %s", MODELO, e)
        return None