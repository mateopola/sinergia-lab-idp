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
