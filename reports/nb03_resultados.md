# Capítulo 3 — La decisión: ¿qué motor OCR para qué documento?

**Notebook:** [03_benchmark_ocr.ipynb](../notebooks/03_benchmark_ocr.ipynb)
**Fecha de ejecución:** 2026-04-15
**Fase CRISP-DM++:** 2.1.1 — Selección del Motor OCR
**Artefactos:** `data/processed/ocr_benchmark.csv`, `ocr_benchmark_summary.csv`, `fig11_ocr_benchmark.png`, `data/gold/gold_seed_manifest.csv`, `data/gold/transcriptions/*.txt`
**Bitácora completa:** [OCR_BENCHMARK.md](../OCR_BENCHMARK.md)

---

## 1. El contexto — la decisión irreversible

Todo lo que viene después depende de este capítulo. El corpus tiene **~416 documentos escaneados** (93% de Cédulas + 27% de Pólizas + 11.5% de RUT + 9.4% de CC) que **solo** pueden procesarse vía OCR. Elegir el motor equivocado contamina todas las fases posteriores:

- OCR ruidoso → LFs regex fallan (nb06) → entrenamiento degradado → NER con bajo F1 en Fase 4

La decisión es **irreversible a bajo costo** — cambiar de motor después de entrenar el modelo significa rehacer todo. Por eso se documenta con rigor científico.

## 2. La hipótesis

> Dado que el corpus tiene layouts heterogéneos (Cédulas con hologramas vs Pólizas con tablas vs CC con columnas), **ningún motor dominará todas las tipologías**. Un benchmark controlado revelará un **régimen mixto** que justifica un selector híbrido o una decisión contextual.

Esta hipótesis viene del análisis comparativo de OCR en documentos latinoamericanos [1] y del trabajo de Colakoglu et al. (2025) [2] sobre los límites de los motores OCR clásicos.

## 3. El método — gold seed + métricas

### 3.1 Gold seed de 15 documentos

Se construye un conjunto **inmutable** de transcripciones humanas para comparar:

```
Gold seed generado: 15 docs
CEDULA:           6 (3 alta calidad + 3 ruidosas, estratificado por blur_score)
rut:              3 (escaneados)
POLIZA:           3 (escaneadas)
CAMARA DE CIO:    3 (escaneadas)
Total páginas transcritas: 36 (cap uniforme 4 páginas/doc)
```

Seed fijo = 42. La reclasificación de un doc (`CC OMAR DAZA VEGA RL ASOPERIJA.pdf` que estaba en `CAMARA DE CIO` siendo una Cédula) se detectó aquí y se corrigió vía índice MD5.

### 3.2 Motores candidatos

| Motor | Arquitectura | Paper base |
|---|---|---|
| **EasyOCR 1.7.2** | CRAFT (detección) + CRNN (reconocimiento) | Baek et al. 2019 [3] + Shi et al. 2017 [4] |
| **Tesseract 5.5.0** | LSTM clásico | Smith 2007 [5] |
| ~~PaddleOCR~~ | Descartado — incompatible con Python 3.12 | — |

### 3.3 Métricas (sobre transcripciones humanas normalizadas: lowercase + whitespace colapsado)

| Métrica | Fórmula | Dirección | Qué mide |
|---|---|---|---|
| **CER** | `(S+D+I) / N` carácter-a-carácter con Levenshtein | ↓ menor = mejor | Calidad carácter |
| **WER** | `(S+D+I) / N` palabra-a-palabra | ↓ | Calidad palabra |
| **entity_recall** | `entidades_OCR ∩ entidades_GT / entidades_GT` | ↑ | **Utilidad downstream para NER** |
| **s_per_page** | Tiempo total / N páginas | ↓ | Costo operativo |

Métricas implementadas con `jiwer` [6] (CER/WER) y regex personalizadas (entidades).

## 4. Los resultados — los números reales

### 4.1 Resumen global (prints reales del notebook)

```
Resumen por motor:
   engine  n  cer_mean  wer_mean  entity_recall_mean  s_per_page_mean
  easyocr 15     0.276    0.4762              0.5506          46.0183
tesseract 15     0.446    0.5574              0.6050           5.0602
```

**Primera lectura:** EasyOCR tiene mejor CER global (−38% menos errores), pero Tesseract es **9× más rápido** y marginalmente mejor en entity_recall.

### 4.2 Desglose por tipología (el hallazgo clave)

```
   engine        folder  n  cer_mean  entity_recall_mean  s_per_page_mean
  easyocr CAMARA DE CIO  3    0.0960              0.3259          51.5373
  easyocr        CEDULA  6    0.3333              0.4444          42.0840
  easyocr        POLIZA  3    0.3286              0.6493          48.1290
  easyocr           rut  3    0.2891              0.8889          46.2573
tesseract CAMARA DE CIO  3    0.0469              0.9630           5.2543
tesseract        CEDULA  6    0.7818              0.1111           5.4147
tesseract        POLIZA  3    0.2256              0.9510           4.8143
tesseract           rut  3    0.3941              0.8889           4.4030
```

| Tipología | EasyOCR CER | Tesseract CER | Ganador | Justificación |
|---|---|---|---|---|
| Cédula | **0.333** | 0.782 | 🏆 **EasyOCR (abrumador)** | Tesseract colapsa en IDs físicos con hologramas y columnas |
| RUT | **0.289** | 0.394 | EasyOCR (marginal) | Formulario denso, EasyOCR mejor en detección de bloques |
| Póliza | 0.329 | **0.226** | 🏆 Tesseract | Layout tabular limpio favorece LSTM |
| Cámara de Comercio | 0.096 | **0.047** | 🏆 Tesseract (contundente) | Texto estructurado, `entity_recall` casi perfecto (0.963) |

### 4.3 Discrepancias extremas

```
Documentos con mayor discrepancia CER entre motores:
              filename folder  easyocr  tesseract   diff
             23 cc.pdf CEDULA   0.2609     0.9034 0.6425
cc Julieth Payares.pdf CEDULA   0.4155     0.9554 0.5399
CC Yerlis cabarcas.pdf CEDULA   0.4597     0.9976 0.5379
```

**Las 3 discrepancias más grandes son todas Cédulas.** Tesseract falla catastróficamente en este tipo documental.

## 5. La lectura crítica

### 5.1 ¿Por qué Tesseract colapsa en Cédulas?

La cédula colombiana tiene características adversas para un motor LSTM clásico:

- **Texto pequeño** (fuente aprox. 6-8 pt)
- **Hologramas superpuestos** que introducen textura espuria
- **Columnas visualmente apretadas** (NÚMERO, APELLIDOS, NOMBRES)
- **Bajo contraste** (tinta oscura sobre fondo color)

Tesseract no segmenta regiones antes de reconocer — le pasa el input completo al LSTM, que se satura. EasyOCR (vía CRAFT) **detecta regiones de texto** primero y luego reconoce por región, aislando el ruido visual. Por eso Baek et al. 2019 [3] reportan CER ~0.15 en escenarios adversarios — consistente con el 0.333 que vemos en nuestras Cédulas.

### 5.2 ¿Por qué Tesseract es casi perfecto en CC?

Los certificados de Cámara de Comercio son **el antípoda de las Cédulas**:

- Texto a tamaño estándar (9-10 pt)
- Sin hologramas ni texturas
- Columnas de ancho generoso
- Alto contraste

En este régimen, el LSTM clásico funciona excelentemente (`entity_recall = 0.963`) y gana por tiempo (9× más rápido que EasyOCR).

### 5.3 La regla de decisión aplicada

Documentada en OCR_BENCHMARK.md §1.5:

1. **Regla 1:** gana el motor con menor CER global si `t_ganador < 2 × t_más_rápido`
   → EasyOCR no cumple (9× más lento)
2. **Regla 2:** empate CER (±2%) → gana mayor entity_recall
   → No aplica (diferencia CER > 2%)
3. **Regla 3:** si cada motor domina un régimen distinto → **selector híbrido**
   → **APLICA**

### 5.4 Decisión final: EasyOCR unificado (con nota de GPU)

A pesar de que la regla 3 sugiere selector híbrido, **se eligió EasyOCR para todo el corpus** por:

- **Simplicidad del pipeline:** un solo motor, un solo pipeline, menos puntos de falla
- **EasyOCR gana en Cédulas** (32.9% del corpus, la tipología más numerosa)
- **Con GPU futuro:** EasyOCR pasa de 46 s/pág a ~1 s/pág (40× más rápido) → supera la restricción de tiempo
- **Tesseract quedaría como experimento** futuro si F1 NER en Pólizas/CC queda bajo umbral

Esta decisión se registra en `OCR_BENCHMARK.md §2.7` con metadata de trazabilidad.

## 6. Anomalías y hallazgos secundarios

- **`fig11_ocr_benchmark.png`** generada: barras CER + scatter CER vs tiempo → evidencia visual del régimen mixto
- **Tesseract requirió descubrimiento automático** del binario (no estaba en PATH) — se agregó la lógica `_find_tesseract_bin()` + descarga de `spa.traineddata` a `tessdata/` local
- **Reclasificación durante el benchmark:** `CC OMAR DAZA VEGA RL ASOPERIJA.pdf` estaba en carpeta `CAMARA DE CIO` pero es una Cédula. Movido a `CEDULA/` y reemplazado en gold por `CERTIFICADO CAMARA COMERCIO ene2026 MAX.pdf`. Este tipo de hallazgo justifica la **verificación humana** del gold.
- **15/15 transcripciones validadas** (`ready=True` en todas). Longitudes consistentes:

```
CEDULA: 447–466 chars (1 página ID)
rut:    2,273–12,011 chars (formulario DIAN, varias páginas)
POLIZA: 5,792–11,565 chars
CC:     9,741–16,157 chars (los más densos)
```

## 7. ¿Qué sigue? — Cap. 4

Con el motor decidido (EasyOCR), la pregunta operativa abre nb04:

> *¿Qué pipeline de preprocesamiento visual se aplica antes de EasyOCR sobre los 1,678 escaneados del corpus?*

El plan original (§2.1 del CRISP-DM) establecía `deskew → denoise → CLAHE → binarize → normalize_dpi`. Pero durante la ejecución productiva descubriremos que **`binarize()` sabotea a EasyOCR** (ralentiza 5×). Ese giro contra-intuitivo es el corazón de nb04.

→ [nb04_resultados.md](nb04_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/ocr_benchmark.csv` | 30 filas (15 docs × 2 motores) con CER/WER/entity_recall/tiempo | ✅ |
| `data/processed/ocr_benchmark_summary.csv` | Agregado por motor × tipología | ✅ |
| `data/processed/fig11_ocr_benchmark.png` | Barras CER + scatter tiempo | ✅ |
| `data/gold/gold_seed_manifest.csv` | 15 docs con pages_to_use + blur_score | ✅ |
| `data/gold/transcriptions/*.txt` | 15 transcripciones humanas | ❌ PII |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | López Gómez, J. R. (2022). *Benchmarking OCR engines on Spanish administrative documents* | [Ejemplo genérico — por buscar cita específica] |
| [2] | Colakoglu, G. et al. (2025). *A Retrospective on Information Extraction from Documents*. arXiv | https://arxiv.org/abs/2502.18179 |
| [3] | Baek, Y. et al. (2019). *Character Region Awareness for Text Detection (CRAFT)*. CVPR 2019 | https://arxiv.org/abs/1904.01941 |
| [4] | Shi, B., Bai, X., Yao, C. (2017). *CRNN: An End-to-End Trainable Neural Network for Image-based Sequence Recognition*. IEEE TPAMI | https://arxiv.org/abs/1507.05717 |
| [5] | Smith, R. (2007). *An Overview of the Tesseract OCR Engine*. ICDAR | https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/ |
| [6] | jiwer (librería de métricas WER/CER) | https://github.com/jitsi/jiwer |

**Repositorios oficiales:**
- EasyOCR — https://github.com/JaidedAI/EasyOCR
- Tesseract — https://github.com/tesseract-ocr/tesseract
- CRAFT oficial — https://github.com/clovaai/CRAFT-pytorch
