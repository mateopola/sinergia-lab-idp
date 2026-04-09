"""
SinergIA Lab — Pipeline de Preprocesamiento Documental
=======================================================
Módulo reutilizable con todas las funciones de Fase 2:
  - Detección de portada (Pólizas y CC; desactivado para Cédulas)
  - Preprocesamiento visual: deskew, denoise, enhance_contrast, binarize, normalize_dpi
  - Filtro CIIU para RUT (elimina sección de actividades económicas antes de embeddings)
  - Regex Labeling Functions para pre-anotación de RUT
  - Chunking por tipología: sliding_window (RUT/Pólizas), layout_aware (CC), sin chunking (Cédula)
  - Función unificada chunk_document(pdf_path, doc_type)

Uso desde la raíz del proyecto:
    from src.preprocessing.pipeline import preprocess_pipeline, chunk_document
"""

import re
from pathlib import Path

import cv2
import fitz
import numpy as np


# ─── Constantes ──────────────────────────────────────────────────────────────
BPE_FACTOR        = 1.25        # Factor de corrección BPE para Llama 3 en español
TOKENS_HARD_LIMIT = 1800        # Límite duro de chunking (12% margen sobre 2,048)
CHUNK_SIZE        = 512         # Tamaño de chunk en tokens
OVERLAP           = 0.30        # Solapamiento del 30%
OVERLAP_TOKENS    = int(CHUNK_SIZE * OVERLAP)    # 153 tokens

# Tipologías para las que la detección de portada está ACTIVA
TIPOLOGIAS_CON_PORTADA = {'Poliza', 'Camara de Comercio'}

# ─── Detección de portada ────────────────────────────────────────────────────

def detectar_portada(pdf_path: Path, categoria: str = '') -> tuple[bool, int]:
    """
    Detecta si la página 1 de un PDF es una portada sin datos estructurados.

    NOTA: desactivado para Cédulas. El criterio lexicon < 50 AND blocks < 5 genera
    falsos positivos en cédulas escaneadas (93% del corpus) donde página 1 = imagen.
    Solo aplica a Pólizas y Cámara de Comercio (tipologías digitales).

    Retorna: (tiene_portada: bool, start_page: int)
    """
    if categoria and categoria not in TIPOLOGIAS_CON_PORTADA:
        return False, 0

    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count <= 1:
            doc.close()
            return False, 0

        p0 = doc[0]
        texto_p0   = p0.get_text().strip()
        bloques_p0 = [b for b in p0.get_text('blocks') if b[6] == 0]
        doc.close()

        es_portada = len(texto_p0) < 50 and len(bloques_p0) < 5
        return es_portada, (1 if es_portada else 0)
    except Exception:
        return False, 0


# ─── Preprocesamiento visual ─────────────────────────────────────────────────

def deskew(img_gray: np.ndarray) -> np.ndarray:
    """Corrige inclinación detectando el ángulo predominante de los contornos de texto."""
    coords = np.column_stack(np.where(img_gray < 200))
    if len(coords) < 100:
        return img_gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:
        return img_gray
    h, w = img_gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img_gray, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def denoise(img_gray: np.ndarray) -> np.ndarray:
    """Elimina ruido con filtro gaussiano suave."""
    return cv2.GaussianBlur(img_gray, (3, 3), 0)


def enhance_contrast(img_gray: np.ndarray, clip_limit: float = 2.0,
                     tile_grid: tuple = (8, 8)) -> np.ndarray:
    """
    Mejora el contraste local con CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Especialmente útil para documentos escaneados con iluminación desigual o fondos grises.

    clip_limit: límite de amplificación de contraste. Valores altos = más contraste,
                más riesgo de amplificar ruido. 2.0 es conservador.
    tile_grid:  tamaño de la cuadrícula de tiles. (8,8) = balance entre detalle y velocidad.
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    return clahe.apply(img_gray)


def binarize(img_gray: np.ndarray) -> np.ndarray:
    """Umbralización adaptativa Otsu: separa texto del fondo de forma robusta."""
    _, binarized = cv2.threshold(
        img_gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binarized


def normalize_dpi(img_rgb: np.ndarray, target_dpi: int = 300,
                  source_dpi: int = 150) -> np.ndarray:
    """Redimensiona la imagen al DPI objetivo (estándar para OCR)."""
    scale = target_dpi / source_dpi
    new_h = int(img_rgb.shape[0] * scale)
    new_w = int(img_rgb.shape[1] * scale)
    return cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)


def preprocess_pipeline(pdf_path: Path, categoria: str = '',
                        source_dpi: int = 150) -> np.ndarray | None:
    """
    Pipeline completo de preprocesamiento visual.
    Flujo: detectar_portada → deskew → denoise → enhance_contrast → binarize → normalize_dpi

    Parámetros:
        pdf_path:   ruta al PDF a procesar
        categoria:  tipología ('Cedula', 'RUT', 'Poliza', 'Camara de Comercio')
                    determina si se aplica detección de portada
        source_dpi: DPI de renderizado del PDF (150 = balance velocidad/calidad)

    Retorna imagen procesada como array RGB, o None si falla.
    """
    try:
        doc = fitz.open(str(pdf_path))
        _, start_page = detectar_portada(pdf_path, categoria)
        if start_page >= doc.page_count:
            start_page = 0

        pix = doc[start_page].get_pixmap(
            matrix=fitz.Matrix(source_dpi / 72, source_dpi / 72),
            colorspace=fitz.csRGB,
        )
        doc.close()

        img_rgb  = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3)
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        img_gray = deskew(img_gray)
        img_gray = denoise(img_gray)
        img_gray = enhance_contrast(img_gray)
        img_gray = binarize(img_gray)
        img_clean = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)
        img_clean = normalize_dpi(img_clean, source_dpi=source_dpi)
        return img_clean
    except Exception:
        return None


# ─── Filtro CIIU para RUT ────────────────────────────────────────────────────

# Vocabulario alimentario que contamina los embeddings de RUT
# Proviene de la lista de actividades CIIU del formulario DIAN
_CIIU_FOOD_TERMS = re.compile(
    r'\b(org[aá]nicas?|congeladas?|congelados?|frasco|lata|secas?|secos?|'
    r'org[aá]nicos?|frescas?|frescos?|deshidratadas?|enlatadas?)\b',
    re.IGNORECASE,
)

# Patrón de encabezado de la sección de actividades CIIU en el formulario DIAN
_CIIU_SECTION_HEADER = re.compile(
    r'(?i)(?:24\.|casilla\s*24|actividades?\s*econ[oó]micas?)',
)


def filtrar_ciiu_rut(texto: str) -> str:
    """
    Elimina el vocabulario CIIU del texto de RUT para embeddings limpios.

    El formulario DIAN imprime la lista completa de clasificaciones CIIU
    (frutas orgánicas, latas, frascos, congelados) que contamina embeddings.

    IMPORTANTE: usar solo para generación de embeddings/TF-IDF, NO para extracción NER.
    Para NER usar el texto completo con extraer_entidades_rut().

    Estrategia conservadora: elimina tokens del vocabulario CIIU conocido sin truncar
    el texto (truncar eliminaría los valores de campos que vienen después del header).
    """
    return _CIIU_FOOD_TERMS.sub('', texto)


# ─── Regex Labeling Functions para RUT ───────────────────────────────────────

def extraer_entidades_rut(texto: str) -> dict:
    """
    Extrae entidades NER de un RUT con regex (Labeling Functions para pre-anotación).
    Retorna dict con entidades encontradas (None si no se detecta).
    Solo para RUT: los 235 docs tienen texto digital disponible.

    NOTA sobre el formato DIAN: PyMuPDF extrae el texto en orden de lectura,
    mezclando labels del formulario con valores. El NIT aparece en cajas de dígito
    individual separados por espacio. Las LFs son un punto de partida para Label Studio
    — se espera corrección humana de ~30% de los campos.
    """
    entidades = {}

    # NIT — dos estrategias:
    # 1. Formato continuo con guión: 860518862-7
    m = re.search(r'\b(\d{7,11})\s*[-\u2013]\s*(\d)\b', texto)
    if m:
        entidades['nit'] = f"{m.group(1)}-{m.group(2)}"
    else:
        # 2. Formato cajas DIAN: dígitos unitarios con 1 espacio entre cada uno
        # Ej: "8 6 0 5 1 8 8 6 2 7" (9 dígitos NIT + 1 DV)
        m = re.search(r'(\d(?: \d){8,9})', texto)
        if m:
            digits = m.group(1).replace(' ', '')
            entidades['nit'] = f"{digits[:-1]}-{digits[-1]}" if len(digits) >= 9 else digits
        else:
            entidades['nit'] = None

    # Razón Social — aparece en MAYÚSCULAS con forma jurídica conocida
    # El formulario DIAN imprime el nombre después del bloque de identificación
    m = re.search(
        r'\n([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.,&-]{8,99}(?:LTDA|SAS|S\.A|E\.U|EIRL|CIA|INC)[^\n]*)\n',
        texto, re.UNICODE,
    )
    entidades['razon_social'] = m.group(1).strip() if m else None

    # Régimen tributario — "régimen ordinario" o "régimen simplificado"
    m = re.search(r'(?i)r[eé]gimen\s+(\w+)', texto)
    if m:
        r = m.group(1).strip()
        if r.lower().startswith('ordinar'):
            r = 'ordinario'
        elif r.lower().startswith('simpli'):
            r = 'simplificado'
        entidades['regimen'] = r
    else:
        entidades['regimen'] = None

    # Dirección — patrón colombiano de nomenclatura urbana
    m = re.search(r'(?i)\b((?:CL|CR|AV|TV|KR|CALLE|CARRERA|AVENIDA)\s+\d+[^\n]{5,80})', texto)
    entidades['direccion'] = m.group(1).strip() if m else None

    # Municipio — lista de ciudades principales de Colombia
    m = re.search(
        r'(Bogot[aá][\s,]*D\.?C\.?|Medell[ií]n|Cali|Barranquilla|Cartagena|'
        r'Bucaramanga|Pereira|Manizales|Ibagu[eé]|C[uú]cuta|Villavicencio|'
        r'Santa Marta|Monter[ií]a|Neiva|Armenia|Pasto|Popay[aá]n)',
        texto, re.IGNORECASE,
    )
    entidades['municipio'] = m.group(1).strip() if m else None

    # Representante legal — APELLIDOS NOMBRES antes de la línea "Representante legal"
    m = re.search(
        r'([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]{2,}){1,5})\s*\nRepresentante legal',
        texto, re.UNICODE,
    )
    entidades['representante_legal'] = m.group(1).strip() if m else None

    return entidades


# ─── Chunking ────────────────────────────────────────────────────────────────

def _palabras_a_tokens_bpe(n_palabras: int) -> int:
    """Estima tokens BPE a partir del conteo de palabras (heurística + factor BPE Llama 3)."""
    return int((n_palabras / 0.75) * BPE_FACTOR)


def sliding_window_chunks(texto: str, chunk_size: int = CHUNK_SIZE,
                          overlap: int = OVERLAP_TOKENS) -> list[str]:
    """
    Divide texto en chunks con ventana deslizante.
    chunk_size y overlap están en tokens estimados (BPE x1.25).
    Retorna lista de strings.
    """
    palabras = texto.split()
    palabras_por_chunk = int(chunk_size / BPE_FACTOR * 0.75)
    palabras_overlap   = int(overlap  / BPE_FACTOR * 0.75)

    chunks, start = [], 0
    while start < len(palabras):
        end = start + palabras_por_chunk
        chunks.append(' '.join(palabras[start:end]))
        start += palabras_por_chunk - palabras_overlap
        if start >= len(palabras):
            break
    return chunks


def layout_aware_chunks(pdf_path: Path, categoria: str = 'Camara de Comercio',
                        gap_px: int = 40, min_words: int = 50) -> list[str]:
    """
    Chunking por secciones lógicas usando bboxes PyMuPDF (para Cámara de Comercio).
    Detecta saltos de sección por espacio vertical entre bloques y agrupa los bloques
    en secciones coherentes, cada una como un chunk independiente.

    gap_px:    espacio vertical mínimo (px) para considerar inicio de nueva sección
    min_words: mínimo de palabras para emitir un chunk (fusiona secciones cortas)
    """
    try:
        doc = fitz.open(str(pdf_path))
        _, start_page = detectar_portada(pdf_path, categoria)
        secciones, seccion_actual = [], []

        for page_num in range(start_page, doc.page_count):
            page   = doc[page_num]
            blocks = sorted(
                [b for b in page.get_text('blocks') if b[6] == 0],
                key=lambda b: (b[1], b[0]),
            )
            prev_y2 = None
            for b in blocks:
                y1, y2, texto_bloque = b[1], b[3], b[4].strip()
                if not texto_bloque:
                    continue
                if prev_y2 is not None and (y1 - prev_y2) > gap_px:
                    if seccion_actual:
                        secciones.append(' '.join(seccion_actual))
                        seccion_actual = []
                seccion_actual.append(texto_bloque)
                prev_y2 = y2

        doc.close()
        if seccion_actual:
            secciones.append(' '.join(seccion_actual))

        # Fusionar secciones muy cortas con la siguiente
        resultado, buffer = [], ''
        for s in secciones:
            buffer = (buffer + ' ' + s).strip()
            if len(buffer.split()) >= min_words:
                resultado.append(buffer)
                buffer = ''
        if buffer:
            resultado.append(buffer)

        return resultado
    except Exception:
        return []


def chunk_document(pdf_path: Path, doc_type: str) -> dict:
    """
    Función unificada de chunking — el doc_type determina la estrategia internamente.

    Estrategias:
        Cedula           → sin chunking (texto OCR corto; imágenes escaneadas)
        RUT              → ventana deslizante (64% supera 1,800 tokens BPE)
        Poliza           → ventana deslizante (14% supera 1,800 tokens BPE)
        Camara de Comercio → layout-aware con bboxes PyMuPDF

    Retorna dict con:
        doc_type, estrategia, n_chunks, chunks (lista de strings), tokens_estimados
    """
    try:
        doc = fitz.open(str(pdf_path))
        _, start_page = detectar_portada(pdf_path, doc_type)
        texto_completo = ' '.join(
            doc[i].get_text() for i in range(start_page, doc.page_count)
        )
        doc.close()
    except Exception:
        return {'doc_type': doc_type, 'estrategia': 'error', 'n_chunks': 0,
                'chunks': [], 'tokens_estimados': 0}

    # Aplicar filtro CIIU para RUT antes de chunking
    if doc_type == 'RUT':
        texto_completo = filtrar_ciiu_rut(texto_completo)

    n_palabras    = len(texto_completo.split())
    tokens_est    = _palabras_a_tokens_bpe(n_palabras)

    if doc_type == 'Cedula':
        chunks    = [texto_completo] if texto_completo.strip() else []
        estrategia = 'sin_chunking'

    elif doc_type == 'Camara de Comercio':
        chunks    = layout_aware_chunks(pdf_path, categoria=doc_type)
        estrategia = 'layout_aware'

    else:  # RUT y Póliza
        if tokens_est > TOKENS_HARD_LIMIT:
            chunks    = sliding_window_chunks(texto_completo)
            estrategia = 'sliding_window'
        else:
            chunks    = [texto_completo]
            estrategia = 'sin_chunking'

    return {
        'doc_type':          doc_type,
        'estrategia':        estrategia,
        'n_chunks':          len(chunks),
        'chunks':            chunks,
        'tokens_estimados':  tokens_est,
    }
