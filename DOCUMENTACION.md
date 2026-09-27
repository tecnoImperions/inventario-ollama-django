# DOCUMENTACION.md - Pingux POS

Documentacion tecnica oficial del proyecto **Pingux POS** (Entregable Final - Programacion IV).
Cubre la instalacion, la arquitectura, cada endpoint, los 8 reportes, la integracion con
Ollama, las validaciones, las pruebas y la resolucion de problemas.

---

## 1. Requisitos previos

| Requisito | Version | Para que sirve |
|---|---|---|
| Python | 3.11 o superior | Lenguaje del backend |
| Django | 5.2.17 | Framework web |
| Ollama | >= 0.5 | Servidor de IA local |
| Modelo base `qwen2.5:1.5b` | - | Base del asistente |

No se requiere conexion a internet en tiempo de ejecucion: la IA corre en local.

---

## 2. Instalacion paso a paso

```bash
# 1) Crear el entorno virtual
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) Configurar el entorno
cp .env.example .env              # Windows: copy .env.example .env

# 4) Aplicar migraciones
python manage.py migrate

# 5) Registrar el modelo de IA en Ollama
ollama pull qwen2.5:1.5b
ollama create pos-inventario-bot -f Modelfile.txt

# 6) Levantar el servidor
python manage.py runserver
```

Abrir `http://127.0.0.1:8000`.

Comprobar que todo esta bien:

```bash
python manage.py check      # => System check identified no issues
python manage.py test       # => Ran 53 tests ... OK
```

---

## 3. Estructura del proyecto

```
config/
  settings.py          Configuracion (env, seguridad, variables de Ollama)
  urls.py              Rutas del proyecto
inventario/
  models.py            Producto, Categoria, ConsultaIA
  forms.py             ProductoForm, CategoriaForm (validaciones)
  views.py             Vistas CRUD, stock, categorias, chat, reportes, historial
  ia.py                Contexto JSON, intents deterministas y fallback
  ollama_client.py     Cliente HTTP (patron Facade)
  reportes.py          Los 8 reportes (patron Strategy)
  admin.py             Registro en el admin de Django
  tests.py             53 pruebas automatizadas
  migrations/          0003 (validadores), 0004 (categoria + datos)
  templates/inventario/index.html   Interfaz POS
Modelfile.txt          Definicion del modelo pos-inventario-bot
requirements.txt       Dependencias
.env.example           Plantilla de variables de entorno
```

---

## 4. Variables de entorno (config/settings.py)

Todas son opcionales: el proyecto arranca con valores por defecto.

| Variable | Por defecto | Descripcion |
|---|---|---|
| `OLLAMA_API_URL` | `http://localhost:11434/api/generate` | Endpoint REST de Ollama |
| `OLLAMA_MODELO` | `pos-inventario-bot` | Nombre exacto del modelo registrado |
| `OLLAMA_TIMEOUT` | `120` | Timeout en segundos (el modelo corre en CPU) |
| `SECRET_KEY` | clave de desarrollo | Clave de Django |
| `DEBUG` | `True` | Modo depuracion |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1],172.25.4.222` | Hosts permitidos, separados por coma |

---

## 5. Modelos de datos

### 5.1 Producto (tabla `productos`)

| Campo | Tipo | Regla |
|---|---|---|
| `codigo` | CharField(50) | **Unico**, validacion case-insensitive en el formulario |
| `nombre` | CharField(150) | Obligatorio |
| `descripcion` | TextField | Opcional |
| `categoria` | CharField(100) | Obligatorio, se sincroniza con el catalogo `Categoria` |
| `precio` | DecimalField(10,2) | `MinValueValidator(0)`: no puede ser negativo |
| `cantidad_existente` | IntegerField | `MinValueValidator(0)`: no puede ser negativa |
| `stock_minimo` | IntegerField | `MinValueValidator(0)`: no puede ser negativo |
| `estado` | BooleanField | Borrado logico (`False` = inactivo) |
| `fecha_registro` | DateTimeField | `auto_now_add` |

### 5.2 Categoria (tabla `categorias`)

Catalogo independiente: `nombre` unico y `fecha_creacion`. Permite elegir de una lista,
agregar y borrar categorias. La migracion `0004` lo poblo con las categorias ya usadas.

### 5.3 ConsultaIA (tabla `consultas_ia`)

`pregunta`, `respuesta` y `fecha` (`auto_now_add`). **Toda** interaccion con la IA queda
registrada, incluidas las respondidas por el fallback local.

---

## 6. Endpoints

| Metodo | Ruta | Descripcion |
|---|---|---|
| GET | `/` | Panel principal (tabla, metricas, chatbot) |
| GET | `/?mostrar=inactivos` | Panel incluyendo productos desactivados |
| POST | `/api/chat/` | Chat con la IA. Parametro: `pregunta` |
| GET | `/api/reporte/?tipo=...&categoria=...` | Reportes predefinidos |
| POST | `/api/producto/guardar/` | Crear o actualizar. `id` presente = edicion |
| POST | `/api/producto/<pk>/eliminar/` | Borrado. `modo=logico` (defecto) o `fisico` |
| POST | `/api/producto/<pk>/ajustar_stock/` | Ajuste. `operacion=sumar` o `restar` |
| GET | `/api/categorias/` | Catalogo con conteo de productos |
| POST | `/api/categoria/guardar/` | Alta (`nombre`) o renombrado (`id` + `nombre`) |
| POST | `/api/categoria/<pk>/eliminar/` | Borrado; se rechaza si hay productos usando la categoria |
| GET | `/api/historial/` | Ultimas 20 consultas a la IA |
| GET | `/admin/` | Administracion de Django |

Todas las vistas de escritura validan el metodo HTTP y responden `405` si no corresponde.
Todas responden JSON.

---

## 7. Validaciones (RF-01 a RF-05)

`ProductoForm` centraliza las reglas y devuelve los errores campo por campo:

| Regla | Implementacion | Mensaje al usuario |
|---|---|---|
| Codigo unico | `clean_codigo()` con `codigo__iexact`, excluyendo la instancia en edicion | "Ya existe un producto con ese codigo unico." |
| Precio >= 0 | `MinValueValidator(0)` en el modelo | "El precio no puede ser negativo." |
| Cantidad >= 0 | `MinValueValidator(0)` en el modelo | "La cantidad no puede ser negativa." |
| Stock minimo >= 0 | `MinValueValidator(0)` en el modelo | "El stock minimo no puede ser negativo." |
| Nombre obligatorio | `CharField` sin `blank` | "Este campo es obligatorio." |
| Categoria no vacia | `CharField` sin `blank` | "Este campo es obligatorio." |

Control de existencias: el ajuste rapido `+1 / -1` no deja bajar de cero (devuelve `400`).
Borrado: el logico desactiva (`estado=False`) y el fisico elimina la fila; los productos
desactivados se pueden revisar con el boton "Ver inactivos" y reactivar desde el formulario.

---

## 8. Los 8 reportes (RF-06)

Implementados con el patron **Strategy** en `inventario/reportes.py`: cada reporte es una
funcion intercambiable y el diccionario `REPORTES` mas `generar_reporte(tipo)` eligen el
algoritmo en tiempo de ejecucion.

| `tipo` | Descripcion | Filtro SQL |
|---|---|---|
| `todos` | Lista todos los productos activos | `estado=True` |
| `mas_caro` | Top 5 mas caros | `estado=True`, orden `-precio` |
| `mas_barato` | Top 5 mas baratos | `estado=True`, orden `precio` |
| `pocas_existencias` | Stock bajo | `0 < cantidad_existente <= stock_minimo` |
| `agotados` | Sin existencias | `cantidad_existente=0` |
| `por_categoria` | Por categoria (parametro `categoria=`) | `categoria__iexact` |
| `valor_total` | Unidades y valor economico (Bs.) | `estado=True` |
| `mayor_cantidad` | Top 5 con mas unidades | `estado=True`, orden `-cantidad_existente` |

Cada reporte genera su tabla Markdown y pide a Ollama una explicacion de 1-2 frases. El
prompt recibe solo un resumen con conteos (nunca la tabla completa) y la respuesta se
descarta si vuelve con `|` o sin puntuacion final, para que el modelo no repita la tabla.

Los 4 botones de consulta rapida del panel son:

| Boton | Mecanismo | Destino en pantalla |
|---|---|---|
| Stock critico | `POST /api/chat/` | Tabla en el chat |
| Producto mas caro | `POST /api/chat/` | Tabla en el chat |
| Valor total | `POST /api/chat/` | Resumen en el chat |
| Reporte: agotados | `GET /api/reporte/?tipo=agotados` | Tabla en el chat |

Ademas, la barra superior tiene un modal **Reportes** con los 8 reportes, un modal
**Categorias** y un modal **Historial**. La pantalla principal no requiere scroll: la tabla
y el chat tienen scroll interno y el resto se abre en modales.

---

## 9. Integracion con Ollama (RF-07 a RF-10)

### 9.1 Cliente HTTP (patron Facade)

`inventario/ollama_client.py` encapsula toda la llamada REST en `consultar_ollama()`:

```python
with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as cliente:
    respuesta = cliente.post(OLLAMA_API_URL, json=payload, headers=headers)
    respuesta.raise_for_status()
    return respuesta.json().get("response", "").strip()
```

`httpx.Client(timeout=120)` aplica el timeout a connect, read, write y pool.

### 9.2 Contexto estructurado

`construir_contexto()` arma un diccionario y `json.dumps` lo serializa en el prompt. Nunca
se inventa informacion: todo sale de consultas a SQLite sobre productos activos.

### 9.3 Manejo de errores

| Situacion | Excepcion | Resultado |
|---|---|---|
| Ollama responde 404 | `ModeloNoRegistrado` | Mensaje con el comando `ollama create pos-inventario-bot -f Modelfile.txt` + datos locales |
| Timeout, servidor caido, red | `Exception` | `logger.warning` + fallback con datos de SQLite |
| Respuesta vacia o truncada | `_respuesta_truncada()` | Se reemplaza por la respuesta local |

Preguntas como "cual es el producto mas caro" se resuelven de forma deterministica con el
contexto JSON, sin llamar al modelo: la respuesta llega en menos de un segundo y es exacta.

### 9.4 Restriccion del modelo

`Modelfile.txt` fija el `SYSTEM` prompt: solo responde con el inventario suministrado, no
inventa productos, precios ni stock, rechaza temas ajenos al POS, responde en espanol y usa
tablas Markdown. `temperature 0.1` reduce la invencion.

```
ollama create pos-inventario-bot -f Modelfile.txt
```

### 9.5 Historial

Cada interaccion se guarda en `ConsultaIA` (pregunta, respuesta, fecha) y se expone en
`GET /api/historial/` para el modal de historial.

---

## 10. Patronos de diseno

1. **Strategy** (`inventario/reportes.py`): `REPORTES` + `generar_reporte(tipo)` permiten
   anadir un reporte nuevo escribiendo una funcion y registrandola en el diccionario.
2. **Facade** (`inventario/ollama_client.py`): `consultar_ollama()` oculta payload, timeout,
   serializacion y errores; el resto del sistema ve una sola funcion.
3. **Repository implicito**: las consultas a datos viven en `ia.py` y `reportes.py`, no en
   las vistas, que solo coordinan HTTP.

---

## 11. Pruebas

```bash
python manage.py test          # 53 pruebas
python manage.py test -v 2     # con detalle
```

Cobertura por area:

| Area | Que se verifica |
|---|---|
| Modelos | Validadores de no negativos, unicidad, `__str__` |
| Formularios | Codigo unico case-insensitive, edicion excluyendo la instancia, negativos |
| CRUD API | Alta, edicion, borrado logico y fisico, modo invalido, stock sin bajar de cero |
| Categorias | Alta, duplicados, renombrado en cascada, borrado en uso, combo del panel |
| Reportes | Los 8 tipos, `tipo` inexistente, rechazo de explicaciones con tabla |
| Ollama | 404 -> `ModeloNoRegistrado`, caida del servidor -> `None`, payload con contexto |
| Chat | Respuesta directa, fallback, respuesta truncada, historial, pregunta vacia |
| Interfaz | Los 4 botones de consulta rapida pintan tabla con todos los datos |

---

## 12. Seguridad aplicada

- Consultas parametrizadas por el ORM de Django (sin SQL concatenado).
- Escapado automatico de la plantilla (proteccion contra XSS).
- Toda entrada de formulario se valida en el servidor, no solo en JavaScript.
- `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` vienen del entorno; sin comodines por defecto.
- Vistas de escritura con control de metodo HTTP (`405`).

Limitacion conocida: las vistas usan `@csrf_exempt` porque el frontend es AJAX sin token
CSRF. En un despliegue publico habria que enviar el token en la cabecera `X-CSRFToken`.

---

## 13. Problemas frecuentes

| Sintoma | Causa | Solucion |
|---|---|---|
| "Modelo 'pos-inventario-bot' aun no registrado" | No se creo el modelo | `ollama create pos-inventario-bot -f Modelfile.txt` |
| "No se pudo consultar a Ollama: down" | El servidor Ollama esta apagado | `ollama serve` |
| Las respuestas tardan ~20 s | El modelo corre en CPU | Normal en CPU; es normal que el chat demore. Las consultas deterministicas son instantaneas |
| Respuestas en otro idioma o inventadas | El modelo base no es el personalizado | Recrear el modelo con el `Modelfile.txt` |
| `No such table: categorias` | Faltan migraciones | `python manage.py migrate` |
| El reporte no muestra nada | Se pulso y se esta generando | El panel muestra "Generando reporte..." mientras Ollama responde |
| Puerto 8000 ocupado | Otro proceso | `python manage.py runserver 8001` |
