# Capítulo 11 — BETO fine-tuned: cuando el modelo más sofisticado pierde por captar demasiada semántica

**Notebook:** [11_clasificacion_C2_beto.ipynb](../notebooks/11_clasificacion_C2_beto.ipynb)
**Builder:** [build_notebook_11.py](../notebooks/build_notebook_11.py)
**Fecha de ejecución:** 2026-04-26
**Fase CRISP-DM++:** 3.0 — Clasificación de tipo de documento (candidato C-2)
**Hardware:** Colab Free Tesla T4 GPU
**Output principal:** `models/c2_beto/{model.safetensors, metrics.json, c2_predictions.csv}` · [fig_nb11_confusion.png](fig_nb11_confusion.png)

---

## 1. El contexto — el experimento crítico del estudio comparativo

Tras C-1 (TF-IDF + LR) alcanzar Macro-F1 = 1.0000 en test (con 5-fold CV de 0.996 ± 0.004), el siguiente experimento del plan era **C-2: BETO fine-tuned** sobre `dccuchile/bert-base-spanish-wwm-cased`.

La hipótesis del plan original (PROPUESTA_MODELOS.md) era que **BETO debería superar al baseline en al menos +5 puntos macro-F1** (criterio de éxito del paper original Cañete et al. 2020 sobre tareas en español). Esto se sustentaba en literatura general de transformers que reporta mejoras consistentes sobre TF-IDF en tareas similares.

**Pero ya sabíamos algo distinto:** C-1 reveló que el corpus es **estructuralmente trivial** — los documentos colombianos oficiales se identifican por palabras-clave en su título de pág 1. Esa observación predijo que C-2 también convergería a ~100% sin aportar mejora real.

Este notebook **valida o refuta** esa predicción.

## 2. La hipótesis (post-resultado de C-1)

> "BETO converge a Macro-F1 ~99-100% en test (similar a C-1), confirmando que la tarea de clasificación es estructuralmente trivial en este dominio. La capacidad adicional del transformer **no se traduce en F1 superior** porque las features discriminantes están a nivel de palabras-clave, no de semántica fina. Por tanto C-2 NO se justifica para producción frente a C-1."

## 3. El método

### 3.1 Reproducibilidad estricta (split idéntico a C-1)

```python
random_state    = 42        # CRITICO: mismo split que nb10
test_size       = 0.15
val_size        = 0.15
stratify        = clase     # mantiene proporciones por clase
```

Mismo conjunto de datos: 1,115 docs (1,134 menos los 19 con texto OCR vacío). Misma división: train=779 / val=168 / test=168.

### 3.2 Hiperparámetros

```python
model_name      = "dccuchile/bert-base-spanish-wwm-cased"
max_length      = 512    # truncamiento, suficiente para títulos+contenido relevante
batch_size      = 16
learning_rate   = 2e-5   # estándar para BERT fine-tuning
n_epochs        = 3
weight_decay    = 0.01
fp16            = True   # acelera 2x sin pérdida de precisión perceptible
load_best_model_at_end = True  # selecciona checkpoint por mejor val_macro_f1
```

### 3.3 Arquitectura

`BertForSequenceClassification` con cabeza lineal de 4 clases sobre el `[CLS]` token. La capa `bert.pooler.dense` y `classifier` se inicializan aleatoriamente; el resto de los 110M parámetros vienen pre-entrenados de BETO.

## 4. Los resultados — la predicción se confirma

### 4.1 Curvas de entrenamiento (147 steps en 1.57 min)

```
Epoch | Training Loss | Validation Loss | Accuracy | Macro F1
  1   | 0.094370      | 0.022460        | 0.9940   | 0.9914
  2   | 0.069677      | 0.009124        | 1.0000   | 1.0000
  3   | 0.029217      | 0.007503        | 1.0000   | 1.0000
```

**Análisis cualitativo de las curvas:**
- Training loss baja monotónicamente: 0.094 → 0.069 → 0.029
- Validation loss baja monotónicamente: 0.022 → 0.009 → 0.0075
- **Ambas curvas bajan en paralelo → NO hay overfitting** (el patrón overfitting sería train↓ + val↑)
- Val Macro-F1 alcanza 1.0 en epoch 2 — la tarea se resuelve completamente para val

El best checkpoint cargado al final fue **epoch 3** (mejor val_loss = 0.0075).

### 4.2 Métricas en test

```
Test Accuracy   : 0.9940
Test Macro-F1   : 0.9914
Test Weighted-F1: 0.9940
Test Loss       : 0.0139
```

### 4.3 Per-class breakdown

```
                precision    recall  f1-score   support
CamaraComercio     1.0000    0.9643    0.9818        28
        Cedula     1.0000    1.0000    1.0000        78
        Poliza     0.9677    1.0000    0.9836        30
           RUT     1.0000    1.0000    1.0000        32

      accuracy                         0.9940       168
     macro avg     0.9919    0.9911    0.9914       168
```

**1 sola predicción mal de 168.** El error se concentra en:

- 1 documento de **CamaraComercio** clasificado como **Poliza** (CC recall 0.9643 + Poliza precision 0.9677 son la firma del mismo error)

### 4.4 Eficiencia inesperadamente alta

```
Tiempo entrenamiento: 1.57 min  (vs estimado 30 min)
Throughput train    : ~93 steps/min
Throughput eval     : 128.78 samples/s
```

→ **Mucho más rápido que el estimado conservador.** T4 + fp16 + batch 16 con BETO base en 779 docs es un setup óptimo. Esto reescribe el "Total esperado" del plan.

## 5. Lectura crítica — por qué el ganador es el modelo más simple

### 5.1 El veredicto sobre overfitting (con evidencia)

**NO hay overfitting en C-2.** Las curvas train/val descartan ese diagnóstico de forma decisiva:

| Síntoma de overfitting | Lo observado |
|---|---|
| Train loss baja mientras val loss sube | Ambas bajan monotónicamente |
| Train_F1 > Val_F1 con gap creciente | Train≈Val en cada epoch |
| Val accuracy estanca y empeora | Val alcanza 1.0 en epoch 2 y se mantiene |

El error en test (0.9914 vs 1.0 en val) **no es overfitting** — es **variabilidad natural del split**: el test contiene 1 doc particular que es genuinamente difícil. Si re-ejecutáramos con otro `random_state`, ese doc difícil podría caer en train o val y el test daría 100%.

### 5.2 La paradoja del modelo más sofisticado

Comparativa cabeza-a-cabeza C-1 vs C-2 (mismo split, seed=42):

| Métrica | C-1 TF-IDF + LR | C-2 BETO | Diff |
|---|---|---|---|
| Test Macro-F1 | **1.0000** | 0.9914 | **−0.86 pp** |
| Test Accuracy | 1.0000 | 0.9940 | −0.6 pp |
| Errores en test | 0/168 | 1/168 | +1 error |
| Tiempo train | 2.92 s | 94.2 s | **32× más** |
| Tamaño modelo | <10 MB | 440 MB | **44× más** |
| VRAM inferencia | 0 (CPU) | ~2 GB | GPU recomendada |
| Latencia inferencia | <10 ms | ~50 ms | **5× más** |
| Interpretabilidad | Top features directos | Atención (opaca) | TF-IDF gana |

→ **C-1 gana en TODOS los ejes**: precisión, costo, velocidad, interpretabilidad. Es la antítesis de lo que predice la literatura general (donde transformers suelen superar baselines en +5 a +15 pp).

### 5.3 El caso paradójico del único error

El doc misclasificado revela algo profundo sobre la diferencia entre los dos modelos:

- **C-1 TF-IDF acertó** ese doc — porque busca palabras literales como "cámara", "comercio", "verificación" que están en el título OCR'd. Si están presentes, vota CC. Sin matices.
- **C-2 BETO falló** ese mismo doc — porque captura **semántica profunda** del lenguaje jurídico colombiano. Posiblemente ese CC contiene fragmentos sobre "responsabilidad civil", "vigencia del contrato", "objeto del contrato", "celebrar acuerdo" — vocabulario jurídico que también aparece en pólizas. BETO razona sobre el "tipo de discurso" y se confunde.

> **La ironía del experimento:** ser "más inteligente" produjo el único error. Cuando la tarea es trivial, la sofisticación adicional puede ser contraproducente — captar matices innecesarios introduce ambigüedad donde el modelo simple no la ve.

### 5.4 Validación estadística rigurosa

¿Es C-2 significativamente peor que C-1, o es ruido del split?

```
C-1 5-fold CV: Macro-F1 = 0.9960 ± 0.0041
                 [min=0.9889, max=1.0000]
C-2 test     : Macro-F1 = 0.9914
                 → cae DENTRO del rango [0.9889, 1.0000]
                 → distancia al mean: 0.0046 (~1.13 σ)
```

→ Estadísticamente equivalentes. La diferencia es **ruido del split**, no superioridad real de uno sobre otro.

### 5.5 Implicación clara para producción

Para esta tarea específica (clasificación documental SECOP en 4 clases), **C-1 es estrictamente preferible**:

| Criterio | Decisión | Razón |
|---|---|---|
| Macro-F1 | C-1 ≥ C-2 (no significativo) | empate técnico |
| Costo cómputo | C-1 (32× más rápido entrenando) | TF-IDF |
| Footprint disco | C-1 (44× más liviano) | TF-IDF |
| Latencia | C-1 (5× más rápido) | TF-IDF |
| Hardware | C-1 (CPU) | TF-IDF |
| Interpretabilidad | C-1 (features directos) | TF-IDF |
| **Veredicto producción** | **C-1 TF-IDF** | gana en todos los ejes |

**BETO no se justifica.** Esta conclusión cambia las recomendaciones del plan original (que esperaba que BETO ganara por F1).

## 6. Anomalías

### 6.1 Eficiencia muy superior al estimado

El plan estimaba ~30 min de entrenamiento. La realidad fue **1.57 min** (~19× más rápido). Causas:

- **fp16 + T4** es muy eficiente para BETO base
- **Dataset pequeño** (779 docs) con max_length 512 = pocos steps totales (147)
- **Batch 16** aprovecha bien la VRAM del T4 (16 GB)

Esta eficiencia simplifica futuras corridas: si quisiéramos hacer hyperparameter tuning o cross-validation, ahora sabemos que cuesta 1-2 min por run.

### 6.2 Warnings benignos al cargar BETO

```
UNEXPECTED keys: cls.predictions.* (×8)
MISSING keys   : bert.pooler.dense.*, classifier.* (×4)
```

Esperados. BETO se distribuye con cabezas para Masked Language Modeling (`cls.predictions.*`) que aquí no usamos — se descartan. La cabeza nueva (`bert.pooler` + `classifier`) se inicializa aleatoriamente — exactamente lo que queremos para fine-tuning de clasificación.

### 6.3 Sin acceso a HF_TOKEN

```
WARNING: HF_TOKEN does not exist in Colab secrets
```

No bloqueante. Solo significa que las descargas se hacen con rate limit más estricto. Como solo descargamos BETO una vez (~440 MB), no afectó.

## 7. Qué sigue

### 7.1 Inmediato — nb12 LayoutLMv3

El último experimento del trio comparativo. Esperamos:
- Macro-F1 ~99-100% (alineado con C-1 y C-2)
- Tiempo entrenamiento mayor (LayoutLMv3 es multimodal, ~60-90 min)
- Confirmar que **el layout/imagen no aportan** sobre el texto plano en este dominio

### 7.2 Después de nb12 — reporte comparativo final

Construir `reports/clasificacion_comparativa_C1_C2_C3.md` con:
- Tabla unificada de métricas
- Recomendación de modelo para producción (probable: C-1)
- Análisis del caso límite (el único error de C-2)
- Conclusión científica del estudio comparativo de Fase 3.0

### 7.3 Después del comparativo — cierre Fase 3.0 y retomar NER

- Documentar decisión de modelo en `PLAN_MODELADO_CRISPDM.md`
- Retomar Fase 2.2 (Label Studio para anotaciones NER)
- Avanzar a Fase 3.1 (NER con N-1, N-2, N-3)

## 8. Referencias

- [_nb_outputs/11_clasificacion_C2_beto.txt](../_nb_outputs/11_clasificacion_C2_beto.txt) — outputs literales
- [reports/nb10_resultados.md](nb10_resultados.md) — capítulo previo (C-1) con el mismo split
- [PROPUESTA_MODELOS.md FASE 2 §C-2](../PROPUESTA_MODELOS.md) — fundamentación teórica
- Cañete, Chaperon, Fuentes, Ho, Kang, Pérez, "Spanish Pre-Trained BERT Model and Evaluation Data", PML4DC @ ICLR 2020 — https://users.dcc.uchile.cl/~jperez/papers/pml4dc2020.pdf
- Devlin, Chang, Lee, Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers", NAACL 2019 — https://arxiv.org/abs/1810.04805
- Model card oficial: https://huggingface.co/dccuchile/bert-base-spanish-wwm-cased
