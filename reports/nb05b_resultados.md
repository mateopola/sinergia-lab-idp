# Resultados — Notebook 05b · Cierre de Gaps OCR (corpus completo)

**Fase CRISP-DM++:** 2.1.4 — Cobertura completa del corpus
**Notebook:** [05b_cierre_gaps_ocr.ipynb](../notebooks/05b_cierre_gaps_ocr.ipynb)
**Fecha de ejecución:** 2026-04-18
**Output principal:** `data/processed/corpus_ocr.csv` (corpus textual completo)

---

## 1. Metadatos de ejecución

- Python 3.12, CPU
- Duración: **~20 min** (8 min Parte A + 10 min Parte B + consolidación)
- Input previo: `corpus_ocr.csv` con solo escaneados (1,669 páginas)
- Output: corpus unificado con escaneados (EasyOCR) + digitales (PyMuPDF)

## 2. Resumen cuantitativo

### 2.1 Ejecución por parte

| Parte | Motor | Filas producidas | Tiempo |
|---|---|---|---|
| A — 9 imágenes `.jpg`/`.jpeg` escaneadas | EasyOCR | 9 | ~8 min |
| B — 590 PDFs digitales | PyMuPDF | 11,576 | ~10 min |
| Consolidación + validación | — | — | ~1 min |

### 2.2 Cobertura final del corpus

| Métrica | Antes del 05b | Después del 05b | Delta |
|---|---|---|---|
| Documentos | 403 | **960** | +557 |
| Páginas | 1,669 | **13,254** | +11,585 |
| Chars totales | 3.5 M | **32.6 M** | **+9×** |
| Errores | 0 | 0 | — |

### 2.3 Páginas por motor en corpus final

| Engine | Páginas | % |
|---|---|---|
| `pymupdf` (digitales) | 11,576 | 87.3% |
| `easyocr` (escaneados) | 1,678 | 12.7% |

### 2.4 Validación post-cierre contra gold seed

Idéntica a §2.6.2 del OCR_BENCHMARK.md — métricas no se movieron (las 15 transcripciones gold son escaneados, que no se tocaron en 05b):

| Folder | N | CER medio | Entity recall |
|---|---|---|---|
| CAMARA DE CIO | 3 | 0.218 | 0.643 |
| CEDULA | 6 | 0.311 | 0.563 |
| POLIZA | 3 | 0.229 | 0.768 |
| rut | 3 | 0.330 | 0.889 |
| **Global** | **15** | **0.280** | **0.685** |

✅ Merge limpio — 0 diferencias en las 15 filas de validación.

## 3. Hallazgos

### 🟢 Hallazgo 1 — Cierre de gap A (9 imágenes) trivial

Eran 9 docs (7 cédulas/RUT + 2 TP). Causa raíz: el filtro del nb 05 (`md5_index = {md5_file(p): p for p in DATA_RAW.rglob('*.pdf')}`) excluía cualquier md5 no mapeable a PDF. **Fix:** no filtrar por `pdf_path` cuando `es_escaneado=True` (se usa `ruta_imagen_procesada` directamente).

### 🟢 Hallazgo 2 — PyMuPDF es 1000× más rápido que EasyOCR

11,576 páginas digitales procesadas en ~10 min = ~0.05 s/pág con PyMuPDF. Comparable: EasyOCR requirió 23h para 1,669 páginas (~50 s/pág). Confirma la decisión arquitectural de bifurcar por `es_escaneado`.

### 🔴 Hallazgo 3 — 463 páginas PyMuPDF con 0 chars (4% del total)

Concentradas en Pólizas (432 de 1,918 páginas). Son **páginas-imagen embebidas** dentro de PDFs "digitales" — certificados escaneados, firmas notariadas anexas que un PDF marca como digital pero cuyo contenido es bitmap.

**No hay docs con todas las páginas vacías** (verificado) → son páginas sueltas mezcladas con texto real. Opción futura: tercer pase EasyOCR sobre estas 463 páginas específicas recuperaría ~400 pág.

Por ahora se aceptan como `text_chars=0` trazable en `corpus_ocr_summary.csv`.

### 🟡 Hallazgo 4 — Mojibake en `folder` de digitales

Los escaneados tienen `folder` ASCII (`CEDULA`, `POLIZA`, `CAMARA DE CIO`, `rut`, `OTROS`) normalizado por nb 04. Los digitales heredan `category` de `quality_report_completo.csv` con mojibake doble-encoded (`CÃ\x83Â©dula` para `Cédula`). Resultado: 10 folders aparentes donde deberían ser 5.

**Fix ligero pendiente para §2.2:** añadir normalización de `folder` al leer `corpus_ocr.csv` (mapeo 1-1 conocido, <5 líneas). Los notebooks 06 y 07 ya lo manejan con `str.lower().str.contains()`.

## 4. Anomalías y limitaciones

- 4 docs corruptos de Fase 1 (n_pages=0) excluidos
- Backup `corpus_ocr_preV2_backup.csv` se conserva local (gitignored por PII) como punto de restauración
- Docs digitales con contenido solo-imagen no recuperables sin tercer pase OCR

## 5. Implicaciones para fases posteriores

1. **Corpus textual listo para Fase 2.2** — nb 06 y 07 ya consumen `corpus_ocr.csv`
2. **Entrenamiento:** los 960 docs con 13,254 páginas y 32.6 M chars son base suficiente para fine-tuning
3. **Fase 2.3 Chunking:** este corpus es el input directo de `chunk_document()` para producir `train.jsonl`/`val.jsonl`

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/corpus_ocr.csv` | Corpus textual completo (13,254 filas) | ❌ PII |
| `data/processed/corpus_ocr_summary.csv` | Métricas sin texto | ✅ |
| `data/processed/corpus_ocr_preV2_backup.csv` | Respaldo pre-merge | ❌ PII |
| `data/gold/ocr_corpus_validation.csv` | Re-validación post-cierre | ✅ |

## 7. Referencias internas

- [OCR_BENCHMARK.md §2.6.3](../OCR_BENCHMARK.md) — ejecución del cierre (canonical)
- [PLAN_MODELADO_CRISPDM.md §2.1.4](../PLAN_MODELADO_CRISPDM.md) — tasks `[x]` cerradas
