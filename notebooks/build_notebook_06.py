"""
Genera el notebook 06_preanotaciones_rut.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_06.py

Proposito:
    Aplicar las Labeling Functions (regex) de RUT a los 216 documentos del
    corpus OCR y generar pre-anotaciones automaticas que se cargaran en
    Label Studio para correccion humana.

Contexto academico: Fase 2 CRISP-DM++ §2.2 — Weak Supervision (primer paso
de la estrategia de etiquetado hibrida). Los humanos solo corrigen los
casos donde la LF fallo; esto reduce el trabajo de anotacion ~70%.

Fundamentacion cientifica:
    - Ratner et al., "Snorkel: Rapid Training Data Creation with Weak Supervision",
      VLDB 2018 — https://arxiv.org/abs/1711.10160

Estructura (M = markdown, C = code):
     1 M  Portada + contexto
     2 M  Que es Weak Supervision y por que aqui
     3 M  Setup
     4 C  Imports + rutas
     5 M  Cargar corpus OCR + filtrar RUT
     6 C  Filtro + consolidar texto por doc
     7 M  Aplicar LFs de pipeline.py
     8 C  Aplicar extraer_entidades_rut()
     9 M  Analisis de cobertura por entidad
    10 C  Stats + visualizacion
    11 M  Validacion contra gold seed (3 RUT transcritos)
    12 C  Medir precision de LFs vs gold
    13 M  Exportar a Label Studio (JSON task format)
    14 C  Generar rut_preanotaciones_labelstudio.json
    15 M  Exportar JSONL compacto para el dataset
    16 C  Generar rut_preanotaciones.jsonl + summary.csv
    17 M  Resumen + siguiente paso
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
cells.append(md("""# SinergIA Lab — Pre-anotaciones RUT via Weak Supervision
## Fase 2 CRISP-DM++ · §2.2 — Generacion de pre-anotaciones automaticas

---

### Proposito

Aplicar las **Labeling Functions (LFs)** de regex ya implementadas en `src/preprocessing/pipeline.py` a los **216 documentos RUT** del corpus OCR y producir:

1. **Pre-anotaciones automaticas** — primer candidato de cada entidad por doc
2. **Tareas Label Studio** — formato JSON listo para importar
3. **Metricas de cobertura** — que % de docs tienen cada entidad detectada

### Que produce este notebook

| Archivo | Contenido | En repo? |
|---|---|---|
| `data/processed/rut_preanotaciones.jsonl` | 1 fila por doc con entidades extraidas | ❌ (PII) |
| `data/processed/rut_preanotaciones_labelstudio.json` | Tareas formato Label Studio | ❌ (PII) |
| `data/processed/rut_preanotaciones_summary.csv` | Cobertura por entidad (sin valores PII) | ✅ |

### Dependencia previa

⚠️ **Requiere haber ejecutado los notebooks 05 y 05b**. Este notebook lee `data/processed/corpus_ocr.csv`.

### Tiempo estimado

~2-3 minutos. Las LFs son regex sobre texto — no hay GPU ni modelos pesados.

### Importancia para el proyecto

Este es el **primer paso de Fase 2 §2.2** y destraba:
- Dataset de entrenamiento para los 3 candidatos de Clasificacion (§3.0)
- Dataset de entrenamiento para los 3 candidatos de NER (§3.1) en tipologia RUT
- Flujo de trabajo de Label Studio para las demas tipologias (Cedula, Poliza, CC)
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. QUE ES WEAK SUPERVISION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Que es Weak Supervision y por que aqui

**Weak Supervision** es un paradigma de creacion de datos etiquetados donde, en vez de pagar por anotacion manual de cada documento, se usan **fuentes de etiquetado ruidosas pero escalables** (heuristicas, reglas, patrones) para generar etiquetas candidatas que luego un humano corrige selectivamente.

### Paper fundacional

> Ratner, A. et al. (2018). **Snorkel: Rapid Training Data Creation with Weak Supervision**. *VLDB 2018.*
> https://arxiv.org/abs/1711.10160

### Aplicacion en este proyecto

Para RUT, las **LFs regex** son un candidato ideal porque:

| Caracteristica del RUT | Implicacion |
|---|---|
| Formulario DIAN estandar, mismos campos para todos los contribuyentes | Las regex funcionan consistentemente |
| Texto digital disponible (PyMuPDF extrae sin OCR) | Sin ruido de OCR que confunda el regex |
| Entidades con formatos regulares (NIT con guion, direccion con CL/CR) | Alta precision en la deteccion |

### Precaucion documentada

> **⚠️ ALERTA v1.3 del plan:** Las Cedulas NO son elegibles para regex LFs porque 93% son escaneadas y el texto OCR tiene ~28% CER — la tasa de error invalida la estrategia automatica. Para Cedulas se usa anotacion manual sobre salida OCR.

### Rendimiento esperado

En el piloto (5 docs validados en Notebook 02) las LFs lograron **5/5 correcto** para todas las entidades. En el corpus completo de 216 RUT se espera algo menor (~70-85% precision) por:
- Layouts variantes entre años (formularios DIAN de 2015 vs 2024)
- Errores de extraccion PyMuPDF en paginas con imagenes embebidas
- Abreviaciones no cubiertas por la regex de direccion

**Por eso la revision humana en Label Studio es obligatoria antes de entrenar.**
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 3. SETUP
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Setup — imports y rutas"""))

cells.append(code("""import sys
import json
import re
import unicodedata
from pathlib import Path
from collections import Counter

import pandas as pd
import numpy as np

# Rutas del proyecto
PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_PROC = PROJECT_ROOT / 'data' / 'processed'
DATA_GOLD = PROJECT_ROOT / 'data' / 'gold'
SRC_DIR   = PROJECT_ROOT / 'src'

# Anadir src al path para importar pipeline.py
if str(SRC_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SRC_DIR.parent))

from src.preprocessing.pipeline import extraer_entidades_rut

CORPUS_OCR        = DATA_PROC / 'corpus_ocr.csv'
PREANOT_JSONL     = DATA_PROC / 'rut_preanotaciones.jsonl'
PREANOT_LABELST   = DATA_PROC / 'rut_preanotaciones_labelstudio.json'
PREANOT_SUMMARY   = DATA_PROC / 'rut_preanotaciones_summary.csv'

assert CORPUS_OCR.exists(), f'Falta {CORPUS_OCR}. Ejecuta primero nb 05 y 05b.'
print(f'Setup OK. Input: {CORPUS_OCR}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGAR CORPUS + FILTRAR RUT
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Cargar `corpus_ocr.csv` y aislar los RUT

El corpus tiene 960 docs / 13,254 paginas. Filtramos por folder que contenga `rut` (case-insensitive) para manejar la normalizacion pendiente de nombres (hay `RUT` y `rut` por mojibake — ver hallazgo §2.1.4 del plan).

Luego consolidamos las paginas de cada doc en un solo texto (muchos RUT tienen 4-16 paginas del formulario DIAN repetido con secciones distintas).
"""))

cells.append(code("""corpus = pd.read_csv(CORPUS_OCR)
print(f'Corpus total: {len(corpus):,} filas / {corpus[\"md5\"].nunique()} docs')

# Filtrar RUT — acepta RUT y rut (normalizacion pendiente)
rut_mask = corpus['folder'].str.lower().str.contains('rut', na=False)
rut_pages = corpus[rut_mask].sort_values(['md5', 'page_num']).reset_index(drop=True)
print(f'Paginas RUT:   {len(rut_pages):,}')
print(f'Docs RUT:      {rut_pages[\"md5\"].nunique()}')
print(f'Por engine:    {rut_pages[\"engine\"].value_counts().to_dict()}')
print()

# Consolidar texto por doc (concat paginas con \\n\\n entre ellas)
# Sintaxis defensiva — evita named aggregation que ha dado conflictos en algunas
# versiones de pandas cuando la key del output coincide con el nombre de la columna input.
def _concat_pages(pages):
    return '\\n\\n'.join(str(x) for x in pages if isinstance(x, str))

rut_docs = (rut_pages
    .groupby('md5', as_index=False)
    .agg({
        'filename':  'first',
        'folder':    'first',
        'engine':    'first',
        'page_num':  'size',
        'texto_ocr': _concat_pages,
    })
    .rename(columns={'page_num': 'n_pages', 'texto_ocr': 'texto_completo'})
)
rut_docs['n_chars'] = rut_docs['texto_completo'].str.len()
print(f'Docs consolidados: {len(rut_docs)}')
print(f'Chars promedio/doc: {rut_docs[\"n_chars\"].mean():.0f}')
print(f'Chars minimo/maximo: {rut_docs[\"n_chars\"].min()} / {rut_docs[\"n_chars\"].max()}')
print()
print('Columnas disponibles:', list(rut_docs.columns))
rut_docs.head(3)[['filename','n_pages','n_chars','engine']]
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. APLICAR LFs
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Aplicar las Labeling Functions de `pipeline.py`

La funcion `extraer_entidades_rut(texto)` aplica en orden las 6 LFs documentadas en §2.2 del plan:

1. **NIT** — formato con guion `860518862-7` o cajas DIAN `8 6 0 5 1 8 8 6 2 7`
2. **razon_social** — MAYUSCULAS con forma juridica (LTDA/SAS/S.A/E.U/EIRL)
3. **regimen** — normalizado (`ordinar*` → `ordinario`, `simpli*` → `simplificado`)
4. **direccion** — nomenclatura colombiana (CL/CR/AV/TV/KR + numero)
5. **municipio** — lista de 17 ciudades principales
6. **representante_legal** — APELLIDOS NOMBRES antes de "Representante legal"

Cada LF devuelve `None` si no matchea. Eso es **informacion util** — nos dice que el anotador humano debe prestar atencion a ese campo.
"""))

cells.append(code("""# Aplicar LFs a cada doc
preanot_list = []
for _, row in rut_docs.iterrows():
    entidades = extraer_entidades_rut(row['texto_completo'])
    preanot_list.append({
        'md5':           row['md5'],
        'filename':      row['filename'],
        'folder':        row['folder'],
        'engine':        row['engine'],
        'n_pages':       row['n_pages'],
        'n_chars':       row['n_chars'],
        **entidades,
    })

preanot = pd.DataFrame(preanot_list)
print(f'Pre-anotaciones generadas: {len(preanot)} docs')
print()
print('Columnas:', list(preanot.columns))
print()
preanot.head(5)
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. ANALISIS DE COBERTURA
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Analisis de cobertura — que % de RUT tiene cada entidad detectada

Para cada entidad, medimos:
- **Cobertura:** % de docs donde la LF encontro un valor (no-null)
- **Unicidad:** cuantos valores unicos aparecen en el corpus

Si una entidad tiene cobertura baja (<50%), o bien la LF tiene un bug, o bien los RUT del corpus no contienen ese campo (ej. direccion en algunos formularios antiguos).

Si una entidad tiene cobertura alta (>90%), la LF esta bien calibrada y la correccion humana sera marginal.
"""))

cells.append(code("""entidades = ['nit', 'razon_social', 'regimen', 'direccion', 'municipio', 'representante_legal']

cobertura = []
for ent in entidades:
    total = len(preanot)
    detectados = preanot[ent].notna().sum()
    unicos = preanot[ent].dropna().nunique()
    cobertura.append({
        'entidad':    ent,
        'detectados': detectados,
        'nulos':      total - detectados,
        'cobertura':  round(detectados / total, 3),
        'unicos':     unicos,
    })

cob_df = pd.DataFrame(cobertura)
print('=== COBERTURA DE LFs POR ENTIDAD ===')
print(cob_df.to_string(index=False))
print()

# Distribuciones interesantes
print('=== Top 5 municipios detectados ===')
if preanot['municipio'].notna().any():
    print(preanot['municipio'].value_counts().head().to_string())

print()
print('=== Top 5 regimenes detectados ===')
if preanot['regimen'].notna().any():
    print(preanot['regimen'].value_counts().head().to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. VALIDACION CONTRA GOLD
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Validacion contra gold seed — medir precision de las LFs

El gold seed tiene **3 RUT transcritos manualmente**. Podemos medir si las LFs extrajeron los mismos valores que el humano.

**Metodologia:**
1. Tomar los 3 md5 del gold que son RUT
2. Aplicar `extraer_entidades_rut()` al texto OCR del mismo doc
3. Comparar contra lo que aparece en las transcripciones manuales (busqueda de substring)

Esta es una validacion **aproximada** porque las transcripciones manuales no tienen estructura campo-por-campo. Pero sirve de sanity check: si una entidad que detecta la LF NO aparece en la transcripcion humana, probablemente es una falsa deteccion.
"""))

cells.append(code("""manifest_gold = pd.read_csv(DATA_GOLD / 'gold_seed_manifest.csv')
rut_gold = manifest_gold[manifest_gold['folder'].str.lower() == 'rut']
print(f'RUT en gold: {len(rut_gold)} docs')

validacion = []
for _, mf in rut_gold.iterrows():
    md5 = mf['md5']
    tpath = DATA_GOLD / 'transcriptions' / f'{md5}.txt'
    if not tpath.exists():
        continue
    gold_text = tpath.read_text(encoding='utf-8', errors='ignore').lower()
    preanot_row = preanot[preanot['md5'] == md5]
    if preanot_row.empty:
        continue
    pr = preanot_row.iloc[0]

    # Para cada entidad: ¿el valor detectado aparece en el texto gold?
    for ent in entidades:
        val = pr[ent]
        if val is None or (isinstance(val, float) and pd.isna(val)):
            validacion.append({'md5': md5[:8], 'entidad': ent, 'detectado': None, 'en_gold': None})
            continue
        # Comparacion flexible: normalizamos (lower, sin tildes) y buscamos
        val_norm = unicodedata.normalize('NFKD', str(val)).encode('ascii','ignore').decode('ascii').lower().strip()
        gold_norm = unicodedata.normalize('NFKD', gold_text).encode('ascii','ignore').decode('ascii').lower()
        # Para NIT: normalizar a solo digitos para comparar
        if ent == 'nit':
            digitos = re.sub(r'[^0-9]', '', val_norm)
            en_gold = digitos in re.sub(r'[^0-9]', '', gold_norm)
        else:
            # Usar primeras 3 palabras del valor si es largo
            chunk = ' '.join(val_norm.split()[:3])
            en_gold = chunk in gold_norm
        validacion.append({'md5': md5[:8], 'entidad': ent, 'detectado': val, 'en_gold': en_gold})

val_df = pd.DataFrame(validacion)
print()
print('=== VALIDACION LFs vs GOLD ===')
print(val_df.to_string(index=False))

# Precision por entidad
det = val_df[val_df['en_gold'].notna()].copy()
if len(det):
    det['en_gold_int'] = det['en_gold'].astype(bool).astype(int)
    prec = det.groupby('entidad')['en_gold_int'].agg(hits='sum', total='size').reset_index()
    prec['precision'] = (prec['hits'].astype(float) / prec['total'].astype(float)).round(3)
    print()
    print('=== PRECISION POR ENTIDAD (sobre docs detectados) ===')
    print(prec.to_string(index=False))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7.5 NORMALIZACION POST-EXTRACCION
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Normalizacion post-extraccion (pre-Label Studio)

Antes de exportar a Label Studio aplicamos dos normalizaciones para evitar contaminar el dataset de entrenamiento con variantes triviales:

### 1. Municipio — unificar variantes de Bogota

Las 4 variantes detectadas en la extraccion raw (`Bogota D.C.`, `Bogota D.C`, `Bogota DC`, `BOGOTA D.C.`) colapsan a un canonico **`Bogota D.C.`**. Lo mismo con el resto: normalizamos espacios y puntuacion final, respetando la capitalizacion del municipio.

### 2. Regimen — distinguir `simple` vs `simplificado`

El regex original mapeaba `simpli*` → `simplificado` pero dejaba `Simple` (Regimen Simple de Tributacion, RST) sin normalizar. Aqui **distinguimos los dos regimenes** porque son juridicamente distintos en Colombia (Ley 2155 de 2021 vs antiguo IVA simplificado):

- `Simple*` / `simple*` → `simple` (RST)
- `Simplifi*` / `simpli*` → `simplificado`

### Por que normalizar ANTES de Label Studio y no DESPUES

Si el humano ve `Bogota D.C` y `Bogota D.C.` como entidades distintas, podria **aprobar ambas como validas**, consolidando el ruido en el ground truth. La normalizacion previa fuerza consistencia.
"""))

cells.append(code("""# Mapeo canonico de municipios — solo consolida variantes evidentes de Bogota
_BOGOTA_VARIANTS = [
    'BOGOTA D.C.', 'Bogota D.C', 'Bogota DC', 'BOGOTÁ D.C.',
    'Bogotá D.C', 'Bogotá DC', 'bogota d.c.', 'bogota d.c',
]
_MUN_CANONICO = {v.lower().strip('.').replace('á','a').replace('  ',' '): 'Bogotá D.C.' for v in _BOGOTA_VARIANTS}

def normalizar_municipio(m):
    if m is None or (isinstance(m, float) and pd.isna(m)):
        return None
    m = str(m).strip()
    # Eliminar puntuacion final repetida, colapsar espacios
    m_clean = re.sub(r'\\s+', ' ', m).strip().strip('.')
    key = unicodedata.normalize('NFKD', m_clean).encode('ascii','ignore').decode('ascii').lower().strip()
    return _MUN_CANONICO.get(key, m)  # si no esta en el mapa, devolver original


def normalizar_regimen(r):
    if r is None or (isinstance(r, float) and pd.isna(r)):
        return None
    r_norm = str(r).lower().strip()
    if r_norm.startswith('simple'):
        return 'simple'         # Regimen Simple de Tributacion (Ley 2155/2021)
    if r_norm.startswith('simpli'):
        return 'simplificado'   # Antiguo regimen simplificado de IVA
    if r_norm.startswith('ordinar'):
        return 'ordinario'
    if r_norm.startswith('especial'):
        return 'especial'
    return r_norm


# Aplicar al dataframe preanot
preanot['municipio'] = preanot['municipio'].apply(normalizar_municipio)
preanot['regimen']   = preanot['regimen'].apply(normalizar_regimen)

print('=== DESPUES DE NORMALIZACION ===\\n')
print('Regimen:')
print(preanot['regimen'].value_counts(dropna=False).to_string())
print()
print('Municipio (top 10):')
print(preanot['municipio'].value_counts(dropna=False).head(10).to_string())

# Refrescar cobertura
cobertura = []
for ent in entidades:
    total = len(preanot)
    detectados = preanot[ent].notna().sum()
    unicos = preanot[ent].dropna().nunique()
    cobertura.append({
        'entidad':    ent,
        'detectados': detectados,
        'nulos':      total - detectados,
        'cobertura':  round(detectados / total, 3),
        'unicos':     unicos,
    })
cob_df = pd.DataFrame(cobertura)
print('\\n=== COBERTURA POST-NORMALIZACION ===')
print(cob_df.to_string(index=False))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. EXPORTAR A LABEL STUDIO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Exportar a formato Label Studio

Label Studio acepta tareas en formato JSON con **predictions** (pre-anotaciones que el humano revisara y corregira). Cada tarea = 1 documento, y contiene:

- El texto completo del RUT
- Las pre-anotaciones como `predictions` con score de confianza
- Metadata (`md5`, `filename`) para trazabilidad

El humano en Label Studio ve el texto + las entidades resaltadas; acepta, corrige o elimina cada una.

**Documentacion:** https://labelstud.io/guide/predictions
"""))

cells.append(code("""# Construir tareas Label Studio
tasks_ls = []
for _, row in preanot.iterrows():
    predictions = []
    # Cada entidad detectada → un span con label
    # Para NER en texto, Label Studio necesita start/end offset en el texto
    for ent in entidades:
        val = row[ent]
        if val is None or (isinstance(val, float) and pd.isna(val)):
            continue
        val_str = str(val)
        # Buscar primer match del valor en el texto
        texto = str(preanot.loc[preanot['md5']==row['md5'], 'md5'].iloc[0])  # placeholder
        # En realidad necesitamos el texto completo — pero no esta en preanot.
        # Lo obtenemos de rut_docs
        texto_real = rut_docs.loc[rut_docs['md5'] == row['md5'], 'texto_completo'].iloc[0]
        idx = texto_real.find(val_str)
        if idx < 0:
            # Intentar match case-insensitive
            idx = texto_real.lower().find(val_str.lower())
        if idx < 0:
            continue
        predictions.append({
            'from_name': 'label',
            'to_name':   'text',
            'type':      'labels',
            'value': {
                'start':  idx,
                'end':    idx + len(val_str),
                'text':   val_str,
                'labels': [ent],
            },
            'score': 0.8,  # confianza heuristica — todas las LFs tienen similar precision
        })

    task = {
        'data': {
            'text':     rut_docs.loc[rut_docs['md5']==row['md5'], 'texto_completo'].iloc[0],
            'md5':      row['md5'],
            'filename': row['filename'],
            'folder':   row['folder'],
            'n_pages':  int(row['n_pages']),
        },
        'predictions': [{
            'model_version': 'LFs_regex_v1',
            'result':        predictions,
        }],
    }
    tasks_ls.append(task)

# Guardar
with PREANOT_LABELST.open('w', encoding='utf-8') as f:
    json.dump(tasks_ls, f, ensure_ascii=False, indent=2)

total_pred = sum(len(t['predictions'][0]['result']) for t in tasks_ls)
print(f'Tareas Label Studio generadas: {len(tasks_ls)}')
print(f'Pre-anotaciones totales: {total_pred}')
print(f'Promedio por doc: {total_pred/len(tasks_ls):.2f}')
print(f'Archivo: {PREANOT_LABELST}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 9. EXPORTAR JSONL + SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Exportar JSONL + summary commiteable

- **`rut_preanotaciones.jsonl`** — 1 fila por doc con entidades. Formato JSONL (una linea JSON por doc) para streaming durante entrenamiento.
- **`rut_preanotaciones_summary.csv`** — metricas de cobertura sin valores PII. **Este si va a git.**
"""))

cells.append(code("""# JSONL compacto
with PREANOT_JSONL.open('w', encoding='utf-8') as f:
    for _, row in preanot.iterrows():
        obj = {
            'md5':      row['md5'],
            'filename': row['filename'],
            'folder':   row['folder'],
            'doc_type': 'RUT',
            'entities': {ent: row[ent] if not pd.isna(row[ent]) else None for ent in entidades},
            'source':   'LFs_regex_v1',
            'requires_human_review': True,
        }
        f.write(json.dumps(obj, ensure_ascii=False) + '\\n')

print(f'Escrito: {PREANOT_JSONL}')
print(f'  {len(preanot)} lineas JSON')

# Summary CSV (sin valores PII — solo conteos y cobertura)
cob_df.to_csv(PREANOT_SUMMARY, index=False)
print(f'Escrito: {PREANOT_SUMMARY}')
print()
print('=== SUMMARY CSV (commiteable) ===')
print(cob_df.to_string(index=False))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 10. RESUMEN Y SIGUIENTE PASO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Resumen + siguiente paso

### Lo que produjo este notebook

1. **216 docs RUT** con pre-anotaciones automaticas de 6 entidades
2. **Archivo Label Studio** listo para import (correccion humana)
3. **JSONL compacto** para streaming durante entrenamiento
4. **CSV de cobertura** commiteable como evidencia en el informe final

### Siguiente paso inmediato (§2.2)

1. **Importar `rut_preanotaciones_labelstudio.json`** en Label Studio (UI o API):
   ```bash
   curl -X POST -H "Authorization: Token TU_TOKEN" \\
        -F "file=@data/processed/rut_preanotaciones_labelstudio.json" \\
        http://localhost:8080/api/projects/{ID}/import
   ```
2. **Definir esquema de labeling** — 6 entidades con colores distintos (nit, razon_social, regimen, direccion, municipio, representante_legal).
3. **Revision humana** — aceptar/corregir cada pre-anotacion. Estimado ~10 min/doc × 216 docs = **~36 horas** de trabajo humano (vs ~72 horas sin pre-anotaciones).
4. **Medir Cohen's Kappa** — doble anotacion sobre muestra de 20 docs para asegurar consistencia ≥ 0.85.

### Despues de la revision humana

Con los RUT anotados, se pueden:
- Entrenar los 3 candidatos de Clasificacion (§3.0 del plan) — RUT es una clase mas
- Entrenar los 3 candidatos de NER (§3.1) con los 216 RUT como primer dataset
- Validar que la pipeline completa funciona antes de escalar a Cedula/Poliza/CC

### Fuentes

- Ratner et al., "Snorkel: Rapid Training Data Creation with Weak Supervision", VLDB 2018: https://arxiv.org/abs/1711.10160
- Label Studio Predictions: https://labelstud.io/guide/predictions
- LFs implementadas en `src/preprocessing/pipeline.py` `extraer_entidades_rut()`
"""))


# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out = Path(__file__).parent / '06_preanotaciones_rut.ipynb'
nbf.write(nb, out)
print(f'Notebook generado: {out}')
md_count = sum(1 for c in cells if c.cell_type == 'markdown')
code_count = sum(1 for c in cells if c.cell_type == 'code')
print(f'  Celdas: {len(cells)} ({md_count} markdown + {code_count} code)')
