# Pingux POS — Sistema de Inventario con IA Local

CRUD de productos en **Django** con un chatbot que responde preguntas sobre tu inventario
usando **Ollama** (IA local, sin internet).

Entregable final — Programación IV.

---

## Requisitos

| Necesitas | Versión | Obligatorio |
|---|---|---|
| Python | 3.11 o superior | **Sí** |
| Ollama | cualquiera | **Sí** |
| Editor de código (VS Code) | cualquiera | No, pero ayuda |
| Internet | — | Solo la primera vez |

Descarga: [Python](https://www.python.org/downloads/) · [Ollama](https://ollama.com/download)

> En Windows, al instalar Python marca la casilla **"Add Python to PATH"**.

---

## Instalación paso a paso

### 1. Descomprimir el proyecto

Descomprime el archivo `.zip` del entregable en una carpeta de tu preferencia.

Dentro encontrarás:

```
proyecto/     ← el código Django (aquí trabajas)
informe.md
informe.pdf
```

### 2. Entrar a la carpeta del proyecto

Abre la terminal **desde dentro de `proyecto/`**.

En VS Code: click derecho en la carpeta → *Abrir en terminal*.

```bash
cd proyecto
```

Verifica que estás en el sitio correcto:

```bash
ls          # Linux y macOS
dir         # Windows
```

Debes ver `manage.py` y `requirements.txt`.

### 3. Crear el entorno virtual

```bash
python3 -m venv venv          # Linux y macOS
python -m venv venv           # Windows
```

Crea una carpeta `venv/` donde se instalan las librerías del proyecto, separadas del
Python de tu computadora. Para no romper otros proyectos.

### 4. Activar el entorno virtual

**Linux y macOS:**
```bash
source venv/bin/activate
```

**Windows (CMD):**
```cmd
venv\Scripts\activate
```

**Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

Debes ver `(venv)` al principio de la línea. Ese paso se repite cada vez que abras una
terminal nueva.

### 5. Instalar las dependencias

```bash
pip install -r requirements.txt
```

Lee el archivo `requirements.txt` y descarga todo lo que el proyecto necesita. Tarda 1-2
minutos la primera vez.

### 6. Crear el archivo de configuración

```bash
cp .env.example .env          # Linux y macOS
copy .env.example .env        # Windows
```

Crea tu copia del archivo de configuración. **No necesitas cambiar nada** para trabajar en
local.

### 7. Instalar la IA con Ollama

Este paso es obligatorio: sin él el chat no tiene modelo de lenguaje.

**7.1** Instala Ollama desde [ollama.com/download](https://ollama.com/download) y
**cierra y reabre la terminal**.

**7.2** Descarga el modelo (986 MB, tarda unos minutos la primera vez):

```bash
ollama pull qwen2.5:1.5b
```

**7.3** Crea el asistente con las reglas del proyecto:

```bash
ollama create pos-inventario-bot -f Modelfile.txt
```

**7.4** Verifica:

```bash
ollama list
```

Debes ver dos líneas:

```
NAME                         ID              SIZE      MODIFIED
qwen2.5:1.5b                 65ec06548149    986 MB    10 days ago
pos-inventario-bot:latest    f6ba89e20845    986 MB    4 days ago
```

### 8. Preparar la base de datos

```bash
python manage.py migrate
```

Verás `No migrations to apply.` **y está bien**: la base de datos ya viene incluida con
52 productos de ejemplo, así que no hay nada pendiente.

### 9. Arrancar el sistema

```bash
python manage.py runserver
```

Abre **http://127.0.0.1:8000**

Para detenerlo: `Ctrl` + `C`.

---

## Verificar que todo funciona

```bash
python manage.py check    # debe decir: System check identified no issues
python manage.py test     # debe terminar en: Ran 53 tests ... OK
ollama list               # debe mostrar los dos modelos
```

---

## Problemas frecuentes

| Error | Causa | Solución |
|---|---|---|
| `command not found: python` | Python no está en el PATH | Reinstala Python marcando "Add Python to PATH" |
| `No module named django` | No activaste el entorno virtual | Repite el paso 4 |
| `No such file or directory: 'manage.py'` | No estás dentro de `proyecto/` | Repite el paso 2 |
| `ollama: command not found` | Ollama no está instalado | Instálalo y reabre la terminal (paso 7.1) |
| `model 'qwen2.5:1.5b' not found` | No descargaste el modelo | `ollama pull qwen2.5:1.5b` |
| El chat no responde con IA | Ollama apagado | Deja `ollama serve` corriendo en otra terminal |
| `address already in use` | El puerto 8000 está ocupado | `python manage.py runserver 8001` |

---

## Comandos del día a día

| Quiero... | Comando |
|---|---|
| Encender el sistema | `source venv/bin/activate` → `python manage.py runserver` |
| Detener el sistema | `Ctrl` + `C` |
| Correr las pruebas | `python manage.py test` |
| Ver el panel de administración | `python manage.py createsuperuser` y abre `/admin/` |

> Al crear el superusuario te pedirá usuario y contraseña. La base de datos no trae
> usuarios por seguridad.

---

## ¿Qué hay en la carpeta?

| Archivo | Qué es |
|---|---|
| `manage.py` | La herramienta de Django |
| `config/` | Configuración de Django |
| `inventario/` | El sistema: modelos, vistas, IA, reportes, HTML y pruebas |
| `requirements.txt` | Lista de librerías |
| `.env.example` | Plantilla de configuración (se copia a `.env`) |
| `db.sqlite3` | Base de datos con 52 productos de ejemplo |
| `Modelfile.txt` | Las reglas del asistente de IA |

---

## ¿Dónde está el resto de la información?

| Quiero saber... | Abrir |
|---|---|
| Cómo está hecho el sistema por dentro | `DOCUMENTACION.md` |
| El informe del coursework | `informe.md` |
| Cómo se construyó con OpenCode | `OPENCODE.md` |
