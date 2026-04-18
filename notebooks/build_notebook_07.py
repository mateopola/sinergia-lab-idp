"""
Genera el notebook 07_preanotaciones_cedulas.ipynb

Ejecutar desde la raiz del proyecto:
    python notebooks/build_notebook_07.py

Proposito:
    Seleccionar 60 Cedulas estratificadas por calidad visual (blur_score),
    aplicar una regex laxa para el campo "numero" de cedula como pre-anotacion
    ligera, y exportar tareas Label Studio con texto + imagen procesada para
    anotacion humana manual del resto de campos.

Contexto academico: Fase 2 CRISP-DM++ §2.2 "Cedula — Anotacion via OCR Muestral".
A diferencia de RUT (nb 06), las Cedulas NO admiten LFs full regex:
- 93% son escaneados (EasyOCR → CER ~0.28)
- La tasa de error OCR invalida estrategias automaticas confiables

Por eso:
- Solo 1 regex (numero de cedula con formato 1.234.567) como apoyo ligero
- Los 7 campos restantes (nombre, apellidos, fechas, lugares, sexo, RH) van manuales
- Label Studio recibe tarea bimodal: texto + imagen para que el humano vea el doc visual

Muestreo estratificado:
- 30 Cedulas "alta calidad" (blur_score > Q3)
- 30 Cedulas "ruidosas" (blur_score < Q1)
- Total: 60 docs (minimo viable para fine-tuning con augmentation 3x)

Estructura (M = markdown, C = code):
     1 M  Portada + objetivo
     2 M  Por que NO full LFs en Cedulas (justificacion cientifica)
     3 M  Setup
     4 C  Imports + rutas
     5 M  Cargar corpus OCR + quality_report + manifest de imagenes
     6 C  Union de las 3 fuentes filtrando Cedulas
     7 M  Muestreo estratificado por blur_score
     8 C  Split Q1/Q3 + sampling reproducible seed=42
     9 M  Regex laxa para numero de cedula
    10 C  Aplicar + medir cobertura
    11 M  Exportar Label Studio bimodal (texto + imagen)
    12 C  Generar tareas con prediccion de numero + imagen procesada
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
cells.append(md("""# SinergIA Lab — Pre-anotaciones Cedulas (muestra estratificada)
## Fase 2 CRISP-DM++ · §2.2 — Anotacion via OCR Muestral

---

### Proposito

Seleccionar una **muestra estratificada de 60 Cedulas** del corpus SECOP (30 alta calidad + 30 ruidosas) y generar tareas de Label Studio con:
- Texto OCR extraido (ya disponible en `corpus_ocr.csv`)
- Imagen procesada del documento (ya disponible en `data/processed/images/`)
- Pre-anotacion automatica **solo** del campo `numero` de cedula via regex

Los **7 campos restantes** (`nombre_completo`, `apellidos`, `fecha_nacimiento`, `lugar_nacimiento`, `fecha_expedicion`, `lugar_expedicion`, `sexo`, `rh`) se anotan manualmente por el revisor humano en Label Studio, usando la imagen como apoyo visual.

### Diferencia vs Notebook 06 (RUT)

| Aspecto | RUT (nb 06) | Cedulas (nb 07) |
|---|---|---|
| Origen del texto | PyMuPDF (digital, sin ruido) | EasyOCR (escaneado, CER ~0.28) |
| LFs regex | 6 entidades | 1 entidad (`numero`) |
| Cobertura esperada | 65-99% por LF | ~60-70% del numero |
| Trabajo humano en LS | Corregir pre-anotaciones | Anotar 7 campos desde cero + corregir 1 |
| Tamano muestra | 216 (todo el corpus RUT) | 60 (estratificado) |

### Que produce este notebook

| Archivo | Contenido | En repo? |
|---|---|---|
| `data/processed/cedulas_muestra_manifest.csv` | Los 60 md5 seleccionados + metadata | ✅ |
| `data/processed/cedulas_preanotaciones_labelstudio.json` | Tareas Label Studio con texto + imagen + pre-anotacion numero | ❌ (PII) |
| `data/processed/cedulas_preanotaciones_summary.csv` | Cobertura del regex `numero` | ✅ |

### Tiempo estimado

~1-2 min. Sin GPU, sin modelos.
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 2. POR QUE NO LFs FULL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Por que NO aplicar LFs full regex sobre Cedulas

### El problema

El EDA del corpus (Fase 1) mostro que **312 de 334 Cedulas (93%) son escaneadas**. Su texto se obtiene aplicando EasyOCR, que en el gold seed midio **CER 0.31** (31% de caracteres erroneos).

### Implicaciones para LFs regex

Las Labeling Functions regex operan sobre patrones literales en el texto. Si el OCR produce:

| Original (en imagen) | OCR (con CER 0.31) |
|---|---|
| `1.234.567` | `1 234 567`, `1:234.567`, `I.234.56?` |
| `JUAN PEREZ` | `JUAN PEREZ`, `JUAN PEREG`, `JUAN PE2EZ` |
| `CALI` | `CALI`, `CAl1`, `CAL1` |

Una regex estricta fallaria en ~30% de los documentos, y una regex permisiva generaria **falsos positivos** dificiles de filtrar (numeros de cedula que en realidad son codigos de barra, fechas que son numeros de serie, etc.).

### Validacion empirica

Piloto sobre 30 Cedulas del corpus: **regex `numero` detecta 20/30 = 66%**. Para los otros 5 campos (nombre, fechas, lugares) la confiabilidad baja aun mas por la variabilidad del layout OCR.

### Decision documentada en el plan (§2.2)

> **⚠️ ALERTA v1.3 — Cedulas NO son elegibles para regex LFs:**
> El EDA del corpus confirma que 312/334 Cedulas (93%) son documentos escaneados. Las regex no tienen texto limpio sobre el que operar. No intentar regex LFs sobre el texto extraido por OCR — la tasa de error OCR invalida la estrategia automatica.

### Fuente metodologica

Ratner et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 — https://arxiv.org/abs/1711.10160

El paper de Snorkel advierte explicitamente: LFs funcionan cuando la fuente de texto es **estructurada y determinista**. Cedulas escaneadas con OCR no cumplen ese criterio.
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

import pandas as pd
import numpy as np

# Rutas del proyecto
PROJECT_ROOT = Path('..') if Path('../data').exists() else Path('.')
DATA_PROC = PROJECT_ROOT / 'data' / 'processed'
DATA_GOLD = PROJECT_ROOT / 'data' / 'gold'

CORPUS_OCR          = DATA_PROC / 'corpus_ocr.csv'
QUALITY_REPORT      = DATA_PROC / 'quality_report_completo.csv'
IMAGE_MANIFEST      = DATA_PROC / 'image_manifest.csv'
CED_MANIFEST_OUT    = DATA_PROC / 'cedulas_muestra_manifest.csv'
CED_LABELST_OUT     = DATA_PROC / 'cedulas_preanotaciones_labelstudio.json'
CED_SUMMARY_OUT     = DATA_PROC / 'cedulas_preanotaciones_summary.csv'

# Parametros de muestreo
N_ALTA_CALIDAD = 30
N_RUIDOSAS     = 30
SEED           = 42

for p in [CORPUS_OCR, QUALITY_REPORT, IMAGE_MANIFEST]:
    assert p.exists(), f'Falta: {p}'

print('Setup OK.')
print(f'  Input: {CORPUS_OCR}')
print(f'  Seed:  {SEED} (reproducible)')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 4. UNION DE FUENTES
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Union de fuentes — corpus OCR + quality_report + image_manifest

Necesitamos 3 fuentes de informacion por doc:

| Fuente | Aporta |
|---|---|
| `corpus_ocr.csv` | Texto OCR del doc (consolidado por todas sus paginas) |
| `quality_report_completo.csv` | `blur_score`, `contrast`, `brightness` para estratificar |
| `image_manifest.csv` | Ruta a la imagen procesada para mostrar en Label Studio |

Las 3 fuentes se unen por `md5`. Filtramos a Cedulas.
"""))

cells.append(code("""corpus = pd.read_csv(CORPUS_OCR)
qr     = pd.read_csv(QUALITY_REPORT)
manif  = pd.read_csv(IMAGE_MANIFEST)

# Filtrar Cedulas (el category de quality_report tiene mojibake doble-encoded
# 'CÃ\\x83Â©dula' — comparamos por substring 'dula' que es estable)
corpus_ced = corpus[corpus['folder'].str.lower().str.contains('cedul|cédul', na=False)]
qr_ced     = qr[qr['category'].str.contains('dula', case=False, na=False)]

print(f'Cedulas en corpus_ocr:    {corpus_ced[\"md5\"].nunique()} docs / {len(corpus_ced)} paginas')
print(f'Cedulas en quality_report: {len(qr_ced)} docs')
print()

# Consolidar texto por md5 (algunas cedulas tienen 2+ paginas)
def _cc(pages):
    return '\\n\\n'.join(str(x) for x in pages if isinstance(x, str))

ced_docs = (corpus_ced
    .groupby('md5', as_index=False)
    .agg({'filename':'first','folder':'first','engine':'first','page_num':'size','texto_ocr':_cc})
    .rename(columns={'page_num':'n_pages','texto_ocr':'texto_completo'})
)
ced_docs['n_chars'] = ced_docs['texto_completo'].str.len()

# Merge con quality_report para traer blur_score
qr_cols = ['md5','blur_score','contrast','brightness','quality_label','n_pages']
ced_full = ced_docs.merge(qr_ced[qr_cols].rename(columns={'n_pages':'n_pages_qr'}), on='md5', how='left')

# Merge con image_manifest para traer ruta_imagen_procesada (pagina 1)
manif_p1 = manif[manif['page_num']==1][['md5','ruta_imagen_procesada']]
ced_full = ced_full.merge(manif_p1, on='md5', how='left')

print(f'Cedulas con texto OCR + calidad + imagen: {ced_full[\"ruta_imagen_procesada\"].notna().sum()}')
print()
print('Distribucion blur_score:')
print(ced_full['blur_score'].describe().round(2).to_string())
print()
print('quality_label:')
print(ced_full['quality_label'].value_counts().to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 5. MUESTREO ESTRATIFICADO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Muestreo estratificado por calidad visual

### Estrategia

El `quality_label` de Fase 1 esta sesgado (324/334 = APTO). Usamos `blur_score` directamente para definir dos estratos:

- **Alta calidad:** `blur_score > Q3` (top 25% mas nitidas)
- **Ruidosas:** `blur_score < Q1` (25% mas borrosas)

Se descartan las Cedulas sin imagen procesada o sin texto OCR. Tomamos `random_state=42` para reproducibilidad.

### Por que 30 + 30 y no 40 + 20

El plan §2.2 define 60 Cedulas como minimo viable para fine-tuning con augmentation 3x. Un split 50/50 por calidad maximiza la variabilidad del dataset: el modelo ve ejemplos nitidos y ruidosos en cantidades iguales → mejor generalizacion.
"""))

cells.append(code("""# Solo considerar docs con texto + imagen + blur_score
candidatos = ced_full[
    ced_full['ruta_imagen_procesada'].notna()
    & ced_full['texto_completo'].str.len().gt(20)
    & ced_full['blur_score'].notna()
].reset_index(drop=True)
print(f'Candidatos: {len(candidatos)} docs')

# Calcular quartiles
q1 = candidatos['blur_score'].quantile(0.25)
q3 = candidatos['blur_score'].quantile(0.75)
print(f'  Q1 blur_score = {q1:.1f}')
print(f'  Q3 blur_score = {q3:.1f}')

# Estratos
alta = candidatos[candidatos['blur_score'] >= q3].copy()
rui  = candidatos[candidatos['blur_score'] <= q1].copy()
print(f'  Pool alta calidad: {len(alta)}')
print(f'  Pool ruidosas:     {len(rui)}')

# Muestreo reproducible
muestra_alta = alta.sample(n=min(N_ALTA_CALIDAD, len(alta)), random_state=SEED).assign(estrato='alta_calidad')
muestra_rui  = rui.sample(n=min(N_RUIDOSAS, len(rui)),  random_state=SEED).assign(estrato='ruidosa')

muestra = pd.concat([muestra_alta, muestra_rui]).reset_index(drop=True)
print(f'\\nMuestra final: {len(muestra)} docs')
print(f'  alta_calidad: {(muestra[\"estrato\"]==\"alta_calidad\").sum()}')
print(f'  ruidosa:      {(muestra[\"estrato\"]==\"ruidosa\").sum()}')
print()
print('blur_score por estrato:')
print(muestra.groupby('estrato')['blur_score'].describe().round(1).to_string())
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 6. REGEX LAXA PARA NUMERO
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Regex laxa para `numero` de cedula

### Patron

Las cedulas colombianas tienen numeros de 7-10 digitos, usualmente impresos con separadores de miles:

- `1.234.567` — punto como separador (formato oficial)
- `1 234 567` — espacios (frecuente en OCR)
- `1,234,567` — coma (menos frecuente)

Pero **7-10 digitos corridos** tambien son validos porque el OCR a veces pierde los separadores:
- `1234567` — sin separadores

Ademas, hay cadenas que pueden confundirse (codigos de barra, numeros de serie, fechas sin separador). Para minimizar falsos positivos, buscamos el numero que aparezca **despues** de alguno de los anchors tipicos: `NUMERO`, `CEDULA`, `CC`, `IDENTIFICACION`.

### Precision esperada

Alta: ~70-85% — porque el anchor reduce falsos positivos. El humano valida en Label Studio; si el regex fallo, anota el campo desde cero.
"""))

cells.append(code("""# Regex: busca numero despues de un anchor
# Tolerancia: hasta 60 chars entre anchor y numero (por layouts variables)
_ANCHORS = r'(?:NUMERO|N[UÚ]MERO|CEDULA|C[EÉ]DULA|\\bC\\.?\\s?C\\.?\\b|IDENTIFICACION|IDENTIFICACI[OÓ]N)'
_NUM     = r'(\\d{1,3}(?:[.,\\s]\\d{3}){2,3}|\\d{7,10})'
RE_NUMERO_CED = re.compile(f'{_ANCHORS}.{{0,60}}?{_NUM}', re.IGNORECASE | re.DOTALL)


def extraer_numero_cedula(texto):
    if not isinstance(texto, str) or len(texto) < 10:
        return None
    m = RE_NUMERO_CED.search(texto)
    if not m:
        return None
    # Normalizar: quitar espacios/puntos/comas
    raw = m.group(1)
    digitos = re.sub(r'[.,\\s]', '', raw)
    if len(digitos) < 7 or len(digitos) > 10:
        return None
    return digitos


# Aplicar a la muestra
muestra['numero_regex'] = muestra['texto_completo'].apply(extraer_numero_cedula)

# Cobertura
detectados_alta = muestra[muestra['estrato']=='alta_calidad']['numero_regex'].notna().sum()
detectados_rui  = muestra[muestra['estrato']=='ruidosa']['numero_regex'].notna().sum()

print(f'Cobertura de numero via regex:')
print(f'  alta_calidad: {detectados_alta}/{N_ALTA_CALIDAD} = {detectados_alta/N_ALTA_CALIDAD:.1%}')
print(f'  ruidosa:      {detectados_rui}/{N_RUIDOSAS} = {detectados_rui/N_RUIDOSAS:.1%}')
print(f'  TOTAL:        {detectados_alta+detectados_rui}/{len(muestra)} = {(detectados_alta+detectados_rui)/len(muestra):.1%}')
print()
print('Ejemplos detectados (primeros 10):')
print(muestra[muestra['numero_regex'].notna()].head(10)[['filename','estrato','numero_regex']].to_string(index=False))
print()
print('Ejemplos NO detectados (primeros 5 — candidatos a anotacion manual):')
print(muestra[muestra['numero_regex'].isna()].head(5)[['filename','estrato','blur_score']].to_string(index=False))
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 7. EXPORTAR LABEL STUDIO BIMODAL
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Exportar Label Studio — tareas bimodales (texto + imagen)

Label Studio soporta tareas con **multiples modalidades** en una sola pantalla. El humano ve:
1. La imagen procesada del documento (referencia visual)
2. El texto OCR extraido (campo anotable)
3. La pre-anotacion del `numero` de cedula resaltada

El humano:
- Valida o corrige el `numero` pre-anotado
- Anota los otros 7 campos manualmente sobre el texto OCR
- Puede referirse a la imagen si el OCR tiene errores

### Esquema de labeling (a configurar en Label Studio)

```xml
<View>
  <Image name="image" value="$image_path"/>
  <Labels name="label" toName="text">
    <Label value="numero" background="#FF6B6B"/>
    <Label value="nombre_completo" background="#4ECDC4"/>
    <Label value="apellidos" background="#45B7D1"/>
    <Label value="fecha_nacimiento" background="#FFA500"/>
    <Label value="lugar_nacimiento" background="#95E1D3"/>
    <Label value="fecha_expedicion" background="#C9A0FF"/>
    <Label value="lugar_expedicion" background="#F38181"/>
    <Label value="sexo" background="#AA96DA"/>
    <Label value="rh" background="#FCBAD3"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

### Documentacion

- Labeling Bimodal: https://labelstud.io/guide/labeling#Bimodal-labeling
- Predictions format: https://labelstud.io/guide/predictions
"""))

cells.append(code("""tasks = []
for _, row in muestra.iterrows():
    texto = str(row['texto_completo'])
    img_path = str(row['ruta_imagen_procesada'])

    predictions = []
    num = row['numero_regex']
    if num is not None and isinstance(num, str):
        # Buscar el numero en el texto para posicionarlo
        idx = texto.find(num)
        if idx < 0:
            # Buscar variantes con separador original
            for sep in ['.', ' ', ',']:
                formatted = sep.join([num[:len(num)-6], num[len(num)-6:-3], num[-3:]])
                idx = texto.find(formatted)
                if idx >= 0:
                    num = formatted
                    break
        if idx >= 0:
            predictions.append({
                'from_name': 'label',
                'to_name':   'text',
                'type':      'labels',
                'value': {
                    'start':  idx,
                    'end':    idx + len(num),
                    'text':   num,
                    'labels': ['numero'],
                },
                'score': 0.7,
            })

    task = {
        'data': {
            'image':    img_path,     # Label Studio renderiza local o URL
            'text':     texto,
            'md5':      row['md5'],
            'filename': row['filename'],
            'estrato':  row['estrato'],
            'blur_score': float(row['blur_score']),
        },
        'predictions': [{
            'model_version': 'regex_numero_cedula_v1',
            'result':        predictions,
        }],
    }
    tasks.append(task)

with CED_LABELST_OUT.open('w', encoding='utf-8') as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f'Tareas Label Studio: {len(tasks)}')
print(f'  con pre-anotacion numero: {sum(1 for t in tasks if t[\"predictions\"][0][\"result\"])}')
print(f'  Archivo: {CED_LABELST_OUT}')

# Manifest commiteable (sin texto PII)
muestra_out = muestra[['md5','filename','estrato','blur_score','contrast','brightness','quality_label','n_pages','engine','numero_regex']].copy()
muestra_out.to_csv(CED_MANIFEST_OUT, index=False)
print(f'Manifest: {CED_MANIFEST_OUT} — {len(muestra_out)} docs')

# Summary commiteable
summary = pd.DataFrame([{
    'total_muestra': len(muestra),
    'alta_calidad': N_ALTA_CALIDAD,
    'ruidosas': N_RUIDOSAS,
    'cobertura_numero_alta': round(detectados_alta/N_ALTA_CALIDAD, 3),
    'cobertura_numero_ruidosa': round(detectados_rui/N_RUIDOSAS, 3),
    'cobertura_numero_global': round((detectados_alta+detectados_rui)/len(muestra), 3),
    'seed': SEED,
}])
summary.to_csv(CED_SUMMARY_OUT, index=False)
print(f'Summary: {CED_SUMMARY_OUT}')
"""))


# ══════════════════════════════════════════════════════════════════════════════
# 8. RESUMEN + SIGUIENTE
# ══════════════════════════════════════════════════════════════════════════════
cells.append(md("""## Resumen + siguiente paso

### Lo que produjo este notebook

1. **60 Cedulas seleccionadas** con muestreo estratificado reproducible (seed=42)
2. **Pre-anotacion del numero** de cedula (esperado ~70% cobertura, a validar)
3. **Tareas Label Studio bimodales** con imagen + texto + anchor del numero
4. **Manifest commiteable** con md5 + estrato + blur_score (trazabilidad)

### Siguiente paso

1. **Subir imagenes procesadas al storage de Label Studio**:
   ```bash
   # Opcion A: servir imagenes desde filesystem local (recomendado para desarrollo)
   label-studio start --root-dir . --allow-serving-local-files
   ```

2. **Crear proyecto Label Studio** con el esquema XML documentado arriba (9 labels).

3. **Importar el JSON**:
   ```bash
   curl -X POST -H "Authorization: Token TU_TOKEN" \\
        -F "file=@data/processed/cedulas_preanotaciones_labelstudio.json" \\
        http://localhost:8080/api/projects/{ID}/import
   ```

4. **Anotacion humana** (estimado ~15 min/doc × 60 docs = **15 horas**):
   - Validar el `numero` pre-anotado (o corregir/anadir)
   - Anotar los otros 7 campos observando la imagen

5. **Exportar anotaciones** en formato JSON-MIN y convertir al esquema del proyecto para §3.0-3.1.

### Paralelamente

- Notebook 08 — Polizas (80 docs muestra aleatoria, anotacion manual sin LFs)
- Notebook 09 — Camara de Comercio (80 docs con chunking layout-aware pre-aplicado)
"""))


# ══════════════════════════════════════════════════════════════════════════════
# GUARDAR
# ══════════════════════════════════════════════════════════════════════════════
nb['cells'] = cells
out = Path(__file__).parent / '07_preanotaciones_cedulas.ipynb'
nbf.write(nb, out)
print(f'Notebook generado: {out}')
md_count = sum(1 for c in cells if c.cell_type == 'markdown')
code_count = sum(1 for c in cells if c.cell_type == 'code')
print(f'  Celdas: {len(cells)} ({md_count} markdown + {code_count} code)')
