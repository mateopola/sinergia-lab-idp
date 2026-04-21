# Resultados — Notebook 04 · Preprocesamiento Visual de Escaneados

**Fase CRISP-DM++:** 2.1 — Pipeline de Preprocesamiento Visual
**Notebook:** [04_preprocesamiento_imagenes.ipynb](../notebooks/04_preprocesamiento_imagenes.ipynb)
**Fecha de ejecución:** 2026-04-17
**Output principal:** `data/processed/image_manifest.csv` (1,678 filas, commiteable)

---

## 1. Metadatos de ejecución

- Python 3.12, CPU
- Duración: **~10 min** (tras corrección del pipeline sin `binarize`)
- Input: subset de escaneados (`es_escaneado==True`) de `quality_report_completo.csv`
- Output: 1,678 JPGs procesados en `data/processed/images/` (1.9 GB) + manifest

## 2. Resumen cuantitativo

### 2.1 Corrida productiva final

| Métrica | Valor |
|---|---|
| Documentos procesados | **412** (403 PDFs escaneados + 9 imágenes directas `.jpg/.jpeg`) |
| Páginas procesadas | **1,678** |
| Errores | **0** |
| Tiempo total | ~10 min |
| Disco ocupado | 1.9 GB |
| Bloques de checkpoint | 34 (`image_bloque_0001..0034.csv`) |

### 2.2 Pipeline aplicado

```
deskew → denoise → enhance_contrast (CLAHE) → normalize_dpi (300 DPI)
```

**`binarize` omitido deliberadamente** (decisión OCR_BENCHMARK.md §2.6.0) — output: imagen grayscale replicada a 3 canales.

### 2.3 Cobertura por tipología

| Folder | Docs | Páginas |
|---|---|---|
| CEDULA | 308 | 356 |
| POLIZA | 59 | 1,024 |
| rut | 24 | 116 |
| CAMARA DE CIO | 16 | 160 |
| OTROS | 5 | 22 |
| **Total** | **412** | **1,678** |

## 3. Hallazgos

### 🟢 Hallazgo 1 — Filtrar escaneados ahorra 12 GB de disco

Pipeline inicial procesaba los 1,014 docs generando 14 GB de JPGs. Tras filtrar `es_escaneado==True` solo se procesan los 412 escaneados → 1.9 GB. Los 548+ digitales van directo a PyMuPDF en nb 05 sin preprocesamiento visual.

### 🟢 Hallazgo 2 — Soporte para imágenes directas (9 docs)

El SECOP incluye 9 documentos entregados como `.jpg`/`.jpeg` (cédulas, RUT, TP). Se agregó soporte via `load_page_as_image()` que bifurca por extensión (PDF → fitz, imagen → `cv2.imread`). Extendido `SUPPORTED_EXTS = {'.pdf', '.jpg', '.jpeg', '.png'}`.

### 🔴 Hallazgo 3 — Bug de numeración de bloques (resuelto)

`image_bloque_NNNN.csv` se sobrescribía en re-ejecuciones (numeración reiniciaba desde 0001). **Fix:** numeración continua desde el último bloque existente (`next_block_num + bk`). Validado post-fix.

### 🟢 Hallazgo 4 — Paths absolutos para interoperabilidad con nb 05

Originalmente `image_manifest.csv` tenía paths relativos `data/processed/images/...`. Al ejecutar nb 05 desde `notebooks/`, esos paths no resolvían → 100% errores en primera corrida nb 05. **Fix:** `str(out_path.resolve())` en nb 04 + resolución defensiva en nb 05.

## 4. Anomalías y limitaciones

- 4 docs con `n_pages=0` (corruptos desde Fase 1) — excluidos
- Mojibake en nombres de archivo → resuelto con índice MD5
- La corrida inicial con `binarize` hubiera demorado ~51h (1,678 × 110s/pág). Post-fix: 10 min.

## 5. Implicaciones para fases posteriores

1. **Nb 05** itera `image_manifest.csv` aplicando EasyOCR sobre `ruta_imagen_procesada`
2. **Nb 05b** completa con digitales + 9 imágenes que fueron filtradas indebidamente
3. **Fase 3** los modelos que requieran imagen (LayoutLMv3, Qwen3-VL) consumen estos mismos 1,678 JPGs preprocesados

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/image_manifest.csv` | 1,678 filas × 13 columnas con paths absolutos | ✅ |
| `data/processed/images/processed_{md5}_page_{N}.jpg` | JPGs grayscale 300 DPI | ❌ (1.9 GB) |
| `data/processed/image_blocks/image_bloque_NNNN.csv` | Checkpoints por bloque de 50 | ❌ |
| `data/processed/fig12_preprocesamiento_test.png` | Visual antes/después de 3 docs piloto | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §2.1](../PLAN_MODELADO_CRISPDM.md) — checklist marcada
- [OCR_BENCHMARK.md §2.6.1](../OCR_BENCHMARK.md) — ejecución productiva documentada
