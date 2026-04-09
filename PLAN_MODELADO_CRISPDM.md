# PLAN MAESTRO DE MODELADO — SinergIA Lab
## Hoja de Ruta Técnica CRISP-DM++ (Enfoque: Modelado y Testeo)
**Proyecto:** IDP para Documentos Colombianos SECOP | PUJ Especialización IA 2026  
**Metodología:** CRISP-DM++ + Scrum + Design Thinking  
**Alcance de esta hoja de ruta:** Desarrollo, Fine-Tuning y Evaluación del Modelo. Excluye API, backend y HITL.

---

## FASE 1 — COMPRENSIÓN DE LOS DATOS (Business & Data Understanding)

### 1.1 Análisis Exploratorio del Corpus (EDA)
- [x] Inventariar los 1,000 documentos SECOP por tipología: Cédula (334), RUT (235), Pólizas (219), Cámara de Comercio (212) *(+ 14 OTROS = 1,014 total)*
- [x] Registrar formatos de entrada presentes: PDF nativo, PDF escaneado *(fig01_inventario.png — todos son PDF)*
- [x] Calcular distribución de páginas por documento *(columna `n_pages` en quality_report_completo.csv)*
- [ ] Identificar variantes regionales/institucionales dentro de cada tipología *(movida a inicio de Fase 2 — requiere revisión visual humana, no automatizable con EDA estadístico)*
- [x] Detectar documentos duplicados con hash MD5 *(columna `is_duplicate`; similitud coseno por embeddings → movida a Fase 2 §2.1)*

### 1.2 Textometría y Análisis de Densidad Textual
- [x] Ejecutar **EasyOCR** como OCR baseline *(reemplaza PaddleOCR — Python 3.12 incompatible. Decisión v1.2)*
  - *Pipeline corregido: PyMuPDF primario para digitales + EasyOCR fallback solo para escaneados (run_fase1.py v1.4)*
- [x] Calcular densidad textual real con bounding boxes *(pymupdf_text_density para digitales, ocr_text_density para escaneados — fig04)*
- [x] Medir: tokens por página, caracteres, densidad *(53 métricas textstat + tokens_bpe_ajustado en quality_report_completo.csv)*
- [x] Calcular frecuencia de entidades objetivo *(columnas ent_cedula, ent_nit, ent_fecha, ent_monto, ent_email, ent_ciiu, ent_matricula, ent_poliza_num)*
- [ ] Construir vocabulario específico por dominio *(movida a Fase 2 — se construye después de definir entidades objetivo, no antes)*
- [x] Identificar documentos digitales vs. escaneados *(columna `es_escaneado`: 423/1,014 = 42% escaneados)*

### 1.3 Evaluación de Calidad Visual
- [x] Medir niveles de iluminación promedio con OpenCV *(columna `brightness` — umbral calibrado: HIGH=253, LOW=60)*
- [x] Calcular contraste *(columna `contrast` — umbral LOW=20)*
- [x] Detectar borrosidad con varianza del operador Laplaciano *(columna `blur_score` — umbral=100)*
- [ ] Identificar rotaciones y correcciones necesarias *(movida a Fase 2 §2.1 — pertenece al pipeline de preprocesamiento, no al EDA)*
- [x] Clasificar cada documento en: [APTO / REQUIERE_PREPROCESAMIENTO / DESCARTADO] *(columna `quality_label`)*
- [x] Generar reporte de calidad visual *(quality_report_completo.csv 1,014 × 57 cols + fig02_scatter_iluminacion_blur.png)*

### 1.4 Entregables de Fase 1
- [x] Notebook `01_analisis_descriptivo_secop.ipynb` ejecutado completamente *(31 celdas, celda 31 = síntesis de hallazgos)*
- [~] ~~Reporte HTML de EDA con gráficos exportado~~ *(eliminada — el notebook .ipynb + 10 figuras PNG + CSV cumplen la función con mayor detalle)*
- [x] CSV `data/processed/quality_report_completo.csv` con metadatos de calidad *(1,014 × 57 cols — incluye textstat, BPE, escaneados)*
- [x] Decisión documentada: qué documentos pasan al pipeline *(fase1_decisiones.json — estrategias de chunking por tipología)*

### 1.5 Actividades Adicionales Ejecutadas (no estaban en plan original)
> *Estas tareas emergieron del análisis del corpus real y son parte del registro de trabajo para el documento final.*

- [x] **Análisis de legibilidad textstat completo en español** *(30 métricas: Flesch, Szigriszt-Pazos, Fernández-Huerta, Crawford, Gunning Fog, etc.)*
- [x] **ANOVA entre tipologías** *(confirma diferencias estadísticamente significativas entre categorías — fig08_anova.png)*
- [x] **Detección de patrones de entidades con regex** *(ent_cedula, ent_nit, ent_fecha, ent_monto, ent_email, ent_ciiu, ent_matricula, ent_poliza_num)*
- [x] **Enriquecimiento BPE post-EDA** *(script enriquecer_reporte.py — agrega columnas sin re-procesar documentos)*
- [x] **Corrección de umbrales de calidad visual** *(calibrados sobre corpus real: BRIGHTNESS_HIGH=253 para PDFs digitales blancos)*
- [x] **Versiones del pipeline documentadas en CHANGELOG** *(v1.0 → v1.4: cada decisión técnica trazable)*
- [x] **Repositorio GitHub** *(mateopola/sinergia-lab-idp — 4 commits, datos PII excluidos por .gitignore)*

---

## FASE 2 — PREPARACIÓN DE LOS DATOS (Data Preparation)

### 2.0 Tareas trasladadas desde Fase 1 (completar antes de preprocesar)
- [x] **Variantes regionales/institucionales:** revisión visual completada (2026-04-08). Hallazgos:
  - **Cédula:** formato único — mismo layout en todo el corpus. Solo varía calidad de imagen.
  - **RUT:** formato único — plantilla DIAN estándar. Solo varía el contenido de las casillas.
  - **Cámara de Comercio:** formato único por cámara, pero **algunos documentos tienen portada** (página 1 = imagen corporativa sin datos). El pipeline debe detectar y saltar portadas antes de extraer texto.
  - **Pólizas:** formato variable por aseguradora. Los 80 docs de anotación deben distribuirse proporcionalmente entre aseguradoras presentes en el corpus para cubrir la variabilidad de layout.
- [x] **Near-duplicates por TF-IDF coseno (Notebook 02):** ejecutado sobre corpus completo. Hallazgos:
  - **Cédula:** 1 par exacto (sim=1.0) → duplicado real, eliminar antes del split.
  - **RUT:** 1 par exacto real (`01 RUT_1.pdf` == `01 RUT_2.pdf`) + ~30 pares con sim 0.90-0.98 → **falsos positivos por estructura DIAN compartida** (plantilla compartida — TF-IDF ve similitud estructural, no de contenido). **Umbral ajustado a ≥0.99 para RUT**, ≥0.90 para las demás tipologías.
  - **Póliza y CC:** sin duplicados detectados a umbral 0.90.
- [x] **Vocabulario por dominio (Notebook 02):** top-30 términos extraídos por tipología. Hallazgos:
  - **RUT — anomalía crítica:** términos dominantes son `orgánicas` (13,879), `lata` (12,437), `frasco` (12,435), `congeladas`, `secas`. Corresponden a **clasificaciones CIIU del formulario DIAN** impresas completas (lista de actividades económicas). No es OCR noise — es artefacto de diseño del formulario. La sección CIIU contamina embeddings. **Decisión:** filtrar sección CIIU antes de generar embeddings para fine-tuning.
  - **Cédula — requiere investigación:** términos de CC (`expedición`, `certificado`, `comercio`, `cámara`) aparecen con alta frecuencia. Hipótesis: el texto proviene de las carátulas de expediente SECOP detectadas como portada (15% de muestra). Estas carátulas contienen membrete institucional con términos de cámara/comercio. **Acción pendiente:** inspeccionar texto de las 3 carátulas de Cédula detectadas para confirmar fuente del ruido.
  - **Póliza y CC:** vocabulario limpio y coherente. Sin anomalías.

### 2.1 Pipeline de Preprocesamiento Visual (OpenCV)
> **Hallazgo v1.6:** algunos documentos tienen portada (pág. 1 = imagen corporativa sin datos). Confirmado en CC; puede aparecer en cualquier tipología. La detección de portada es el primer paso del pipeline, antes de cualquier extracción.

- [x] **Detección de portada (todas las tipologías, Notebook 02):** implementada y validada. Resultados e inspección posterior:
  - **Cédula: DESACTIVADA.** Las 3 "portadas" detectadas son falsos positivos — cédulas escaneadas normales con página 1 = imagen (0 texto), que cumplen el criterio `lexicon < 50 AND blocks < 5` por ser imágenes, no por ser portadas. Con 93% del corpus escaneado, el detector dispara en casi todo el corpus. Excepción detectada: `4. DOCUMENTO DE IDENTIDAD RL.pdf` (6 págs, portada textual real de expediente), pero es un caso aislado. Decisión: **no aplicar detección de portada a Cédulas — procesar todas las páginas por OCR directamente**.
  - **Vocabulario CC en Cédulas:** origen probable = documentos mal clasificados en carpeta CEDULA del SECOP (ej. `Ponderable 3.1 Copia CC Socios - Autentica.pdf`). No es ruido de portadas.
  - RUT: 0/20 (0%) — plantilla DIAN siempre inicia con datos. Correcto.
  - Póliza: 5/20 (25%) — portadas corporativas de aseguradoras. Detector válido y útil.
  - Cámara de Comercio: 2/20 (10%) — algunas cámaras incluyen página de presentación. Detector válido.
- [x] Implementar función `deskew()`: corrección de rotación con minAreaRect *(Notebook 02, Sección 3)*
- [x] Implementar función `denoise()`: filtro gaussiano + Non-Local Means para escaneados ruidosos *(Notebook 02, Sección 3)*
- [x] Implementar función `binarize()`: umbralización adaptativa Otsu *(Notebook 02, Sección 3)*
- [x] Implementar función `enhance_contrast()`: CLAHE (Contrast Limited Adaptive Histogram Equalization) *(Notebook 02 v2, pipeline.py)*
- [x] Implementar función `normalize_dpi()`: re-muestreo a 300 DPI estándar *(Notebook 02, Sección 3)*
- [x] Construir pipeline modular: `detect_cover → deskew → denoise → enhance_contrast → binarize → normalize_dpi` *(Notebook 02 v2, pipeline.py)*
- [ ] Guardar imágenes procesadas en `data/processed/images/` con nomenclatura estandarizada
- [ ] Validar pipeline con muestra de 50 documentos y comparar métricas OCR antes/después

### 2.2 Estrategia de Etiquetado y Curación (Weak Supervision + Revisión Humana)
> **Decisión arquitectural v2:** Reemplaza la anotación manual completa (800 docs) por un pipeline de
> pre-anotación automática + corrección humana. Reduce el trabajo de anotación ~70% sin envenenar el ground truth.

- [ ] Definir esquema de anotación JSON para cada tipología:
  - Cédula: `{numero, nombre_completo, apellidos, fecha_nacimiento, lugar_nacimiento, fecha_expedicion, lugar_expedicion, sexo, rh}`
  - RUT: `{nit, razon_social, tipo_contribuyente, regimen, actividad_economica, ciiu, representante_legal, direccion, municipio, departamento}`
  - Póliza: `{numero_poliza, aseguradora, tomador, asegurado, vigencia_desde, vigencia_hasta, valor_asegurado, prima_neta, amparo_principal}`
  - Cámara de Comercio: `{nit, razon_social, tipo_sociedad, matricula, fecha_renovacion, domicilio, objeto_social, representante_legal, activos, capital_social}`

#### RUT — Weak Supervision con Regex Labeling Functions (LFs)
*Justificación: estructura fija y predecible + texto digital disponible → las LFs tienen alta precisión, bajo riesgo de propagar errores.*

> **⚠️ ALERTA v1.3 — Cédulas NO son elegibles para regex LFs:**
> El EDA del corpus confirma que **312 de 334 Cédulas (93%) son documentos escaneados** — no contienen texto como caracteres. Las regex no tienen texto sobre el que operar. Ver Hallazgo 1 en `01_analisis_descriptivo_secop.ipynb`.

- [x] Implementar LFs con regex para RUT *(Notebook 02 v2, Sección 5b + pipeline.py)*:
  - `nit`: formato continuo con guión + cajas DIAN (dígitos individuales separados por espacio) — 5/5 docs correctos
  - `razon_social`: líneas en MAYÚSCULAS con forma jurídica (LTDA, SAS, S.A, E.U) — 5/5 docs correctos
  - `regimen`: normalizado ("ordinar*" → "ordinario", "simpli*" → "simplificado") — 5/5 docs correctos
  - `direccion`: nomenclatura colombiana (CL/CR/AV/TV/KR + número) — 5/5 docs correctos
  - `municipio`: lista de ciudades principales Colombia — 5/5 docs (municipio siempre "Cali" en muestra → revisar en corpus)
  - `representante_legal`: APELLIDOS NOMBRES antes de "Representante legal" — 5/5 docs correctos
  - **NOTA sobre `filtrar_ciiu_rut()`:** usar SOLO para embeddings/TF-IDF, NO para extracción NER. La función elimina tokens CIIU (orgánicas, lata, frasco) del texto para generar embeddings limpios.
- [ ] Generar pre-anotaciones automáticas sobre los **235 RUT** (texto digital)
- [ ] Cargar pre-anotaciones en Label Studio → revisión humana solo para corregir (no anotar desde cero)
- [ ] Target: Cohen's Kappa > 0.85 en muestra de validación cruzada de 50 docs por tipología

#### Cédula — Anotación vía OCR Muestral (flujo alternativo)
*Justificación: 93% son imágenes escaneadas → el texto debe extraerse con OCR antes de poder anotar.*
- [ ] Aplicar EasyOCR sobre muestra representativa de **60 Cédulas** (30 alta calidad + 30 con ruido)
- [ ] Revisar y corregir manualmente la salida OCR en Label Studio (bounding boxes visuales)
- [ ] Usar las 60 anotaciones corregidas como seed para fine-tuning; escalar con augmentación 3x
- [ ] **No** intentar regex LFs sobre el texto extraído por OCR — la tasa de error OCR invalida la estrategia automática

#### Pólizas — Anotación Manual (muestra aleatoria)
> **Decisión v1.7:** Las entidades objetivo de Póliza (número_poliza, aseguradora, tomador, vigencia_desde, vigencia_hasta, valor_asegurado, prima_neta, amparo_principal) son estándar del contrato de seguro colombiano — iguales en todas las aseguradoras independientemente del layout. La identificación de aseguradora **no es requisito para estratificar** el set de entrenamiento. Selección: muestra aleatoria del corpus de Pólizas digitales.

- [x] Identificar aseguradoras presentes en el corpus — ejecutado en Notebook 02 (`aseguradoras_corpus.json`). Dato informativo, no bloqueante.
- [ ] Seleccionar aleatoriamente **80 Pólizas digitales** — conjunto de entrenamiento
- [ ] Anotar manualmente **80 Pólizas** — conjunto de entrenamiento
- [ ] Anotar **40 Pólizas** (muestra aleatoria) — conjunto de validación sin augmentación

#### Cámara de Comercio — Anotación Manual Reducida
*Justificación: formato consistente entre cámaras, solo varía logo. Layout-aware chunking es viable.*
- [ ] Anotar manualmente **80 documentos** — conjunto de entrenamiento
  - *Reducido de 200 → 80: mínimo viable para fine-tuning con augmentación 3x aplicada posteriormente*
- [ ] Anotar **40 documentos** — conjunto de validación sin augmentación

#### Configuración común
- [ ] Configurar Label Studio con bounding boxes (BIO tagging para NER) para las 4 tipologías
- [ ] Establecer revisión cruzada obligatoria sobre el 100% del set de validación

### 2.3 Fragmentación Semántica — Chunking Quirúrgico por Tipología
> **Decisión arquitectural v2:** Estrategia diferenciada por tipología según longitud real medida en EDA.
> No aplicar lógica layout-aware a todo el corpus — solo donde el retorno justifica la complejidad.

> **⚠️ ALERTA v1.3 — Corrección BPE obligatoria:** El tokenizador BPE de Llama 3 fragmenta palabras legales en español en subpalabras. Factor de corrección empírico: **x1.25** sobre la estimación heurística básica (`lexicon_count / 0.75`). El límite duro de chunking es **1,800 tokens** (margen 12% sobre 2,048).

> **⚠️ CORRECCIÓN v1.4 — RUT requiere chunking:** Contra lo asumido en v1.1-v1.3, el enriquecimiento BPE sobre el corpus real revela que **151/235 RUT (64%) superan el límite de 1,800 tokens**. La mediana BPE del RUT es 1,861 tokens — por encima del límite. RUT se mueve de "sin chunking" a "ventana deslizante", igual que Pólizas. *Fuente: quality_report_completo.csv, columna `tokens_bpe_ajustado`, umbral 1,800.*

| Tipología | Mediana tokens (BPE x1.25) | Docs > 1,800 tok | Estrategia de Chunking | Justificación |
|---|---|---|---|---|
| Cédula de Ciudadanía | ~0 (imágenes) | 0 | **Sin chunking** | 93% escaneadas; texto OCR es corto |
| RUT (DIAN) | **1,861** | **151 (64%)** | **Ventana deslizante** | Formulario denso supera límite en mayoría del corpus |
| Pólizas de Seguros | ~806 | **31 (14%)** | **Ventana deslizante** | Volumen moderado, layout variable entre aseguradoras |
| Cámara de Comercio | ~1,772 | **96 (45%)** | **Layout-aware (OpenCV)** | Docs multipágina con estructura tabular consistente |

#### Sin Chunking — Solo Cédula
- [ ] Cédulas: sin chunking de texto; el pipeline OCR genera fragmentos cortos por naturaleza (~0 tokens digitales)

#### Ventana Deslizante — RUT y Pólizas de Seguros
> *RUT agregado en v1.4: 151/235 docs (64%) superan 1,800 tokens BPE. Misma estrategia que Pólizas.*
- [ ] Implementar ventana deslizante con `size=512 tokens`, `overlap=30%` *(aumentado de 20% → 30% para reducir cortes de entidades en el borde)*
- [ ] Para RUT: respetar fronteras de sección DIAN (casillas agrupadas por bloque) al definir puntos de corte — no cortar a mitad de una micro-casilla
- [ ] Añadir lógica de re-ensamble: al combinar chunks en inferencia, descartar predicciones duplicadas en zona de solapamiento usando NMS (Non-Maximum Suppression sobre spans)

#### Layout-Aware con OpenCV — Cámara de Comercio (único doc que justifica el esfuerzo)
- [ ] Detectar separadores horizontales con `cv2.HoughLinesP` → identifican fronteras entre secciones lógicas
- [ ] Segmentar en 4 bloques canónicos: `[datos_basicos, representantes_legales, establecimientos, actividades_economicas]`
- [ ] Validar que ningún bloque supere 512 tokens; si supera, aplicar ventana deslizante local dentro del bloque
- [ ] Test de regresión: verificar que ninguna entidad objetivo queda cortada entre dos chunks

#### Construcción del Dataset Final
- [x] Construir función `chunk_document(pdf_path, doc_type)` *(Notebook 02 v2, Sección 5 + pipeline.py)* — estrategia determinada por tipología: sin_chunking (Cédula), layout_aware (CC), sliding_window (RUT/Póliza si >1800 tok)
- [ ] Generar dataset JSONL final: `data/processed/train.jsonl` y `data/processed/val.jsonl`
- [ ] Formato JSONL: `{"image_path": "...", "text_input": "...", "entities": [{...}], "doc_type": "...", "chunk_id": "...", "chunk_strategy": "..."}`

### 2.4 Augmentación de Datos
- [ ] Implementar augmentaciones conservadoras: rotación ±5°, variación de brillo ±15%, ruido gaussiano leve
- [ ] Augmentación específica para Cédulas: variantes de fondo (hologramas simulados), degradación controlada
- [ ] Factor de augmentación objetivo: 3x para tipologías minoritarias (Pólizas, Cámara de Comercio)
- [ ] Verificar que augmentaciones no distorsionen entidades objetivo

### 2.5 Entregables de Fase 2
- [x] Notebook `02_preprocesamiento_pipeline.ipynb` ejecutado (22 celdas, 0 errores funcionales)
- [x] Script `src/preprocessing/pipeline.py` — módulo de producción con todas las funciones
- [ ] `data/processed/train.jsonl` (~2,400 ejemplos tras augmentación)
- [ ] `data/processed/val.jsonl` (268 ejemplos sin augmentación)
- [ ] Reporte de calidad del dataset: distribución de entidades, cobertura por tipología

---

## FASE 3 — MODELADO (El Núcleo)

### 3.1 Arquitectura de Dos Etapas

#### Etapa A — Modelo de Visión-Lenguaje para Extracción de Tablas y Documentos Estructurados
**Modelo:** Arctic-Extract (Snowflake, 6.6 GiB VRAM)  
**Tarea:** Extracción sin OCR de tablas y campos estructurados de Cámara de Comercio y RUT

> **✅ CONFIRMADO v1.3 — RUT como caso primario de Arctic-Extract:** El EDA del corpus mide en una página típica de RUT **97 bloques de texto** y **26.2% de densidad de área de texto**. Esta estructura tabular densa (micro-casillas DIAN con campos de 2-3 caracteres) supera la capacidad de extracción de Llama 3 basado en texto plano. Arctic-Extract, diseñado para formularios sin OCR, es la herramienta indicada. Dato registrado en `01_analisis_descriptivo_secop.ipynb` Hallazgo 2.

- [ ] Instalar dependencias: `pip install snowflake-arctic-embed transformers accelerate`
- [ ] Descargar modelo: `Snowflake/arctic-embed-l` o variante Arctic-Extract específica
- [ ] Configurar inferencia en 8-bit con `BitsAndBytesConfig` para optimizar VRAM
- [ ] Implementar pipeline de inferencia: `image → Arctic-Extract → structured_JSON`
- [ ] Definir prompt template para extracción por tipología:
  ```
  "Extrae las siguientes entidades del documento colombiano tipo {doc_type}: {entity_list}. 
   Responde ÚNICAMENTE en JSON válido con las claves especificadas. Si no encuentras un campo, usa null."
  ```
- [ ] Evaluar baseline zero-shot sobre 50 documentos del set de validación
- [ ] Medir VRAM en uso: target < 12 GB para dejar margen al pipeline de fine-tuning

#### Etapa B — SLM Fine-Tuning con QLoRA para NER Especializado
**Modelo Base:** Llama 3 8B (meta-llama/Meta-Llama-3-8B-Instruct)  
**Framework de Fine-Tuning:** Unsloth + HuggingFace PEFT  
**Cuantización:** 4-bit NF4 con doble cuantización

- [ ] Instalar entorno de fine-tuning:
  ```bash
  pip install unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git
  pip install --no-deps trl peft accelerate bitsandbytes xformers
  pip install datasets transformers sentencepiece protobuf
  ```
- [ ] Configurar carga del modelo base con cuantización 4-bit:
  ```python
  from unsloth import FastLanguageModel
  model, tokenizer = FastLanguageModel.from_pretrained(
      model_name="meta-llama/Meta-Llama-3-8B-Instruct",
      max_seq_length=2048,
      dtype=None,  # auto-detect
      load_in_4bit=True,
  )
  ```
- [ ] Configurar adaptadores LoRA con parámetros optimizados:
  ```python
  model = FastLanguageModel.get_peft_model(
      model,
      r=16,                    # rank — balance entre capacidad y VRAM
      target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj"],
      lora_alpha=16,
      lora_dropout=0.05,
      bias="none",
      use_gradient_checkpointing="unsloth",  # 30% ahorro VRAM
      random_state=42,
  )
  ```
- [ ] Diseñar plantilla de prompt estructurado para NER en español colombiano:
  ```
  <|begin_of_text|><|start_header_id|>system<|end_header_id|>
  Eres un experto extractor de información de documentos oficiales colombianos. 
  Tu tarea es identificar y extraer entidades específicas en formato JSON estructurado.
  Responde SOLO con JSON válido, sin texto adicional.<|eot_id|>
  <|start_header_id|>user<|end_header_id|>
  Documento tipo: {doc_type}
  Texto del documento:
  {document_text}
  Extrae: {entities_to_extract}<|eot_id|>
  <|start_header_id|>assistant<|end_header_id|>
  {expected_json_output}<|eot_id|>
  ```
- [ ] Configurar SFTTrainer con hiperparámetros para GPU 24 GB:
  ```python
  from trl import SFTTrainer
  from transformers import TrainingArguments
  
  training_args = TrainingArguments(
      output_dir="./checkpoints/llama3-secop-ner",
      num_train_epochs=3,
      per_device_train_batch_size=2,
      gradient_accumulation_steps=8,   # effective batch = 16
      warmup_steps=100,
      learning_rate=2e-4,
      fp16=True,                        # mixed precision
      logging_steps=25,
      save_strategy="epoch",
      evaluation_strategy="epoch",
      load_best_model_at_end=True,
      metric_for_best_model="eval_f1",
      optim="adamw_8bit",              # optimizador 8-bit para VRAM
      lr_scheduler_type="cosine",
      seed=42,
      report_to="tensorboard",
  )
  ```
- [ ] Implementar callback de early stopping: paciencia de 2 épocas
- [ ] Monitorear VRAM durante entrenamiento: target pico < 22 GB
- [ ] Guardar modelo fine-tuneado: `models/llama3-secop-ner-v1/`
- [ ] Exportar a GGUF 4-bit para servicio con Ollama:
  ```python
  model.save_pretrained_gguf("models/llama3-secop-ner-v1-gguf", 
                              tokenizer, quantization_method="q4_k_m")
  ```

### 3.2 Configuración de Ollama para Inferencia Local
- [ ] Crear `Modelfile` para Ollama:
  ```
  FROM ./models/llama3-secop-ner-v1-gguf/model.gguf
  SYSTEM "Eres SinergIA, experto extractor de documentos colombianos SECOP."
  PARAMETER temperature 0.1
  PARAMETER top_p 0.9
  PARAMETER num_ctx 2048
  ```
- [ ] Registrar modelo: `ollama create sinergialab-ner -f Modelfile`
- [ ] Validar inferencia local: `ollama run sinergialab-ner "Test de carga"`

### 3.3 Entregables de Fase 3
- [ ] Notebook `03_finetuning_llama3_qlora.ipynb` con entrenamiento documentado
- [ ] `models/llama3-secop-ner-v1/` — modelo PEFT guardado
- [ ] `models/llama3-secop-ner-v1-gguf/` — modelo GGUF para Ollama
- [ ] `checkpoints/` — checkpoints por época con métricas de entrenamiento
- [ ] `logs/tensorboard/` — logs de entrenamiento para visualización
- [ ] Gráficas de training/validation loss por época

---

## FASE 4 — EVALUACIÓN Y TESTEO

### 4.1 Métricas de Evaluación NER (Nivel Entidad)
- [ ] Implementar evaluación a nivel de entidad (span-level):
  - **Precision:** TP / (TP + FP) — de lo que extrae el modelo, ¿cuánto es correcto?
  - **Recall:** TP / (TP + FN) — de todas las entidades reales, ¿cuántas encuentra?
  - **F1-Score:** 2 × (P × R) / (P + R) — métrica principal de optimización
  - **F1 Macro:** promedio no ponderado por tipología — penaliza tipologías con bajo rendimiento
  - **F1 Micro:** ponderado por frecuencia — refleja rendimiento global real
- [ ] Targets mínimos aceptables por tipología:
  | Tipología | F1 Mínimo | F1 Objetivo |
  |-----------|-----------|-------------|
  | Cédula | 0.88 | 0.95 |
  | RUT | 0.85 | 0.92 |
  | Póliza | 0.82 | 0.90 |
  | Cámara de Comercio | 0.80 | 0.88 |

### 4.2 Evaluación de Alucinaciones y Confiabilidad
- [ ] Implementar detección de alucinaciones factuales: valores inventados no presentes en el documento fuente
- [ ] Calcular tasa de alucinación: `hallucinated_entities / total_extracted_entities` — target < 2%
- [ ] Evaluar consistencia: re-inferir mismo documento 3 veces con temperatura 0.1 → medir varianza de salida
- [ ] Test de robustez: evaluar sobre documentos con calidad visual degradada (grupo REQUIERE_PREPROCESAMIENTO)
- [ ] Detectar negativas falsas críticas: entidades de alto impacto legal que el modelo NO extrae (NIT, número de cédula)

### 4.3 Diseño Experimental
- [ ] **Experimento 1 — Baseline:** PaddleOCR + regex → F1 por tipología (cota inferior)
- [ ] **Experimento 2 — Zero-Shot:** Llama 3 8B sin fine-tuning sobre texto PaddleOCR → F1
- [ ] **Experimento 3 — Fine-Tuned:** Llama 3 8B + QLoRA entrenado → F1 por tipología
- [ ] **Experimento 4 — VLM:** Arctic-Extract sobre imagen directa → F1 por tipología
- [ ] **Experimento 5 — Ensemble:** Arctic-Extract (tablas) + Llama 3 (texto libre) → F1 combinado
  > **Gestión de VRAM obligatoria para Experimento 5:** Inferencia secuencial — nunca cargar ambos modelos simultáneamente.
  > Presupuesto VRAM estimado: Arctic-Extract ~6.6 GB + overhead ~2 GB = ~9 GB pico. Llama 3 4-bit ~5 GB + overhead ~2 GB = ~7 GB pico.
  ```python
  # Patrón de ejecución del Experimento 5 — inferencia secuencial con liberación explícita
  import torch, gc

  # — Etapa 1: Arctic-Extract —
  model_arctic = load_arctic_extract()          # ~9 GB VRAM
  results_arctic = run_batch(model_arctic, val_docs)
  save_intermediate(results_arctic, 'exp5_arctic_raw.json')
  del model_arctic
  torch.cuda.empty_cache(); gc.collect()        # liberar antes de cargar Llama
  assert torch.cuda.memory_allocated() < 1e9, "VRAM no liberada correctamente"

  # — Etapa 2: Llama 3 fine-tuned —
  model_llama = load_llama_finetuned()          # ~7 GB VRAM
  results_llama = run_batch(model_llama, val_docs)
  save_intermediate(results_llama, 'exp5_llama_raw.json')
  del model_llama
  torch.cuda.empty_cache(); gc.collect()

  # — Etapa 3: Merge en CPU —
  final_results = merge_ensemble(results_arctic, results_llama)  # sin GPU
  ```
- [ ] Documentar tabla comparativa de experimentos con métricas, VRAM pico y latencia

### 4.4 Pruebas de Inferencia y Latencia
- [ ] Medir latencia de inferencia con Ollama: target ≤ 5s para documentos de 1 página
- [ ] Medir latencia para Cámara de Comercio multipágina: target < 45s
- [ ] Prueba de carga: 10 documentos secuenciales → medir throughput (docs/min)
- [ ] Perfilar uso de VRAM durante inferencia: target < 10 GB (dejar margen para concurrencia futura)

### 4.5 Análisis de Errores (Error Analysis)
- [ ] Construir matriz de confusión a nivel de tipo de entidad
- [ ] Identificar las 10 entidades con menor F1 → analizar patrones de error
- [ ] Clasificar errores por causa: [OCR_RUIDO / FORMATO_VARIANTE / ALUCINACION / AMBIGUEDAD]
- [ ] Definir acciones correctivas: más datos de augmentación, ajuste de prompt, o post-procesamiento regex

### 4.6 Entregables de Fase 4
- [ ] Notebook `04_evaluacion_metricas.ipynb` con evaluación completa
- [ ] `reports/experiment_results.csv` — tabla comparativa de los 5 experimentos
- [ ] `reports/error_analysis.md` — análisis cualitativo de fallos
- [ ] Decisión documentada: ¿el modelo cumple umbrales para avanzar a la siguiente fase?

---

## CONTROL DE VERSIONES Y REPRODUCIBILIDAD

- [ ] Crear `requirements.txt` con versiones exactas de todas las librerías
- [ ] Crear `environment.yml` para reproducción de entorno Conda
- [ ] Documentar semilla aleatoria usada en todos los experimentos: `seed=42`
- [ ] Registrar hashes de commits de modelos base descargados
- [ ] Crear `config/model_config.yaml` con todos los hiperparámetros centralizados

---

## LIBRERÍAS CLAVE POR FASE

| Fase | Librería | Versión mínima | Propósito |
|------|----------|----------------|-----------|
| EDA | `easyocr` | 1.7+ | OCR con bounding boxes nativos — **reemplaza PaddleOCR para EDA** ¹ |
| EDA | `opencv-python` | 4.8+ | Análisis visual y layout-aware chunking |
| EDA | `pymupdf` | 1.23+ | Conversión PDF→imagen sin dependencias del sistema (reemplaza pdf2image+Poppler) |
| EDA | `matplotlib`, `seaborn` | latest | Visualización |
| Prepro | `Pillow` | 10.0+ | Manipulación imágenes |
| Modelado | `paddlepaddle==2.6.1` | 2.6.1 | Backend PaddleOCR — **entorno Python 3.10 separado** ² |
| Modelado | `paddleocr` | 2.7+ | OCR para pipeline de fine-tuning (entorno Python 3.10) |
| Modelado | `unsloth` | latest | Fine-tuning optimizado |
| Modelado | `peft` | 0.7+ | LoRA adapters |
| Modelado | `trl` | 0.7+ | SFTTrainer |
| Modelado | `bitsandbytes` | 0.41+ | Cuantización 4-bit |
| Modelado | `transformers` | 4.38+ | HuggingFace core |
| Modelado | `datasets` | 2.16+ | Carga de datos JSONL |
| Evaluación | `seqeval` | 1.2+ | Métricas NER |
| Evaluación | `scikit-learn` | 1.3+ | Métricas adicionales |
| Inferencia | `ollama` | 0.1.6+ | Servicio local |

---

## ESTRUCTURA DE CARPETAS OBJETIVO

```
SinergiaLabProyecto/
├── data/
│   ├── raw/                    # Documentos originales sin tocar
│   │   ├── cedulas/
│   │   ├── rut/
│   │   ├── polizas/
│   │   └── camara_comercio/
│   └── processed/
│       ├── images/             # Imágenes preprocesadas
│       ├── train.jsonl
│       ├── val.jsonl
│       └── quality_report.csv
├── notebooks/
│   ├── 01_analisis_descriptivo_secop.ipynb
│   ├── 02_preprocesamiento_pipeline.ipynb
│   ├── 03_finetuning_llama3_qlora.ipynb
│   └── 04_evaluacion_metricas.ipynb
├── src/
│   └── preprocessing/
│       └── pipeline.py
├── models/
│   ├── llama3-secop-ner-v1/
│   └── llama3-secop-ner-v1-gguf/
├── checkpoints/
├── logs/
│   └── tensorboard/
├── reports/
│   ├── experiment_results.csv
│   └── error_analysis.md
├── config/
│   └── model_config.yaml
├── PLAN_MODELADO_CRISPDM.md
├── requirements.txt
└── environment.yml
```

---

---

## NOTAS DE ENTORNO

**¹ EasyOCR vs PaddleOCR — Decisión de entorno (2026-04-03)**
- **Causa:** PaddleOCR no tiene wheels oficiales para Python 3.12. El entorno de desarrollo actual corre Python 3.12.10.
- **Decisión:** EasyOCR para la Fase 1 (EDA). API equivalente: retorna `[bbox, text, confidence]` por bloque — misma estructura que PaddleOCR.
- **Impacto en el plan:** Ninguno en métricas ni decisiones de chunking. Las columnas `token_count`, `bbox_count`, `text_density`, `avg_confidence` del reporte se calculan igual.
- **Reversible:** Sí. Cuando el entorno de fine-tuning (Fase 3) use Python 3.10, PaddleOCR se instala sin fricción.

**² Estrategia de entornos**
- `env_eda/` → Python 3.12 + EasyOCR + OpenCV + PyMuPDF (EDA, Fases 1-2)
- `env_training/` → Python 3.10 + PaddleOCR + Unsloth + QLoRA (Fine-tuning, Fase 3)

**³ PyMuPDF reemplaza pdf2image+Poppler**
- **Causa:** `pdf2image` requiere binarios Poppler instalados en el sistema operativo (no disponibles por defecto en Windows).
- **Decisión:** PyMuPDF (`fitz`) — librería Python pura, sin dependencias del sistema, más rápida para conversión PDF→imagen.

---

*Documento generado: 2026-04-03 | Versión: 1.0 | Estado: ACTIVO*
*Actualizado: 2026-04-03 | Versión: 1.1 — Revisión arquitectural Tech Lead aplicada*
*Actualizado: 2026-04-03 | Versión: 1.2 — Ajustes de entorno de desarrollo*
*Actualizado: 2026-04-08 | Versión: 1.3 — Hallazgos del EDA real del corpus integrados*
*Actualizado: 2026-04-08 | Versión: 1.4 — Corrección chunking RUT tras enriquecimiento BPE*
*Actualizado: 2026-04-08 | Versión: 1.5 — Revisión de tareas Fase 1: reclasificación y eliminación*
*Actualizado: 2026-04-08 | Versión: 1.6 — Hallazgos de revisión visual de variantes de layout*
*Actualizado: 2026-04-08 | Versión: 1.7 — Hallazgos de ejecución Notebook 02*

**Cambios v1.1:**
- `§1.2` PaddleOCR reemplaza Tesseract como OCR baseline (bounding boxes nativos)
- `§2.2` Estrategia de etiquetado híbrida: Weak Supervision (regex LFs) para Cédula/RUT + anotación manual reducida a 80 docs para Pólizas/CC
- `§2.3` Chunking quirúrgico diferenciado por tipología: sin chunking (Cédula/RUT), ventana deslizante 30% (Pólizas), layout-aware OpenCV (solo Cámara de Comercio)
- `§4.3` Experimento 5 con patrón de inferencia secuencial + liberación explícita de VRAM entre modelos

**Cambios v1.2:**
- `§Librerías` EasyOCR reemplaza PaddleOCR en entorno EDA (Python 3.12 — incompatibilidad de wheels)
- `§Librerías` PyMuPDF reemplaza pdf2image+Poppler (sin dependencias del sistema en Windows)
- `§Notas` Estrategia de dos entornos documentada: `env_eda` (Python 3.12) / `env_training` (Python 3.10)

**Cambios v1.3** *(hallazgos derivados del EDA real del corpus — quality_report_completo.csv, 1,014 docs × 53 columnas)*:

- `§2.2` **Cédulas excluidas de regex LFs:** 312/334 (93%) son documentos escaneados sin texto digital. Flujo alternativo: OCR muestral de 60 Cédulas + anotación manual en Label Studio. Las regex LFs se aplican únicamente a los 235 RUT digitales.
- `§2.3` **Chunking es requisito duro para CC y Pólizas (corrección BPE x1.25):** El factor BPE confirma que 70 docs de Cámara de Comercio (33%) y 24 Pólizas (11%) superan 2,048 tokens. Límite de seguridad establecido en 1,800 tokens. Tabla de estrategias actualizada con columna `Docs > 2,048 tokens`.
- `§3.1` **RUT confirmado como caso primario de Arctic-Extract:** EDA mide 97 bloques de texto y 26.2% de densidad de área en página típica de RUT. La estructura de micro-casillas DIAN valida el uso de Arctic-Extract sin OCR para este tipo documental.

**Cambios v1.4** *(enriquecimiento BPE sobre corpus real — quality_report_completo.csv, 1,014 docs × 57 columnas)*:
- `§2.3` **RUT requiere chunking (corrección sobre v1.1-v1.3):** El enriquecimiento BPE confirma que 151/235 RUT (64%) superan el límite de 1,800 tokens — mediana BPE de 1,861 tokens. La asunción anterior ("sin chunking") era incorrecta. RUT pasa a ventana deslizante junto con Pólizas, con punto de corte en fronteras de sección DIAN. Cifras reales del corpus: Cédula 0 docs, RUT 151 docs, Póliza 31 docs, CC 96 docs.

**Cambios v1.5** *(revisión de tareas Fase 1 — reclasificación y eliminación de tareas)*:
- `§1.1` Variantes regionales → movida a §2.0 (requiere revisión visual humana, no automatizable en EDA)
- `§1.1` Near-duplicates coseno → movida a §2.0 (tarea de preparación de dataset, no de EDA)
- `§1.2` Vocabulario por dominio → movida a §2.0 (se define después de las entidades objetivo)
- `§1.3` Rotaciones Hough → ya estaba en §2.1; nota aclaratoria añadida
- `§1.4` Reporte HTML → **eliminada** (notebook + figuras PNG + CSV cumplen la función)
- `§2.0` Nueva sección: agrupa las 3 tareas trasladadas como pre-requisitos de Fase 2

**Cambios v1.6** *(hallazgos de revisión visual de variantes de layout — revisión humana 2026-04-08)*:
- `§2.0` **Variantes completadas:** Cédula y RUT formato único; CC formato único con posible portada; Pólizas formato variable por aseguradora
- `§2.1` **Detección de portada generalizada:** primer paso del pipeline para todas las tipologías (`lexicon < 50` Y `blocks < 5` en pág. 1 → portada → saltar a pág. 2)
- `§2.2` **Anotación Pólizas estratificada por aseguradora:** los 80 docs de entrenamiento deben distribuirse proporcionalmente entre aseguradoras para cubrir variabilidad de layout

**Cambios v1.7** *(hallazgos Notebook 02 — near-duplicates, vocabulario, portadas, aseguradoras — 2026-04-08)*:
- `§2.0` **Near-duplicates completado:** 1 dup exacto en Cédula, 1 en RUT; umbral ajustado a ≥0.99 para RUT por falsos positivos de plantilla DIAN compartida
- `§2.0` **Vocabulario completado — anomalía RUT:** términos CIIU (orgánicas, lata, frasco, congeladas) con 12k+ ocurrencias contaminan embeddings. Decisión: filtrar sección CIIU antes de indexar para fine-tuning
- `§2.0` **Vocabulario Cédula — requiere investigación:** términos de CC en vocabulario de Cédula. Hipótesis: texto de carátulas SECOP detectadas como portada. Pendiente confirmar inspeccionando los 3 docs con portada
- `§2.1` **Pipeline de preprocesamiento implementado:** `detect_cover → deskew → denoise → binarize → normalize_dpi` operativo en Notebook 02. Artefactos: `portadas_detectadas.json`
- `§2.1` **Portadas validadas por muestra:** CC 10%, Pólizas 25%, Cédulas 15% (carátulas SECOP), RUT 0%
- `§2.2` **Pólizas — estratificación eliminada:** las entidades objetivo son estándar del contrato colombiano (iguales en todas las aseguradoras). La identificación de aseguradora es dato informativo, no requisito para anotación. Selección: muestra aleatoria de Pólizas digitales.

*Actualizado: 2026-04-08 | Versión: 1.7 — Hallazgos Notebook 02 + implementación pipeline.py + LFs RUT*
