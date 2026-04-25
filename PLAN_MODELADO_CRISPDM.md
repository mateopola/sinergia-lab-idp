# PLAN MAESTRO DE MODELADO — SinergIA Lab
## Hoja de Ruta Técnica CRISP-DM++ (Enfoque: Modelado y Testeo)
**Proyecto:** IDP para Documentos Colombianos SECOP | PUJ Especialización IA 2026  
**Metodología:** CRISP-DM++ + Scrum + Design Thinking  
**Alcance de esta hoja de ruta:** Desarrollo, Fine-Tuning y Evaluación del Modelo. Excluye API, backend y HITL.
**Versión:** v2.0 (2026-04-18) — Fase 3 reescrita tras auditoría de fuentes.

**Documentos vinculantes:**
- [PROPUESTA_MODELOS.md](PROPUESTA_MODELOS.md) — fundamentación científica de los 9 candidatos (3 OCR + 3 Clasificación + 3 NER) con citas a papers revisados por pares.
- [OCR_BENCHMARK.md](OCR_BENCHMARK.md) — bitácora del benchmark OCR y decisión (EasyOCR).
- [Resumen_Investigacion_SinergIA_Lab.md](Resumen_Investigacion_SinergIA_Lab.md) — contexto académico y estado del arte.

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
- [x] Implementar función `binarize()`: umbralización adaptativa Otsu *(Notebook 02, Sección 3)* — **NO SE USA EN PIPELINE FINAL** (ver §2.1.3)
- [x] Implementar función `enhance_contrast()`: CLAHE (Contrast Limited Adaptive Histogram Equalization) *(Notebook 02 v2, pipeline.py)*
- [x] Implementar función `normalize_dpi()`: re-muestreo a 300 DPI estándar *(Notebook 02, Sección 3)*
- [x] Construir pipeline modular: `detect_cover → deskew → denoise → enhance_contrast → binarize → normalize_dpi` *(Notebook 02 v2, pipeline.py)* — **pipeline final en nb 04 omite `binarize`** (ver §2.1.3)
- [x] **Guardar imágenes procesadas en `data/processed/images/` con nomenclatura estandarizada** *(Notebook 04, 2026-04-17 — 1,678 páginas / 412 docs escaneados procesadas, 0 errores, 1.9 GB)*
- [x] **Validar pipeline con muestra** *(Notebook 04: test visual en `fig12_preprocesamiento_test.png` + validación post-corrida en celda 20)*

### 2.1.3 Decisión técnica: omitir `binarize()` del pipeline final — 2026-04-17

> **Hallazgo crítico durante la ejecución productiva:** la binarización con Otsu ralentiza EasyOCR **~5×** (de ~20 s/pág a ~110 s/pág). Extrapolado al corpus completo: 51 horas vs 9-12 horas.

**Causa raíz:** el detector CRAFT de EasyOCR es deep learning entrenado con imágenes naturales. Una imagen binarizada 0/255 pura tiene pocos valores únicos y confunde el detector, que gasta más tiempo en inferencia de texto.

**Contexto histórico:** `binarize` era convención del paradigma OCR clásico (Tesseract ≤2010). Los motores modernos basados en deep learning (EasyOCR, PaddleOCR, TrOCR) funcionan mejor sobre grayscale con CLAHE, sin umbralizar.

**Decisión:** el pipeline productivo (nb 04) aplica `deskew → denoise → CLAHE → normalize_dpi`, sin `binarize`. La función `binarize()` se conserva en `pipeline.py` para compatibilidad del nb 02 (análisis exploratorio) y para futuras pruebas con OCRs clásicos.

**Evidencia:**
- Corrida del 2026-04-17 a las 15:30: 1h54m para 68 páginas (110 s/pág) con binarize
- Pipeline actualizado, re-corrida estimada: ~9-12 h para 1,678 páginas (20 s/pág)
- Calidad OCR idéntica en ambos casos (ambos convergen al mismo texto, solo cambia velocidad)

**Referencias:**
- [OCR_BENCHMARK.md §2.6.0](OCR_BENCHMARK.md) — tabla comparativa de tiempos
- [notebooks/build_notebook_04.py](notebooks/build_notebook_04.py) — `process_page()` sin binarize
- [src/preprocessing/pipeline.py](src/preprocessing/pipeline.py) — función `binarize()` se conserva pero no se llama en pipeline productivo

### 2.1.1 ✅ Selección del Motor OCR (Benchmark Comparativo) — COMPLETADO 2026-04-15

> **Ejecutado y decidido.** Ver detalles en [OCR_BENCHMARK.md](OCR_BENCHMARK.md) y notebook [notebooks/03_benchmark_ocr.ipynb](notebooks/03_benchmark_ocr.ipynb).

**Motores evaluados:**
| Motor | Rol |
|---|---|
| PyMuPDF | Extractor nativo (no OCR) — usado siempre si `es_escaneado == False` |
| EasyOCR 1.7.2 | OCR deep learning |
| Tesseract 5.5.0 | OCR clásico LSTM |
| ~~PaddleOCR~~ | Descartado (incompatible con Python 3.12) |
| ~~Donut~~ | No es OCR — descartado como arquitectura global en §ALT-1 |

**Métricas calculadas (sobre 15 docs escaneados, 36 páginas transcritas manualmente):**
- `CER` — Character Error Rate (Levenshtein a nivel carácter, menor = mejor)
- `WER` — Word Error Rate (nivel palabra, menor = mejor)
- `entity_recall` — % de entidades NIT/cédula/fecha/monto recuperadas (mayor = mejor) — **métrica clave para este proyecto porque el objetivo es NER, no transcripción**
- `s_per_page` — tiempo por página (restricción de la regla de decisión)

**Resultados globales:**

| Motor | CER | WER | Entity recall | s/pág |
|---|---|---|---|---|
| EasyOCR (CPU) | **0.276** | 0.476 | 0.551 | 46.02 |
| Tesseract | 0.446 | 0.557 | **0.605** | **5.06** |

**Resultados por tipología:**

| Tipología | Ganador | Justificación |
|---|---|---|
| Cédula | 🏆 EasyOCR | Tesseract colapsa (CER 0.78) en IDs físicos con hologramas/columnas |
| RUT | Empate (entity 0.89 ambos); Tesseract gana por velocidad (10× más rápido) |
| Póliza | 🏆 Tesseract | Mejor CER (0.23 vs 0.33) y entity_recall (0.95 vs 0.65) |
| Cámara de Comercio | 🏆 Tesseract | Dominante: CER 0.05, entity_recall 0.96 |

**Decisión final — CPU only (laboratorio actual):**
```python
def select_ocr(tipologia):
    return 'easyocr' if tipologia == 'Cedula' else 'tesseract'
```

**Recomendación con GPU (mediano plazo):** EasyOCR unificado. Razones:
- GPU reduce EasyOCR de ~46 s/pág → ~1 s/pág (40× más rápido) → supera la restricción de tiempo.
- Pipeline más simple (sin clasificación previa de tipología).
- Elimina el talón de Aquiles de Tesseract en Cédulas (33% del corpus).
- Re-OCR corpus completo: ~20 h CPU → ~30 min GPU.

**Tareas completadas:**
- [x] Instalar Tesseract 5 + pytesseract + jiwer + modelo `spa.traineddata`
- [x] Implementar benchmark en notebook `03_benchmark_ocr.ipynb` (Secciones D, E, F)
- [x] Cálculo de CER/WER con `jiwer` contra transcripciones del gold
- [x] Ejecutar benchmark y generar `data/processed/ocr_benchmark.csv` + `ocr_benchmark_summary.csv` + `fig11_ocr_benchmark.png`
- [x] Documentar decisión en [OCR_BENCHMARK.md](OCR_BENCHMARK.md) Parte 2 y en Sección G del notebook

**Tareas pendientes (transición a Fase 2 §2.2):**
- [ ] Implementar `select_ocr(tipologia)` en [src/preprocessing/pipeline.py](src/preprocessing/pipeline.py) reemplazando el default EasyOCR
- [ ] Gestionar acceso a GPU con PUJ/el laboratorio

### 2.1.4 Ejecución productiva del OCR del corpus — 2026-04-17/18

> **Ejecutado.** EasyOCR CPU sobre 1,669 páginas escaneadas durante 23.42 h overnight. Validado contra gold seed.

**Outputs:**
- [data/processed/corpus_ocr.csv](data/processed/corpus_ocr.csv) — texto + bboxes por página (39 MB, gitignored por PII)
- [data/processed/corpus_ocr_summary.csv](data/processed/corpus_ocr_summary.csv) — métricas sin texto (300 KB, commiteable)
- [data/gold/ocr_corpus_validation.csv](data/gold/ocr_corpus_validation.csv) — CER + entity_recall contra gold seed
- 68 bloques de checkpoint en `data/processed/ocr_blocks/`

**Validación contra gold seed (15 docs):**

| Folder | N | CER medio | CER mediano | Entity recall |
|---|---|---|---|---|
| CAMARA DE CIO | 3 | 0.218 | 0.066 | 0.643 |
| CEDULA | 6 | 0.311 | 0.287 | 0.563 |
| POLIZA | 3 | 0.229 | 0.174 | 0.768 |
| rut | 3 | 0.330 | 0.359 | 0.889 |
| **Global** | **15** | **0.280** | **0.270** | **0.685** |

**Lectura:** el pipeline productivo reproduce el CER del benchmark aislado (0.276) y **mejora entity_recall global +24%** (0.685 vs 0.551 del benchmark) — atribuible al pipeline sin binarize (§2.1.3).

**Gaps detectados en la corrida productiva:**

1. **9 archivos `.jpg`/`.jpeg`** (7 cédulas/RUT + 2 TP) — Están en `image_manifest.csv` pero el nb 05 los filtra por una línea que resuelve `pdf_path` contra `data/raw/*.pdf`. Cierre trivial: quitar el filtro cuando `es_escaneado=True` (no necesita PDF original, usa la imagen procesada).

2. **548 PDFs digitales** (CAMARA 196 + POLIZA 160 + CEDULA 29 + rut 154 + OTROS 9) — Nunca entraron al nb 05 porque el nb 04 solo llena el manifest con escaneados. El branch `extraer_pymupdf()` está implementado pero nunca se ejecuta. Cierre: notebook 05b dedicado a digitales, iterando `quality_report_completo.csv` donde `es_escaneado=False`, llamando `fitz.open(pdf).get_text()` por página — estimado <10 min.

**Tareas completadas (cierre de §2.1 — 2026-04-18):**
- [x] Cerrar gap 1: notebook 05b Parte A procesa las 9 imágenes vía EasyOCR
- [x] Cerrar gap 2: notebook 05b Parte B procesa los 590 PDFs digitales vía PyMuPDF (11,576 páginas)
- [x] Re-validación contra gold seed: métricas idénticas a §2.6.2 (merge limpio, sin corrupción)

**Cobertura final del corpus_ocr.csv:**

| Métrica | Valor |
|---|---|
| Documentos | 960 (95% del corpus original de 1,014) |
| Páginas | 13,254 |
| Chars extraídos | 32.6 M |
| Motor EasyOCR | 1,678 páginas (escaneados) |
| Motor PyMuPDF | 11,576 páginas (digitales) |
| Errores | 0 |
| Páginas vacías | 463 (páginas-imagen dentro de PDFs digitales — mayormente Pólizas) |

**Tareas menores pendientes para §2.2:**
- [ ] Normalizar columna `folder` (actualmente 10 valores por mojibake de digitales vs 5 reales)
- [ ] Opcional: pasar las 463 páginas-imagen (dentro de digitales) por EasyOCR como tercer pase (recuperaría ~400 pág que hoy aparecen con `text_chars=0`)

### 2.1.5 Re-unificación OCR — decisión 2026-04-21

> **Cambio de arquitectura:** se elimina el selector híbrido EasyOCR/PyMuPDF documentado en §2.1.1. A partir del 2026-04-21 el corpus se procesa **íntegramente con EasyOCR** (escaneados Y digitales) por razones de paridad train-inference.

**Justificación:** En producción los documentos llegan sin clasificar previamente; si entrenamos los modelos NER y de Clasificación con texto procedente de dos motores OCR distintos (perfecto desde PyMuPDF para digitales vs ruidoso desde EasyOCR para escaneados), introducimos un **distribution shift** entre el dataset de entrenamiento y la realidad de inferencia. La unificación bajo EasyOCR garantiza que toda página vista en entrenamiento tenga la misma distribución de errores que tendrá en producción.

**Costo aceptado:** las páginas digitales degradan su CER de ~0.0 a ~0.28 (un retroceso aparente de calidad), pero ese costo se compensa con uniformidad estadística del dataset.

**Beneficio colateral:** los `bboxes_json` quedan poblados para el 100% del corpus (antes solo para los 1,674 escaneados procesados con EasyOCR), resolviendo el gap de insumos para el candidato C-3 LayoutLMv3.

**Decisiones operativas confirmadas (2026-04-21):**

1. **Excluir clase Otros** del corpus de entrenamiento (9 docs heterogéneos, sin patrón discriminativo). Clases finales del clasificador: `{Cedula, RUT, Poliza, CamaraComercio}` — 4 clases.
2. **Límite de 10 páginas por documento** durante el OCR. Justificación: 79% del corpus ya es ≤10 págs naturalmente; BETO/LayoutLMv3 truncan a 512 tokens; TF-IDF tiene suficiente con 10 págs × 2k chars = 20k chars; el cache MD5 permite re-OCR extendido si NER (futuro) lo necesita.
3. **Hallazgo de calidad resuelto:** 2 docs en folder `RUT` eran en realidad RUPs (`10. REGISTRO UNICO DE PROPONENTES.pdf` 1,331 págs y `Registro Unico de Propnentes (RUP).pdf` 606 págs). **Eliminados** del corpus: movidos a `data/raw/_quarantine_misclassified/` y limpiadas sus 1,937 filas de `corpus_ocr.csv` (2026-04-21).

**Volumen final a procesar:** 747 docs únicos · ~3,821 páginas · ~6.4 h Colab T4.

**Tareas:**
- [x] Crear `scripts/identificar_pendientes_ocr.py` que produce `data/processed/ocr_pendientes.csv` (✅ 2026-04-21)
- [x] Decidir scope: sin Otros + límite 10 págs (✅ 2026-04-21)
- [ ] Re-correr script con dedup md5 + exclusión Otros (fix bug menor)
- [ ] Crear `notebooks/colab_ocr_unificacion.ipynb` para Colab Free GPU
- [ ] Subir `data/raw/{CEDULA,POLIZA,CAMARA DE CIO,rut}/` a Google Drive (~1.5 GB)
- [ ] Sesión Colab (~6.4 h) — cabe en 1 sola
- [ ] Descargar `corpus_ocr.csv` actualizado, verificar integridad
- [ ] Generar imágenes pág 1 para 548 digitales (PyMuPDF render local, no OCR)
- [ ] Commit `feat(fase2.1.5): OCR unificado EasyOCR (Colab GPU, limite 10 pags)`

**Hardware:** se ejecuta en Colab Free (Tesla T4 16 GB) porque el equipo del usuario (AMD Ryzen 5 4500U + AMD integrada sin CUDA + 8 GB RAM al 88%) tomaría ~9-12 días vs ~6.4 h en Colab.

**Documentos relacionados:** ver [PLAN_OCR_COLAB.md](PLAN_OCR_COLAB.md) para checklist operativo, métricas de éxito y cómo retomar tras caída de sesión.

### 2.1.2 Gold Standard (verdad absoluta para evaluación)
> **Qué es:** conjunto reducido de documentos anotados manualmente con máxima rigurosidad, usado como referencia inmutable para medir OCR, LFs y modelo NER final. Sin gold no se puede responder "¿funciona mi modelo?".

**Composición propuesta (~70 docs):**
| Tipología | Docs | Criterio de selección |
|---|---|---|
| Cédula | 20 | 10 alta calidad + 10 ruidosas (estratificado por `blur_score`) |
| RUT | 15 | 10 digitales + 5 escaneados |
| Pólizas | 20 | 4 por aseguradora (top 5 aseguradoras del corpus) |
| Cámara de Comercio | 15 | Distribuidas entre cámaras presentes |

**Reglas:**
- Doble anotación (2 revisores) + resolución de discrepancias → Cohen's Kappa ≥ 0.85
- Inmutable tras validación: no entra al training, no se modifica durante el desarrollo
- Contiene: PDF + transcripción textual perfecta + entidades con bounding boxes + metadatos

**Tareas:**
- [ ] Definir esquema JSON del gold (extensión del esquema de §2.2 + transcripción completa)
- [ ] Implementar `src/gold/sample_selector.py` — selección estratificada reproducible (seed fija)
- [ ] Estructura en disco: `data/gold/{tipologia}/{doc_id}.json` + `data/gold/gold_manifest.csv`
- [ ] Anotar 70 docs en Label Studio (doble revisor) y medir Kappa
- [ ] Congelar v1.0 del gold con hash SHA-256 para trazabilidad

**Usos a lo largo del proyecto:**
1. Benchmark OCR (§2.1.1) ← uso inmediato
2. Validación de LFs de RUT (§2.2)
3. Evaluación F1 del modelo NER final (Fase 4)
4. Reporte de métricas finales al cliente/tesis

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
  - **Estructura del texto DIAN (hallazgo crítico para LFs):** PyMuPDF extrae el RUT en un orden no intuitivo: primero todos los LABELS del formulario (~1,500 chars de nombres de casillas), después los VALORES reales. Truncar el texto en el header "Actividad económica" (que aparece en la sección de labels) elimina todos los valores. Por eso `filtrar_ciiu_rut()` usa eliminación de tokens (no truncado) y las LFs operan sobre el texto completo sin filtrar.
- [x] **Generar pre-anotaciones automáticas sobre los 216 RUT del corpus OCR** — [Notebook 06](notebooks/06_preanotaciones_rut.ipynb) ejecutado 2026-04-18. Outputs: `data/processed/rut_preanotaciones.jsonl`, `rut_preanotaciones_labelstudio.json`, `rut_preanotaciones_summary.csv`.

  **Cobertura empírica de las LFs (tras normalización):**

  | Entidad | Cobertura | Notas |
  |---|---|---|
  | `municipio` | 99.5% | 4 variantes de Bogotá consolidadas a canónico; 9 municipios únicos |
  | `regimen` | 98.6% | 3 valores limpios: `ordinario`, `especial`, `simple` (RST Ley 2155/2021) |
  | `nit` | 98.1% | 4 fallos son docs escaneados con OCR ruidoso en dígitos |
  | `direccion` | 93.1% | — |
  | `razon_social` | 81.9% | Fallos típicos son docs escaneados |
  | `representante_legal` | 65.3% | Cuello de botella — 75 docs requerirán corrección humana |

  **Validación contra gold seed (3 RUT transcritos):** 4/6 campos correctos en docs digitales, 2/6 en el escaneado (RUT ASOVITAL). Confirma hipótesis: LFs excelentes sobre PyMuPDF, degradan con OCR.

  **Normalizaciones aplicadas post-extracción** (documentadas en nb 06 §7.5):
  - `municipio`: 4 variantes de Bogotá (`Bogotá D.C.`, `Bogotá D.C`, `Bogotá DC`, `BOGOTÁ D.C.`) → canónico `Bogotá D.C.`
  - `regimen`: `Simple` → `simple` (distinto de `simplificado` — son regímenes jurídicamente distintos)

  **Geografía del corpus:** 183/216 RUT son de Cali (85%) — confirma origen CCC. Implicación para §3.0 Clasificación: `municipio` no discrimina tipología.

- [ ] Cargar `rut_preanotaciones_labelstudio.json` en Label Studio → revisión humana solo para corregir (no anotar desde cero)
- [ ] Priorizar revisión humana de los 75 docs sin `representante_legal` y los ~6 docs escaneados (baja cobertura)
- [ ] Target: Cohen's Kappa > 0.85 en muestra de validación cruzada de 50 docs por tipología

#### Cédula — Anotación vía OCR Muestral (flujo alternativo)
*Justificación: 93% son imágenes escaneadas → el texto debe extraerse con OCR antes de poder anotar.*
- [x] **Seleccionar muestra estratificada de 60 Cédulas** (30 alta calidad + 30 ruidosas por `blur_score` Q1/Q3) — [Notebook 07](notebooks/07_preanotaciones_cedulas.ipynb) ejecutado 2026-04-18. Reproducible con `seed=42`. Outputs: `data/processed/cedulas_muestra_manifest.csv`, `cedulas_preanotaciones_labelstudio.json`, `cedulas_preanotaciones_summary.csv`.
- [x] **Aplicar regex laxa con anchor (NUMERO|CEDULA|CC|IDENTIFICACION) para `numero` únicamente** — única entidad viable sobre texto OCR ruidoso:

  | Estrato | Cobertura | Notas |
  |---|---|---|
  | alta_calidad | 47% (14/30) | Inesperadamente menor — anchors confundidos por contexto denso |
  | ruidosa | 80% (24/30) | Texto más concentrado, anchors más claros |
  | **Global** | **63.3% (38/60)** | Resto se anota manual |

  Los otros 7 campos (`nombre_completo`, `apellidos`, `fecha_nacimiento`, `lugar_nacimiento`, `fecha_expedicion`, `lugar_expedicion`, `sexo`, `rh`) van manuales en Label Studio.

- [ ] Cargar `cedulas_preanotaciones_labelstudio.json` en Label Studio → anotación bimodal (texto + imagen procesada)
- [ ] Revisar y corregir manualmente la salida OCR en Label Studio (bounding boxes visuales)
- [ ] Usar las 60 anotaciones corregidas como seed para fine-tuning; escalar con augmentación 3x
- [x] **Confirmado empíricamente:** regex LFs full no funcionan sobre Cédulas. Solo `numero` con anchor + verificación de longitud 7-10 dígitos da cobertura usable. Los otros campos fallan por variabilidad OCR.

#### Pólizas — Anotación Manual (muestra aleatoria)
> **Decisión v1.7:** Las entidades objetivo de Póliza (número_poliza, aseguradora, tomador, vigencia_desde, vigencia_hasta, valor_asegurado, prima_neta, amparo_principal) son estándar del contrato de seguro colombiano — iguales en todas las aseguradoras independientemente del layout. La identificación de aseguradora **no es requisito para estratificar** el set de entrenamiento. Selección: muestra aleatoria del corpus de Pólizas digitales.

- [x] Identificar aseguradoras presentes en el corpus — ejecutado en Notebook 02 (`aseguradoras_corpus.json`). Dato informativo, no bloqueante.
- [x] **Seleccionar aleatoriamente 120 Pólizas (80 train + 40 val)** — [Notebook 08](notebooks/08_preanotaciones_polizas.ipynb) con seed=42. Reproducible. Cobertura smoke test: `numero_poliza` 70%, `aseguradora` 50% (lookup). Outputs: `data/processed/polizas_muestra_manifest.csv`, `polizas_preanotaciones_labelstudio.json`, `polizas_preanotaciones_summary.csv`. Ver [reports/nb08_resultados.md](reports/nb08_resultados.md).
- [ ] Anotar manualmente **80 Pólizas** — conjunto de entrenamiento (en Label Studio, ~20 min/doc)
- [ ] Anotar **40 Pólizas** — conjunto de validación sin augmentación

#### Cámara de Comercio — Anotación Manual Reducida
*Justificación: formato consistente entre cámaras, solo varía logo. Layout-aware chunking es viable.*
- [x] **Seleccionar 120 CC (80 train + 40 val)** — [Notebook 09](notebooks/09_preanotaciones_camara_comercio.ipynb) con seed=42. Cobertura smoke test: `razon_social` 96.7%, `matricula` 80.8%, `nit` 64.2%. LFs de RUT reutilizadas + regex propia para matrícula mercantil. Outputs: `camara_comercio_muestra_manifest.csv`, `camara_comercio_preanotaciones_labelstudio.json`, `camara_comercio_preanotaciones_summary.csv`. Ver [reports/nb09_resultados.md](reports/nb09_resultados.md).
- [ ] Anotar manualmente **80 documentos** — conjunto de entrenamiento (~25 min/doc)
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

## DECISIONES ARQUITECTURALES — ALTERNATIVAS EVALUADAS

> *Esta sección registra rutas alternativas que la literatura sugiere y que se evaluaron conscientemente antes de adoptar el diseño actual. Se anotan para no perderlas y para revisitar si el diseño actual no alcanza los umbrales de F1 objetivo.*

### ALT-1 — Donut (Document Understanding Transformer)
**Qué es:** modelo end-to-end de NAVER (2022) que procesa la imagen del documento directamente y produce JSON estructurado, sin OCR como paso separado.

**Por qué aparece en literatura de IDP:** colapsa el pipeline OCR → LLM en un solo paso. Funciona bien para documentos de formato fijo (recibos, facturas, formularios).

**Por qué no se adoptó:**
- El corpus tiene 4 tipologías con estructuras radicalmente distintas — requeriría 4 modelos Donut separados
- El 70-91% de RUT, CC y Pólizas son PDFs digitales con texto extraíble gratis vía PyMuPDF — usar Donut ignora esa ventaja
- El modelo base fue entrenado en inglés; vocabulario jurídico colombiano requiere fine-tuning costoso desde cero
- No escala bien a documentos multipágina (CC de 8-12 páginas)

**Cuándo revisitar:** si la tasa de error en Cédulas (93% escaneadas) es inaceptable después de la Fase 4. Para ese caso específico — imágenes de ID con layout fijo y entidades estandarizadas — Donut sería una alternativa válida.

---

### ALT-2 — LayoutLMv3 (Microsoft, 2022)
**Qué es:** modelo multimodal pre-entrenado que recibe simultáneamente texto + coordenadas de bounding box + imagen de cada bloque. Estado del arte en benchmarks de document NER (FUNSD, CORD, DocVQA).

**Por qué es relevante para este corpus:**
- El RUT tiene 97 bloques por página en un formulario DIAN denso. La posición espacial de cada campo (qué está arriba, qué está al lado) es información crítica que PyMuPDF → texto plano → Llama 3 pierde completamente.
- Para RUT y CC (layout fijo), LayoutLMv3 fine-tuneado probablemente supera a Llama 3 8B en F1, con inferencia 10x más rápida y sin riesgo de alucinación (es un modelo discriminativo que clasifica tokens, no genera texto).

**Comparación directa con el diseño actual:**

| Criterio | Diseño actual (OCR → Llama 3) | LayoutLMv3 |
|---|---|---|
| Aprovecha layout espacial | No — texto plano | Sí — bounding boxes nativos |
| Riesgo de alucinación | Alto | Bajo (discriminativo) |
| Tamaño del modelo | 8B params (~5GB VRAM en 4-bit) | 125M params (<1GB VRAM) |
| Velocidad inferencia | ~5-15s/doc | <1s/doc |
| Funciona para Pólizas | Sí — layout variable | No — necesita layout consistente |
| Complejidad de anotación | Texto span | Bounding boxes por token (más trabajo) |

**Por qué no se adoptó como diseño principal:**
- Requiere anotar con coordenadas espaciales en Label Studio (más trabajo por documento)
- Para Pólizas (layout variable por aseguradora), LayoutLMv3 no es adecuado — el diseño actual con Llama 3 sigue siendo la mejor opción para esa tipología
- El proyecto ya tiene invertido el flujo de anotación en texto span

**Recomendación de revisión:** si en Fase 4 (evaluación) los experimentos muestran F1 < 0.85 en RUT o CC, considerar reemplazar la Etapa A (Arctic-Extract) por LayoutLMv3 fine-tuneado. Sería el Experimento 6 adicional.

**Para incorporar como Experimento 6 (opcional):**
```python
# Fine-tuning LayoutLMv3 para RUT
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Processor
# Requiere: anotaciones con bounding boxes por token
# Datos mínimos: ~100-150 RUT anotados con coordenadas
# Inferencia: processor(image, text, boxes) → logits por token
```

---

## FASE 3 — MODELADO (El Núcleo)

> **⚠️ REVISIÓN v2.0 — 2026-04-18:** esta fase fue reescrita. El esquema anterior ("Arquitectura de 2 Etapas: Arctic-Extract + Llama 3 8B") se abandonó por dos razones auditadas contra fuentes oficiales (abril 2026):
> 1. **Arctic-Extract no tiene pesos abiertos** — es servicio gestionado en Snowflake Cortex, incompatible con soberanía de datos colombiana (Ley 1581/2012).
> 2. **Llama 3 base (abril 2024) fue superado** por Llama 3.3, Qwen 2.5 y alternativas con mejor soporte de español.
>
> El nuevo esquema es **dos sub-fases con 3 candidatos cada una** (Clasificación + NER = 6 modelos), diseñado para comparación científica rigurosa. Todas las decisiones están documentadas en [PROPUESTA_MODELOS.md](PROPUESTA_MODELOS.md) con cita a paper revisado por pares o repositorio institucional oficial.

### 3.0 Clasificación de tipo de documento

**Tarea:** dado un documento (texto OCR + opcional imagen), predecir su tipología ∈ `{Cedula, RUT, Poliza, CC, Otros}`.
**Por qué es necesaria:** en producción los documentos llegan sin clasificar; además, el modelo NER usa la tipología como señal de *routing* para aplicar el esquema correcto.

**Candidatos (ver PROPUESTA_MODELOS.md §"Fase 2 — Clasificación"):**

| ID | Modelo | Qué es (breve) | Fundamentación científica | Hardware |
|---|---|---|---|---|
| **C-1** | **TF-IDF** (Term Frequency – Inverse Document Frequency) + Regresión Logística | Vectoriza cada documento pesando palabras por su frecuencia local y su rareza global en el corpus; luego un clasificador lineal decide la tipología sobre ese vector. | Spärck Jones, *Journal of Documentation* 1972 + Manning, Raghavan, Schütze, *Introduction to Information Retrieval* 2008 — baseline interpretable obligatorio | CPU, <10 MB |
| **C-2** | **BETO** fine-tuned (`dccuchile/bert-base-spanish-wwm-cased`) | Modelo BERT de 110M parámetros pre-entrenado desde cero en ~3 GB de español por la Universidad de Chile. Se fine-tunea para clasificación de texto. | Cañete et al., PML4DC @ ICLR 2020 + Devlin et al., NAACL 2019 | GPU 6 GB |
| **C-3** | **LayoutLMv3** fine-tuned | Modelo multimodal de Microsoft que ingesta texto + bounding boxes + parches de imagen en un mismo encoder. Estado del arte en documentos con layout. | Huang et al., ACM MM 2022 | GPU 8 GB |

**Tareas:**
- [ ] Implementar `notebooks/06_clasificacion_baseline.ipynb` — entrena C-1 sobre `corpus_ocr.csv` con split 70/15/15 (train/val/test) estratificado por folder
- [ ] Implementar `notebooks/07_clasificacion_beto.ipynb` — fine-tuning de C-2 con HuggingFace `Trainer`
- [ ] Implementar `notebooks/08_clasificacion_layoutlmv3.ipynb` — fine-tuning de C-3 con tokens + bounding boxes
- [ ] Evaluar los 3 sobre el mismo test set → reportar macro-F1, accuracy y matriz de confusión
- [ ] Seleccionar ganador por macro-F1 (desempate por VRAM → latencia)

### 3.1 Extracción NER (3 candidatos)

**Tarea:** dado un documento con tipología conocida, extraer las entidades del esquema JSON definido en §2.2 del plan.

**Candidatos (ver PROPUESTA_MODELOS.md §"Fase 3 — Extracción de Entidades"):**

| ID | Modelo | Qué es (breve) | Fundamentación científica | Hardware |
|---|---|---|---|---|
| **N-1** | **spaCy + BETO-NER** (token classification con BIO tags) | Pipeline spaCy que clasifica cada token con etiquetas Beginning/Inside/Outside usando BETO como backbone. Discriminativo — **no puede alucinar** entidades. | spaCy Zenodo DOI + BETO PML4DC 2020 + CoNLL-2002 Shared Task | CPU / GPU 6 GB |
| **N-2** | **Llama 3.3 8B-Instruct + QLoRA** (generativo, produce JSON) | LLM generativo de Meta ajustado con **QLoRA** (Quantized Low-Rank Adaptation: pesos base en 4 bits congelados + matrices pequeñas entrenables). Produce JSON directo con las entidades. | Grattafiori et al., arXiv:2407.21783 + Dettmers et al., NeurIPS 2023 + LlamaFactory ACL 2024 | GPU 24 GB |
| **N-3** | **LayoutLMv3** fine-tuned para token classification (discriminativo, layout-aware) | Mismo modelo que C-3 pero entrenado para clasificar tokens con BIO. Usa el layout espacial — ideal para RUT y CC con formularios de estructura fija. | Huang et al., ACM MM 2022 + Colakoglu et al., arXiv:2502.18179 | GPU 8 GB |

> **Nota sobre N-2:** la alternativa a Llama 3.3 dentro del mismo pipeline Unsloth/QLoRA es **Qwen2.5-7B-Instruct** (Qwen Team, arXiv:2412.15115). Si el fine-tuning de Llama 3.3 no converge, se intercambia sin cambiar el resto del pipeline.

**Tareas para N-1 (spaCy + BETO-NER):**
- [ ] Convertir anotaciones (§2.2) a formato BIO spans compatible con spaCy v3
- [ ] Entrenar con `spacy train` usando config basado en `spacy-transformers` + `dccuchile/bert-base-spanish-wwm-cased`
- [ ] Serializar modelo a `models/spacy-secop-ner-v1/` (<500 MB)
- [ ] Evaluación: F1 por entidad con `spacy evaluate`

**Tareas para N-2 (Llama 3.3 + QLoRA):**
- [ ] Instalar entorno: `pip install unsloth[colab-new] trl peft accelerate bitsandbytes xformers datasets transformers`
- [ ] Configurar carga del modelo base 4-bit:
  ```python
  from unsloth import FastLanguageModel
  model, tokenizer = FastLanguageModel.from_pretrained(
      model_name="meta-llama/Llama-3.3-8B-Instruct",  # o "Qwen/Qwen2.5-7B-Instruct"
      max_seq_length=2048,
      dtype=None,
      load_in_4bit=True,
  )
  ```
- [ ] Configurar adaptadores LoRA (r=16, alpha=16, dropout=0.05, target q/k/v/o + gate/up/down_proj)
- [ ] Template de prompt para NER en español colombiano:
  ```
  <|begin_of_text|><|start_header_id|>system<|end_header_id|>
  Eres un experto extractor de información de documentos oficiales colombianos.
  Responde SOLO con JSON válido, sin texto adicional.<|eot_id|>
  <|start_header_id|>user<|end_header_id|>
  Documento tipo: {doc_type}
  Texto: {document_text}
  Extrae: {entities_to_extract}<|eot_id|>
  <|start_header_id|>assistant<|end_header_id|>
  {expected_json_output}<|eot_id|>
  ```
- [ ] SFTTrainer con hiperparámetros para GPU 24 GB: 3 épocas, batch 2 + grad_accum 8, LR 2e-4, cosine scheduler, adamw_8bit, early stopping paciencia 2
- [ ] Guardar modelo: `models/llama33-secop-ner-v1/`
- [ ] Exportar a GGUF 4-bit si el modelo gana (para despliegue con Ollama — ver §3.2)

**Tareas para N-3 (LayoutLMv3 token classification):**
- [ ] Convertir anotaciones a formato con bounding boxes por token (extensión del esquema §2.2)
- [ ] Fine-tuning con `transformers.LayoutLMv3ForTokenClassification` sobre pares (texto, bbox, imagen)
- [ ] Evaluación: F1 por entidad, comparar contra N-1/N-2 especialmente en RUT (97 bloques) y CC (multipágina)

### 3.2 Despliegue con Ollama (condicional a ganador de N-2)

> **Condicional:** esta sección solo aplica si **N-2 gana la comparación de §4.3**. Si el ganador es N-1 (spaCy) o N-3 (LayoutLMv3), se sirve con FastAPI / un wrapper nativo de spaCy/transformers, no con Ollama.

- [ ] Crear `Modelfile` para Ollama:
  ```
  FROM ./models/llama33-secop-ner-v1-gguf/model.gguf
  SYSTEM "Eres SinergIA, experto extractor de documentos colombianos SECOP."
  PARAMETER temperature 0.1
  PARAMETER top_p 0.9
  PARAMETER num_ctx 2048
  ```
- [ ] Registrar: `ollama create sinergialab-ner -f Modelfile`
- [ ] Validar latencia: `ollama run sinergialab-ner "..."` < 5s por doc 1 página

### 3.3 Entregables de Fase 3

**Clasificación:**
- [ ] `notebooks/06_clasificacion_baseline.ipynb` (C-1)
- [ ] `notebooks/07_clasificacion_beto.ipynb` (C-2)
- [ ] `notebooks/08_clasificacion_layoutlmv3.ipynb` (C-3)
- [ ] `reports/clasificacion_resultados.csv` — tabla macro-F1 + accuracy + VRAM por candidato
- [ ] Ganador documentado en `reports/decision_clasificacion.md`

**NER:**
- [ ] `notebooks/09_ner_spacy.ipynb` (N-1)
- [ ] `notebooks/10_ner_llama33_qlora.ipynb` (N-2)
- [ ] `notebooks/11_ner_layoutlmv3.ipynb` (N-3)
- [ ] `models/spacy-secop-ner-v1/`, `models/llama33-secop-ner-v1/`, `models/layoutlmv3-secop-ner-v1/`
- [ ] `reports/ner_resultados.csv` — F1 por entidad + hallucination rate (solo N-2) + latencia
- [ ] Ganador documentado en `reports/decision_ner.md`

**Checkpoints y logs:**
- [ ] `checkpoints/` — checkpoints por época para los 3 modelos entrenables
- [ ] `logs/tensorboard/` — curvas de loss/F1 comparadas entre candidatos

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

> **Reescrito v2.0 (2026-04-18):** de 5 experimentos (con PaddleOCR descartado y Arctic-Extract sin pesos abiertos) a **6 experimentos comparables + 3 ablaciones opcionales**, alineados con los candidatos de §3.0 y §3.1.

**Principios del diseño:**
1. Mismo split 70/15/15 estratificado por tipología, semilla fija = 42.
2. Mismo gold set para evaluación final (15 docs ya existentes + extensión a 70 según §2.1.2).
3. Cada experimento reporta: hiperparámetros, tiempo de entrenamiento, VRAM pico, tamaño del modelo en disco, métricas primarias y secundarias.

**Experimentos de Clasificación (Fase 3 §3.0):**

| # | ID | Modelo | Input | Métrica primaria |
|---|---|---|---|---|
| 1 | C-1 | TF-IDF + Regresión Logística | Texto OCR | Macro-F1 (cota inferior clásica) |
| 2 | C-2 | BETO fine-tuned | Texto OCR | Macro-F1 |
| 3 | C-3 | LayoutLMv3 fine-tuned | Texto + bbox + imagen | Macro-F1 |

**Experimentos de NER (Fase 3 §3.1):**

| # | ID | Modelo | Input | Métrica primaria | Métricas adicionales |
|---|---|---|---|---|---|
| 4 | N-1 | spaCy + BETO-NER | Texto OCR con BIO tags | F1 por entidad | Latencia, tamaño modelo |
| 5 | N-2 | Llama 3.3 + QLoRA (o Qwen2.5-7B) | Texto OCR + prompt estructurado | F1 por entidad | **Hallucination rate** (target <2%), latencia |
| 6 | N-3 | LayoutLMv3 token classification | Texto + bbox por token + imagen | F1 por entidad (por tipología, atención en RUT/CC) | Latencia |

**Ablaciones opcionales (condicionales al resultado de los 6 experimentos primarios):**

| # | Ablación | Cuándo ejecutar |
|---|---|---|
| A1 | Pipeline completo: clasificador ganador → NER ganador (end-to-end) | Siempre que exista ganador de cada sub-fase |
| A2 | NER-ganador con prompt **sin** doc_type (inferencia libre del tipo) | Si N-2 gana, para medir dependencia del hint de tipología |
| A3 | Ensemble N-1 (span) + N-3 (layout) con reconciliación por reglas | Si ningún modelo supera F1 objetivo en alguna tipología |

**Gestión de VRAM (aplicable a experimentos 5 y A3):**
Inferencia secuencial — nunca cargar dos modelos simultáneamente. Patrón:
```python
import torch, gc

model_a = load_model_a()                     # ~8 GB VRAM
results_a = run_batch(model_a, val_docs)
del model_a; torch.cuda.empty_cache(); gc.collect()
assert torch.cuda.memory_allocated() < 1e9, "VRAM no liberada"

model_b = load_model_b()                     # ~7 GB VRAM
results_b = run_batch(model_b, val_docs)
del model_b; torch.cuda.empty_cache(); gc.collect()

final = merge_results(results_a, results_b)   # en CPU
```

- [ ] Ejecutar los 6 experimentos primarios
- [ ] Evaluar ablaciones A1-A3 según criterios documentados
- [ ] Generar tabla comparativa final en `reports/experiment_results.csv` con: ID, modelo, F1 primario, F1 secundario, VRAM pico, tamaño MB, latencia ms/doc
- [ ] Documentar decisión final en `reports/decision_arquitectura.md` — pipeline ganador = Clasificador_X + NER_Y

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
- [ ] Notebook `12_evaluacion_metricas.ipynb` con evaluación completa de los 6 experimentos primarios + ablaciones
- [ ] `reports/experiment_results.csv` — tabla comparativa de los 6 experimentos (+ ablaciones si aplicaron)
- [ ] `reports/error_analysis.md` — análisis cualitativo de fallos
- [ ] `reports/decision_arquitectura.md` — pipeline ganador (Clasificador + NER) con justificación
- [ ] Decisión documentada: ¿el pipeline cumple umbrales para avanzar a la siguiente fase?

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
