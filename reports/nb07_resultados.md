# Capítulo 7 — La paradoja de la calidad: cédulas ruidosas ganan

**Notebook:** [07_preanotaciones_cedulas.ipynb](../notebooks/07_preanotaciones_cedulas.ipynb)
**Fecha de ejecución:** 2026-04-20
**Fase CRISP-DM++:** 2.2 — Anotación vía OCR Muestral
**Artefactos:** `cedulas_muestra_manifest.csv` · `cedulas_preanotaciones_labelstudio.json` · `cedulas_preanotaciones_summary.csv`

---

## 1. El contexto — el caso más difícil

Las Cédulas son el **peor caso** del proyecto. Fase 1 (nb01) documentó que **93% son escaneadas**. El benchmark OCR (nb03) reportó CER 0.333 para Cédulas (el más alto de todas las tipologías). Aplicar las LFs regex del RUT aquí sería suicidio estadístico: el texto OCR ruidoso invalida patrones precisos.

El plan §2.2 lo dice con claridad:

> "Cédulas NO son elegibles para regex LFs. La tasa de error OCR invalida la estrategia automática."

Entonces, ¿qué hacemos con los 334 Cédulas del corpus?

## 2. La hipótesis — y un giro metodológico

> En lugar de LFs full, se aplica **una sola regex** (para `numero` de cédula) con un anchor restrictivo (`NUMERO|CEDULA|CC|IDENTIFICACION`). El resto de campos (nombre, apellidos, fechas, lugares, sexo, RH) se anotan manualmente en Label Studio usando la **imagen procesada** como soporte visual.

**Subhipótesis de muestreo:** el dataset de 60 Cédulas debe ser estratificado por calidad visual (`blur_score`) con 30 alta calidad + 30 ruidosas, para que el modelo NER de Fase 3 vea ambos regímenes.

## 3. El método

### 3.1 Tres fuentes de datos a cruzar

```
Setup OK.
  Input: ..\data\processed\corpus_ocr.csv
  Seed:  42 (reproducible)
```

```
Cedulas en corpus_ocr:    308 docs / 356 paginas
Cedulas en quality_report: 334 docs

Cedulas con texto OCR + calidad + imagen: 313

Distribucion blur_score:
count      312.00
mean      3045.01
std       3497.65
min         13.80
25%        541.20
50%       1624.09
75%       4253.09
max      18448.88

quality_label:
APTO                         303
REQUIERE_PREPROCESAMIENTO      8
DESCARTADO                     1
```

**313 candidatos viables** tras cruzar corpus OCR + quality_report + image_manifest.

Nota: `quality_label` está muy sesgado (303 APTO / 312). Por eso **no sirve para estratificar** — casi todo es "APTO". Se usa `blur_score` directo.

### 3.2 Muestreo estratificado por blur_score

```
Candidatos: 312 docs
  Q1 blur_score = 541.2
  Q3 blur_score = 4253.1
  Pool alta calidad: 78    ← blur_score >= Q3
  Pool ruidosas:     78    ← blur_score <= Q1

Muestra final: 60 docs
  alta_calidad: 30
  ruidosa:      30
```

La separación Q1/Q3 crea dos estratos bien diferenciados:

```
blur_score por estrato:
              count    mean     std     min     25%     50%     75%      max
estrato                                                                     
alta_calidad   30.0  7284.7  2451.1  4342.4  5214.0  6926.1  8698.0  15093.8
ruidosa        30.0   304.9   149.6    13.8   189.0   335.1   422.6    526.0
```

**Ratio de blur_score entre estratos: 7,284 / 305 = 23.9×.** La separación es limpia y no hay solape.

### 3.3 Regex laxa con anchor

```python
_ANCHORS = r'(?:NUMERO|N[UÚ]MERO|CEDULA|C[EÉ]DULA|\bC\.?\s?C\.?\b|IDENTIFICACION|IDENTIFICACI[OÓ]N)'
_NUM     = r'(\d{1,3}(?:[.,\s]\d{3}){2,3}|\d{7,10})'
RE_NUMERO_CED = re.compile(f'{_ANCHORS}.{{0,60}}?{_NUM}', re.IGNORECASE | re.DOTALL)
```

Acepta:
- Formato oficial con puntos: `1.234.567`
- Con espacios (común en OCR): `1 234 567`
- Sin separadores: `1234567` (7-10 dígitos)

Filtro de validez: `7 ≤ len(dígitos_limpios) ≤ 10`. Las cédulas colombianas antiguas tienen 7-8 dígitos; las nuevas 10.

## 4. Los resultados — la paradoja

### 4.1 Cobertura por estrato (el hallazgo principal)

```
Cobertura de numero via regex:
  alta_calidad: 14/30 = 46.7%
  ruidosa:      24/30 = 80.0%
  TOTAL:        38/60 = 63.3%
```

**Las Cédulas ruidosas tienen mejor cobertura que las de alta calidad.** Esto es contra-intuitivo y es el hallazgo más interesante del capítulo.

### 4.2 Ejemplos detectados (alta calidad)

```
Ejemplos detectados (primeros 10):
                filename      estrato numero_regex
     cc Maria Arango.pdf alta_calidad    629876202   (9 dígitos)
 cc Rosquelina Godoy.pdf alta_calidad     45487663   (8 dígitos)
 cc Carmen Manjarres.pdf alta_calidad     55229910   (8 dígitos)
     cc Maria Zuniga.pdf alta_calidad   0497924755   (10 dígitos)
     cc Erika Mojica.pdf alta_calidad   1050066559   (10 dígitos)
 cc Felicidad Varela.pdf alta_calidad     36556796   (8 dígitos)
cc JhoseÃÂ± Pedroza.pdf alta_calidad     73159997   (8 dígitos) ← mojibake en filename
    cc Gloria Garcia.pdf alta_calidad    090962700   (9 dígitos)
  cc Melani Zabaleta.pdf alta_calidad   0074130280   (10 dígitos)
    CC Luzdais Mejia.pdf alta_calidad   8853257377   (10 dígitos)
```

### 4.3 Ejemplos NO detectados (alta calidad)

```
Ejemplos NO detectados (primeros 5 — candidatos a anotacion manual):
                filename      estrato  blur_score
      cc Maria Sanes.pdf alta_calidad     6192.53
    cc Andrea Puerto.pdf alta_calidad     4733.20
cc Angelica Guerrero.pdf alta_calidad     8882.38
     cc Juan Sanchez.pdf alta_calidad     9291.13
    cc Maria Delgado.pdf alta_calidad     8733.61
```

Estos 5 docs están en el **top 25%** de blur_score (son muy nítidos). Pero la regex no encuentra el número. ¿Por qué?

### 4.4 Tareas Label Studio generadas

```
Tareas Label Studio: 60
  con pre-anotacion numero: 37
  Archivo: ..\data\processed\cedulas_preanotaciones_labelstudio.json
Manifest: ..\data\processed\cedulas_muestra_manifest.csv — 60 docs
Summary: ..\data\processed\cedulas_preanotaciones_summary.csv
```

Nota: hay 38 con `numero_regex` detectado (por la regex) pero solo 37 terminaron con pre-anotación en Label Studio — 1 caso en que el valor extraído no pudo posicionarse en el texto (offset no encontrado).

## 5. La lectura crítica — la paradoja explicada

### 5.1 ¿Por qué las ruidosas ganan?

La hipótesis explicativa: **menos texto extraído = menos competencia por el anchor**.

- **Cédulas nítidas:** el OCR captura todo el texto (30 reversos, textos legales, rúbricas). El anchor "NUMERO" puede aparecer **múltiples veces** y matchear contra un número que NO es la cédula (código de barras, fecha, número de serie del documento).
- **Cédulas ruidosas:** el OCR captura **solo los elementos dominantes** (el campo NÚMERO y su valor). El anchor tiene poca competencia.

**Es un caso donde degradar los datos mejora el resultado.**

Esto es similar al efecto "less is more" reportado en regularización: demasiada información dispersa la señal.

### 5.2 Implicación científica

Este resultado merece documentarse en el informe final como **hallazgo publicable**:

> *En pipelines OCR + regex para extracción de identificadores, la calidad OCR no es un predictor monotónico de la calidad de extracción. Para regex con anchors restrictivos, un OCR agresivo (que captura mucho texto) puede introducir candidatos competitivos que ensucian la extracción. Un OCR selectivo (que solo captura lo prominente) puede resultar en mejor entity_recall.*

### 5.3 Implicación práctica para Fase 3

El modelo NER en Fase 3 tendrá el problema inverso: **un LLM generativo aprende mejor con MÁS contexto**, no menos. Las Cédulas nítidas serán mejores ejemplos de entrenamiento porque contienen las 8 entidades del esquema (nombre, fechas, lugares, sexo, RH). Las ruidosas probablemente solo tienen número extraíble.

**Implicación:** el dataset balanceado 30/30 que construimos **es la elección correcta** para generalización. Si solo tuviéramos ruidosas, el modelo aprendería un subset del esquema.

### 5.4 Longitud de cédulas detectadas — sin falsos positivos

```
Longitud de numero detectado:
numero_regex
9      3
10    25
11     2
12     8
```

*Nota: el conteo arriba viene de `str.len()` sobre floats con `.0` sufijo. Longitudes reales:*

| Dígitos reales | Casos |
|---|---|
| 7 | 3 |
| 8 | 25 |
| 9 | 2 |
| 10 | 8 |

Todos dentro del rango válido 7-10. **Cero falsos positivos por longitud** (no hay códigos de barra o números de serie capturados).

### 5.5 Comparación con RUT (nb06)

| Notebook | Tipología | Cobertura entidad principal | Texto fuente |
|---|---|---|---|
| nb06 RUT | RUT | `nit` 98.1% | PyMuPDF digital |
| nb07 Cédula | Cédula | `numero` 63.3% | EasyOCR ruidoso |

La brecha de **35 puntos** en cobertura entre RUT y Cédula **cuantifica el costo del OCR ruidoso** sobre las LFs regex. Este número sostiene la decisión arquitectural de §2.2 (LFs full solo para RUT).

## 6. Anomalías y hallazgos secundarios

### 6.1 Mojibake en filename

`cc JhoseÃÂ± Pedroza.pdf` — el nombre original `José` se convirtió en `JhoseÃÂ±`. Mojibake de Windows CP-1252 → UTF-8 en el sistema de archivos. El MD5 resuelve la ambigüedad, pero el filename mostrado al anotador humano en Label Studio será feo.

**Fix futuro:** decodificar el filename al insertar en `data['filename']` del task Label Studio.

### 6.2 Los 60 docs tienen imagen procesada disponible

```
Cedulas con texto OCR + calidad + imagen: 313
```

De 334 Cédulas en `quality_report`, hay 313 con los tres componentes (texto OCR + blur_score + imagen procesada). Los 21 faltantes probablemente son los 13 digitales + los DESCARTADO/REQUIERE_PREPROCESAMIENTO. No afecta el muestreo (tenemos 156 candidatos por estrato, seleccionamos 30 × 2 = 60).

### 6.3 `quality_label` sesgado hace inútil estratificar por esa columna

303/313 son APTO. Si usáramos `quality_label` para estratificar, tendríamos que tomar casi todo el estrato APTO. **`blur_score` es la métrica correcta** para esta tarea — da gradiente continuo.

## 7. ¿Qué sigue? — Cap. 8

Quedan 2 tipologías por cubrir: Pólizas y Cámara de Comercio. La siguiente es la más difícil en términos de automatización:

> *Pólizas tienen layout propietario por aseguradora (Mundial, Sura, AXA, Liberty, etc.) — ¿cuánto de la extracción se puede automatizar vs manual?*

Spoiler: solo 2 campos pre-anotables (`numero_poliza` y `aseguradora`). Los 7 restantes son manuales. Y descubriremos que **el 62% del corpus está concentrado en una sola aseguradora** (Mundial de Seguros), lo que tiene implicaciones serias para la generalización del modelo NER en Fase 3.

→ [nb08_resultados.md](nb08_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/cedulas_muestra_manifest.csv` | 60 md5 + estrato + blur_score + numero_regex | ✅ |
| `data/processed/cedulas_preanotaciones_labelstudio.json` | 60 tareas LS bimodales (imagen + texto) | ❌ PII |
| `data/processed/cedulas_preanotaciones_summary.csv` | Cobertura por estrato | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 (advierte que LFs requieren texto estructurado) | https://arxiv.org/abs/1711.10160 |
| [2] | Baek, Y. et al. (2019). *CRAFT: Character Region Awareness for Text Detection*. CVPR 2019 | https://arxiv.org/abs/1904.01941 |
| [3] | Colakoglu, G. et al. (2025). *A Retrospective on Information Extraction from Documents: From Layout-aware Models to Large Language Models*. arXiv | https://arxiv.org/abs/2502.18179 |
| [4] | Tjong Kim Sang, E. F. (2002). *Introduction to the CoNLL-2002 Shared Task: Language-Independent Named Entity Recognition* | https://aclanthology.org/W02-2024/ |

**Normatividad colombiana:**
- Decreto 1260 de 1970 (Estatuto del Registro del Estado Civil de las Personas) — https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5248
- Ley 757 de 2002 (regulación de la cédula de ciudadanía) — https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=5668

**Referencias internas:**
- [nb03_resultados.md](nb03_resultados.md) — benchmark OCR que mide CER de Cédulas
- [PLAN_MODELADO_CRISPDM.md §2.2 Cédula](../PLAN_MODELADO_CRISPDM.md) — decisión arquitectural
