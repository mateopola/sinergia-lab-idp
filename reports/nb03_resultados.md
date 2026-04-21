# Resultados — Notebook 03 · Benchmark OCR (EasyOCR vs Tesseract)

**Fase CRISP-DM++:** 2.1.1 — Selección del Motor OCR
**Notebook:** [03_benchmark_ocr.ipynb](../notebooks/03_benchmark_ocr.ipynb)
**Fecha de ejecución:** 2026-04-15
**Bitácora completa:** [OCR_BENCHMARK.md](../OCR_BENCHMARK.md) (este documento resume lo esencial)

---

## 1. Metadatos de ejecución

- Python 3.12, CPU
- Duración: ~3h (transcripción manual + 20 min cómputo)
- Input: 15 documentos del gold seed (`data/gold/gold_seed_manifest.csv`)
- Métricas: CER, WER, entity_recall, s/página

## 2. Resumen cuantitativo

### 2.1 Resultados globales

| Motor | CER medio | WER medio | Entity recall | s/página |
|---|---|---|---|---|
| **EasyOCR (CPU)** | **0.276** | 0.476 | 0.551 | 46.02 |
| Tesseract 5 | 0.446 | 0.557 | **0.605** | **5.06** |

### 2.2 Por tipología

| Tipología | EasyOCR CER | Tesseract CER | Ganador |
|---|---|---|---|
| Cédula | **0.333** | 0.782 | 🏆 **EasyOCR** (abrumador) |
| RUT | **0.289** | 0.394 | EasyOCR (marginal) |
| Póliza | 0.329 | **0.226** | 🏆 Tesseract |
| Cámara de Comercio | 0.096 | **0.047** | 🏆 Tesseract (contundente) |

## 3. Hallazgos

### 🏆 Hallazgo 1 — Régimen mixto: cada motor domina una zona

- **EasyOCR** gana en Cédulas (tipología más numerosa: 332 docs) y es marginalmente mejor en RUT
- **Tesseract** gana en Pólizas y CC (documentos con layout tabular limpio) y es **9× más rápido** en CPU

### 🟢 Hallazgo 2 — Decisión final fundamentada

Aplicando la regla de decisión documentada (`§1.5 del benchmark`):

1. EasyOCR menor CER global, pero 9× más lento → viola restricción `t_ganador < 2×t_rápido`
2. Régimen mixto confirmado → **selector híbrido** si CPU / **EasyOCR unificado** si GPU

**Decisión adoptada:** EasyOCR unificado en CPU (pagando el tiempo) — simplicidad del pipeline supera la pérdida en Pólizas/CC. Corrida productiva de 23h sobre 1,678 páginas escaneadas (ver [nb05_resultados.md](nb05_resultados.md)).

### 🟡 Hallazgo 3 — Razón por la que Tesseract colapsa en Cédulas

Tesseract CER 0.782 en Cédulas = efectivamente inutilizable. Causa: texto pequeño, hologramas, columnas y bajo contraste saturan el clasificador LSTM de Tesseract. EasyOCR (CRAFT + CRNN) maneja mejor ese tipo de layout porque el detector CRAFT segmenta regiones antes de reconocer.

### 🔴 Hallazgo 4 — `binarize()` ralentiza EasyOCR 5×

**Descubrimiento crítico post-benchmark (2026-04-17):** aplicar Otsu antes de EasyOCR lleva el throughput de ~20 s/pág a ~110 s/pág.

- Causa: el detector CRAFT es deep learning entrenado con imágenes naturales con gradientes suaves. Una imagen binarizada 0/255 tiene pocos valores únicos — CRAFT gasta más tiempo en inferencia.
- Convención OCR clásica (Tesseract) recomendaba binarizar. **Contraproducente** para deep learning moderno.
- Decisión: eliminar `binarize()` del pipeline productivo (§2.1.3 del plan, §2.6.0 del benchmark).

## 4. Anomalías y limitaciones

- PaddleOCR **descartado** — incompatible con Python 3.12 al momento del benchmark
- Donut **descartado** — no es OCR sino VLM end-to-end, requeriría 4 modelos especializados por tipología (ver ALT-1 del plan)
- Tesseract requirió configurar `TESSDATA_PREFIX` y descargar `spa.traineddata` manualmente
- Gold seed es 15 docs — suficiente para decisión OCR pero **no** para F1 NER (requiere 70 docs extendidos)

## 5. Implicaciones para fases posteriores

1. **Nb 04** aplica pipeline sin `binarize` a los 1,678 escaneados
2. **Nb 05** usa EasyOCR para escaneados, PyMuPDF para digitales
3. **Nb 05b** completa el corpus añadiendo 9 imágenes + 590 digitales
4. **Fase 3 Etapa A** originalmente proponía Arctic-Extract pero cambió tras auditoría (ver PROPUESTA_MODELOS.md y §3.0 del plan v2.0)

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/ocr_benchmark.csv` | 30 filas (15 docs × 2 motores) con CER/WER/entity_recall/tiempo | ✅ |
| `data/processed/ocr_benchmark_summary.csv` | Agregado por motor y tipología | ✅ |
| `data/processed/fig11_ocr_benchmark.png` | Barras CER + scatter CER vs tiempo | ✅ |
| `data/gold/gold_seed_manifest.csv` | 15 docs con pages_to_use + blur_score | ✅ |
| `data/gold/transcriptions/*.txt` | Transcripciones humanas | ❌ PII |

## 7. Referencias internas

- [OCR_BENCHMARK.md](../OCR_BENCHMARK.md) — bitácora completa del procedimiento y hallazgos (canonical)
- [PLAN_MODELADO_CRISPDM.md §2.1.1](../PLAN_MODELADO_CRISPDM.md) — task `[x]` con decisión
- [PROPUESTA_MODELOS.md §Fase 1 OCR](../PROPUESTA_MODELOS.md) — citas científicas de EasyOCR, Tesseract, PyMuPDF

## 8. Referencias bibliográficas

- Baek et al. (2019). Character Region Awareness for Text Detection (CRAFT). CVPR. https://arxiv.org/abs/1904.01941
- Shi, Bai, Yao (2017). CRNN. IEEE TPAMI. https://arxiv.org/abs/1507.05717
- Smith (2007). An Overview of the Tesseract OCR Engine. ICDAR. https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/
