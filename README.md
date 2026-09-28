# Pingux POS — Sistema de Inventario con IA Local

Proyecto final de **Programación IV**. Es un sistema de inventario (tipo punto de venta)
hecho con **Django**, que además incluye un **chatbot con IA local** (Ollama) que responde
preguntas sobre el inventario **sin inventarse datos**.

**¿Es tu primera vez aquí?** Ve directo a la
[Guía de instalación](#guía-de-instalación-paso-a-paso). Está escrita comando por comando,
sin saltarse nada. No hace falta saber Django: solo seguir los pasos en orden.

---

## Antes de empezar: qué necesitas tener listo

| Necesitas | Versión | ¿Obligatorio? | De dónde se descarga |
|---|---|---|---|
| **Python** | **3.11 o superior** | **Sí** | [python.org/downloads](https://www.python.org/downloads/) |
| **Ollama** (la IA) | cualquiera | **Sí** | [ollama.com/download](https://ollama.com/download) |
| **Un editor de código** (recomendado: VS Code) | cualquiera | No, pero ayuda mucho | [code.visualstudio.com](https://code.visualstudio.com/) |
| **Git** | cualquiera | No (hay alternativa sin Git) | [git-scm.com/downloads](https://git-scm.com/downloads) |
| **Internet** | — | Solo la primera vez | Para descargar Python, los paquetes y el modelo de IA |

> ### ⚠️ Ollama SÍ es obligatorio
>
> Este proyecto **no funciona sin Ollama**. La IA local es una parte obligatoria del
> entregable, no un extra: el chatbot es el corazón del sistema y sin Ollama no tiene
> modelo de lenguaje con el que responder.
>
> Por eso el [Paso 7](#paso-7--instalar-la-ia-con-ollama-obligatorio) no se puede saltar.
> Necesitas **las dos cosas**:
>
> | Qué | Por qué |
> |---|---|
> | El programa **Ollama** | Es el motor que ejecuta el modelo en tu computadora |
> | El modelo **`qwen2.5:1.5b`** | Son los ~986 MB del modelo de lenguaje que responde |
>
> Tarda unos minutos la **primera vez** (descarga los 986 MB). De ahí en adelante ya
> está en tu máquina y nunca más lo bajas otra vez.

### Cómo saber qué versión de Python tienes

Abre la terminal y ejecuta:

```bash
python --version      # Windows
python3 --version     # Linux y macOS
```

Debe decir algo como `Python 3.11.2` o mayor. Si dice `Python 3.9` o `3.10`, instala
una versión nueva antes de continuar.

> **Windows:** al instalar Python, marca la casilla **"Add Python to PATH"**. Si no lo
> haces, la terminal no reconocerá el comando `python`.

> **Linux:** si `python3 --version` no existe, instala primero
> `sudo apt install python3-venv` antes de continuar.

---

# Guía de instalación (paso a paso)

Hay 9 pasos. **Hazlos todos, en orden.** El paso 7 (la IA con Ollama) es
**obligatorio**. Al final tendrás el sistema corriendo con la IA funcionando.

Resumen rapidísimo, pero **no te saltes la explicación de cada paso**:

```bash
git clone https://github.com/tecnoImperions/inventario-ollama-django.git   # 1. descargar
cd inventario-ollama-django                                                 # 2. entrar
python3 -m venv venv                                                       # 3. crear entorno
source venv/bin/activate                                                    # 4. activar
pip install -r requirements.txt                                             # 5. dependencias
cp .env.example .env                                                        # 6. configuración
ollama pull qwen2.5:1.5b                                                    # 7. IA (OBLIGATORIO)
ollama create pos-inventario-bot -f Modelfile.txt                           # 7. IA (OBLIGATORIO)
python manage.py migrate                                                    # 8. base de datos
python manage.py runserver                                                  # 9. arrancar
```

---

## Paso 1 — Descargar el proyecto

### Opción A: con Git (recomendado)

Abre la terminal y ejecuta:

```bash
git clone https://github.com/tecnoImperions/inventario-ollama-django.git
```

Esto descarga el proyecto en una carpeta llamada `inventario-ollama-django`.

### Opción B: sin Git

1. Entra al repositorio en GitHub.
2. Click en el botón verde **Code** → **Download ZIP**.
3. Descomprime el ZIP donde quieras trabajar.

---

## Paso 2 — Entrar a la carpeta del proyecto

Este es **el paso más importante y el más olvidado**. Todos los comandos que vienen
después solo funcionan si estás *dentro* de la carpeta del proyecto.

Si usaste la **Opción A** ( clonaste con Git ):

```bash
cd inventario-ollama-django
```

Si usaste la **Opción B** (descargaste el ZIP ), el nombre puede ser distinto, por ejemplo
`inventario-ollama-django-main`:

```bash
cd inventario-ollama-django-main
```

> **Atajo:** también puedes abrir la carpeta en VS Code con `code .` y usar su terminal
> integrada, que ya se ubica en la carpeta correcta.

### ¿Cómo verifico que estoy en el lugar correcto?

MIRA qué archivos tienes:

```bash
ls          # Linux y macOS
dir         # Windows
```

Debes ver algo como esto:

```
config/    inventario/    venv?  manage.py   requirements.txt   informe.md   ...
```

Si ves **`manage.py`** y **`requirements.txt`**, estás en el sitio correcto y puedes
seguir. Si no los ves, es que todavía no entraste bien a la carpeta: vuelve a repetir el
`cd`.

---

## Paso 3 — Crear el entorno virtual

```bash
python3 -m venv venv          # Linux y macOS
python -m venv venv           # Windows
```

### ¿Qué es esto? ¿Por qué lo hago?

Un **entorno virtual** es como una "caja" donde se instalan las librerías del proyecto,
**separada** del Python de tu computadora.

- Sin esto, al instalar Django pip lo mezclaría con tus otros proyectos y podrías
  romper algo que ya tenías funcionando.
- Con esto, todo lo que instala este proyecto **se queda adentro de la carpeta `venv/`**
  y no toca nada más de tu máquina.
- El nombre `venv` es convención: puedes llamarle otro, pero `installar.sh` y la
  documentación asumen que se llama `venv`.

Este comando **crea la carpeta** `venv/`. Todavía no instala nada, solo prepara el espacio.

---

## Paso 4 — Activar el entorno virtual

Creaste la caja, ahora hay que "entrar" a ella. **Este paso lo tienes que repetir cada
vez que abras una terminal nueva.**

**Linux y macOS:**

```bash
source venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**

```powershell
.\venv\Scripts\Activate.ps1
```

### ¿Ya funcionó? Cómo saberlo

Tu terminal debe mostrar `venv` al principio de la línea, entre paréntesis:

```
(venv) usuario@equipo:~/inventario-ollama-django$
```

Si ves el `(venv)`, estás dentro del entorno virtual.

### ¿Y cómo salgo?

```bash
deactivate
```

Te va a desaparecer el `(venv)`. No lo necesitas para el trabajo normal, pero lo aclaro
por si te lo preguntan en clase.

---

## Paso 5 — Instalar las dependencias

```bash
pip install -r requirements.txt
```

### ¿Qué es `requirements.txt`?

Es simplemente la **lista de librerías que este proyecto necesita**, con su versión exacta:

| Paquete | Versión | Para qué sirve |
|---|---|---|
| `Django` | 5.2.17 | El framework web del proyecto |
| `ollama` | 0.6.2 | Comunicarse con la IA local |
| `python-dotenv` | 1.2.3 | Leer el archivo `.env` |
| `markdown` | 3.11 | Convertir el informe a PDF |
| `xhtml2pdf` | 0.2.21 | Generar `informe.pdf` |

El `-r` significa "lee este archivo de requirements". El comando `pip` recorre la lista
y descarga todo. **Tarda 1-2 minutos la primera vez**, es normal.

> Si te pide permisos o dice `externally-managed-environment`, activa el entorno virtual
> otra vez (Paso 4) y repite. Es el error más común.

---

## Paso 6 — Crear el archivo de configuración

```bash
cp .env.example .env          # Linux y macOS
copy .env.example .env        # Windows (Command Prompt)
```

### ¿Qué es esto?

El proyecto trae un archivo de ejemplo llamado **`.env.example`**. Este comando crea una
copia tuya llamada **`.env`**, que es donde se guardan las direcciones y contraseñas
personalizadas.

Por seguridad **el archivo `.env` nunca se sube a GitHub** (está en el `.gitignore`), así
que cada persona crea el suyo. El archivo `.env.example` sí se sube, y por eso puedes
copiarlo.

**No necesitas cambiar nada para trabajar en local.** Los valores por defecto ya están
bien. Si algún día cambias el puerto de Ollama o pones una `SECRET_KEY` real, lo editas
ahí. (Abre `.env` con un editor de texto si necesitas.)

---

## Paso 7 — Instalar la IA con Ollama (OBLIGATORIO)

> **Este paso no se puede saltar.** Es la parte de IA del proyecto y sin él el chatbot no
> tiene modelo de lenguaje con el que responder. Son 3 comandos y solo los haces **una
> vez** en tu computadora.

### 7.1 Instalar el programa Ollama

Descárgalo de [ollama.com/download](https://ollama.com/download) (Linux, macOS o
Windows) e instálalo. Después **cierra y vuelve a abrir la terminal** para que reconozca
el comando.

Verifica que quedó instalado:

```bash
ollama --version
```

Debe mostrarte un número de versión, por ejemplo `ollama version is 0.6.2`.

### 7.2 Descargar el modelo de lenguaje (los 986 MB)

```bash
ollama pull qwen2.5:1.5b
```

Este comando **descarga el modelo de lenguaje** que responderá las preguntas. Son
**986 MB** y puede tardar **5-10 minutos** la primera vez (depende de tu internet).

Es un modelo **pequeño y rápido**, elegido a propósito porque funciona bien **sin GPU
dedicada**: corre en un portátil normal.

> ¿Se cortó la descarga? No pasa nada: vuelve a ejecutar el mismo `ollama pull` y
> continúa desde donde se quedó.

### 7.3 Crear nuestro asistente con las reglas del POS

```bash
ollama create pos-inventario-bot -f Modelfile.txt
```

¿Qué hace esto? Toma el modelo que acabas de descargar (`qwen2.5:1.5b`) y le **pega las
instrucciones** de `Modelfile.txt`:

- que **nunca invente datos**,
- que solo responda con el inventario real que le pasa el backend,
- que sea concreto y no se invente campos.

El resultado es un modelo propio llamado **`pos-inventario-bot`**. Este es el que usa
el sistema.

### 7.4 Comprobar que quedó bien

```bash
ollama list
```

Debes ver **las dos líneas** (el nombre exacto de la primera termina en `:latest`, es
normal):

```
NAME                         ID              SIZE      MODIFIED
qwen2.5:1.5b                 65ec06548149    986 MB    10 days ago
pos-inventario-bot:latest    f6ba89e20845    986 MB    4 days ago
```

- La primera es el **modelo base** que descargaste: `qwen2.5:1.5b`, **986 MB**.
- La segunda es **nuestro asistente**, ya creado con las reglas del POS a partir del
  anterior. Por eso ocupa lo mismo: es el mismo modelo con instrucciones encima.

> Si solo aparece `qwen2.5:1.5b` y no `pos-inventario-bot`, se te pasó el paso 7.3.
> Vuelve a ejecutarlo.

> **¿Ollama no está corriendo?** Si el chat te avisa que no puede conectarse, es que
> Ollama no está iniciado. En Linux/macOS ejecuta `ollama serve` en otra terminal y
> déjalo ahí abierto. En Windows normalmente corre solo como servicio.
---

## Paso 8 — Preparar la base de datos

```bash
python manage.py migrate
```

### ¿Qué hace esto?

Crea las tablas donde se guardan tus datos: productos, categorías e historial del chat.

Si todo salió bien, vas a ver algo así:

```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, inventario, sessions
Running migrations:
  No migrations to apply.
```

> ### "No migrations to apply" — ¿está bien? 🤔
>
> **Sí, está perfecto.** Es la mejor respuesta posible.
>
> Significa que la base de datos `db.sqlite3` **ya viene en el repositorio con la
> estructura creada y con 52 productos de ejemplo**. Como ya está todo hecho, no hay nada
> pendiente por aplicar.
>
> Esto es a propósito: al abrir el sistema por primera vez ya vas a ver datos reales en
> la tabla y puedes probar sin tener que crear 50 productos a mano.
---

## Paso 9 — Arrancar el sistema

Este es el momento. Con el entorno virtual activado (Paso 4):

```bash
python manage.py runserver
```

Debes ver:

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

**Abre el navegador en:** <http://127.0.0.1:8000>

¡Listo! Ves el panel con el catálogo de productos a la izquierda y el chatbot a la derecha.

### Cómo detener el servidor

En la terminal donde lo estás corriendo, presiona **`Ctrl` + `C`**.

---

## ¿Windows? Todo en un solo bloque

Si prefieres pegar todo de una vez en el Command Prompt (después de tener clonado el
proyecto y **con Ollama instalado**), esto es lo mismo que los pasos 2 a 9:

```cmd
cd inventario-ollama-django
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
ollama pull qwen2.5:1.5b
ollama create pos-inventario-bot -f Modelfile.txt
python manage.py migrate
python manage.py runserver
```

> Si usas **PowerShell**, el único cambio es la línea 3: `.\venv\Scripts\Activate.ps1`

---

# Verificar que todo funciona

Antes de presentar el proyecto, comprueba que nada esté roto. Con el entorno virtual
activado:

```bash
python manage.py check
```

Debe decir: `System check identified no issues (0 silenced).`

```bash
python manage.py test
```

Debe terminar con: `Ran 53 tests` y luego `OK`.

Y por último, que la IA esté viva:

```bash
ollama list
```

Debe mostrar `qwen2.5:1.5b` **y** `pos-inventario-bot`. Si aparecen las dos, tu
instalación está correcta y el proyecto está listo para entregar.

---

# ¿Algo falló? Problemas frecuentes

| El error dice | Qué significa | Cómo lo arreglo |
|---|---|---|
| `command not found: python` / `'python' no se reconoce` | Python no está en el PATH | En Windows, reinstala Python marcando **"Add Python to PATH"** |
| `No module named django` | El entorno virtual **no está activado** | Repite el [Paso 4](#paso-4--activar-el-entorno-virtual) |
| `externally-managed-environment` | `pip` intentó instalar fuera del entorno | Activa el entorno virtual y repite el [Paso 5](#paso-5--instalar-las-dependencias) |
| `No such file or directory: 'manage.py'` | **No estás dentro de la carpeta** del proyecto | Repite el [Paso 2](#paso-2--entrar-a-la-carpeta-del-proyecto) |
| `ollama: command not found` | **Ollama no está instalado** (es obligatorio) | Instálalo en [ollama.com/download](https://ollama.com/download), cierra y reabre la terminal |
| `Error: model 'pos-inventario-bot' not found` | No creaste el asistente con el `Modelfile` | Repite el paso 7.3: `ollama create pos-inventario-bot -f Modelfile.txt` |
| `model 'qwen2.5:1.5b' not found` | No descargaste el modelo base | Ejecuta `ollama pull qwen2.5:1.5b` (son 986 MB) |
| `address already in use` (puerto 8000 ocupado) | Otro programa usa ese puerto | `python manage.py runserver 8001` y abre el puerto 8001 |
| `TemplateSyntaxError` o errores raros de vista | Cambiaste mal un archivo | `git status` para ver qué tocaste, y revisa la sintaxis |
| El chat dice que no encuentra `pos-inventario-bot` | Faltó el paso 7 | Ve al [Paso 7](#paso-7--instalar-la-ia-con-ollama-obligatorio) |
| El chat responde lento | El modelo corre en CPU | Es normal la primera vez. Puedes subir `OLLAMA_TIMEOUT` en `.env` |
| El chat responde sin IA ("motor de IA no disponible") | Ollama apagado | Deja `ollama serve` corriendo en otra terminal |

---

# Comandos del día a día

Estos son los que vas a usar siempre. **Todos necesitan el entorno virtual activo.**

| Quiero... | Comando |
|---|---|
| Encender el sistema | `source venv/bin/activate` → `python manage.py runserver` |
| Apagar el sistema | `Ctrl` + `C` en la terminal del servidor |
| Where am I? (carpeta actual) | `pwd`  ·  `cd` en Windows |
| Listar archivos | `ls`  ·  `dir` en Windows |
| Crear un modelo en la base de datos (si tocas `models.py`) | `python manage.py makemigrations` y luego `python manage.py migrate` |
| Correr las pruebas | `python manage.py test` |
| Entrar al panel de administración de Django | `python manage.py createsuperuser` y luego abre `/admin/` |

> **Sobre `createsuperuser`:** la base de datos no trae usuarios (es a propósito, por
> seguridad). Si quieres ver el panel de administración de Django en `/admin/`, crea tu
> propio usuario con ese comando la primera vez.

---

# Atajo: ¿prefieres un solo comando?

Si ya te sientes cómodo y solo quieres instalarlo rápido, al final del proyecto dejé
un script que hace los **pasos 3 a 7** de una vez:

```bash
bash instalar.sh
```

**Pero ten en cuenta qué hace**, porque no es magia:

1. Crea el entorno virtual (Paso 3)
2. Instala las dependencias (Paso 5)
3. Copia el `.env` (Paso 6)
4. Descarga `qwen2.5:1.5b` y crea `pos-inventario-bot` si faltan (Paso 7)
5. Aplica las migraciones (Paso 8)
6. Corre las pruebas para confirmar que todo sirve

Es exactamente lo mismo que los pasos manuales, solo que encadenado. **Si algo falla,
el script te dice en qué paso fue** — y en ese caso vuelve a la guía manual, porque
sabrás exactamente dónde se rompió.

> Aunque uses el script, **lee igual el Paso 7**. Ollama es obligatorio y es el paso que
> más confunde a quien empieza. Saber qué hace `ollama pull` y `ollama create` es
> justamente lo que te va a servir cuando algo falle en una sustentación.

---

# ¿Qué hay en este repositorio?

| Carpeta / archivo | Qué contiene | ¿Lo necesito para usar el sistema? |
|---|---|---|
| `config/` | Configuración de Django (settings, rutas) | Sí, no se toca |
| `inventario/` | **Todo el sistema**: modelos, vistas, IA, reportes, HTML y pruebas | Sí, aquí está el código |
| `inventario/templates/` | La interfaz web (el panel que ves en el navegador) | Sí |
| `inventario/migrations/` | El historial de cambios de la base de datos | Sí |
| `db.sqlite3` | La base de datos SQLite (52 productos de ejemplo) | Sí, viene con datos |
| `manage.py` | La herramienta de Django que usas en todos los comandos | Sí |
| `requirements.txt` | La lista de librerías (Paso 5) | Sí |
| `.env.example` | Plantilla de configuración (Paso 6) | Sí, se copia a `.env` |
| `Modelfile.txt` | Las reglas de nuestro asistente de IA (Paso 7.3) | **Sí**, es obligatorio |
| `instalar.sh` | Atajo opcional que hace los pasos 3-7 | Opcional |
| `informe.md` / `informe.pdf` | El informe académico del proyecto | Entrega del coursework |
| `exportar_pdf.py` | Convierte `informe.md` en `informe.pdf` | Solo para regenerar el PDF |
| `DOCUMENTACION.md` | Manual técnico: endpoints, validaciones, pruebas | Si necesitas el detalle |
| `OPENCODE.md` | Convenciones para asistentes de IA que trabajen en el repo | Opcional |

El código vive en dos carpetas: **`config/`** (la configuración de Django) e
**`inventario/`** (todo tu sistema). Adentro de `inventario/` está el corazón del
proyecto.

---

# ¿Qué hace el sistema?

## La pantalla principal

Sin scroll: todo cabe en una pantalla.

- **Izquierda — el sistema:** métricas, catálogo de productos, búsqueda, ajuste rápido
  de stock `+1 / -1`, edición y borrado.
- **Derecha — el chatbot:** consultas en lenguaje natural con 4 accesos rápidos
  (`Stock crítico`, `Producto más caro`, `Valor total`, `Reporte: agotados`).
- **Barra superior:** botones de **Reportes** (8 tipos), **Categorías** (alta y baja)
  e **Historial** de consultas, que se abren en modales para no alargar la página.

## El chatbot no inventa datos

Este es el punto más importante del proyecto. El backend construye el inventario real
como **JSON** y se lo pasa al modelo; el modelo solo puede responder con eso. Si Ollama
está apagado o el modelo no existe, el sistema responde con los datos de SQLite y te
dice qué comando ejecutar. **No hay forma de que alucine datos.**

## Las 8 cosas que puedes hacer

- **CRUD de productos** — crear, ver, editar y borrar.
- **Ajuste de stock** en un clic, sin dejar que baje de cero.
- **Validaciones de servidor** — código único (sin importar si es `ABC` o `abc`) y
  ningún número negativo.
- **8 reportes predefinidos**, todos filtrando solo productos activos.
- **Categorías** — agrégalas, renómbralas y bórralas (solo si ningún producto las usa).
- **Chat con IA** que responde preguntas sobre tu inventario.
- **Historial** de todas las consultas que le hiciste a la IA.
- **Borrado lógico o físico** — por defecto solo se desactiva el producto.

---

# Detalle técnico

> Esta sección es para quien quiera entender el proyecto por dentro, o para defenderlo
> en la sustentación. Si solo necesitas usarlo, arriba está todo.

## Endpoints (nomenclatura snake_case)

| Método | Ruta | Función |
|---|---|---|
| GET | `/` | Panel principal (métricas, tabla, chatbot) |
| GET | `/?mostrar=inactivos` | Panel incluyendo productos desactivados |
| POST | `/api/chat/` | Chat con IA (parámetro `pregunta`) |
| GET | `/api/reporte/?tipo=...` | Reportes predefinidos |
| POST | `/api/producto/guardar/` | Crear / actualizar producto (si llega `id`, es edición) |
| POST | `/api/producto/<pk>/eliminar/` | Borrado: `modo=logico` (defecto) o `fisico` |
| POST | `/api/producto/<pk>/ajustar_stock/` | Ajuste de stock (`operacion=sumar` o `restar`) |
| GET | `/api/categorias/` | Listar el catálogo con conteo de productos |
| POST | `/api/categoria/guardar/` | Crear (`nombre`) o renombrar (`id` + `nombre`) una categoría |
| POST | `/api/categoria/<pk>/eliminar/` | Eliminar categoría (solo si ningún producto la usa) |
| GET | `/api/historial/` | Historial de consultas a la IA |
| GET | `/admin/` | Administración de Django (necesita `createsuperuser`) |

**Tipos de reporte** (parámetro `tipo`): `todos`, `mas_caro`, `mas_barato`,
`pocas_existencias`, `agotados`, `por_categoria` (usa `categoria=`), `valor_total`,
`mayor_cantidad`.

## Arquitectura

- **`inventario/models.py`** — entidades `Producto`, `Categoria` y `ConsultaIA`
  (tablas `productos`, `categorias` y `consultas_ia`).
- **`inventario/forms.py`** — `ProductoForm` y `CategoriaForm` con validaciones de
  servidor: código único (case-insensitive) y números NO negativos.
- **`inventario/reportes.py`** — los 8 reportes predefinidos con explicación de Ollama.
- **`inventario/ia.py`** — construcción del contexto **JSON** + chat con
  `pos-inventario-bot`; si Ollama está caído responde con datos locales.
- **`inventario/ollama_client.py`** — cliente REST (`/api/generate`) y `build_context()`
  que arma el contexto desde los modelos reales.
- **`inventario/views.py`** — vistas CRUD, stock, categorías, chat, reportes e historial.
- **`inventario/tests.py`** — 53 pruebas de modelos, formularios, CRUD, categorías,
  reportes, cliente Ollama y chat.
- **`inventario/templates/inventario/index.html`** — la interfaz POS (con `marked.js`
  para el Markdown del chat).

### Por qué `Producto.categoria` sigue siendo texto

`Categoria` es un catálogo independiente para poder elegir, agregar y borrar categorías
sin reescribir los reportes ni los filtros ya validados. Al guardar un producto, la
categoría escrita se registra sola en el catálogo (`get_or_create`), y la migración `0004`
pobló el catálogo con las categorías que ya usaban los productos. Borrar una categoría en
uso se rechaza indicando cuántos productos la usan.

### Patrones de diseño aplicados

1. **Strategy** (`inventario/reportes.py`): cada tipo de reporte es un algoritmo
   intercambiable; el diccionario `REPORTES` + `generar_reporte(tipo)` selecciona la
   estrategia en tiempo de ejecución sin condicionales encadenados.
2. **Facade** (`inventario/ollama_client.py`): `consultar_ollama()` encapsula todo el
   detalle de la API REST de Ollama (payload, timeout, errores, manejo de 404 con la
   excepción propia `ModeloNoRegistrado` y fallback silencioso a `None`); el resto del
   sistema solo ve una función simple.

---

# Entregables

| Archivo | Descripción |
|---|---|
| `informe.md` | Informe de la Actividad 5 (Programación IV). |
| `informe.pdf` | Versión PDF del informe (A4). |
| `exportar_pdf.py` | Script que convierte `informe.md` en `informe.pdf`. |

Para regenerar el PDF (desde la raíz del proyecto, con el entorno virtual activo):

```bash
python exportar_pdf.py
```

> `informe.md` está escrito **sin tildes ni eñes** de forma intencional (requisito de la
> rúbrica), por eso el nombre del docente aparece como "Lopez Leano" en el archivo. El PDF
> se genera con las mismas fuentes sin diacríticos.
