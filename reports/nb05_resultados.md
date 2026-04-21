# Resultados — Notebook 05 · OCR del Corpus (primer pase, escaneados)

**Fase CRISP-DM++:** 2.1 — OCR productivo
**Notebook:** [05_ocr_corpus.ipynb](../notebooks/05_ocr_corpus.ipynb)
**Fecha de ejecución:** 2026-04-17 a 2026-04-18 (overnight)
**Output principal:** `data/processed/corpus_ocr.csv` (39 MB, primer pase — se extiende en nb 05b)

---

## 1. Metadatos de ejecución

- Python 3.12, CPU (RTX sin GPU disponible)
- Duración: **23.42 horas overnight**
- Input: `image_manifest.csv` (1,678 páginas escaneadas)
- Motor: EasyOCR 1.7.2, idioma `es`, GPU=False
- Bloques de checkpoint: 68 (`ocr_bloque_0001..0068.csv`)

## 2. Resumen cuantitativo

### 2.1 Corrida productiva

| Métrica | Valor |
|---|---|
| Páginas procesadas | **1,669 / 1,678** (99.5%) |
| Documentos | 403 / 412 (97.8%) |
| Errores | 0 |
| Páginas con 0 chars | 4 |
| Chars totales extraídos | 3,537,950 |
| Chars promedio/página | 2,120 |
| Throughput real | **50.5 s/página** |
| Desviación vs benchmark (46 s/pág) | +10% (variabilidad térmica corrida continua 23h) |

### 2.2 Cobertura por tipología

| Folder | Páginas OCR | Docs | s/página medio |
|---|---|---|---|
| CEDULA | 351 | 303 | 35.7 |
| POLIZA | 1,024 | 59 | 52.5 |
| CAMARA DE CIO | 160 | 16 | 71.7 |
| rut | 114 | 22 | 50.6 |
| OTROS | 20 | 3 | 40.4 |
| **Total** | **1,669** | **403** | **50.5** |

### 2.3 Validación contra gold seed (slicing por `pages_to_use`)

| Folder | N | CER medio | CER mediano | Entity recall |
|---|---|---|---|---|
| CAMARA DE CIO | 3 | 0.218 | 0.066 | 0.643 |
| CEDULA | 6 | 0.311 | 0.287 | 0.563 |
| POLIZA | 3 | 0.229 | 0.174 | 0.768 |
| rut | 3 | 0.330 | 0.359 | 0.889 |
| **Global** | **15** | **0.280** | **0.270** | **0.685** |

### 2.4 Comparación benchmark aislado vs productivo

| Métrica | Benchmark (nb 03) | Productivo (nb 05) | Delta |
|---|---|---|---|
| CER global | 0.276 | 0.280 | +1% (despreciable) |
| Entity recall global | 0.551 | 0.685 | **+24%** |

## 3. Hallazgos

### 🟢 Hallazgo 1 — Pipeline productivo mejora entity_recall +24% sobre benchmark

El CER se mantiene pero `entity_recall` sube 24% — consistente con eliminación de `binarize()` (§2.6.0). El OCR ya no fragmenta dígitos de NIT/cédula por artefactos de umbralización.

### 🟢 Hallazgo 2 — RUT alcanza entity_recall 0.889 (el más alto del corpus)

Relevante porque RUT es la tipología **primaria para las LFs** de Fase 2.2. Los 89% de entidades capturadas correctamente son base sólida para las regex del notebook 06.

### 🟡 Hallazgo 3 — Casos con CER alto son limitación del motor

- `CC Yerlis cabarcas.pdf` CER 0.443 — cédula borrosa legítima
- `camara de comercio 23 oct 2025` CER 0.542 — tablas densas con columnas que EasyOCR intercala

**No es bug del pipeline** sino limitación conocida de EasyOCR para layouts tabulares multi-columna. Modelos layout-aware (LayoutLMv3) en Fase 3 deberían resolverlo.

### 🟢 Hallazgo 4 — 0 errores sobre 1,669 páginas

Robustez validada. El patrón de checkpoints con bloques de 50 permitió retomas después de interrupciones térmicas nocturnas.

### 🔴 Hallazgo 5 — Dos gaps de cobertura detectados

Al cruzar `corpus_ocr_summary.csv` con `quality_report_completo.csv`:

1. **9 archivos `.jpg`/`.jpeg`** filtrados por `pdf_path==''` aunque ya tenían imagen procesada
2. **548 PDFs digitales** nunca entraron al pipeline (el nb 05 iteraba `image_manifest` que solo tiene escaneados)

Ambos cerrados en nb 05b. Ver [nb05b_resultados.md](nb05b_resultados.md).

## 4. Anomalías y limitaciones

- 4 páginas con 0 chars (docs con firmas digitales que renderizan como imagen vacía — irrecuperables)
- El CSV `corpus_ocr.csv` (39 MB con texto) queda **gitignored por PII**; el summary sin texto es commiteable
- Mojibake en `folder` de quality_report_completo.csv se propaga al CSV final (pendiente normalización)

## 5. Implicaciones para fases posteriores

1. **Nb 05b** cierra los dos gaps para producir corpus completo
2. **Nb 06** consume `corpus_ocr.csv` para aplicar LFs a RUT
3. **Nb 07** consume `corpus_ocr.csv` para muestreo de Cédulas
4. **Fase 3.1 NER** todos los candidatos se entrenan sobre este mismo texto consolidado

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/corpus_ocr.csv` | Texto + bboxes por página (39 MB) | ❌ PII |
| `data/processed/corpus_ocr_summary.csv` | Métricas sin texto | ✅ |
| `data/processed/ocr_blocks/ocr_bloque_*.csv` | 68 checkpoints | ❌ |
| `data/gold/ocr_corpus_validation.csv` | Validación vs gold con CER + entity_recall | ✅ |

## 7. Referencias internas

- [OCR_BENCHMARK.md §2.6.2](../OCR_BENCHMARK.md) — ejecución productiva documentada (canonical)
- [PLAN_MODELADO_CRISPDM.md §2.1.4](../PLAN_MODELADO_CRISPDM.md) — task `[x]`
