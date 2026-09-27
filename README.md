# Pingux POS — Sistema Web de Productos con IA Local (Ollama)

Entregable Final — Programación 4.
Sistema web Django con **CRUD completo** de productos, ajuste rápido de stock,
reportes predefinidos y un **asistente de inteligencia artificial local (Ollama)**.

---

## 1. Servidor (host)

La aplicación queda publicada en:

```
http://172.25.4.222:8000
```

> El host `172.25.4.222` ya está incluido en `ALLOWED_HOSTS`.

---

## 2. Requisitos

- Python 3.10 o superior.
- [Ollama](https://ollama.com) instalado y en ejecución.

### Crear el modelo del asistente (pos-inventario-bot)

El modelo base `qwen2.5:1.5b` ya está descargado. Solo registra el asistente
desde `Modelfile.txt` (el SYSTEM estricto del POS se incrusta ahí):

```bash
ollama create pos-inventario-bot -f Modelfile.txt
```

---

## 3. Instalación

```bash
# 1) Clonar el repositorio y entrar
git clone <url-del-repo> inventario_ia
cd inventario_ia

# 2) Crear y activar el entorno virtual
python -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows

# 3) Configurar variables de entorno (opcional, hay valores por defecto)
cp .env.example .env            # y editar si hace falta

# 4) Instalar dependencias
pip install -r requirements.txt

# 5) Aplicar migraciones (base de datos + tablas nuevas)
python manage.py makemigrations inventario
python manage.py migrate

# 6) Opcional: cargar datos de ejemplo
python manage.py shell -c "from inventario.models import Producto; \
Producto.objects.count() or print('Crea productos desde el panel con Nuevo Producto')"
```

La configuración de Ollama se lee desde el entorno / `.env`
(`OLLAMA_API_URL`, `OLLAMA_MODELO`, `OLLAMA_TIMEOUT`) con valores por defecto
seguros en `config/settings.py`.

---

## 4. Ejecución (publicado para el host)

```bash
# Servir en todas las interfaces de red, puerto 8000
python manage.py runserver 0.0.0.0:8000
```

Abrir desde cualquier equipo de la red: **http://172.25.4.222:8000**

---

## 5. Endpoints (nomenclatura snake_case)

| Método | Ruta | Función |
|---|---|---|
| GET | `/` | Panel principal (métricas, tabla, chatbot)
| GET | `/?mostrar=inactivos` | Panel incluyendo productos desactivados |
| POST | `/api/chat/` | Chat con IA (parámetro `pregunta`) |
| GET | `/api/reporte/?tipo=...` | Reportes predefinidos |
| POST | `/api/producto/guardar/` | Crear / actualizar producto (id presente = edición) |
| POST | `/api/producto/<pk>/eliminar/` | Borrado: `modo=logico` (defecto) o `fisico` |
| POST | `/api/producto/<pk>/ajustar_stock/` | Ajuste de stock (parámetro `operacion=sumar|restar`) |
| GET | `/api/categorias/` | Listar el catálogo con conteo de productos |
| POST | `/api/categoria/guardar/` | Crear (`nombre`) o renombrar (`id` + `nombre`) una categoría |
| POST | `/api/categoria/<pk>/eliminar/` | Eliminar categoría (solo si ningún producto la usa) |
| GET | `/api/historial/` | Historial de consultas a la IA |
| GET | `/admin/` | Administración de Django |

Reportes disponibles (`tipo`): `todos`, `mas_caro`, `mas_barato`,
`pocas_existencias`, `agotados`, `por_categoria` (usa `categoria=`),
`valor_total`, `mayor_cantidad`.

---

## 6. Arquitectura

- **`DOCUMENTACION.md`** — manual técnico completo (endpoints, validaciones, pruebas, problemas frecuentes).
- **`OPENCODE.md`** — convenciones y prohibiciones para asistentes de IA que trabajen en el repo.
- **`inventario/models.py`** — entidades `Producto`, `Categoria` y `ConsultaIA`
  (tablas `productos`, `categorias` y `consultas_ia`).
- **`inventario/forms.py`** — `ProductoForm` y `CategoriaForm` con validaciones de
  servidor: código único (case-insensitive) y números NO negativos.
- **`inventario/reportes.py`** — los 8 reportes predefinidos con explicación de Ollama.
- **`inventario/ia.py`** — construcción de contexto **JSON** + chat con `pos-inventario-bot`;
  si Ollama está caído responde con datos locales y registra todo en `ConsultaIA`.
- **`inventario/ollama_client.py`** — cliente REST (`/api/generate`) y
  `build_context()` que arma el contexto desde los modelos reales.
- **`Modelfile.txt`** — definición del modelo `pos-inventario-bot` (sistema estricto POS +
  temperatura baja para evitar alucinaciones).
- **`inventario/views.py`** — vistas CRUD, stock, categorías, chat, reportes e historial.
- **`inventario/tests.py`** — pruebas unitarias (53 casos) de modelos, formularios,
  CRUD, categorías, reportes, cliente Ollama y chat.
- **`inventario/templates/inventario/index.html`** — interfaz POS con Markdown (`marked.js`).

### Pantalla: sistema a la izquierda, chatbot a la derecha

El panel sigue la separación pedida en los requerimientos, y además está pensado para
que el usuario **no tenga que hacer scroll** en la pantalla principal:

- **Columna izquierda (sistema)**: métricas y catálogo de productos. La tabla tiene su
  propio scroll interno y el panel se estira hasta el alto de la ventana
  (`flex: 1` + `min-height: 0`), de modo que el contenido siempre entra en una pantalla.
- **Columna derecha (chatbot)**: únicamente conversación con la IA y sus accesos rápidos,
  también con scroll propio.
- **Barra superior**: botones `Reportes`, `Categorías` e `Historial`, que abren **modales**
  (el de reportes es ancho, `1040px`, para que quepan las tablas completas). Así el
  usuario trabaja sobre modales grandes en lugar de alargar la página.
- El formulario de producto usa un **combo** (`datalist`) con el catálogo: se puede
  elegir una categoría existente o escribir una nueva, que se registra sola al guardar.

### Categorías: por qué `Producto.categoria` sigue siendo texto

`Categoria` es un catálogo independiente para poder elegir, agregar y borrar categorías
sin reescribir los reportes ni los filtros ya validados. Al guardar un producto, la
categoría escrita se registra en el catálogo (`get_or_create`) y la migración `0004`
pobló el catálogo con las categorías que ya usaban los productos. Borrar una categoría
en uso se rechaza indicando cuántos productos la usan.

### Patrones de diseño aplicados

1. **Strategy** (`inventario/reportes.py`): cada tipo de reporte es un algoritmo
   intercambiable; el diccionario `REPORTES` + `generar_reporte(tipo)` selecciona la
   estrategia en tiempo de ejecución sin condicionales encadenados.
2. **Facade** (`inventario/ollama_client.py`): `consultar_ollama()` encapsula todo el
   detalle de la API REST de Ollama (payload, timeout, errores, manejo de 404 con la
   excepción propia `ModeloNoRegistrado` y fallback silencioso a `None`);
   el resto del sistema solo ve una función simple.

---

## 7. Funcionalidades del panel

- Búsqueda en vivo por código, nombre o categoría.
- Botones rápidos **+1 / −1** de stock por producto.
- Reportes predefinidos con análisis de IA.
- Chat con formato **Markdown** (tablas y negritas).
- Modal CRUD con validaciones: **sin números negativos** y **código único**.

---

## 8. Entregables y exportación del informe

| Archivo | Descripción |
|---|---|
| `informe.md` | Informe de la Actividad 5 (Programación IV), escrito sin tildes ni eñes. |
| `informe.pdf` | Versión PDF del informe (7 páginas, A4). |
| `exportar_pdf.py` | Script que convierte `informe.md` en `informe.pdf`. |

Para regenerar el PDF (desde la raíz del proyecto):

```bash
# Opción 1: script (Markdown -> HTML -> PDF con xhtml2pdf, sin dependencias del sistema)
venv/bin/python exportar_pdf.py

# Opción 2: con LibreOffice directamente (si prefieres no usar el script)
venv/bin/python -c "import markdown,pathlib; pathlib.Path('informe.html').write_text('<html><body>'+markdown.markdown(pathlib.Path('informe.md').read_text(encoding='utf-8'), extensions=['extra','tables','fenced_code'])+'</body></html>', encoding='utf-8')"
libreoffice --headless --convert-to pdf --outdir . informe.html
rm -f informe.html
```

El script detecta el motor disponible: usa **xhtml2pdf** y, si no está instalado,
recurre a **LibreOffice** (`soffice --headless --convert-to pdf`).

> `informe.md` está escrito **sin tildes ni eñes** de forma intencional (requisito
> de la rúbrica), por eso el nombre del docente aparece como "Lopez Leano" en el
> archivo. El PDF se genera con las mismas fuentes sin diacríticos.