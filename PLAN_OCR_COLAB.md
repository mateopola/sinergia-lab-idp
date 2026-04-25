# Plan OCR Unificado en Colab GPU

**Fecha decisión inicial:** 2026-04-21
**Decisiones operativas confirmadas:** 2026-04-21
**Estado:** En ejecución
**Documentos relacionados:** [PLAN_MODELADO_CRISPDM.md §2.1.5](PLAN_MODELADO_CRISPDM.md) · [OCR_BENCHMARK.md](OCR_BENCHMARK.md) (histórico)

---

## 1. Decisión arquitectural

A partir de esta fecha el corpus se procesa **íntegramente con EasyOCR** (escaneados Y digitales), eliminando el selector híbrido EasyOCR/PyMuPDF que estaba en producción desde nb05/nb05b.

### Por qué

**Paridad train-inference.** En producción, el sistema recibe documentos de origen mixto sin saber a priori cuál es cuál. Si entrenamos modelos sobre texto procedente de dos motores (perfecto vs ruidoso), introducimos un **distribution shift** que degrada generalización.

### Costo aceptado

| Métrica | Antes (híbrido) | Después (EasyOCR único) |
|---|---|---|
| CER promedio digitales | ~0.00 (texto perfecto PyMuPDF) | ~0.28 (típico EasyOCR) |
| CER promedio escaneados | ~0.28 | ~0.28 |
| **Uniformidad train-inference** | ❌ | ✅ |
| Bboxes por palabra | Solo escaneados (1,674) | **100% del corpus** (resuelve gap C-3 LayoutLMv3) |

La degradación intencional de calidad se reporta en el documento académico como decisión deliberada, no como mejora.

---

## 2. Decisiones operativas confirmadas (2026-04-21)

### 2.1 Eliminación de la clase "Otros"

Se elimina la clase **`Otros`** del corpus de entrenamiento. Razón: **no aporta valor para el clasificador** (es heterogénea, sin patrón visual o textual común) y solo introduce ruido. Los 9 documentos de esa carpeta no se procesan.

**Clases finales del clasificador:** `{Cedula, RUT, Poliza, CamaraComercio}` — 4 clases.

### 2.2 Límite de 10 páginas por documento

Se procesa un máximo de **10 páginas por documento**. Los documentos con más páginas se truncan a las primeras 10.

**Justificación:**
- 79% del corpus ya tiene ≤ 10 páginas naturalmente
- BETO y LayoutLMv3 truncan a 512 tokens (~1 página de texto denso) de todas formas — más páginas no aporta a esos modelos
- TF-IDF tiene de sobra con 10 págs × 2,000 chars = 20,000 chars por doc
- Las páginas 1-3 son las más informativas para clasificar (carátulas, encabezados, formularios estructurados)
- Para NER (futuro): si alguna tipología necesita más páginas, el cache MD5 permite re-OCR extendido sin re-procesar todo

### 2.3 Eliminación de 2 RUPs mal clasificados en RUT (resuelto 2026-04-21)

Detectados durante el inventario y **eliminados** del corpus:

| Filename | Folder original | Págs | Acción tomada |
|---|---|---|---|
| `10. REGISTRO UNICO DE PROPONENTES.pdf` | rut/ | 1,331 | Movido a `data/raw/_quarantine_misclassified/` |
| `Registro Unico de Propnentes (RUP).pdf` | rut/ | 606 | Movido a `data/raw/_quarantine_misclassified/` |

**Razón:** RUP (Registro Único de Proponentes) ≠ RUT (Registro Único Tributario). Son trámites distintos. Estos 2 docs contaminaban la clase RUT con ejemplos que no son RUTs.

**Limpieza ejecutada:**
- 2 PDFs movidos a `data/raw/_quarantine_misclassified/` (se preservan para trazabilidad, no se eliminan del disco)
- 1,937 filas removidas de `corpus_ocr.csv` (eran las páginas previamente procesadas por PyMuPDF)
- 2 filas removidas de `ocr_pendientes.csv`
- `data/raw/rut/` queda con 231 PDFs (antes 233)

---

## 3. Inventario final

### Lo que se MANTIENE intacto (cache MD5)

- **1,678 páginas escaneadas** procesadas con EasyOCR en nb05 (overnight de 23 h, 2026-04-17/18). Se mantienen exactamente como están.

### Lo que se PROCESA en Colab

| Origen | Docs únicos | Páginas (límite 10) |
|---|---|---|
| Cédulas nuevas (ingresadas 2026-04-21) | 210 | ~210 |
| Cámara de Comercio (re_ocr) | 182 | ~1,800 |
| Cédula (re_ocr digitales) | 21 | ~50 |
| Pólizas (re_ocr) | 144 | ~1,000 |
| RUT (re_ocr, sin RUPs) | 190 | ~760 |
| **TOTAL a procesar** | **747** | **~3,821 págs** |

**Excluidos:**
- 9 docs en folder `Otros` (clase descartada para clasificador)
- 2 RUPs movidos a quarantine (`data/raw/_quarantine_misclassified/`)

### Resultado final

`data/processed/corpus_ocr.csv` actualizado con:
- ~5,499 filas (1,678 escaneadas viejas + 3,821 nuevas/re_OCR con límite 10)
- Columna `engine` = `easyocr` para 100% de las filas
- Columna `bboxes_json` poblada para 100% de las filas

---

## 4. Por qué Colab GPU y no local

| Recurso | PC del usuario | Colab Free |
|---|---|---|
| GPU | AMD Radeon integrada (sin CUDA) | Tesla T4 16 GB CUDA |
| Tiempo total | ~9-12 días continuos | **~6.4 h en 1 sesión** |
| RAM disponible | 859 MB libres / 8 GB total (88% en uso) | 12 GB asignados al runtime |
| Costo | $0 (electricidad y throttling) | $0 (Free tier) |

→ **Colab Free es la única opción viable** sin invertir en hardware o suscripción.

**Una sola sesión de Colab Free (12 h max) es suficiente** dado el límite de 10 págs.

---

## 5. Pipeline en Colab — pasos

### 5.1 Pre-Colab (local) — ~10 min

1. **(Re-)Identificar pendientes** — `python scripts/identificar_pendientes_ocr.py`
   - Genera `data/processed/ocr_pendientes.csv` (sin Otros, con dedup)
2. **Subir a Drive (~1.5 GB):**
   - `data/raw/CEDULA/`, `data/raw/POLIZA/`, `data/raw/CAMARA DE CIO/`, `data/raw/rut/`
   - `data/processed/ocr_pendientes.csv`
   - `notebooks/colab_ocr_unificacion.ipynb`

### 5.2 En Colab — ~6.4 h

1. Conectar Drive
2. `Run All` del notebook
3. El notebook escribe checkpoints cada 50 documentos a Drive
4. Si la sesión se cae: `Run All` retoma desde último checkpoint (cache MD5)

### 5.3 Post-Colab (local) — ~15 min

1. **Descargar** `data/processed/corpus_ocr.csv` actualizado de Drive
2. **Verificar:**
   - `(df['engine']=='easyocr').mean() == 1.0`
   - `df['bboxes_json'].str.len().gt(5).mean() >= 0.99`
   - Conteo de docs por categoría coincide con esperado
3. **Generar imágenes pág 1** para 548 digitales (PyMuPDF render local, ~5 min) — input C-3 LayoutLMv3
4. **Actualizar** `corpus_ocr_summary.csv` (versión sin texto, commiteable)
5. **Commit** `feat(fase2.1.5): OCR unificado EasyOCR (Colab GPU, limite 10 pags)`

---

## 6. Checklist

### Preparación
- [x] Apagar Label Studio (✅ 2026-04-21)
- [x] Crear `scripts/identificar_pendientes_ocr.py` (✅)
- [x] Decidir scope (sin Otros, límite 10 págs) (✅ 2026-04-21)
- [ ] Re-correr script con dedup + exclusión Otros
- [ ] Crear `notebooks/colab_ocr_unificacion.ipynb`
- [ ] Verificar velocidad de subida WiFi (`speedtest-cli` o measurelab.org)
- [ ] Subir carpetas `data/raw/{CEDULA,POLIZA,CAMARA DE CIO,rut}` a Drive (`SinergIA-Lab/raw/`)
- [ ] Subir `ocr_pendientes.csv` y notebook a Drive
- [ ] Verificar acceso de Colab a Drive

### Ejecución
- [ ] Sesión Colab: ejecutar Run All
- [ ] Monitorear que escriba checkpoints
- [ ] Si se cae: re-ejecutar (cache MD5 retoma)

### Cierre
- [ ] Descargar `corpus_ocr.csv` actualizado
- [ ] Ejecutar verificaciones de integridad
- [ ] Generar imágenes pág 1 para 548 digitales (local)
- [ ] Actualizar `corpus_ocr_summary.csv`
- [ ] Commit
- [ ] Marcar este PLAN como ✅ Completado

---

## 7. Métricas de éxito

| Métrica | Valor objetivo | Cómo se mide |
|---|---|---|
| % filas con `engine == 'easyocr'` | 100% | `(df['engine']=='easyocr').mean()` |
| % filas con `bboxes_json` no vacío | ≥99% | `df['bboxes_json'].str.len().gt(5).mean()` |
| Páginas totales en corpus | ~5,519 | `len(df)` |
| Docs únicos en clasificador (sin Otros) | ~960 (210 nuevas + ~750 existentes - duplicados) | `df.drop_duplicates('doc_id').shape[0]` |
| 0 errores OCR | 0 | `df['error'].notna().sum()` |
| Tiempo Colab | ≤ 8 h | suma de `elapsed_s` |

---

## 8. Riesgos y mitigaciones

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Colab Free desconecta sesión a las ~12 h | Baja (estimado 6.4 h) | Cache MD5 retoma; cabe en 1 sesión |
| Cuota diaria Colab agotada | Baja | Esperar 24 h o usar Kaggle como fallback |
| WiFi del usuario lento para subir 1.5 GB | Media | Medir antes; alternativa: subir desde lugar con mejor red |
| Drive Free agota 15 GB | Baja | El corpus + outputs caben en ~3 GB |
| PDFs corruptos rompen el procesamiento | Baja | try/except por documento, log a `error` |
| Páginas dañadas dentro de un PDF | Baja | EasyOCR continúa con siguientes páginas |

---

## 9. Cómo retomar si se cae la sesión Colab

El notebook implementa cache MD5 idéntico a nb05. Al re-ejecutar:

1. Lee `corpus_ocr.csv` actual del Drive
2. Filtra `ocr_pendientes.csv` excluyendo lo ya procesado (por `md5+page_num`)
3. Continúa donde quedó

**Tiempo de re-arranque tras caída:** ~30 segundos (carga modelo EasyOCR + lectura de cache).

---

## 10. Lo que NO cambia

- Pipeline de preprocesamiento visual (nb04) — solo se aplica a escaneados nuevos
- Esquema de `corpus_ocr.csv` (columnas) — sigue igual
- Decisiones de chunking, anotaciones (NER parqueado), modelado — intactas
- `OCR_BENCHMARK.md` queda como evidencia histórica del benchmark inicial; la decisión de selector híbrido descrita ahí queda **superada** por este plan

---

## 11. Decisiones siguientes (post-OCR)

Una vez completado este plan:

1. **nb10 — Clasificación C-1 (TF-IDF + LR)** local CPU, ~20 min
2. **nb11 — Clasificación C-2 (BETO fine-tuned)** Colab T4, ~30 min
3. **nb12 — Clasificación C-3 (LayoutLMv3)** Colab T4, ~45 min
4. **Reporte comparativo** macro-F1, accuracy, matriz de confusión, latencia
5. **Decisión:** seleccionar el ganador para producción
6. (Pendiente, después) — Retomar Label Studio + NER (Fase 2.2 + Fase 3.1)
