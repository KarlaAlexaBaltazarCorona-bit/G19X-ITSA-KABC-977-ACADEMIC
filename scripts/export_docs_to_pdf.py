"""
export_docs_to_pdf.py — Generador automatizado de documentos PDF para LegalprojectIA.
═══════════════════════════════════════════════════════════════════════════════════════════
Convierte los archivos Markdown de la suite de documentación a formato PDF corporativo
utilizando markdown-it-py para el renderizado HTML y el motor Chromium de Microsoft Edge
o Google Chrome en modo headless con alta fidelidad gráfica.
"""

import os
import re
import shutil
import tempfile
import subprocess
from pathlib import Path
from markdown_it import MarkdownIt

# Configurar motor Chromium
CHROME_OR_EDGE_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe"),
    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
]

def find_browser_executable() -> str:
    for path in CHROME_OR_EDGE_PATHS:
        if os.path.exists(path):
            return path
    which_edge = shutil.which("msedge") or shutil.which("chrome")
    if which_edge:
        return which_edge
    raise RuntimeError("No se encontró ejecutable de Microsoft Edge o Google Chrome para la conversión a PDF.")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    @page {{
      size: letter portrait;
      margin: 20mm 15mm 20mm 15mm;
      @bottom-right {{
        content: counter(page);
      }}
    }}

    *, *:before, *:after {{
      box-sizing: border-box;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-size: 10pt;
      line-height: 1.55;
      color: #1e293b;
      background: #ffffff;
      margin: 0;
      padding: 0;
    }}

    /* Encabezado Corporativo */
    .doc-header {{
      border-bottom: 2px solid #2563eb;
      padding-bottom: 8px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .doc-header .org {{
      font-size: 8.5pt;
      font-weight: 700;
      color: #1e40af;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .doc-header .meta {{
      font-size: 8pt;
      color: #64748b;
    }}

    /* Tipografía y Títulos */
    h1 {{
      font-size: 19pt;
      font-weight: 800;
      color: #0f172a;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 8px;
      margin-top: 0;
      margin-bottom: 12px;
      page-break-after: avoid;
    }}

    h2 {{
      font-size: 14pt;
      font-weight: 700;
      color: #1e3a8a;
      margin-top: 24px;
      margin-bottom: 10px;
      border-bottom: 1px dashed #cbd5e1;
      padding-bottom: 4px;
      page-break-after: avoid;
    }}

    h3 {{
      font-size: 11.5pt;
      font-weight: 600;
      color: #1e293b;
      margin-top: 18px;
      margin-bottom: 6px;
      page-break-after: avoid;
    }}

    p {{
      margin-top: 0;
      margin-bottom: 10px;
      text-align: justify;
    }}

    a {{
      color: #2563eb;
      text-decoration: none;
    }}

    /* Tablas Ejecutivas */
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;
      font-size: 8.5pt;
      page-break-inside: avoid;
    }}

    th, td {{
      padding: 7px 10px;
      border: 1px solid #cbd5e1;
      text-align: left;
      vertical-align: top;
    }}

    th {{
      background-color: #f1f5f9;
      color: #0f172a;
      font-weight: 700;
      text-transform: uppercase;
      font-size: 8pt;
      letter-spacing: 0.03em;
    }}

    tr:nth-child(even) td {{
      background-color: #f8fafc;
    }}

    /* Bloques de Código y Sintaxis */
    pre {{
      background-color: #0f172a;
      color: #f8fafc;
      padding: 12px 14px;
      border-radius: 6px;
      font-family: Consolas, "Courier New", monospace;
      font-size: 8pt;
      line-height: 1.45;
      overflow-x: auto;
      margin: 12px 0;
      page-break-inside: avoid;
    }}

    code {{
      font-family: Consolas, "Courier New", monospace;
      background-color: #f1f5f9;
      color: #b91c1c;
      padding: 2px 5px;
      border-radius: 4px;
      font-size: 8.5pt;
    }}

    pre code {{
      background-color: transparent;
      color: inherit;
      padding: 0;
      border-radius: 0;
    }}

    /* Diagramas y Bloques de Texto Estructurado */
    pre.diagram-block {{
      background-color: #f8fafc;
      color: #1e293b;
      border: 1px solid #cbd5e1;
      border-left: 4px solid #2563eb;
      font-family: Consolas, "Courier New", monospace;
      font-size: 7.5pt;
      line-height: 1.35;
      white-space: pre-wrap;
    }}

    /* Citas y Callouts */
    blockquote {{
      margin: 14px 0;
      padding: 10px 14px;
      background-color: #eff6ff;
      border-left: 4px solid #3b82f6;
      color: #1e3a8a;
      font-size: 9pt;
      border-radius: 0 4px 4px 0;
      page-break-inside: avoid;
    }}

    blockquote p {{
      margin: 0;
    }}

    /* Listas */
    ul, ol {{
      margin-top: 0;
      margin-bottom: 10px;
      padding-left: 22px;
    }}

    li {{
      margin-bottom: 4px;
    }}

    hr {{
      border: 0;
      border-top: 1px solid #e2e8f0;
      margin: 20px 0;
    }}

    /* Insignias e Indicadores */
    .badge {{
      display: inline-block;
      padding: 2px 6px;
      font-size: 7.5pt;
      font-weight: 600;
      border-radius: 4px;
      background-color: #e2e8f0;
      color: #334155;
    }}

    /* Pie de Página */
    .doc-footer {{
      margin-top: 30px;
      padding-top: 10px;
      border-top: 1px solid #e2e8f0;
      font-size: 7.5pt;
      color: #94a3b8;
      display: flex;
      justify-content: space-between;
    }}
  </style>
</head>
<body>
  <div class="doc-header">
    <div class="org">PluriOne S.A. de C.V. &bull; ITSA &bull; LegalprojectIA</div>
    <div class="meta">Documentación Oficial de Sistema &bull; Etapa Terminal</div>
  </div>

  <main>
    {content}
  </main>

  <div class="doc-footer">
    <div>LegalprojectIA &mdash; Plataforma de Workflow para Revisión Jurídica (SaaS)</div>
    <div>Confidencial &bull; Registro de Residencia Profesional</div>
  </div>
</body>
</html>
"""

def clean_markdown_for_pdf(md_text: str) -> str:
    """Sanea el Markdown para una renderización limpia en PDF."""
    # Convertir bloques de código ```mermaid en diagramas estructurados legibles
    def replace_mermaid(match):
        code = match.group(1).strip()
        return f'<pre class="diagram-block"><strong>[DIAGRAMA DE ARQUITECTURA / FLUJO]</strong>\n\n{code}</pre>'

    md_text = re.sub(r'```mermaid\s*([\s\S]*?)```', replace_mermaid, md_text)

    # Manejar imágenes badge que no carguen en local (sustituir texto alternativo si es badge)
    md_text = re.sub(r'\[!\[(.*?)\]\(.*?\)\]\(.*?\)', r'<span class="badge">\1</span>', md_text)
    md_text = re.sub(r'!\[(.*?)\]\(.*?\)', r'<span class="badge">\1</span>', md_text)

    return md_text

def convert_md_to_pdf(md_path: Path, output_pdf_path: Path, browser_exe: str):
    """Convierte un archivo Markdown individual a PDF."""
    print(f"-> Procesando: {md_path.name}...")
    text = md_path.read_text(encoding="utf-8")

    # Extraer título del primer H1
    h1_match = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    doc_title = h1_match.group(1) if h1_match else md_path.stem

    cleaned_md = clean_markdown_for_pdf(text)

    # Parsear a HTML con tablas y GFM
    md_parser = MarkdownIt("gfm-like", {"linkify": False})
    body_html = md_parser.render(cleaned_md)

    full_html = HTML_TEMPLATE.format(title=doc_title, content=body_html)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as temp_file:
        temp_file.write(full_html)
        temp_html_path = Path(temp_file.name)

    try:
        cmd = [
            browser_exe,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={output_pdf_path.resolve()}",
            f"file:///{temp_html_path.resolve().as_posix()}"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 or not output_pdf_path.exists():
            print(f"   [Error] Falló la conversión para {md_path.name}: {res.stderr}")
        else:
            size_kb = output_pdf_path.stat().st_size / 1024
            print(f"   [OK] Generado: {output_pdf_path.name} ({size_kb:.1f} KB)")
    finally:
        if temp_html_path.exists():
            try:
                temp_html_path.unlink()
            except Exception:
                pass

def main():
    root_dir = Path(__file__).resolve().parent.parent
    docs_dir = root_dir / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    browser_exe = find_browser_executable()
    print("=== Generador de Documentación PDF para LegalprojectIA ===")
    print(f"Motor Chromium detectado: {browser_exe}")
    print(f"Directorio de salida: {docs_dir.resolve()}\n")

    # Lista de archivos a convertir
    files_to_export = [
        # Documentación de docs/
        (docs_dir / "INDEX.md", docs_dir / "INDEX.pdf"),
        (docs_dir / "MANUAL_USUARIO_Y_ROLES.md", docs_dir / "MANUAL_USUARIO_Y_ROLES.pdf"),
        (docs_dir / "ARQUITECTURA_SISTEMA.md", docs_dir / "ARQUITECTURA_SISTEMA.pdf"),
        (docs_dir / "MATRIZ_HISTORIAS_USUARIO.md", docs_dir / "MATRIZ_HISTORIAS_USUARIO.pdf"),
        (docs_dir / "API_REFERENCE.md", docs_dir / "API_REFERENCE.pdf"),
        (docs_dir / "SEGURIDAD_Y_DEVSECOPS.md", docs_dir / "SEGURIDAD_Y_DEVSECOPS.pdf"),
        (docs_dir / "GUIA_ENTREGA_CLIENTE_AZURE.md", docs_dir / "GUIA_ENTREGA_CLIENTE_AZURE.pdf"),
        # Documentos centrales del repositorio (también exportados a docs/ para el paquete de entrega)
        (root_dir / "README.md", docs_dir / "README.pdf"),
        (root_dir / "CONTRIBUTING.md", docs_dir / "CONTRIBUTING.pdf"),
    ]

    count = 0
    for src_md, out_pdf in files_to_export:
        if src_md.exists():
            convert_md_to_pdf(src_md, out_pdf, browser_exe)
            count += 1
        else:
            print(f"   [Aviso] No encontrado: {src_md.name}")

    print("\n=======================================================")
    print(f"Finalizado con éxito. Se generaron {count} archivos PDF en {docs_dir}.")

if __name__ == "__main__":
    main()
