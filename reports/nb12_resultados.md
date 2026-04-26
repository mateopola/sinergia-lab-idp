# Capítulo 12 — LayoutLMv3 multimodal: el modelo más sofisticado falla en su PROPIO documento difícil (no el mismo que BETO)

**Notebook:** [12_clasificacion_C3_layoutlmv3.ipynb](../notebooks/12_clasificacion_C3_layoutlmv3.ipynb)
**Builder:** [build_notebook_12.py](../notebooks/build_notebook_12.py)
**Fecha de ejecución:** 2026-04-26 (refactor v2.1, ver §6.2 sobre 2 fallos previos)
**Fase CRISP-DM++:** 3.0 — Clasificación de tipo de documento (candidato C-3)
**Hardware:** Colab Free Tesla T4 GPU (con 3a cuenta de Google del usuario)
**Output principal:** `models/c_layoutlmv3/{model.safetensors, metrics.json, c3_predictions.csv}`

---

## 1. El contexto — el experimento estrella del estudio comparativo

Tras C-1 (TF-IDF) llegar a 100% F1 y C-2 (BETO) a 99.14% F1 sobre el mismo split, **C-3 (LayoutLMv3) era el experimento más esperado** del estudio comparativo. La hipótesis del paper original (Huang et al. 2022, ACM MM) y de la literatura general es que un modelo multimodal con **texto + bounding boxes + imagen** debería superar a los modelos puramente textuales en tareas de Document AI:

- **FUNSD benchmark:** LayoutLMv3 reporta F1 = 90.8 vs ~85% de modelos solo texto (gap de +5-6 pp)
- **CORD benchmark:** LayoutLMv3 reporta F1 = 98.48 vs ~96% (gap de +2-3 pp)

Por eso el plan original esperaba que C-3 ganara o al menos empatara con C-2 en F1.

## 2. La hipótesis (post-resultados de C-1 y C-2)

> "C-3 LayoutLMv3 con info visual + layout debería **igualar o superar** a C-2 BETO. Si la tarea fuera trivial textualmente, el aporte del layout debería al menos resolver el 1 doc que C-2 falló."

## 3. El método

### 3.1 Mismo split estratificado que nb10/nb11 (`random_state=42`)

```
Train: 779 docs
Val  : 168 docs
Test : 168 docs
```

### 3.2 Pipeline de inputs para LayoutLMv3

LayoutLMv3 requiere **tres entradas por documento**:
1. Imagen pág 1 (procesador la reescala a 224×224)
2. Lista de palabras (words)
3. Bounding boxes normalizados a [0, 1000] por palabra

Para mantener **paridad train-inference** (decisión arquitectural §2.1.5), los words+boxes se obtienen re-ejecutando EasyOCR sobre la imagen pág 1 (no Tesseract built-in). Esto se hace en el paso pre-modelo del notebook.

### 3.3 Hiperparámetros

```python
model_name              = "microsoft/layoutlmv3-base"  # 125M parametros
max_length              = 512
batch_size              = 2     # bajo por VRAM
gradient_accumulation   = 4     # batch efectivo = 8
learning_rate           = 2e-5
n_epochs                = 5
apply_ocr               = False # usamos nuestros words/boxes via EasyOCR
fp16                    = True
```

### 3.4 Refactor v2 anti-OOM (clave para que el experimento se completara)

La v1 del notebook acumulaba 1,115 PIL Images + words + boxes en memoria simultáneamente (~12.7 GB total) → kernel restarted en Colab Free. La v2 introdujo:

1. **EasyOCR procesado en chunks de 50 docs**, guardando cada record a JSONL en Drive (memoria liberada entre chunks)
2. **Cache JSONL retomable**: si el kernel cae, al re-ejecutar salta los docs ya procesados
3. **Dataset con lazy image loading**: PIL.Image.open en `__getitem__`, no en carga del dataset

→ RAM peak baja de 9.6 GB (v1) a 5.4 GB (v2). Cabe holgado en Colab Free 12.7 GB.

## 4. Los resultados — convergencia idéntica a C-2 EN MÉTRICAS, pero diferente en errores

### 4.1 Métricas en test

```
Test Accuracy   : 0.9940
Test Macro-F1   : 0.9914
Test Weighted-F1: 0.9940
Test Loss       : 0.0490
Tiempo training : 12.53 min en T4 GPU (5 epochs)
```

**Métricas IDÉNTICAS a C-2 BETO** (también 0.9914 macro-F1, 0.9940 accuracy).

### 4.2 Per-class breakdown

```
                precision    recall  f1-score   support
CamaraComercio     1.0000    0.9643    0.9818        28   <- 1 falso negativo
        Cedula     1.0000    1.0000    1.0000        78
        Poliza     0.9677    1.0000    0.9836        30   <- 1 falso positivo
           RUT     1.0000    1.0000    1.0000        32
```

→ 1 doc de **Cámara de Comercio** clasificado como **Póliza**. El mismo PATRÓN que C-2.

### 4.3 ⚡ Hallazgo crítico — el doc fallado es DIFERENTE al de C-2

| Modelo | doc_id del único error | Predijo como |
|---|---|---|
| C-1 TF-IDF | (ninguno) | — |
| **C-2 BETO** | `7f9aa819ade69612a6cae542d5600935` | Poliza |
| **C-3 LayoutLMv3** | `d7c6fde95ee509a0bc8eba44d4efccfa` | Poliza |

→ **Son DOCS DISTINTOS.** Las debilidades de C-2 y C-3 son **ortogonales**.

¿Qué pasó en cada doc?

```
Doc difícil de C-2 (7f9aa819...) — CC real:
  C-1 acertó (proba 0.81)
  C-2 BETO ❌ confundió con Poliza
  C-3 LayoutLMv3 ✅ acertó (el layout/imagen lo salvó)

Doc difícil de C-3 (d7c6fde9...) — CC real:
  C-1 acertó (proba 0.92)
  C-2 BETO ✅ acertó (el texto puro lo identifica)
  C-3 LayoutLMv3 ❌ confundió con Poliza (layout/imagen lo confunde aquí)
```

### 4.4 ⚡⚡ Hallazgo bonus — un ENSEMBLE C-1+C-2+C-3 da 100% perfecto

Voto por mayoría simple de los 3 modelos sobre cada doc del test set:

```
Doc 7f9aa: votos = [CC, Poliza, CC]    → mayoría CC ✅
Doc d7c6f: votos = [CC, CC, Poliza]    → mayoría CC ✅
Demás 166 docs: los 3 votan igual y aciertan

Ensemble accuracy = 168/168 = 100.00% ⭐
```

## 5. Lectura crítica — ¿por qué LayoutLMv3 NO superó a BETO?

### 5.1 La hipótesis se rompe (otra vez) por la trivialidad del dominio

Esperábamos que C-3 superase a C-2 por +2-3 pp (como en CORD/FUNSD). **Pero igualó.**

Las razones, ya conocidas y consolidadas:
1. **El dominio se resuelve textualmente.** Los headers de cada doc identifican la tipología sin necesidad de mirar el layout.
2. **Las imágenes pág 1 son visualmente similares entre clases jurídicas** (CC y Pólizas son ambos formatos de doc administrativo formal). El modelo no encuentra señal visual discriminativa adicional.
3. **EasyOCR sobre imágenes pequeñas (224×224) genera bboxes de calidad limitada** — el aporte espacial es marginal.
4. **El dataset es pequeño (779 train docs)** para un modelo de 125M params multimodal. El fine-tuning no aprovecha la capacidad estructural completa.

### 5.2 El experimento ortogonalidad de errores es lo más interesante

C-2 y C-3 fallan en **docs distintos**, no en el mismo. Esto significa:
- BETO captura patrones semánticos que ESTE doc específico (`7f9aa819...`) hace ambiguos
- LayoutLMv3 captura patrones visual+layout que ESTE OTRO doc (`d7c6fde9...`) hace ambiguos
- C-1 (TF-IDF), al solo mirar palabras-clave del título, **evita ambas trampas**

**Implicación científica:** los modelos sofisticados no comparten un "doc imposible universal". Cada arquitectura tiene su propia debilidad. Para máxima robustez, un ensemble compensa.

### 5.3 La ironía estadística — estamos en el ruido

```
C-1 5-fold CV: Macro-F1 = 0.9960 ± 0.0041
C-2 test     : Macro-F1 = 0.9914 (cae en el rango de C-1)
C-3 test     : Macro-F1 = 0.9914 (cae en el rango de C-1)
```

Las diferencias son **estadísticamente indistinguibles**. Si re-ejecutáramos con otro `random_state`, los rankings podrían invertirse o emparejarse.

### 5.4 El veredicto operativo — C-1 sigue ganando definitivamente

Comparativa cabeza-a-cabeza-a-cabeza:

| Métrica | C-1 TF-IDF | C-2 BETO | C-3 LayoutLMv3 | Ganador |
|---|---|---|---|---|
| Test Macro-F1 | **1.0000** | 0.9914 | 0.9914 | **C-1** (no significativo) |
| Tiempo train | **2.92 s** | 94 s | 753 s | **C-1** (256× más rápido) |
| Tamaño modelo | **<10 MB** | 440 MB | 503 MB | **C-1** (50× más liviano) |
| VRAM inferencia | **0 (CPU)** | ~2 GB | ~4 GB | **C-1** (sin GPU) |
| Latencia inferencia | **<10 ms** | ~50 ms | ~200 ms | **C-1** (20× más rápido) |
| Interpretabilidad | **Top features** | Atención (opaca) | Atención (opaca) | **C-1** |

→ **C-1 gana en 6/6 ejes.** La conclusión del estudio es definitiva.

### 5.5 La conclusión académica del trio comparativo

> "Para clasificación de tipo de documento sobre el corpus SECOP de 4 tipologías colombianas (Cédula, RUT, Póliza, Cámara de Comercio), los tres candidatos comparados — TF-IDF + Regresión Logística (C-1), BETO fine-tuned (C-2), y LayoutLMv3 fine-tuned (C-3) — convergen al techo del dominio (~99-100% Macro-F1) en test, sin diferencias estadísticamente significativas entre ellos.
>
> **Hallazgo central:** la complejidad arquitectural adicional (semántica con BETO, multimodal con LayoutLMv3) **no produce ganancia de F1** sobre el baseline trivial, contrariamente a lo reportado en la literatura general (RVL-CDIP, FUNSD, CORD). Esto refleja la **especificidad del dominio**: documentos administrativos colombianos altamente estandarizados con headers auto-identificadores en página 1.
>
> **Hallazgo metodológico:** las debilidades de C-2 y C-3 son **ortogonales** — fallan en docs distintos. Un ensemble por mayoría simple de los 3 modelos alcanza 100% perfecto en test, validando la diversidad de errores entre arquitecturas. Sin embargo, este ensemble no se justifica para producción dado que C-1 solo ya alcanza 100%.
>
> **Implicación práctica:** para producción de IDP en este dominio, **C-1 TF-IDF + Regresión Logística es estrictamente preferible** por dominar todos los ejes secundarios (256× más rápido en entrenamiento, 50× más liviano, 20× menor latencia, sin requerir GPU, e interpretable). La inversión en infraestructura para BETO o LayoutLMv3 no se justifica para esta tarea específica."

## 6. Anomalías

### 6.1 Las debilidades de C-2 y C-3 NO coinciden — invalida hipótesis previa

Mi análisis previo (en el chat con el usuario) asumía que C-2 y C-3 fallarían en el MISMO doc, lo cual habría implicado que ese doc era "estructuralmente imposible". Los datos lo desmienten — son docs distintos. **Cada arquitectura tiene su propio sesgo**, no un sesgo compartido del corpus.

### 6.2 El experimento C-3 requirió 2 fallos para completarse

| Intento | Falló por | Tiempo perdido |
|---|---|---|
| **v1** (notebook original) | OOM en EasyOCR step (acumuló 1,115 PIL Images en RAM) | ~30 min |
| **v2 primer intento** | `ValueError: LayoutLMv3ForSequenceClassification does not support gradient_checkpointing` | ~5 min (falló inmediato) |
| **v2.1** (sin gradient_checkpointing) | ✅ Exitoso | 12.5 min training |

**Lección operativa:** el cache JSONL en Drive (introducido en v2) salvó el experimento. Sin él, cada fallo hubiera obligado a re-ejecutar 60 min de EasyOCR. Con cache, los re-intentos costaron solo 30 segundos de skip.

### 6.3 El usuario consumió 3 cuentas de Google para este experimento

Cuotas Colab Free se agotaron en orden:
1. `mateopolanco2@gmail.com` — sesión OCR + sesión nb12 v1
2. (segunda cuenta del usuario, vía Drive shortcut) — re-intento nb12 v2
3. `polancorodriguezmateo@gmail.com` — corrida exitosa nb12 v2.1

Esta táctica (multi-cuenta + Drive sharing) está documentada en `memory/colab_drive_setup.md`.

### 6.4 El metrics.json reporta `gradient_checkpointing: true` aunque NO se aplicó

En v2.1 removimos la línea `model.gradient_checkpointing_enable()` por el ValueError, pero el dict `summary` del notebook quedó con la metadata original `'gradient_checkpointing': True`. Esto es metadata mal puesta, no afecta nada del experimento. Para ser estrictos: **el modelo entrenado NO tiene gradient checkpointing aplicado**.

### 6.5 Carpeta de modelo nombrada inconsistentemente

El usuario guardó el modelo en `models/c_layoutlmv3/` (sin el dígito "3"), mientras que C-1 está en `c1_tfidf/` y C-2 en `c2_beto/`. Para consistencia futura podría renombrarse a `c3_layoutlmv3/`. No es bloqueante.

### 6.6 Mismo gap de class_weights ya documentado en nb11 (sec 6.4)

El Trainer de HuggingFace usado en nb12 también NO aplica class weights (mismo gap que nb11). Como el desbalance de clases no es severo y los resultados son sólidos, no se considera blocker. Documentado para honestidad metodológica.

## 7. Qué sigue

### 7.1 Cierre formal de Fase 3.0 — Clasificación

Con los 3 candidatos ejecutados, Fase 3.0 está **completa**. Reporte comparativo final consolidado en [reports/clasificacion_comparativa_C1_C2_C3.md](clasificacion_comparativa_C1_C2_C3.md).

### 7.2 Decisión arquitectural cerrada

Modelo seleccionado para producción: **C-1 TF-IDF + Regresión Logística**, con base en:
- Empate técnico de F1 con los otros 2 candidatos (no significativo)
- Dominio absoluto en los 5 ejes secundarios (costo, latencia, tamaño, hardware, interpretabilidad)

### 7.3 Retomar Fase 2.2 (NER en Label Studio)

Las 516 pre-anotaciones generadas hace tiempo (nb06-nb09) siguen intactas en `data/processed/*_preanotaciones_labelstudio.json`. El siguiente paso del proyecto es retomar esa fase: instalar Label Studio, importar las 4 tareas, revisar humanamente las pre-anotaciones, exportar el dataset corregido para entrenar los modelos NER (N-1, N-2, N-3) en Fase 3.1.

Ver [LABEL_STUDIO_SETUP.md](../LABEL_STUDIO_SETUP.md) y [CRITERIOS_ANOTACION.md](../CRITERIOS_ANOTACION.md) para retomar.

### 7.4 (Opcional) Experimento de robustez Opción B

Si en algún momento se requiere fortalecer el comparativo académico, queda como pendiente:
- `nb10b_clasificacion_C1_ablacion_lexical.ipynb` (eliminar términos auto-identificadores para crear margen de comparación)
- Re-correr C-2 y C-3 con esa ablación → ver si recuperan ventaja sobre C-1

No urgente, pero queda como vía de fortalecimiento metodológico.

## 8. Referencias

- [_nb_outputs/12_clasificacion_C3_layoutlmv3.txt](../_nb_outputs/12_clasificacion_C3_layoutlmv3.txt) — outputs literales
- [reports/nb10_resultados.md](nb10_resultados.md) — capítulo C-1 (mismo split)
- [reports/nb11_resultados.md](nb11_resultados.md) — capítulo C-2 (mismo split)
- [reports/clasificacion_comparativa_C1_C2_C3.md](clasificacion_comparativa_C1_C2_C3.md) — reporte final consolidado
- Huang, Lv, Cui, Lu, Wei, "LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking", ACM MM 2022 — https://arxiv.org/abs/2204.08387
- Microsoft official repo: https://github.com/microsoft/unilm/tree/master/layoutlmv3
- HuggingFace model card: https://huggingface.co/microsoft/layoutlmv3-base
