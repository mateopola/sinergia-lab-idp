"""
Genera el notebook 04_preprocesamiento_imagenes.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_04.py

Proposito del notebook 04:
    Aplicar el pipeline de preprocesamiento visual (definido en Notebook 02 y
    exportado a src/preprocessing/pipeline.py) a los 1,014 documentos del corpus,
    generando una imagen procesada por pagina para alimentar el OCR (Notebook 05).

Contexto: Fase 2 CRISP-DM++ §2.1 — tareas pendientes
    - [ ] Guardar imagenes procesadas en data/processed/images/ con nomenclatura estandarizada
    - [ ] Validar pipeline con muestra de documentos antes del OCR masivo

Estructura (marcdown = M, codigo = C):
     1 M  Portada + objetivo + referencias
     2 M  ¿Por que preprocesar antes de OCR?
     3 M  Setup
     4 C  Imports + rutas + constantes
     5 M  Cargar metadata del corpus (Fase 1)
     6 C  Leer quality_report_completo.csv y filtrar duplicados
     7 M  Indexar data/raw/ por MD5 (root-fix de clasificacion)
     8 C  Construir md5_index + derivar folder desde disco
     9 M  Plan de la corrida
    10 C  Preparar lista de trabajo + estadisticas
    11 M  Pipeline de preprocesamiento visual — funciones
    12 C  Import funciones de src/preprocessing/pipeline.py + helper por pagina
    13 M  Test visual — 3 paginas antes/despues
    14 C  Renderizar 3 ejemplos y mostrar comparativo
    15 M  Procesamiento masivo — estrategia de bloques con checkpoint
    16 C  Loop principal con tqdm, skip-if-exists, try/except
    17 M  Consolidacion del image_manifest.csv
    18 C  Unir bloques, guardar manifest final
    19 M  Validacion de la corrida
    20 C  Conteos, errores, muestra aleatoria
    21 M  Siguiente paso
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
cells.append(md("""# SinergIA Lab — Preprocesamiento Visual del Corpus
## Fase 2 CRISP-DM++ · §2.1 — Generacion de Imagenes Procesadas

---

### Proposito del notebook

Aplicar el **pipeline de preprocesamiento visual** (definido en el Notebook 02 y exportado a `src/preprocessing/pipeline.py`) a los **416 documentos escaneados del corpus**, generando una imagen procesada por pagina. Estas imagenes alimentan el OCR del Notebook 05.

> **Importante:** los 548 PDFs digitales (`es_escaneado=False`) NO pasan por este notebook. El Notebook 05 los procesa directamente con PyMuPDF sobre el PDF original — no necesitan imagen ni OCR. Generarles una imagen procesada seria desperdicio de disco y CPU (~9 GB, ~60 min).

### Relacion con otros notebooks

| Notebook | Rol | Estado |
|---|---|---|
| **01** | Analisis descriptivo (EDA) — calidad visual, densidad textual, tipologias | ✅ Ejecutado |
| **02** | Define las funciones de preprocesamiento visual (deskew, denoise, CLAHE, binarize, normalize_dpi) y las exporta a `pipeline.py` | ✅ Ejecutado |
| **03** | Benchmark OCR — decide EasyOCR como motor | ✅ Ejecutado |
| **04 (este)** | Aplica el pipeline del nb 02 a todo el corpus → imagenes procesadas | ⏳ |
| **05** | OCR sobre las imagenes procesadas → `corpus_ocr.csv` | Siguiente |

### Que hace este notebook?

Por cada PDF escaneado del corpus:
1. Resuelve su ruta actual por MD5 (robusto a renombres/reclasificaciones).
2. Por cada pagina: renderiza a imagen 300 DPI, aplica el pipeline OpenCV.
3. Guarda como `data/processed/images/processed_{md5}_page_{N}.jpg`.
4. Anota metadata en `data/processed/image_manifest.csv`.

### Referencias

- Plan maestro: `PLAN_MODELADO_CRISPDM.md` §2.1
- Modulo reutilizado: `src/preprocessing/pipeline.py`

### Tiempo estimado

- Corrida de prueba (10 docs): ~2 min
- Corrida completa (416 docs escaneados, ~1,678 paginas): **~8-15 min** en CPU
- Output aproximado: ~1,678 imagenes × ~1.1 MB ≈ **~1.85 GB** (en `.gitignore`)
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. POR QUE PREPROCESAR
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## ¿Por que preprocesar antes del OCR?

El OCR trabaja mejor sobre imagenes **limpias, derechas, bien contrastadas y con resolucion consistente**. Cada paso del pipeline ataca un problema real del corpus:

| Etapa | Problema que resuelve | Funcion |
|---|---|---|
| `deskew` | Documentos escaneados rotados ±5-15° | Correccion de angulo con `cv2.minAreaRect` |
| `denoise` | Ruido de escaner (especialmente en cedulas viejas) | `cv2.fastNlMeansDenoising` |
| `enhance_contrast` (CLAHE) | Paginas con iluminacion despareja | Ecualizacion adaptativa local |
| `binarize` | Fondo no uniforme dificulta detectar bordes de texto | Otsu umbralizacion adaptativa |
| `normalize_dpi` | Escaneos en 150 DPI mezclados con nativos 72 DPI | Resample a 300 DPI estandar |

**Evidencia del corpus (Fase 1):**
- 428 docs escaneados (42%) con variabilidad fuerte de calidad visual
- Cedulas: 93% escaneadas, muchas con hologramas y bajo contraste
- Hallazgo v1.6: algunos CC y Polizas tienen **portada corporativa** en pagina 1 (detectada y saltada para esas tipologias, NO para Cedulas ni RUT).

**Nota sobre PDFs digitales:** los 586 digitales tambien se renderizan a imagen por uniformidad, aunque su texto se extraera via PyMuPDF (texto nativo) en el Notebook 05. La imagen queda disponible por si el NER posterior necesita usar bboxes.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 3. SETUP
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Configuracion inicial

Importamos librerias, fijamos rutas y definimos constantes de la corrida.
"""))

cells.append(code("""import hashlib
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import cv2
import fitz                # PyMuPDF
import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

# Rutas del proyecto
PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
IMAGES_DIR   = DATA_PROC / 'images'
BLOCKS_DIR   = DATA_PROC / 'image_blocks'
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
BLOCKS_DIR.mkdir(parents=True, exist_ok=True)

QUALITY_REPORT     = DATA_PROC / 'quality_report_completo.csv'
IMAGE_MANIFEST     = DATA_PROC / 'image_manifest.csv'
PROCESSED_LOG      = BLOCKS_DIR / 'processed_log.csv'

# Agregar raiz al path para importar src/preprocessing/pipeline.py
sys.path.insert(0, str(PROJECT_ROOT.resolve()))

# Constantes de la corrida
RENDER_DPI      = 300   # DPI al renderizar PDF → imagen (coincide con benchmark del nb 03)
JPG_QUALITY     = 92    # Calidad JPG (90-95 es buen balance tamano/fidelidad)
BLOCK_SIZE      = 50    # Paginas por bloque (checkpoint)
FORCE_REPROCESS = False # True = ignora cache e reprocesa todo

print(f'Rutas OK.')
print(f'  Imagenes -> {IMAGES_DIR.resolve()}')
print(f'  Manifest -> {IMAGE_MANIFEST}')
print(f'  DPI={RENDER_DPI}  JPG_QUALITY={JPG_QUALITY}  BLOCK_SIZE={BLOCK_SIZE}  FORCE_REPROCESS={FORCE_REPROCESS}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGAR METADATA DEL CORPUS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Cargar metadata del corpus (Fase 1)

Leemos `quality_report_completo.csv` generado en Fase 1. Filtramos:

- **Sin duplicados** (`is_duplicate == False`) — no tiene sentido preprocesar copias identicas.
- **Solo escaneados** (`es_escaneado == True`) — los digitales NO pasan por este preprocesamiento.

### ¿Por que solo escaneados?

En el Notebook 05 (OCR):
- **Escaneados** → EasyOCR sobre la imagen procesada (este notebook la genera).
- **Digitales** → PyMuPDF lee el texto directamente del PDF (sin imagen, sin OCR).

Los digitales nunca necesitan la imagen procesada. Generarlas gastaria ~9 GB de disco y ~60 min de CPU en pixeles que nadie leera.

**Detector:** la columna `es_escaneado` fue computada en Fase 1 (`notebooks/run_fase1.py`). La logica: si PyMuPDF extrae < 50 caracteres de la primera pagina, se considera escaneado. Umbral validado sobre el corpus.

| Tipo | Docs | Paginas | Este notebook los procesa? |
|---|---|---|---|
| Escaneados | 416 | ~1,678 | **Si** — genera imagen procesada |
| Digitales | 548 | ~11,576 | **No** — quedan fuera del nb 04, van directo a PyMuPDF en nb 05 |
"""))

cells.append(code("""df_full = pd.read_csv(QUALITY_REPORT, encoding='utf-8-sig')
print(f'Corpus total (incluye duplicados): {len(df_full)}')

# Filtrar: sin duplicados
df_nodup = df_full[df_full['is_duplicate'] == False].copy()
print(f'Sin duplicados:                    {len(df_nodup)}')
print(f'  Digitales (saltan este nb):      {(~df_nodup[\"es_escaneado\"]).sum()} docs, {int(df_nodup.loc[~df_nodup[\"es_escaneado\"], \"n_pages\"].sum())} paginas')
print(f'  Escaneados (se procesan aqui):   {df_nodup[\"es_escaneado\"].sum()} docs, {int(df_nodup.loc[df_nodup[\"es_escaneado\"], \"n_pages\"].sum())} paginas')

# Nuestro DataFrame de trabajo es SOLO los escaneados
df = df_nodup[df_nodup['es_escaneado'] == True].reset_index(drop=True)
print(f'\\nDataFrame de trabajo: {len(df)} docs escaneados')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. INDICE MD5
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Indexar `data/raw/` por MD5

**Importante:** el campo `filepath` del CSV fue registrado en Fase 1. Si despues movieron algun archivo a otra carpeta (como `CC OMAR DAZA` que se reclasifico a `CEDULA`), ese `filepath` queda desactualizado.

Solucion: construimos un indice MD5 → ruta actual en disco. La carpeta tipologica real se deriva del directorio padre del archivo vigente, no del CSV.

**Formatos soportados:** `.pdf`, `.jpg`, `.jpeg`, `.png`. Algunos documentos del corpus (9 cedulas/rut/TP) estan como imagenes directas, no como PDFs. Fase 1 los clasifico correctamente con `es_escaneado=True`; aqui los tratamos como documentos de 1 pagina.
"""))

cells.append(code("""SUPPORTED_EXTS = {'.pdf', '.jpg', '.jpeg', '.png'}

def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

print('Indexando data/raw/ por MD5 (1-2 min la primera vez)...')
md5_index = {}
for f in DATA_RAW.rglob('*'):
    if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS:
        md5_index[md5_file(f)] = f
pdfs   = sum(1 for p in md5_index.values() if p.suffix.lower() == '.pdf')
imgs   = sum(1 for p in md5_index.values() if p.suffix.lower() in {'.jpg','.jpeg','.png'})
print(f'  {len(md5_index)} archivos indexados:  PDFs={pdfs}  Imagenes directas={imgs}')

# Derivar ruta y carpeta reales desde disco
df['local_path'] = df['md5'].map(lambda h: str(md5_index.get(h, '')))
df['folder']     = df['md5'].map(lambda h: md5_index[h].parent.name if h in md5_index else '')
df['folder_fase1'] = df['filepath'].str.replace('\\\\', '/', regex=False).str.split('/').str[-2]

missing = (df['local_path'] == '').sum()
print(f'  Sin match por MD5 en disco: {missing} (se excluyen)')
df = df[df['local_path'] != ''].reset_index(drop=True)

# Reportar reclasificaciones
reclassified = df[df['folder'] != df['folder_fase1']]
if len(reclassified):
    print(f'\\n  ⚠ {len(reclassified)} docs reclasificados desde Fase 1:')
    for _, r in reclassified.iterrows():
        print(f'     - {r[\"filename\"][:55]:<55}  {r[\"folder_fase1\"]} -> {r[\"folder\"]}')
else:
    print('  OK: ninguna reclasificacion detectada.')

print(f'\\nDistribucion actual por carpeta:')
print(df['folder'].value_counts())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. PLAN DE LA CORRIDA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Plan de la corrida

Expandimos el DataFrame a nivel pagina: una fila por cada pagina del corpus. Luego filtramos las paginas que ya estan procesadas (si existe el JPG en `data/processed/images/`).

**Modo prueba:** para ejecutar solo sobre 10 docs cambiar la flag `PRUEBA` a `True` abajo. Util para validar antes del corrida completa.
"""))

cells.append(code("""PRUEBA = False   # True = procesar solo 10 docs al azar (seed=42)

if PRUEBA:
    df_run = df.sample(n=10, random_state=42).reset_index(drop=True)
    print(f'MODO PRUEBA: procesando {len(df_run)} docs de muestra')
else:
    df_run = df.copy()
    print(f'MODO COMPLETO: procesando {len(df_run)} docs')

# Expandir a nivel pagina
pages = []
for _, row in df_run.iterrows():
    for page_num in range(1, int(row['n_pages']) + 1):
        pages.append({
            'md5':        row['md5'],
            'doc_id':     row['md5'],
            'filename':   row['filename'],
            'folder':     row['folder'],
            'page_num':   page_num,
            'n_pages':    int(row['n_pages']),
            'local_path': row['local_path'],
            'es_escaneado': bool(row['es_escaneado']),
        })
pages_df = pd.DataFrame(pages)
print(f'Total paginas a procesar: {len(pages_df)}')

# Detectar paginas ya procesadas en disco
def imagen_destino(md5, page_num):
    return IMAGES_DIR / f'processed_{md5}_page_{page_num}.jpg'

pages_df['out_path'] = pages_df.apply(
    lambda r: str(imagen_destino(r['md5'], r['page_num'])), axis=1)
pages_df['ya_existe'] = pages_df['out_path'].map(lambda p: Path(p).exists())

if FORCE_REPROCESS:
    pending = pages_df.copy()
    print(f'FORCE_REPROCESS=True -> reprocesando todas las paginas ({len(pending)})')
else:
    pending = pages_df[~pages_df['ya_existe']].reset_index(drop=True)
    print(f'Paginas ya procesadas (cache): {pages_df[\"ya_existe\"].sum()}')
    print(f'Paginas pendientes:             {len(pending)}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. FUNCIONES DE PREPROCESAMIENTO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Pipeline de preprocesamiento visual — funciones

Importamos las funciones ya definidas y validadas en el Notebook 02, ahora empaquetadas en `src/preprocessing/pipeline.py`:

- `deskew(img_gray)` — correccion de rotacion
- `denoise(img_gray)` — filtro de ruido
- `enhance_contrast(img_gray)` — CLAHE
- `binarize(img_gray)` — Otsu
- `normalize_dpi(img_rgb)` — resample a 300 DPI
- `detectar_portada(pdf_path, categoria)` — detecta portada en Polizas y CC

El pipeline del nb 02 (`preprocess_pipeline`) procesa SOLO la primera pagina util. Aqui necesitamos procesar **todas las paginas** del PDF, asi que componemos las funciones individuales en un helper `process_page(...)` definido abajo.
"""))

cells.append(code("""from src.preprocessing.pipeline import (
    deskew, denoise, enhance_contrast, binarize, normalize_dpi,
    detectar_portada, TIPOLOGIAS_CON_PORTADA,
)

# Mapeo folder disco -> categoria para detectar_portada
FOLDER_TO_CATEGORIA = {
    'CEDULA':        'Cedula',
    'rut':           'RUT',
    'POLIZA':        'Poliza',
    'CAMARA DE CIO': 'Camara de Comercio',
    'OTROS':         'Otros',
}

def folder_to_categoria(folder: str) -> str:
    return FOLDER_TO_CATEGORIA.get(folder, 'Otros')

def load_page_as_image(file_path: Path, page_num: int, dpi: int = RENDER_DPI) -> np.ndarray:
    \"\"\"Carga una pagina como RGB uint8.

    - PDF: renderiza la pagina especificada via PyMuPDF.
    - Imagen directa (.jpg/.jpeg/.png): carga con cv2. page_num se ignora (siempre 1).
    \"\"\"
    suffix = file_path.suffix.lower()
    if suffix == '.pdf':
        doc = fitz.open(str(file_path))
        try:
            page = doc[page_num - 1]  # 1-indexed a 0-indexed
            pix = page.get_pixmap(
                matrix=fitz.Matrix(dpi / 72, dpi / 72),
                colorspace=fitz.csRGB,
            )
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            return img.copy()
        finally:
            doc.close()
    elif suffix in {'.jpg', '.jpeg', '.png'}:
        img_bgr = cv2.imread(str(file_path))
        if img_bgr is None:
            raise IOError(f'No se pudo leer la imagen: {file_path}')
        return cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    else:
        raise ValueError(f'Formato no soportado: {suffix}')

# Alias para compatibilidad interna
pdf_page_to_image = load_page_as_image

def process_page(img_rgb: np.ndarray, source_dpi: int = RENDER_DPI) -> np.ndarray:
    \"\"\"Aplica el pipeline visual a una sola imagen RGB.

    Flujo: gray -> deskew -> denoise -> enhance_contrast -> binarize
           -> vuelve a RGB -> normalize_dpi a 300 DPI
    \"\"\"
    img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    img_gray = deskew(img_gray)
    img_gray = denoise(img_gray)
    img_gray = enhance_contrast(img_gray)
    img_gray = binarize(img_gray)
    img_clean = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)
    img_clean = normalize_dpi(img_clean, source_dpi=source_dpi)
    return img_clean

def save_jpg(img_rgb: np.ndarray, out_path: Path, quality: int = JPG_QUALITY) -> None:
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])

print('Funciones de preprocesamiento listas.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. TEST VISUAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Test visual — 3 paginas antes/despues

Seleccionamos 3 paginas representativas (una de distinta tipologia) y comparamos visualmente el resultado del pipeline. Esto es **obligatorio** ejecutar antes de la corrida completa: si el pipeline destruye el texto (por ejemplo, binarizacion demasiado agresiva sobre cedulas con fondo complejo), lo detectamos aqui antes de 1-2 horas de corrida perdidas.
"""))

cells.append(code("""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Escoger 3 paginas: una CEDULA escaneada, una rut digital, una POLIZA digital
samples = []
for folder, label in [('CEDULA', 'Cedula escaneada'),
                      ('rut', 'RUT digital'),
                      ('POLIZA', 'Poliza')]:
    sub = pages_df[(pages_df['folder'] == folder) & (pages_df['page_num'] == 1)]
    if len(sub):
        r = sub.sample(n=1, random_state=42).iloc[0]
        samples.append((label, r))

fig, axes = plt.subplots(len(samples), 2, figsize=(12, 4 * len(samples)))
if len(samples) == 1:
    axes = [axes]

for row_idx, (label, r) in enumerate(samples):
    pdf_path = Path(r['local_path'])
    try:
        img_raw   = pdf_page_to_image(pdf_path, int(r['page_num']))
        img_clean = process_page(img_raw)
        axes[row_idx][0].imshow(img_raw)
        axes[row_idx][0].set_title(f'{label} — ANTES\\n{r[\"filename\"][:50]}', fontsize=9)
        axes[row_idx][0].axis('off')
        axes[row_idx][1].imshow(img_clean)
        axes[row_idx][1].set_title(f'{label} — DESPUES', fontsize=9)
        axes[row_idx][1].axis('off')
    except Exception as e:
        axes[row_idx][0].text(0.5, 0.5, f'ERROR: {e}', ha='center', va='center')

plt.tight_layout()
test_path = DATA_PROC / 'fig12_preprocesamiento_test.png'
plt.savefig(test_path, dpi=100, bbox_inches='tight')
plt.close()
print(f'Figura de test guardada: {test_path}')
print('Abrela y verifica que el texto sigue legible tras el preprocesamiento.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 9. PROCESAMIENTO MASIVO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Procesamiento masivo — bloques con checkpoint

Estrategia de robustez (inspirada en el flujo que ya usa el equipo):

- Las paginas se procesan en **bloques** de `BLOCK_SIZE` (default 50).
- Tras cada bloque se guarda un CSV parcial en `data/processed/image_blocks/` y se actualiza el log de paginas procesadas.
- Si el kernel se cae o el proceso se interrumpe, al re-ejecutar la celda continua automaticamente desde la ultima pagina procesada (los JPG existentes se detectan como cache).
- Errores por pagina se capturan y registran; no abortan la corrida completa.
"""))

cells.append(code("""def procesar_pagina(row) -> dict:
    \"\"\"Procesa una pagina y devuelve la fila de manifest correspondiente.\"\"\"
    t0 = time.perf_counter()
    out_path = Path(row['out_path'])
    pdf_path = Path(row['local_path'])
    try:
        img_raw   = pdf_page_to_image(pdf_path, int(row['page_num']))
        img_clean = process_page(img_raw)
        save_jpg(img_clean, out_path)
        elapsed = time.perf_counter() - t0
        h, w = img_clean.shape[:2]
        return {
            'md5':                    row['md5'],
            'doc_id':                 row['md5'],
            'filename':               row['filename'],
            'folder':                 row['folder'],
            'page_num':               int(row['page_num']),
            'n_pages_total':          int(row['n_pages']),
            'es_escaneado':           bool(row['es_escaneado']),
            'ruta_imagen_procesada':  str(out_path),
            'width':                  int(w),
            'height':                 int(h),
            'preprocess_elapsed_s':   round(elapsed, 3),
            'timestamp':              datetime.now(timezone.utc).isoformat(),
            'error':                  None,
        }
    except Exception as e:
        return {
            'md5':                    row['md5'],
            'doc_id':                 row['md5'],
            'filename':               row['filename'],
            'folder':                 row['folder'],
            'page_num':               int(row['page_num']),
            'n_pages_total':          int(row['n_pages']),
            'es_escaneado':           bool(row['es_escaneado']),
            'ruta_imagen_procesada':  None,
            'width':                  None,
            'height':                 None,
            'preprocess_elapsed_s':   round(time.perf_counter() - t0, 3),
            'timestamp':              datetime.now(timezone.utc).isoformat(),
            'error':                  f'{type(e).__name__}: {e}',
        }

if len(pending) == 0:
    print('Nada pendiente. Todas las paginas ya estan procesadas (cache).')
else:
    num_blocks = (len(pending) + BLOCK_SIZE - 1) // BLOCK_SIZE
    print(f'Procesando {len(pending)} paginas en {num_blocks} bloques de {BLOCK_SIZE}...')

    # IMPORTANTE: calcular el proximo numero de bloque a partir de los existentes
    # para NO sobreescribir bloques de corridas previas.
    existing_blocks = sorted(BLOCKS_DIR.glob('image_bloque_*.csv'))
    next_block_num = 1
    if existing_blocks:
        last = int(existing_blocks[-1].stem.split('_')[-1])
        next_block_num = last + 1
        print(f'  Bloques existentes: {len(existing_blocks)}  ->  continuando desde bloque {next_block_num:04d}')

    global_results = []
    errores = 0
    with tqdm(total=len(pending), desc='Paginas') as pbar:
        for bk in range(num_blocks):
            start = bk * BLOCK_SIZE
            end   = min(start + BLOCK_SIZE, len(pending))
            block = pending.iloc[start:end]

            block_results = []
            for _, row in block.iterrows():
                res = procesar_pagina(row)
                block_results.append(res)
                if res['error']:
                    errores += 1
                pbar.update(1)

            # Guardar bloque parcial con numero unico (continuo)
            bk_id = next_block_num + bk
            ruta_bloque = BLOCKS_DIR / f'image_bloque_{bk_id:04d}.csv'
            pd.DataFrame(block_results).to_csv(ruta_bloque, index=False, encoding='utf-8-sig')
            global_results.extend(block_results)

            # Actualizar log de paginas procesadas
            log_entries = [{'md5': r['md5'], 'page_num': r['page_num']}
                           for r in global_results if not r['error']]
            pd.DataFrame(log_entries).to_csv(PROCESSED_LOG, index=False, encoding='utf-8-sig')

    print(f'\\nBloques completados. Paginas con error: {errores}/{len(pending)} ({100*errores/max(len(pending),1):.1f}%)')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 10. CONSOLIDACION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Consolidacion del `image_manifest.csv`

Unimos todos los CSVs de bloque en un manifest unico. Este manifest es el **insumo principal** del Notebook 05 (OCR): cada fila corresponde a una imagen procesada lista para ser OCR'd.
"""))

cells.append(code("""block_files = sorted(BLOCKS_DIR.glob('image_bloque_*.csv'))
print(f'Bloques encontrados: {len(block_files)}')

if block_files:
    dfs = [pd.read_csv(f, encoding='utf-8-sig') for f in block_files]
    manifest = pd.concat(dfs, ignore_index=True)

    # Si hay duplicados (re-ejecuciones con FORCE_REPROCESS=True), nos quedamos con el timestamp mas reciente
    manifest = (manifest
                .sort_values('timestamp')
                .drop_duplicates(subset=['md5', 'page_num'], keep='last')
                .reset_index(drop=True))

    manifest.to_csv(IMAGE_MANIFEST, index=False, encoding='utf-8-sig')
    print(f'image_manifest.csv: {len(manifest)} filas -> {IMAGE_MANIFEST}')
else:
    print('No hay bloques. ¿Se ejecuto el loop de procesamiento?')
    manifest = pd.DataFrame()
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 11. VALIDACION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Validacion de la corrida

Checks automaticos sobre el manifest y el disco:

1. Cantidad de filas = paginas esperadas
2. Errores < 2%
3. Los archivos JPG existen fisicamente
4. Cada md5 del manifest existe en `quality_report_completo.csv`
5. Distribucion por tipologia consistente con el corpus
"""))

cells.append(code("""if len(manifest) == 0:
    print('Manifest vacio. Imposible validar.')
else:
    checks = []

    # 1. Conteo
    paginas_esperadas = int(df_run['n_pages'].sum())
    checks.append(('Paginas esperadas vs en manifest',
                   paginas_esperadas == len(manifest),
                   f'esperadas={paginas_esperadas}, en manifest={len(manifest)}'))

    # 2. Errores
    err_pct = 100 * manifest['error'].notna().sum() / max(len(manifest), 1)
    checks.append(('Tasa de errores < 2%',
                   err_pct < 2.0,
                   f'{err_pct:.2f}% ({manifest[\"error\"].notna().sum()} paginas)'))

    # 3. Archivos en disco
    missing_files = sum(1 for p in manifest['ruta_imagen_procesada'].dropna()
                        if not Path(p).exists())
    checks.append(('Archivos JPG existen',
                   missing_files == 0,
                   f'{missing_files} archivos faltantes'))

    # 4. MD5 en quality_report
    unknown = ~manifest['md5'].isin(df_full['md5'])
    checks.append(('MD5 presentes en quality_report',
                   unknown.sum() == 0,
                   f'{unknown.sum()} md5 desconocidos'))

    # 5. Distribucion
    print('\\nDistribucion por tipologia (paginas procesadas):')
    dist = manifest.groupby('folder').size().sort_values(ascending=False)
    print(dist.to_string())

    # Reporte
    print('\\n' + '='*60)
    print('RESULTADO DE VALIDACION')
    print('='*60)
    all_pass = True
    for name, ok, detail in checks:
        mark = '✅' if ok else '❌'
        print(f'  {mark} {name}')
        print(f'     {detail}')
        if not ok:
            all_pass = False
    print('='*60)
    print('OK — listo para Notebook 05' if all_pass else 'Hay checks fallidos — revisar antes de continuar')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 12. RESULTADOS + SIGUIENTE PASO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Resultados de la corrida productiva

**Fecha:** 2026-04-17
**Duracion total:** ~9 minutos
**Estado:** ✅ Exitoso

### Totales

| Metrica | Valor |
|---|---|
| Documentos procesados | **412** (403 PDFs + 9 imagenes directas jpg/jpeg) |
| Paginas procesadas | **1,678** |
| Errores | **0** |
| Tiempo medio por pagina | 0.33 s |
| Disco ocupado | **1.90 GB** |

### Distribucion por tipologia

| Folder | Docs | Paginas |
|---|---|---|
| CEDULA | 308 | 356 |
| RUT | 24 | 116 |
| POLIZA | 59 | 1,024 |
| CAMARA DE CIO | 16 | 160 |
| OTROS | 5 | 22 |

### Docs excluidos y por que

- **548 digitales** (`es_escaneado=False`): no pasan por este notebook. El Nb 05 los procesa directamente con PyMuPDF (ver seccion "¿Por que solo escaneados?" arriba).
- **4 PDFs con n_pages=0**: corruptos/vacios desde Fase 1. Irrecuperables. Listado:
  - `_Camara de comercio Centro Oriente 14 enero.pdf`
  - `_Camara de comercio Fundacion Ernesto 14 enerp.pdf`
  - `6RUT Multiser Actualizado.pdf`
  - `13. GARANTIA DE SERIEDAD_1.pdf`

### Hallazgos e iteraciones durante el desarrollo

1. **Primera corrida: disco lleno.** El notebook procesaba los 1,014 docs (incluyendo digitales) y saturo el disco (10.4 GB). Se aplico **fix arquitectural** — solo procesar escaneados — reduciendo de 14 GB estimado a 1.9 GB reales.

2. **Bug: bloques sobreescritos.** El naming `image_bloque_NNNN.csv` empezaba desde 0001 en cada re-ejecucion, sobreescribiendo bloques previos. Se perdieron 50 filas del manifest en una re-corrida. **Arreglado:** ahora el numero de bloque continua desde el ultimo existente (ver celda del loop). El manifest se reconstruyo escaneando los JPGs en disco.

3. **Docs en formato imagen directa.** 9 cedulas/RUT/TP estan en el corpus como `.jpg`/`.jpeg`, no como PDF. El codigo inicial solo indexaba `.pdf`. **Arreglado:** ahora se indexan `.pdf`, `.jpg`, `.jpeg`, `.png`, y la funcion `load_page_as_image()` decide entre `fitz.open` (PDFs) y `cv2.imread` (imagenes directas).

### Observacion pendiente

En la Poliza del test visual (fig12) se observo que el `deskew` sobre-corrige ligeramente en docs casi-rectos. Monitorear impacto en OCR. Si el CER de Polizas sube significativamente vs benchmark del nb 03, ajustar `deskew()` con un umbral minimo de angulo (no rotar si |angulo| < 1°).

---

## Siguiente paso — Notebook 05 (OCR)

Con `image_manifest.csv` listo, el Notebook 05 (`05_ocr_corpus.ipynb`):

1. Lee el manifest.
2. Por cada pagina:
   - **Escaneado** → EasyOCR (CPU) sobre la imagen procesada.
   - **Digital** → PyMuPDF sobre el PDF original (no usa la imagen).
3. Reconstruye texto desde bboxes + consolida en `corpus_ocr.csv`.
4. Valida contra los 15 docs del gold seed.

**Artefactos producidos por este notebook:**

| Archivo | Ubicacion | En repo? |
|---|---|---|
| `image_manifest.csv` | `data/processed/` | ✅ (metadata pequena) |
| `processed_{md5}_page_{N}.jpg` | `data/processed/images/` | ❌ (1.9 GB, gitignore) |
| CSVs de bloque | `data/processed/image_blocks/` | ❌ (intermedios) |
| `processed_log.csv` | `data/processed/image_blocks/` | ❌ (intermedio) |
| `fig12_preprocesamiento_test.png` | `data/processed/` | ✅ (evidencia visual) |

**Para re-correr:** `Run All`. Detecta JPGs existentes via cache y salta lo ya procesado.
**Para forzar reprocesamiento completo:** `FORCE_REPROCESS = True` en celda de setup.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# ESCRIBIR NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out_path = Path(__file__).parent / '04_preprocesamiento_imagenes.ipynb'
nbf.write(nb, out_path)
print(f'Notebook generado: {out_path}  ({len(cells)} celdas)')
