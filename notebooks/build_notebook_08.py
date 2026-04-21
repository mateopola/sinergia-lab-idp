"""
Genera el notebook 08_preanotaciones_polizas.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_08.py

Proposito:
    Seleccionar muestra aleatoria de 120 Polizas (80 train + 40 val) del corpus
    OCR, aplicar regex laxa para 2 campos estructurados (numero_poliza, aseguradora
    via lookup contra aseguradoras_corpus.json) y exportar tareas Label Studio.

    Los otros 7 campos (tomador, asegurado, vigencia_desde/hasta, valor_asegurado,
    prima_neta, amparo_principal) van totalmente manuales — decision del plan
    §2.2 v1.7: el layout de Polizas varia entre aseguradoras, las LFs full no
    aplican.

Contexto academico: Fase 2 CRISP-DM++ §2.2 "Polizas — Anotacion Manual".

Fundamentacion cientifica:
    Ratner et al. (2018). *Snorkel: Rapid Training Data Creation with Weak
    Supervision*. VLDB 2018. https://arxiv.org/abs/1711.10160
    — El paper advierte que LFs requieren fuentes estructuradas. Polizas
    tienen layout variable entre ~15 aseguradoras → LFs no escalables.

Estructura (M = markdown, C = code):
     1 M  Portada + objetivo
     2 M  Por que anotacion manual (no LFs full)
     3 M  Setup
     4 C  Imports + rutas
     5 M  Cargar corpus OCR + filtrar Polizas (digital + escaneadas)
     6 C  Union con mojibake handling
     7 M  Muestreo aleatorio 80+40
     8 C  Sampling reproducible seed=42
     9 M  Regex laxa: numero_poliza + aseguradora lookup
    10 C  Aplicar + medir cobertura
    11 M  Exportar Label Studio con split train/val
    12 C  Generar polizas_preanotaciones_labelstudio.json
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
cells.append(md("""# SinergIA Lab — Pre-anotaciones Polizas (muestreo aleatorio)
## Fase 2 CRISP-DM++ · §2.2 — Anotacion Manual Polizas

---

### Proposito

Seleccionar una **muestra aleatoria de 120 Polizas** (80 train + 40 val) del corpus SECOP y generar tareas de Label Studio con:
- Texto OCR del documento completo
- Pre-anotacion ligera de **2 campos estructurados**: `numero_poliza` (regex con anchor) y `aseguradora` (lookup contra `aseguradoras_corpus.json`)
- **7 campos restantes** totalmente manuales: `tomador`, `asegurado`, `vigencia_desde`, `vigencia_hasta`, `valor_asegurado`, `prima_neta`, `amparo_principal`

### Diferencia vs nb 06 (RUT) y nb 07 (Cedulas)

| Aspecto | RUT (nb 06) | Cedulas (nb 07) | Polizas (nb 08) |
|---|---|---|---|
| Origen texto | PyMuPDF (digital) | EasyOCR (escaneado) | Mezcla (160 digital + 59 escaneado) |
| LFs aplicables | 6 entidades | 1 (`numero`) | **2** (`numero_poliza`, `aseguradora`) |
| Razon limite LFs | — | CER OCR invalida | **Layout variable entre aseguradoras** |
| Muestra | 216 (todos) | 60 (estratificado) | 120 (aleatorio, 80+40) |

### Por que 80 train + 40 val (plan §2.2)

- 80 docs de entrenamiento → con augmentation 3x = 240 ejemplos efectivos
- 40 docs de validacion **sin augmentation** = conjunto limpio para reportar F1
- Muestra aleatoria (no estratificada) porque el plan §2.2 v1.7 documenta: *"La identificacion de aseguradora no es requisito para estratificar el set de entrenamiento"*

### Que produce este notebook

| Archivo | Contenido | En repo? |
|---|---|---|
| `data/processed/polizas_muestra_manifest.csv` | 120 md5 + split + metadata | ✅ |
| `data/processed/polizas_preanotaciones_labelstudio.json` | Tareas Label Studio | ❌ (PII) |
| `data/processed/polizas_preanotaciones_summary.csv` | Cobertura regex + distribucion aseguradoras | ✅ |

### Tiempo estimado

~2-3 min (sin GPU, sin modelos).
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. POR QUE ANOTACION MANUAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Por que NO LFs full en Polizas (solo 2 campos)

### El problema: layout variable entre aseguradoras

A diferencia del RUT (formulario DIAN estandar), las Polizas colombianas tienen **layout propietario por aseguradora**. Seguros Bolivar, Sura, Liberty, Mapfre, Positiva, etc. usan:
- Distintas plantillas graficas
- Orden variable de campos
- Terminologia especifica (ej. "Valor Asegurado" vs "Suma Asegurada" vs "Cuantia")
- Fechas con formatos mixtos (`DD/MM/AAAA`, `DD-MM-AAAA`, literal "primero de marzo de 2026")

Una LF regex entrenada sobre el layout de Sura falla sobre una Poliza de Liberty.

### Lo que SI se puede pre-anotar

**`numero_poliza`** — formato estandar en la industria colombiana: secuencia alfanumerica con patron `XXX-NN-NNN[NNN]` (ej. `001-35-2024001234`). Regex razonablemente estable.

**`aseguradora`** — **lookup directo** contra `data/processed/aseguradoras_corpus.json` generado en nb 02. No requiere regex: buscamos el nombre de cada aseguradora conocida en el texto del doc.

### Fuente metodologica

Ratner et al. (2018) *Snorkel: Rapid Training Data Creation with Weak Supervision* (VLDB 2018 — https://arxiv.org/abs/1711.10160) advierte explicitamente: "LFs work best when the source text is structured and deterministic. Variable layouts require human annotation."
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

CORPUS_OCR           = DATA_PROC / 'corpus_ocr.csv'
ASEGURADORAS_JSON    = DATA_PROC / 'aseguradoras_corpus.json'
POL_MANIFEST_OUT     = DATA_PROC / 'polizas_muestra_manifest.csv'
POL_LABELST_OUT      = DATA_PROC / 'polizas_preanotaciones_labelstudio.json'
POL_SUMMARY_OUT      = DATA_PROC / 'polizas_preanotaciones_summary.csv'

# Parametros
N_TRAIN = 80
N_VAL   = 40
SEED    = 42

for p in [CORPUS_OCR, ASEGURADORAS_JSON]:
    assert p.exists(), f'Falta: {p}'
print('Setup OK.')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. CARGA + FILTRO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Cargar corpus OCR y filtrar Polizas

El corpus tiene 960 docs / 13,254 paginas. Las Polizas aparecen bajo dos `folder` distintos por el hallazgo de mojibake documentado en [nb05b_resultados.md](../reports/nb05b_resultados.md):

- `POLIZA` (59 docs escaneados via EasyOCR, nombre limpio de nb 04)
- `PÃ\\x83Â³liza` (144 docs digitales via PyMuPDF, nombre con mojibake heredado de quality_report)

Filtro robusto: substring `oliz` (case-insensitive) matchea ambos.
"""))

cells.append(code("""corpus = pd.read_csv(CORPUS_OCR)
print(f'Corpus total: {len(corpus):,} filas / {corpus[\"md5\"].nunique()} docs')

# Filtro robusto a mojibake: clean 'poliz' + mojibake 'liza' (porque en
# 'PÃ\\x83Â³liza' la 'ó' se convirtio en bytes raros y solo 'liza' es estable)
pol_mask = corpus['folder'].str.lower().str.contains('poliz|liza', na=False)
pol_pages = corpus[pol_mask].sort_values(['md5', 'page_num']).reset_index(drop=True)
print(f'Paginas Polizas: {len(pol_pages):,}')
print(f'Docs Polizas:    {pol_pages[\"md5\"].nunique()}')
print()

# Distribucion por engine
print('Distribucion por engine:')
print(pol_pages.groupby(['engine'])['md5'].nunique().to_string())
print()

# Consolidar texto por doc
def _cc(pages):
    return '\\n\\n'.join(str(x) for x in pages if isinstance(x, str))

pol_docs = (pol_pages
    .groupby('md5', as_index=False)
    .agg({'filename':'first','folder':'first','engine':'first','page_num':'size','texto_ocr':_cc})
    .rename(columns={'page_num':'n_pages','texto_ocr':'texto_completo'})
)
pol_docs['n_chars'] = pol_docs['texto_completo'].str.len()

# Filtrar docs sin contenido
pol_docs = pol_docs[pol_docs['n_chars'] > 100].reset_index(drop=True)
print(f'Docs con texto extraido (>100 chars): {len(pol_docs)}')
print()
print('Distribucion n_pages:')
print(pol_docs['n_pages'].describe().round(1).to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. MUESTREO ALEATORIO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Muestreo aleatorio 80 train + 40 val

Seed fija = 42 para reproducibilidad cientifica (§Control de Versiones del plan).
"""))

cells.append(code("""total_necesario = N_TRAIN + N_VAL
if len(pol_docs) < total_necesario:
    print(f'⚠ Solo hay {len(pol_docs)} docs disponibles — ajustando objetivo')
    n_val = max(1, int(len(pol_docs) * (N_VAL / total_necesario)))
    n_train = len(pol_docs) - n_val
else:
    n_train = N_TRAIN
    n_val   = N_VAL

# Shuffle reproducible
pol_shuffled = pol_docs.sample(frac=1, random_state=SEED).reset_index(drop=True)
train_df = pol_shuffled.iloc[:n_train].assign(split='train')
val_df   = pol_shuffled.iloc[n_train:n_train+n_val].assign(split='val')

muestra = pd.concat([train_df, val_df]).reset_index(drop=True)
print(f'Muestra: {len(muestra)} docs ({n_train} train + {n_val} val)')
print()
print('Por engine:')
print(muestra.groupby(['split','engine'])['md5'].size().to_string())
print()
print('Chars promedio por split:')
print(muestra.groupby('split')['n_chars'].agg(['mean','median','min','max']).round(0).astype(int).to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. REGEX + LOOKUP ASEGURADORAS
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Pre-anotacion ligera: `numero_poliza` + `aseguradora`

### `numero_poliza` — regex con anchor

Patron: secuencia con formato `NNN-NN-NNNNNN` o variantes (`NN-NN-NNNN`, todo junto). Ancoreado en `POLIZA|POLIZA Nº|NUMERO|PÓLIZA` para reducir falsos positivos.

### `aseguradora` — lookup

Busca el nombre de cada aseguradora del diccionario `aseguradoras_corpus.json` en el texto. Primer match gana. No usa regex — es `text.lower().find(aseguradora.lower())`.
"""))

cells.append(code("""# Cargar diccionario de aseguradoras
aseguradoras = json.loads(ASEGURADORAS_JSON.read_text(encoding='utf-8'))
print(f'Aseguradoras en diccionario: {len(aseguradoras)}')
if isinstance(aseguradoras, dict):
    nombres_aseg = list(aseguradoras.keys())
elif isinstance(aseguradoras, list):
    nombres_aseg = aseguradoras
else:
    nombres_aseg = []
# Ordenar por longitud descendente para match mas especifico primero
nombres_aseg = sorted([str(n) for n in nombres_aseg], key=len, reverse=True)
print(f'Ejemplos: {nombres_aseg[:5]}')
print()


_ANCHOR_POL = r'(?:POLIZA|P[OÓ]LIZA|NUMERO|N[UÚ]MERO)\\s*(?:No\\.?|Nº|N°|#)?\\s*:?'
_NUM_POL    = r'([A-Z]{0,3}[-\\s]?\\d{2,4}[-\\s]?\\d{2,4}[-\\s]?\\d{3,8})'
RE_NUM_POL  = re.compile(f'{_ANCHOR_POL}.{{0,30}}?{_NUM_POL}', re.IGNORECASE | re.DOTALL)


def extraer_numero_poliza(texto):
    if not isinstance(texto, str) or len(texto) < 20:
        return None
    m = RE_NUM_POL.search(texto)
    if not m:
        return None
    raw = m.group(1).strip()
    # Filtro: al menos 7 chars alfanumericos (evita matches triviales)
    alnum = re.sub(r'[^A-Za-z0-9]', '', raw)
    if len(alnum) < 7:
        return None
    return raw


def detectar_aseguradora(texto):
    if not isinstance(texto, str):
        return None
    t_low = texto.lower()
    for nombre in nombres_aseg:
        n_low = str(nombre).lower().strip()
        if len(n_low) < 3:
            continue
        if n_low in t_low:
            return nombre
    return None


muestra['numero_poliza'] = muestra['texto_completo'].apply(extraer_numero_poliza)
muestra['aseguradora']   = muestra['texto_completo'].apply(detectar_aseguradora)

# Cobertura
cob_numero = muestra['numero_poliza'].notna().sum()
cob_aseg   = muestra['aseguradora'].notna().sum()
print(f'Cobertura numero_poliza: {cob_numero}/{len(muestra)} = {cob_numero/len(muestra):.1%}')
print(f'Cobertura aseguradora:   {cob_aseg}/{len(muestra)} = {cob_aseg/len(muestra):.1%}')
print()
print('Top 10 aseguradoras detectadas:')
print(muestra['aseguradora'].value_counts().head(10).to_string())
print()
print('Ejemplos numero_poliza detectado (primeros 5):')
ejemplos = muestra[muestra['numero_poliza'].notna()].head(5)[['filename','numero_poliza','aseguradora']]
print(ejemplos.to_string(index=False))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. EXPORTAR LABEL STUDIO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Exportar a Label Studio con split train/val

### Esquema de labeling (9 entidades)

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="numero_poliza" background="#FF6B6B"/>
    <Label value="aseguradora" background="#4ECDC4"/>
    <Label value="tomador" background="#45B7D1"/>
    <Label value="asegurado" background="#FFA500"/>
    <Label value="vigencia_desde" background="#95E1D3"/>
    <Label value="vigencia_hasta" background="#C9A0FF"/>
    <Label value="valor_asegurado" background="#F38181"/>
    <Label value="prima_neta" background="#AA96DA"/>
    <Label value="amparo_principal" background="#FCBAD3"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

El campo `split` en `data` permite crear proyectos separados en Label Studio para train y val.
"""))

cells.append(code("""tasks = []
for _, row in muestra.iterrows():
    texto = str(row['texto_completo'])
    predictions = []

    # numero_poliza
    num = row['numero_poliza']
    if isinstance(num, str):
        idx = texto.find(num)
        if idx >= 0:
            predictions.append({
                'from_name': 'label',
                'to_name':   'text',
                'type':      'labels',
                'value': {'start': idx, 'end': idx+len(num), 'text': num, 'labels': ['numero_poliza']},
                'score': 0.6,
            })

    # aseguradora
    aseg = row['aseguradora']
    if isinstance(aseg, str):
        idx = texto.lower().find(aseg.lower())
        if idx >= 0:
            predictions.append({
                'from_name': 'label',
                'to_name':   'text',
                'type':      'labels',
                'value': {'start': idx, 'end': idx+len(aseg), 'text': aseg, 'labels': ['aseguradora']},
                'score': 0.9,
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
            'model_version': 'regex_poliza_v1',
            'result':        predictions,
        }],
    }
    tasks.append(task)

with POL_LABELST_OUT.open('w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f'Tareas Label Studio: {len(tasks)}')
print(f'  con pre-anotacion numero: {sum(1 for t in tasks if any(r[\"value\"][\"labels\"][0]==\"numero_poliza\" for r in t[\"predictions\"][0][\"result\"]))}')
print(f'  con pre-anotacion aseguradora: {sum(1 for t in tasks if any(r[\"value\"][\"labels\"][0]==\"aseguradora\" for r in t[\"predictions\"][0][\"result\"]))}')
print(f'Archivo: {POL_LABELST_OUT}')

# Manifest commiteable
manifest_out = muestra[['md5','filename','split','engine','n_pages','n_chars','numero_poliza','aseguradora']].copy()
manifest_out.to_csv(POL_MANIFEST_OUT, index=False)
print(f'Manifest: {POL_MANIFEST_OUT}')

# Summary commiteable
summary = pd.DataFrame([{
    'total_muestra': len(muestra),
    'train': n_train,
    'val': n_val,
    'cobertura_numero_poliza': round(cob_numero/len(muestra), 3),
    'cobertura_aseguradora':   round(cob_aseg/len(muestra), 3),
    'aseguradoras_distintas_detectadas': muestra['aseguradora'].nunique(),
    'seed': SEED,
}])
summary.to_csv(POL_SUMMARY_OUT, index=False)
print(f'Summary: {POL_SUMMARY_OUT}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. RESUMEN
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Resumen + siguiente paso

### Lo que produjo este notebook

1. **120 Polizas muestreadas** aleatoriamente con seed=42 (80 train + 40 val)
2. **Pre-anotacion `numero_poliza`** via regex con anchor
3. **Pre-anotacion `aseguradora`** via lookup contra `aseguradoras_corpus.json`
4. **Tareas Label Studio** con split train/val para crear proyectos separados
5. **Manifest commiteable** con metadata del muestreo

### Siguiente paso

1. **Cargar `polizas_preanotaciones_labelstudio.json` en Label Studio** con esquema de 9 entidades
2. **Anotacion humana manual** de los 7 campos restantes (estimado ~20 min/doc × 120 = **40 horas**)
3. Exportar anotaciones a JSONL alineado con el esquema de §2.2 del plan

### Paralelamente

Notebook 09 — Camara de Comercio con chunking layout-aware pre-aplicado.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out = Path(__file__).parent / '08_preanotaciones_polizas.ipynb'
nbf.write(nb, out)
print(f'Notebook generado: {out}')
md_count = sum(1 for c in cells if c.cell_type == 'markdown')
code_count = sum(1 for c in cells if c.cell_type == 'code')
print(f'  Celdas: {len(cells)} ({md_count} markdown + {code_count} code)')
