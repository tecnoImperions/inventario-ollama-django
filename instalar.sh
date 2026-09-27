#!/usr/bin/env bash
# ======================================================================
# instalar.sh - Deja el proyecto listo para usarse con un solo comando.
#
#   bash instalar.sh
#
# Hace todo lo necesario: entorno virtual, dependencias, configuracion,
# base de datos, modelo de IA y pruebas. Si algo falla, avisa y se detiene.
# ======================================================================

set -e

BOLD="\033[1m"; VERDE="\033[32m"; ROJO="\033[31m"; GRIS="\033[0m"
paso()  { echo -e "\n${BOLD}[$1/6] $2${GRIS}"; }
ok()    { echo -e "  ${VERDE}OK${GRIS} $1"; }
fallo() { echo -e "  ${ROJO}ERROR${GRIS} $1"; exit 1; }

echo -e "${BOLD}=============================================="
echo -e " Pingux POS - instalacion automatica"
echo -e "==============================================${GRIS}"

# --- 1. Python --------------------------------------------------------
paso 1 "Verificando Python"
command -v python3 >/dev/null 2>&1 || fallo "No se encontro python3. Instala Python 3.11 o superior."
PYV=$(python3 --version | awk '{print $2}')
echo "$PYV" | grep -qE '^3\.(1[1-9]|[2-9][0-9])' || fallo "Se necesita Python 3.11 o superior (tienes $PYV)."
ok "Python $PYV"

# --- 2. Entorno virtual ----------------------------------------------
paso 2 "Creando el entorno virtual"
[ -d venv ] || python3 -m venv venv || fallo "No se pudo crear el entorno virtual."
ok "venv/ listo"

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --quiet --upgrade pip
ok "pip actualizado"

# --- 3. Dependencias --------------------------------------------------
paso 3 "Instalando dependencias"
pip install --quiet -r requirements.txt || fallo "Fallo pip install -r requirements.txt"
ok "$(pip list 2>/dev/null | grep -ci django) Django y dependencias instaladas"

# --- 4. Configuracion -------------------------------------------------
paso 4 "Configurando variables de entorno"
[ -f .env ] || { cp .env.example .env; ok ".env creado desde .env.example"; } || ok ".env ya existe"
ok "Ollama apuntando a http://localhost:11434"

# --- 5. Base de datos -------------------------------------------------
paso 5 "Preparando la base de datos"
python manage.py migrate --noinput || fallo "Fallo la migracion de la base de datos."
ok "Migraciones aplicadas"

# --- 6. Modelo de IA + pruebas ---------------------------------------
paso 6 "Verificando Ollama y ejecutando pruebas"
if command -v ollama >/dev/null 2>&1; then
    if curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
        ok "Servidor de Ollama encendido"
        if ollama list 2>/dev/null | grep -q "pos-inventario-bot"; then
            ok "Modelo pos-inventario-bot ya registrado"
        else
            if ollama list 2>/dev/null | grep -q "qwen2.5:1.5b"; then
                ok "Modelo base qwen2.5:1.5b ya descargado"
            else
                echo "  Descargando el modelo base qwen2.5:1.5b (puede tardar)..."
                ollama pull qwen2.5:1.5b >/dev/null 2>&1 \
                    && ok "Modelo base qwen2.5:1.5b descargado" \
                    || echo "  ${GRIS}Aviso: no se pudo descargar qwen2.5:1.5b (sin internet?).${GRIS}"
            fi
            echo "  Registrando el modelo desde Modelfile.txt..."
            ollama create pos-inventario-bot -f Modelfile.txt >/dev/null 2>&1 \
                && ok "Modelo pos-inventario-bot creado" \
                || echo "  ${GRIS}Aviso: no se pudo crear el modelo. Ejecuta manualmente:${GRIS}"
                 echo "         ollama pull qwen2.5:1.5b"
                 echo "         ollama create pos-inventario-bot -f Modelfile.txt"
        fi
    else
        echo "  ${GRIS}Aviso: Ollama no responde. La app funciona igual (usa datos de SQLite),${GRIS}"
        echo "  ${GRIS}pero para la IA debes iniciar el servidor con: ollama serve${GRIS}"
    fi
else
    echo "  ${GRIS}Aviso: Ollama no esta instalado. La app arranca igual sin la IA.${GRIS}"
fi

echo ""
TEST_LOG=$(python manage.py test 2>&1)
if echo "$TEST_LOG" | grep -qE "^(OK|FAILED)"; then
    if echo "$TEST_LOG" | grep -q "^OK"; then
        ok "Pruebas automatizadas correctas ($(echo "$TEST_LOG" | grep -oE 'Ran [0-9]+ tests' | head -1))"
    else
        echo "$TEST_LOG" | tail -20
        fallo "Las pruebas fallaron. Revisa el mensaje de arriba."
    fi
else
    fallo "No se pudo ejecutar la suite de pruebas."
fi

echo -e "\n${BOLD}=============================================="
echo -e " INSTALACION COMPLETADA"
echo -e "==============================================${GRIS}"
echo ""
echo -e "  ${BOLD}Para arrancar el sistema:${GRIS}"
echo -e "    1) ${BOLD}bash instalar.sh${GRIS}      (solo la primera vez)"
echo -e "    2) ${BOLD}source venv/bin/activate${GRIS}"
echo -e "    3) ${BOLD}python manage.py runserver${GRIS}"
echo ""
echo -e "  Luego abre en el navegador: ${BOLD}http://127.0.0.1:8000${GRIS}"
echo ""
