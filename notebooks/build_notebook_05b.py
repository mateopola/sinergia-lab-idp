"""
Genera el notebook 05b_cierre_gaps_ocr.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_05b.py

Proposito:
    Cerrar los dos gaps de cobertura detectados tras la corrida productiva del
    Notebook 05 (ver OCR_BENCHMARK.md §2.6.2 y PLAN_MODELADO_CRISPDM.md §2.1.4):

    - GAP 1: 9 archivos .jpg/.jpeg escaneados excluidos por un filtro restrictivo.
             Se procesan con EasyOCR igual que los PDFs escaneados.
    - GAP 2: 548 PDFs digitales que nunca entraron al pipeline.
             Se procesan con PyMuPDF (decision del plan §1.2).

    Tras cerrar ambos gaps, se reconstruye corpus_ocr.csv + summary y se
    re-valida contra el gold seed de 15 documentos.

Contexto academico: este notebook es insumo del documento final del proyecto.
Cada celda markdown explica que se hace, por que, y como se valida.

Estructura (M = markdown, C = code):
     1 M  Portada + contexto de los gaps detectados
     2 M  Diagnostico detallado de cada gap
     3 M  Estrategia de cierre
     4 M  Setup
     5 C  Imports + rutas + constantes
     6 M  Inventario inicial: estado del corpus_ocr.csv
     7 C  Cargar corpus_ocr actual + detectar docs faltantes
     8 M  === PARTE A === 9 imagenes directas via EasyOCR
     9 C  Cargar EasyOCR + procesar las 9 paginas pendientes
    10 M  === PARTE B === 548 digitales via PyMuPDF
    11 C  Identificar digitales + extraer con PyMuPDF
    12 M  Consolidacion: merge con corpus_ocr.csv previo
    13 C  Concatenar + regenerar summary + backup del anterior
    14 M  Validacion: re-medir contra gold seed
    15 C  Recalcular CER + entity_recall ahora con el corpus completo
    16 M  Cierre Fase 2 §2.1
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
cells.append(md("""# SinergIA Lab — Cierre de Gaps OCR
## Fase 2 CRISP-DM++ · §2.1.4 — Completar `corpus_ocr.csv`

---

### Contexto

El Notebook 05 corrio overnight el 2026-04-17/18 y genero `corpus_ocr.csv` con **1,669 paginas / 403 documentos**. Al analizar la cobertura contra `quality_report_completo.csv` (1,014 docs del corpus Fase 1) se detectaron dos gaps:

| Gap | Documentos | Causa raiz | Solucion |
|---|---|---|---|
| **A** — 9 archivos `.jpg`/`.jpeg` escaneados | 9 | El nb 05 filtra filas cuyo MD5 no existe como `.pdf` en `data/raw/` | EasyOCR sobre imagen preprocesada (ya existen en disco) |
| **B** — ~590 PDFs digitales (12,415 paginas) | ~590 | El nb 04 solo procesa escaneados; el nb 05 itera sobre el manifest que resulta de nb 04 → los digitales nunca entran | PyMuPDF `page.get_text()` directo sobre PDF original |

### Lo que produce este notebook

| Archivo | Descripcion | Commiteable? |
|---|---|---|
| `data/processed/corpus_ocr.csv` | Texto del corpus **completo** (1,014 docs) | ❌ (PII) |
| `data/processed/corpus_ocr_summary.csv` | Metricas sin texto del corpus completo | ✅ |
| `data/processed/corpus_ocr_preV2_backup.csv` | Respaldo del CSV previo antes de merge | ❌ |
| `data/gold/ocr_corpus_validation.csv` | Validacion actualizada contra gold seed | ✅ |

### Tiempo estimado

| Parte | Tiempo |
|---|---|
| Parte A — 9 imagenes via EasyOCR | ~8 min |
| Parte B — ~590 docs / 12,415 paginas via PyMuPDF | ~8-15 min (depende del disco) |
| Indexado MD5 de `data/raw/` (+consolidacion + validacion) | ~2 min |
| **Total** | **~20-25 min** |

### Importancia para el documento final

Este paso cierra la **cobertura del corpus** — insumo critico para §2.2 (anotaciones) y Fase 3 (fine-tuning). Sin cerrar estos gaps, el 54% del corpus (los 548 digitales) quedaria fuera del entrenamiento, reduciendo drasticamente el tamaño efectivo del dataset.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. DIAGNOSTICO DETALLADO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Diagnostico detallado de los gaps

### Gap A — 9 imagenes directas

El SECOP incluye 9 documentos entregados como imagen (`.jpg`/`.jpeg`) en vez de PDF. El pipeline Fase 1 los indexo correctamente, el nb 04 los preproceso correctamente (estan en `data/processed/images/` con nombre `processed_{md5}_page_1.jpg`), pero el nb 05 los filtro en esta linea:

```python
md5_index = {md5_file(p): p for p in DATA_RAW.rglob('*.pdf')}   # ← solo PDFs
img_manifest['pdf_path'] = img_manifest['md5'].map(lambda h: str(md5_index.get(h, '')))
img_manifest = img_manifest[img_manifest['pdf_path'] != '']     # ← excluye no-PDFs
```

**Archivos afectados:**

| Folder | Filename | MD5 |
|---|---|---|
| CEDULA | CEDULA (1).jpeg, CEDULA (2).jpeg, CEDULA SINDY VARGAS.jpg, CEDULA ZAMIR.jpg, Copia de CEDULA.jpeg | 5 docs |
| rut | RUT 1.jpg, RUT ZAMIR MORENO.jpg | 2 docs |
| OTROS | TP (1).jpeg, TP (2).jpeg | 2 docs |

**Fix:** no requieren `pdf_path` porque son escaneados (usan `ruta_imagen_procesada`). Los procesamos aqui directamente con EasyOCR.

### Gap B — ~590 PDFs digitales (verificado empiricamente: 590 docs / 12,415 paginas)

El nb 04 aplico el filtro `es_escaneado=True` deliberadamente (decision v1.7 del plan: ahorro de 12 GB de disco). Esto significa que el `image_manifest.csv` solo contiene paginas escaneadas. El nb 05 itera ese manifest, y aunque implemento la funcion `extraer_pymupdf()` para digitales, esa rama **nunca se invoca** porque no hay digitales en el manifest.

**Composicion de los digitales (verificado empiricamente — cruzando `quality_report_completo.csv` vs `image_manifest.csv`):**

| Folder (`category` en QR) | Docs | Paginas |
|---|---|---|
| Camara de Comercio | 185 | 2,993 |
| RUT | 193 | 3,640 |
| Poliza | 145 | 1,918 |
| Cedula | 21 | 60 |
| Otros | 9 | 3,804 |
| **Total** | **~590** | **~12,415** |

> La cifra exacta puede variar ±2 por documentos con `n_pages=0` (corruptos) que se filtran en runtime.

**Fix:** iterar `quality_report_completo.csv` sobre los docs NO presentes en el manifest, abrirlos con `fitz.open()` y extraer texto nativo con `page.get_text('text')`. PyMuPDF es determinista e instantaneo (<50 ms/pagina).
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 3. ESTRATEGIA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Estrategia de cierre

```
┌─────────────────────────────────────────────────────────────┐
│  Input:   corpus_ocr.csv (1,669 paginas) + quality_report   │
│                                                              │
│  Parte A: 9 imagenes  ──► EasyOCR  ──► 9 filas              │
│  Parte B: 548 PDFs    ──► PyMuPDF  ──► ~N filas             │
│                                                              │
│  Merge:   corpus_ocr.csv + nuevas filas                     │
│                                                              │
│  Output:  corpus_ocr.csv v2 (completo) + summary + backup   │
│  Validar: CER + entity_recall contra gold seed              │
└─────────────────────────────────────────────────────────────┘
```

**Principios del merge:**
1. **No sobrescribir** lo que ya esta — si una `(md5, page_num)` ya existe, se conserva.
2. **Backup antes de pisar** — `corpus_ocr_preV2_backup.csv` se crea antes de escribir el nuevo corpus.
3. **Schema identico** — mismas columnas, mismo tipo, para que consumers downstream no rompan.
4. **Columna `engine`** permite trazabilidad: `easyocr` para escaneados, `pymupdf` para digitales.

**Metricas esperadas tras el cierre:**
- Docs totales: 1,014 (baseline Fase 1) menos los corruptos (pages=0) y duplicados
- Paginas totales: suma de paginas por doc validado
- Entity recall sobre gold: no debe cambiar el valor de los 15 docs (todos escaneados)
- Si aparecen digitales en el gold en el futuro: esperamos CER ≈ 0 (PyMuPDF es exacto)
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. SETUP
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Setup — imports, rutas, constantes"""))

cells.append(code("""import json
import re
import sys
import time
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import cv2
import easyocr
import fitz                     # PyMuPDF
import numpy as np
import pandas as pd
from tqdm import tqdm
from jiwer import cer as jiwer_cer

# Rutas del proyecto
PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
DATA_GOLD    = PROJECT_ROOT / 'data' / 'gold'
IMAGES_DIR   = DATA_PROC / 'images'

IMAGE_MANIFEST  = DATA_PROC / 'image_manifest.csv'
QUALITY_REPORT  = DATA_PROC / 'quality_report_completo.csv'
CORPUS_OCR_CSV  = DATA_PROC / 'corpus_ocr.csv'
CORPUS_SUMMARY  = DATA_PROC / 'corpus_ocr_summary.csv'
CORPUS_BACKUP   = DATA_PROC / 'corpus_ocr_preV2_backup.csv'

# EasyOCR
EASYOCR_LANGS   = ['es']
EASYOCR_GPU     = False
EASYOCR_VERSION = easyocr.__version__
PYMUPDF_VERSION = fitz.__version__

for p in [IMAGE_MANIFEST, QUALITY_REPORT, CORPUS_OCR_CSV]:
    assert p.exists(), f'Falta archivo requerido: {p}'

print('Setup OK')
print(f'  corpus_ocr.csv actual: {CORPUS_OCR_CSV}')
print(f'  image_manifest.csv:    {IMAGE_MANIFEST}')
print(f'  quality_report.csv:    {QUALITY_REPORT}')
print(f'  EasyOCR:  {EASYOCR_VERSION}')
print(f'  PyMuPDF:  {PYMUPDF_VERSION}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. INVENTARIO INICIAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Inventario inicial

Antes de tocar nada, caracterizamos el estado actual de `corpus_ocr.csv` y calculamos **exactamente** cuantas filas nuevas esperamos añadir. Esto nos da un numero objetivo para validar al final.
"""))

cells.append(code("""# Cargar corpus OCR actual
corpus_actual = pd.read_csv(CORPUS_OCR_CSV)
print(f'corpus_ocr.csv actual: {len(corpus_actual):,} filas / {corpus_actual[\"md5\"].nunique()} docs')
print(f'Engines actuales: {corpus_actual[\"engine\"].value_counts().to_dict()}')
print()

# Cargar manifest (todas las paginas escaneadas preprocesadas)
manifest = pd.read_csv(IMAGE_MANIFEST)
print(f'image_manifest.csv: {len(manifest):,} filas / {manifest[\"md5\"].nunique()} docs escaneados')
print()

# Cargar quality report (todo el corpus Fase 1)
qr = pd.read_csv(QUALITY_REPORT)
print(f'quality_report_completo.csv: {len(qr):,} docs Fase 1')
print()

# ── GAP A: paginas en manifest pero NO en corpus_ocr ──
key_corpus   = set(zip(corpus_actual['md5'], corpus_actual['page_num']))
key_manifest = set(zip(manifest['md5'],      manifest['page_num']))
paginas_gap_a = key_manifest - key_corpus
print(f'=== GAP A === Paginas escaneadas pendientes: {len(paginas_gap_a)}')
gap_a_rows = manifest[manifest.apply(lambda r: (r['md5'], r['page_num']) in paginas_gap_a, axis=1)].copy()
gap_a_rows[['folder','filename','page_num']].head(15)
"""))

cells.append(code("""# ── GAP B: docs en quality_report pero NO en manifest (= digitales) ──
docs_en_manifest  = set(manifest['md5'].unique())
docs_en_qr        = set(qr['md5'].unique())
docs_digitales    = docs_en_qr - docs_en_manifest

print(f'=== GAP B === Docs digitales (no escaneados, nunca procesados): {len(docs_digitales)}')

gap_b_docs = qr[qr['md5'].isin(docs_digitales)].copy()

# Filtrar corruptos (n_pages=0 — detectados en Fase 1)
corruptos = (gap_b_docs['n_pages'] == 0).sum()
if corruptos:
    print(f'Docs corruptos (n_pages=0) que se excluyen: {corruptos}')
    gap_b_docs = gap_b_docs[gap_b_docs['n_pages'] > 0].reset_index(drop=True)

print(f'Docs a procesar: {len(gap_b_docs)}')
print(f'Paginas totales: {gap_b_docs[\"n_pages\"].sum():,}')
print()
print('Por folder:')
print(gap_b_docs.groupby('category').agg(docs=('md5','nunique'), paginas=('n_pages','sum')))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. PARTE A: 9 IMAGENES VIA EASYOCR
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## PARTE A — Procesar 9 imagenes directas via EasyOCR

### Que hacemos

Para cada fila de `gap_a_rows`:
1. Leer la imagen preprocesada de `ruta_imagen_procesada`.
2. Pasarla al lector de EasyOCR → lista de detecciones `(bbox, text, confidence)`.
3. Reconstruir el texto en orden de lectura (misma funcion del nb 05).
4. Armar fila con schema identico al corpus_ocr.csv.

### Por que EasyOCR y no PyMuPDF

Son imagenes, no PDFs. No hay texto nativo que extraer — hay que hacer OCR. Usamos EasyOCR (no Tesseract) para mantener consistencia con los otros 1,669 escaneados del corpus (misma distribucion de errores OCR → downstream estable).
"""))

cells.append(code("""def reconstruir_texto(detections):
    \"\"\"Ordena bboxes por Y-center y luego X para leer en orden natural.\"\"\"
    if not detections:
        return ''
    items = []
    for bbox, text, conf in detections:
        xs = [p[0] for p in bbox]; ys = [p[1] for p in bbox]
        cy = (min(ys) + max(ys)) / 2.0
        items.append({'text': text, 'cy': cy, 'lx': min(xs), 'h': max(ys)-min(ys)})
    items.sort(key=lambda it: it['cy'])
    median_h = float(np.median([it['h'] for it in items])) if items else 1.0
    tol = max(median_h * 0.5, 5.0)
    lineas, actual, actual_y = [], [items[0]], items[0]['cy']
    for it in items[1:]:
        if abs(it['cy'] - actual_y) <= tol:
            actual.append(it)
        else:
            lineas.append(actual); actual = [it]; actual_y = it['cy']
    lineas.append(actual)
    out = []
    for ln in lineas:
        ln.sort(key=lambda it: it['lx'])
        out.append(' '.join(it['text'] for it in ln))
    return '\\n'.join(out)


def detections_a_json(detections) -> str:
    payload = []
    for bbox, text, conf in detections:
        payload.append({
            'bbox': [[float(x), float(y)] for x, y in bbox],
            'text': text,
            'confidence': float(conf),
        })
    return json.dumps(payload, ensure_ascii=False)


# Cargar EasyOCR (una sola vez)
print('Cargando EasyOCR...')
reader = easyocr.Reader(EASYOCR_LANGS, gpu=EASYOCR_GPU, verbose=False)
print('Listo.')
"""))

cells.append(code("""# Procesar las 9 paginas pendientes
filas_nuevas_a = []
for _, row in tqdm(gap_a_rows.iterrows(), total=len(gap_a_rows), desc='Parte A - EasyOCR'):
    try:
        img_path = Path(row['ruta_imagen_procesada'])
        if not img_path.is_absolute():
            img_path = (PROJECT_ROOT / img_path).resolve()
        img = cv2.imread(str(img_path))
        if img is None:
            raise IOError(f'No se pudo leer: {img_path}')
        t0 = time.perf_counter()
        detections = reader.readtext(img)
        elapsed = time.perf_counter() - t0
        texto = reconstruir_texto(detections)
        filas_nuevas_a.append({
            'md5':            row['md5'],
            'doc_id':         row['md5'],
            'filename':       row['filename'],
            'folder':         row['folder'],
            'page_num':       int(row['page_num']),
            'timestamp':      datetime.now(timezone.utc).isoformat(),
            'error':          None,
            'engine':         'easyocr',
            'engine_version': EASYOCR_VERSION,
            'gpu_used':       EASYOCR_GPU,
            'texto_ocr':      texto,
            'bboxes_json':    detections_a_json(detections),
            'n_detections':   len(detections),
            'elapsed_s':      round(elapsed, 3),
            'text_chars':     len(texto),
        })
    except Exception as e:
        filas_nuevas_a.append({
            'md5': row['md5'], 'doc_id': row['md5'], 'filename': row['filename'],
            'folder': row['folder'], 'page_num': int(row['page_num']),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': f'{type(e).__name__}: {e}',
            'engine': None, 'engine_version': None, 'gpu_used': None,
            'texto_ocr': None, 'bboxes_json': None, 'n_detections': None,
            'elapsed_s': None, 'text_chars': None,
        })

df_gap_a = pd.DataFrame(filas_nuevas_a)
print(f'Parte A completa. Filas producidas: {len(df_gap_a)}')
print(f'  Con error: {df_gap_a[\"error\"].notna().sum()}')
print(f'  Chars promedio: {df_gap_a[\"text_chars\"].mean():.0f}')
print(f'  s/pagina:       {df_gap_a[\"elapsed_s\"].mean():.1f}')
df_gap_a[['folder','filename','page_num','text_chars','elapsed_s','error']]
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. PARTE B: 548 DIGITALES VIA PYMUPDF
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## PARTE B — Procesar ~590 digitales via PyMuPDF

### Que hacemos

Para cada PDF digital en `gap_b_docs`:
1. Abrir con `fitz.open()`.
2. Para cada pagina: `page.get_text('text')` → string con el texto en orden natural.
3. Armar una fila por pagina con schema del corpus_ocr.csv.

### Que NO hacemos

- **No renderizamos a imagen.** Seria tiempo perdido y degradaria texto perfecto.
- **No aplicamos OCR.** Los caracteres estan embebidos en el PDF como texto, no como pixeles.
- **No validamos contenido.** PyMuPDF es determinista; si el PDF tiene el texto, lo extrae.

### Por que los digitales no necesitan preprocesamiento

Preprocesar (deskew, CLAHE, etc.) aplica a **imagenes**. Un PDF digital no es imagen — es una estructura que contiene glifos posicionados. Dibujar esos glifos a pixeles y luego OCR'rlos seria volver a un problema que ya esta resuelto.

### Casos edge a manejar

1. **PDF corrupto** (n_pages=0 en quality_report): skip.
2. **PDF protegido con password**: skip con error registrado.
3. **Pagina sin texto** (raro en digitales, pero posible si tiene solo imagenes): devuelve '' — queda registrado con `text_chars=0`.
4. **Encoding raro**: `get_text('text')` devuelve Unicode; no hay conversion adicional.
"""))

cells.append(code("""# Construir indice MD5 → ruta del PDF en disco (algunos docs se movieron de carpeta en Fase 2)
import hashlib
def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

print('Indexando data/raw/ por MD5 (toma ~30 s)...')
md5_index = {}
for p in DATA_RAW.rglob('*.pdf'):
    md5_index[md5_file(p)] = p
print(f'  {len(md5_index)} PDFs indexados en disco')
print()

# Mapear cada doc digital a su path actual
gap_b_docs = gap_b_docs.assign(pdf_path_actual=gap_b_docs['md5'].map(lambda h: md5_index.get(h)))
sin_pdf = gap_b_docs['pdf_path_actual'].isna().sum()
if sin_pdf:
    print(f'Docs digitales sin PDF en disco (se excluyen): {sin_pdf}')
    gap_b_docs = gap_b_docs[gap_b_docs['pdf_path_actual'].notna()].reset_index(drop=True)
print(f'Docs a procesar: {len(gap_b_docs)}')
"""))

cells.append(code("""def extraer_pymupdf_doc(pdf_path: Path, md5: str, filename: str, folder: str):
    \"\"\"Extrae texto pagina por pagina. Devuelve lista de dicts con el mismo schema del corpus_ocr.\"\"\"
    filas = []
    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        return [{
            'md5': md5, 'doc_id': md5, 'filename': filename, 'folder': folder,
            'page_num': 1, 'timestamp': datetime.now(timezone.utc).isoformat(),
            'error': f'open_failed: {type(e).__name__}: {e}',
            'engine': None, 'engine_version': None, 'gpu_used': None,
            'texto_ocr': None, 'bboxes_json': None, 'n_detections': None,
            'elapsed_s': None, 'text_chars': None,
        }]
    try:
        for i in range(len(doc)):
            t0 = time.perf_counter()
            page = doc[i]
            texto = page.get_text('text')
            elapsed = time.perf_counter() - t0
            filas.append({
                'md5': md5, 'doc_id': md5, 'filename': filename, 'folder': folder,
                'page_num': i + 1,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': None,
                'engine': 'pymupdf',
                'engine_version': PYMUPDF_VERSION,
                'gpu_used': False,
                'texto_ocr': texto,
                'bboxes_json': None,        # PyMuPDF no produce bboxes en 'text' mode
                'n_detections': 0,
                'elapsed_s': round(elapsed, 3),
                'text_chars': len(texto),
            })
    finally:
        doc.close()
    return filas


# Loop sobre los 548 digitales
filas_nuevas_b = []
for _, row in tqdm(gap_b_docs.iterrows(), total=len(gap_b_docs), desc='Parte B - PyMuPDF'):
    filas_nuevas_b.extend(extraer_pymupdf_doc(
        Path(row['pdf_path_actual']),
        row['md5'],
        row['filename'],
        row['category'],
    ))

df_gap_b = pd.DataFrame(filas_nuevas_b)
print(f'\\nParte B completa.')
print(f'  Filas producidas: {len(df_gap_b):,}')
print(f'  Docs procesados:  {df_gap_b[\"md5\"].nunique()}')
print(f'  Con error:        {df_gap_b[\"error\"].notna().sum()}')
print(f'  Chars promedio:   {df_gap_b[\"text_chars\"].mean():.0f}')
print(f'  Chars totales:    {df_gap_b[\"text_chars\"].sum():,}')
print(f'  s/pagina (mean):  {df_gap_b[\"elapsed_s\"].mean():.3f}  ← instantaneo')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. CONSOLIDACION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Consolidacion — merge con el corpus previo

### Pasos

1. **Backup** de `corpus_ocr.csv` previo a `corpus_ocr_preV2_backup.csv`.
2. **Concatenacion**: `corpus_actual + df_gap_a + df_gap_b`.
3. **Dedup defensivo** por `(md5, page_num)` — si alguna fila se procesa dos veces, preservamos la version con menos errores y mas texto.
4. **Ordenamiento** por `folder, filename, page_num` para lectura reproducible.
5. **Escritura** de nuevo `corpus_ocr.csv` + regeneracion de `corpus_ocr_summary.csv`.
"""))

cells.append(code("""# 1. Backup
if not CORPUS_BACKUP.exists():
    shutil.copy2(CORPUS_OCR_CSV, CORPUS_BACKUP)
    print(f'Backup creado: {CORPUS_BACKUP.name}')
else:
    print(f'Backup ya existia (se conserva el mas antiguo): {CORPUS_BACKUP.name}')

# 2. Concatenar
corpus_v2 = pd.concat([corpus_actual, df_gap_a, df_gap_b], ignore_index=True)
print(f'Tras concat: {len(corpus_v2):,} filas')

# 3. Dedup defensivo: si hay duplicados (md5, page_num), nos quedamos con la que tenga mas chars
corpus_v2['_chars'] = corpus_v2['text_chars'].fillna(-1)
corpus_v2 = corpus_v2.sort_values('_chars', ascending=False).drop_duplicates(
    subset=['md5', 'page_num'], keep='first').drop(columns='_chars')

# 4. Orden reproducible
corpus_v2 = corpus_v2.sort_values(['folder', 'filename', 'page_num']).reset_index(drop=True)

# 5. Guardar corpus_ocr.csv
corpus_v2.to_csv(CORPUS_OCR_CSV, index=False)
print(f'Escrito: {CORPUS_OCR_CSV.name} — {len(corpus_v2):,} filas')

# 6. Regenerar summary (sin texto)
cols_summary = ['md5','doc_id','filename','folder','page_num','engine','engine_version',
                'gpu_used','n_detections','text_chars','elapsed_s','timestamp','error']
summary_v2 = corpus_v2[cols_summary].copy()
summary_v2.to_csv(CORPUS_SUMMARY, index=False)
print(f'Escrito: {CORPUS_SUMMARY.name} — {len(summary_v2):,} filas')
"""))

cells.append(code("""# Reporte final de cobertura
print('=== COBERTURA FINAL DEL CORPUS OCR ===\\n')
print(f'Docs totales:     {corpus_v2[\"md5\"].nunique():,}')
print(f'Paginas totales:  {len(corpus_v2):,}')
print(f'Chars totales:    {corpus_v2[\"text_chars\"].sum():,}')
print()
print('Por engine:')
print(corpus_v2['engine'].value_counts().to_string())
print()
print('Por folder:')
print(corpus_v2.groupby('folder').agg(
    docs=('md5','nunique'), paginas=('md5','size'),
    chars=('text_chars','sum'), engine=('engine', lambda x: x.value_counts().to_dict())
).to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 9. VALIDACION CONTRA GOLD
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Validacion — CER + entity_recall contra gold seed

Re-medimos contra los 15 docs del gold seed. Las metricas **no deberian moverse** significativamente (los 15 gold son todos escaneados y ya estaban en el corpus previo). Este paso es sanity check: confirma que el merge no corrompio ninguna fila.

### Metodologia

- Para cada doc del gold, tomamos los primeros `pages_to_use` del corpus_ocr.
- Normalizamos (lowercase + whitespace colapsado).
- Calculamos `CER` con `jiwer` y `entity_recall` con regex.

### Patrones regex (alineados con benchmark §1.4)

| Entidad | Pattern |
|---|---|
| NIT | `\\b\\d{9,11}\\b` |
| Cedula | `\\b\\d{7,10}\\b` |
| Fecha | `\\b(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}\\|\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})\\b` |
| Monto | `\\b\\d{1,3}(?:[.,]\\d{3})+\\b` |
"""))

cells.append(code("""TRANS = DATA_GOLD / 'transcriptions'
manifest_gold = pd.read_csv(DATA_GOLD / 'gold_seed_manifest.csv')

def norm(s):
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r'\\s+', ' ', s).strip()
    return s

RE_NIT   = re.compile(r'\\b\\d{9,11}\\b')
RE_CED   = re.compile(r'\\b\\d{7,10}\\b')
RE_DATE  = re.compile(r'\\b(\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}|\\d{4}[/-]\\d{1,2}[/-]\\d{1,2})\\b')
RE_MONEY = re.compile(r'\\b\\d{1,3}(?:[.,]\\d{3})+\\b')

def entities(text):
    t = text or ''
    return {
        'nit':   set(RE_NIT.findall(t)),
        'ced':   set(RE_CED.findall(t)),
        'date':  set(RE_DATE.findall(t)),
        'money': set(RE_MONEY.findall(t)),
    }

def recall(gold_ent, ocr_ent):
    total = sum(len(v) for v in gold_ent.values())
    if total == 0:
        return None
    hits = sum(len(gold_ent[k] & ocr_ent[k]) for k in gold_ent)
    return hits / total

results = []
for _, mf in manifest_gold.iterrows():
    md5 = mf['md5']; folder = mf['folder']; fname = mf['filename']
    pages_use = int(mf['pages_to_use'])
    tpath = TRANS / f'{md5}.txt'
    if not tpath.exists():
        continue
    gold = tpath.read_text(encoding='utf-8', errors='ignore')
    rows = corpus_v2[corpus_v2['md5'] == md5].sort_values('page_num').head(pages_use)
    if rows.empty:
        results.append({'md5': md5, 'folder': folder, 'filename': fname[:40],
                        'pag': pages_use, 'cer': None, 'ent_recall': None, 'note': 'NO_EN_CORPUS'})
        continue
    ocr_text = '\\n'.join(rows['texto_ocr'].fillna('').astype(str).tolist())
    c = jiwer_cer(norm(gold), norm(ocr_text))
    er = recall(entities(gold), entities(ocr_text))
    results.append({
        'md5': md5, 'folder': folder, 'filename': fname[:40],
        'pag': pages_use,
        'chars_gold': len(norm(gold)), 'chars_ocr': len(norm(ocr_text)),
        'cer': round(c, 4), 'ent_recall': round(er, 3) if er is not None else None,
    })

val_df = pd.DataFrame(results)
print('=== VALIDACION POST-CIERRE ===\\n')
print(val_df.to_string(index=False))
print()
print('Agregados por folder:')
print(val_df.groupby('folder')[['cer','ent_recall']].mean().round(4))
print()
print(f'CER global (media):     {val_df[\"cer\"].mean():.4f}')
print(f'CER global (mediana):   {val_df[\"cer\"].median():.4f}')
print(f'Entity recall (media):  {val_df[\"ent_recall\"].mean():.4f}')

# Guardar validacion actualizada
val_df.to_csv(DATA_GOLD / 'ocr_corpus_validation.csv', index=False)
print(f'\\nGuardado: {DATA_GOLD / \"ocr_corpus_validation.csv\"}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 10. CIERRE
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Cierre Fase 2 §2.1 — corpus textual completo

Si las celdas anteriores corrieron sin errores, `corpus_ocr.csv` ahora contiene **texto para los ~1,014 documentos del corpus SECOP**:

- **Escaneados (EasyOCR):** ~1,678 paginas — texto OCR'd con pipeline sin binarize.
- **Digitales (PyMuPDF):** ~N paginas — texto nativo perfecto.

### Proximos pasos

1. **Commit del summary actualizado** (`corpus_ocr_summary.csv`) — el CSV con texto es gitignored por PII.
2. **Actualizar la documentacion maestra:**
   - `OCR_BENCHMARK.md` §2.6.2 con la cobertura final
   - `PLAN_MODELADO_CRISPDM.md` §2.1 marcar como 🟢 completa
   - `README.md` tabla de estado
3. **Continuar a §2.2:** pre-anotaciones RUT via Labeling Functions sobre `corpus_ocr.csv`.

### Preguntas que este corpus permite responder (insumo para el informe final)

- Cual es la distribucion de tamaños de texto por tipologia?
- Cuantos NIT/cedulas/fechas/montos hay en total en el corpus?
- Que proporcion del corpus es escaneado vs digital (en paginas, no solo en docs)?
- Cual es el vocabulario dominante tras OCR (insumo para §2.2 LFs)?

Este es el insumo textual del proyecto. Todo lo que venga despues (entrenamiento, evaluacion) se construye sobre este archivo.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out = Path(__file__).parent / '05b_cierre_gaps_ocr.ipynb'
nbf.write(nb, out)
print(f'Notebook generado: {out}')
print(f'  Celdas totales: {len(cells)}')
md_count = sum(1 for c in cells if c.cell_type == 'markdown')
code_count = sum(1 for c in cells if c.cell_type == 'code')
print(f'  Markdown: {md_count}')
print(f'  Code:     {code_count}')
