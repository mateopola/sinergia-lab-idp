"""
SinergIA Lab — Fase 1 CRISP-DM++: Analisis Descriptivo del Corpus SECOP
========================================================================
Ejecutar desde la raiz del proyecto:
    python notebooks/run_fase1.py

Entorno: Python 3.12 (env_eda)
PDF:     PyMuPDF (fitz) — extraccion primaria de texto digital + bounding boxes
         Sin dependencias del sistema (reemplaza pdf2image+Poppler).
OCR:     EasyOCR 1.7+ — SOLO fallback para documentos escaneados (lexicon < 50 chars).
         No se corre sobre documentos digitales. Decision documentada en PLAN v1.3.
Tokens:  Heuristica: lexicon_count / 0.75
         Correccion BPE Llama 3: * 1.25 (fragmentacion de jerga legal en espanol)
         Limite duro de chunking: 1,800 tokens (margen 12% sobre 2,048).
"""
import json
import hashlib
import warnings
from pathlib import Path
from typing import Dict, Optional

import fitz                        # PyMuPDF
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from tqdm import tqdm

warnings.filterwarnings('ignore')

# ── Rutas ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
DATA_PROC.mkdir(parents=True, exist_ok=True)

# Nombres exactos de carpetas en disco (verificados en EDA inicial)
CATEGORIES: Dict[str, Path] = {
    'Cedula':             DATA_RAW / 'CEDULA',
    'RUT':                DATA_RAW / 'rut',
    'Poliza':             DATA_RAW / 'POLIZA',
    'Camara de Comercio': DATA_RAW / 'CAMARA DE CIO',
}

SUPPORTED_EXT = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.pdf'}

# ── Umbrales de calidad visual ─────────────────────────────────────────────────
# Calibrados sobre corpus SECOP real (PDFs digitales nativos — fondo blanco ~248-252)
BLUR_THRESHOLD   = 100    # Varianza Laplaciana < umbral -> borroso
BRIGHTNESS_LOW   = 60     # < umbral -> muy oscuro
BRIGHTNESS_HIGH  = 253    # > umbral -> sobreexpuesto
CONTRAST_LOW     = 20     # < umbral -> texto indistinguible del fondo

# ── Umbrales de texto ─────────────────────────────────────────────────────────
MIN_TEXT_CHARS   = 50     # Si PyMuPDF extrae menos de esto -> documento escaneado
TOKENS_HARD_LIMIT = 1800  # Limite duro de seguridad para chunking (12% margen sobre 2,048)
BPE_CORRECTION   = 1.25  # Factor BPE Llama 3: fragmenta jerga legal en espanol
HEURISTIC_RATIO  = 0.75  # words -> tokens basico: tokens = words / 0.75

PALETTE = {
    'Cedula':             '#4C72B0',
    'RUT':                '#DD8452',
    'Poliza':             '#55A868',
    'Camara de Comercio': '#C44E52',
}

sns.set_theme(style='whitegrid', palette='muted', font_scale=1.1)
plt.rcParams.update({'figure.dpi': 120})
np.random.seed(42)


# ── Inicializacion EasyOCR (fallback para escaneados) ─────────────────────────
print('Inicializando EasyOCR (fallback para documentos escaneados)...')
print('  (Primera ejecucion: descarga modelos ~300MB. Las siguientes usan cache local.)')
try:
    import easyocr
    OCR = easyocr.Reader(['es', 'en'], gpu=False, verbose=False)
    OCR_OK = True
    print(f'  EasyOCR {easyocr.__version__} listo.')
except ImportError:
    OCR = None
    OCR_OK = False
    print('  ADVERTENCIA: EasyOCR no disponible — documentos escaneados sin OCR.')
    print('  Instalar con: pip install easyocr')


# ── Carga de imagen ───────────────────────────────────────────────────────────
def load_image(filepath: str) -> Optional[np.ndarray]:
    """
    Carga imagen o primera pagina de PDF como array RGB.
    PyMuPDF convierte PDFs sin Poppler ni ghostscript.
    """
    path = Path(filepath)
    try:
        if path.suffix.lower() == '.pdf':
            doc = fitz.open(str(path))
            if doc.page_count == 0:
                return None
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(150/72, 150/72),
                                     colorspace=fitz.csRGB)
            doc.close()
            return np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3)
        else:
            img_bgr = cv2.imread(str(path))
            if img_bgr is None:
                return None
            return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    except Exception:
        return None


# ── Calidad visual (OpenCV) ───────────────────────────────────────────────────
def analyze_visual(img_rgb: np.ndarray) -> Dict:
    """
    Metricas de calidad visual:
      brightness : luminosidad media (0-255)
      contrast   : std de luminosidad — bajo (<20) = texto/fondo indistinguibles
      blur_score : varianza del Laplaciano — <100 borroso, >500 nitido
    """
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    b  = float(np.mean(gray))
    c  = float(np.std(gray))
    bl = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if bl < 20 or c < 10 or b < 30 or b > 253:
        label = 'DESCARTADO'
    elif bl < BLUR_THRESHOLD or c < CONTRAST_LOW or b < BRIGHTNESS_LOW or b > BRIGHTNESS_HIGH:
        label = 'REQUIERE_PREPROCESAMIENTO'
    else:
        label = 'APTO'

    return {
        'brightness':    round(b, 2),
        'contrast':      round(c, 2),
        'blur_score':    round(bl, 2),
        'width_px':      img_rgb.shape[1],
        'height_px':     img_rgb.shape[0],
        'quality_label': label,
    }


# ── Extraccion primaria: PyMuPDF (documentos digitales) ───────────────────────
def extract_text_pymupdf(filepath: str) -> Dict:
    """
    Intento 1 de extraccion de texto: PyMuPDF sobre PDFs digitales.

    Retorna:
      lexicon_count        : palabras en el texto digital
      pymupdf_blocks       : bloques de texto detectados (proxy de densidad de layout)
      pymupdf_text_density : area_texto / area_pagina (ratio 0-1)
      es_escaneado         : True si el documento no tiene texto digital suficiente
      extraccion_metodo    : 'pymupdf' | 'imagen_directa' (necesita OCR)

    Para imagenes directas (.jpg, .png, etc.) siempre retorna es_escaneado=True.
    Para PDFs con texto digital, PyMuPDF es ~100x mas rapido que OCR y mas preciso
    en bounding boxes (coordenadas exactas, no estimadas por red neuronal).

    El RUT DIAN es el caso paradigmatico: 97 bloques, 26.2% densidad — datos del EDA.
    """
    path = Path(filepath)

    # Imagenes directas: no tienen capa de texto, siempre necesitan OCR
    if path.suffix.lower() != '.pdf':
        return {
            'lexicon_count':        0,
            'pymupdf_blocks':       0,
            'pymupdf_text_density': 0.0,
            'es_escaneado':         True,
            'extraccion_metodo':    'imagen_directa',
        }

    try:
        doc = fitz.open(str(path))
        if doc.page_count == 0:
            doc.close()
            return {
                'lexicon_count':        0,
                'pymupdf_blocks':       0,
                'pymupdf_text_density': 0.0,
                'es_escaneado':         True,
                'extraccion_metodo':    'pdf_vacio',
            }

        page      = doc[0]
        text      = page.get_text()
        blocks    = page.get_text('blocks')
        page_area = page.rect.width * page.rect.height
        doc.close()

        # Solo bloques tipo texto (type==0); type==1 son imagenes incrustadas
        text_blocks = [b for b in blocks if b[6] == 0]
        text_area   = sum((b[2] - b[0]) * (b[3] - b[1]) for b in text_blocks)
        density     = text_area / page_area if page_area > 0 else 0.0

        word_count   = len(text.split())
        es_escaneado = len(text.strip()) < MIN_TEXT_CHARS

        return {
            'lexicon_count':        word_count,
            'pymupdf_blocks':       len(text_blocks),
            'pymupdf_text_density': round(density, 4),
            'es_escaneado':         es_escaneado,
            'extraccion_metodo':    'ocr_requerido' if es_escaneado else 'pymupdf',
        }

    except Exception as e:
        return {
            'lexicon_count':        0,
            'pymupdf_blocks':       0,
            'pymupdf_text_density': 0.0,
            'es_escaneado':         True,
            'extraccion_metodo':    f'pymupdf_error:{type(e).__name__}',
        }


# ── Fallback OCR: EasyOCR (solo documentos escaneados) ────────────────────────
def bbox_area(bbox) -> float:
    """Area de un bounding box cuadrilatero [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]."""
    pts = np.array(bbox, dtype=np.float32)
    n = len(pts)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return abs(area) / 2.0


def run_easyocr_fallback(img_rgb: np.ndarray, reader) -> Dict:
    """
    Fallback OCR (solo se ejecuta cuando PyMuPDF no encuentra texto digital).
    EasyOCR retorna [bbox, text, confidence] por bloque detectado.

    La densidad calculada aqui complementa la de PyMuPDF para documentos escaneados:
    sin este paso, las Cedulas (93% escaneadas) quedarian con text_density=0
    y no podriamos comparar densidades entre tipologias de forma homogenea.
    """
    img_h, img_w = img_rgb.shape[:2]
    img_area = img_h * img_w

    results = reader.readtext(img_rgb)

    if not results:
        return {
            'ocr_lexicon_count': 0,
            'ocr_bbox_count':    0,
            'ocr_text_density':  0.0,
            'avg_confidence':    0.0,
        }

    texts, confs, text_area = [], [], 0.0
    for (bbox, text, conf) in results:
        texts.append(text)
        confs.append(conf)
        text_area += bbox_area(bbox)

    word_count = len(' '.join(texts).split())
    return {
        'ocr_lexicon_count': word_count,
        'ocr_bbox_count':    len(results),
        'ocr_text_density':  round(text_area / img_area, 4) if img_area else 0.0,
        'avg_confidence':    round(float(np.mean(confs)), 4),
    }


# ── Calculo de tokens con correccion BPE ─────────────────────────────────────
def calc_tokens(lexicon_count: int) -> Dict:
    """
    Dos estimaciones de tokens para el contexto de Llama 3 (BPE):

      tokens_heuristica   : lexicon_count / 0.75 — estimacion basica (1 token ~ 0.75 palabras)
      tokens_bpe_ajustado : * 1.25 — correccion empirica para BPE de Llama 3

    La jerga legal colombiana (NIT, CIIU, RUNT, siglas DIAN, denominaciones societarias)
    se fragmenta en subpalabras por el tokenizador BPE, generando mas tokens que en
    texto general. El factor x1.25 fue validado sobre el corpus SECOP en el EDA.

    El limite duro de chunking es TOKENS_HARD_LIMIT (1,800) — margen del 12% sobre 2,048
    para absorber varianza entre documentos de la misma tipologia.
    """
    tokens_h   = int(lexicon_count / HEURISTIC_RATIO)
    tokens_bpe = int(tokens_h * BPE_CORRECTION)
    return {
        'tokens_heuristica':   tokens_h,
        'tokens_bpe_ajustado': tokens_bpe,
        'supera_limite_bpe':   tokens_bpe > TOKENS_HARD_LIMIT,
    }


# ── Inventario del corpus ─────────────────────────────────────────────────────
def compute_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8192), b''):
            h.update(block)
    return h.hexdigest()


def scan_corpus(categories: Dict[str, Path]) -> pd.DataFrame:
    records = []
    for cat, folder in categories.items():
        if not folder.exists():
            print(f'  ADVERTENCIA: carpeta no encontrada -> {folder}')
            continue
        files = [fp for fp in folder.iterdir()
                 if fp.is_file() and fp.suffix.lower() in SUPPORTED_EXT]
        for fp in files:
            records.append({
                'filepath':  str(fp),
                'filename':  fp.name,
                'category':  cat,
                'extension': fp.suffix.lower(),
                'size_kb':   round(fp.stat().st_size / 1024, 2),
                'md5':       compute_md5(fp),
            })
    df = pd.DataFrame(records)
    if not df.empty:
        df['is_duplicate'] = df.duplicated(subset='md5', keep='first')
    return df


# ── Pipeline por documento ────────────────────────────────────────────────────
def process_document(row: pd.Series) -> Dict:
    """
    Pipeline de tres etapas por documento:

      1. Calidad visual (OpenCV) — siempre
      2. Extraccion PyMuPDF     — siempre para PDFs (texto digital + bounding boxes)
      3. OCR EasyOCR            — SOLO si PyMuPDF no encuentra texto suficiente

    Esta logica evita correr OCR (lento, ~1-2 min/doc en CPU) sobre documentos
    que ya tienen texto digital accesible, como el 83% de los RUT y el 92% de
    los Certificados de Camara de Comercio.

    Columnas de salida relevantes:
      extraccion_metodo    : 'pymupdf' | 'easyocr' | 'ocr_no_disponible' | 'imagen_directa'
      lexicon_count        : palabras del texto digital (PyMuPDF) o 0 si escaneado
      pymupdf_blocks       : bloques de texto PyMuPDF (solo docs digitales)
      pymupdf_text_density : densidad de texto PyMuPDF (solo docs digitales)
      ocr_bbox_count       : bloques EasyOCR (solo docs escaneados)
      ocr_text_density     : densidad EasyOCR (solo docs escaneados)
      tokens_heuristica    : estimacion basica lexicon / 0.75
      tokens_bpe_ajustado  : estimacion BPE Llama 3 (heuristica * 1.25)
      supera_limite_bpe    : True si tokens_bpe_ajustado > 1,800 (requiere chunking)
    """
    result = {
        'filepath': row['filepath'],   'filename':  row['filename'],
        'category': row['category'],   'extension': row['extension'],
        'size_kb':  row['size_kb'],    'md5':       row['md5'],
        'is_duplicate':        row.get('is_duplicate', False),
        # Calidad visual
        'brightness': None, 'contrast': None, 'blur_score': None,
        'width_px':   None, 'height_px': None, 'quality_label': 'ERROR',
        # Extraccion PyMuPDF
        'lexicon_count':        None,
        'pymupdf_blocks':       None,
        'pymupdf_text_density': None,
        'es_escaneado':         None,
        'extraccion_metodo':    None,
        # OCR fallback (solo escaneados)
        'ocr_lexicon_count': None,
        'ocr_bbox_count':    None,
        'ocr_text_density':  None,
        'avg_confidence':    None,
        # Tokens con correccion BPE
        'tokens_heuristica':   None,
        'tokens_bpe_ajustado': None,
        'supera_limite_bpe':   None,
        'error': None,
    }

    # ── Etapa 1: Calidad visual ────────────────────────────────────────────────
    try:
        img = load_image(row['filepath'])
        if img is None:
            result['error'] = 'load_failed'
            return result
        result.update(analyze_visual(img))
    except Exception as e:
        result['error'] = f'opencv_error:{type(e).__name__}'
        return result

    # ── Etapa 2: Extraccion PyMuPDF ───────────────────────────────────────────
    try:
        pymupdf_data = extract_text_pymupdf(row['filepath'])
        result.update(pymupdf_data)
        es_escaneado = pymupdf_data.get('es_escaneado', True)
    except Exception as e:
        result['error'] = f'pymupdf_error:{type(e).__name__}'
        es_escaneado = True  # Si falla PyMuPDF, intentar OCR

    # ── Etapa 3: OCR fallback (solo si no hay texto digital) ──────────────────
    if es_escaneado:
        if OCR_OK and OCR is not None:
            try:
                ocr_data = run_easyocr_fallback(img, OCR)
                result.update(ocr_data)
                result['extraccion_metodo'] = 'easyocr'
                # Para calcular tokens en escaneados usamos el lexicon del OCR
                lexicon_para_tokens = result.get('ocr_lexicon_count') or 0
            except Exception as e:
                msg = f'easyocr_error:{type(e).__name__}'
                result['error'] = (result['error'] + '|' + msg) if result['error'] else msg
                lexicon_para_tokens = 0
        else:
            result['extraccion_metodo'] = 'ocr_no_disponible'
            lexicon_para_tokens = 0
    else:
        # Documento digital: tokens del texto PyMuPDF
        lexicon_para_tokens = result.get('lexicon_count') or 0

    # ── Calculo de tokens con correccion BPE ──────────────────────────────────
    if lexicon_para_tokens is not None:
        result.update(calc_tokens(lexicon_para_tokens))

    return result


# ── Visualizaciones ───────────────────────────────────────────────────────────
def plot_distribucion(df: pd.DataFrame):
    counts    = df['category'].value_counts()
    colors    = [PALETTE.get(c, '#888') for c in counts.index]
    ql_counts = df['quality_label'].value_counts()
    ql_colors = {'APTO': '#2ecc71', 'REQUIERE_PREPROCESAMIENTO': '#f39c12',
                 'DESCARTADO': '#e74c3c', 'ERROR': '#95a5a6'}

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Distribucion del Corpus SECOP — SinergIA Lab', fontsize=13, fontweight='bold')

    bars = axes[0].barh(counts.index, counts.values, color=colors, edgecolor='white')
    for bar, v in zip(bars, counts.values):
        axes[0].text(v + 0.05, bar.get_y() + bar.get_height() / 2,
                     f'{v}  ({v/counts.sum()*100:.1f}%)', va='center', fontsize=9)
    axes[0].set_xlabel('Documentos')
    axes[0].set_title('Por tipologia')
    axes[0].set_xlim(0, counts.max() * 1.35)

    axes[1].pie(ql_counts.values, labels=ql_counts.index, autopct='%1.1f%%',
                colors=[ql_colors.get(l, '#bdc3c7') for l in ql_counts.index],
                startangle=90, textprops={'fontsize': 9})
    axes[1].set_title('Calidad visual global')

    plt.tight_layout()
    out = DATA_PROC / 'fig01_distribucion_corpus.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


def plot_scatter_calidad(df: pd.DataFrame):
    df_viz = df.dropna(subset=['brightness', 'blur_score'])
    ql_markers = {'APTO': 'o', 'REQUIERE_PREPROCESAMIENTO': 's',
                  'DESCARTADO': 'X', 'ERROR': 'D'}

    fig, ax = plt.subplots(figsize=(12, 6))
    for cat, color in PALETTE.items():
        for ql, marker in ql_markers.items():
            sub = df_viz[(df_viz['category'] == cat) & (df_viz['quality_label'] == ql)]
            if sub.empty:
                continue
            ax.scatter(sub['brightness'], sub['blur_score'], c=color, marker=marker,
                       alpha=0.7, s=80, edgecolors='white', linewidths=0.5)

    ax.axhline(BLUR_THRESHOLD,  color='red',    linestyle='--', lw=1.2,
               label=f'Umbral blur ({BLUR_THRESHOLD})')
    ax.axvline(BRIGHTNESS_LOW,  color='orange', linestyle=':', lw=1.2)
    ax.axvline(BRIGHTNESS_HIGH, color='orange', linestyle=':', lw=1.2,
               label=f'Rango brillo ({BRIGHTNESS_LOW}-{BRIGHTNESS_HIGH})')
    ax.axhspan(0, BLUR_THRESHOLD, alpha=0.06, color='red')

    legend_cats = [mpatches.Patch(color=c, label=cat) for cat, c in PALETTE.items()]
    legend_ql   = [plt.scatter([], [], marker=m, color='grey', label=l)
                   for l, m in ql_markers.items()]
    l1 = ax.legend(handles=legend_cats, title='Tipologia', loc='upper left', fontsize=8)
    ax.add_artist(l1)
    ax.legend(handles=legend_ql + [
        plt.Line2D([0],[0], color='red',    linestyle='--', label=f'Blur < {BLUR_THRESHOLD}'),
        plt.Line2D([0],[0], color='orange', linestyle=':',  label='Rango brillo'),
    ], title='Calidad / Umbrales', loc='upper right', fontsize=8)

    ax.set_yscale('log')
    ax.set_xlabel('Brillo (luminosidad media 0-255)')
    ax.set_ylabel('Blur Score (varianza Laplaciana — escala log)')
    ax.set_title('Calidad Visual: Iluminacion vs. Nitidez por Tipologia', fontweight='bold')
    plt.tight_layout()
    out = DATA_PROC / 'fig02_scatter_iluminacion_blur.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


def plot_textometria(df: pd.DataFrame):
    # Usar tokens_bpe_ajustado; fallback a tokens_heuristica si no existe
    tok_col = 'tokens_bpe_ajustado' if 'tokens_bpe_ajustado' in df.columns else 'tokens_heuristica'
    df_t = df.dropna(subset=[tok_col])
    if df_t.empty:
        print('  (Sin datos de tokens — fig03 omitida)')
        return

    cat_order = df_t.groupby('category')[tok_col].median().sort_values().index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Estimacion de Tokens por Tipologia (BPE x1.25 — Llama 3)',
                 fontsize=13, fontweight='bold')

    sns.violinplot(data=df_t, x=tok_col, y='category', order=cat_order,
                   palette=PALETTE, inner='box', ax=axes[0])
    axes[0].axvline(TOKENS_HARD_LIMIT, color='red',    linestyle='--', lw=1.5,
                    label=f'Limite chunking ({TOKENS_HARD_LIMIT})')
    axes[0].axvline(2048,              color='orange', linestyle=':',  lw=1.2,
                    label='Contexto max (2,048)')
    axes[0].set_xlabel('Tokens estimados (BPE x1.25)')
    axes[0].set_title('Distribucion de longitud — con correccion BPE')
    axes[0].legend(fontsize=8)

    # Docs que superan el limite por tipologia
    supera = df_t.groupby('category')['supera_limite_bpe'].sum().reindex(cat_order)
    total  = df_t.groupby('category').size().reindex(cat_order)
    pct    = (supera / total * 100).fillna(0)
    colors = [PALETTE.get(c, '#888') for c in cat_order]
    bars = axes[1].barh(cat_order, supera.values, color=colors, edgecolor='white')
    for bar, v, p in zip(bars, supera.values, pct.values):
        axes[1].text(v + 0.3, bar.get_y() + bar.get_height() / 2,
                     f'{int(v)} docs  ({p:.1f}%)', va='center', fontsize=9)
    axes[1].set_xlabel('Documentos que superan limite BPE')
    axes[1].set_title(f'Docs > {TOKENS_HARD_LIMIT} tokens (requieren chunking)')
    axes[1].set_xlim(0, supera.max() * 1.5 if supera.max() > 0 else 10)

    plt.tight_layout()
    out = DATA_PROC / 'fig03_tokens_bpe.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


def plot_densidad_layout(df: pd.DataFrame):
    """
    Densidad textual por tipologia.
    - Documentos digitales: densidad de PyMuPDF (exacta, coordenadas reales)
    - Documentos escaneados: densidad de EasyOCR (estimada por red neuronal)
    Unificar en una sola columna 'text_density_efectiva' para comparacion.
    """
    df = df.copy()
    # Prioridad: PyMuPDF para digitales, EasyOCR para escaneados
    df['text_density_efectiva'] = np.where(
        df['es_escaneado'] == False,
        df['pymupdf_text_density'],
        df['ocr_text_density']
    )
    df_d = df.dropna(subset=['text_density_efectiva'])
    if df_d.empty:
        print('  (Sin datos de densidad — fig04 omitida)')
        return

    cat_order = (df_d.groupby('category')['text_density_efectiva']
                 .median().sort_values(ascending=False).index.tolist())

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.boxplot(data=df_d, x='category', y='text_density_efectiva',
                order=cat_order, palette=PALETTE, ax=ax)
    ax.set_title('Densidad Textual por Tipologia\n'
                 '(PyMuPDF para digitales | EasyOCR para escaneados)',
                 fontweight='bold')
    ax.set_xlabel('Tipologia')
    ax.set_ylabel('Densidad textual (area texto / area pagina)')

    # Anotar mediana
    for i, cat in enumerate(cat_order):
        med = df_d[df_d['category'] == cat]['text_density_efectiva'].median()
        ax.text(i, med + 0.005, f'{med:.3f}', ha='center', fontsize=9, fontweight='bold')

    plt.tight_layout()
    out = DATA_PROC / 'fig04_densidad_layout.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print('=' * 65)
    print('  FASE 1 CRISP-DM++ — SinergIA Lab')
    print('  PyMuPDF (digital) + EasyOCR fallback (escaneados) + BPE x1.25')
    print('=' * 65)
    print()

    # 1. Inventario
    print('[1/5] Escaneando corpus...')
    df_corpus = scan_corpus(CATEGORIES)
    if df_corpus.empty:
        print('ERROR: No se encontraron documentos en data/raw/.')
        return

    n_dup = df_corpus['is_duplicate'].sum()
    print(f'  Documentos  : {len(df_corpus)}')
    print(f'  Duplicados  : {n_dup}')
    print(f'  Tamano total: {df_corpus["size_kb"].sum()/1024:.1f} MB')
    print()
    print(df_corpus.groupby('category')[['filename']].count()
          .rename(columns={'filename': 'docs'}).to_string())
    print()

    # 2. Pipeline completo
    print('[2/5] Analizando documentos...')
    print('      Etapa A: Calidad visual (OpenCV)')
    print('      Etapa B: Extraccion texto (PyMuPDF — digital)')
    print('      Etapa C: OCR fallback (EasyOCR — solo escaneados)')
    if not OCR_OK:
        print('      [AVISO] EasyOCR no disponible — escaneados sin fallback OCR.')
    records = []
    for _, row in tqdm(df_corpus.iterrows(), total=len(df_corpus), desc='  Procesando'):
        records.append(process_document(row))
    df = pd.DataFrame(records)

    n_err = df['error'].notna().sum()
    print(f'\n  Procesados : {len(df)} | Errores: {n_err}')
    if n_err:
        print(df[df['error'].notna()][['filename', 'category', 'error']].to_string(index=False))

    # 3. Estadisticas
    print()
    print('[3/5] Estadisticas...')
    print()
    print('  CALIDAD VISUAL:')
    print('  ' + df['quality_label'].value_counts().to_string().replace('\n', '\n  '))

    print()
    print('  DOCUMENTOS ESCANEADOS VS DIGITALES:')
    scan_stats = df.groupby('category')['es_escaneado'].agg(['sum', 'count'])
    scan_stats['pct_escaneados'] = (scan_stats['sum'] / scan_stats['count'] * 100).round(1)
    scan_stats.columns = ['escaneados', 'total', 'pct_escaneados']
    print('  ' + scan_stats.to_string().replace('\n', '\n  '))

    print()
    print('  DENSIDAD TEXTUAL — PyMuPDF (documentos digitales):')
    df_dig = df[df['es_escaneado'] == False].dropna(subset=['pymupdf_text_density'])
    if not df_dig.empty:
        dens = (df_dig.groupby('category')[['pymupdf_blocks', 'pymupdf_text_density']]
                .agg(['mean', 'median']).round(3))
        print('  ' + dens.to_string().replace('\n', '\n  '))
    else:
        print('  (Sin documentos digitales con datos de densidad)')

    print()
    print('  TOKENS BPE (correccion x1.25 sobre heuristica):')
    tok_col = 'tokens_bpe_ajustado'
    df_tok = df.dropna(subset=[tok_col])
    if not df_tok.empty:
        for cat in df_tok['category'].unique():
            sub  = df_tok[df_tok['category'] == cat]
            med  = sub[tok_col].median()
            n_sup = sub['supera_limite_bpe'].sum()
            pct  = n_sup / len(sub) * 100
            flag = ' <- REQUIERE CHUNKING' if n_sup > 0 else ''
            print(f'    {cat:<22} mediana={med:.0f} tok | '
                  f'{n_sup}/{len(sub)} docs > {TOKENS_HARD_LIMIT}{flag}')

    print()
    print('  ESTRATEGIA DE CHUNKING (limite duro: BPE tokens > 1,800):')
    for cat in df['category'].dropna().unique():
        sub = df[df['category'] == cat].dropna(subset=[tok_col])
        if sub.empty:
            strat = 'sin_datos'
        else:
            med = sub[tok_col].median()
            if med > 2048:
                strat = 'layout_aware_opencv  (mediana BPE {:.0f} tok)'.format(med)
            elif sub['supera_limite_bpe'].mean() > 0.10:
                strat = 'sliding_window_30pct (mediana BPE {:.0f} tok)'.format(med)
            else:
                strat = 'sin_chunking         (mediana BPE {:.0f} tok)'.format(med)
        print(f'    {cat:<22} -> {strat}')

    # 4. Graficas
    print()
    print('[4/5] Generando graficas...')
    plot_distribucion(df)
    plot_scatter_calidad(df)
    plot_textometria(df)
    plot_densidad_layout(df)

    # 5. Exportar
    print()
    print('[5/5] Exportando artefactos...')
    EXPORT_COLS = [
        'filepath', 'filename', 'category', 'extension', 'size_kb',
        'md5', 'is_duplicate', 'quality_label',
        'brightness', 'contrast', 'blur_score', 'width_px', 'height_px',
        # Extraccion
        'extraccion_metodo', 'es_escaneado', 'lexicon_count',
        'pymupdf_blocks', 'pymupdf_text_density',
        # OCR fallback
        'ocr_lexicon_count', 'ocr_bbox_count', 'ocr_text_density', 'avg_confidence',
        # Tokens
        'tokens_heuristica', 'tokens_bpe_ajustado', 'supera_limite_bpe',
        'error',
    ]
    df_out = df[[c for c in EXPORT_COLS if c in df.columns]]
    report_path = DATA_PROC / 'quality_report.csv'
    df_out.to_csv(report_path, index=False, encoding='utf-8')
    print(f'  quality_report.csv -> {report_path}')

    # Decisiones
    ql         = df['quality_label'].value_counts().to_dict()
    total      = len(df)
    cat_counts = df['category'].value_counts().to_dict()
    mx, mn     = max(cat_counts.values()), min(cat_counts.values())

    n_escaneados = int(df['es_escaneado'].sum()) if 'es_escaneado' in df.columns else None

    chunking = {}
    for cat in df['category'].dropna().unique():
        sub = df[df['category'] == cat].dropna(subset=[tok_col])
        if sub.empty:
            chunking[cat] = {'mediana_tokens_bpe': None, 'estrategia': 'sin_datos',
                             'docs_superan_limite': 0}
        else:
            med   = sub[tok_col].median()
            n_sup = int(sub['supera_limite_bpe'].sum())
            if med > 2048:
                strat = 'layout_aware_opencv'
            elif n_sup / len(sub) > 0.10:
                strat = 'sliding_window_30pct'
            else:
                strat = 'sin_chunking'
            chunking[cat] = {
                'mediana_tokens_bpe':   int(med),
                'estrategia':           strat,
                'docs_superan_limite':  n_sup,
            }

    decisions = {
        'ocr_engine':      'easyocr_fallback_only',
        'pdf_engine':      'pymupdf_primario',
        'python_version':  '3.12',
        'bpe_correction':  BPE_CORRECTION,
        'tokens_hard_limit': TOKENS_HARD_LIMIT,
        'calidad_visual': {
            'distribucion':         ql,
            'pct_aptos':            round(ql.get('APTO', 0) / total * 100, 1),
            'pct_preprocesamiento': round(ql.get('REQUIERE_PREPROCESAMIENTO', 0) / total * 100, 1),
            'pct_descartados':      round(ql.get('DESCARTADO', 0) / total * 100, 1),
        },
        'escaneados': {
            'total':      n_escaneados,
            'pct_corpus': round(n_escaneados / total * 100, 1) if n_escaneados else None,
        },
        'chunking': chunking,
        'balance':  {
            'conteos':              cat_counts,
            'ratio':                round(mx / mn, 2),
            'requiere_augmentacion': (mx / mn) > 3,
        },
    }
    dec_path = DATA_PROC / 'fase1_decisiones.json'
    with open(dec_path, 'w', encoding='utf-8') as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)
    print(f'  fase1_decisiones.json -> {dec_path}')

    print()
    print('=' * 65)
    print('  RESUMEN EJECUTIVO')
    print('=' * 65)
    cv = decisions['calidad_visual']
    print(f'  Aptos                     : {cv["pct_aptos"]}%')
    print(f'  Requieren preprocesamiento: {cv["pct_preprocesamiento"]}%')
    print(f'  Descartados               : {cv["pct_descartados"]}%')
    if n_escaneados is not None:
        print(f'  Documentos escaneados     : {n_escaneados} ({decisions["escaneados"]["pct_corpus"]}%)')
    print(f'  Balance ratio             : {decisions["balance"]["ratio"]}:1')
    print()
    print('  ESTRATEGIA DE CHUNKING (BPE x1.25 | limite 1,800 tokens):')
    for cat, info in chunking.items():
        n_sup = info['docs_superan_limite']
        flag  = f' ({n_sup} docs superan limite)' if n_sup else ''
        print(f'    {cat:<22} -> {info["estrategia"]}{flag}')
    print()
    print('  FASE 1 COMPLETADA')
    print('  Siguiente: notebooks/02_preprocesamiento_pipeline.ipynb')
    print('=' * 65)


if __name__ == '__main__':
    main()
