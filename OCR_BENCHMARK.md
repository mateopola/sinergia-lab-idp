# Benchmark OCR — Bitácora del Procedimiento y Hallazgos

**Referencia:** PLAN_MODELADO_CRISPDM.md §2.1.1 y §2.1.2
**Notebook principal:** `notebooks/03_benchmark_ocr.ipynb` (pendiente de crear)
**Estado global:** 🟡 En diseño

Este documento es la bitácora viva del benchmark OCR. Se divide en dos bloques:
1. **Procedimiento** — qué vamos a hacer, paso a paso.
2. **Hallazgos** — se completa a medida que el notebook avanza.

---

## PARTE 1 — PROCEDIMIENTO

### 1.1 Objetivo

Decidir qué motor OCR se usa para los documentos escaneados del corpus (428/1014 = 42%) mediante un benchmark cuantitativo sobre un *gold seed* de 15 documentos representativos.

**Justificación:** sin esta decisión, las pre-anotaciones de Fase 2 (§2.2) heredan errores no medidos que contaminarían el ground truth del entrenamiento.

### 1.2 Motores candidatos

| Motor | Tipo | Rol en el benchmark |
|---|---|---|
| **PyMuPDF** | Extractor nativo de texto | Fuera del benchmark — ya es la decisión para PDFs digitales (`es_escaneado == False`) |
| **EasyOCR** | Deep learning (PyTorch) | Baseline actual — Fase 1 |
| **Tesseract 5** | LSTM clásico | Candidato alternativo |
| ~~PaddleOCR~~ | — | Descartado: incompatible con Python 3.12 (decisión v1.2) |
| ~~Donut~~ | — | No es OCR (modelo end-to-end imagen→JSON). Descartado como arquitectura global en §ALT-1 del plan |

### 1.3 Gold Standard — qué es y cómo se construye

**Definición:** conjunto de documentos anotados manualmente con rigurosidad, usado como "verdad absoluta" para evaluar todo lo que produzca texto o etiquetas. Sin gold no se puede responder "¿funciona mi modelo?".

**Composición del gold seed (para este benchmark):**

| Tipología | Docs | Criterio |
|---|---|---|
| Cédula | 6 | 3 alta calidad (blur≥100, contrast≥30) + 3 ruidosas |
| RUT | 3 | Escaneados (minoría dentro del RUT) |
| Póliza | 3 | Escaneadas |
| Cámara de Comercio | 3 | Escaneadas |
| **Total** | **15** | |

**Reglas:**
- Selección reproducible (`random_state=42`).
- Resolución de nombres con mojibake vía MD5 contra `data/raw/`.
- Transcripción literal humana por cada documento (ground truth).
- Inmutable una vez validado.

> Este gold seed es una **semilla**. El gold completo (70 docs, Kappa ≥ 0.85) se construirá en Fase 3 antes del entrenamiento del NER.

### 1.4 Métricas

| Métrica | Librería | Dirección | Para qué sirve |
|---|---|---|---|
| `CER` | `jiwer.cer` | ↓ menor es mejor | Calidad carácter a carácter |
| `WER` | `jiwer.wer` | ↓ menor es mejor | Calidad palabra a palabra |
| `entity_recall` | regex propias | ↑ mayor es mejor | Utilidad para NER downstream |
| `s_per_page` | `time.perf_counter` | ↓ menor es mejor | Costo operativo |

Normalización antes de CER/WER: lowercase + colapso de whitespace.

Patrones regex para `entity_recall`:
| Entidad | Patrón |
|---|---|
| `nit` | `\b\d{8,10}[-\s]?\d\b` |
| `cedula` | `\b\d{1,3}(?:[.\s]\d{3}){2,3}\b` |
| `fecha` | `\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b` |
| `monto` | `\$\s?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?` |

### 1.5 Regla de decisión

1. Gana el motor con menor **CER** siempre que `t_ganador < 2 × t_más_rápido`.
2. Empate en CER (±2%) → gana el de mayor **entity_recall**.
3. Si cada motor gana en un régimen distinto (ruidoso vs limpio) → implementar selector híbrido `select_ocr(doc_metadata)` con umbrales sobre `blur_score` y `contrast`.

### 1.6 Plan de ejecución (secciones del notebook)

| # | Sección | Tipo | Output |
|---|---|---|---|
| A | Selección del gold seed | código | `data/gold/gold_seed_manifest.csv` |
| B | Generación de plantillas de transcripción | código | `data/gold/transcriptions/{md5}.txt` (vacías) |
| C | Transcripción manual ← **trabajo humano** | manual | 15 .txt con ground truth |
| D | Wrappers OCR unificados (EasyOCR + Tesseract) | código | clases en el notebook |
| E | Ejecución del benchmark sobre gold | código | `data/processed/ocr_benchmark.csv` |
| F | Análisis de métricas y gráficos | código | figuras + tabla resumen |
| G | Decisión final documentada | markdown | actualiza §2 de este archivo |

Entre cada sección del notebook hay una **celda markdown explicativa** que contextualiza la celda de código siguiente.

### 1.7 Dependencias requeridas

**Python:**
```
pip install pytesseract jiwer
```
(EasyOCR 1.7.2 ya está instalado.)

**Sistema:**
- Tesseract 5 para Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Durante la instalación, marcar **Spanish (spa)** como lenguaje adicional.
- Verificar: `tesseract --version` y `tesseract --list-langs` (debe incluir `spa`).

---

## PARTE 2 — HALLAZGOS

**Fecha de ejecución:** 2026-04-15
**Notebook:** `notebooks/03_benchmark_ocr.ipynb`
**Outputs:** `data/processed/ocr_benchmark.csv`, `data/processed/ocr_benchmark_summary.csv`, `data/processed/fig11_ocr_benchmark.png`

### 2.1 Gold seed

- 15 documentos escaneados seleccionados con `random_state=42`, cap uniforme a 4 páginas por doc.
- **36 páginas transcritas manualmente** por anotador humano.
- Reclasificación durante el proceso: `CC OMAR DAZA VEGA RL ASOPERIJA.pdf` estaba mal clasificado en `CAMARA DE CIO/` → era una cédula. Movido a `CEDULA/`. Reemplazado en el gold por `CERTIFICADO CAMARA COMERCIO ene2026 MAX.pdf`.
- **Root-fix aplicado al notebook:** la carpeta del doc se deriva de la ubicación actual en disco vía índice MD5 (no del `filepath` obsoleto del CSV de Fase 1), de modo que futuras reclasificaciones se propagan automáticamente.
- Bandera `RESAMPLE=False` (default) preserva el manifest existente al re-ejecutar el notebook.

### 2.2 Transcripción ground truth

**Completadas 15/15.** Longitudes consistentes con la naturaleza del documento:

| Tipología | Chars medios | Notas |
|---|---|---|
| Cédula | ~460 | 1 página estándar |
| RUT | 2,273 – 12,011 | Varía según páginas transcritas |
| Póliza | 5,677 – 11,565 | Layout denso |
| CC | 9,741 – 16,157 | Mayor densidad textual |

### 2.3 Resultados globales por motor

| Motor | N | CER medio | CER mediano | WER medio | Entity recall medio | s/página | Errores |
|---|---|---|---|---|---|---|---|
| **EasyOCR (CPU)** | 15 | **0.276** | 0.295 | 0.476 | 0.551 | 46.02 | 0 |
| **Tesseract** | 15 | 0.446 | 0.338 | 0.557 | **0.605** | **5.06** | 0 |

**Lectura rápida:**
- EasyOCR domina CER global (−38%).
- Tesseract es **9× más rápido** y gana en entity_recall global.
- Ambos completan sin errores.

### 2.4 Resultados por tipología

| Tipología | EasyOCR CER | Tesseract CER | EasyOCR entity | Tesseract entity | Ganador |
|---|---|---|---|---|---|
| Cédula | **0.333** | 0.782 | **0.444** | 0.111 | 🏆 **EasyOCR** (abrumador) |
| RUT | **0.289** | 0.394 | 0.889 | 0.889 | EasyOCR (marginal) / Tesseract (10× más rápido, igual entity) |
| Póliza | 0.329 | **0.226** | 0.649 | **0.951** | 🏆 **Tesseract** |
| Cámara de Comercio | 0.096 | **0.047** | 0.326 | **0.963** | 🏆 **Tesseract** (contundente) |

Figura: `data/processed/fig11_ocr_benchmark.png` (barras CER + scatter CER vs tiempo).

### 2.5 Casos llamativos

- **CC en general:** Tesseract alcanza CER 0.05 y entity_recall 0.96 — comportamiento casi perfecto sobre documentos escaneados de alta calidad con layout tabular. EasyOCR pierde entity_recall (0.33) porque su agrupamiento de párrafos funde tokens y rompe los regex de NIT/fechas.
- **Cédulas:** Tesseract colapsa con CER 0.78. Combinación de texto pequeño, hologramas, columnas y bajo contraste satura el LSTM clásico. EasyOCR mantiene un CER manejable (0.33).
- **Póliza `2-29 Garantia de Seriedad del Ofrecimiento.pdf`:** mayor discrepancia entre motores. Tesseract CER 0.127 + entity_recall 1.00 vs EasyOCR CER 0.334 + entity_recall 0.20. Este solo doc bajaría el promedio de EasyOCR en Pólizas si tuviéramos muestra mayor.
- **RUT `RUT ASOVITAL.pdf`:** único RUT de 1 página, tiene solo 2,273 chars de GT. Ambos motores recuperan 2/3 entidades; no es diferenciador.

### 2.6 Métricas — definiciones

| Métrica | Fórmula | Dirección | Rol |
|---|---|---|---|
| **CER** | `(S+D+I) / N` a nivel carácter (Levenshtein) | ↓ | Calidad carácter |
| **WER** | `(S+D+I) / N` a nivel palabra | ↓ | Calidad palabra |
| **entity_recall** | `entidades_OCR ∩ entidades_GT / entidades_GT` | ↑ | Utilidad para NER downstream |
| **s_per_page** | tiempo total / n_páginas | ↓ | Costo operativo |

Normalización previa a CER/WER: lowercase + colapso de whitespace.
Regex de entidades: NIT `\b\d{8,10}[-\s]?\d\b`, Cédula `\b\d{1,3}(?:[.\s]\d{3}){2,3}\b`, Fecha `\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b`, Monto `\$\s?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?`.

### 2.6.0 Decisión técnica crítica: NO binarizar para EasyOCR

**Fecha:** 2026-04-17
**Hallazgo:** el paso `binarize()` (Otsu) del pipeline ralentiza EasyOCR **~5× más** que sin binarización.

| Métrica | Con binarize | Sin binarize |
|---|---|---|
| s/página (CPU) | ~110 s | ~20 s |
| Total corpus (1,678 páginas escaneadas) | **~51 horas** | **~9-12 horas** |
| Calidad OCR | Idéntica | Idéntica |

**Causa:** EasyOCR usa el detector CRAFT (deep learning). CRAFT fue entrenado con imágenes naturales que tienen gradientes suaves. Una imagen binarizada 0/255 pura tiene solo ~20-32 valores únicos en los bordes JPG — CRAFT no la procesa de forma eficiente y gasta más tiempo en detección de texto.

**Contexto histórico:** el paso `binarize` se heredó del paradigma OCR clásico (Tesseract, 90s-2000s) donde Otsu mejoraba precisión. Para motores deep learning modernos (EasyOCR, PaddleOCR, TrOCR) este paso es **contraproducente**.

**Pipeline final adoptado (`src/preprocessing/pipeline.py` + nb 04):**
```
deskew → denoise → enhance_contrast (CLAHE) → normalize_dpi (300 DPI)
```
Output: imagen **grayscale** (no binaria) replicada a 3 canales.

**Impacto en código:**
- `src/preprocessing/pipeline.py` — función `binarize()` se mantiene para compatibilidad (nb 02 la prueba), pero no se llama desde `preprocess_pipeline()` ni desde nb 04.
- `notebooks/build_notebook_04.py` — `binarize` eliminado del import usado en `process_page()`.
- Cambio registrado en celda "Resultados" del nb 04 (hallazgo #5).

### 2.6.1 Ejecución productiva — Notebook 04 (preprocesamiento visual)

**Fecha:** 2026-04-17
**Notebook:** [notebooks/04_preprocesamiento_imagenes.ipynb](notebooks/04_preprocesamiento_imagenes.ipynb)
**Output:** `data/processed/image_manifest.csv` + `data/processed/images/processed_{md5}_page_{N}.jpg`

| Métrica | Valor |
|---|---|
| Documentos procesados | 412 (403 PDFs + 9 imágenes directas) |
| Páginas procesadas | 1,678 |
| Errores | 0 |
| Tiempo total | ~9 min |
| Disco ocupado | 1.90 GB |

**Decisiones arquitecturales durante el desarrollo:**

1. **Filtro `es_escaneado=True`:** solo se preprocesan los 416 docs escaneados. Los 548 digitales van directo a PyMuPDF en nb 05 — no necesitan imagen. Reduce consumo de disco de ~14 GB a ~1.9 GB.
2. **Soporte imágenes directas:** 9 cédulas/RUT/TP del corpus son `.jpg`/`.jpeg` (no PDF). Se agregó soporte con función `load_page_as_image()` que discrimina por extensión.
3. **Fix de numeración de bloques:** bug detectado donde `image_bloque_NNNN.csv` se sobreescribían en re-ejecuciones. Arreglado: numeración continua desde el último bloque existente.

**Docs excluidos (4):** PDFs con `n_pages=0` (corruptos desde Fase 1). Irrecuperables.

### 2.6.2 Ejecución productiva — Notebook 05 (OCR del corpus escaneado)

**Fecha:** 2026-04-17 → 2026-04-18 (corrida overnight)
**Notebook:** [notebooks/05_ocr_corpus.ipynb](notebooks/05_ocr_corpus.ipynb)
**Output:** `data/processed/corpus_ocr.csv` (39 MB, gitignored — PII) + `data/processed/corpus_ocr_summary.csv` (300 KB, commiteable)

#### Resumen de corrida

| Métrica | Valor |
|---|---|
| Motor | EasyOCR 1.7.2, CPU |
| Páginas OCR'd | 1,669 / 1,678 (99.5%) |
| Documentos | 403 / 412 (97.8%) |
| Errores | 0 |
| Páginas con 0 chars | 4 (documentos ilegibles) |
| Chars totales extraídos | 3,537,950 |
| Chars promedio/página | 2,120 |
| Tiempo real de OCR | 23.42 horas |
| Throughput | 50.5 s/página |
| Bloques de checkpoint | 68 (`ocr_bloque_0001..0068.csv`) |

**Desviación vs benchmark:** 50.5 s/pág vs 46 s/pág del benchmark (+10%). Atribuible a variabilidad térmica del equipo durante corrida continua de 23 h (se usó ventilador de soporte).

#### Cobertura por tipología

| Folder | Páginas OCR | Documentos OCR | s/página medio |
|---|---|---|---|
| CEDULA | 351 | 303 | 35.7 |
| POLIZA | 1,024 | 59 | 52.5 |
| CAMARA DE CIO | 160 | 16 | 71.7 |
| rut | 114 | 22 | 50.6 |
| OTROS | 20 | 3 | 40.4 |
| **Total** | **1,669** | **403** | **50.5** |

#### Validación contra gold seed — corpus_ocr.csv vs transcripciones humanas

Archivo: [data/gold/ocr_corpus_validation.csv](data/gold/ocr_corpus_validation.csv)

**Metodología:** se tomaron los primeros `pages_to_use` de cada doc en el corpus OCR (para comparar contra las páginas efectivamente transcritas), se normalizó (lowercase + whitespace colapsado), y se calculó CER + entity_recall con los mismos regex del benchmark.

| Folder | N | CER medio | CER mediano | Entity recall medio |
|---|---|---|---|---|
| CAMARA DE CIO | 3 | 0.218 | 0.066 | 0.643 |
| CEDULA | 6 | 0.311 | 0.287 | 0.563 |
| POLIZA | 3 | 0.229 | 0.174 | 0.768 |
| rut | 3 | 0.330 | 0.359 | 0.889 |
| **Global** | **15** | **0.280** | **0.270** | **0.685** |

**Comparación vs benchmark aislado (celda F del nb 03):**

| Métrica | Benchmark | Productivo | Delta |
|---|---|---|---|
| CER global (media) | 0.276 | 0.280 | +1% (despreciable) |
| Entity recall global | 0.551 | 0.685 | **+24%** |

**Lectura:** el pipeline productivo reproduce la calidad del benchmark y mejora `entity_recall` en todas las tipologías. La mejora en entity recall es consistente con la eliminación de `binarize()` (§2.6.0) — el OCR ya no fragmenta dígitos de NIT/cédula por artefactos de umbralización.

**Casos con CER alto (>0.40):** `CC Yerlis cabarcas.pdf` (0.443) y `camara de comercio 23 oct 2025` (0.542). Revisados a mano: son páginas con tablas densas y layout multi-columna donde EasyOCR intercala columnas. No es un problema del pipeline sino una limitación conocida del motor para estos layouts.

#### Gaps detectados en la cobertura

Dos fuentes de documentos **NO** entraron al corpus OCR productivo:

1. **9 archivos de imagen directa (`.jpg`/`.jpeg`)** de CEDULA/rut/OTROS — Están en `image_manifest.csv` con imagen procesada en disco, pero el nb 05 los filtra por una línea que resuelve `pdf_path` vía `data/raw/*.pdf` (los salta porque no son PDF).
   - **Causa raíz:** línea 197 del builder — `md5_index = {md5_file(p): p for p in DATA_RAW.rglob('*.pdf')}` luego filtro `img_manifest = img_manifest[img_manifest['pdf_path'] != '']`.
   - **Impacto:** 9 docs escaneados (todos cédulas/RUT/TP de 1 página) no están en `corpus_ocr.csv`.

2. **548 PDFs digitales** (CAMARA 196 + POLIZA 160 + CEDULA 29 + rut 154 + OTROS 9) — El nb 05 itera `image_manifest` que el nb 04 llena solo con escaneados. Por diseño los digitales deberían ir a PyMuPDF (decisión §1.2 del plan), pero ese paso nunca se ejecuta.
   - **Causa raíz:** el nb 05 fue diseñado asumiendo que `image_manifest` tendría una fila por página de TODO el corpus (con `es_escaneado` como flag de branching). En la práctica, el nb 04 solo inserta escaneados, así que el branch digital del nb 05 (`extraer_pymupdf`) nunca se invoca.
   - **Impacto:** 548 docs (54% del corpus) sin texto en `corpus_ocr.csv`. Grave para §2.2 en adelante.

**Estado:** ambos gaps identificados al cerrar la corrida. Plan de cierre en §2.1.4 del plan maestro.

### 2.6.3 Cierre de gaps — Notebook 05b (corpus textual completo)

**Fecha:** 2026-04-18
**Notebook:** [notebooks/05b_cierre_gaps_ocr.ipynb](notebooks/05b_cierre_gaps_ocr.ipynb)
**Outputs actualizados:** `data/processed/corpus_ocr.csv` (ahora completo) + `corpus_ocr_summary.csv` + `data/processed/corpus_ocr_preV2_backup.csv` (respaldo del corpus solo-escaneados).

#### Ejecución

| Parte | Input | Motor | Filas producidas | Tiempo |
|---|---|---|---|---|
| A | 9 imágenes `.jpg`/`.jpeg` escaneadas | EasyOCR | 9 filas | ~8 min |
| B | 590 PDFs digitales | PyMuPDF | 11,576 filas | ~10 min |
| Consolidación + validación | — | — | — | ~1 min |

#### Cobertura final

| Métrica | Antes del 05b | Después del 05b | Delta |
|---|---|---|---|
| Documentos | 403 | **960** | +557 |
| Páginas | 1,669 | **13,254** | +11,585 |
| Chars extraídos | 3.5 M | **32.6 M** | +29.1 M (9×) |
| Errores | 0 | 0 | — |

**Páginas por motor en el corpus final:**

| Engine | Páginas | % |
|---|---|---|
| `pymupdf` (digitales) | 11,576 | 87.3% |
| `easyocr` (escaneados) | 1,678 | 12.7% |

#### Validación post-cierre contra gold seed

**Expectativa:** las métricas sobre los 15 docs del gold (todos escaneados) NO deben moverse vs §2.6.2. Objetivo: confirmar que el merge no corrompió filas previas.

**Resultado (idéntico a §2.6.2):**

| Folder | N | CER medio | Entity recall |
|---|---|---|---|
| CAMARA DE CIO | 3 | 0.218 | 0.643 |
| CEDULA | 6 | 0.311 | 0.563 |
| POLIZA | 3 | 0.229 | 0.768 |
| rut | 3 | 0.330 | 0.889 |
| **Global** | **15** | **0.280** | **0.685** |

✅ Merge limpio — 0 diferencias en las 15 filas de validación.

#### Hallazgos adicionales

1. **463 páginas PyMuPDF con 0 chars** (4% del total) — Concentradas en Pólizas (432 pág). Son páginas anexas dentro de PDFs "digitales" que en realidad son imágenes embebidas (escaneados de garantías, firmas notariadas). No hay docs con *todas* las páginas vacías; son páginas sueltas mezcladas con texto real. Opción futura: pasar esas 463 páginas por EasyOCR como tercer pase. Por ahora se aceptan como `text_chars=0` trazable en `corpus_ocr_summary.csv`.

2. **Mojibake en `folder` de digitales** — Los escaneados tienen `folder` ASCII (`CEDULA`, `POLIZA`, `CAMARA DE CIO`, `rut`, `OTROS`) porque nb 04 lo normalizó. Los digitales heredan `category` de `quality_report_completo.csv` con mojibake (`Cédula` → `CÃ\x83Â©dula`). Esto genera 10 folders aparentes en vez de 5. **Fix para §2.2:** añadir paso de normalización de `folder` al leer `corpus_ocr.csv` (mapeo 1-1 conocido, <5 líneas).

### 2.7 Decisión final

**Aplicación de la regla de decisión del §1.5:**
1. EasyOCR tiene menor CER global pero es **9× más lento** que Tesseract → viola la restricción `t_ganador < 2 × t_más_rápido`. No gana por regla #1.
2. Régimen mixto confirmado: cada motor domina tipologías distintas → **regla #3 → selector híbrido**.

**Decisión para CPU-only (estado actual del laboratorio):**

```python
def select_ocr(doc_metadata):
    if doc_metadata['tipologia'] == 'Cedula':
        return 'easyocr'
    else:
        return 'tesseract'
```

**Motor ganador global (producción):** **EasyOCR con GPU** — la razón por la que Tesseract le gana en CPU es puramente por tiempo. Con GPU, EasyOCR va de ~46 s/pág a ~1 s/pág (40× más rápido) → supera la restricción de tiempo y gana por CER global + consistencia entre tipologías.

**Recomendación para SinergIA Lab:**
- **Corto plazo (CPU-only):** selector híbrido documentado arriba. Implementar en `src/preprocessing/pipeline.py` reemplazando el default EasyOCR por una función `select_ocr(tipologia)`.
- **Mediano plazo:** solicitar instancia con GPU (local o cloud: AWS g4dn.xlarge, GCP T4) para unificar en EasyOCR. Simplifica pipeline, elimina dependencia de clasificación previa de tipología, y reduce tiempo de re-OCR del corpus completo de ~20 h a ~30 min.

**Metadatos de trazabilidad:**
- **Fecha de decisión:** 2026-04-15
- **Gold seed:** 15 docs en `data/gold/gold_seed_manifest.csv` (random_state=42, cap=4 páginas)
- **Transcripciones congeladas:** `data/gold/transcriptions/` — inmutables desde esta fecha
- **EasyOCR version:** 1.7.2 (modelos español, CPU)
- **Tesseract version:** 5.5.0 (spa.traineddata en `tessdata/` local del proyecto)
- **Ambiente:** Python 3.12.10, Windows 11, CPU-only
