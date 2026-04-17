# Plan de Desarrollo — OCR Local del Corpus (equipo SinergIA Lab)

**Fase:** Desarrollo (no producción).
**Referencia:** Fase 2 CRISP-DM++ §2.1.1 (decisión EasyOCR).
**Estrategia:** Ejecución 100% local con CPU. Sin dependencias de Colab, Drive o cuentas compartidas.
**Objetivo:** generar `corpus_ocr.csv` con el texto de los 1,014 documentos del corpus, para habilitar §2.2 (pre-anotaciones RUT) y fases siguientes.

---

## 1. Por qué local CPU

Tras evaluar el flujo actual del equipo (varios miembros corriendo en Colab GPU con código ligeramente distinto por tipología), decidimos **resetear y unificar**:

- **Reproducibilidad:** una persona clona el repo y corre los mismos 2 notebooks, sin configurar cuentas ni Drive.
- **Trazabilidad:** todo el código versionado en Git; outputs con metadata de ejecución (timestamp, commit hash, versiones).
- **Seguridad:** cero PII viaja a servicios externos.
- **Consistencia:** todo el equipo usa exactamente el mismo pipeline para todas las tipologías.

**Trade-off aceptado:** ~20-27 horas de CPU vs ~30-60 min en GPU. Se corre una vez overnight.

---

## 2. Arquitectura del pipeline

Dos etapas separadas en dos notebooks, siguiendo el patrón ya establecido en el repo (notebooks 01, 02, 03).

```
┌─────────────────────────────────────────────────────────────┐
│                       data/raw/                             │
│  1,014 PDFs (CEDULA, rut, POLIZA, CAMARA DE CIO, OTROS)     │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │  Notebook 04            │  ← Preprocesamiento visual
          │  04_preprocesamiento_   │  (PDF → imágenes + OpenCV)
          │  imagenes.ipynb         │
          └────────────┬────────────┘
                       │
                       ▼
          data/processed/images/
          processed_{md5}_page_{N}.jpg  (~5,000 imágenes, gitignore)
          image_manifest.csv            (metadata por página)
                       │
          ┌────────────▼────────────┐
          │  Notebook 05            │  ← OCR + reconstrucción
          │  05_ocr_corpus.ipynb    │  (EasyOCR CPU sobre imágenes)
          └────────────┬────────────┘
                       │
                       ▼
          data/processed/
          corpus_ocr.csv          (texto completo + bboxes)  ← gitignore
          corpus_ocr_summary.csv  (métricas sin texto)       ← commitear
```

### 2.1 Separación de responsabilidades

| Etapa | Qué hace | Reusa código de |
|---|---|---|
| **Notebook 04 — Preprocesamiento** | PDF → imagen 300 DPI → detect_cover → deskew → denoise → CLAHE → binarize → normalize_dpi | `src/preprocessing/pipeline.py` (funciones ya implementadas en Fase 2 §2.1) |
| **Notebook 05 — OCR** | Lee imágenes procesadas → EasyOCR CPU → reconstruir texto desde bboxes → consolidar CSV | `easyocr.Reader` + función `reconstruir_texto()` local |

**Por qué separados:**
- Si mañana queremos cambiar parámetros OpenCV (CLAHE clip, Otsu threshold) → re-corremos 04 sin re-OCR
- Si mañana queremos probar otro motor OCR → re-corremos 05 sin re-preprocesar
- Debugging aislado: si falla el texto, sabemos si fue la imagen o el OCR

---

## 3. Schema acordado (page-level)

**Granularidad:** una fila por **página**, no por documento. Alineado con la convención del equipo.

### 3.1 `image_manifest.csv` (output de notebook 04)

| Columna | Tipo | Descripción |
|---|---|---|
| `md5` | str | Hash del PDF original (primary key de doc) |
| `doc_id` | str | = `md5` (redundante pero claro en uso) |
| `filename` | str | Nombre legible del PDF |
| `folder` | str | Tipología (CEDULA, rut, POLIZA, CAMARA DE CIO, OTROS) |
| `page_num` | int | 1-indexed |
| `n_pages_total` | int | Páginas totales del PDF |
| `es_escaneado` | bool | Flag de Fase 1 (True → requiere OCR) |
| `ruta_imagen_original` | str | Path de la imagen sin procesar (intermedia, efímera) |
| `ruta_imagen_procesada` | str | Path de `processed_{md5}_page_{N}.jpg` |
| `width`, `height` | int | Dimensiones tras preprocesamiento |
| `preprocess_elapsed_s` | float | Tiempo de OpenCV para esa página |
| `timestamp` | str | ISO-8601 |

Clave compuesta única: `(md5, page_num)`.

### 3.2 `corpus_ocr.csv` (output de notebook 05)

| Columna | Tipo | Descripción |
|---|---|---|
| `md5` | str | Primary key de doc |
| `doc_id` | str | = `md5` |
| `filename` | str | Nombre legible |
| `folder` | str | Tipología |
| `page_num` | int | 1-indexed |
| `engine` | str | `easyocr` (escaneados) o `pymupdf` (digitales) |
| `engine_version` | str | Versión del motor |
| `gpu_used` | bool | False en dev local |
| `texto_ocr` | str | Texto reconstruido (orden natural de lectura) |
| `bboxes_json` | str | JSON con `[{bbox, text, confidence}, ...]` por región (alimenta Label Studio en §2.2) |
| `n_detections` | int | Cajas detectadas |
| `text_chars` | int | Longitud de `texto_ocr` |
| `elapsed_s` | float | Tiempo OCR de la página |
| `timestamp` | str | ISO-8601 |
| `commit_hash` | str | SHA del commit del repo |
| `error` | str\|null | null si OK; traceback corto si falló |

### 3.3 `corpus_ocr_summary.csv` (se commitea al repo)

Mismas columnas **excepto `texto_ocr` y `bboxes_json`**. Así el equipo puede revisar avance y errores sin exponer PII.

---

## 4. Políticas de caché y reanudación

Ambos notebooks implementan **checkpoint por bloques** (tomado del estilo que ya usa tu equipo):

- Se procesa en bloques de N (default 50 páginas por bloque)
- Cada bloque guarda su CSV parcial: `data/processed/ocr_blocks/resultado_bloque_{k}.csv`
- Log de páginas procesadas: `data/processed/ocr_blocks/processed_log.csv`
- Si un notebook se interrumpe, al re-ejecutarse **salta las páginas ya presentes en el log**
- Al terminar todos los bloques, se consolidan en el CSV final

Para forzar re-procesamiento completo: flag `FORCE_REPROCESS = True` en la primera celda del notebook.

---

## 5. Archivos que se versionan (commit) y los que no

| Archivo | Commit | Razón |
|---|---|---|
| `notebooks/build_notebook_04.py`, `build_notebook_05.py` | ✅ | Código fuente |
| `notebooks/04_preprocesamiento_imagenes.ipynb`, `05_ocr_corpus.ipynb` | ✅ | Notebook generado |
| `data/processed/images/` (imágenes) | ❌ (gitignore) | Varios GB, regenerables |
| `data/processed/image_manifest.csv` | ✅ | Metadata pequeño, útil para auditoría |
| `data/processed/ocr_blocks/` | ❌ (gitignore) | Intermedios |
| `data/processed/corpus_ocr.csv` | ❌ (gitignore) | Texto completo = PII |
| `data/processed/corpus_ocr_summary.csv` | ✅ | Métricas sin texto |

---

## 6. Procedimiento paso a paso

### 6.1 Para quien desarrolle el pipeline (Mateo + Claude)

| Paso | Tarea | Duración | Output |
|---|---|---|---|
| 1 | Este plan aprobado | ✅ | `PLAN_OCR_EQUIPO.md` |
| 2 | `build_notebook_04.py` + generar `04_preprocesamiento_imagenes.ipynb` | 45 min | Notebook 04 |
| 3 | Correr nb 04 sobre 10 docs de prueba | 15 min | 10 × `processed_*.jpg` + manifest parcial |
| 4 | Validar visualmente 5 imágenes procesadas al azar | 10 min | OK / ajustar parámetros |
| 5 | `build_notebook_05.py` + generar `05_ocr_corpus.ipynb` | 45 min | Notebook 05 |
| 6 | Correr nb 05 sobre los 10 docs de prueba | 30 min | `corpus_ocr.csv` parcial de 10 docs |
| 7 | Validar contra gold seed (§2.1.2): comparar texto OCR vs transcripciones humanas de los docs comunes | 30 min | Métricas CER/entity_recall consistentes con benchmark |
| 8 | Corrida completa — nb 04 | ~1-2h | image_manifest.csv + ~5,000 imágenes |
| 9 | Corrida completa — nb 05 | ~20-27h overnight | `corpus_ocr.csv` final |
| 10 | Checks de validación + docs | 30 min | Summary commiteado + plan actualizado |

### 6.2 Para cualquier otro miembro del equipo

Después de merge a `main`:

```bash
git pull
# Abrir VSCode y ejecutar en orden:
# 1. notebooks/04_preprocesamiento_imagenes.ipynb  (Run All)
# 2. notebooks/05_ocr_corpus.ipynb                 (Run All)
```

Mismo flujo, mismo resultado. Si ya hay `corpus_ocr.csv` local, los notebooks lo detectan y no re-procesan.

---

## 7. Validación post-corrida

### 7.1 Checks automáticos (celda final del nb 05)

- [ ] Cantidad de filas = Σ páginas del corpus (verificable contra `quality_report_completo.csv`)
- [ ] Todos los `md5` presentes en `quality_report_completo.csv`
- [ ] < 2% de páginas con `error != null`
- [ ] Páginas con `text_chars == 0`: documentar cuáles (algunos escaneados muy degradados pueden salir vacíos; es normal)
- [ ] Distribución por motor: digitales → pymupdf, escaneados → easyocr

### 7.2 Check cualitativo contra gold seed

Los 15 docs del gold seed (§2.1.2) tienen transcripciones humanas en `data/gold/transcriptions/`. El notebook 05 incluye una celda final que:

1. Carga `gold_seed_manifest.csv`
2. Lee las transcripciones humanas (ground truth)
3. Lee el texto OCR producido para esos 15 docs
4. Calcula CER y entity_recall
5. Compara con los valores reportados en el benchmark original (EasyOCR CPU: CER ≈ 0.276, entity_recall ≈ 0.55)

Tolerancia: ±5% (leve variación por preprocesamiento OpenCV adicional).

Si los valores caen fuera, algo cambió en el pipeline y hay que investigar antes de usar el CSV.

---

## 8. Tiempo total estimado

| Etapa | Duración |
|---|---|
| Desarrollo (pasos 1-7) | ~4-5 horas (distribuibles en varias sesiones) |
| Corrida preprocesamiento (paso 8) | ~1-2 horas |
| Corrida OCR completa (paso 9) | ~20-27 horas (overnight, desatendida) |
| Validación + docs (paso 10) | 30 min |

**Total humano activo:** ~5 horas
**Total reloj:** 1-2 días (incluyendo el overnight)

---

## 9. Qué sigue después

Una vez cerrado este plan y con `corpus_ocr.csv` disponible:

- **§2.2 Pre-anotaciones RUT:** las LFs ya implementadas en notebook 02 leen del CSV y generan pre-etiquetas para los 235 RUTs.
- **§2.3 Chunking:** el texto se divide por tipología según decisiones del plan maestro.
- **Fase 3 Fine-tuning:** texto + anotaciones alimentan el entrenamiento NER.
- **Fase 4 Evaluación:** gold seed se usa para medir F1 final del modelo.

El CSV queda como **insumo textual único** para todo lo que sigue. Si se re-entrenan modelos o se cambian decisiones de chunking, no se re-OCR — se lee del CSV.

---

## 10. Historial de cambios

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-04-15 | Plan inicial enfocado en Colab | — |
| 2026-04-15 | **Reset:** enfoque local CPU, 2 notebooks separados, schema page-level, sin dependencia de Drive | Mateo + Claude |
