# FASE 3.1 — Extracción NER

**Proyecto:** SinergIA Lab — IDP para Documentos Corporativos Colombianos
**Documento vinculante:** [PLAN_MODELADO_CRISPDM.md §3.1](PLAN_MODELADO_CRISPDM.md) — esta hoja restringe y aterriza esa sección al hardware disponible.
**Versión:** v1.1 (2026-05-16)
**Estado:** ✅ Cerrada. Ganador seleccionado por tipología; NER-4 Qwen QLoRA evaluado y descartado.

---

## 1. Objetivo

Dado un documento clasificado en una de las 4 tipologías (Cédula, RUT, Póliza, Cámara de Comercio), extraer las entidades estructurales de su esquema:

| Tipología | Entidades | # etiquetas |
|---|---|---|
| Cámara de Comercio (CC) | CC_RAZON_SOCIAL, CC_NIT, CC_NUM_MATRICULA, CC_FECHA_CONSTITUCION | 4 |
| Cédula (CED) | CED_NUMERO, CED_NOMBRE, CED_APELLIDO, CED_LUGAR_EXPEDICION, CED_FECHA_EXPEDICION | 5 |
| Póliza (POL) | POL_NUM_POLIZA, POL_ENTIDAD_ASEGURADA, POL_TOMADOR, POL_PRIMA | 4 |
| RUT | RUT_NIT, RUT_RAZON_SOCIAL, RUT_DIRECCION_PPAL, RUT_ACTIVIDAD_ECO | 4 |

**17 etiquetas en total**, sin solapamiento entre tipologías (los prefijos `CC_`/`CED_`/`POL_`/`RUT_` actúan como namespace).

---

## 2. Estado del dataset

### 2.1 Anotadores

5 anotadores asignados, **3 entregaron exports de Labelbox**:

| Anotador | NDJSON entregado | Tipologías predominantes |
|---|---|---|
| Sebas | ✅ `export_Sebas_20260513.ndjson` | Pólizas (lider) + CC |
| Camilo | ✅ `Export  project - NER_Documentos_CAMILO.ndjson` | CC + Cédulas |
| Mateo | ✅ `export_Mateo_20260512 (1).ndjson` | RUT + Cédulas |
| Caro | ⛔ pendiente | (sus 187 .txt están en `base_Caro.zip`) |
| Yera | ⛔ pendiente | (sus 188 .txt están en `base_Yera.zip`) |

**Decisión 2026-05-16:** se entrena con los 3 NDJSON ya entregados (559 documentos). Si Caro/Yera entregan después se reentrena.

### 2.2 Cobertura por entidad

Sumando los 3 NDJSON (~1,995 anotaciones totales):

```
CED_NUMERO              210     POL_ENTIDAD_ASEGURADA   103
CED_APELLIDO            205     RUT_ACTIVIDAD_ECO       100
CED_FECHA_EXPEDICION    200     POL_PRIMA                97
CED_LUGAR_EXPEDICION    199     POL_TOMADOR              96
CED_NOMBRE              198     RUT_NIT                  95
RUT_DIRECCION_PPAL      133     CC_RAZON_SOCIAL          79
RUT_RAZON_SOCIAL        126     CC_NIT                   75
                                CC_NUM_MATRICULA         73
                                CC_FECHA_CONSTITUCION    70
                                POL_NUM_POLIZA           60
```

Mediana ~100 anotaciones por entidad. `POL_NUM_POLIZA` y `CC_FECHA_CONSTITUCION` son las más escasas (cola larga).

### 2.3 Formato de origen

- **Tipo de anotación Labelbox:** `TextEntity` con `location.start`, `location.end`, `location.token`.
- **Substrato textual:** archivos `.txt` subidos a Labelbox, uno por documento. Descargados localmente en [data/raw/ner_corpus/](data/raw/ner_corpus/) (559 archivos, ~1.2 MB total) mediante [scripts/descargar_textos_labelbox.py](scripts/descargar_textos_labelbox.py).
- **Sin layout / sin bboxes por token.** Los spans son sobre texto plano.

### 2.4 Hallazgo técnico: offset Labelbox es `end` inclusivo

Verificado empíricamente sobre muestras de cada anotador: `location.token == txt[start:end+1]`, no `txt[start:end]`. Si se interpreta como slice Python estándar (`end` exclusivo), todas las entidades quedan truncadas exactamente 1 carácter al final.

Este ajuste se aplica al convertir spans → BIO en el notebook 15.

---

## 3. Candidatos NER seleccionados

### 3.1 Restricción de hardware

El equipo de trabajo es AMD Ryzen 5 4500U + 8 GB RAM, sin GPU CUDA. La Fase 2/3.0 (OCR + clasificación) se ejecutó parcialmente en Colab Free GPU; para esta iteración de NER se optó por **CPU local únicamente** para acotar dependencias y mantener reproducibilidad.

Esta restricción descarta los 3 candidatos originales del plan ([PROPUESTA_MODELOS.md §"Fase 3 — Extracción de Entidades"](PROPUESTA_MODELOS.md)):
- **N-1 spaCy + BETO transformer:** fine-tuning BETO (110M params) en CPU 8 GB → tiempos prohibitivos (~horas) y riesgo de OOM con secuencias largas.
- **N-2 Llama 3.3 + QLoRA:** requiere ≥16 GB VRAM. Inviable.
- **N-3 LayoutLMv3:** requiere bboxes por token. Las anotaciones son `TextEntity` sin coordenadas → además del hardware, faltaría reproyectar spans a tokens-con-bbox desde `corpus_ocr.csv`.

### 3.2 Set adaptado para CPU (decisión 2026-05-16)

Tres candidatos comparables que cubren las 3 familias de NER reportadas en la literatura, todos entrenables en CPU < 1 h por tipología:

| ID | Modelo | Familia | Fundamentación |
|---|---|---|---|
| **NER-1** | **Regex + diccionarios (Labeling Functions)** | Reglas | Baseline trivial. Reutiliza LFs ya implementadas en nb06-nb09. |
| **NER-2** | **CRF** (`sklearn-crfsuite`) | ML clásico con features hand-crafted | Lafferty, McCallum, Pereira, "Conditional Random Fields: Probabilistic Models for Segmenting and Labeling Sequence Data", *ICML 2001*. Baseline obligatorio en literatura NER (CoNLL-2003 winners). |
| **NER-3** | **spaCy v3 + CNN tok2vec** | Deep learning ligero (no transformer) | Honnibal & Montani, *spaCy: Industrial-Strength Natural Language Processing*. Zenodo DOI: 10.5281/zenodo.1212303. |

Esta selección replica la lógica de Fase 3.0 (C-1 clásico / C-2 transformer / C-3 multimodal) en versión CPU: regla → ML clásico → deep learning ligero.

**No descartamos N-1/N-2/N-3 del plan original** — quedan registrados como "trabajo futuro" si se obtiene acceso GPU.

### 3.3 Estrategia: un modelo por tipología

Cada uno de los 3 candidatos se entrena **4 veces** (una por tipología: CC, CED, POL, RUT) para alinear con el pipeline de inferencia: el clasificador C-1 ya entrenado en Fase 3.0 enruta cada documento entrante a la cabeza NER correspondiente.

Total: **3 candidatos × 4 tipologías = 12 entrenamientos**, todos en CPU local.

---

## 4. Métricas y protocolo

### 4.1 Métricas

- **Primaria:** F1 por entidad (exact match span-level).
- **Secundarias:** F1 macro por tipología, precision, recall, tiempo train, tiempo inferencia.
- **Reporte:** matriz F1 entidad × candidato; ganador por tipología.

### 4.2 Split

70 / 15 / 15 (train / dev / test) estratificado por tipología, `random_state=42` — consistente con Fase 3.0.

### 4.3 Reproducibilidad

- Notebook fuente: `notebooks/15_ner_dataset_construccion.ipynb` (generado por `build_notebook_15.py`).
- Datasets gold: `data/processed/ner/{cc,ced,pol,rut}/{train,dev,test}.{jsonl,spacy}`.
- Seed fija 42, exports versionados (offset inclusive ajustado, validado).

---

## 5. Roadmap de notebooks

| # | Notebook | Tarea | Estado |
|---|---|---|---|
| 15 | `15_ner_dataset_construccion.ipynb` | Parsear 3 NDJSON → ajustar offset Labelbox → alinear con .txt → split 70/15/15 → exportar JSONL | ✅ ejecutado |
| 16 | `16_ner_NER1_regex_baseline.ipynb` | NER-1 regex/LFs sobre test, F1 entity-level | ✅ ejecutado |
| 17 | `17_ner_NER2_crf.ipynb` | NER-2 CRF por tipología (4 modelos) | ✅ ejecutado |
| 18 | `18_ner_NER3_spacy_cnn.ipynb` | NER-3 spaCy v3 + CNN por tipología | ✅ ejecutado |
| 19 | `19_ner_comparativa.ipynb` | Reporte comparativo NER-1/2/3 × {CC,CED,POL,RUT}, ganadores | ✅ ejecutado |
| 20 | `20_ner_qlora_dataset.ipynb` | Convertir BIO → prompt-completion JSONL para POL (Qwen/Llama SFT) | ✅ ejecutado |
| 21 | `21_ner_qwen_qlora_colab.ipynb` | **NER-4** Qwen 2.5 3B + QLoRA en Colab Free T4 (POL) | ✅ ejecutado — descartado |

### Cómo correr nb21 en Colab

1. **Subir dataset a Drive**: copiar la carpeta `data/_to_upload/qlora_pol/` (3 archivos JSONL generados por nb20) a `MyDrive/datasets/SinergiaLab/qlora_pol/` en la cuenta `mateopolanco2@gmail.com`.
2. **Abrir nb21 en Colab**: `colab.research.google.com` → File → Upload notebook → seleccionar `notebooks/21_ner_qwen_qlora_colab.ipynb`.
3. **Activar GPU**: Runtime → Change runtime type → T4 GPU.
4. **Ejecutar Run all**. Tiempo estimado: ~30-50 min para 3 épocas sobre 79 docs.
5. **Outputs en Drive**: `nb21_resumen.json`, `predictions_test.jsonl`, `model/final/` (LoRA adapter).

Si Colab corta la sesión por cuota, checkpoints quedan en Drive cada 25 steps — al retomar, `resume_from_checkpoint=True`.

### Criterio de éxito para NER-4 — resultado y decisión

POL es el cuello de botella del benchmark CPU (spaCy+CNN max = 0.337 macro F1). Si Qwen QLoRA superaba ese 0.337 sobre el mismo test set, se escalaba a CC/CED/RUT.

**Resultado (2026-05-16):** Qwen 2.5 **3B** + QLoRA (3 épocas, 30 steps, batch efectivo 8, lr 2e-4) sobre 79 docs train de POL llegó a **macro F1 = 0.067**, muy por debajo del baseline spaCy+CNN (0.337). El modelo aprendió el formato JSON pero no el copy-task: devuelve `{}` vacío en la mayoría de docs. Causa raíz: insuficientes gradient updates + capacidad limitada del 3B + corpus pequeño.

**Decisión:** NER-4 se descarta para producción. **No se escala** a CC/CED/RUT. Queda como referencia documentada del costo/beneficio del LLM generativo en este dominio. Coherente con Kalušev & Brkljač (arXiv:2502.10582): LLMs generativos para NER legal necesitan fine-tuning específico con datos suficientes para mitigar tanto alucinación como conservadurismo trivial.

**Plan B no ejecutado** (queda registrado por trazabilidad): Qwen **7B** + seq_len=512 podría haber subido el F1 a 0.30-0.50 según expectativa, pero requería ~45 min adicionales en Colab. Se priorizó cerrar Fase 3.1 con el ganador clásico (spaCy+CNN) sobre seguir iterando NER-4.

---

## 6. Estructura de archivos

```
SinergiaLabProyecto/
├── data/raw/
│   ├── ner_annotations/         # Exports NDJSON Labelbox (PII — gitignored)
│   │   ├── Export  project - NER_Documentos_CAMILO.ndjson
│   │   ├── export_Mateo_20260512 (1).ndjson
│   │   └── export_Sebas_20260513.ndjson
│   ├── ner_corpus/              # 559 .txt descargados de Labelbox (PII — gitignored)
│   └── ner_textos_zip/          # ZIPs originales de asignación por anotador
├── data/processed/ner/          # Datasets BIO generados por nb15 (a crear)
│   ├── cc/{train,dev,test}.jsonl
│   ├── ced/{train,dev,test}.jsonl
│   ├── pol/{train,dev,test}.jsonl
│   └── rut/{train,dev,test}.jsonl
├── scripts/
│   └── descargar_textos_labelbox.py
├── notebooks/
│   ├── 15_ner_dataset_construccion.ipynb     (próximo)
│   ├── 16_ner_NER1_regex_baseline.ipynb
│   ├── 17_ner_NER2_crf.ipynb
│   ├── 18_ner_NER3_spacy_cnn.ipynb
│   └── 19_ner_comparativa.ipynb
└── FASE_3_1_NER.md              # este documento
```

---

## 7. Cierre — ganadores finales por tipología

| Tipología | Ganador | Macro F1 | Razón |
|---|---|---:|---|
| **CC** | NER-2 CRF | 0.915 | Layout fijo tabular; ML clásico con features alcanza |
| **CED** | NER-3 spaCy+CNN | 0.921 | OCR ruidoso de cédulas requiere generalización de red neuronal |
| **POL** | NER-3 spaCy+CNN | 0.337 | Variabilidad de layout + corpus pequeño; ningún candidato pasa de 0.34 |
| **RUT** | NER-3 spaCy+CNN | 0.696 | Formulario DIAN tiene anchors estables; CNN aprende patrones bien |

**Promedios macro F1:** Regex 0.431 / CRF 0.673 / spaCy+CNN **0.710** / Qwen 3B QLoRA — (solo POL: 0.067, descartado).

Para producción, se sirve **un modelo por tipología** según ganador. La tipología la decide el clasificador C-1 TF-IDF de Fase 3.0 (acc 1.000). Para POL se reconoce el techo bajo (0.337) y se sugiere usar el modelo solo como pre-anotación con revisión humana.

Ver [reports/nb19_comparativa.md](reports/nb19_comparativa.md) para el reporte completo con detalle por etiqueta.

## 8. Trabajo futuro (post-CPU)

- **NER-4 Qwen 2.5 7B + QLoRA (Colab GPU):** ⏳ en curso — nb20/nb21 listos para correr en Colab T4 sobre POL. Si supera 0.337 macro F1, escalar a CC/CED/RUT.
- **Llama 3.1 8B + QLoRA (Colab GPU):** intercambiable con Qwen 2.5 en el mismo nb21, requiere HuggingFace token + licencia Llama aceptada (~24 h de espera). Comparable contra Qwen.
- **spaCy + BETO transformer (Colab GPU):** reentrenar NER-3 con backbone BETO para comparar contra NER-3 (CNN) que ya entrenamos.
- **LayoutLMv3 (Colab GPU):** requiere puente span→token-bbox usando `bboxes_json` de `corpus_ocr.csv`. Crítico para RUT (formulario DIAN denso) y CC (estructura tabular multipágina).
- **Doble anotación + Cohen's Kappa:** los 559 docs actuales tienen 1 anotador cada uno. Para una validación inter-anotador hay que doblar la anotación sobre una muestra (50 docs por tipología).
- **Cerrar Caro/Yera:** sus 187+188 .txt en `data/raw/ner_textos_zip/` están sin anotar. Si entregan, regenerar dataset y reentrenar.
