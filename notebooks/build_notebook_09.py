"""
Genera el notebook 09_preanotaciones_camara_comercio.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_09.py

Proposito:
    Seleccionar muestra aleatoria de 120 Camaras de Comercio (80 train + 40 val),
    aplicar regex laxa para campos estructurados compartidos con RUT (`nit`,
    `razon_social`, `matricula`) y exportar tareas Label Studio con chunking
    layout-aware informativo.

    Los otros 7 campos (tipo_sociedad, fecha_renovacion, domicilio, objeto_social,
    representante_legal, activos, capital_social) van manuales — decision del
    plan §2.2.

Contexto academico: Fase 2 CRISP-DM++ §2.2 "Camara de Comercio — Anotacion
Manual Reducida". El plan §2.3 define chunking layout-aware con HoughLinesP
para dividir CC en 4 bloques canonicos (datos_basicos, representantes_legales,
establecimientos, actividades_economicas).

Fundamentacion cientifica:
    - Ratner et al. (2018). Snorkel. VLDB 2018.
      https://arxiv.org/abs/1711.10160
    - La decision de limitar a 80 docs (reducido de 200 originales) esta en
      §2.2 del plan — minimo viable para fine-tuning con augmentation 3x.

Estructura (M = markdown, C = code):
     1 M  Portada + objetivo
     2 M  Por que CC es distinto (layout consistente + multipagina denso)
     3 M  Setup
     4 C  Imports + rutas
     5 M  Cargar corpus OCR + filtrar CC (mojibake handling)
     6 C  Union con mojibake handling
     7 M  Muestreo aleatorio 80+40
     8 C  Sampling reproducible seed=42
     9 M  Regex laxa: nit + matricula + razon_social
    10 C  Aplicar + medir cobertura
    11 M  Exportar Label Studio
    12 C  Generar camara_comercio_preanotaciones_labelstudio.json
    13 M  Resumen + siguiente paso
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
cells.append(md("""# SinergIA Lab — Pre-anotaciones Camara de Comercio
## Fase 2 CRISP-DM++ · §2.2 — Anotacion Manual Reducida

---

### Proposito

Seleccionar **120 certificados de Camara de Comercio** (80 train + 40 val) del corpus SECOP y generar tareas de Label Studio con:
- Texto OCR del documento completo
- Pre-anotacion de **3 campos estructurados** compartidos con RUT: `nit`, `matricula`, `razon_social`
- **7 campos restantes** manuales: `tipo_sociedad`, `fecha_renovacion`, `domicilio`, `objeto_social`, `representante_legal`, `activos`, `capital_social`

### Diferencia vs Polizas (nb 08)

CC es **mas favorable** para pre-anotacion que Polizas porque:
1. **Layout mas consistente entre camaras** — solo varia logo + header
2. **Campos estructurados compartidos con RUT** — nit, razon social con formas juridicas conocidas
3. **Densidad textual alta** (~2,500 chars/pag × 11 paginas promedio) — mas informacion para los regex

### Entidades objetivo (10 campos del plan §2.2)

| Campo | Pre-anotable? | Estrategia |
|---|---|---|
| `nit` | ✅ | Regex compartido con RUT |
| `razon_social` | ✅ | Regex MAYUSCULAS + forma juridica |
| `matricula` | ✅ | Regex `MATRICULA\\s*N[°o.]?\\s*\\d+` |
| `tipo_sociedad` | — | Manual (vocabulario pequeno: SAS, LTDA, S.A, E.U) |
| `fecha_renovacion` | — | Manual (fechas con muchos formatos) |
| `domicilio` | — | Manual (direccion colombiana) |
| `objeto_social` | — | Manual (texto libre extenso) |
| `representante_legal` | — | Manual |
| `activos` | — | Manual (monto) |
| `capital_social` | — | Manual (monto) |

### Que produce este notebook

| Archivo | Contenido | En repo? |
|---|---|---|
| `data/processed/camara_comercio_muestra_manifest.csv` | 120 md5 + split + metadata | ✅ |
| `data/processed/camara_comercio_preanotaciones_labelstudio.json` | Tareas LS | ❌ PII |
| `data/processed/camara_comercio_preanotaciones_summary.csv` | Cobertura por entidad | ✅ |

### Tiempo estimado

~2-3 min (sin GPU, sin modelos).
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. POR QUE CC ES DISTINTO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Por que CC es favorable para pre-anotacion

### Layout consistente entre camaras

Las 30+ camaras de comercio de Colombia (CCB, CCC, CCM, etc.) usan **el mismo marco normativo** (Decreto 2150/1995, Circular Externa 02/2007) y por tanto certificados con **estructura reglamentada**:

- Encabezado: NIT, razon social, matricula mercantil
- Seccion de datos basicos: fecha constitucion, domicilio, objeto social
- Seccion de representacion legal: nombre, identificacion, facultades
- Seccion financiera: activos, capital social

Lo unico que varia es el logo de cada camara.

### Ventaja vs Polizas

En Polizas, el layout cambia por aseguradora comercial (Mundial vs Sura vs AXA). Cada empresa privada disena su plantilla. En CC, la estructura es **regulatoria**, no comercial.

### Ventaja vs Cedula

En Cedula, el 93% del corpus es escaneado con OCR ruidoso (CER 0.28). En CC, la mezcla es **92% digital / 8% escaneado** — PyMuPDF extrae texto limpio en la mayoria.

### Chunking layout-aware

El plan §2.3 define chunking layout-aware con `cv2.HoughLinesP` para CC:
- Detecta separadores horizontales → identifica fronteras entre secciones logicas
- Segmenta en 4 bloques canonicos: `[datos_basicos, representantes_legales, establecimientos, actividades_economicas]`

Este notebook **no aplica el chunking** (eso va en §2.3 sobre el corpus anotado). Aqui solo preparamos el dataset de entrenamiento.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 3. SETUP
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Setup — imports y rutas"""))

cells.append(code("""import json
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import numpy as np

PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_PROC = PROJECT_ROOT / 'data' / 'processed'
DATA_GOLD = PROJECT_ROOT / 'data' / 'gold'

CORPUS_OCR        = DATA_PROC / 'corpus_ocr.csv'
CC_MANIFEST_OUT   = DATA_PROC / 'camara_comercio_muestra_manifest.csv'
CC_LABELST_OUT    = DATA_PROC / 'camara_comercio_preanotaciones_labelstudio.json'
CC_SUMMARY_OUT    = DATA_PROC / 'camara_comercio_preanotaciones_summary.csv'

N_TRAIN = 80
N_VAL   = 40
SEED    = 42

assert CORPUS_OCR.exists(), f'Falta: {CORPUS_OCR}'
print('Setup OK.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGA + FILTRO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Cargar corpus OCR y filtrar CC

Dos `folder` por mojibake:
- `CAMARA DE CIO` (16 docs escaneados de nb 04, nombre limpio)
- `CÃ\\x83Â¡mara de Comercio` (183 docs digitales de nb 05b/PyMuPDF)

Filtro robusto por substring: `amara` matchea clean, `mara` matchea mojibake.
"""))

cells.append(code("""corpus = pd.read_csv(CORPUS_OCR)
print(f'Corpus total: {len(corpus):,} filas / {corpus[\"md5\"].nunique()} docs')

# Filtro robusto: 'amara' (clean) + 'Â¡mara' (mojibake exclusivo de camara)
cc_mask = corpus['folder'].str.lower().str.contains('amara|mara de com', na=False)
cc_pages = corpus[cc_mask].sort_values(['md5','page_num']).reset_index(drop=True)
print(f'Paginas CC: {len(cc_pages):,}')
print(f'Docs CC:    {cc_pages[\"md5\"].nunique()}')
print()
print('Por engine:')
print(cc_pages.groupby('engine')['md5'].nunique().to_string())
print()

def _cc(pages):
    return '\\n\\n'.join(str(x) for x in pages if isinstance(x, str))

cc_docs = (cc_pages
    .groupby('md5', as_index=False)
    .agg({'filename':'first','folder':'first','engine':'first','page_num':'size','texto_ocr':_cc})
    .rename(columns={'page_num':'n_pages','texto_ocr':'texto_completo'})
)
cc_docs['n_chars'] = cc_docs['texto_completo'].str.len()
cc_docs = cc_docs[cc_docs['n_chars'] > 100].reset_index(drop=True)

print(f'Docs CC con texto >100 chars: {len(cc_docs)}')
print()
print('Distribucion n_pages (CC suele ser multipagina):')
print(cc_docs['n_pages'].describe().round(1).to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. MUESTREO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Muestreo aleatorio 80 train + 40 val (seed=42)"""))

cells.append(code("""total_necesario = N_TRAIN + N_VAL
if len(cc_docs) < total_necesario:
    print(f'⚠ Solo hay {len(cc_docs)} docs disponibles — ajustando')
    n_val = max(1, int(len(cc_docs) * (N_VAL / total_necesario)))
    n_train = len(cc_docs) - n_val
else:
    n_train = N_TRAIN
    n_val   = N_VAL

cc_shuffled = cc_docs.sample(frac=1, random_state=SEED).reset_index(drop=True)
train_df = cc_shuffled.iloc[:n_train].assign(split='train')
val_df   = cc_shuffled.iloc[n_train:n_train+n_val].assign(split='val')
muestra  = pd.concat([train_df, val_df]).reset_index(drop=True)

print(f'Muestra: {len(muestra)} docs ({n_train} train + {n_val} val)')
print()
print('Por engine:')
print(muestra.groupby(['split','engine'])['md5'].size().to_string())
print()
print('Chars y paginas por split:')
print(muestra.groupby('split').agg(
    n_docs=('md5','size'),
    chars_medio=('n_chars', lambda s: int(s.mean())),
    paginas_medio=('n_pages', lambda s: round(s.mean(),1)),
).to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. REGEX PRE-ANOTACIONES
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Pre-anotacion de 3 campos: `nit`, `matricula`, `razon_social`

Los tres son los campos mas estructurados del certificado CC. Los otros 7 requieren lectura humana.

### `nit` — reutilizamos el regex del RUT

El mismo patron funciona: formato continuo `860518862-7` o cajas DIAN.

### `matricula` — patron regulatorio

`MATRICULA` (o variantes con tilde) seguido de `N°` + digitos. Ej: `MATRICULA N° 00502789`.

### `razon_social` — MAYUSCULAS + forma juridica

Mismo patron que RUT: linea en MAYUSCULAS con sufijo `LTDA|SAS|S.A|E.U|EIRL`.
"""))

cells.append(code("""# Reutilizar LFs de pipeline.py para nit y razon_social
sys.path.insert(0, str(PROJECT_ROOT.resolve()))
from src.preprocessing.pipeline import extraer_entidades_rut


# Regex propia para matricula (especifico de CC)
RE_MATRICULA = re.compile(
    r'MATR[IÍ]CULA\\s*(?:MERCANTIL)?\\s*(?:N[°o.]|No\\.?|N[úu]mero)?\\s*:?\\s*(\\d{5,10})',
    re.IGNORECASE,
)


def extraer_matricula(texto):
    if not isinstance(texto, str) or len(texto) < 20:
        return None
    m = RE_MATRICULA.search(texto)
    return m.group(1) if m else None


# Aplicar
def extraer_cc(texto):
    base = extraer_entidades_rut(texto)  # nit + razon_social + otros 4 no usados
    return {
        'nit':          base.get('nit'),
        'razon_social': base.get('razon_social'),
        'matricula':    extraer_matricula(texto),
    }


resultados = muestra['texto_completo'].apply(extraer_cc)
muestra['nit']          = resultados.apply(lambda d: d['nit'])
muestra['razon_social'] = resultados.apply(lambda d: d['razon_social'])
muestra['matricula']    = resultados.apply(lambda d: d['matricula'])

cob_nit    = muestra['nit'].notna().sum()
cob_rs     = muestra['razon_social'].notna().sum()
cob_matric = muestra['matricula'].notna().sum()

print(f'Cobertura nit:          {cob_nit}/{len(muestra)} = {cob_nit/len(muestra):.1%}')
print(f'Cobertura razon_social: {cob_rs}/{len(muestra)} = {cob_rs/len(muestra):.1%}')
print(f'Cobertura matricula:    {cob_matric}/{len(muestra)} = {cob_matric/len(muestra):.1%}')
print()

# Ejemplos
print('Ejemplos detectados (primeros 5):')
print(muestra[muestra['nit'].notna()].head(5)[['filename','nit','matricula','razon_social']].to_string(index=False))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. EXPORTAR LABEL STUDIO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Exportar Label Studio con 10 entidades

### Esquema XML (crear en la UI de Label Studio)

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="nit" background="#FF6B6B"/>
    <Label value="razon_social" background="#4ECDC4"/>
    <Label value="matricula" background="#45B7D1"/>
    <Label value="tipo_sociedad" background="#FFA500"/>
    <Label value="fecha_renovacion" background="#95E1D3"/>
    <Label value="domicilio" background="#C9A0FF"/>
    <Label value="objeto_social" background="#F38181"/>
    <Label value="representante_legal" background="#AA96DA"/>
    <Label value="activos" background="#FCBAD3"/>
    <Label value="capital_social" background="#B5EAD7"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```
"""))

cells.append(code("""tasks = []
for _, row in muestra.iterrows():
    texto = str(row['texto_completo'])
    predictions = []

    for campo, label in [('nit', 'nit'), ('razon_social', 'razon_social'), ('matricula', 'matricula')]:
        val = row[campo]
        if not isinstance(val, str) or not val.strip():
            continue
        idx = texto.find(val)
        if idx < 0:
            idx = texto.lower().find(val.lower())
        if idx < 0:
            continue
        predictions.append({
            'from_name': 'label',
            'to_name':   'text',
            'type':      'labels',
            'value': {'start': idx, 'end': idx+len(val), 'text': val, 'labels': [label]},
            'score': 0.7,
        })

    task = {
        'data': {
            'text':     texto,
            'md5':      row['md5'],
            'filename': row['filename'],
            'split':    row['split'],
            'engine':   row['engine'],
            'n_pages':  int(row['n_pages']),
        },
        'predictions': [{
            'model_version': 'regex_cc_v1',
            'result':        predictions,
        }],
    }
    tasks.append(task)

with CC_LABELST_OUT.open('w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f'Tareas Label Studio: {len(tasks)}')
total_preds = sum(len(t['predictions'][0]['result']) for t in tasks)
print(f'Pre-anotaciones totales: {total_preds} (promedio {total_preds/len(tasks):.2f} por doc)')
print(f'Archivo: {CC_LABELST_OUT}')

# Manifest commiteable
manifest_out = muestra[['md5','filename','split','engine','n_pages','n_chars','nit','matricula','razon_social']].copy()
manifest_out.to_csv(CC_MANIFEST_OUT, index=False)
print(f'Manifest: {CC_MANIFEST_OUT}')

# Summary commiteable
summary = pd.DataFrame([{
    'total_muestra':           len(muestra),
    'train':                   n_train,
    'val':                     n_val,
    'cobertura_nit':           round(cob_nit/len(muestra), 3),
    'cobertura_razon_social':  round(cob_rs/len(muestra), 3),
    'cobertura_matricula':     round(cob_matric/len(muestra), 3),
    'seed':                    SEED,
}])
summary.to_csv(CC_SUMMARY_OUT, index=False)
print(f'Summary: {CC_SUMMARY_OUT}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Resumen + siguiente paso

### Lo que produjo este notebook

1. **120 CC muestreadas** (80 train + 40 val, seed=42)
2. **3 entidades pre-anotadas** (`nit`, `razon_social`, `matricula`) reutilizando LFs del RUT
3. **Tareas Label Studio** con split train/val
4. **Manifest commiteable** con metadata del muestreo

### Siguiente paso

1. **Cargar en Label Studio** con esquema de 10 entidades
2. **Anotacion humana** (estimado ~25 min/doc × 120 = **50 horas** — mayor que Polizas por densidad textual y numero de campos)
3. Exportar anotaciones → en §2.3 del plan aplicar chunking layout-aware con `cv2.HoughLinesP` para segmentar cada CC en 4 bloques canonicos

### Al cerrar los 4 notebooks (06, 07, 08, 09)

Tenemos el pipeline completo de Fase 2.2:
- 216 RUT pre-anotados (6 entidades)
- 60 Cedulas muestreadas (1 entidad pre-anotada, 7 manuales)
- 120 Polizas muestreadas (2 pre, 7 manuales)
- 120 CC muestreadas (3 pre, 7 manuales)

**Total: 516 docs listos para revision humana en Label Studio.**
"""))


# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out = Path(__file__).parent / '09_preanotaciones_camara_comercio.ipynb'
nbf.write(nb, out)
print(f'Notebook generado: {out}')
md_count = sum(1 for c in cells if c.cell_type == 'markdown')
code_count = sum(1 for c in cells if c.cell_type == 'code')
print(f'  Celdas: {len(cells)} ({md_count} markdown + {code_count} code)')
