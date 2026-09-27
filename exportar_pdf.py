#!/usr/bin/env python3
"""Exporta informe.md a informe.pdf en la raiz del proyecto.

Uso (desde la raiz del proyecto):

    venv/bin/python exportar_pdf.py

Motor principal: Markdown -> HTML -> PDF con xhtml2pdf (sin dependencias del
sistema). Si xhtml2pdf no esta disponible, usa LibreOffice como alternativa
(libreoffice --headless --convert-to pdf). Los archivos temporales HTML se
borran al terminar; en la raiz solo quedan informe.md e informe.pdf.
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ORIGEN = RAIZ / "informe.md"
DESTINO = RAIZ / "informe.pdf"

CSS = """
@page {
    size: A4;
    margin: 2cm 1.8cm 2cm 1.8cm;
    @frame footer { -pdf-frame-content: footer; bottom: 1cm; margin-left: 1.8cm;
                    margin-right: 1.8cm; height: 1cm; }
}
body { font-family: Helvetica, sans-serif; font-size: 10.5pt; line-height: 1.45;
       color: #1f2933; }
h1 { font-size: 16pt; color: #1a365d; border-bottom: 2px solid #1a365d;
     padding-bottom: 4pt; margin-top: 18pt; }
h2 { font-size: 13pt; color: #2c5282; margin-top: 14pt; }
p  { text-align: justify; margin: 5pt 0; }
code { font-family: Courier, monospace; font-size: 8.8pt; background-color: #f4f6f8;
       color: #1a202c; }
pre { font-family: Courier, monospace; font-size: 8.4pt; background-color: #f4f6f8;
      border: 0.6pt solid #cbd5e0; padding: 6pt; line-height: 1.3; }
table { border-collapse: collapse; width: 100%; font-size: 9.5pt; margin: 8pt 0; }
th { background-color: #1a365d; color: #ffffff; text-align: left; padding: 5pt; }
td { border: 0.5pt solid #cbd5e0; padding: 4pt; }
ul { margin: 5pt 0 5pt 16pt; }
li { margin: 2.5pt 0; }
strong { color: #1a202c; }
"""


def markdown_a_html(texto: str) -> str:
    import markdown

    cuerpo = markdown.markdown(
        texto,
        extensions=["extra", "tables", "fenced_code", "sane_lists", "nl2br"],
    )
    # nl2br no es necesario en el informe: puede romper las celdas de las tablas.
    cuerpo = cuerpo.replace("<br />\n", "\n")
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{cuerpo}</body></html>'


def exportar_con_xhtml2pdf(ruta_html: Path) -> bool:
    try:
        from xhtml2pdf import pisa
    except ImportError:
        return False
    with ruta_html.open("rb") as origen:
        with DESTINO.open("wb") as salida:
            estado = pisa.CreatePDF(
                src=origen,
                dest=salida,
                encoding="utf-8",
                path=str(RAIZ / "xhtml2pdf.log"),
            )
    if estado.err:
        print("[AVISO] xhtml2pdf reporto errores (ver xhtml2pdf.log)")
        return False
    return True


def exportar_con_libreoffice(ruta_html: Path) -> bool:
    ejecutable = shutil.which("soffice") or shutil.which("libreoffice")
    if not ejecutable:
        return False
    subprocess.run(
        [ejecutable, "--headless", "--convert-to", "pdf:writer_web_pdf_Export",
         "--outdir", str(RAIZ), str(ruta_html)],
        check=True, capture_output=True,
    )
    generado = ruta_html.with_suffix(".pdf")
    if not generado.exists():
        return False
    shutil.move(str(generado), str(DESTINO))
    return True


def main() -> int:
    if not ORIGEN.exists():
        print(f"[ERROR] No se encontró {ORIGEN.name} en la raíz del proyecto.")
        return 1

    # Respeta la regla del informe: PDF solo con caracteres ASCII.
    texto = ORIGEN.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        ruta_html = Path(tmp) / "informe.html"
        ruta_html.write_text(markdown_a_html(texto), encoding="utf-8")

        if exportar_con_xhtml2pdf(ruta_html):
            motor = "xhtml2pdf"
        elif exportar_con_libreoffice(ruta_html):
            motor = "LibreOffice"
        else:
            print("[ERROR] No hay motor de conversion disponible.")
            print("        Instala las dependencias: venv/bin/pip install -r requirements.txt")
            return 1

    limpio = not any(ord(c) > 127 for c in texto)
    tam = DESTINO.stat().st_size / 1024
    print(f"[OK] {DESTINO.name} generado con {motor} ({tam:.1f} KB)")
    print(f"     Entrada: {ORIGEN.name} - texto sin tildes/enies: {'si' if limpio else 'NO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
