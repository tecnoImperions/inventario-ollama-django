# OPENCODE.md — Uso de OpenCode en el proyecto

Este archivo es la evidencia de cómo se construyó **Pingux POS** con OpenCode: las
sesiones de trabajo, los prompts enviados, y qué cambió en el proyecto por cada uno.

> Las convenciones técnicas están en `DOCUMENTACION.md` y la guía de instalación en
> `README.md`. Aquí solo va el registro de las sesiones.

---

## 1. Qué es OpenCode y cómo se usó

OpenCode es un asistente de codificación con IA que se ejecuta **en la terminal**. Se usó
como compañero de desarrollo: se describía el problema en lenguaje natural, proponía el
código, y luego se verificaba ejecutando el proyecto.

**Nada se dio por bueno sin probarlo.** Cada bloque generado se validó con:

| Verificación | Comando |
|---|---|
| La app no tiene errores | `python manage.py check` |
| Las 53 pruebas pasan | `python manage.py test` |
| Las migraciones están al día | `python manage.py makemigrations --check --dry-run` |
| Los endpoints responden | `curl` contra el servidor |
| La instalación desde cero funciona | Instalar en una copia limpia y arrancar |

---

## 2. Resumen de sesiones

| # | Sesión | Prompt enviado | Resultado |
|---|---|---|---|
| 1 | Validaciones | "Estructura `clean_codigo` y `clean_precio` sin códigos duplicados ni valores negativos" | `ProductoForm` con unicidad case-insensitive |
| 2 | Patrón Strategy | "Diccionario de estrategias para 8 reportes sin if-else encadenados" | `REPORTES` + `generar_reporte(tipo)` |
| 3 | Cliente Ollama | "try-except con httpx que capture el 404 y los timeouts, con fallback a SQLite" | `consultar_ollama()` y excepción `ModeloNoRegistrado` |
| 4 | Interfaz | "La pantalla principal no debe hacer scroll; tabla y chat con scroll interno" | Layout con `flex: 1` + `min-height: 0`, y modales |
| 5 | Categorías | "Agrega un catálogo de categorías sin reescribir los reportes ya validados" | Modelo `Categoria`, migración `0004`, 3 endpoints |
| 6 | Combo de categorías | "Que aparezca un combo para que el usuario no invente nombres nuevos" | `<select>` en vez de campo de texto libre |
| 7 | Repositorio | "Si alguien entra a la repo no entendería qué hacer; revisa qué está versionado" | De 9.197 a 34 archivos, con `.gitignore` |
| 8 | Documentación | "El README debe ser una guía paso a paso, no un instalador mágico" | README de 9 pasos, con Ollama obligatorio |
| 9 | Auditoría | "¿Cumplimos con todo lo que pide la rúbrica?" | `pip freeze`, referencias y `.zip` de entrega |

---

## 3. Las sesiones con código

### Sesión 1 — Validación de código único

El prompt pedía evitar duplicados distinguiendo mayúsculas de minúsculas, sin romper la
edición. OpenCode propuso separar la exclusividad en su propio `clean_*` y **excluir la
instancia actual**, que era el detalle que faltaba:

```python
def clean_codigo(self):
    codigo = self.cleaned_data["codigo"].strip()
    qs = Producto.objects.filter(codigo__iexact=codigo)
    if self.instance.pk:
        qs = qs.exclude(pk=self.instance.pk)   # <- permite editar sin cambiar el código
    if qs.exists():
        raise forms.ValidationError("Ya existe un producto con ese código.")
    return codigo
```

**Impacto:** sin ese `exclude`, guardar una edición sin tocar el código fallaba con
"código duplicado". Se agregó una prueba que edita un producto y confirma que no se bloquea.

### Sesión 2 — Patrón Strategy para los reportes

El prompt pedía evitar condicionales encadenados. La solución fue un diccionario que
resuelve el algoritmo en tiempo de ejecución:

```python
REPORTES = {
    "mas_caro": reporte_producto_mas_caro,
    "valor_total": reporte_valor_total,
    # ... 8 en total
}

def generar_reporte(tipo, **kwargs):
    return REPORTES[tipo](**kwargs)
```

**Impacto:** agregar un reporte nuevo es una función más y una línea. No se toca ningún
`if`. Es el patrón Strategy del punto 3 del informe.

### Sesión 3 — Manejo de errores de Ollama

El prompt pedía distinguir el 404 del resto de fallos. OpenCode los separó porque requieren
mensajes distintos al usuario:

```python
except httpx.HTTPStatusError as e:
    if e.response.status_code == 404:
        raise ModeloNoRegistrado(MODELO) from e
    return None
```

**Impacto:** se cumplen los requisitos 2.4 y 2.5. Si Ollama está apagado, el chat responde
con datos de SQLite; si el modelo no existe, muestra el comando `ollama create` exacto. La
aplicación nunca se cae.

### Sesión 6 — Combo de categorías

El prompt pidió que el formulario mostrara las categorías existentes para que el usuario no
inventara nombres. La solución fue cambiar el campo de texto libre por un `<select>` que
solo lista el catálogo, con un enlace para crear una nueva desde el modal de Categorías.

**Impacto:** las categorías quedan bajo control y la entrada de datos es más consistente.

### Sesión 7 — Limpieza del repositorio

El repositorio tenía **9.197 archivos** versionados, casi todos `venv/` y `__pycache__`.
Se creó un `.gitignore` y se desindexó lo que no debía estar.

**Impacto:** el repositorio pasó a **34 archivos**. Se conservaron a propósito `db.sqlite3`
(para que el sistema abra con datos de ejemplo) e `informe.pdf` (es un entregable),
dejándolo anotado en el propio `.gitignore`.

### Sesión 9 — Auditoría contra la rúbrica

Se recorre el enunciado completo de la actividad y se detectan cuatro incumplimientos:

| Incumplimiento | Corrección |
|---|---|
| `requirements.txt` escrito a mano (5 paquetes) | Regenerado con `pip freeze` (48 paquetes) |
| Sin documentar la descarga del modelo (punto 2.1) | Sección con `ollama pull` y salida de `ollama list` |
| Sin citas y referencias | Sección 6 del informe con enlaces a Django, Ollama y OpenCode |
| No existía el `.zip` de entrega | Creado con la estructura `proyecto/`, `informe.md`, `informe.pdf` |

---

## 4. Impacto en el desarrollo

| Aspecto | Con OpenCode | Sin OpenCode |
|---|---|---|
| Validaciones | Una sesión, con prueba que lo cubre | Iterar errores de unicidad a mano |
| 8 reportes | Diccionario extensible | Ocho `if/elif` que crecerían sin control |
| Cliente Ollama | Excepción propia y fallback a SQLite | Depurar errores HTTP a ciegas |
| Interfaz | Scroll interno y modales resueltos | Medir alturas y `overflow` a mano |
| Repositorio | De 9.197 a 34 archivos | Subir `venv/` a GitHub por error |
| Verificación | 53 pruebas en cada cambio | "Funciona en mi máquina" |

**Lo más útil no fue escribir código, sino verificarlo.** Varios bloques no salieron
correctos a la primera. El ejemplo más claro: el reporte `valor_total` sumaba unidades de
productos **desactivados**. El error no se vio leyendo el código, sino al comparar el total
con la tabla, y se corrigió agregando una prueba que lo detecta.

Ese ciclo —generar, ejecutar, comparar, probar— es lo que mantuvo el proyecto coherente
durante todo el desarrollo.
