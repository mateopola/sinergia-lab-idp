"""
SinergIA Lab — Fase 1 CRISP-DM++: Analisis Descriptivo del Corpus SECOP
========================================================================
Ejecutar desde la raiz del proyecto:
    python notebooks/run_fase1.py

Entorno: Python 3.12 (env_eda)
OCR:     EasyOCR 1.7+ — reemplaza PaddleOCR por incompatibilidad con Python 3.12
         PaddleOCR se usara en env_training (Python 3.10) para Fase 3.
         Decision documentada en PLAN_MODELADO_CRISPDM.md v1.2, seccion Notas de Entorno.
PDF:     PyMuPDF (fitz) — reemplaza pdf2image+Poppler (sin dependencias del sistema en Windows)
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
matplotlib.use('Agg')              # sin ventana emergente, guarda figuras a disco
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

CATEGORIES: Dict[str, Path] = {
    'Cedula':             DATA_RAW / 'cedulas',
    'RUT':                DATA_RAW / 'rut',
    'Poliza':             DATA_RAW / 'polizas',
    'Camara de Comercio': DATA_RAW / 'camara_comercio',
}

SUPPORTED_EXT = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.pdf'}

# ── Umbrales de calidad visual ─────────────────────────────────────────────────
# Calibrados para PDFs digitales nativos (fondo blanco real ~248-252 es NORMAL)
# v1.2: ajustados tras primera ejecucion — corpus SECOP son PDFs digitales, no escaneados
BLUR_THRESHOLD   = 100    # Varianza Laplaciana < umbral -> borroso
BRIGHTNESS_LOW   = 60     # < umbral -> muy oscuro (subexposicion real)
BRIGHTNESS_HIGH  = 253    # > umbral -> sobreexpuesto (255 = blanco puro absoluto)
CONTRAST_LOW     = 20     # < umbral -> texto indistinguible del fondo

PALETTE = {
    'Cedula':             '#4C72B0',
    'RUT':                '#DD8452',
    'Poliza':             '#55A868',
    'Camara de Comercio': '#C44E52',
}

sns.set_theme(style='whitegrid', palette='muted', font_scale=1.1)
plt.rcParams.update({'figure.dpi': 120})
np.random.seed(42)


# ── Inicializacion EasyOCR ────────────────────────────────────────────────────
print('Inicializando EasyOCR...')
print('  (Primera ejecucion: descarga modelos ~300MB. Las siguientes usan cache local.)')
try:
    import easyocr
    # gpu=False: CPU es suficiente para el EDA de 21 documentos
    # ['es','en']: español + ingles para cubrir siglas y formularios bilingues
    OCR = easyocr.Reader(['es', 'en'], gpu=False, verbose=False)
    OCR_OK = True
    print(f'  EasyOCR {easyocr.__version__} listo. [Python 3.12 compatible]')
except ImportError:
    OCR = None
    OCR_OK = False
    print('  ADVERTENCIA: EasyOCR no disponible.')
    print('  Instala con:  pip install easyocr')
    print('  token_count, bbox_count, text_density y avg_confidence quedaran en None.')


# ── Carga de imagen ───────────────────────────────────────────────────────────
def load_image(filepath: str) -> Optional[np.ndarray]:
    """
    Carga imagen o primera pagina de PDF.
    PyMuPDF (fitz) convierte PDFs sin depender de Poppler ni ghostscript.
    Retorna ndarray RGB o None si el archivo es ilegible.
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
    Tres metricas de calidad visual acordadas en revision arquitectural v1.1:
      brightness : luminosidad media (0-255). PDFs nativos tipicamente 220-252.
      contrast   : std de luminosidad. Bajo (<20) = texto/fondo indistinguibles.
      blur_score : varianza del Laplaciano. <100 = borroso, >500 = nitido.
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


# ── Textometria (EasyOCR) ─────────────────────────────────────────────────────
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


def run_easyocr(img_rgb: np.ndarray, reader) -> Dict:
    """
    EasyOCR retorna lista de: [bbox, text, confidence]
    donde bbox = [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]

    Metricas extraidas:
      token_count    : palabras / 0.75 (aproximacion estandar NLP)
      bbox_count     : bloques de texto detectados (proxy de densidad de layout)
      text_density   : area_texto_px / area_imagen_px
      avg_confidence : confianza promedio del OCR (0-1)
    """
    img_h, img_w = img_rgb.shape[:2]
    img_area = img_h * img_w

    results = reader.readtext(img_rgb)

    if not results:
        return {'token_count': 0, 'bbox_count': 0,
                'text_area_px': 0.0, 'text_density': 0.0, 'avg_confidence': 0.0}

    texts, confs, text_area = [], [], 0.0
    for (bbox, text, conf) in results:
        texts.append(text)
        confs.append(conf)
        text_area += bbox_area(bbox)

    word_count = len(' '.join(texts).split())
    return {
        'token_count':    int(word_count / 0.75),
        'bbox_count':     len(results),
        'text_area_px':   round(text_area, 1),
        'text_density':   round(text_area / img_area, 4) if img_area else 0.0,
        'avg_confidence': round(float(np.mean(confs)), 4),
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
                'filepath':     str(fp),
                'filename':     fp.name,
                'category':     cat,
                'extension':    fp.suffix.lower(),
                'size_kb':      round(fp.stat().st_size / 1024, 2),
                'md5':          compute_md5(fp),
            })
    df = pd.DataFrame(records)
    if not df.empty:
        df['is_duplicate'] = df.duplicated(subset='md5', keep='first')
    return df


# ── Pipeline por documento ────────────────────────────────────────────────────
def process_document(row: pd.Series) -> Dict:
    """
    Pipeline completo por documento con manejo de errores granular.
    Un archivo corrupto o ilegible no detiene el procesamiento del lote.
    El error se registra en la columna 'error' del reporte para trazabilidad.
    """
    result = {
        'filepath': row['filepath'], 'filename': row['filename'],
        'category': row['category'], 'extension': row['extension'],
        'size_kb':  row['size_kb'],  'md5': row['md5'],
        'is_duplicate': row.get('is_duplicate', False),
        'brightness': None, 'contrast': None, 'blur_score': None,
        'width_px': None,   'height_px': None, 'quality_label': 'ERROR',
        'token_count': None, 'bbox_count': None,
        'text_density': None, 'avg_confidence': None, 'error': None,
    }

    try:
        img = load_image(row['filepath'])
        if img is None:
            result['error'] = 'load_failed: imagen nula o formato no soportado'
            return result
    except Exception as e:
        result['error'] = f'load_exception: {type(e).__name__}: {e}'
        return result

    try:
        result.update(analyze_visual(img))
    except Exception as e:
        result['error'] = f'opencv_error: {type(e).__name__}: {e}'

    if OCR_OK and OCR is not None:
        try:
            result.update(run_easyocr(img, OCR))
        except Exception as e:
            msg = f'easyocr_error: {type(e).__name__}: {e}'
            result['error'] = (result['error'] + ' | ' + msg) if result['error'] else msg

    return result


# ── Visualizaciones ───────────────────────────────────────────────────────────
def plot_distribucion(df: pd.DataFrame):
    counts = df['category'].value_counts()
    colors = [PALETTE.get(c, '#888') for c in counts.index]
    ql_counts = df['quality_label'].value_counts()
    ql_colors_map = {'APTO': '#2ecc71', 'REQUIERE_PREPROCESAMIENTO': '#f39c12',
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
                colors=[ql_colors_map.get(l, '#bdc3c7') for l in ql_counts.index],
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

    ax.axhline(BLUR_THRESHOLD,   color='red',    linestyle='--', lw=1.2,
               label=f'Umbral blur ({BLUR_THRESHOLD})')
    ax.axvline(BRIGHTNESS_LOW,   color='orange', linestyle=':',  lw=1.2)
    ax.axvline(BRIGHTNESS_HIGH,  color='orange', linestyle=':',  lw=1.2,
               label=f'Rango brillo optimo ({BRIGHTNESS_LOW}-{BRIGHTNESS_HIGH})')
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
    df_t = df.dropna(subset=['token_count'])
    if df_t.empty:
        print('  (Sin datos de OCR — fig03 omitida)')
        return

    cat_order = df_t.groupby('category')['token_count'].median().sort_values().index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Textometria del Corpus — EasyOCR', fontsize=13, fontweight='bold')

    sns.violinplot(data=df_t, x='token_count', y='category', order=cat_order,
                   palette=PALETTE, inner='box', ax=axes[0])
    axes[0].axvline(512,  color='orange', linestyle='--', lw=1.2, label='512 tok')
    axes[0].axvline(2048, color='red',    linestyle='--', lw=1.2, label='2048 tok')
    axes[0].set_xlabel('Tokens aproximados (primera pagina)')
    axes[0].set_title('Distribucion de longitud textual')
    axes[0].legend(fontsize=8)

    for cat, color in PALETTE.items():
        sub = df_t[df_t['category'] == cat]
        axes[1].scatter(sub['token_count'], sub['avg_confidence'],
                        color=color, alpha=0.7, s=60, label=cat)
    axes[1].axhline(0.85, color='red', linestyle='--', lw=1, label='85% confianza')
    axes[1].set_xlabel('Tokens')
    axes[1].set_ylabel('Confianza promedio EasyOCR')
    axes[1].set_title('Tokens vs. Confianza OCR')
    axes[1].legend(fontsize=8)

    plt.tight_layout()
    out = DATA_PROC / 'fig03_textometria.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print()
    print('=' * 60)
    print('  FASE 1 CRISP-DM++ — SinergIA Lab')
    print('  OCR: EasyOCR (Python 3.12) | PDF: PyMuPDF')
    print('=' * 60)
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

    # 2. Pipeline
    print('[2/5] Analizando documentos (OpenCV + EasyOCR)...')
    if not OCR_OK:
        print('      [AVISO] EasyOCR no disponible — solo calidad visual.')
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
    print(('  ' + df['quality_label'].value_counts().to_string().replace('\n', '\n  ')))
    print()
    stats_vq = (df.groupby('category')[['brightness', 'contrast', 'blur_score']]
                .agg(['mean', 'std']).round(1))
    print('  METRICAS VISUALES POR TIPOLOGIA:')
    print(('  ' + stats_vq.to_string().replace('\n', '\n  ')))

    df_t = df.dropna(subset=['token_count'])
    if not df_t.empty:
        print()
        print('  TEXTOMETRIA (EasyOCR):')
        stats_txt = (df_t.groupby('category')
                     [['token_count', 'bbox_count', 'text_density', 'avg_confidence']]
                     .agg(['mean', 'median']).round(3))
        print(('  ' + stats_txt.to_string().replace('\n', '\n  ')))
        print()
        print('  CHUNKING RECOMENDADO (v1.1):')
        for cat in df_t['category'].unique():
            med = df_t[df_t['category'] == cat]['token_count'].median()
            if med > 2048:
                s = f'layout_aware_opencv  (mediana {med:.0f} tok)'
            elif med > 512:
                s = f'sliding_window_30pct (mediana {med:.0f} tok)'
            else:
                s = f'sin_chunking         (mediana {med:.0f} tok)'
            print(f'    {cat:<22} -> {s}')

    # 4. Graficas
    print()
    print('[4/5] Generando graficas...')
    plot_distribucion(df)
    plot_scatter_calidad(df)
    plot_textometria(df)

    # 5. Exportar
    print()
    print('[5/5] Exportando artefactos...')
    EXPORT_COLS = ['filepath', 'filename', 'category', 'extension', 'size_kb',
                   'md5', 'is_duplicate', 'brightness', 'contrast', 'blur_score',
                   'width_px', 'height_px', 'quality_label', 'token_count',
                   'bbox_count', 'text_density', 'avg_confidence', 'error']
    df_out = df[[c for c in EXPORT_COLS if c in df.columns]]
    report_path = DATA_PROC / 'quality_report.csv'
    df_out.to_csv(report_path, index=False, encoding='utf-8')
    print(f'  quality_report.csv -> {report_path}')

    # Decisiones
    ql    = df['quality_label'].value_counts().to_dict()
    total = len(df)
    cat_counts = df['category'].value_counts().to_dict()
    mx, mn = max(cat_counts.values()), min(cat_counts.values())

    chunking = {}
    for cat in df['category'].dropna().unique():
        med = df[df['category'] == cat]['token_count'].median()
        if pd.isna(med):
            strat = 'sin_datos_ocr'
        elif med > 2048:
            strat = 'layout_aware_opencv'
        elif med > 512:
            strat = 'sliding_window_30pct'
        else:
            strat = 'sin_chunking'
        chunking[cat] = {'mediana_tokens': None if pd.isna(med) else int(med),
                         'estrategia': strat}

    decisions = {
        'ocr_engine': 'easyocr',
        'pdf_engine': 'pymupdf',
        'python_version': '3.12',
        'calidad_visual': {
            'distribucion': ql,
            'pct_aptos':            round(ql.get('APTO', 0) / total * 100, 1),
            'pct_preprocesamiento': round(ql.get('REQUIERE_PREPROCESAMIENTO', 0) / total * 100, 1),
            'pct_descartados':      round(ql.get('DESCARTADO', 0) / total * 100, 1),
        },
        'chunking': chunking,
        'balance':  {'conteos': cat_counts, 'ratio': round(mx / mn, 2),
                     'requiere_augmentacion': (mx / mn) > 3},
        'calidad_ocr': {
            cat: round(float(df[df['category'] == cat]['avg_confidence'].mean()), 4)
            for cat in df['category'].dropna().unique()
            if not pd.isna(df[df['category'] == cat]['avg_confidence'].mean())
        },
    }
    dec_path = DATA_PROC / 'fase1_decisiones.json'
    with open(dec_path, 'w', encoding='utf-8') as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)
    print(f'  fase1_decisiones.json -> {dec_path}')

    print()
    print('=' * 60)
    print('  RESUMEN EJECUTIVO')
    print('=' * 60)
    cv = decisions['calidad_visual']
    print(f'  Aptos                    : {cv["pct_aptos"]}%')
    print(f'  Requieren preprocesamiento: {cv["pct_preprocesamiento"]}%')
    print(f'  Descartados              : {cv["pct_descartados"]}%')
    print(f'  Balance ratio            : {decisions["balance"]["ratio"]}:1')
    print()
    print('  ESTRATEGIA DE CHUNKING:')
    for cat, info in chunking.items():
        print(f'    {cat:<22} -> {info["estrategia"]}')
    print()
    print('  FASE 1 COMPLETADA')
    print('  Siguiente: notebooks/02_preprocesamiento_pipeline.ipynb')
    print('=' * 60)


if __name__ == '__main__':
    main()
