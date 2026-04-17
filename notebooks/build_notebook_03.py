"""
Genera el notebook 03_benchmark_ocr.ipynb
Ejecutar: python notebooks/build_notebook_03.py

Sigue el mismo patron que build_notebook_02.py: celdas markdown
explicativas antes de cada bloque de codigo, con referencias al plan
CRISP-DM++ (secciones 2.1.1 y 2.1.2) y a OCR_BENCHMARK.md.
"""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []

def md(src):  return nbf.v4.new_markdown_cell(src)
def code(src): return nbf.v4.new_code_cell(src)


# ══════════════════════════════════════════════════════════════════════════════
# 1. PORTADA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""# SinergIA Lab — Benchmark OCR
## Fase 2 CRISP-DM++ · §2.1.1 — Seleccion del Motor OCR Ganador

---

### Por que este notebook?

En Fase 1 descubrimos que **428 de 1,014 documentos (42%) son escaneados**, lo que significa que su texto no se puede leer directamente con PyMuPDF — necesitamos OCR. El problema es que **no todos los motores OCR se comportan igual**: algunos son mas precisos pero lentos, otros son rapidos pero tropiezan con ruido. Antes de generar pre-anotaciones sobre el corpus escaneado, tenemos que decidir con datos cual motor usar.

Este notebook ejecuta un **benchmark cuantitativo** sobre una muestra pequena pero representativa del corpus (15 documentos) para responder:

> *De los motores OCR compatibles con nuestro entorno, ¿cual produce mejor texto y mas util para el NER downstream, y a que costo en tiempo?*

### Referencias

- Plan maestro: `PLAN_MODELADO_CRISPDM.md` §2.1.1 (benchmark) y §2.1.2 (gold standard)
- Bitacora de procedimiento y hallazgos: `OCR_BENCHMARK.md`

### Estructura del notebook

| Seccion | Que hace | Tipo |
|---|---|---|
| A | Selecciona 15 documentos estratificados (gold seed) | codigo |
| B | Genera plantillas vacias de transcripcion | codigo |
| C | Transcripcion manual del ground truth | **trabajo humano** |
| D | Wrappers unificados de los motores OCR | codigo |
| E | Ejecucion del benchmark | codigo |
| F | Analisis de metricas + figuras | codigo |
| G | Decision final documentada | markdown |
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. MOTORES CANDIDATOS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Motores candidatos

| Motor | Tipo | Rol | Por que dentro / fuera |
|---|---|---|---|
| **PyMuPDF** | Extractor nativo | Fuera del benchmark | Decision ya tomada para PDFs digitales (`es_escaneado == False`). No es OCR. |
| **EasyOCR** | Deep learning (PyTorch) | Candidato | Baseline de Fase 1. Soporta espanol, robusto con ruido y rotaciones. |
| **Tesseract 5** | LSTM clasico | Candidato | Rapido, maduro, liviano. Requiere preprocesamiento cuando hay ruido fuerte. |
| ~~PaddleOCR~~ | — | Descartado | Incompatible con Python 3.12 (decision v1.2 del plan). |
| ~~Donut~~ | — | Descartado | No es OCR — es un modelo imagen→JSON de extremo a extremo que reemplazaria el pipeline completo. Evaluado y rechazado como arquitectura global en §ALT-1 del plan (corpus heterogeneo, ignora la ventaja de PDFs digitales, base en ingles, no escala a CC multipagina). Solo seria revisitable para Cedulas si F1 final resulta insuficiente en Fase 4. |
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 3. GOLD STANDARD
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Que es el Gold Standard y por que 15 documentos

**Gold Standard** = conjunto reducido de documentos anotados manualmente con maxima rigurosidad, usado como "verdad absoluta" para medir desempeno. Sin gold no se puede responder *"¿mi modelo funciona?"* — solo *"mi modelo corre sin errores"*, que no es lo mismo.

**Propiedades clave:**
- **Pequeno pero representativo:** la estadistica no necesita miles de docs; necesita variedad controlada.
- **Inmutable tras validacion:** no se toca mientras desarrollamos, para poder comparar versiones.
- **Separado del training:** estos docs nunca entran al entrenamiento del modelo.

### Composicion del gold seed (15 docs)

Este es un **seed** pequeno para el benchmark OCR. El gold completo (70 docs con doble anotacion y Kappa ≥ 0.85) se construira en Fase 3.

| Tipologia | Docs | Criterio |
|---|---|---|
| Cedula | 6 | 3 alta calidad + 3 ruidosas (tipologia mas critica: 93% escaneadas) |
| RUT | 3 | Escaneados (minoria del corpus RUT) |
| Poliza | 3 | Escaneadas |
| Camara de Comercio | 3 | Escaneadas |

Clasificacion de calidad:
- **alta calidad:** `blur_score >= 100` AND `contrast >= 30`
- **ruidosa:** `blur_score < 100` OR `contrast < 20`
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. METRICAS Y REGLA DE DECISION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Metricas y regla de decision

### Metricas

| Metrica | Como se calcula | Direccion | Para que sirve |
|---|---|---|---|
| **CER** (Character Error Rate) | `jiwer.cer(ref, hyp)` | ↓ menor es mejor | Calidad caracter a caracter |
| **WER** (Word Error Rate) | `jiwer.wer(ref, hyp)` | ↓ menor es mejor | Calidad palabra a palabra |
| **entity_recall** | % de entidades del ground truth recuperadas por regex en el OCR | ↑ mayor es mejor | Utilidad para NER downstream |
| **s_per_page** | `time.perf_counter()` / n_pages | ↓ menor es mejor | Costo operativo |

Normalizacion antes de CER/WER: minusculas + colapso de whitespace.

Patrones regex usados en `entity_recall`:

| Entidad | Patron |
|---|---|
| NIT | `\\b\\d{8,10}[-\\s]?\\d\\b` |
| Cedula | `\\b\\d{1,3}(?:[.\\s]\\d{3}){2,3}\\b` |
| Fecha | `\\b\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}\\b` |
| Monto | `\\$\\s?\\d{1,3}(?:[.,]\\d{3})+(?:[.,]\\d{1,2})?` |

### Regla de decision

1. Gana el motor con **menor CER** siempre que `t_ganador < 2 × t_mas_rapido` (no premiar precision a cualquier costo).
2. Empate en CER (±2%) → gana el de **mayor entity_recall** (el objetivo del proyecto es NER, no transcripcion perfecta).
3. Si cada motor gana en un regimen distinto (ruidoso vs limpio) → implementar **selector hibrido** `select_ocr(doc_metadata)` con umbrales sobre `blur_score` y `contrast`.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. SECCION A — SELECCION DEL GOLD SEED
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion A — Seleccion del Gold Seed

Construimos la muestra estratificada de 15 documentos escaneados. La seleccion es **reproducible** (random_state fijo) y se guarda como manifest en `data/gold/gold_seed_manifest.csv`.

### Imports y constantes

Cargamos librerias y fijamos rutas. `SEED = 42` garantiza que la seleccion sea identica entre ejecuciones.
"""))

cells.append(code("""import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
DATA_GOLD    = PROJECT_ROOT / 'data' / 'gold'
DATA_GOLD.mkdir(parents=True, exist_ok=True)
(DATA_GOLD / 'transcriptions').mkdir(parents=True, exist_ok=True)
(DATA_GOLD / 'ocr_output').mkdir(parents=True, exist_ok=True)

QUALITY_REPORT = DATA_PROC / 'quality_report_completo.csv'
MANIFEST_PATH  = DATA_GOLD / 'gold_seed_manifest.csv'

SEED = 42

# RESAMPLE = False: si existe un manifest valido en disco, se reutiliza (preserva
#                   las transcripciones manuales ya realizadas).
# RESAMPLE = True : ignora el manifest existente y muestrea desde cero.
#                   SOLO usar al arrancar un gold seed nuevo — pierdes alineacion
#                   con las transcripciones actuales.
RESAMPLE = False

PLAN = {
    'CEDULA':        {'alta': 3, 'ruidosa': 3},
    'rut':           {'cualquiera': 3},
    'POLIZA':        {'cualquiera': 3},
    'CAMARA DE CIO': {'cualquiera': 3},
}
print('Rutas OK. RESAMPLE =', RESAMPLE)
print('Plan de muestreo:', PLAN)
"""))


cells.append(md("""### Cargar el reporte de calidad de Fase 1

Leemos `quality_report_completo.csv` y filtramos:
- Solo documentos escaneados (`es_escaneado == True`)
- Sin duplicados (`is_duplicate == False`)

**Importante:** NO derivamos la carpeta del `filepath` del CSV, porque ese campo fue escrito en Fase 1 y puede estar desactualizado si algun PDF se ha reclasificado despues (mover entre carpetas). La carpeta real se deriva en el paso siguiente desde la ubicacion actual del archivo en disco, via el indice MD5. Asi, cualquier reclasificacion futura se respeta automaticamente sin parches manuales.
"""))

cells.append(code("""df_full = pd.read_csv(QUALITY_REPORT, encoding='utf-8-sig')
print(f'Corpus total: {len(df_full)} documentos')

df = df_full[(df_full['es_escaneado'] == True) & (df_full['is_duplicate'] == False)].copy()
print(f'Escaneados unicos: {len(df)}')
"""))


cells.append(md("""### Indexar `data/raw/` por MD5 y derivar carpeta desde disco

Indexamos cada PDF del corpus por su hash MD5. El indice nos da dos cosas:
1. **Ruta real** del archivo (resuelve nombres con mojibake como `CASTAÃÂO` → ruta correcta).
2. **Carpeta real** = nombre del directorio padre del PDF en disco.

Esta es la **unica fuente de verdad** para la clasificacion por tipologia en este notebook. Si un PDF se mueve entre carpetas, el selector lo ve en su nueva ubicacion automaticamente — sin tocar `quality_report_completo.csv`, sin patches en el manifest.
"""))

cells.append(code("""def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

print('Indexando data/raw/ por MD5 (puede tomar 1-2 min la primera vez)...')
md5_index = {}
for pdf in DATA_RAW.rglob('*.pdf'):
    md5_index[md5_file(pdf)] = pdf
print(f'  {len(md5_index)} PDFs indexados en disco')

# Derivar ruta actual y carpeta REAL desde el indice (no desde el CSV obsoleto)
df['local_path'] = df['md5'].map(lambda h: str(md5_index.get(h, '')))
df['folder']     = df['md5'].map(lambda h: md5_index[h].parent.name if h in md5_index else '')

missing = (df['local_path'] == '').sum()
print(f'  Sin match por MD5 en disco (excluidos): {missing}')
df = df[df['local_path'] != ''].reset_index(drop=True)

# Reconciliacion: reportar docs cuya carpeta actual difiere de la registrada en Fase 1
df['folder_fase1'] = df['filepath'].str.replace('\\\\', '/').str.split('/').str[-2]
reclassified = df[df['folder'] != df['folder_fase1']]
if len(reclassified):
    print(f'\\n  ⚠ {len(reclassified)} docs reclasificados desde Fase 1 (carpeta actual != Fase 1):')
    for _, r in reclassified.iterrows():
        print(f'     - {r[\"filename\"][:60]:<60}  {r[\"folder_fase1\"]} -> {r[\"folder\"]}')
else:
    print('  OK: ninguna reclasificacion detectada respecto a Fase 1.')

print('\\nDistribucion actual por carpeta (escaneados sin duplicados):')
print(df['folder'].value_counts())
"""))


cells.append(md("""### Construccion (o reutilizacion) del manifest

Dos rutas segun la bandera `RESAMPLE`:

1. **`RESAMPLE = False` (default)** — si `gold_seed_manifest.csv` existe y todos sus md5 estan presentes en disco, **se reutiliza**. Solo se refrescan los campos derivados (`local_path`, `folder`, `pages_to_use`) desde el indice MD5 y el corpus actual. Esto **preserva las transcripciones manuales** realizadas.

2. **`RESAMPLE = True`** — ignora el manifest y construye uno nuevo con muestreo estratificado (`random_state=SEED`). Uso unico: al arrancar un gold seed desde cero. Si ya hay transcripciones hechas, se quedan huerfanas.

El manifest resultante se guarda en `data/gold/gold_seed_manifest.csv`.
"""))

cells.append(code("""MAX_PAGES = 4  # cap uniforme para transcripcion manual y benchmark

def pick(df, folder, calidad, n, seed=SEED):
    sub = df[df['folder'] == folder].copy()
    if calidad == 'alta':
        sub = sub[(sub['blur_score'] >= 100) & (sub['contrast'] >= 30)]
    elif calidad == 'ruidosa':
        sub = sub[(sub['blur_score'] < 100) | (sub['contrast'] < 20)]
    if len(sub) < n:
        raise ValueError(f'{folder}/{calidad}: requeridos={n}, disponibles={len(sub)}')
    return sub.sample(n=n, random_state=seed).assign(gold_bucket=f'{folder}_{calidad}')

def build_fresh_manifest():
    picks = []
    for folder, buckets in PLAN.items():
        for calidad, n in buckets.items():
            picks.append(pick(df, folder, calidad, n))
    m = pd.concat(picks, ignore_index=True)
    return m

def refresh_derived(m):
    # Refresca campos derivados de fuentes actuales de verdad (md5_index + quality_report)
    m = m.copy()
    m['local_path'] = m['md5'].map(lambda h: str(md5_index.get(h, '')))
    m['folder']     = m['md5'].map(lambda h: md5_index[h].parent.name if h in md5_index else '')
    # n_pages, blur, contrast: del quality_report vigente.
    # El CSV puede tener md5 duplicados (archivos identicos); usamos la primera ocurrencia.
    meta_cols = ['n_pages', 'brightness', 'contrast', 'blur_score', 'quality_label', 'filename']
    meta = df_full.drop_duplicates(subset='md5', keep='first').set_index('md5')[meta_cols]
    for c in meta_cols:
        m[c] = m['md5'].map(meta[c])
    m['pages_to_use'] = m['n_pages'].clip(upper=MAX_PAGES)
    return m

if RESAMPLE:
    print('Modo RESAMPLE=True -> construyendo manifest desde cero...')
    manifest = build_fresh_manifest()
elif MANIFEST_PATH.exists():
    prev = pd.read_csv(MANIFEST_PATH, encoding='utf-8-sig')
    all_resolvable = prev['md5'].isin(md5_index).all()
    if all_resolvable and len(prev) == sum(sum(b.values()) for b in PLAN.values()):
        print(f'Reutilizando manifest existente ({len(prev)} docs). Refrescando campos derivados...')
        manifest = refresh_derived(prev[['md5', 'gold_bucket']])
    else:
        print('Manifest existente invalido (md5 faltantes o tamano incorrecto) -> rehaciendo desde cero...')
        manifest = build_fresh_manifest()
else:
    print('No hay manifest previo -> construyendo desde cero...')
    manifest = build_fresh_manifest()

manifest = manifest[[
    'local_path', 'filename', 'folder', 'gold_bucket',
    'n_pages', 'pages_to_use', 'brightness', 'contrast', 'blur_score',
    'quality_label', 'md5',
]]
manifest.to_csv(MANIFEST_PATH, index=False, encoding='utf-8-sig')
print(f'Gold seed generado: {len(manifest)} docs')
print(f'Manifest: {MANIFEST_PATH}')
manifest[['folder', 'gold_bucket', 'n_pages', 'blur_score', 'contrast']]
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. SECCION B — PLANTILLAS DE TRANSCRIPCION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion B — Generacion de plantillas de transcripcion

Para cada documento del gold seed creamos un archivo `.txt` vacio en `data/gold/transcriptions/{md5}.txt`. El archivo contiene:
- Encabezado con metadatos y ruta del PDF.
- Instrucciones para el anotador humano.
- Un marcador `<<< INICIO >>>` donde se pega la transcripcion.

Si una plantilla ya existe, **no se sobreescribe** (protege el trabajo manual).
"""))

cells.append(code("""TEMPLATE = '''# Ground-truth transcription para benchmark OCR
# ---------------------------------------------------------------
# filename      : {filename}
# folder        : {folder}
# n_pages       : {n_pages}
# pages_to_use  : 1 a {pages_to_use}  <-- TRANSCRIBIR SOLO ESTAS PAGINAS
# md5           : {md5}
# blur_score    : {blur_score}
# contrast      : {contrast}
# ---------------------------------------------------------------
# INSTRUCCIONES:
#   1. Abre el PDF: {local_path}
#   2. Transcribe el texto visible SOLO de las paginas 1 a {pages_to_use}.
#   3. Preserva saltos de linea entre bloques/parrafos.
#   4. NO corrijas ortografia — refleja lo impreso literalmente.
#   5. Entre paginas inserta una linea en blanco doble.
#   6. BORRA estas lineas de instrucciones antes de guardar.
#   7. Guarda en UTF-8 sin BOM.
# ---------------------------------------------------------------

<<< INICIO DE LA TRANSCRIPCION — BORRAR ESTA LINEA Y ESCRIBIR ABAJO >>>

'''

TRANSCRIPTIONS_DIR = DATA_GOLD / 'transcriptions'
created = skipped = 0
for _, row in manifest.iterrows():
    out = TRANSCRIPTIONS_DIR / f\"{row['md5']}.txt\"
    if out.exists():
        skipped += 1
        continue
    out.write_text(TEMPLATE.format(**row.to_dict()), encoding='utf-8')
    created += 1
print(f'Plantillas creadas: {created}   (existentes respetadas: {skipped})')
print(f'Directorio: {TRANSCRIPTIONS_DIR.resolve()}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. SECCION C — TRANSCRIPCION MANUAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion C — Transcripcion manual (trabajo humano)

**⚠️ Esta seccion no tiene codigo — es trabajo humano.** El notebook no puede avanzar a la Seccion E hasta que las 15 transcripciones esten completas.

### Instrucciones

Para cada archivo en `data/gold/transcriptions/{md5}.txt`:

1. Abrir el PDF indicado en el encabezado de la plantilla.
2. Transcribir **TODO** el texto visible, en orden natural de lectura.
3. Preservar saltos de linea entre bloques.
4. **NO** corregir ortografia — reflejar lo impreso literalmente.
5. Entre paginas: linea en blanco doble.
6. Borrar el encabezado de instrucciones.
7. Guardar en UTF-8 sin BOM.

### Tiempo estimado

- 15–25 minutos por documento × 15 = **4–6 horas totales**.
- Se recomienda dividir en 3 sesiones de 5 docs.

### Checklist (marcar a mano)

- [ ] 6 Cedulas transcritas (3 alta calidad + 3 ruidosas)
- [ ] 3 RUT transcritos
- [ ] 3 Polizas transcritas
- [ ] 3 CC transcritas
- [ ] Todas guardadas en UTF-8
- [ ] Encabezados de instrucciones borrados en todas

### Validacion rapida (ejecutar cuando termines)

La celda siguiente verifica que cada `.txt` tenga contenido real (no solo el template).
"""))

cells.append(code("""def transcription_ready(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding='utf-8')
    # Consideramos 'lista' si tiene >200 chars utiles (no solo el template)
    clean = re.sub(r'#.*', '', text)
    clean = clean.replace('<<< INICIO DE LA TRANSCRIPCION — BORRAR ESTA LINEA Y ESCRIBIR ABAJO >>>', '')
    return len(clean.strip()) > 200

status = []
for _, row in manifest.iterrows():
    p = TRANSCRIPTIONS_DIR / f\"{row['md5']}.txt\"
    status.append({
        'folder': row['folder'],
        'filename': row['filename'],
        'ready': transcription_ready(p),
        'chars': len(p.read_text(encoding='utf-8')) if p.exists() else 0,
    })
status_df = pd.DataFrame(status)
ready = status_df['ready'].sum()
print(f'Transcripciones listas: {ready}/{len(status_df)}')
status_df
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. SECCION D — WRAPPERS OCR
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion D — Wrappers OCR unificados

Definimos una interfaz comun para los motores. Cada motor expone un metodo `.run(pdf_path) -> OCRResult` que:
- Renderiza el PDF a imagenes a 300 DPI con PyMuPDF.
- Ejecuta OCR pagina por pagina.
- Mide tiempo por pagina y total.
- Captura errores sin romper el loop del benchmark.

### Estructura `OCRResult` y utilidades compartidas
"""))

cells.append(code("""import io
import fitz
import numpy as np
from PIL import Image

RENDER_DPI = 300

@dataclass
class OCRResult:
    engine: str
    pdf_path: str
    text: str
    n_pages: int
    elapsed_s: float
    per_page_s: list = field(default_factory=list)
    error: str = None

def pdf_pages_as_images(pdf_path: Path, dpi: int = RENDER_DPI, max_pages: int = None):
    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for i, page in enumerate(doc):
        if max_pages is not None and i >= max_pages:
            break
        pix = page.get_pixmap(matrix=mat, alpha=False)
        images.append(Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB'))
    doc.close()
    return images

print('OCRResult y pdf_pages_as_images definidos.')
"""))


cells.append(md("""### Motor 1 — EasyOCR

Deep learning basado en PyTorch. Carga el modelo de espanol (~60 MB). La primera ejecucion descarga pesos; las siguientes los reutilizan.
"""))

cells.append(code("""class EasyOCREngine:
    name = 'easyocr'
    def __init__(self, languages=('es',), gpu=False):
        import easyocr
        self.reader = easyocr.Reader(list(languages), gpu=gpu, verbose=False)

    def run(self, pdf_path: Path, max_pages: int = None) -> OCRResult:
        t0 = time.perf_counter()
        per_page = []
        try:
            images = pdf_pages_as_images(pdf_path, max_pages=max_pages)
            chunks = []
            for img in images:
                p0 = time.perf_counter()
                lines = self.reader.readtext(np.array(img), detail=0, paragraph=True)
                chunks.append('\\n'.join(lines))
                per_page.append(time.perf_counter() - p0)
            return OCRResult(
                engine=self.name, pdf_path=str(pdf_path),
                text='\\n\\n'.join(chunks), n_pages=len(images),
                elapsed_s=time.perf_counter() - t0, per_page_s=per_page,
            )
        except Exception as e:
            return OCRResult(
                engine=self.name, pdf_path=str(pdf_path), text='',
                n_pages=0, elapsed_s=time.perf_counter() - t0,
                per_page_s=per_page, error=f'{type(e).__name__}: {e}',
            )
print('EasyOCREngine listo.')
"""))


cells.append(md("""### Motor 2 — Tesseract 5

Clasico LSTM. Requiere:
1. Binario `tesseract.exe` (Windows: instalador de UB Mannheim).
2. Paquete de idioma `spa.traineddata`.

**Descubrimiento automatico:**
- Ejecutable: busca en `C:\\Program Files\\Tesseract-OCR\\tesseract.exe` (default del instalador). Si no esta ahi, ajusta `TESSERACT_CMD` abajo.
- Datos de idioma: usa la carpeta local del proyecto `tessdata/` si existe (asi evitamos necesitar permisos de admin para instalar idiomas en Program Files). Si no existe, usa el `tessdata` global de la instalacion.
"""))

cells.append(code("""import os, shutil

# Descubrimiento automatico del binario Tesseract
def _find_tesseract():
    found = shutil.which('tesseract')
    if found:
        return found
    for p in [r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
              r'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe']:
        if Path(p).exists():
            return p
    return None

TESSERACT_CMD = _find_tesseract()
print(f'Tesseract binary: {TESSERACT_CMD or \"NO ENCONTRADO — instalar desde https://github.com/UB-Mannheim/tesseract/wiki\"}')

# Datos de idioma: preferir tessdata/ local del proyecto.
# La forma robusta de apuntar a un tessdata custom es la variable de entorno
# TESSDATA_PREFIX (no usar --tessdata-dir en la config string: pytesseract
# tokeniza por espacios y las comillas terminan literalmente en la ruta).
LOCAL_TESSDATA = (PROJECT_ROOT / 'tessdata').resolve()
TESSDATA_PREFIX = str(LOCAL_TESSDATA) if LOCAL_TESSDATA.exists() else None
if TESSDATA_PREFIX:
    os.environ['TESSDATA_PREFIX'] = TESSDATA_PREFIX
    print(f'Usando tessdata local: {TESSDATA_PREFIX}')
else:
    print('tessdata local no encontrado — se usara el global de la instalacion.')


class TesseractEngine:
    name = 'tesseract'
    def __init__(self, lang='spa', psm=3, tesseract_cmd=None, tessdata_prefix=None):
        import pytesseract
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        if tessdata_prefix:
            os.environ['TESSDATA_PREFIX'] = tessdata_prefix
        self.pytesseract = pytesseract
        self.lang = lang
        self.config = f'--psm {psm}'

    def run(self, pdf_path: Path, max_pages: int = None) -> OCRResult:
        t0 = time.perf_counter()
        per_page = []
        try:
            images = pdf_pages_as_images(pdf_path, max_pages=max_pages)
            chunks = []
            for img in images:
                p0 = time.perf_counter()
                txt = self.pytesseract.image_to_string(img, lang=self.lang, config=self.config)
                chunks.append(txt)
                per_page.append(time.perf_counter() - p0)
            return OCRResult(
                engine=self.name, pdf_path=str(pdf_path),
                text='\\n\\n'.join(chunks), n_pages=len(images),
                elapsed_s=time.perf_counter() - t0, per_page_s=per_page,
            )
        except Exception as e:
            return OCRResult(
                engine=self.name, pdf_path=str(pdf_path), text='',
                n_pages=0, elapsed_s=time.perf_counter() - t0,
                per_page_s=per_page, error=f'{type(e).__name__}: {e}',
            )

print('TesseractEngine listo.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 9. SECCION E — EJECUCION DEL BENCHMARK
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion E — Ejecucion del benchmark

Recorremos cada (documento × motor), calculamos metricas contra el ground truth transcrito y acumulamos filas en `ocr_benchmark.csv`.

### Funciones de metricas: CER, WER, entity_recall
"""))

cells.append(code("""import jiwer

ENTITY_PATTERNS = {
    'nit':    re.compile(r'\\b\\d{8,10}[-\\s]?\\d\\b'),
    'cedula': re.compile(r'\\b\\d{1,3}(?:[.\\s]\\d{3}){2,3}\\b'),
    'fecha':  re.compile(r'\\b\\d{1,2}[/-]\\d{1,2}[/-]\\d{2,4}\\b'),
    'monto':  re.compile(r'\\$\\s?\\d{1,3}(?:[.,]\\d{3})+(?:[.,]\\d{1,2})?'),
}

def normalize(text: str) -> str:
    return re.sub(r'\\s+', ' ', text.lower()).strip()

def cer_wer(reference: str, hypothesis: str):
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return (1.0 if hyp else 0.0, 1.0 if hyp else 0.0)
    return jiwer.cer(ref, hyp), jiwer.wer(ref, hyp)

def entity_recall(reference: str, hypothesis: str):
    per_type = {}
    total_ref = total_hit = 0
    hyp_norm = normalize(hypothesis)
    for name, pat in ENTITY_PATTERNS.items():
        ref_hits = {m.group(0) for m in pat.finditer(reference)}
        hyp_hits = {m.group(0) for m in pat.finditer(hypothesis)}
        hyp_hits_norm = {m.group(0) for m in pat.finditer(hyp_norm)}
        hits = sum(1 for e in ref_hits if e in hyp_hits or e.lower() in hyp_hits_norm)
        per_type[name] = {'ref': len(ref_hits), 'hit': hits,
                          'recall': (hits / len(ref_hits)) if ref_hits else None}
        total_ref += len(ref_hits)
        total_hit += hits
    recall = (total_hit / total_ref) if total_ref else 0.0
    return {'total_ref': total_ref, 'total_hit': total_hit,
            'recall': recall, 'per_type': per_type}

print('Funciones de metricas listas.')
"""))


cells.append(md("""### Loop principal del benchmark

- Filtra el gold seed a solo los documentos con transcripcion lista.
- Inicializa cada motor una sola vez.
- Por cada documento corre ambos motores y acumula una fila de metricas.
- Guarda el texto crudo en `data/gold/ocr_output/{engine}/{md5}.txt` para inspeccion cualitativa posterior.
"""))

cells.append(code("""ENGINES_TO_RUN = ['easyocr', 'tesseract']  # ajustar si quieres correr solo uno

ready_mask = manifest['md5'].map(lambda h: transcription_ready(TRANSCRIPTIONS_DIR / f'{h}.txt'))
bench_df = manifest[ready_mask].reset_index(drop=True)
print(f'Documentos con transcripcion lista: {len(bench_df)}/{len(manifest)}')

if len(bench_df) == 0:
    print('⚠️  No hay transcripciones listas. Completa la Seccion C antes de continuar.')
    rows = []
else:
    engine_objs = {}
    if 'easyocr' in ENGINES_TO_RUN:
        print('Cargando EasyOCR...'); engine_objs['easyocr'] = EasyOCREngine()
    if 'tesseract' in ENGINES_TO_RUN:
        print('Cargando Tesseract...'); engine_objs['tesseract'] = TesseractEngine(tesseract_cmd=TESSERACT_CMD, tessdata_prefix=TESSDATA_PREFIX)

    rows = []
    for _, row in bench_df.iterrows():
        pdf_path = Path(row['local_path'])
        ref = (TRANSCRIPTIONS_DIR / f\"{row['md5']}.txt\").read_text(encoding='utf-8')
        print(f\"\\n[{row['folder']}] {row['filename']}\")
        max_p = int(row['pages_to_use'])
        for eng_name, engine in engine_objs.items():
            print(f'  > {eng_name} (pags 1-{max_p})...', end=' ', flush=True)
            result = engine.run(pdf_path, max_pages=max_p)
            out_dir = DATA_GOLD / 'ocr_output' / eng_name
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f\"{row['md5']}.txt\").write_text(result.text, encoding='utf-8')
            if result.error:
                print(f'ERROR {result.error}')
                rows.append({'md5': row['md5'], 'filename': row['filename'],
                             'folder': row['folder'], 'gold_bucket': row['gold_bucket'],
                             'n_pages': 0, 'engine': eng_name,
                             'elapsed_s': round(result.elapsed_s, 3),
                             's_per_page': None, 'cer': None, 'wer': None,
                             'entity_recall': None, 'entities_ref': None,
                             'entities_hit': None, 'error': result.error})
                continue
            cer, wer = cer_wer(ref, result.text)
            er = entity_recall(ref, result.text)
            print(f\"cer={cer:.3f} wer={wer:.3f} ent={er['recall']:.2f} t={result.elapsed_s:.1f}s\")
            rows.append({'md5': row['md5'], 'filename': row['filename'],
                         'folder': row['folder'], 'gold_bucket': row['gold_bucket'],
                         'n_pages': result.n_pages, 'engine': eng_name,
                         'elapsed_s': round(result.elapsed_s, 3),
                         's_per_page': round(result.elapsed_s / max(result.n_pages, 1), 3),
                         'cer': round(cer, 4), 'wer': round(wer, 4),
                         'entity_recall': round(er['recall'], 4),
                         'entities_ref': er['total_ref'],
                         'entities_hit': er['total_hit'],
                         'error': None})
bench_out = pd.DataFrame(rows)
if len(bench_out):
    bench_out.to_csv(DATA_PROC / 'ocr_benchmark.csv', index=False, encoding='utf-8-sig')
    print(f\"\\nGuardado: {DATA_PROC / 'ocr_benchmark.csv'}\")
bench_out
"""))


cells.append(md("""### Guardar resumen agregado

Dos agregaciones:
- Por motor (promedio global).
- Por motor × tipologia (para detectar si un motor gana en un regimen y otro en otro).
"""))

cells.append(code("""if len(bench_out):
    summary_engine = (bench_out.groupby('engine')
                      .agg(n=('md5','count'),
                           cer_mean=('cer','mean'),
                           wer_mean=('wer','mean'),
                           entity_recall_mean=('entity_recall','mean'),
                           s_per_page_mean=('s_per_page','mean'))
                      .round(4).reset_index())

    summary_cross = (bench_out.groupby(['engine','folder'])
                     .agg(n=('md5','count'),
                          cer_mean=('cer','mean'),
                          wer_mean=('wer','mean'),
                          entity_recall_mean=('entity_recall','mean'),
                          s_per_page_mean=('s_per_page','mean'))
                     .round(4).reset_index())

    summary_cross.to_csv(DATA_PROC / 'ocr_benchmark_summary.csv', index=False, encoding='utf-8-sig')
    print('Resumen por motor:')
    print(summary_engine.to_string(index=False))
    print('\\nResumen por motor x tipologia:')
    print(summary_cross.to_string(index=False))
else:
    summary_engine = summary_cross = pd.DataFrame()
    print('Sin datos — ejecuta la Seccion E primero.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 10. SECCION F — ANALISIS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion F — Analisis visual

Dos figuras clave:
1. **Barras CER por motor y tipologia** — identifica si un motor gana consistentemente o solo en algunas tipologias.
2. **Scatter CER vs tiempo** — compromiso precision/costo. Cuadrante inferior-izquierdo = ideal.
"""))

cells.append(code("""import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if len(bench_out):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Barras CER por motor x tipologia
    pivot = summary_cross.pivot(index='folder', columns='engine', values='cer_mean')
    pivot.plot(kind='bar', ax=axes[0])
    axes[0].set_title('CER medio por motor y tipologia (menor es mejor)')
    axes[0].set_ylabel('CER'); axes[0].set_xlabel('')
    axes[0].tick_params(axis='x', rotation=30)
    axes[0].grid(axis='y', alpha=0.3)

    # Scatter CER vs tiempo por doc
    for eng in bench_out['engine'].unique():
        sub = bench_out[bench_out['engine'] == eng]
        axes[1].scatter(sub['s_per_page'], sub['cer'], label=eng, alpha=0.7, s=80)
    axes[1].set_xlabel('Segundos por pagina')
    axes[1].set_ylabel('CER')
    axes[1].set_title('Compromiso precision vs tiempo (ideal: esquina inferior-izquierda)')
    axes[1].legend(); axes[1].grid(alpha=0.3)

    plt.tight_layout()
    fig_path = DATA_PROC / 'fig11_ocr_benchmark.png'
    plt.savefig(fig_path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f'Figura guardada: {fig_path}')
else:
    print('Sin datos — ejecuta la Seccion E primero.')
"""))


cells.append(md("""### Inspeccion cualitativa — docs con mayor discrepancia entre motores

Listamos los 3 documentos donde los motores difieren mas en CER. Estos son los candidatos a revisar visualmente para entender si hay un patron (ej. un motor falla en fondos oscuros).
"""))

cells.append(code("""if len(bench_out) and bench_out['engine'].nunique() >= 2:
    wide = bench_out.pivot(index=['md5','filename','folder'], columns='engine', values='cer').reset_index()
    wide['diff'] = (wide['easyocr'] - wide['tesseract']).abs()
    top = wide.sort_values('diff', ascending=False).head(3)
    print('Documentos con mayor discrepancia CER entre motores:')
    print(top[['filename','folder','easyocr','tesseract','diff']].to_string(index=False))
else:
    print('Se necesita al menos 2 motores ejecutados para comparar.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 11. SECCION G — DECISION FINAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---

## Seccion G — Decision final

**Fecha:** 2026-04-15 | **Estado:** Benchmark ejecutado y decision tomada.

### G.1 Recordatorio: ¿que mide cada metrica?

Antes de la decision, una vuelta rapida por las cuatro metricas que calculamos, para que la justificacion tenga sentido:

| Metrica | Que cuenta | Formula | Direccion |
|---|---|---|---|
| **CER** (Character Error Rate) | Caracteres mal leidos vs el ground truth | `(S + D + I) / N` a nivel caracter (Levenshtein) | ↓ menor = mejor |
| **WER** (Word Error Rate) | Palabras mal leidas vs el ground truth | `(S + D + I) / N` a nivel palabra | ↓ menor = mejor |
| **entity_recall** | Fraccion de entidades clave del GT recuperadas por regex en el OCR | `entidades_OCR ∩ entidades_GT / entidades_GT` | ↑ mayor = mejor |
| **s_per_page** | Tiempo medio de inferencia por pagina | `tiempo_total / n_paginas` | ↓ menor = mejor |

**Donde S/D/I/N son:** Sustituciones, Deleciones, Inserciones, y N = total de unidades (caracteres o palabras) en el ground truth.

**Normalizacion previa a CER/WER:** minusculas + colapso de whitespace (evita castigar diferencias triviales de espaciado).

**Entidades consideradas en entity_recall** (regex aplicados tanto al GT como al OCR):
- **NIT:** `\\\\b\\\\d{8,10}[-\\\\s]?\\\\d\\\\b`
- **Cedula:** `\\\\b\\\\d{1,3}(?:[.\\\\s]\\\\d{3}){2,3}\\\\b`
- **Fecha:** `\\\\b\\\\d{1,2}[/-]\\\\d{1,2}[/-]\\\\d{2,4}\\\\b`
- **Monto:** `\\\\$\\\\s?\\\\d{1,3}(?:[.,]\\\\d{3})+(?:[.,]\\\\d{1,2})?`

**¿Por que entity_recall es la metrica mas importante para este proyecto?** Porque el objetivo final NO es transcripcion perfecta — es extraccion de entidades. Un motor con CER = 0.30 (mucho ruido general) pero entity_recall = 1.00 (recupera TODOS los NIT, fechas, montos) sirve perfectamente para el pipeline NER downstream. Esto explica por que Tesseract "pierde" en CER global pero "gana" en Camara de Comercio: destroza el texto ambiental pero identifica con precision los numeros clave.

**¿Por que no basta CER solo?** Porque un solo caracter mal en `$1.234.567` puede cambiar un monto (grave para ingesta financiera). Pero CER no captura esa importancia relativa — trata todos los caracteres igual. Por eso emparejamos CER + entity_recall.

**¿Por que incluir s_per_page?** Porque el corpus tiene 428 docs escaneados. Un motor 10x mas lento implica dias en lugar de horas para re-OCR. Lo usamos como restriccion de la regla de decision (`t_ganador < 2 × t_mas_rapido`).

---

### G.2 Resultado del benchmark

**Globales:**

| Motor | N | CER medio | WER medio | Entity recall | s/pag | Errores |
|---|---|---|---|---|---|---|
| **EasyOCR (CPU)** | 15 | **0.276** | 0.476 | 0.551 | 46.02 | 0 |
| **Tesseract 5.5** | 15 | 0.446 | 0.557 | **0.605** | **5.06** | 0 |

**Por tipologia:**

| Tipologia | EasyOCR CER | Tesseract CER | EasyOCR entity | Tesseract entity | Ganador |
|---|---|---|---|---|---|
| Cedula | **0.333** | 0.782 | **0.444** | 0.111 | 🏆 EasyOCR (abrumador) |
| RUT | **0.289** | 0.394 | 0.889 | 0.889 | EasyOCR (marginal) / Tesseract (10x mas rapido, igual entity) |
| Poliza | 0.329 | **0.226** | 0.649 | **0.951** | 🏆 Tesseract |
| Camara de Comercio | 0.096 | **0.047** | 0.326 | **0.963** | 🏆 Tesseract (contundente) |

---

### G.3 Aplicacion de la regla de decision

**Regla #1** (menor CER global con `t_ganador < 2 × t_mas_rapido`):
- EasyOCR tiene menor CER global (0.276 vs 0.446) ✓
- Pero EasyOCR es **9x mas lento** que Tesseract ✗ → viola la restriccion.
- EasyOCR NO gana por regla #1.

**Regla #2** (empate CER ±2% → mayor entity_recall): no aplica, diferencia global es 17 puntos.

**Regla #3** (regimen mixto → selector hibrido): aplica.
- EasyOCR domina en Cedula (CER 0.33 vs 0.78; entity 0.44 vs 0.11)
- Tesseract domina en CC y Poliza (CER menor, entity_recall muy superior, 10x mas rapido)
- RUT empata en entity_recall (0.89 ambos); Tesseract gana por velocidad.

**Conclusion:** selector hibrido.

---

### G.4 Decision final

**Motor para produccion CPU-only (estado actual del laboratorio):**

```python
def select_ocr(tipologia: str) -> str:
    if tipologia == 'Cedula':
        return 'easyocr'
    return 'tesseract'   # RUT, Poliza, Camara de Comercio
```

**Motor recomendado con GPU disponible (mediano plazo):** `EasyOCR` unificado para todo el corpus escaneado. Razones:
- Con GPU: ~46 s/pag → ~1 s/pag (40x mas rapido) → ya supera la restriccion de tiempo y gana por CER global.
- Pipeline mas simple: un solo motor, sin necesidad de clasificacion previa de tipologia antes del OCR.
- Mejor consistencia: sin el "talon de Aquiles" de Tesseract en Cedulas (33% del corpus).
- Tiempo estimado re-OCR corpus completo: **~20 h en CPU → ~30 min en GPU**.

---

### G.5 Metadatos de trazabilidad

- **Fecha de congelacion del gold seed:** 2026-04-15
- **Manifest:** `data/gold/gold_seed_manifest.csv` (15 docs, random_state=42, cap=4 paginas/doc)
- **Transcripciones ground truth:** `data/gold/transcriptions/` — inmutables desde esta fecha
- **EasyOCR version:** 1.7.2 (modelos espanol, CPU)
- **Tesseract version:** 5.5.0 (spa.traineddata en `tessdata/` local del proyecto)
- **Ambiente:** Python 3.12.10, Windows 11, CPU-only
- **Outputs:** `data/processed/ocr_benchmark.csv`, `ocr_benchmark_summary.csv`, `fig11_ocr_benchmark.png`

---

### G.6 Proximos pasos

1. ✅ Bitacora actualizada: `OCR_BENCHMARK.md` Parte 2 contiene los hallazgos.
2. ✅ §2.1.1 marcado como completado en `PLAN_MODELADO_CRISPDM.md`.
3. ⏳ Implementar `select_ocr(tipologia)` en `src/preprocessing/pipeline.py` reemplazando el default EasyOCR.
4. ⏳ Gestionar acceso a GPU con PUJ/el laboratorio para la siguiente iteracion.
5. ⏳ Continuar con Fase 2 §2.2 — pre-anotaciones RUT con el OCR correspondiente segun tipologia.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# ESCRIBIR NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out_path = Path(__file__).parent / '03_benchmark_ocr.ipynb'
nbf.write(nb, out_path)
print(f'Notebook generado: {out_path}  ({len(cells)} celdas)')
