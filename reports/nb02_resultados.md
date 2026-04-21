# Resultados — Notebook 02 · Pipeline de Preprocesamiento + LFs + Chunking

**Fase CRISP-DM++:** 2.0 / 2.2 / 2.3
**Notebook:** [02_preprocesamiento_pipeline.ipynb](../notebooks/02_preprocesamiento_pipeline.ipynb)
**Fecha de ejecución:** 2026-04-08
**Output principal:** módulo productivo `src/preprocessing/pipeline.py`

---

## 1. Metadatos de ejecución

- Python 3.12, entorno local CPU
- Duración: ~15 min
- Propósito: definir y validar sobre piloto las funciones del pipeline que luego se aplicarán al corpus completo en notebooks posteriores (04, 05, 05b, 06)

## 2. Resumen cuantitativo

### 2.1 Funciones implementadas (12 funciones)

**Preprocesamiento visual** (4 funciones):
- `deskew()` — corrección de rotación con `cv2.minAreaRect`
- `denoise()` — filtro gaussiano + Non-Local Means
- `enhance_contrast()` — CLAHE (Contrast Limited Adaptive Histogram Equalization)
- `normalize_dpi()` — re-muestreo a 300 DPI
- `binarize()` — Otsu (implementada pero **NO USADA** en pipeline productivo, ver nb 03)

**Detección** (1 función):
- `detectar_portada()` — heurística lexicon+blocks por tipología

**Labeling Functions RUT** (1 función):
- `extraer_entidades_rut()` — 6 entidades: nit, razon_social, regimen, direccion, municipio, representante_legal

**Filtrado** (1 función):
- `filtrar_ciiu_rut()` — elimina vocabulario CIIU para embeddings limpios

**Chunking** (3 funciones):
- `sliding_window_chunks()` — 512 tokens / 30% overlap
- `layout_aware_chunks()` — `cv2.HoughLinesP` para separar bloques CC
- `chunk_document()` — dispatcher por tipología

### 2.2 Validación sobre piloto (5 docs por tipología)

| Entidad RUT | Precisión sobre piloto |
|---|---|
| nit | 5/5 (100%) |
| razon_social | 5/5 (100%) |
| regimen | 5/5 (100%) |
| direccion | 5/5 (100%) |
| municipio | 5/5 (100%) — todos Cali en muestra |
| representante_legal | 5/5 (100%) |

> La validación a escala completa (216 RUT) está documentada en [nb06_resultados.md](nb06_resultados.md). Sobre el corpus real la precisión es menor por diversidad de layouts.

## 3. Hallazgos

### 🟢 Hallazgo 1 — Estructura no intuitiva del texto PyMuPDF en RUT

PyMuPDF extrae el RUT en un orden **no natural**: primero los LABELS del formulario (~1,500 chars de nombres de casillas), después los VALORES reales. Esto tiene dos implicaciones:

1. **No se puede truncar** el texto en headers como "Actividad económica" (eliminaría valores).
2. Las LFs deben operar sobre **texto completo** con patrones basados en valores, no en posiciones.

Justifica la estrategia de `filtrar_ciiu_rut()` por **eliminación de tokens** en vez de truncado.

### 🟢 Hallazgo 2 — Forma jurídica como discriminador de razón social

El patrón más robusto para `razon_social` son líneas en MAYÚSCULAS con sufijo jurídico colombiano conocido (`LTDA`, `SAS`, `S.A`, `E.U`, `EIRL`). Menos falsos positivos que buscar nombres por capitalización.

### 🟡 Hallazgo 3 — Detección de portadas solo viable en Póliza/CC

Cédulas dispararon falsos positivos (3 docs) porque la página 1 es una imagen con poco texto, criterio que también cumplen portadas reales. Decisión: **desactivar detección de portadas en Cédulas**.

### 🟢 Hallazgo 4 — RUT es el único caso que supera el chunking simple

151/235 RUT superan 1,800 tokens BPE. La función `chunk_document` dispatchea:
- Cédula → sin chunking
- RUT → sliding window (inicialmente "sin chunking" en v1.1; corregido v1.4)
- Póliza → sliding window
- CC → layout-aware (`HoughLinesP` detecta separadores horizontales)

## 4. Anomalías y limitaciones

- Regex `direccion` usa nomenclatura Colombia (`CL/CR/AV/TV/KR`); fallaría en direcciones con formato distinto
- Regex `municipio` es lista cerrada de 17 ciudades; no cubre veredas o municipios pequeños
- Regex `representante_legal` requiere que el patrón exacto `APELLIDOS NOMBRES\nRepresentante legal` aparezca — fuente de la baja cobertura del 65% sobre corpus completo (ver nb 06)

## 5. Implicaciones para fases posteriores

1. **Nb 04** usa `preprocess_pipeline()` sin `binarize` (decisión nb 03)
2. **Nb 06** aplica `extraer_entidades_rut()` a los 216 RUT del corpus
3. **Fase 2.3** aplicará `chunk_document()` sobre el corpus anotado para generar `train.jsonl`/`val.jsonl`

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `src/preprocessing/pipeline.py` | Módulo productivo con 12 funciones | ✅ |
| `data/processed/aseguradoras_corpus.json` | Aseguradoras detectadas en corpus de Pólizas | ✅ |
| `data/processed/vocabulario_dominio.json` | Términos dominio por tipología | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §2.0 / §2.2 / §2.3](../PLAN_MODELADO_CRISPDM.md)
- [OCR_BENCHMARK.md §2.6.0](../OCR_BENCHMARK.md) — decisión sobre `binarize()`
