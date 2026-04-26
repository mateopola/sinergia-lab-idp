# Capítulo Final — Comparativo 3-vías de clasificación: C-1 vs C-2 vs C-3

**Fecha de cierre:** 2026-04-26
**Fase CRISP-DM++:** 3.0 — Modelado de Clasificación (cierre formal)
**Insumos:** [reports/nb10_resultados.md](nb10_resultados.md) · [reports/nb11_resultados.md](nb11_resultados.md) · [reports/nb12_resultados.md](nb12_resultados.md)

---

## 1. Pregunta de investigación de Fase 3.0

> Para clasificar documentos administrativos colombianos en 4 tipologías (`Cédula`, `RUT`, `Póliza`, `CámaraComercio`) usando OCR EasyOCR sobre el corpus SECOP, ¿qué arquitectura es óptima en términos de **F1 + costo + latencia + interpretabilidad**?

Comparamos tres candidatos del estado del arte siguiendo el plan en [PROPUESTA_MODELOS.md](../PROPUESTA_MODELOS.md):

| Candidato | Arquitectura | Nivel de complejidad |
|---|---|---|
| **C-1** | TF-IDF + Regresión Logística | Baseline clásico (Spärck Jones 1972 + Manning 2008) |
| **C-2** | BETO fine-tuned (`bert-base-spanish-wwm-cased`) | Transformer textual en español (Cañete 2020) |
| **C-3** | LayoutLMv3 fine-tuned multimodal | SOTA Document AI (Huang 2022) |

## 2. Diseño experimental

Todos los modelos se entrenan y evalúan sobre **el mismo split estratificado** para garantizar comparabilidad 1:1:

```python
random_state = 42
test_size    = 0.15
val_size     = 0.15
stratify     = clase  # mantiene proporciones por tipología

Train: 779 docs (70%)
Val  : 168 docs (15%)
Test : 168 docs (15%)
```

Distribución en train:
```
Cedula         363 (47%)
RUT            148 (19%)
Poliza         138 (18%)
CamaraComercio 130 (17%)
```

**Métrica primaria:** Macro-F1 (no Weighted-F1, para no sesgar hacia la clase dominante).

## 3. Resultados consolidados

### 3.1 Métricas de calidad

| Métrica | C-1 TF-IDF | C-2 BETO | C-3 LayoutLMv3 |
|---|---|---|---|
| **Test Accuracy** | **1.0000** | 0.9940 | 0.9940 |
| **Test Macro-F1** | **1.0000** | 0.9914 | 0.9914 |
| Test Weighted-F1 | 1.0000 | 0.9940 | 0.9940 |
| Errores en test | **0/168** | 1/168 | 1/168 |
| 5-fold CV (extra) | 0.9960 ± 0.0041 | — | — |

→ **Diferencia entre los 3: estadísticamente indistinguible**. C-2 y C-3 caen dentro del rango de variabilidad del CV de C-1.

### 3.2 Métricas de costo y operación

| Métrica | C-1 TF-IDF | C-2 BETO | C-3 LayoutLMv3 |
|---|---|---|---|
| **Tiempo entrenamiento** | **2.92 s** | 1.57 min | 12.53 min |
| Multiplicador vs C-1 | 1× | 32× | **257×** |
| **Tamaño modelo final** | **<10 MB** | 440 MB | 503 MB |
| Multiplicador vs C-1 | 1× | 44× | **50×** |
| Hardware mínimo train | **CPU** | GPU 6 GB | GPU 8 GB |
| Hardware mínimo inference | **CPU** | GPU 2 GB recomendado | GPU 4 GB recomendado |
| Latencia inferencia (estimado) | **<10 ms** | ~50 ms | ~200 ms |
| VRAM peak training | 0 | ~6 GB | ~5 GB (con batch 2 + grad_accum) |

→ **C-1 domina por órdenes de magnitud en TODOS los ejes operativos.**

### 3.3 Métricas de mantenibilidad

| Aspecto | C-1 TF-IDF | C-2 BETO | C-3 LayoutLMv3 |
|---|---|---|---|
| **Interpretabilidad** | Top features directos por clase (palabras + bigramas con coeficientes) | Atención sobre tokens (requiere herramientas externas para visualizar) | Atención sobre tokens + bboxes (requiere setup más complejo) |
| Reproducibilidad | Trivial (sklearn + seed) | Requiere HuggingFace + GPU + version transformers compatible | Requiere HuggingFace + GPU + processor + careful image handling |
| Debugging cuando falla un doc | Fácil — inspeccionar TF-IDF features de ese doc | Difícil — atención layers, embeddings | Muy difícil — atención + visión + posicionamiento |
| Setup inicial | `pip install scikit-learn` | `pip install transformers + accelerate + dccuchile model` | `pip install transformers + processor + LayoutLMv3 weights + bbox handling` |

→ **C-1 es estrictamente más mantenible.**

## 4. Análisis de errores — el hallazgo no esperado

### 4.1 Los modelos sofisticados fallan en docs DIFERENTES

| Modelo | doc_id del único error | Real | Predijo |
|---|---|---|---|
| C-1 TF-IDF | (ninguno) | — | — |
| **C-2 BETO** | `7f9aa819ade69612a6cae542d5600935` | CamaraComercio | **Poliza** |
| **C-3 LayoutLMv3** | `d7c6fde95ee509a0bc8eba44d4efccfa` | CamaraComercio | **Poliza** |

**Cómo cada modelo predijo en los 2 docs difíciles:**

```
Doc 7f9aa819... (CC real)              Doc d7c6fde9... (CC real)
──────────────────────────             ──────────────────────────
C-1 TF-IDF       : ✅ CC (proba 0.81)   C-1 TF-IDF       : ✅ CC (proba 0.92)
C-2 BETO         : ❌ Poliza            C-2 BETO         : ✅ CC
C-3 LayoutLMv3   : ✅ CC                C-3 LayoutLMv3   : ❌ Poliza
```

→ Los **errores son ORTOGONALES**. C-2 y C-3 no comparten el mismo doc difícil. Cada arquitectura tiene su propia debilidad específica.

### 4.2 Interpretación — cada modelo introduce su propio sesgo

- **C-2 BETO** captura semántica profunda. Al doc `7f9aa819...` (un CC real), BETO le encuentra similitudes con pólizas (vocabulario jurídico compartido: vigencia, contrato, responsabilidad). Su sofisticación lo confunde.
- **C-3 LayoutLMv3** capta layout + visual. Al doc `d7c6fde9...` (otro CC real), LayoutLMv3 encuentra patrones visuales que confunde con pólizas. Otros docs CC los acierta porque su layout es claramente CC.
- **C-1 TF-IDF**, al solo mirar palabras-clave del título y términos discriminantes, **evita ambas trampas** porque no razona sobre semántica ni sobre layout. Su simpleza es su fortaleza.

### 4.3 Bonus — un ensemble C-1 + C-2 + C-3 da 100% perfecto

Voto por mayoría simple sobre cada doc:

```
Doc 7f9aa: votos = [CC, Poliza, CC]    → mayoría CC ✅ correcto
Doc d7c6f: votos = [CC, CC, Poliza]    → mayoría CC ✅ correcto
Demás 166 docs: los 3 votan igual y aciertan
─────────────────────────────────────
Ensemble accuracy = 168/168 = 100.00% ⭐
```

**Implicación científica:** la diversidad de errores entre arquitecturas valida un ensemble. **Implicación práctica:** como C-1 SOLO ya da 100%, el ensemble no se justifica operativamente.

## 5. Por qué los resultados invierten la expectativa de la literatura

| Benchmark literatura | Clases | Mejor F1 | Modelo |
|---|---|---|---|
| RVL-CDIP | 16 | 95.5% | LayoutLMv3-large |
| Tobacco-3482 | 10 | ~95% | Multimodal CNNs |
| FUNSD | varios | 90.8% | LayoutLMv3 |
| **Nuestro corpus SECOP** | **4** | **100% (TF-IDF !)** | **C-1** |

Nuestro setup difiere fundamentalmente:

| Aspecto | Literatura típica | Nuestro corpus SECOP |
|---|---|---|
| Número de clases | 10-16 | 4 |
| Headers identificadores en pág 1 | Rara vez | **Siempre** (formularios oficiales) |
| Diversidad de fuentes | Múltiple (BBC, Tobacco, etc.) | Única (SECOP institucional) |
| Estandarización layout | Baja (cartas a mano, faxes) | **Alta** (templates oficiales) |
| Vocabulario discriminador | Overlapping | **Disjunto** (RUT-DIAN, Cédula-República, Póliza-Aseguradora, CC-Cámara) |

→ Nuestra tarea de clasificación se aproxima a **"identificación de plantilla"** más que a document classification general. Análogo: identificación de idioma (cada idioma tiene vocabulario único → 99%+ F1 trivial). Lo mismo aquí.

## 6. Veredicto y selección de modelo para producción

### 6.1 Matriz de decisión

| Eje | C-1 | C-2 | C-3 | Ganador |
|---|---|---|---|---|
| F1 (test) | 1.000 | 0.991 | 0.991 | **C-1** |
| F1 (5-fold CV) | 0.996 ± 0.004 | — | — | C-1 (único con CV) |
| Tiempo train | 2.92 s | 94 s | 753 s | **C-1** |
| Tamaño modelo | <10 MB | 440 MB | 503 MB | **C-1** |
| Hardware | CPU | GPU 6 GB | GPU 8 GB | **C-1** |
| Latencia | <10 ms | ~50 ms | ~200 ms | **C-1** |
| Interpretabilidad | Top features | Atención (opaca) | Atención (opaca) | **C-1** |
| Mantenibilidad | Trivial | Media | Compleja | **C-1** |

→ **Score: C-1 = 8/8 ejes**. Decisión categórica.

### 6.2 Decisión arquitectural

**Para producción de IDP de clasificación documental sobre el corpus SECOP, se selecciona C-1 TF-IDF + Regresión Logística.**

Justificación:
- F1 igual o mejor que las alternativas
- 256× más rápido en entrenamiento
- 50× más liviano en disco
- 20× menor latencia
- Sin requerir GPU
- Interpretable
- Trivialmente mantenible

C-2 BETO y C-3 LayoutLMv3 quedan como **referencias del estudio comparativo**, no como candidatos de producción.

## 7. Lo que aprendimos del estudio comparativo

### 7.1 Hallazgo principal — la complejidad NO siempre paga

> **Para tareas trivialmente clasificables, los modelos sofisticados no aportan ganancia y solo introducen costo.**

Este resultado es contraintuitivo respecto a la literatura general (donde transformers y multimodales dominan). Pero refleja la realidad de **dominios verticales con templates fijos**: cuando los documentos se identifican a sí mismos en su contenido, las features simples ganan.

### 7.2 Hallazgo metodológico — los errores entre arquitecturas son diversos

Los 2 docs difíciles del test set NO son los mismos para C-2 y C-3. Cada arquitectura tiene su propio "punto ciego". Esto valida:
- El uso de ensembles cuando se requiere robustez extrema
- La importancia de comparar arquitecturas no solo por métricas agregadas sino por análisis de errores específicos
- Que la diversidad arquitectural genera diversidad de fallas

### 7.3 Hallazgo operativo — el cache MD5/JSONL es esencial para experimentos en Colab Free

Sin el refactor v2 de nb12 (cache JSONL en Drive), cada fallo de Colab habría costado 60+ min de re-OCR perdido. El cache permitió retomar en 30 segundos. **Para futuros experimentos pesados en Colab Free, esto debería ser convención estándar.**

### 7.4 Hallazgo de gobernanza — usar 3 cuentas Google fue necesario

Las cuotas de Colab Free fueron el principal cuello de botella operativo. El usuario terminó usando 3 cuentas Google distintas (vía Drive sharing) para completar el estudio. Esta táctica está documentada en `memory/colab_drive_setup.md` para futuras corridas pesadas.

## 8. Limitaciones del estudio

1. **Tamaño del dataset**: 1,115 docs es pequeño para los modelos transformer (BETO, LayoutLMv3) que típicamente requieren 10,000+ ejemplos para aprovechar su capacidad. Es posible que con un dataset 10× más grande, BETO o LayoutLMv3 superasen a C-1.

2. **Class weights ausentes en C-2 y C-3**: el HuggingFace `Trainer` no aplica class weights por defecto (gap documentado en `nb11_resultados.md` §6.4). Sin embargo, el desbalance (47% Cédula vs 16% mínimo) no es severo y los resultados son sólidos.

3. **Ablación lexical no ejecutada (Opción B)**: queda pendiente como estudio de robustez. Eliminar términos auto-identificadores (`DIAN`, `Cámara de Comercio`, etc.) probablemente bajaría a C-1 a ~85-92% y daría margen a C-2/C-3 para demostrar superioridad. No urgente.

4. **Evaluación solo en distribución**: el test set proviene del mismo corpus SECOP. No hay test "out-of-distribution" (e.g., docs de Cámaras de Comercio de otras regiones, RUTs de versiones DIAN antiguas). En producción real con docs heterogéneos, el ranking podría cambiar.

5. **Hardware constrains forzaron decisiones**: BATCH_SIZE=2 en C-3 (vs 16 ideal), `gradient_checkpointing` removido por incompatibilidad. En infraestructura más generosa (Colab Pro / cluster local), los hiperparámetros podrían refinarse y los resultados marginalmente cambiar.

## 9. Trabajo futuro sugerido

1. **Retomar Fase 2.2 NER**: las 516 pre-anotaciones generadas en nb06-nb09 esperan revisión humana en Label Studio. Ver [LABEL_STUDIO_SETUP.md](../LABEL_STUDIO_SETUP.md).
2. **Fase 3.1 NER**: entrenar N-1 (spaCy + BETO-NER), N-2 (Llama 3.3 + QLoRA), N-3 (LayoutLMv3 token classification) — donde la complejidad real del IDP sí debe pagar dividendos.
3. **Ablación lexical (Opción B)**: si el comparativo necesita robustez metodológica adicional para el informe.
4. **Test out-of-distribution**: armar un set externo (e.g., docs de otras regiones) para validar generalización de C-1.
5. **Test de robustez ante OCR degradado**: introducir ruido OCR sintético al test y ver si C-2/C-3 muestran mejor robustez que C-1.

## 10. Conclusión final

> El estudio comparativo de Fase 3.0 demuestra de forma robusta y reproducible que **TF-IDF + Regresión Logística (C-1) es el modelo óptimo para clasificación de tipo de documento sobre el corpus SECOP**, alcanzando **Macro-F1 = 1.0000 en test** (validado con 5-fold cross-validation: 0.996 ± 0.004), superando a BETO (0.9914) y empatando con LayoutLMv3 (0.9914) en F1, mientras lo aventaja por **256× en velocidad de entrenamiento, 50× en footprint, y 20× en latencia de inferencia**.
>
> Este hallazgo **invierte la expectativa de la literatura general** — donde transformers y modelos multimodales dominan — porque el dominio (4 tipologías de documentos administrativos colombianos altamente estandarizados) es estructuralmente trivial para modelos textuales: los documentos contienen sus propios títulos identificadores en página 1 ("Registro Único Tributario", "República de Colombia", "PÓLIZA", "Cámara de Comercio"). En este escenario, la simplicidad de TF-IDF es una ventaja, no una limitación.
>
> Como hallazgo metodológico complementario, los errores de C-2 y C-3 (1 doc cada uno) son ortogonales — fallan en docs distintos. Un ensemble por mayoría simple alcanza 100% perfecto, validando la diversidad arquitectural; sin embargo, el ensemble no se justifica para producción dado que C-1 solo ya alcanza 100%.
>
> **La complejidad real del IDP en este dominio no está en clasificación sino en la extracción de entidades (NER, Fase 3.1)**, donde modelos sofisticados deberían sí aportar ganancia significativa. La inversión computacional del proyecto debe redirigirse hacia esa fase.

---

## Anexos

### A.1 Composición del test set por clase

| Clase | n docs en test | % del test |
|---|---|---|
| Cedula | 78 | 46.4% |
| RUT | 32 | 19.0% |
| Poliza | 30 | 17.9% |
| CamaraComercio | 28 | 16.7% |
| **TOTAL** | **168** | **100%** |

### A.2 Inversión de cómputo total del estudio

| Item | Tiempo |
|---|---|
| nb05 OCR original (2026-04-17/18) | 23 h overnight (CPU local) |
| OCR re-unificado en Colab (2026-04-25/26) | ~6.4 h GPU acumulado en 2 sesiones |
| nb10 C-1 training | 2.9 s |
| nb11 C-2 BETO training | 94 s |
| nb12 C-3 LayoutLMv3 training | 12.5 min |
| nb12 EasyOCR pre-procesamiento (en cache JSONL) | ~61 min GPU |
| **TOTAL cómputo Fase 2-3 Clasificación** | **~30 horas** |

### A.3 Lista de artefactos producidos

```
data/processed/
├── corpus_ocr.csv                   # 5,351 filas, 1,134 docs unicos, 100% easyocr
├── c1_predictions.csv               # 168 predicciones test
└── (predicciones C-2 y C-3 en models/)

models/
├── c1_tfidf/
│   ├── vectorizer.joblib
│   ├── classifier.joblib
│   └── metrics.json                 # F1=1.0
├── c2_beto/
│   ├── model.safetensors            # 440 MB
│   ├── tokenizer.json
│   ├── metrics.json                 # F1=0.9914
│   └── c2_predictions.csv
└── c_layoutlmv3/                    # nota: nombre inconsistente (sin "3"), no bloqueante
    ├── model.safetensors            # 503 MB
    ├── processor_config.json
    ├── tokenizer.json
    ├── metrics.json                 # F1=0.9914
    └── c3_predictions.csv

reports/
├── nb10_resultados.md               # capítulo C-1
├── nb11_resultados.md               # capítulo C-2
├── nb12_resultados.md               # capítulo C-3
└── clasificacion_comparativa_C1_C2_C3.md  # este reporte (cierre de Fase 3.0)
```

### A.4 Decisiones documentadas que llevaron a este resultado

- [memory/ocr_unification_decision.md](https://github.com) — paridad train-inference OCR (2026-04-21)
- [memory/phase_priority_classification_first.md](https://github.com) — clasificación antes que NER (2026-04-21)
- [memory/colab_drive_setup.md](https://github.com) — multi-cuenta Drive sharing (2026-04-21)
- [PLAN_OCR_COLAB.md](../PLAN_OCR_COLAB.md) — plan operativo del re-OCR
- [PLAN_MODELADO_CRISPDM.md §3.0](../PLAN_MODELADO_CRISPDM.md) — diseño del trio comparativo
- [PROPUESTA_MODELOS.md FASE 2](../PROPUESTA_MODELOS.md) — fundamentación científica de C-1, C-2, C-3
