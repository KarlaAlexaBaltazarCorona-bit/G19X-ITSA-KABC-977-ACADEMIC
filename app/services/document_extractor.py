"""Extractor y Administrador de Texto de Documentos para Asistencia de IA."""

import io
import logging
import uuid
try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # nosec B314
import zipfile
from sqlalchemy.orm import Session

from app.models.document import Documento
from app.models.version import VersionDocumento
from app.services.azure_blob import AzureBlobService
from app.services.azure_doc_intel import DocumentIntelligenceService

logger = logging.getLogger(__name__)

# Caché en memoria para evitar descargar repetidamente el documento en cada turno de chat
_DOCUMENT_TEXT_CACHE: dict[str, str] = {}


def extract_text_from_bytes(content: bytes, filename: str = "", content_type: str = "") -> str:
    """Extrae el texto legible de un archivo a partir de sus bytes brutos."""
    if not content:
        return ""

    filename_lower = filename.lower()

    # 1. Archivos PDF (Enfoque híbrido digital + Azure OCR)
    if filename_lower.endswith(".pdf") or "pdf" in content_type.lower():
        pypdf_text = ""
        has_adequate_text = False
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            extracted_pages = []
            total_chars = 0
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    cleaned = page_text.strip()
                    extracted_pages.append(f"--- Página {i+1} ---\n{cleaned}")
                    total_chars += len(cleaned)
            if extracted_pages:
                pypdf_text = "\n\n".join(extracted_pages)
                # Considerar texto adecuado si supera los 250 caracteres en total
                # y al menos 60 caracteres promedio por página con texto
                avg_chars = total_chars / max(1, len(extracted_pages))
                if total_chars >= 250 and avg_chars >= 60:
                    has_adequate_text = True
        except Exception as e:
            logger.warning("Fallo al extraer texto con pypdf: %s", e)

        # Si pypdf extrajo suficiente texto nítido, retornarlo (0 costo, 0 latencia de red)
        if has_adequate_text:
            return pypdf_text

        # Si el texto digital es escaso, fragmentado o el PDF es un escaneo/imagen:
        # Activar el OCR de Azure Document Intelligence para máxima fidelidad
        logger.info("PDF con texto digital insuficiente o escaneado. Activando OCR de Azure Document Intelligence...")
        try:
            intel_res = DocumentIntelligenceService.extract_clauses_from_pdf(content)
            ocr_text = (intel_res.get("texto") or "").strip()
            if ocr_text:
                logger.info("OCR de Azure completado con éxito (%d caracteres extraídos).", len(ocr_text))
                return ocr_text
        except Exception as e:
            logger.warning("Fallo en OCR de Document Intelligence: %s", e)

        # Si el OCR falló o no devolvió texto, regresar el mejor texto digital que pypdf pudo encontrar
        if pypdf_text:
            return pypdf_text

    # 2. Archivos de imagen directa (PNG, JPG, JPEG, TIFF, BMP, WEBP) -> Directo a OCR de Azure
    image_extensions = (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp")
    if any(filename_lower.endswith(ext) for ext in image_extensions) or "image/" in content_type.lower():
        try:
            logger.info("Imagen detectada (%s). Extrayendo texto mediante Azure Document Intelligence OCR...", filename)
            intel_res = DocumentIntelligenceService.extract_clauses_from_pdf(content)
            ocr_text = (intel_res.get("texto") or "").strip()
            if ocr_text:
                return ocr_text
        except Exception as e:
            logger.warning("Fallo al extraer texto de imagen con Document Intelligence: %s", e)

    # 3. Archivos Word (.docx)
    if filename_lower.endswith(".docx") or "word" in content_type.lower() or "officedocument" in content_type.lower():
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if "word/document.xml" in z.namelist():
                    xml_content = z.read("word/document.xml")
                    tree = ET.fromstring(xml_content)  # nosec B314
                    text_parts = []
                    for elem in tree.iter():
                        if elem.tag.endswith("t") and elem.text:
                            text_parts.append(elem.text)
                    if text_parts:
                        return " ".join(text_parts)
        except Exception as e:
            logger.warning("Fallo al extraer texto de DOCX: %s", e)

    # 4. Archivos de texto plano / markdown / json / csv
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except Exception:
            pass

    return ""


def cache_document_text(key: str | uuid.UUID, text: str) -> None:
    """Almacena el texto extraído en la caché en memoria."""
    if key and text:
        _DOCUMENT_TEXT_CACHE[str(key)] = text


def get_cached_document_text(key: str | uuid.UUID) -> str | None:
    """Obtiene el texto en caché si está disponible."""
    return _DOCUMENT_TEXT_CACHE.get(str(key))


def get_document_text_for_solicitud(db: Session, solicitud_id: uuid.UUID) -> str:
    """Recupera el texto completo del documento asociado a una solicitud de revisión."""
    # 1. Verificar si ya está en caché por solicitud_id
    cached = get_cached_document_text(solicitud_id)
    if cached:
        return cached

    # 2. Buscar documento y última versión en BD
    doc = db.query(Documento).filter(Documento.solicitud_id == solicitud_id).first()
    if not doc:
        return ""

    cached_doc = get_cached_document_text(doc.id)
    if cached_doc:
        cache_document_text(solicitud_id, cached_doc)
        return cached_doc

    # Buscar última versión del documento
    ult_ver = (
        db.query(VersionDocumento)
        .filter(VersionDocumento.documento_id == doc.id)
        .order_by(VersionDocumento.numero_version.desc())
        .first()
    )
    if not ult_ver or not ult_ver.ubicacion:
        return ""

    cached_ver = get_cached_document_text(ult_ver.id)
    if cached_ver:
        cache_document_text(solicitud_id, cached_ver)
        return cached_ver

    # 3. Descargar el archivo desde Azure Blob Storage
    try:
        raw_bytes = AzureBlobService.download_file(ult_ver.ubicacion)
        if raw_bytes:
            texto = extract_text_from_bytes(
                content=raw_bytes,
                filename=ult_ver.nombre_archivo or doc.nombre,
                content_type=ult_ver.formato_archivo or "",
            )
            if texto:
                cache_document_text(solicitud_id, texto)
                cache_document_text(doc.id, texto)
                cache_document_text(ult_ver.id, texto)
                return texto
    except Exception as e:
        logger.error("Error al obtener texto del documento para solicitud %s: %s", solicitud_id, e)

    return ""


def extract_dense_legal_context(text: str, max_chars: int = 1800) -> str:
    """Extrae un extracto denso y de alto valor legal del documento (partes, objeto, penas, vigencia)
    garantizando que el prompt quepa holgadamente dentro de cuotas estrictas de tokens (ej. 1000 TPM).
    """
    if not text or len(text) <= max_chars:
        return text

    # 1. Tomar encabezado y declaraciones iniciales (primeros 700 caracteres)
    partes = [text[:700].strip()]

    # 2. Buscar fragmentos clave mediante palabras jurídicas críticas
    palabras_clave = ("pena", "sanci", "vigencia", "plazo", "rescisi", "jurisdicci", "monto", "pago")
    parrafos = text.split("\n")
    parrafos_clave = []
    longitud_acumulada = 700

    for p in parrafos:
        p_clean = p.strip()
        if len(p_clean) < 20:
            continue
        p_lower = p_clean.lower()
        if any(kw in p_lower for kw in palabras_clave):
            if longitud_acumulada + len(p_clean) < max_chars:
                parrafos_clave.append(p_clean)
                longitud_acumulada += len(p_clean)

    if parrafos_clave:
        partes.append("\n[... EXTRACTO DE CLÁUSULAS CRÍTICAS DETECTADAS ...]\n" + "\n".join(parrafos_clave))
    else:
        partes.append("\n[... CIERRE DEL DOCUMENTO ...]\n" + text[-600:].strip())

    return "\n\n".join(partes)


def generate_local_legal_summary(text: str, title: str = "") -> str:
    """Genera una auditoría jurídica estructurada a partir del texto extraído directamente,
    sirviendo como respaldo analítico inmediato ante límites de concurrencia en la API externa.
    """
    lineas = [linea.strip() for linea in text.splitlines() if linea.strip()]
    if not lineas:
        return "El documento no contiene texto legible suficiente para un análisis estructurado."

    intro = "\n".join(lineas[:6])
    penas = [linea for linea in lineas if any(k in linea.lower() for k in ("pena ", "penas ", "multa", "sanción", "sancion", "moratorio", "indemniz"))]
    vigencia = [linea for linea in lineas if any(k in linea.lower() for k in ("vigencia", "plazo", "duración", "duracion", "término", "termino"))]
    jurisdiccion = [linea for linea in lineas if any(k in linea.lower() for k in ("jurisdicción", "jurisdiccion", "tribunales", "competencia", "ley aplicable", "legislación", "legislacion"))]

    resultado = [
        "### 📋 Dictamen y Auditoría Preliminar del Documento",
        f"**Expediente / Archivo:** {title or 'Documento adjunto'}",
        f"**Extensión analizada:** {len(lineas)} párrafos digitalizados.",
        "",
        "#### 1. Identificación y Declaraciones Iniciales",
        f"> {intro[:350]}...",
        "",
        "#### 2. Cláusulas de Penalización y Sanciones Detectadas",
    ]
    if penas:
        resultado.extend([f"- {p[:200]}" for p in penas[:4]])
    else:
        resultado.append("- *No se identificaron cláusulas expresas de penalización o multas en los fragmentos analizados.*")

    resultado.extend([
        "",
        "#### 3. Vigencia y Plazos",
    ])
    if vigencia:
        resultado.extend([f"- {v[:200]}" for v in vigencia[:3]])
    else:
        resultado.append("- *Plazo general o vigencia indeterminada.*")

    resultado.extend([
        "",
        "#### 4. Jurisdicción y Ley Aplicable",
    ])
    if jurisdiccion:
        resultado.extend([f"- {j[:200]}" for j in jurisdiccion[:2]])
    else:
        resultado.append("- *Jurisdicción estándar o supletoria según la legislación aplicable.*")

    resultado.extend([
        "",
        "---",
        "💡 *Análisis legal preliminar generado directamente a partir del contenido digitalizado del expediente. Para formular preguntas adicionales específicas sobre alguna cláusula, envíalas directamente en el chat.*",
    ])

    return "\n".join(resultado)

