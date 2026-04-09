"""
Genera el notebook 01_analisis_descriptivo_secop.ipynb
Ejecutar: python notebooks/build_notebook.py
"""
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
cells = []

def md(src): return nbf.v4.new_markdown_cell(src)
def code(src): return nbf.v4.new_code_cell(src)

# ══════════════════════════════════════════════════════════════════════════════
# PORTADA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""# SinergIA Lab — Análisis Exploratorio del Corpus SECOP
## Fase 1 CRISP-DM++: Comprensión de los Datos

---

### ¿Qué hace este notebook?

Este notebook analiza en profundidad los documentos que usaremos para entrenar la inteligencia artificial de SinergIA Lab. Antes de entrenar cualquier modelo, necesitamos entender muy bien los datos que tenemos.

Piénsalo así: antes de enseñarle a alguien a leer documentos legales, primero debes saber qué tan largos son, qué tan difíciles están escritos, si están en buen estado, y qué información contienen. Eso es exactamente lo que hace este notebook.

### ¿Qué vamos a descubrir?

| Sección | Pregunta que responde |
|---|---|
| 1. Inventario | ¿Cuántos documentos tenemos por tipo? |
| 2. Calidad visual | ¿Están los documentos en buen estado para ser leídos por la IA? |
| 3. Extracción de texto | ¿Cuánto texto tiene cada tipo de documento? |
| 4. Conteos básicos | ¿Cuántas palabras, oraciones y sílabas tienen? |
| 5. Legibilidad | ¿Qué tan difícil está escrito cada tipo de documento? |
| 6. Legibilidad en español | Métricas especialmente diseñadas para textos en español |
| 7. Patrones de entidades | ¿Con qué frecuencia aparecen NITs, cédulas, fechas y montos? |
| 8. Estadística | ¿Las diferencias entre tipos de documento son reales o aleatorias? |
| 9. Exportación | Guardar todos los resultados para usarlos en la siguiente fase |

### Corpus analizado
- **Cédulas de Ciudadanía:** 334 documentos
- **RUT (DIAN):** 235 documentos
- **Pólizas de Seguros:** 219 documentos
- **Cámara de Comercio:** 212 documentos
- **Otros:** 14 documentos

> 📋 **Nota legal:** Todo el procesamiento ocurre localmente en tu computador. Ningún documento sale del entorno. Cumplimiento: Ley 1581/2012 (Habeas Data) + Circular SIC 002/2024.
"""))

# ══════════════════════════════════════════════════════════════════════════════
# CÓMO USAR
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## ¿Cómo usar este notebook?

1. **Ejecuta las celdas en orden**, de arriba hacia abajo. Cada celda de código tiene un botón ▶ al lado izquierdo.
2. **Las celdas grises** contienen código Python — no necesitas entenderlo, solo ejecutarlo.
3. **Las celdas blancas** (como esta) contienen explicaciones en texto.
4. **Los resultados** aparecen automáticamente debajo de cada celda de código.
5. Si una celda tarda mucho, es normal — espera a que el símbolo `[*]` cambie a un número.

> ⚠️ **Importante:** Ejecuta primero la **Sección 0 (Configuración)** antes que cualquier otra sección. Sin ella, el resto del notebook no funcionará.
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 0: CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 0 — Configuración Inicial

Esta celda carga todas las herramientas que el notebook necesita para funcionar. Es como abrir la caja de herramientas antes de empezar a trabajar.

**Herramientas que usamos:**
- **OpenCV:** analiza la calidad visual de las imágenes (como un inspector de documentos visual)
- **PyMuPDF:** lee y extrae el texto de los PDFs (como un lector de documentos)
- **textstat:** mide la complejidad del texto (como un analizador de legibilidad)
- **pandas / matplotlib / seaborn:** organiza los datos y crea las gráficas
"""))

cells.append(code("""# ── Instalación (ejecutar solo si ves errores de módulos no encontrados) ──────
# !pip install opencv-python pymupdf textstat pandas matplotlib seaborn scipy tqdm

import sys, json, hashlib, re, warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz                          # PyMuPDF — lectura de PDFs
import cv2                           # OpenCV  — análisis visual
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import textstat
from scipy import stats              # pruebas estadísticas (ANOVA)
from tqdm.notebook import tqdm

warnings.filterwarnings('ignore')

# ── Configuración de textstat para español ────────────────────────────────────
# Esto hace que las métricas de legibilidad usen las fórmulas adaptadas al español
textstat.set_lang("es")

# ── Rutas del proyecto ────────────────────────────────────────────────────────
PROJECT_ROOT = Path('..').resolve()
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
DATA_PROC.mkdir(parents=True, exist_ok=True)

# ── Tipologías y sus carpetas reales ──────────────────────────────────────────
CATEGORIES = {
    'Cédula':             DATA_RAW / 'CEDULA',
    'RUT':                DATA_RAW / 'rut',
    'Póliza':             DATA_RAW / 'POLIZA',
    'Cámara de Comercio': DATA_RAW / 'CAMARA DE CIO',
    'Otros':              DATA_RAW / 'OTROS',
}

SUPPORTED_EXT = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif'}

# ── Paleta de colores por tipología ──────────────────────────────────────────
PALETTE = {
    'Cédula':             '#4C72B0',
    'RUT':                '#DD8452',
    'Póliza':             '#55A868',
    'Cámara de Comercio': '#C44E52',
    'Otros':              '#8172B2',
}

# ── Estilo de gráficas ────────────────────────────────────────────────────────
sns.set_theme(style='whitegrid', font_scale=1.05)
plt.rcParams.update({'figure.dpi': 110, 'figure.figsize': (14, 5)})
np.random.seed(42)

# ── Umbrales de calidad visual (calibrados para PDFs digitales nativos) ───────
BLUR_THRESHOLD  = 100
BRIGHTNESS_LOW  = 60
BRIGHTNESS_HIGH = 253
CONTRAST_LOW    = 20

print('✅ Configuración completada.')
print(f'   Raíz del proyecto : {PROJECT_ROOT}')
print(f'   Carpeta de datos  : {DATA_RAW}')
print(f'   Python {sys.version.split()[0]} | pandas {pd.__version__} | textstat instalado')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1: INVENTARIO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 1 — ¿Cuántos documentos tenemos?

Antes de analizar el contenido, necesitamos saber exactamente con qué material trabajamos. Esta sección hace un inventario completo del corpus: cuántos documentos hay, de qué tipo, en qué formato y cuánto espacio ocupan.

También detectamos automáticamente **documentos duplicados** usando una "huella digital" (hash MD5) — si dos archivos producen la misma huella, son idénticos aunque tengan nombres distintos. Los duplicados en el conjunto de entrenamiento pueden inflar artificialmente las métricas del modelo.
"""))

cells.append(code("""def compute_md5(path: Path) -> str:
    \"\"\"Calcula la huella digital (hash MD5) de un archivo para detectar duplicados.\"\"\"
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8192), b''):
            h.update(block)
    return h.hexdigest()


def scan_corpus(categories: Dict[str, Path]) -> pd.DataFrame:
    \"\"\"Escanea todas las carpetas y construye el inventario del corpus.\"\"\"
    records = []
    for cat, folder in categories.items():
        if not folder.exists():
            print(f'  ⚠️  Carpeta no encontrada: {folder}')
            continue
        files = [f for f in folder.rglob('*')
                 if f.is_file() and f.suffix.lower() in SUPPORTED_EXT]
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


print('Escaneando corpus completo...')
df_corpus = scan_corpus(CATEGORIES)

# ── Resumen del inventario ────────────────────────────────────────────────────
n_total = len(df_corpus)
n_dup   = df_corpus['is_duplicate'].sum() if not df_corpus.empty else 0
size_mb = df_corpus['size_kb'].sum() / 1024 if not df_corpus.empty else 0

print(f'\\n══ INVENTARIO DEL CORPUS ══')
print(f'  Total de documentos   : {n_total:,}')
print(f'  Documentos únicos     : {n_total - n_dup:,}')
print(f'  Duplicados detectados : {n_dup}')
print(f'  Tamaño total          : {size_mb:.1f} MB')
print()

resumen = df_corpus.groupby('category').agg(
    documentos=('filename', 'count'),
    duplicados=('is_duplicate', 'sum'),
    size_mb=('size_kb', lambda x: round(x.sum()/1024, 2))
).reset_index()
resumen['% del corpus'] = (resumen['documentos'] / n_total * 100).round(1)
print(resumen.to_string(index=False))
"""))

cells.append(code("""# ── Gráficas de distribución ─────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Distribución del Corpus SECOP — SinergIA Lab', fontsize=14, fontweight='bold')

# Barras por tipología
cat_counts = df_corpus['category'].value_counts()
colors = [PALETTE.get(c, '#888') for c in cat_counts.index]
bars = axes[0].barh(cat_counts.index, cat_counts.values, color=colors, edgecolor='white')
for bar, v in zip(bars, cat_counts.values):
    axes[0].text(v + 1, bar.get_y() + bar.get_height()/2,
                 f'{v:,}  ({v/n_total*100:.1f}%)', va='center', fontsize=9)
axes[0].set_xlabel('Número de documentos')
axes[0].set_title('Documentos por tipología')
axes[0].set_xlim(0, cat_counts.max() * 1.3)

# Pie chart
axes[1].pie(cat_counts.values,
            labels=[c[:14] for c in cat_counts.index],
            autopct='%1.1f%%', colors=colors,
            startangle=90, textprops={'fontsize': 9})
axes[1].set_title('Proporción del corpus')

# Distribución de formatos
ext_counts = df_corpus['extension'].value_counts()
axes[2].bar(ext_counts.index, ext_counts.values,
            color=sns.color_palette('pastel', len(ext_counts)), edgecolor='grey')
for i, v in enumerate(ext_counts.values):
    axes[2].text(i, v + 1, str(v), ha='center', fontweight='bold')
axes[2].set_xlabel('Formato de archivo')
axes[2].set_ylabel('Cantidad')
axes[2].set_title('Documentos por formato')

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig01_inventario.png', bbox_inches='tight', dpi=150)
plt.show()

print('📊 Gráfica guardada: data/processed/fig01_inventario.png')

# Distribución de tamaños por tipología
fig, ax = plt.subplots(figsize=(14, 5))
for cat, color in PALETTE.items():
    sub = df_corpus[df_corpus['category'] == cat]['size_kb']
    if not sub.empty:
        ax.hist(sub, bins=30, alpha=0.6, color=color, label=cat, edgecolor='white')
ax.set_xlabel('Tamaño del archivo (KB)')
ax.set_ylabel('Frecuencia')
ax.set_title('Distribución de Tamaños por Tipología')
ax.legend()
plt.tight_layout()
plt.savefig(DATA_PROC / 'fig02_tamanos.png', bbox_inches='tight', dpi=150)
plt.show()

print('📊 Gráfica guardada: data/processed/fig02_tamanos.png')
print()
print('── Estadísticas de tamaño por tipología (KB) ──')
print(df_corpus.groupby('category')['size_kb']
      .agg(['mean','median','std','min','max']).round(1).to_string())
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 2: CALIDAD VISUAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 2 — ¿Están los documentos en buen estado?

Así como un escáner de documentos necesita que el papel esté limpio y bien posicionado, nuestra IA necesita que los documentos tengan buena calidad visual. Esta sección mide tres cosas clave:

- 🌟 **Brillo (Luminosidad):** ¿Está el documento muy oscuro o muy sobreexpuesto?
- 🎨 **Contraste:** ¿Se distingue claramente el texto del fondo?
- 🔍 **Nitidez (Blur Score):** ¿Está borroso o nítido?

**¿Cómo se clasifican los documentos?**
- ✅ **APTO:** Puede pasar directamente a la IA sin preprocesamiento
- ⚡ **REQUIERE PREPROCESAMIENTO:** Necesita ajustes antes de ser procesado
- ❌ **DESCARTADO:** Calidad irrecuperable, debe conseguirse nuevamente

> 💡 **¿Por qué importa esto?** Si le damos a la IA documentos borrosos o muy oscuros, aprenderá mal y cometerá errores al extraer información.
"""))

cells.append(code("""def load_image_first_page(filepath: str) -> Optional[np.ndarray]:
    \"\"\"Carga la primera página de un PDF o una imagen directamente.\"\"\"
    path = Path(filepath)
    try:
        if path.suffix.lower() == '.pdf':
            doc = fitz.open(str(path))
            if doc.page_count == 0:
                return None
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(120/72, 120/72),
                                     colorspace=fitz.csRGB)
            doc.close()
            return np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, 3)
        else:
            img = cv2.imread(str(path))
            return cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img is not None else None
    except Exception:
        return None


def analyze_visual_quality(img_rgb: np.ndarray) -> Dict:
    \"\"\"
    Calcula tres métricas de calidad visual sobre la imagen.
    - brightness : luminosidad media (0-255)
    - contrast   : desviación estándar de la luminosidad
    - blur_score : varianza del operador Laplaciano (nitidez)
    \"\"\"
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


print('Analizando calidad visual de los documentos...')
print('(Procesando primera página de cada documento — tarda ~2-3 minutos para 1,014 docs)')

vq_records = []
for _, row in tqdm(df_corpus.iterrows(), total=len(df_corpus), desc='Calidad visual'):
    rec = {'filepath': row['filepath'], 'category': row['category'],
           'brightness': None, 'contrast': None, 'blur_score': None,
           'width_px': None, 'height_px': None, 'quality_label': 'ERROR', 'vq_error': None}
    try:
        img = load_image_first_page(row['filepath'])
        if img is not None:
            rec.update(analyze_visual_quality(img))
        else:
            rec['vq_error'] = 'imagen_nula'
    except Exception as e:
        rec['vq_error'] = str(e)[:80]
    vq_records.append(rec)

df_vq = pd.DataFrame(vq_records)
df_corpus = df_corpus.merge(df_vq[['filepath','brightness','contrast','blur_score',
                                    'width_px','height_px','quality_label','vq_error']],
                             on='filepath', how='left')

print('\\n✅ Análisis de calidad visual completado.')
print()
print('── Clasificación de calidad ──')
print(df_corpus['quality_label'].value_counts().to_string())
print()
print('── Métricas visuales por tipología ──')
print(df_corpus.groupby('category')[['brightness','contrast','blur_score']]
      .agg(['mean','std']).round(1).to_string())
"""))

cells.append(code("""# ── Gráficas de calidad visual ───────────────────────────────────────────────
ql_colors = {'APTO': '#2ecc71', 'REQUIERE_PREPROCESAMIENTO': '#f39c12',
             'DESCARTADO': '#e74c3c', 'ERROR': '#95a5a6'}

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Calidad Visual del Corpus SECOP', fontsize=14, fontweight='bold')

# Calidad por tipología (barras apiladas %)
ql_by_cat = df_corpus.groupby(['category', 'quality_label']).size().unstack(fill_value=0)
ql_by_cat_pct = ql_by_cat.div(ql_by_cat.sum(axis=1), axis=0) * 100
ql_by_cat_pct.plot(kind='bar', stacked=True, ax=axes[0],
                    color=[ql_colors.get(c, '#ccc') for c in ql_by_cat_pct.columns],
                    edgecolor='white', linewidth=0.5)
axes[0].set_ylabel('% de documentos')
axes[0].set_title('Calidad por tipología')
axes[0].tick_params(axis='x', rotation=20)
axes[0].legend(fontsize=8, loc='lower right')

# Scatter brillo vs blur
df_viz = df_corpus.dropna(subset=['brightness','blur_score'])
for cat, color in PALETTE.items():
    sub = df_viz[df_viz['category'] == cat]
    axes[1].scatter(sub['brightness'], sub['blur_score'], c=color,
                    alpha=0.4, s=20, label=cat, edgecolors='none')
axes[1].axhline(BLUR_THRESHOLD, color='red', linestyle='--', lw=1.2,
                label=f'Umbral blur ({BLUR_THRESHOLD})')
axes[1].set_yscale('log')
axes[1].set_xlabel('Brillo (luminosidad media)')
axes[1].set_ylabel('Blur Score (escala log) — más alto = más nítido')
axes[1].set_title('Brillo vs. Nitidez por tipología')
axes[1].legend(fontsize=7)

# Box plot contraste
df_corpus.dropna(subset=['contrast']).boxplot(column='contrast', by='category',
    ax=axes[2], patch_artist=True,
    boxprops=dict(facecolor='#AED6F1'),
    medianprops=dict(color='red', linewidth=2))
axes[2].set_xlabel('')
axes[2].set_ylabel('Contraste (desviación estándar de luminosidad)')
axes[2].set_title('Contraste por tipología')
axes[2].tick_params(axis='x', rotation=20)
plt.suptitle('')

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig03_calidad_visual.png', bbox_inches='tight', dpi=150)
plt.show()
print('📊 Gráfica guardada: data/processed/fig03_calidad_visual.png')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3: EXTRACCIÓN DE TEXTO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 3 — Extracción del Texto de los Documentos

Para analizar el contenido textual, primero debemos extraer el texto de cada PDF. Como nuestros documentos son PDFs digitales nativos (no escaneados), podemos extraer el texto directamente — es mucho más rápido y preciso que usar OCR.

Esto es como la diferencia entre copiar texto de un Word (instantáneo) vs. fotografiarlo y luego intentar reconocer las letras (lento y con errores).

> ⏱️ **Tiempo estimado:** ~3-5 minutos para los 1,014 documentos.
"""))

cells.append(code("""def extract_text_pymupdf(filepath: str, max_pages: int = 3) -> Tuple[str, int]:
    \"\"\"
    Extrae el texto embebido de un PDF usando PyMuPDF.
    - max_pages: analiza las primeras N páginas para agilizar el proceso
    - Retorna: (texto_extraido, numero_total_de_paginas)
    \"\"\"
    try:
        doc = fitz.open(str(filepath))
        n_pages = doc.page_count
        text_parts = []
        for i in range(min(max_pages, n_pages)):
            text_parts.append(doc[i].get_text('text'))
        doc.close()
        return ' '.join(text_parts), n_pages
    except Exception as e:
        return '', 0


print('Extrayendo texto de los documentos...')
texts, n_pages_list, text_errors = [], [], []

for _, row in tqdm(df_corpus.iterrows(), total=len(df_corpus), desc='Extrayendo texto'):
    if row['extension'] == '.pdf':
        txt, npg = extract_text_pymupdf(row['filepath'])
    else:
        txt, npg = '', 1
    texts.append(txt.strip())
    n_pages_list.append(npg)
    text_errors.append(None if txt else 'sin_texto')

df_corpus['raw_text']  = texts
df_corpus['n_pages']   = n_pages_list
df_corpus['text_error'] = text_errors

# Documentos con y sin texto extraíble
con_texto   = (df_corpus['raw_text'].str.len() > 50).sum()
sin_texto   = (df_corpus['raw_text'].str.len() <= 50).sum()

print(f'\\n✅ Extracción completada.')
print(f'   Con texto extraíble  : {con_texto:,} documentos ({con_texto/len(df_corpus)*100:.1f}%)')
print(f'   Sin texto / muy poco : {sin_texto:,} documentos — posiblemente escaneados')
print()
print('── Páginas por tipología ──')
print(df_corpus.groupby('category')['n_pages']
      .agg(['mean','median','max']).round(1).rename(
      columns={'mean':'Promedio','median':'Mediana','max':'Máximo'}).to_string())
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4: CONTEOS BÁSICOS (TEXTSTAT)
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 4 — Conteos Básicos del Texto

Ahora calculamos las métricas más fundamentales de cada documento: cuántas palabras tiene, cuántas oraciones, sílabas, etc. Estas métricas son la base para decisiones técnicas importantes:

| Métrica | ¿Para qué sirve en el proyecto? |
|---|---|
| **Palabras (lexicon_count)** | Determina si el documento cabe completo en la IA o necesita dividirse |
| **Oraciones (sentence_count)** | Define el tamaño de la ventana de contexto para NER |
| **Sílabas (syllable_count)** | Indica la complejidad morfológica del vocabulario legal |
| **Palabras cortas (miniword_count)** | Artículos, preposiciones — ruido para la extracción de entidades |
| **Palabras largas (long_word_count)** | Terminología técnica — lo que más importa para NER |
| **Palabras difíciles (difficult_words)** | Jerga legal/contable — indica cuánto especializó el texto |
| **Tiempo de lectura (reading_time)** | Proxy de densidad informacional del documento |
"""))

cells.append(code("""def compute_basic_counts(text: str) -> Dict:
    \"\"\"
    Calcula todos los conteos básicos disponibles en textstat.
    Si el texto está vacío, retorna ceros para no romper el análisis.
    \"\"\"
    if not text or len(text.strip()) < 20:
        return {k: 0 for k in ['char_count','letter_count','syllable_count',
                                 'lexicon_count','sentence_count','polysyllabcount',
                                 'monosyllabcount','miniword_count','long_word_count',
                                 'difficult_words','reading_time_s',
                                 'avg_sentence_length','avg_syllables_per_word',
                                 'avg_character_per_word']}
    return {
        'char_count':           textstat.char_count(text),
        'letter_count':         textstat.letter_count(text),
        'syllable_count':       textstat.syllable_count(text),
        'lexicon_count':        textstat.lexicon_count(text),
        'sentence_count':       textstat.sentence_count(text),
        'polysyllabcount':      textstat.polysyllabcount(text),
        'monosyllabcount':      textstat.monosyllabcount(text),
        'miniword_count':       textstat.miniword_count(text),
        'long_word_count':      textstat.long_word_count(text),
        'difficult_words':      textstat.difficult_words(text),
        'reading_time_s':       round(textstat.reading_time(text, ms_per_char=14.69), 1),
        'avg_sentence_length':  round(textstat.avg_sentence_length(text), 2),
        'avg_syllables_per_word': round(textstat.avg_syllables_per_word(text), 3),
        'avg_character_per_word': round(textstat.avg_character_per_word(text), 2),
    }


print('Calculando conteos básicos con textstat...')
basic_rows = []
for _, row in tqdm(df_corpus.iterrows(), total=len(df_corpus), desc='Conteos básicos'):
    counts = compute_basic_counts(row['raw_text'])
    counts['filepath'] = row['filepath']
    basic_rows.append(counts)

df_basic = pd.DataFrame(basic_rows)
df_corpus = df_corpus.merge(df_basic, on='filepath', how='left')

print('\\n✅ Conteos básicos completados.')
print()
print('── Estadísticas de PALABRAS por tipología ──')
print(df_corpus.groupby('category')['lexicon_count']
      .agg(['mean','median','std','min','max']).round(0).astype(int).to_string())
print()
print('── Estadísticas de ORACIONES por tipología ──')
print(df_corpus.groupby('category')['sentence_count']
      .agg(['mean','median','std']).round(1).to_string())
print()
print('── Tiempo de lectura promedio por tipología (segundos) ──')
print(df_corpus.groupby('category')['reading_time_s']
      .agg(['mean','median']).round(1).to_string())
"""))

cells.append(code("""# ── Visualizaciones de conteos básicos ───────────────────────────────────────
df_plot = df_corpus[df_corpus['lexicon_count'] > 0].copy()

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Textometría Básica por Tipología de Documento', fontsize=14, fontweight='bold')

metrics_basic = [
    ('lexicon_count',           'Palabras totales',              'Número de palabras'),
    ('sentence_count',          'Oraciones totales',             'Número de oraciones'),
    ('difficult_words',         'Palabras difíciles / técnicas', 'Cantidad'),
    ('avg_sentence_length',     'Longitud promedio de oración',  'Palabras por oración'),
    ('avg_syllables_per_word',  'Sílabas promedio por palabra',  'Sílabas'),
    ('reading_time_s',          'Tiempo de lectura (segundos)',  'Segundos'),
]

for ax, (col, title, ylabel) in zip(axes.flat, metrics_basic):
    cat_order = df_plot.groupby('category')[col].median().sort_values().index.tolist()
    sns.boxplot(data=df_plot, x='category', y=col, order=cat_order,
                palette=PALETTE, ax=ax, linewidth=0.8)
    ax.set_title(title, fontsize=10, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_xlabel('')
    ax.tick_params(axis='x', rotation=20, labelsize=8)

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig04_conteos_basicos.png', bbox_inches='tight', dpi=150)
plt.show()
print('📊 Gráfica guardada: data/processed/fig04_conteos_basicos.png')
print()

# Tabla resumen completa
print('── TABLA RESUMEN: CONTEOS BÁSICOS (mediana por tipología) ──')
summary_cols = ['lexicon_count','sentence_count','difficult_words',
                'avg_sentence_length','avg_syllables_per_word','reading_time_s']
summary = df_plot.groupby('category')[summary_cols].median().round(1)
summary.columns = ['Palabras','Oraciones','Pal.Difíciles','Long.Oración','Síl/Palabra','Lectura(s)']
display(summary)
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5: LEGIBILIDAD
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 5 — Índices de Legibilidad

Los índices de legibilidad miden qué tan fácil o difícil es leer y entender un texto. Son especialmente útiles para nuestro proyecto porque **un documento más complejo necesita más ejemplos de entrenamiento** para que la IA aprenda a extraer información correctamente.

### ¿Cómo interpretar los puntajes?

**Flesch Reading Ease** (adaptado al español):

| Puntaje | Nivel de dificultad | Ejemplo |
|---|---|---|
| 90 – 100 | Muy fácil | Cuentos infantiles |
| 70 – 90  | Fácil | Novela popular |
| 50 – 70  | Normal | Artículo de periódico |
| 30 – 50  | Difícil | Texto universitario |
| 0 – 30   | Muy difícil | Textos legales / técnicos |

**Gunning Fog Index:** número de años de educación necesarios para entender el texto.
- Puntaje 12 → requiere bachillerato completo
- Puntaje 17 → requiere posgrado

**Smog Index:** similar al Gunning Fog, pero más preciso para textos cortos.

**Coleman-Liau / ARI:** estimaciones del nivel escolar basadas en caracteres y oraciones.
"""))

cells.append(code("""def compute_readability(text: str) -> Dict:
    \"\"\"
    Calcula todos los índices de legibilidad disponibles en textstat.
    Incluye tanto las métricas generales como las específicas para español.
    \"\"\"
    if not text or len(text.strip()) < 100:
        return {k: None for k in [
            'flesch_reading_ease','flesch_kincaid_grade','smog_index',
            'coleman_liau_index','automated_readability_index',
            'dale_chall_readability_score','linsear_write_formula',
            'gunning_fog','text_standard',
            'fernandez_huerta','szigriszt_pazos','gutierrez_polini','crawford',
            'lix','rix','mcalpine_eflaw','wiener_sachtextformel']}
    return {
        # ── Métricas generales ────────────────────────────────────────────────
        'flesch_reading_ease':           round(textstat.flesch_reading_ease(text), 2),
        'flesch_kincaid_grade':          round(textstat.flesch_kincaid_grade(text), 2),
        'smog_index':                    round(textstat.smog_index(text), 2),
        'coleman_liau_index':            round(textstat.coleman_liau_index(text), 2),
        'automated_readability_index':   round(textstat.automated_readability_index(text), 2),
        'dale_chall_readability_score':  round(textstat.dale_chall_readability_score(text), 2),
        'linsear_write_formula':         round(textstat.linsear_write_formula(text), 2),
        'gunning_fog':                   round(textstat.gunning_fog(text), 2),
        'text_standard':                 textstat.text_standard(text, float_output=False),
        # ── Métricas específicas para español ────────────────────────────────
        'fernandez_huerta':              round(textstat.fernandez_huerta(text), 2),
        'szigriszt_pazos':               round(textstat.szigriszt_pazos(text), 2),
        'gutierrez_polini':              round(textstat.gutierrez_polini(text), 2),
        'crawford':                      round(textstat.crawford(text), 2),
        # ── Métricas adicionales ─────────────────────────────────────────────
        'lix':                           round(textstat.lix(text), 2),
        'rix':                           round(textstat.rix(text), 2),
        'mcalpine_eflaw':                round(textstat.mcalpine_eflaw(text), 2),
        'wiener_sachtextformel':         round(textstat.wiener_sachtextformel(text, variant=1), 2),
    }


print('Calculando índices de legibilidad...')
read_rows = []
for _, row in tqdm(df_corpus.iterrows(), total=len(df_corpus), desc='Legibilidad'):
    r = compute_readability(row['raw_text'])
    r['filepath'] = row['filepath']
    read_rows.append(r)

df_read = pd.DataFrame(read_rows)
df_corpus = df_corpus.merge(df_read, on='filepath', how='left')

print('\\n✅ Índices de legibilidad calculados.')
print()
print('── FLESCH READING EASE por tipología (más alto = más fácil de leer) ──')
print(df_corpus.groupby('category')['flesch_reading_ease']
      .agg(['mean','median','std']).round(2).to_string())
print()
print('── GUNNING FOG (años de educación requeridos) ──')
print(df_corpus.groupby('category')['gunning_fog']
      .agg(['mean','median']).round(2).to_string())
print()
print('── NIVEL ESTÁNDAR DE TEXTO más frecuente por tipología ──')
print(df_corpus.groupby('category')['text_standard']
      .agg(lambda x: x.mode()[0] if not x.mode().empty else 'N/A').to_string())
"""))

cells.append(code("""# ── Visualizaciones de legibilidad ───────────────────────────────────────────
df_read_plot = df_corpus.dropna(subset=['flesch_reading_ease']).copy()

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Índices de Legibilidad por Tipología', fontsize=14, fontweight='bold')

read_metrics = [
    ('flesch_reading_ease',         'Flesch Reading Ease\\n(más alto = más fácil)'),
    ('gunning_fog',                 'Gunning Fog Index\\n(años de educación requeridos)'),
    ('smog_index',                  'SMOG Index\\n(grado escolar)'),
    ('coleman_liau_index',          'Coleman-Liau Index\\n(grado escolar)'),
    ('automated_readability_index', 'ARI\\n(índice de legibilidad automatizado)'),
    ('dale_chall_readability_score','Dale-Chall Score\\n(dificultad de vocabulario)'),
]

for ax, (col, title) in zip(axes.flat, read_metrics):
    cat_order = df_read_plot.groupby('category')[col].median().sort_values().index.tolist()
    sns.violinplot(data=df_read_plot, x='category', y=col, order=cat_order,
                   palette=PALETTE, inner='box', ax=ax, linewidth=0.8)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_xlabel('')
    ax.tick_params(axis='x', rotation=20, labelsize=8)

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig05_legibilidad.png', bbox_inches='tight', dpi=150)
plt.show()
print('📊 Gráfica guardada: data/processed/fig05_legibilidad.png')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6: LEGIBILIDAD EN ESPAÑOL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 6 — Métricas de Legibilidad en Español

Las métricas anteriores fueron diseñadas principalmente para el inglés. Aquí usamos fórmulas específicamente adaptadas para textos en **español**, que tienen en cuenta las diferencias morfológicas del idioma (más sílabas por palabra, estructuras gramaticales distintas).

### Métricas en español:

- **Fernández-Huerta:** Adaptación española del Flesch. Rango 0-100, más alto = más fácil.
- **Szigriszt-Pazos (Índice INFLESZ):** Muy usado en textos médicos y legales en España y Latinoamérica.
  - `< 40` → Muy difícil (textos científicos)
  - `40–55` → Algo difícil (textos universitarios)
  - `55–65` → Normal (prensa general)
  - `65–80` → Bastante fácil
  - `> 80` → Muy fácil
- **Gutiérrez de Polini:** Fórmula colombiana y latinoamericana. Rango 0-100.
- **Crawford:** Estima los años de escolaridad necesarios para comprender el texto.

> 🇨🇴 **Relevancia para SinergIA Lab:** Estas métricas son las más pertinentes porque nuestros documentos son colombianos. El resultado nos dice cuánto dominio del español legal-administrativo necesita la IA.
"""))

cells.append(code("""# ── Métricas de legibilidad en español ───────────────────────────────────────
esp_metrics = ['fernandez_huerta', 'szigriszt_pazos', 'gutierrez_polini', 'crawford']
df_esp = df_corpus.dropna(subset=['fernandez_huerta']).copy()

fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('Métricas de Legibilidad en Español por Tipología', fontsize=14, fontweight='bold')

descriptions = {
    'fernandez_huerta':  'Fernández-Huerta\\n(0-100, más alto = más fácil)',
    'szigriszt_pazos':   'Szigriszt-Pazos / INFLESZ\\n(0-100, más alto = más fácil)',
    'gutierrez_polini':  'Gutiérrez de Polini\\n(0-100, latinoamericano)',
    'crawford':          'Crawford\\n(años de escolaridad necesarios)',
}

for ax, col in zip(axes.flat, esp_metrics):
    cat_order = df_esp.groupby('category')[col].median().sort_values().index.tolist()
    sns.boxplot(data=df_esp, x='category', y=col, order=cat_order,
                palette=PALETTE, ax=ax, linewidth=0.8)
    ax.set_title(descriptions[col], fontsize=10, fontweight='bold')
    ax.set_xlabel('')
    ax.tick_params(axis='x', rotation=20, labelsize=9)

    # Líneas de referencia
    if col in ['fernandez_huerta', 'szigriszt_pazos', 'gutierrez_polini']:
        ax.axhline(40, color='red',    linestyle=':', lw=1, alpha=0.7, label='Muy difícil (<40)')
        ax.axhline(55, color='orange', linestyle=':', lw=1, alpha=0.7, label='Difícil (40-55)')
        ax.axhline(65, color='green',  linestyle=':', lw=1, alpha=0.7, label='Normal (55-65)')
        ax.legend(fontsize=7)

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig06_legibilidad_espanol.png', bbox_inches='tight', dpi=150)
plt.show()
print('📊 Gráfica guardada: data/processed/fig06_legibilidad_espanol.png')
print()
print('── TABLA COMPLETA: Métricas en español (mediana por tipología) ──')
tabla_esp = df_esp.groupby('category')[esp_metrics].median().round(2)
tabla_esp.columns = ['Fernández-Huerta','Szigriszt-Pazos','Gutiérrez-Polini','Crawford']
display(tabla_esp)
print()
print('Interpretación Szigriszt-Pazos (INFLESZ):')
for cat in tabla_esp.index:
    score = tabla_esp.loc[cat, 'Szigriszt-Pazos']
    if score < 40:   nivel = '🔴 Muy difícil — texto científico/legal complejo'
    elif score < 55: nivel = '🟠 Algo difícil — texto universitario'
    elif score < 65: nivel = '🟡 Normal — prensa general'
    elif score < 80: nivel = '🟢 Bastante fácil'
    else:            nivel = '🟢 Muy fácil'
    print(f'  {cat:<22}: {score:.1f} → {nivel}')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 7: PATRONES DE ENTIDADES
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 7 — Patrones de Entidades Objetivo

Esta sección busca en el texto de cada documento los tipos de información que queremos que la IA aprenda a extraer. Es como buscar patrones conocidos: ¿cuántas veces aparece un número de cédula? ¿Un NIT? ¿Una fecha? ¿Un valor monetario?

Esto nos dice **qué tan frecuente es cada entidad** en cada tipo de documento, lo cual guía directamente cuántos ejemplos de entrenamiento necesitamos por entidad.

| Patrón buscado | Ejemplo real |
|---|---|
| Número de cédula | `1.032.456.789` |
| NIT | `900.123.456-7` |
| Fecha | `15/03/2025`, `2025-03-15` |
| Valor monetario | `$1.500.000`, `COP 2.300.000` |
| Email | `contacto@empresa.com.co` |
| Código CIIU | `CIIU 6201` |
"""))

cells.append(code("""# ── Patrones regex para entidades colombianas ────────────────────────────────
ENTITY_PATTERNS = {
    'cedula':     r'\\b\\d{1,3}[\\.,]\\d{3}[\\.,]\\d{3}\\b|\\b\\d{6,10}\\b',
    'nit':        r'\\b\\d{6,10}[-–]\\d\\b',
    'fecha':      r'\\b\\d{1,2}[/\\-]\\d{1,2}[/\\-]\\d{2,4}\\b|\\b\\d{4}[-]\\d{2}[-]\\d{2}\\b',
    'monto':      r'\\$\\s?[\\d\\.,]+|\\bCOP\\s?[\\d\\.,]+',
    'email':      r'[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}',
    'ciiu':       r'(?i)CIIU\\s*[:\\s]*\\d{4}',
    'matricula':  r'(?i)matr[íi]cula\\s*(?:mercantil)?\\s*[:\\s]*[\\d\\-]+',
    'poliza_num': r'(?i)p[oó]liza\\s*(?:n[oú]mero|no\\.?|#)\\s*[:\\s]*[\\w\\-]+',
}

def count_entities(text: str) -> Dict:
    if not text or len(text.strip()) < 20:
        return {f'ent_{k}': 0 for k in ENTITY_PATTERNS}
    return {f'ent_{k}': len(re.findall(v, text))
            for k, v in ENTITY_PATTERNS.items()}


print('Detectando patrones de entidades...')
ent_rows = []
for _, row in tqdm(df_corpus.iterrows(), total=len(df_corpus), desc='Entidades'):
    e = count_entities(row['raw_text'])
    e['filepath'] = row['filepath']
    ent_rows.append(e)

df_ent = pd.DataFrame(ent_rows)
df_corpus = df_corpus.merge(df_ent, on='filepath', how='left')

ent_cols = [f'ent_{k}' for k in ENTITY_PATTERNS]
print('\\n✅ Detección de entidades completada.')
print()
print('── FRECUENCIA PROMEDIO de entidades por tipología ──')
ent_means = df_corpus.groupby('category')[ent_cols].mean().round(2)
ent_means.columns = list(ENTITY_PATTERNS.keys())
display(ent_means)
"""))

cells.append(code("""# ── Heatmap y gráficas de entidades ──────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(18, 6))
fig.suptitle('Presencia de Entidades Objetivo por Tipología', fontsize=14, fontweight='bold')

# Heatmap
ent_display = ent_means.copy()
ent_display.index = [c[:18] for c in ent_display.index]
sns.heatmap(ent_display, annot=True, fmt='.1f', cmap='YlOrRd', ax=axes[0],
            linewidths=0.5, cbar_kws={'label': 'Promedio por documento'})
axes[0].set_title('Frecuencia promedio de entidades (calor = más frecuente)')
axes[0].tick_params(axis='x', rotation=30)

# Barras agrupadas — top entidades
ent_totals = df_corpus.groupby('category')[ent_cols].sum()
ent_totals.columns = list(ENTITY_PATTERNS.keys())
ent_totals.T.plot(kind='bar', ax=axes[1], color=list(PALETTE.values())[:5],
                   edgecolor='white', linewidth=0.5)
axes[1].set_title('Total de entidades detectadas en el corpus')
axes[1].set_ylabel('Número total de coincidencias')
axes[1].tick_params(axis='x', rotation=30)
axes[1].legend(fontsize=8)

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig07_entidades.png', bbox_inches='tight', dpi=150)
plt.show()
print('📊 Gráfica guardada: data/processed/fig07_entidades.png')
print()
print('── DOCUMENTOS con al menos 1 entidad detectada ──')
for col in ent_cols:
    nombre = col.replace('ent_','')
    n = (df_corpus[col] > 0).sum()
    pct = n / len(df_corpus) * 100
    print(f'  {nombre:<15}: {n:>5} docs ({pct:.1f}%)')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 8: ESTADÍSTICA INFERENCIAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 8 — ¿Las diferencias son estadísticamente significativas?

Hasta ahora vimos que los distintos tipos de documentos parecen tener características diferentes (unas pólizas son más largas, los RUT tienen menos palabras difíciles, etc.). Pero, **¿esas diferencias son reales o podrían ser por azar?**

Para responder esto usamos el **Test ANOVA de una vía** (Análisis de Varianza). Este test compara los grupos y nos dice con qué certeza podemos afirmar que son realmente distintos.

**¿Cómo interpretar el resultado?**
- **p-value < 0.05** → ✅ Las diferencias son reales (estadísticamente significativas)
- **p-value ≥ 0.05** → ⚠️ No podemos concluir que sean distintos con suficiente certeza

**¿Por qué importa?** Si las diferencias son estadísticamente significativas, estamos justificados en diseñar **estrategias de entrenamiento distintas** para cada tipología, como lo establecimos en el plan v1.1.
"""))

cells.append(code("""# ── ANOVA entre tipologías ────────────────────────────────────────────────────
from scipy import stats

anova_metrics = [
    ('lexicon_count',          'Número de palabras'),
    ('difficult_words',        'Palabras difíciles'),
    ('flesch_reading_ease',    'Flesch Reading Ease'),
    ('gunning_fog',            'Gunning Fog Index'),
    ('fernandez_huerta',       'Fernández-Huerta (español)'),
    ('szigriszt_pazos',        'Szigriszt-Pazos (español)'),
    ('avg_sentence_length',    'Longitud promedio de oración'),
    ('blur_score',             'Nitidez visual (Blur Score)'),
]

results_anova = []
cats = [c for c in df_corpus['category'].unique() if c != 'Otros']

print('══ RESULTADOS ANOVA (¿son las diferencias entre tipologías estadísticamente significativas?) ══')
print()

for col, label in anova_metrics:
    groups = [df_corpus[df_corpus['category'] == c][col].dropna().values for c in cats]
    groups = [g for g in groups if len(g) >= 5]
    if len(groups) < 2:
        continue
    try:
        f_stat, p_val = stats.f_oneway(*groups)
        significant = p_val < 0.05
        results_anova.append({
            'Métrica': label, 'F-estadístico': round(f_stat, 2),
            'p-valor': round(p_val, 5),
            'Significativo': '✅ SÍ (p<0.05)' if significant else '⚠️  NO (p≥0.05)'
        })
        simbolo = '✅' if significant else '⚠️ '
        print(f'  {simbolo} {label:<38} F={f_stat:>8.2f}  p={p_val:.5f}')
    except Exception as e:
        print(f'  ❌ {label}: error — {e}')

print()
df_anova = pd.DataFrame(results_anova)
display(df_anova)
"""))

cells.append(code("""# ── Visualización ANOVA: comparación de medias por tipología ─────────────────
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle('Comparación Estadística entre Tipologías (ANOVA)', fontsize=14, fontweight='bold')

top_metrics = [
    ('lexicon_count',       'Palabras por documento'),
    ('difficult_words',     'Palabras difíciles'),
    ('fernandez_huerta',    'Legibilidad Fernández-Huerta'),
    ('gunning_fog',         'Gunning Fog (complejidad)'),
    ('avg_sentence_length', 'Longitud promedio de oración'),
    ('szigriszt_pazos',     'INFLESZ (legibilidad en español)'),
]

df_anova_plot = df_corpus[df_corpus['category'] != 'Otros'].copy()

for ax, (col, title) in zip(axes.flat, top_metrics):
    cat_order = df_anova_plot.groupby('category')[col].median().sort_values().index.tolist()
    # Mostrar medias con barras de error (intervalo de confianza 95%)
    means = df_anova_plot.groupby('category')[col].mean().reindex(cat_order)
    sems  = df_anova_plot.groupby('category')[col].sem().reindex(cat_order)
    colors_plot = [PALETTE.get(c, '#888') for c in cat_order]
    bars = ax.bar(range(len(cat_order)), means.values, color=colors_plot,
                   yerr=sems.values * 1.96, capsize=4, edgecolor='white',
                   error_kw={'elinewidth': 1.2, 'ecolor': 'grey'})
    ax.set_xticks(range(len(cat_order)))
    ax.set_xticklabels([c[:14] for c in cat_order], rotation=20, ha='right', fontsize=8)
    ax.set_title(title, fontsize=9, fontweight='bold')
    ax.set_ylabel('Media (± IC 95%)')

plt.tight_layout()
plt.savefig(DATA_PROC / 'fig08_anova.png', bbox_inches='tight', dpi=150)
plt.show()
print('📊 Gráfica guardada: data/processed/fig08_anova.png')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 9: EXPORTACIÓN
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Sección 9 — Exportación del Reporte Completo

Consolidamos todos los análisis en un archivo CSV completo que será usado por las siguientes fases del proyecto. Este reporte es el **entregable formal de la Fase 1 del CRISP-DM++**.

> 🔒 **Privacidad:** El texto crudo extraído de los documentos NO se guarda en el CSV (contiene información personal — PII). Solo se guardan las métricas estadísticas derivadas de ese texto.
"""))

cells.append(code("""# ── Exportar reporte completo ─────────────────────────────────────────────────
# Columnas a exportar (SIN raw_text — contiene PII)
EXPORT_COLS = [
    'filepath','filename','category','extension','size_kb','md5','is_duplicate',
    'n_pages',
    # Calidad visual
    'brightness','contrast','blur_score','width_px','height_px','quality_label',
    # Conteos básicos
    'char_count','letter_count','syllable_count','lexicon_count','sentence_count',
    'polysyllabcount','monosyllabcount','miniword_count','long_word_count',
    'difficult_words','reading_time_s','avg_sentence_length',
    'avg_syllables_per_word','avg_character_per_word',
    # Legibilidad
    'flesch_reading_ease','flesch_kincaid_grade','smog_index','coleman_liau_index',
    'automated_readability_index','dale_chall_readability_score',
    'linsear_write_formula','gunning_fog','text_standard',
    # Legibilidad en español
    'fernandez_huerta','szigriszt_pazos','gutierrez_polini','crawford',
    'lix','rix','mcalpine_eflaw','wiener_sachtextformel',
    # Entidades
    'ent_cedula','ent_nit','ent_fecha','ent_monto','ent_email',
    'ent_ciiu','ent_matricula','ent_poliza_num',
]

df_export = df_corpus[[c for c in EXPORT_COLS if c in df_corpus.columns]].copy()

report_path = DATA_PROC / 'quality_report_completo.csv'
df_export.to_csv(report_path, index=False, encoding='utf-8-sig')

print(f'✅ Reporte exportado: {report_path}')
print(f'   Filas     : {len(df_export):,}')
print(f'   Columnas  : {len(df_export.columns)}')
print()
display(df_export.head(5))
print()

# Estadísticas descriptivas completas
print('── ESTADÍSTICAS DESCRIPTIVAS GLOBALES ──')
numeric_cols = df_export.select_dtypes(include=[np.number]).columns
display(df_export[numeric_cols].describe().round(2))
"""))

cells.append(code("""# ── Decisiones técnicas automatizadas ────────────────────────────────────────
decisions = {'ocr_engine': 'easyocr_fallback_pymupdf', 'python_version': '3.12'}

# Calidad visual
ql = df_corpus['quality_label'].value_counts().to_dict()
total = len(df_corpus)
decisions['calidad_visual'] = {
    'distribucion': ql,
    'pct_aptos':            round(ql.get('APTO', 0) / total * 100, 1),
    'pct_preprocesamiento': round(ql.get('REQUIERE_PREPROCESAMIENTO', 0) / total * 100, 1),
    'pct_descartados':      round(ql.get('DESCARTADO', 0) / total * 100, 1),
}

# Chunking por tipología
decisions['chunking'] = {}
for cat in df_corpus['category'].unique():
    med = df_corpus[df_corpus['category'] == cat]['lexicon_count'].median()
    token_est = int(med / 0.75) if not pd.isna(med) else 0
    if token_est > 2048:  strat = 'layout_aware_opencv'
    elif token_est > 512: strat = 'sliding_window_30pct'
    else:                 strat = 'sin_chunking'
    decisions['chunking'][cat] = {'mediana_palabras': int(med) if not pd.isna(med) else 0,
                                   'tokens_estimados': token_est, 'estrategia': strat}

# Complejidad por tipología
decisions['complejidad_lectura'] = {}
for cat in df_corpus['category'].unique():
    sub = df_corpus[df_corpus['category'] == cat]
    decisions['complejidad_lectura'][cat] = {
        'flesch_mediana':      round(float(sub['flesch_reading_ease'].median()), 2) if 'flesch_reading_ease' in sub else None,
        'szigriszt_mediana':   round(float(sub['szigriszt_pazos'].median()), 2) if 'szigriszt_pazos' in sub else None,
        'difficult_words_avg': round(float(sub['difficult_words'].mean()), 1) if 'difficult_words' in sub else None,
    }

dec_path = DATA_PROC / 'fase1_decisiones.json'
with open(dec_path, 'w', encoding='utf-8') as f:
    json.dump(decisions, f, ensure_ascii=False, indent=2)

print('✅ Decisiones técnicas guardadas:', dec_path)
print()
print('══ RESUMEN EJECUTIVO — FASE 1 COMPLETADA ══')
print()
print('CALIDAD VISUAL:')
cv = decisions['calidad_visual']
print(f'  Aptos                    : {cv["pct_aptos"]}%')
print(f'  Requieren preprocesamiento: {cv["pct_preprocesamiento"]}%')
print(f'  Descartados              : {cv["pct_descartados"]}%')
print()
print('ESTRATEGIA DE CHUNKING (v1.1):')
for cat, info in decisions['chunking'].items():
    print(f'  {cat:<22} → {info["estrategia"]:<25} ({info["tokens_estimados"]:,} tokens est.)')
print()
print('COMPLEJIDAD TEXTUAL (Szigriszt-Pazos mediana):')
for cat, info in decisions['complejidad_lectura'].items():
    score = info.get('szigriszt_mediana')
    if score is None: continue
    if score < 40:   nivel = 'Muy difícil'
    elif score < 55: nivel = 'Algo difícil'
    elif score < 65: nivel = 'Normal'
    else:            nivel = 'Fácil'
    print(f'  {cat:<22} → {score:.1f} ({nivel})')
print()
print('► Siguiente paso: notebooks/02_preprocesamiento_pipeline.ipynb')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# CONCLUSIONES
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Conclusiones

Al terminar de ejecutar este notebook habrás respondido las preguntas fundamentales de la Fase 1 del CRISP-DM++ para SinergIA Lab:

1. **¿Cuántos documentos tenemos?** → Inventario completo con detección de duplicados
2. **¿Están en buen estado?** → Clasificación visual APTO / REQUIERE PREPROCESAMIENTO / DESCARTADO
3. **¿Qué tan largos son?** → Estrategia de chunking validada con datos reales
4. **¿Qué tan complejos son?** → Nivel de dificultad que la IA necesita aprender
5. **¿Qué entidades contienen?** → Mapa de frecuencia de entidades por tipología
6. **¿Las diferencias son reales?** → Confirmación estadística (ANOVA)

### Artefactos generados en `data/processed/`

| Archivo | Contenido |
|---|---|
| `quality_report_completo.csv` | Todas las métricas por documento (sin texto crudo) |
| `fase1_decisiones.json` | Decisiones técnicas para Fase 2 |
| `fig01_inventario.png` | Distribución del corpus |
| `fig02_tamanos.png` | Tamaños de archivo |
| `fig03_calidad_visual.png` | Calidad visual (brillo, contraste, nitidez) |
| `fig04_conteos_basicos.png` | Textometría básica |
| `fig05_legibilidad.png` | Índices de legibilidad generales |
| `fig06_legibilidad_espanol.png` | Métricas de legibilidad en español |
| `fig07_entidades.png` | Patrones de entidades detectadas |
| `fig08_anova.png` | Comparación estadística entre tipologías |

---
*SinergIA Lab | PUJ Especialización IA 2026 | CRISP-DM++ Fase 1 v1.2*
*Herramientas: PyMuPDF · OpenCV · textstat · scipy · pandas · seaborn*
"""))

# ══════════════════════════════════════════════════════════════════════════════
# GENERAR EL NOTEBOOK
# ══════════════════════════════════════════════════════════════════════════════
nb.cells = cells
out_path = Path(__file__).parent / '01_analisis_descriptivo_secop.ipynb'
nbf.write(nb, str(out_path))
print(f'Notebook generado: {out_path}')
print(f'Total de celdas  : {len(cells)}')
