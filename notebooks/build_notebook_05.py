"""
Genera el notebook 05_ocr_corpus.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_05.py

Proposito:
    Aplicar EasyOCR (CPU) a las imagenes preprocesadas del Notebook 04, y
    extraer texto nativo via PyMuPDF para los PDFs digitales. Consolida todo
    en corpus_ocr.csv (1 fila por pagina) + corpus_ocr_summary.csv.

Contexto: Fase 2 CRISP-DM++ §2.1.1 — decision EasyOCR (ver OCR_BENCHMARK.md)

Estructura (M = markdown, C = code):
     1 M  Portada + objetivo
     2 M  Estrategia: OCR para escaneados, PyMuPDF para digitales
     3 M  Setup
     4 C  Imports + rutas + constantes
     5 M  Cargar manifest de imagenes + quality_report
     6 C  Cargar y unir
     7 M  Funciones — reconstruccion de texto desde bboxes
     8 C  reconstruir_texto + helper bboxes a JSON
     9 M  Funciones — extractores por motor
    10 C  EasyOCR sobre imagen procesada + PyMuPDF sobre PDF original
    11 M  Test sobre 3 paginas
    12 C  Test code
    13 M  Procesamiento masivo — bloques con checkpoint
    14 C  Loop principal con tqdm + skip-if-exists
    15 M  Consolidacion del CSV final + summary
    16 C  Unir bloques, generar corpus_ocr.csv + corpus_ocr_summary.csv
    17 M  Validacion contra gold seed
    18 C  Calcular CER + entity_recall sobre 15 docs del gold + comparar con benchmark
    19 M  Siguiente paso
"""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []

def md(src):   return nbf.v4.new_markdown_cell(src)
def code(src): return nbf.v4.new_code_cell(src)


# ══════════════════════════════════════════════════════════════════════════════
# 1. PORTADA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""# SinergIA Lab — OCR del Corpus
## Fase 2 CRISP-DM++ · §2.1 — Generacion de `corpus_ocr.csv`

---

### Proposito

Convertir todo el corpus en **texto extraible** y consolidarlo en un unico CSV (`corpus_ocr.csv`) que sera el insumo textual para:
- §2.2 Pre-anotaciones RUT (Labeling Functions sobre el texto)
- §2.3 Chunking por tipologia
- Fase 3 Fine-tuning del modelo NER

### Que produce este notebook

| Archivo | Contenido | En repo? |
|---|---|---|
| `data/processed/corpus_ocr.csv` | Texto + bboxes por pagina (1 fila por pagina) | ❌ (PII) |
| `data/processed/corpus_ocr_summary.csv` | Metricas por pagina sin texto | ✅ |
| `data/processed/ocr_blocks/` | CSVs intermedios de checkpoint | ❌ |

### Dependencia previa

⚠️ **Requiere haber ejecutado el Notebook 04** primero. Este notebook lee `data/processed/image_manifest.csv` para saber que paginas estan listas para OCR.

### Tiempo estimado

- Modo prueba (10 docs): ~5 min
- Corrida completa (~5,000 paginas): **~10-20 horas** en CPU (overnight)
- Retomable: si se interrumpe, al re-ejecutar continua desde donde quedo
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. ESTRATEGIA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Estrategia: dos motores segun tipo de documento

| Tipo | Motor | Por que |
|---|---|---|
| Escaneado (`es_escaneado=True`) | **EasyOCR (CPU)** | El texto esta como pixeles, requiere OCR. Decision del benchmark §2.1.1. |
| Digital (`es_escaneado=False`) | **PyMuPDF** | El texto esta como caracteres en el PDF. Extraccion instantanea y 100% precisa. |

**Por que NO aplicar OCR a los digitales:** seria desperdiciar tiempo y degradar texto perfecto. Un PDF digital tiene los caracteres reales — al renderizarlo a imagen y luego OCR'rlo, introducimos errores que no existen.

**Por que NO usar EasyOCR sobre la imagen RAW del escaneado:** el preprocesamiento (deskew, denoise, CLAHE, binarize) del Notebook 04 limpia la imagen, lo que mejora la precision del OCR. Esa es la motivacion de tener dos notebooks separados.

**Aclaracion sobre Tesseract:** aunque en el benchmark §2.1.1 Tesseract gano en Polizas y CC, la decision documentada (`OCR_BENCHMARK.md`) fue **EasyOCR unificado con GPU** o **selector hibrido en CPU**. Aqui usamos EasyOCR para todo lo escaneado por simplicidad y consistencia, asumiendo acceso a GPU en el mediano plazo. Si manana se requiere selector hibrido, basta con anadir una rama `if folder == 'CEDULA': easyocr else: tesseract` en `procesar_pagina`.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 3. SETUP
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Configuracion inicial

Importamos librerias, fijamos rutas, definimos constantes.
"""))

cells.append(code("""import json
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import cv2
import easyocr
import fitz  # PyMuPDF
import numpy as np
import pandas as pd
from tqdm import tqdm

# Rutas del proyecto
PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
DATA_GOLD    = PROJECT_ROOT / 'data' / 'gold'
IMAGES_DIR   = DATA_PROC / 'images'
OCR_BLOCKS_DIR = DATA_PROC / 'ocr_blocks'
OCR_BLOCKS_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_MANIFEST   = DATA_PROC / 'image_manifest.csv'
QUALITY_REPORT   = DATA_PROC / 'quality_report_completo.csv'
CORPUS_OCR_CSV   = DATA_PROC / 'corpus_ocr.csv'
CORPUS_SUMMARY   = DATA_PROC / 'corpus_ocr_summary.csv'
OCR_PROCESSED_LOG = OCR_BLOCKS_DIR / 'ocr_processed_log.csv'

# Constantes
EASYOCR_LANGS    = ['es']
EASYOCR_GPU      = False     # CPU mode
EASYOCR_VERSION  = easyocr.__version__
BLOCK_SIZE       = 25        # paginas por bloque (mas pequeno que nb 04 porque cada pagina toma mas tiempo)
FORCE_REPROCESS  = False     # True = reprocesa todas las paginas

# Verificar prerequisito
if not IMAGE_MANIFEST.exists():
    raise FileNotFoundError(
        f'Falta {IMAGE_MANIFEST}. Ejecuta primero el Notebook 04.')

print(f'Rutas OK.')
print(f'  Manifest entrada: {IMAGE_MANIFEST}')
print(f'  Salida final:     {CORPUS_OCR_CSV}')
print(f'  Bloques:          {OCR_BLOCKS_DIR}')
print(f'  EasyOCR version:  {EASYOCR_VERSION}  (GPU={EASYOCR_GPU})')
print(f'  BLOCK_SIZE={BLOCK_SIZE}  FORCE_REPROCESS={FORCE_REPROCESS}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGAR MANIFEST
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Cargar manifest de imagenes + metadata del corpus

Combinamos:
- `image_manifest.csv` (output del Notebook 04) — una fila por pagina con la ruta a la imagen procesada
- `quality_report_completo.csv` (Fase 1) — solo necesitamos `local_path` actualizada del PDF original (para PyMuPDF en digitales)
"""))

cells.append(code("""img_manifest = pd.read_csv(IMAGE_MANIFEST, encoding='utf-8-sig')
print(f'image_manifest: {len(img_manifest)} filas (paginas preprocesadas)')

# Resolver ruta del PDF original via MD5 (algunos pueden haberse movido entre carpetas)
import hashlib
def md5_file(path):
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

print('Indexando data/raw/ por MD5...')
md5_index = {md5_file(p): p for p in DATA_RAW.rglob('*.pdf')}
print(f'  {len(md5_index)} PDFs indexados')

img_manifest['pdf_path'] = img_manifest['md5'].map(lambda h: str(md5_index.get(h, '')))
faltantes = (img_manifest['pdf_path'] == '').sum()
if faltantes:
    print(f'  ⚠ {faltantes} paginas sin PDF en disco — se excluyen')
    img_manifest = img_manifest[img_manifest['pdf_path'] != ''].reset_index(drop=True)

# Excluir paginas con error en el preprocesamiento (sin imagen procesada)
img_manifest = img_manifest[img_manifest['ruta_imagen_procesada'].notna()].reset_index(drop=True)
print(f'Paginas listas para OCR: {len(img_manifest)}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. RECONSTRUIR TEXTO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Reconstruccion de texto desde bounding boxes

EasyOCR devuelve una lista de detecciones `[(bbox, text, confidence), ...]`. Cada `bbox` es un poligono con 4 esquinas. **El orden de las detecciones no es el orden natural de lectura** — viene en el orden interno del modelo (aproximadamente arriba-a-abajo pero con saltos).

Para reconstruir un texto legible:
1. Calcular el centro Y de cada bbox.
2. Agrupar detecciones en **lineas** segun proximidad de Y (toleramos hasta 50% del alto medio).
3. Dentro de cada linea, ordenar por X.
4. Concatenar lineas con `\\n`.

Esto preserva la estructura del documento (las lineas separadas son saltos de linea) y respeta el orden de columnas dentro de cada linea.
"""))

cells.append(code("""def _bbox_center_y(bbox):
    return float(np.mean([p[1] for p in bbox]))

def _bbox_left_x(bbox):
    return float(min(p[0] for p in bbox))

def _bbox_height(bbox):
    ys = [p[1] for p in bbox]
    return float(max(ys) - min(ys))

def reconstruir_texto(detections) -> str:
    \"\"\"
    detections: lista de (bbox, text, confidence) de easyocr.readtext

    Devuelve string con saltos de linea entre lineas y espacios entre tokens.
    \"\"\"
    if not detections:
        return ''
    items = []
    for bbox, text, conf in detections:
        items.append({
            'cy': _bbox_center_y(bbox),
            'lx': _bbox_left_x(bbox),
            'h':  _bbox_height(bbox),
            'text': text,
        })
    # Orden inicial por Y
    items.sort(key=lambda it: it['cy'])

    # Tolerancia para considerar misma linea: 50% de la altura mediana
    median_h = float(np.median([it['h'] for it in items])) if items else 1.0
    tol = max(median_h * 0.5, 5.0)

    # Agrupar en lineas
    lineas = []
    actual = [items[0]]
    actual_y = items[0]['cy']
    for it in items[1:]:
        if abs(it['cy'] - actual_y) <= tol:
            actual.append(it)
        else:
            lineas.append(actual)
            actual = [it]
            actual_y = it['cy']
    lineas.append(actual)

    # Dentro de cada linea, orden por X y unir con espacio
    out_lines = []
    for ln in lineas:
        ln.sort(key=lambda it: it['lx'])
        out_lines.append(' '.join(it['text'] for it in ln))

    return '\\n'.join(out_lines)


def detections_a_json(detections) -> str:
    \"\"\"Serializa las detecciones (bbox + text + confidence) como JSON string.\"\"\"
    payload = []
    for bbox, text, conf in detections:
        payload.append({
            'bbox': [[float(x), float(y)] for x, y in bbox],
            'text': text,
            'confidence': float(conf),
        })
    return json.dumps(payload, ensure_ascii=False)

print('Funciones de reconstruccion listas.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. EXTRACTORES POR MOTOR
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Extractores: EasyOCR para escaneados, PyMuPDF para digitales

Dos funciones con la misma firma `(image_path, pdf_path, page_num) -> dict`. La funcion principal `extraer_pagina` decide cual usar segun `es_escaneado`.

**EasyOCR:** carga el modelo una sola vez (`easyocr.Reader`) — la primera ejecucion descarga ~60 MB de pesos del modelo de espanol.

**PyMuPDF:** abre el PDF y llama a `page.get_text()` que devuelve el texto en orden de lectura nativo del PDF.
"""))

cells.append(code("""# Cargar EasyOCR una sola vez (lazy: la primera ejecucion descarga modelos)
print('Cargando EasyOCR (la primera vez descarga ~60 MB de pesos)...')
reader = easyocr.Reader(EASYOCR_LANGS, gpu=EASYOCR_GPU, verbose=False)
print('EasyOCR listo.')

def extraer_easyocr(image_path: Path) -> dict:
    \"\"\"OCR sobre imagen procesada. Devuelve dict con texto, bboxes y metricas.\"\"\"
    t0 = time.perf_counter()
    img = cv2.imread(str(image_path))
    if img is None:
        raise IOError(f'No se pudo leer la imagen: {image_path}')
    detections = reader.readtext(img)
    elapsed = time.perf_counter() - t0
    return {
        'engine':         'easyocr',
        'engine_version': EASYOCR_VERSION,
        'gpu_used':       EASYOCR_GPU,
        'texto_ocr':      reconstruir_texto(detections),
        'bboxes_json':    detections_a_json(detections),
        'n_detections':   len(detections),
        'elapsed_s':      round(elapsed, 3),
    }


def extraer_pymupdf(pdf_path: Path, page_num: int) -> dict:
    \"\"\"Extraccion nativa de texto del PDF. Usado para digitales.\"\"\"
    t0 = time.perf_counter()
    doc = fitz.open(str(pdf_path))
    try:
        page = doc[page_num - 1]
        texto = page.get_text('text')   # texto en orden natural de lectura
    finally:
        doc.close()
    elapsed = time.perf_counter() - t0
    return {
        'engine':         'pymupdf',
        'engine_version': fitz.__version__,
        'gpu_used':       False,
        'texto_ocr':      texto,
        'bboxes_json':    None,
        'n_detections':   0,
        'elapsed_s':      round(elapsed, 3),
    }


def extraer_pagina(row) -> dict:
    \"\"\"Decide motor y ejecuta. Captura errores como string.\"\"\"
    base = {
        'md5':            row['md5'],
        'doc_id':         row['md5'],
        'filename':       row['filename'],
        'folder':         row['folder'],
        'page_num':       int(row['page_num']),
        'timestamp':      datetime.now(timezone.utc).isoformat(),
        'error':          None,
    }
    try:
        if bool(row['es_escaneado']):
            res = extraer_easyocr(Path(row['ruta_imagen_procesada']))
        else:
            res = extraer_pymupdf(Path(row['pdf_path']), int(row['page_num']))
        base.update(res)
        base['text_chars'] = len(base['texto_ocr'])
    except Exception as e:
        base.update({
            'engine':         None,
            'engine_version': None,
            'gpu_used':       None,
            'texto_ocr':      None,
            'bboxes_json':    None,
            'n_detections':   None,
            'elapsed_s':      None,
            'text_chars':     None,
            'error':          f'{type(e).__name__}: {e}',
        })
    return base
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. TEST SOBRE 3 PAGINAS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Test sobre 3 paginas — sanity check antes de la corrida masiva

Procesamos 3 paginas (1 escaneada + 1 digital + 1 random) y mostramos el primer fragmento del texto extraido. Si esto se ve coherente, lanzamos la corrida completa con confianza.
"""))

cells.append(code("""samples = []
# 1 escaneada
sub = img_manifest[img_manifest['es_escaneado'] == True].head(1)
if len(sub): samples.append(('Escaneada (EasyOCR)', sub.iloc[0]))
# 1 digital
sub = img_manifest[img_manifest['es_escaneado'] == False].head(1)
if len(sub): samples.append(('Digital (PyMuPDF)', sub.iloc[0]))
# 1 random adicional
samples.append(('Random', img_manifest.sample(n=1, random_state=42).iloc[0]))

for label, row in samples:
    print(f'\\n=== {label} ===')
    print(f'  filename: {row[\"filename\"]}  pag {row[\"page_num\"]}/{row[\"n_pages_total\"]}')
    res = extraer_pagina(row)
    if res['error']:
        print(f'  ERROR: {res[\"error\"]}')
    else:
        print(f'  engine: {res[\"engine\"]}  detecciones: {res[\"n_detections\"]}  tiempo: {res[\"elapsed_s\"]}s  chars: {res[\"text_chars\"]}')
        print(f'  primeros 300 chars del texto:')
        print('  ' + (res['texto_ocr'][:300] or '(vacio)').replace('\\n', '\\n  '))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. PROCESAMIENTO MASIVO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Procesamiento masivo — bloques con checkpoint

Mismo patron que el Notebook 04:
- Bloques de `BLOCK_SIZE` (default 25, mas chico porque cada OCR toma mas tiempo)
- CSV parcial por bloque en `data/processed/ocr_blocks/`
- Log de paginas procesadas en `ocr_processed_log.csv`
- Detecta paginas ya procesadas (en log) y las salta — permite reanudar tras interrupciones
- Errores capturados por pagina, no abortan la corrida
"""))

cells.append(code("""# Detectar paginas ya procesadas en bloques previos
processed_keys = set()
if not FORCE_REPROCESS and OCR_PROCESSED_LOG.exists():
    log_df = pd.read_csv(OCR_PROCESSED_LOG, encoding='utf-8-sig')
    processed_keys = {(r['md5'], int(r['page_num'])) for _, r in log_df.iterrows()}
    print(f'Paginas ya procesadas (cache): {len(processed_keys)}')

img_manifest['key'] = list(zip(img_manifest['md5'], img_manifest['page_num']))
pending = img_manifest[~img_manifest['key'].isin(processed_keys)].drop(columns='key').reset_index(drop=True)
print(f'Paginas pendientes: {len(pending)}')

if len(pending) == 0:
    print('Nada que procesar. Todas las paginas ya tienen OCR en cache.')
else:
    num_blocks = (len(pending) + BLOCK_SIZE - 1) // BLOCK_SIZE
    print(f'Procesando en {num_blocks} bloques de {BLOCK_SIZE}...')

    # Numerar bloques continuando desde los existentes para NO sobreescribir.
    existing_blocks = sorted(OCR_BLOCKS_DIR.glob('ocr_bloque_*.csv'))
    next_block_num = 1
    if existing_blocks:
        last = int(existing_blocks[-1].stem.split('_')[-1])
        next_block_num = last + 1
        print(f'  Bloques existentes: {len(existing_blocks)}  ->  continuando desde bloque {next_block_num:04d}')

    accumulated = []  # solo para log; los datos van al CSV de bloque
    if OCR_PROCESSED_LOG.exists():
        accumulated = pd.read_csv(OCR_PROCESSED_LOG, encoding='utf-8-sig').to_dict('records')

    with tqdm(total=len(pending), desc='OCR paginas') as pbar:
        for bk in range(num_blocks):
            start = bk * BLOCK_SIZE
            end   = min(start + BLOCK_SIZE, len(pending))
            block = pending.iloc[start:end]

            block_results = []
            for _, row in block.iterrows():
                res = extraer_pagina(row)
                block_results.append(res)
                accumulated.append({'md5': res['md5'], 'page_num': res['page_num']})
                pbar.update(1)

            # Bloque con id continuo, nunca sobreescribe previos
            bk_id = next_block_num + bk
            ruta_bloque = OCR_BLOCKS_DIR / f'ocr_bloque_{bk_id:04d}.csv'
            pd.DataFrame(block_results).to_csv(ruta_bloque, index=False, encoding='utf-8-sig')
            # Actualizar log
            pd.DataFrame(accumulated).drop_duplicates().to_csv(
                OCR_PROCESSED_LOG, index=False, encoding='utf-8-sig')

    print(f'\\nCorrida completa.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 9. CONSOLIDACION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Consolidacion — `corpus_ocr.csv` y `corpus_ocr_summary.csv`

Unimos todos los CSVs de bloque, deduplicamos por (md5, page_num) tomando el timestamp mas reciente, y producimos:

- **`corpus_ocr.csv`** — datos completos (incluye `texto_ocr` y `bboxes_json`). NO se commitea (PII).
- **`corpus_ocr_summary.csv`** — sin `texto_ocr` ni `bboxes_json`. SI se commitea (auditoria sin exponer texto).
"""))

cells.append(code("""block_files = sorted(OCR_BLOCKS_DIR.glob('ocr_bloque_*.csv'))
print(f'Bloques OCR encontrados: {len(block_files)}')

if not block_files:
    print('No hay bloques. ¿Se ejecuto el loop de procesamiento?')
    corpus_ocr = pd.DataFrame()
else:
    dfs = [pd.read_csv(f, encoding='utf-8-sig') for f in block_files]
    corpus_ocr = pd.concat(dfs, ignore_index=True)

    # Dedup por (md5, page_num) tomando timestamp mas reciente
    corpus_ocr = (corpus_ocr
                  .sort_values('timestamp')
                  .drop_duplicates(subset=['md5', 'page_num'], keep='last')
                  .reset_index(drop=True))

    # Reordenar columnas
    cols = ['md5', 'doc_id', 'filename', 'folder', 'page_num',
            'engine', 'engine_version', 'gpu_used',
            'texto_ocr', 'bboxes_json', 'n_detections', 'text_chars',
            'elapsed_s', 'timestamp', 'error']
    corpus_ocr = corpus_ocr[[c for c in cols if c in corpus_ocr.columns]]

    corpus_ocr.to_csv(CORPUS_OCR_CSV, index=False, encoding='utf-8-sig')
    print(f'corpus_ocr.csv:   {len(corpus_ocr)} filas -> {CORPUS_OCR_CSV}')
    size_mb = CORPUS_OCR_CSV.stat().st_size / 1024 / 1024
    print(f'  tamano: {size_mb:.1f} MB')

    # Summary sin texto ni bboxes
    summary = corpus_ocr.drop(columns=['texto_ocr', 'bboxes_json'])
    summary.to_csv(CORPUS_SUMMARY, index=False, encoding='utf-8-sig')
    print(f'corpus_ocr_summary.csv: {len(summary)} filas -> {CORPUS_SUMMARY}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 10. VALIDACION CONTRA GOLD SEED
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Validacion contra gold seed (15 docs con transcripciones humanas)

Los 15 docs del gold seed tienen transcripcion humana en `data/gold/transcriptions/{md5}.txt`. Comparamos:

1. El OCR de las primeras N paginas de cada gold-doc (consolidado a un solo string por doc).
2. Contra la transcripcion humana del archivo `.txt`.

Calculamos:
- **CER** (Character Error Rate) — debe ser comparable al benchmark (EasyOCR CPU ~0.276 medio)
- **entity_recall** — fraccion de NIT/cedula/fecha/monto del GT presentes en el OCR

Si los valores caen muy por debajo de los del benchmark, algo cambio en el pipeline (preprocesamiento adicional vs OCR sobre PDF directo). Tolerancia: ±10%.
"""))

cells.append(code("""GOLD_MANIFEST_PATH = DATA_GOLD / 'gold_seed_manifest.csv'
TRANSCRIPTIONS_DIR = DATA_GOLD / 'transcriptions'

if not GOLD_MANIFEST_PATH.exists() or len(corpus_ocr) == 0:
    print('No hay gold seed o corpus_ocr vacio. Saltando validacion.')
else:
    try:
        import jiwer
    except ImportError:
        print('jiwer no instalado. pip install jiwer para validacion. Saltando.')
        jiwer = None

    if jiwer is not None:
        gold = pd.read_csv(GOLD_MANIFEST_PATH, encoding='utf-8-sig')

        ENTITY_PATTERNS = {
            'nit':    re.compile(r'\\b\\d{8,10}[-\\s]?\\d\\b'),
            'cedula': re.compile(r'\\b\\d{1,3}(?:[.\\s]\\d{3}){2,3}\\b'),
            'fecha':  re.compile(r'\\b\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}\\b'),
            'monto':  re.compile(r'\\$\\s?\\d{1,3}(?:[.,]\\d{3})+(?:[.,]\\d{1,2})?'),
        }

        def normalize(t):
            return re.sub(r'\\s+', ' ', (t or '').lower()).strip()

        def cer(ref, hyp):
            r, h = normalize(ref), normalize(hyp)
            if not r:
                return 0.0 if not h else 1.0
            return jiwer.cer(r, h)

        def entity_recall(ref, hyp):
            total_ref = total_hit = 0
            hyp_norm = normalize(hyp)
            for pat in ENTITY_PATTERNS.values():
                ref_hits = {m.group(0) for m in pat.finditer(ref or '')}
                hyp_hits = {m.group(0) for m in pat.finditer(hyp or '')}
                hyp_hits_norm = {m.group(0) for m in pat.finditer(hyp_norm)}
                total_ref += len(ref_hits)
                total_hit += sum(1 for e in ref_hits if e in hyp_hits or e.lower() in hyp_hits_norm)
            return (total_hit / total_ref) if total_ref else 0.0

        rows = []
        for _, g in gold.iterrows():
            tpath = TRANSCRIPTIONS_DIR / f'{g[\"md5\"]}.txt'
            if not tpath.exists():
                continue
            ref_raw = tpath.read_text(encoding='utf-8')
            # limpiar comentarios del template
            ref = re.sub(r'^#.*', '', ref_raw, flags=re.MULTILINE)
            ref = ref.replace('<<< INICIO DE LA TRANSCRIPCION', '').strip()

            # Concatenar texto OCR de las paginas que estan en el gold (1 hasta pages_to_use)
            cap = int(g.get('pages_to_use', g['n_pages']))
            sub = corpus_ocr[(corpus_ocr['md5'] == g['md5']) & (corpus_ocr['page_num'] <= cap)]
            if len(sub) == 0:
                continue
            hyp = '\\n\\n'.join(sub.sort_values('page_num')['texto_ocr'].fillna('').tolist())

            rows.append({
                'folder':        g['folder'],
                'filename':      g['filename'],
                'pages_used':    int(cap),
                'cer':           round(cer(ref, hyp), 4),
                'entity_recall': round(entity_recall(ref, hyp), 4),
                'ref_chars':     len(ref),
                'hyp_chars':     len(hyp),
            })
        val = pd.DataFrame(rows)
        if len(val):
            print('Validacion contra gold seed (15 docs):')
            print(val.to_string(index=False))
            print()
            print('Resumen por tipologia:')
            print(val.groupby('folder').agg(
                n=('filename','count'),
                cer_mean=('cer','mean'),
                entity_recall_mean=('entity_recall','mean'),
            ).round(4).to_string())
            print()
            print(f'CER medio global:           {val[\"cer\"].mean():.4f}  (benchmark EasyOCR CPU ≈ 0.276)')
            print(f'Entity recall medio global: {val[\"entity_recall\"].mean():.4f}  (benchmark ≈ 0.55)')
        else:
            print('No se pudo calcular validacion: sin docs gold con OCR.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 11. SIGUIENTE PASO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Siguiente paso

Con `corpus_ocr.csv` generado y validado, lo siguiente es **§2.2 — Pre-anotaciones RUT**:

1. Cargar `corpus_ocr.csv` y filtrar `folder == 'rut'`.
2. Para cada RUT, aplicar las Labeling Functions ya implementadas en `src/preprocessing/pipeline.py` (`extraer_entidades_rut`).
3. Generar pre-anotaciones JSON para los 235 RUTs.
4. Cargar a Label Studio para revision humana (corregir, no anotar desde cero).

**Para retomar la corrida:** si el notebook se interrumpe (Ctrl+C, kernel muerto, etc.), simplemente vuelve a ejecutar todas las celdas. La logica de cache `processed_keys` salta lo ya hecho.

**Para forzar reprocesamiento:** cambia `FORCE_REPROCESS = True` en la celda de setup.

**Artefactos producidos:**

| Archivo | Ubicacion | En repo? |
|---|---|---|
| `corpus_ocr.csv` | `data/processed/` | ❌ (PII) |
| `corpus_ocr_summary.csv` | `data/processed/` | ✅ |
| Bloques intermedios | `data/processed/ocr_blocks/` | ❌ |

**Recordatorio:** este notebook cierra §2.1 del plan maestro. Tras validar, marcar como completado y avanzar a §2.2.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# ESCRIBIR NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out_path = Path(__file__).parent / '05_ocr_corpus.ipynb'
nbf.write(nb, out_path)
print(f'Notebook generado: {out_path}  ({len(cells)} celdas)')
