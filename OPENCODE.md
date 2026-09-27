# OPENCODE.md

Guia de referencia para asistentes de IA (OpenCode, Claude, Copilot) que trabajen en este
repositorio. Describe el stack, los comandos, las convenciones y las reglas que no se deben
romper.

---

## 1. Que es este proyecto

**Pingux POS**: sistema web de inventario y ventas desarrollado en Django 5.2, con un
asistente de IA local sobre Ollama. Entregable final de la asignatura Programacion IV.

El backend arma el contexto del inventario en JSON y lo envia a un modelo local; el modelo
solo responde con los datos suministrados. Si Ollama falla, el sistema responde con datos
de SQLite.

---

## 2. Stack y prohibiciones

| Elemento | Valor |
|---|---|
| Python | 3.11 |
| Framework | Django 5.2.17 |
| IA | Ollama + `qwen2.5:1.5b` (modelo `pos-inventario-bot`) |
| Cliente HTTP | `httpx` (con timeout) |
| Base de datos | SQLite (`db.sqlite3`) |
| Entorno | `venv/` en la raiz |
| Frontend | Plantilla unica, JS vanilla, Bootstrap Icons, `marked.js` via CDN |

**Prohibido**:

- Anyadir dependencias sin actualizar `requirements.txt`.
- Usar la API de Ollama con el SDK `ollama` (el proyecto usa `httpx` a proposito).
- Consultar a Ollama desde una vista. Las consultas de datos viven en `ia.py` y
  `reportes.py`; las vistas solo coordinan HTTP.
- Enviar al modelo la tabla Markdown completa de un reporte (solo conteos).
- Dejar que el modelo reemplace una respuesta calculada con datos.
- Escribir SQL concatenado a mano. Usar el ORM de Django.
- Editar o borrar `db.sqlite3` desde codigo fuera de las vistas y migraciones.

---

## 3. Comandos

```bash
# Entorno
source venv/bin/activate

# Ejecutar
python manage.py runserver

# Validar y probar
python manage.py check
python manage.py test
python manage.py test inventario.tests.CrudApiTests

# Migraciones (SIEMPRE despues de tocar models.py)
python manage.py makemigrations
python manage.py migrate
python manage.py makemigrations --check --dry-run   # debe decir "No changes detected"

# Modelo de IA (solo si se modifico Modelfile.txt)
ollama create pos-inventario-bot -f Modelfile.txt

# Regenerar el PDF del informe
python exportar_pdf.py
```

Estado esperado: `53 tests ... OK` y `System check identified no issues`.

---

## 4. Mapa del codigo

| Archivo | Responsabilidad | No debe contener |
|---|---|---|
| `config/settings.py` | Env, seguridad, variables de Ollama | Logica de negocio |
| `config/urls.py` | Rutas con `name=` para `reverse()` | Vistas inline |
| `inventario/models.py` | `Producto`, `Categoria`, `ConsultaIA` y validadores | Consultas a otros modelos |
| `inventario/forms.py` | `ProductoForm`, `CategoriaForm` | Acceso a `request` |
| `inventario/views.py` | HTTP, validacion de metodo, JSON | Consultas complexas a datos |
| `inventario/ia.py` | Contexto JSON, intents, fallback | Llamadas directas a Ollama |
| `inventario/ollama_client.py` | Cliente HTTP, errores | Contexto de negocio |
| `inventario/reportes.py` | Los 8 reportes (Strategy) | Dependencia de Django |
| `inventario/tests.py` | 53 pruebas | Datos de produccion |

Flujo de una consulta del chat:

```
navegador -> POST /api/chat/ -> views.chat_ia -> ia.chat_consulta
   -> construir_contexto()  (SQLite, productos activos)
   -> intent determinista?  -> respuesta calculada
   -> si no: consultar_ollama() -> modelo
   -> error/truncado? -> _respuesta_fallback()
   -> ConsultaIA.objects.create(...) -> JSON al navegador
```

---

## 5. Convenciones

- **Nombres**: `snake_case` en Python, `nombres_latinos` en espanol para variables de
  negocio (`cantidad_existente`, `stock_minimo`), `camelCase` en JavaScript.
- **Rutas**: siempre con `name=` para poder usar `{% url %}` y `reverse()`.
- **Endpoints**: validan el metodo HTTP (`405`), responden JSON, usan `get_object_or_404`.
- **JS**: funciones `async` con `try / catch / finally`, siempre con feedback visible
  (spinner, toast o estado de carga). Nada de `fetch` sin manejo de error.
- **Plantilla**: el panel no debe hacer scroll. Lo secundario va en modales; la tabla y el
  chat tienen scroll interno (`flex: 1` + `min-height: 0`).
- **Modelos**: todo cambio en `models.py` exige `makemigrations` + `migrate`.
- **Tests**: toda funcion o vista nueva necesita al menos un test.

---

## 6. Reglas de la interfaz

1. La pantalla principal tiene solo dos paneles: catalogo (izquierda) y chatbot (derecha).
2. Reportes, categorias e historial se abren en modales desde la barra superior.
3. Los 4 botones de consulta rapida de la rubrica viven en el chat y pintan sus tablas:
   `Stock critico`, `Producto mas caro`, `Valor total`, `Reporte: agotados`.
4. El formulario de producto usa un combo (`datalist`) con el catalogo de categorias.
5. Nada de scroll en la pagina principal en tamano de escritorio.
6. Toda accion debe dar feedback inmediato (las consultas con Ollama pueden tardar ~20 s).

---

## 7. Restricciones de la IA

En `Modelfile.txt` (`SYSTEM`):

- Responder **solo** con el inventario del contexto JSON recibido.
- No inventar productos, precios ni stock.
- Rechazar temas ajenos al POS con la frase exacta definida.
- Responder en espanol, breve, sin relleno.
- `temperature 0.1` para reducir alucinaciones.

Si se cambia el prompt, hay que recrear el modelo con
`ollama create pos-inventario-bot -f Modelfile.txt` o los cambios no tendran efecto.

---

## 8. Reglas de negocio

- Solo los productos con `estado=True` cuentan en metricas, reportes y contexto para la IA.
- `agotado` es `cantidad_existente == 0`.
- `pocas_existencias` es `0 < cantidad_existente <= stock_minimo`.
- El ajuste rapido de stock nunca baja de cero.
- El borrado por defecto es **logico** (`estado=False`); el fisico es optimo (`modo=fisico`).
- Una categoria en uso no se puede borrar; se avisa cuantos productos la usan.
- Al guardar un producto, su categoria se registra en el catalogo automaticamente.

---

## 9. Documentos que hay que mantener al dia

| Archivo | Cuando se actualiza |
|---|---|
| `README.md` | Cada endpoint, patron o comando nuevo |
| `DOCUMENTACION.md` | Cambios de arquitectura, validaciones o pruebas |
| `informe.md` / `informe.pdf` | Cambios visibles del entregable (debe quedar **sin tildes ni enies**) |
| `requirements.txt` | Cada dependencia nueva |
| `.env.example` | Cada variable de entorno nueva |
| `OPENCODE.md` (este) | Cambios de convenciones o prohibiciones |

`informe.md` **no puede llevar tildes ni enies** (lo exige el docente). El comando
`python exportar_pdf.py` verifica esa regla y genera el PDF.

---

## 10. Errores frecuentes de un asistente

| Error tipico | Consecuencia | Como evitarlo |
|---|---|---|
| Editar `models.py` sin migrar | La app revienta al arrancar | `makemigrations` + `migrate` siempre |
| Anadir un reporte sin registrarlo en `REPORTES` | `KeyError` en tiempo de ejecucion | Registrar en el diccionario |
| Filtrar solo por precio sin `estado=True` | El reporte incluye productos desactivados | Filtrar por `estado=True` en los 8 |
| `Sum()` sin filtro en un reporte | Cifras que no cuadran con la tabla | Usar siempre el mismo queryset |
| Dejar el `.innerHTML` del reporte en el chat | El reporte se mezcla con la conversacion | Renderizar en `#reportOutput` |
| Quitar un boton de la rubrica | Se pierde puntaje | Los 4 botones de consulta rapida son obligatorios |
| Anadir scroll a la pantalla principal | Se pierde eficiencia de uso | Modales y scroll interno |
| Subir texto del `SYSTEM` desde Python | Se duplica la fuente de verdad | La instruction vive solo en el `Modelfile` |
