"""
Genera el notebook 02_preprocesamiento_pipeline.ipynb
Ejecutar: python notebooks/build_notebook_02.py
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
cells.append(md("""# SinergIA Lab — Preparacion de Datos
## Fase 2 CRISP-DM++: Del Corpus Crudo al Dataset de Entrenamiento

---

### Que hace este notebook?

En el Notebook 01 conocimos el corpus: cuantos documentos tenemos, en que estado estan y como esta escrito el texto. Ahora, en la Fase 2, vamos a **preparar** ese corpus para que el modelo de inteligencia artificial pueda aprender de el.

Piensalo asi: en el Notebook 01 hicimos el diagnostico medico del corpus. En este notebook vamos a **aplicar el tratamiento**: limpiar documentos en mal estado, identificar duplicados, dividir documentos muy largos en fragmentos manejables, y dejar todo listo para la etapa de anotacion.

### Que vamos a hacer?

| Seccion | Que resuelve |
|---|---|
| 1. Pre-requisitos | Duplicados casi identicos y vocabulario juridico del corpus |
| 2. Deteccion de portadas | Identificar paginas sin datos en todos los tipos de documento |
| 3. Preprocesamiento visual | Limpiar y normalizar documentos escaneados o degradados |
| 4. Identificacion de aseguradoras | Distribuir la anotacion de Polizas proporcionalmente |
| 5. Pipeline de chunking | Dividir documentos largos respetando el contexto |
| 6. Resumen y proximos pasos | Que queda listo y que sigue (anotacion en Label Studio) |

### Hallazgos del Notebook 01 que guian este trabajo

| Hallazgo | Decision de diseno |
|---|---|
| 93% Cedulas son imagenes escaneadas | OCR muestral; no regex LFs |
| RUT: formato DIAN unico, 64% supera 1,800 tokens | Ventana deslizante obligatoria |
| Polizas: layout variable por aseguradora | Anotacion estratificada por aseguradora |
| CC: formato consistente, algunos con portada | Deteccion de portada antes de extraer texto |
| BPE x1.25: RUT 151, CC 96, Polizas 31 docs > 1,800 tok | Chunking es requisito duro |
"""))

# ══════════════════════════════════════════════════════════════════════════════
# CELDA 1: SETUP
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Configuracion inicial

Cargamos las librerias y definimos las rutas del proyecto.
"""))

cells.append(code("""import warnings, json, re
from pathlib import Path
from collections import Counter

import fitz                       # PyMuPDF
import cv2
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

warnings.filterwarnings('ignore')

PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_RAW     = PROJECT_ROOT / 'data' / 'raw'
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
DATA_PROC.mkdir(parents=True, exist_ok=True)

CATEGORIES = {
    'Cedula':             DATA_RAW / 'CEDULA',
    'RUT':                DATA_RAW / 'rut',
    'Poliza':             DATA_RAW / 'POLIZA',
    'Camara de Comercio': DATA_RAW / 'CAMARA DE CIO',
}

PALETTE = {'Cedula': '#4C72B0', 'RUT': '#DD8452',
           'Poliza': '#55A868', 'Camara de Comercio': '#C44E52'}

sns.set_theme(style='whitegrid', font_scale=1.1)
plt.rcParams.update({'figure.dpi': 120})
np.random.seed(42)

# Cargar reporte del EDA (utf-8 sin BOM — formato estandar del proyecto)
csv_path = DATA_PROC / 'quality_report_completo.csv'
df_eda = pd.read_csv(csv_path, encoding='utf-8')
# Defensa extra: limpiar cualquier prefijo no ASCII en nombres de columna
df_eda.columns = [''.join(c for c in col if c.isascii() and c.isprintable())
                  for col in df_eda.columns]
assert 'filepath' in df_eda.columns, f"Columna 'filepath' no encontrada. Columnas: {list(df_eda.columns[:5])}"

print(f'CSV cargado: {df_eda.shape[0]} documentos x {df_eda.shape[1]} columnas')
print(df_eda['category'].value_counts().to_string())
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 1: PRE-REQUISITOS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 1 — Pre-Requisitos: Duplicados y Vocabulario

### 1.1 Deteccion de Near-Duplicates

Los duplicados exactos ya los eliminamos en el EDA (columna `is_duplicate` con MD5).
Ahora buscamos documentos **casi identicos**: por ejemplo, dos certificados de Camara de Comercio
del mismo NIT renovados en diferentes anos — tienen el mismo texto pero con fechas distintas.

Si estos pares entran al set de entrenamiento, el modelo aprendera que esos documentos son
equivalentes y sobreestimara su confianza. Hay que detectarlos y elegir uno por par.

**Como funciona:** extraemos texto de cada documento digital con PyMuPDF, convertimos ese texto
a vectores TF-IDF (una representacion numerica del contenido), y calculamos la similitud coseno
entre pares. Similitud > 0.90 = documentos casi identicos.
"""))

cells.append(code("""# Tipologias donde la deteccion de portada es valida
# Cedulas: DESACTIVADA — 93% son escaneadas y el criterio genera falsos positivos
TIPOLOGIAS_CON_PORTADA = {'Poliza', 'Camara de Comercio'}

def extract_text_sample(category_path, categoria='', n=None):
    \"\"\"Extrae texto digital de PDFs en una carpeta. n=None extrae todos.\"\"\"
    records = []
    files = sorted(category_path.glob('*.pdf'))
    if n:
        files = files[:n]
    for fp in files:
        try:
            doc = fitz.open(str(fp))
            # Saltar portada SOLO para tipologias digitales (Poliza y CC)
            # Para Cedulas: NO aplicar — el criterio genera falsos positivos en imagenes escaneadas
            start_page = 0
            if categoria in TIPOLOGIAS_CON_PORTADA and doc.page_count > 1:
                p0_text = doc[0].get_text().strip()
                p0_blocks = [b for b in doc[0].get_text('blocks') if b[6] == 0]
                if len(p0_text) < 50 and len(p0_blocks) < 5:
                    start_page = 1
            text = ' '.join(doc[i].get_text() for i in range(start_page, doc.page_count))
            doc.close()
            records.append({'filepath': str(fp), 'filename': fp.name, 'text': text.strip()})
        except Exception as e:
            records.append({'filepath': str(fp), 'filename': fp.name, 'text': ''})
    return pd.DataFrame(records)

print('Extrayendo texto para analisis de duplicados...')
near_dup_results = {}

for cat, folder in CATEGORIES.items():
    if not folder.exists():
        print(f'  Carpeta no encontrada: {folder}')
        continue
    df_cat = extract_text_sample(folder, categoria=cat)
    df_cat = df_cat[df_cat['text'].str.len() > 100]  # solo docs con texto real

    if len(df_cat) < 2:
        print(f'  {cat}: muy pocos docs digitales para comparar')
        continue

    tfidf = TfidfVectorizer(max_features=500, ngram_range=(1,2), min_df=2)
    try:
        matriz = tfidf.fit_transform(df_cat['text'])
        sim = cosine_similarity(matriz)
        np.fill_diagonal(sim, 0)  # ignorar auto-similitud

        umbral = 0.90
        pares = []
        for i in range(len(df_cat)):
            for j in range(i+1, len(df_cat)):
                if sim[i, j] >= umbral:
                    pares.append({
                        'doc_a': df_cat.iloc[i]['filename'],
                        'doc_b': df_cat.iloc[j]['filename'],
                        'similitud': round(sim[i, j], 3)
                    })

        near_dup_results[cat] = pares
        print(f'  {cat}: {len(df_cat)} docs digitales | {len(pares)} pares similitud >= {umbral}')
    except Exception as e:
        print(f'  {cat}: error en TF-IDF — {e}')

# Guardar resultados
with open(DATA_PROC / 'near_duplicates.json', 'w', encoding='utf-8') as f:
    json.dump(near_dup_results, f, ensure_ascii=False, indent=2)
print('\\nResultados guardados en near_duplicates.json')
"""))

cells.append(md("""### 1.2 Vocabulario Especifico por Dominio

El tokenizador BPE de Llama 3 fue entrenado con texto general en ingles y espanol.
Palabras como *CIIU*, *RUNT*, *contraloria*, *escritura publica*, *poliza de cumplimiento*
se fragmentan en subpalabras raras, lo que reduce la precision del modelo.

Identificar estos terminos nos permite:
1. Confirmar el factor de correccion BPE x1.25 que usamos en el EDA
2. Preparar un glosario para el documento final del proyecto
3. Evaluar si necesitamos ampliar el vocabulario del tokenizador en el fine-tuning

**Como funciona:** extraemos las palabras mas frecuentes en cada tipologia usando el texto
digital disponible, y filtramos las palabras comunes del espanol para quedarnos con el
vocabulario juridico especifico.
"""))

cells.append(code("""from sklearn.feature_extraction.text import CountVectorizer

# Stopwords basicas en espanol (sin libreria externa)
STOPWORDS_ES = set([
    'de','la','el','en','y','a','los','del','las','un','una','por','con','no',
    'se','su','para','es','al','lo','como','mas','o','pero','sus','le','ya',
    'ha','me','si','fue','que','esta','son','hay','han','ser','una','todo',
    'este','bien','puede','desde','hasta','entre','sobre','sin','muy','tambien',
    'cuando','donde','quien','cual','cada','durante','mediante','segun','ante',
])

print('Extrayendo vocabulario por dominio...')
vocab_results = {}

for cat, folder in CATEGORIES.items():
    if not folder.exists():
        continue
    df_cat = extract_text_sample(folder, categoria=cat)
    df_cat = df_cat[df_cat['text'].str.len() > 100]

    if df_cat.empty:
        continue

    corpus = df_cat['text'].str.lower().tolist()
    try:
        vec = CountVectorizer(
            max_features=300,
            ngram_range=(1, 2),
            token_pattern=r'[a-zA-ZáéíóúñÁÉÍÓÚÑ]{4,}',
        )
        X = vec.fit_transform(corpus)
        freq = dict(zip(vec.get_feature_names_out(), X.toarray().sum(axis=0)))

        # Filtrar stopwords y quedarse con los 30 terminos mas especificos
        # int() convierte numpy.int64 a int nativo para que json.dump no falle
        terminos = {t: int(f) for t, f in sorted(freq.items(), key=lambda x: -x[1])
                    if not any(sw in t.split() for sw in STOPWORDS_ES)}
        top_terminos = dict(list(terminos.items())[:30])
        vocab_results[cat] = top_terminos

        print(f'\\n  {cat} — Top 10 terminos especificos:')
        for t, f in list(top_terminos.items())[:10]:
            print(f'    {t:<35} {f:>5} ocurrencias')
    except Exception as e:
        print(f'  {cat}: error — {e}')

with open(DATA_PROC / 'vocabulario_dominio.json', 'w', encoding='utf-8') as f:
    json.dump(vocab_results, f, ensure_ascii=False, indent=2)
print('\\nVocabulario guardado en vocabulario_dominio.json')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 2: DETECCION DE PORTADAS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 2 — Deteccion de Portadas

Algunos documentos tienen una primera pagina que es solo imagen corporativa: el logo de la
Camara de Comercio, el encabezado de la aseguradora, o una caratula institucional.
Esta pagina no contiene datos estructurados y si la incluimos en la extraccion de texto,
contaminara el input del modelo con texto irrelevante.

**Criterio de deteccion:** si la pagina 1 tiene menos de 50 palabras Y menos de 5 bloques
de texto detectados por PyMuPDF, la clasificamos como portada y la saltamos.

Este criterio fue definido con base en el hallazgo de la revision visual del corpus (Fase 2, §2.0).
Se aplica a **todas las tipologias** — no solo a Camara de Comercio.
"""))

cells.append(code("""def detectar_portada(pdf_path, categoria=''):
    \"\"\"
    Detecta si la pagina 1 de un PDF es una portada (sin datos estructurados).
    Retorna: (tiene_portada: bool, start_page: int)

    NOTA — Cedulas EXCLUIDAS: el criterio (lexicon < 50 AND blocks < 5) genera
    falsos positivos en cedulas escaneadas (93% del corpus) donde pagina 1 = imagen.
    La deteccion de portada solo aplica a Polizas y Camara de Comercio.
    \"\"\"
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

# Ejecutar sobre muestra de 20 docs por tipologia
print('Detectando portadas en muestra del corpus...')
print('(Cedulas: desactivado — falsos positivos en imagenes escaneadas)\\n')
portada_resumen = {}

for cat, folder in CATEGORIES.items():
    if not folder.exists():
        continue
    files = sorted(folder.glob('*.pdf'))[:20]
    con_portada = []

    if cat not in TIPOLOGIAS_CON_PORTADA:
        portada_resumen[cat] = {
            'muestra': len(files), 'con_portada': 0, 'pct': 0.0,
            'ejemplos': [], 'nota': 'Desactivado: no aplica a esta tipologia'
        }
        print(f'  {cat:<22}: DESACTIVADO (no aplica)')
        continue

    for fp in files:
        tiene, _ = detectar_portada(fp, categoria=cat)
        if tiene:
            con_portada.append(fp.name)

    portada_resumen[cat] = {
        'muestra': len(files),
        'con_portada': len(con_portada),
        'pct': round(len(con_portada) / len(files) * 100, 1) if files else 0,
        'ejemplos': con_portada[:3],
    }
    print(f'  {cat:<22}: {len(con_portada)}/{len(files)} docs con portada '
          f'({portada_resumen[cat]["pct"]}%)')

with open(DATA_PROC / 'portadas_detectadas.json', 'w', encoding='utf-8') as f:
    json.dump(portada_resumen, f, ensure_ascii=False, indent=2)
print('\\nResultados guardados en portadas_detectadas.json')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 3: PREPROCESAMIENTO VISUAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 3 — Pipeline de Preprocesamiento Visual

Los documentos clasificados como `REQUIERE_PREPROCESAMIENTO` en el EDA tienen algun
problema de calidad: estan torcidos, tienen bajo contraste, estan borrosos o tienen
iluminacion desigual.

Antes de pasarlos por OCR o por el modelo, los corregimos con este pipeline:

```
imagen_cruda → deskew → denoise → binarize → normalize_dpi → imagen_limpia
```

| Funcion | Que hace | Para que sirve |
|---|---|---|
| `deskew` | Corrige la inclinacion del documento | El OCR falla si el texto esta torcido |
| `denoise` | Elimina ruido de granos y manchas | El ruido confunde al OCR con caracteres falsos |
| `binarize` | Convierte a blanco y negro puro | Simplifica la imagen para el modelo |
| `normalize_dpi` | Redimensiona a 300 DPI | Resolucion estandar para OCR de precision |
"""))

cells.append(code("""def deskew(img_gray):
    \"\"\"Corrige inclinacion detectando el angulo predominante de los contornos de texto.\"\"\"
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

def denoise(img_gray):
    \"\"\"Elimina ruido con filtro gaussiano suave.\"\"\"
    return cv2.GaussianBlur(img_gray, (3, 3), 0)

def enhance_contrast(img_gray, clip_limit=2.0, tile_grid=(8, 8)):
    \"\"\"
    Mejora el contraste local con CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Util para documentos escaneados con iluminacion desigual o fondos grises.
    clip_limit=2.0 es conservador: mejora sin amplificar ruido.
    \"\"\"
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    return clahe.apply(img_gray)

def binarize(img_gray):
    \"\"\"Umbralización adaptativa Otsu: separa texto del fondo de forma robusta.\"\"\"
    _, binarized = cv2.threshold(
        img_gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    return binarized

def normalize_dpi(img_rgb, target_dpi=300, source_dpi=150):
    \"\"\"Redimensiona la imagen al DPI objetivo (estandar para OCR).\"\"\"
    scale = target_dpi / source_dpi
    new_h = int(img_rgb.shape[0] * scale)
    new_w = int(img_rgb.shape[1] * scale)
    return cv2.resize(img_rgb, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

def preprocess_pipeline(pdf_path, categoria=''):
    \"\"\"
    Pipeline completo: abre PDF, detecta portada (segun tipologia), aplica correcciones.
    Flujo: deskew -> denoise -> enhance_contrast -> binarize -> normalize_dpi
    Retorna imagen procesada como array RGB o None si falla.
    \"\"\"
    try:
        doc = fitz.open(str(pdf_path))
        # Detectar portada respetando la tipologia (Cedulas: siempre start_page=0)
        _, start_page = detectar_portada(pdf_path, categoria=categoria)
        if start_page >= doc.page_count:
            start_page = 0

        pix = doc[start_page].get_pixmap(matrix=fitz.Matrix(150/72, 150/72),
                                          colorspace=fitz.csRGB)
        doc.close()
        img_rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3)

        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
        img_gray = deskew(img_gray)
        img_gray = denoise(img_gray)
        img_gray = enhance_contrast(img_gray)   # CLAHE antes de binarizar
        img_gray = binarize(img_gray)
        img_rgb_clean = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)
        img_rgb_clean = normalize_dpi(img_rgb_clean)
        return img_rgb_clean
    except Exception as e:
        return None

print('Funciones de preprocesamiento definidas:')
print('  deskew()           — correccion de inclinacion')
print('  denoise()          — eliminacion de ruido gaussiano')
print('  enhance_contrast() — CLAHE para iluminacion desigual')
print('  binarize()         — binarizacion Otsu')
print('  normalize_dpi()    — normalizacion a 300 DPI')
print('  preprocess_pipeline(pdf_path, categoria) — pipeline completo')
print()
print('NOTA: preprocess_pipeline() acepta categoria para activar/desactivar')
print('      deteccion de portada segun tipologia.')
"""))

cells.append(code("""# Validar pipeline en muestra de docs con REQUIERE_PREPROCESAMIENTO
df_prepro = df_eda[df_eda['quality_label'] == 'REQUIERE_PREPROCESAMIENTO'].copy()
print(f'Documentos que requieren preprocesamiento: {len(df_prepro)}')
print(df_prepro['category'].value_counts().to_string())

muestra = df_prepro.groupby('category').head(3)  # 3 por tipologia
resultados_prepro = []

print(f'\\nValidando pipeline sobre {len(muestra)} documentos...')
for _, row in muestra.iterrows():
    fp = Path(row['filepath'])
    if not fp.exists():
        continue
    img_clean = preprocess_pipeline(fp)
    ok = img_clean is not None
    resultados_prepro.append({
        'filename': row['filename'],
        'category': row['category'],
        'preprocesado': ok,
        'dim_resultado': f'{img_clean.shape[1]}x{img_clean.shape[0]}' if ok else 'error',
    })

df_val = pd.DataFrame(resultados_prepro)
if not df_val.empty:
    print('\\nResultados de validacion:')
    print(df_val.to_string(index=False))
    tasa_exito = df_val['preprocesado'].mean() * 100
    print(f'\\nTasa de exito del pipeline: {tasa_exito:.0f}%')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 4: IDENTIFICACION DE ASEGURADORAS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 4 — Identificacion de Aseguradoras en Polizas

La revision visual del corpus confirmo que las Polizas tienen **layout variable por aseguradora**.
Esto significa que si anotamos 80 Polizas de una sola aseguradora, el modelo aprendera solo ese
formato y fallara con las demas.

La solucion es **anotacion estratificada**: distribuir los 80 documentos de entrenamiento
proporcionalmente entre las aseguradoras presentes en el corpus.

Esta celda identifica automaticamente las aseguradoras presentes usando expresiones regulares
sobre el texto extraido con PyMuPDF de las Polizas digitales.
"""))

cells.append(code("""# Patrones de aseguradoras colombianas comunes
ASEGURADORAS_REGEX = [
    (r'(?i)sura',                    'Sura'),
    (r'(?i)bolivar',                 'Bolivar'),
    (r'(?i)allianz',                 'Allianz'),
    (r'(?i)liberty',                 'Liberty'),
    (r'(?i)axa\\s*colpatria',         'AXA Colpatria'),
    (r'(?i)mapfre',                  'Mapfre'),
    (r'(?i)cardif',                  'Cardif'),
    (r'(?i)previsora',               'La Previsora'),
    (r'(?i)mundial\\s*de\\s*seguros',  'Mundial de Seguros'),
    (r'(?i)equidad',                 'La Equidad'),
    (r'(?i)state\\s*farm',            'State Farm'),
    (r'(?i)chubb',                   'Chubb'),
    (r'(?i)zurich',                  'Zurich'),
    (r'(?i)generali',                'Generali'),
]

def identificar_aseguradora(texto):
    for patron, nombre in ASEGURADORAS_REGEX:
        if re.search(patron, texto):
            return nombre
    return 'Otra/No identificada'

folder_poliza = CATEGORIES.get('Poliza')
conteo_aseg = Counter()
sin_texto = 0

if folder_poliza and folder_poliza.exists():
    files = sorted(folder_poliza.glob('*.pdf'))
    print(f'Analizando {len(files)} Polizas...')
    for fp in tqdm(files, desc='  Polizas'):
        try:
            doc = fitz.open(str(fp))
            _, start = detectar_portada(fp)
            texto = ' '.join(doc[i].get_text()
                             for i in range(start, min(start+3, doc.page_count)))
            doc.close()
            if len(texto.strip()) < 50:
                sin_texto += 1
                conteo_aseg['Escaneada (sin texto)'] += 1
            else:
                aseg = identificar_aseguradora(texto)
                conteo_aseg[aseg] += 1
        except Exception:
            conteo_aseg['Error de lectura'] += 1

    total = sum(conteo_aseg.values())
    print(f'\\nDistribucion de aseguradoras ({total} Polizas):')
    print(f'{"Aseguradora":<30} {"Docs":>6} {"% corpus":>10} {"Docs train (80)":>16}')
    print('-' * 65)
    for aseg, n in conteo_aseg.most_common():
        pct = n / total * 100
        n_train = max(1, round(80 * pct / 100))
        print(f'  {aseg:<28} {n:>6} {pct:>9.1f}% {n_train:>15}')

    # Guardar
    resultado_aseg = {k: v for k, v in conteo_aseg.most_common()}
    with open(DATA_PROC / 'aseguradoras_corpus.json', 'w', encoding='utf-8') as f:
        json.dump(resultado_aseg, f, ensure_ascii=False, indent=2)
    print('\\nGuardado en aseguradoras_corpus.json')
else:
    print('Carpeta POLIZA no encontrada')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 5: CHUNKING
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 5 — Pipeline de Chunking

El modelo Llama 3 tiene un limite de contexto de 2,048 tokens. Con la correccion BPE (x1.25
por la fragmentacion de vocabulario juridico en espanol), el limite duro de seguridad que
usamos es **1,800 tokens**.

Del EDA sabemos que estos documentos superan ese limite con frecuencia:

| Tipologia | Docs > 1,800 tok | Estrategia |
|---|---|---|
| Cedula | 0 | Sin chunking (texto OCR corto) |
| RUT | 151 (64%) | Ventana deslizante 512 tok, overlap 30% |
| Poliza | 31 (14%) | Ventana deslizante 512 tok, overlap 30% |
| Camara de Comercio | 96 (45%) | Layout-aware con OpenCV (secciones logicas) |

### Ventana deslizante

Divide el texto en fragmentos de 512 tokens con un solapamiento del 30%.
El solapamiento garantiza que una entidad que cae justo en el borde de un fragmento
no se pierda — aparece en los dos fragmentos adyacentes y el modelo puede recuperarla.

### Layout-aware (Camara de Comercio)

Usa los bounding boxes de PyMuPDF para detectar secciones logicas del documento
(datos basicos, representantes, establecimientos, actividades economicas) y genera
un chunk por seccion en lugar de cortar arbitrariamente por conteo de tokens.
"""))

cells.append(code("""# Constantes de chunking
TOKENS_HARD_LIMIT = 1800
CHUNK_SIZE        = 512
OVERLAP           = 0.30      # 30% de solapamiento
OVERLAP_TOKENS    = int(CHUNK_SIZE * OVERLAP)   # 153 tokens
BPE_FACTOR        = 1.25

def palabras_a_tokens_bpe(palabras):
    \"\"\"Estima tokens BPE a partir del conteo de palabras.\"\"\"
    return int((palabras / 0.75) * BPE_FACTOR)

def sliding_window_chunks(texto, chunk_size=CHUNK_SIZE, overlap=OVERLAP_TOKENS):
    \"\"\"
    Divide texto en chunks con ventana deslizante.
    chunk_size y overlap estan en tokens estimados.
    Retorna lista de strings (chunks).
    \"\"\"
    palabras = texto.split()
    # Convertir a 'palabras equivalentes' segun ratio inverso BPE
    palabras_por_chunk = int(chunk_size / BPE_FACTOR * 0.75)
    palabras_overlap   = int(overlap / BPE_FACTOR * 0.75)

    chunks, start = [], 0
    while start < len(palabras):
        end = start + palabras_por_chunk
        chunks.append(' '.join(palabras[start:end]))
        start += palabras_por_chunk - palabras_overlap
        if start >= len(palabras):
            break

    return chunks

def layout_aware_chunks(pdf_path):
    \"\"\"
    Chunking por secciones logicas usando bboxes PyMuPDF (para Camara de Comercio).
    Detecta saltos de seccion por espacio vertical entre bloques y agrupa los bloques
    en secciones coherentes, cada una como un chunk independiente.
    \"\"\"
    try:
        doc = fitz.open(str(pdf_path))
        _, start_page = detectar_portada(pdf_path, categoria='Camara de Comercio')
        secciones, seccion_actual = [], []

        for page_num in range(start_page, doc.page_count):
            page   = doc[page_num]
            blocks = page.get_text('blocks')
            blocks = sorted([b for b in blocks if b[6] == 0], key=lambda b: (b[1], b[0]))

            prev_y2 = None
            for b in blocks:
                y1, y2, texto_bloque = b[1], b[3], b[4].strip()
                if not texto_bloque:
                    continue
                # Salto de seccion: espacio vertical > 40px
                if prev_y2 is not None and (y1 - prev_y2) > 40:
                    if seccion_actual:
                        secciones.append(' '.join(seccion_actual))
                        seccion_actual = []
                seccion_actual.append(texto_bloque)
                prev_y2 = y2

        doc.close()
        if seccion_actual:
            secciones.append(' '.join(seccion_actual))

        # Fusionar secciones muy cortas (<50 palabras) con la siguiente
        resultado = []
        buffer = ''
        for s in secciones:
            buffer = (buffer + ' ' + s).strip()
            if len(buffer.split()) >= 50:
                resultado.append(buffer)
                buffer = ''
        if buffer:
            resultado.append(buffer)

        return resultado
    except Exception as e:
        return []

print('Funciones de chunking definidas:')
print(f'  sliding_window_chunks(): chunk={CHUNK_SIZE} tok, overlap={OVERLAP_TOKENS} tok (30%)')
print('  layout_aware_chunks(): segmentacion por secciones logicas con bboxes PyMuPDF')
"""))

cells.append(code("""# Validar chunking sobre muestra de docs que superan el limite
df_chunking = df_eda[df_eda.get('supera_limite_bpe', False) == True].copy() if 'supera_limite_bpe' in df_eda.columns else pd.DataFrame()

if df_chunking.empty:
    # Si no tiene la columna BPE, usar tokens_bpe_ajustado > 1800 del EDA
    df_chunking = df_eda[df_eda.get('tokens_bpe_ajustado', 0) > TOKENS_HARD_LIMIT].copy()

print(f'Documentos que superan limite ({TOKENS_HARD_LIMIT} tok BPE): {len(df_chunking)}')
if not df_chunking.empty:
    print(df_chunking['category'].value_counts().to_string())

# Testear en 2 docs por tipologia
resultados_chunks = []
cats_chunking = ['RUT', 'Poliza', 'Camara de Comercio']

for cat in cats_chunking:
    folder = CATEGORIES.get(cat)
    if not folder or not folder.exists():
        continue
    files = sorted(folder.glob('*.pdf'))[:2]

    for fp in files:
        doc = fitz.open(str(fp))
        _, start = detectar_portada(fp, categoria=cat)
        texto = ' '.join(doc[i].get_text() for i in range(start, doc.page_count))
        doc.close()

        n_palabras = len(texto.split())
        tokens_est = palabras_a_tokens_bpe(n_palabras)

        if cat == 'Camara de Comercio':
            chunks = layout_aware_chunks(fp)
            metodo = 'layout_aware'
        else:
            chunks = sliding_window_chunks(texto) if tokens_est > TOKENS_HARD_LIMIT else [texto]
            metodo = 'sliding_window' if tokens_est > TOKENS_HARD_LIMIT else 'sin_chunking'

        resultados_chunks.append({
            'filename': fp.name,
            'category': cat,
            'tokens_estimados': tokens_est,
            'n_chunks': len(chunks),
            'metodo': metodo,
            'max_chunk_palabras': max((len(c.split()) for c in chunks), default=0),
        })

df_chunks = pd.DataFrame(resultados_chunks)
if not df_chunks.empty:
    print('\\nValidacion de chunking:')
    print(df_chunks.to_string(index=False))
"""))

cells.append(code("""import re as _re

# Filtro CIIU inline — necesario antes de chunk_document (definicion completa en Seccion 5b)
_CIIU_HEADER = _re.compile(r'(?i)(?:24\\.\\s*ACTIVIDADES?\\s*ECON[OO]MICAS?|casilla\\s*24)')
_CIIU_FOOD   = _re.compile(
    r'\\b(org[aá]nicas?|congeladas?|congelados?|frasco|lata|secas?|secos?|org[aá]nicos?)\\b',
    _re.IGNORECASE)

def filtrar_ciiu_rut(texto):
    m = _CIIU_HEADER.search(texto)
    if m:
        filtrado = texto[:m.start()].strip()
        if len(filtrado) > 200:
            return filtrado
    return _CIIU_FOOD.sub('', texto)

def chunk_document(pdf_path, doc_type):
    \"\"\"
    Funcion unificada de chunking — doc_type determina la estrategia internamente.

    Estrategias:
      Cedula           -> sin chunking (texto OCR corto)
      RUT              -> filtro CIIU + ventana deslizante si > 1800 tokens
      Poliza           -> ventana deslizante si > 1800 tokens
      Camara de Comercio -> layout-aware con bboxes PyMuPDF

    Retorna dict: {doc_type, estrategia, n_chunks, chunks, tokens_estimados}
    \"\"\"
    try:
        doc = fitz.open(str(pdf_path))
        _, start_page = detectar_portada(pdf_path, categoria=doc_type)
        texto = ' '.join(doc[i].get_text() for i in range(start_page, doc.page_count))
        doc.close()
    except Exception:
        return {'doc_type': doc_type, 'estrategia': 'error', 'n_chunks': 0,
                'chunks': [], 'tokens_estimados': 0}

    # Filtro CIIU solo para RUT
    if doc_type == 'RUT':
        texto = filtrar_ciiu_rut(texto)

    tokens_est = palabras_a_tokens_bpe(len(texto.split()))

    if doc_type == 'Cedula':
        return {'doc_type': doc_type, 'estrategia': 'sin_chunking',
                'n_chunks': 1 if texto.strip() else 0,
                'chunks': [texto] if texto.strip() else [],
                'tokens_estimados': tokens_est}

    if doc_type == 'Camara de Comercio':
        chunks = layout_aware_chunks(pdf_path)
        return {'doc_type': doc_type, 'estrategia': 'layout_aware',
                'n_chunks': len(chunks), 'chunks': chunks, 'tokens_estimados': tokens_est}

    # RUT y Poliza: ventana deslizante si supera el limite
    if tokens_est > TOKENS_HARD_LIMIT:
        chunks = sliding_window_chunks(texto)
        estrategia = 'sliding_window'
    else:
        chunks = [texto]
        estrategia = 'sin_chunking'

    return {'doc_type': doc_type, 'estrategia': estrategia,
            'n_chunks': len(chunks), 'chunks': chunks, 'tokens_estimados': tokens_est}

# Demostrar chunk_document() sobre un doc por tipologia
print('Demostracion de chunk_document():')
print('-' * 65)
for cat, folder in CATEGORIES.items():
    if not folder.exists():
        continue
    fp = sorted(folder.glob('*.pdf'))[0]
    result = chunk_document(fp, cat)
    print(f'  {cat:<22} | estrategia={result[\"estrategia\"]:<16} '
          f'| chunks={result[\"n_chunks\"]} | tokens_est={result[\"tokens_estimados\"]}')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 5b: FILTRO CIIU + LABELING FUNCTIONS PARA RUT
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 5b — Filtro CIIU y Pre-anotacion Automatica de RUT

### Por que necesitamos esto?

El analisis de vocabulario revelo que los documentos RUT contienen la lista completa de
clasificaciones CIIU del formulario DIAN — miles de terminos de actividades economicas
(frutas organicas, latas, frascos, congelados) que no son entidades NER sino ruido del
formulario. Si estos terminos entran en los embeddings de RUT, el modelo aprendera
asociaciones erroneas.

**Solucion en dos pasos:**
1. `filtrar_ciiu_rut()` — elimina la seccion CIIU antes de generar embeddings
2. `extraer_entidades_rut()` — regex Labeling Functions para pre-anotar los 235 RUT
   automaticamente antes de la revision humana en Label Studio
"""))

cells.append(code("""import re

# ── Filtro CIIU para RUT ─────────────────────────────────────────────────────
# Patron del encabezado de la seccion de actividades economicas en el formulario DIAN
_CIIU_HEADER = re.compile(
    r'(?i)(?:24\\.\\s*ACTIVIDADES?\\s*ECON[OO]MICAS?|casilla\\s*24)',
)
# Vocabulario alimentario CIIU que contamina embeddings de RUT
_CIIU_FOOD_TERMS = re.compile(
    r'\\b(org[aá]nicas?|congeladas?|congelados?|frasco|lata|secas?|secos?|'
    r'org[aá]nicos?|frescas?|frescos?|deshidratadas?|enlatadas?)\\b',
    re.IGNORECASE,
)

def filtrar_ciiu_rut(texto):
    \"\"\"
    Elimina la seccion de actividades CIIU del texto de un RUT para embeddings limpios.
    Paso 1: truncar desde el header de la seccion CIIU.
    Paso 2 (fallback): eliminar tokens del vocabulario CIIU conocido.
    \"\"\"
    match = _CIIU_HEADER.search(texto)
    if match:
        filtrado = texto[:match.start()].strip()
        if len(filtrado) > 200:
            return filtrado
    return _CIIU_FOOD_TERMS.sub('', texto)

# ── Regex Labeling Functions para RUT ────────────────────────────────────────
def extraer_entidades_rut(texto):
    \"\"\"
    Extrae entidades NER de un RUT con regex (Labeling Functions para pre-anotacion).
    Retorna dict con entidades encontradas (None si no se detecta).
    Usar sobre texto COMPLETO (NO aplicar filtrar_ciiu_rut antes para NER).

    Calibrado para el formato real del formulario DIAN:
    - NIT: cajas de digitos individuales separados por espacio (8 6 0 5 1...)
    - Razon social: MAYUSCULAS con forma juridica (LTDA, SAS, SA, EU...)
    - RL: APELLIDOS NOMBRES justo antes de la linea 'Representante legal'
    \"\"\"
    entidades = {}

    # NIT — formato continuo con guion O cajas DIAN (digitos con espacio)
    m = re.search(r'\\b(\\d{7,11})\\s*[-\\u2013]\\s*(\\d)\\b', texto)
    if m:
        entidades['nit'] = f\"{m.group(1)}-{m.group(2)}\"
    else:
        m = re.search(r'(\\d(?: \\d){8,9})', texto)
        if m:
            digits = m.group(1).replace(' ', '')
            entidades['nit'] = f\"{digits[:-1]}-{digits[-1]}\" if len(digits) >= 9 else digits
        else:
            entidades['nit'] = None

    # Razon social — lineas MAYUSCULAS con forma juridica conocida
    m = re.search(
        r'\\n([A-Z][A-Z\\s\\.,&-]{8,99}(?:LTDA|SAS|S\\.A|E\\.U|EIRL|CIA|INC)[^\\n]*)\\n',
        texto,
    )
    entidades['razon_social'] = m.group(1).strip() if m else None

    # Regimen — normalizado: ordinar* -> ordinario, simpli* -> simplificado
    m = re.search(r'(?i)r[eé]gimen\\s+(\\w+)', texto)
    if m:
        r = m.group(1).strip()
        if r.lower().startswith('ordinar'):
            r = 'ordinario'
        elif r.lower().startswith('simpli'):
            r = 'simplificado'
        entidades['regimen'] = r
    else:
        entidades['regimen'] = None

    # Direccion — nomenclatura colombiana (CL, CR, AV, TV, KR + numero)
    m = re.search(r'(?i)\\b((?:CL|CR|AV|TV|KR|CALLE|CARRERA|AVENIDA)\\s+\\d+[^\\n]{5,80})', texto)
    entidades['direccion'] = m.group(1).strip() if m else None

    # Municipio — ciudades principales de Colombia
    m = re.search(
        r'(Bogot[aá][\\s,]*D\\.?C\\.?|Medell[ií]n|Cali|Barranquilla|Cartagena|'
        r'Bucaramanga|Pereira|Manizales|Ibagu[eé]|[Cc][uú]cuta|Villavicencio|'
        r'Santa Marta|Monter[ií]a|Neiva|Armenia|Pasto|Popay[aá]n)',
        texto,
    )
    entidades['municipio'] = m.group(1).strip() if m else None

    # Representante legal — APELLIDOS NOMBRES antes de linea 'Representante legal'
    m = re.search(
        r'([A-Z]{2,}(?:\\s+[A-Z]{2,}){1,5})\\s*\\nRepresentante legal',
        texto,
    )
    entidades['representante_legal'] = m.group(1).strip() if m else None

    return entidades

# ── Validar sobre muestra de RUT ─────────────────────────────────────────────
folder_rut = CATEGORIES.get('RUT')
if folder_rut and folder_rut.exists():
    files_rut = sorted(folder_rut.glob('*.pdf'))[:5]
    print('Validacion de Labeling Functions sobre 5 documentos RUT:')
    print('-' * 70)
    exitosos = 0
    for fp in files_rut:
        doc = fitz.open(str(fp))
        texto_crudo = ' '.join(doc[i].get_text() for i in range(doc.page_count))
        doc.close()
        # NOTA: para NER usar texto COMPLETO (no filtrado)
        # filtrar_ciiu_rut() es solo para embeddings/TF-IDF
        entidades = extraer_entidades_rut(texto_crudo)
        encontradas = sum(1 for v in entidades.values() if v is not None)
        exitosos += (1 if encontradas >= 3 else 0)
        print(f'  {fp.name[:45]:<45} | ents: {encontradas}/6')
        for campo, valor in entidades.items():
            if valor:
                print(f'      {campo:<22}: {str(valor)[:60]}')
    print(f'\\n  LFs exitosas (>= 3 entidades encontradas): {exitosos}/{len(files_rut)}')
else:
    print('Carpeta RUT no encontrada')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# SECCION 6: RESUMEN Y PROXIMOS PASOS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""---
## Seccion 6 — Resumen y Proximos Pasos

### Que queda listo despues de este notebook

| Artefacto | Descripcion |
|---|---|
| `near_duplicates.json` | Pares de documentos con similitud coseno >= 0.90 |
| `vocabulario_dominio.json` | Top 30 terminos juridicos por tipologia |
| `portadas_detectadas.json` | Proporcion de documentos con portada por tipologia |
| `aseguradoras_corpus.json` | Distribucion de aseguradoras en Polizas (dato informativo) |
| Funciones de preprocesamiento | `deskew`, `denoise`, `enhance_contrast`, `binarize`, `normalize_dpi`, `preprocess_pipeline` |
| Funciones de chunking | `sliding_window_chunks`, `layout_aware_chunks`, `chunk_document` |
| Filtro CIIU | `filtrar_ciiu_rut()` — elimina ruido de actividades economicas antes de embeddings |
| Labeling Functions RUT | `extraer_entidades_rut()` — pre-anotacion automatica regex para 235 RUT |

### Que sigue: la anotacion humana

El siguiente paso es la **anotacion de los documentos** en Label Studio.
Este es el unico paso que requiere intervencion humana — es el trabajo de etiquetado
que el modelo usara como ground truth para aprender.

**Distribucion de la carga de anotacion:**

| Tipologia | Estrategia | Docs a anotar |
|---|---|---|
| Cedula | OCR muestral (EasyOCR) + revision manual bboxes | 60 docs |
| RUT | Pre-anotacion automatica LFs + revision humana | 235 docs (revision de errores) |
| Poliza | Anotacion manual (muestra aleatoria digitales) | 80 docs |
| Camara de Comercio | Anotacion manual | 80 docs |

**Nota sobre RUT:** las Labeling Functions generan pre-anotaciones automaticas
sobre los 235 docs digitales. En Label Studio solo hay que corregir los errores,
no anotar desde cero. Esto reduce el trabajo de anotacion de RUT en ~70%.

Una vez completada la anotacion, el **Notebook 03** tomara estos datos anotados
y ejecutara el fine-tuning del modelo Llama 3 con QLoRA.
"""))

cells.append(code("""# Exportar resumen de artefactos generados
artefactos = {
    'near_duplicates':       str(DATA_PROC / 'near_duplicates.json'),
    'vocabulario_dominio':   str(DATA_PROC / 'vocabulario_dominio.json'),
    'portadas_detectadas':   str(DATA_PROC / 'portadas_detectadas.json'),
    'aseguradoras_corpus':   str(DATA_PROC / 'aseguradoras_corpus.json'),
}

print('Artefactos generados en esta fase:')
for nombre, ruta in artefactos.items():
    existe = Path(ruta).exists()
    estado = 'OK' if existe else 'PENDIENTE'
    print(f'  [{estado}] {nombre:<30} {ruta}')

print()
print('FASE 2 — Pipeline automatizado completado.')
print('Siguiente paso: anotacion en Label Studio (Seccion 2.2 del plan).')
"""))

# ══════════════════════════════════════════════════════════════════════════════
# ENSAMBLAR Y GUARDAR
# ══════════════════════════════════════════════════════════════════════════════
nb.cells = cells
nb.metadata = {
    'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
    'language_info': {'name': 'python', 'version': '3.12.0'},
}

out = Path(__file__).parent / '02_preprocesamiento_pipeline.ipynb'
import nbformat
nbformat.write(nb, str(out))
print(f'Notebook generado: {out}')
print(f'Total celdas: {len(cells)}')
