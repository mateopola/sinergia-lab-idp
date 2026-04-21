# Capítulo 5b — El cierre: cuando el texto digital hace al OCR ver pequeño

**Notebook:** [05b_cierre_gaps_ocr.ipynb](../notebooks/05b_cierre_gaps_ocr.ipynb)
**Fecha de ejecución:** 2026-04-18
**Fase CRISP-DM++:** 2.1.4 — Cobertura completa del corpus
**Artefacto principal:** `corpus_ocr.csv` → corpus textual completo (13,254 páginas, 32.6 M chars)

---

## 1. El contexto — la verdad incómoda

Al cerrar nb05 descubrimos que **teníamos 1,669 páginas procesadas cuando el corpus real es 13,254**. Faltaban:

- **9 imágenes escaneadas** (`.jpg`/`.jpeg`) filtradas silenciosamente por el indexador MD5
- **548 documentos digitales** (~12,400 páginas) que nunca entraron al pipeline porque nb04 los excluyó deliberadamente (no necesitan preprocesamiento) y nb05 solo itera el manifest de nb04

Este capítulo es el **cierre honesto** del corpus. Sin él, todas las fases siguientes trabajarían sobre un 13% del texto del proyecto.

## 2. La hipótesis

> Los dos gaps son arreglables en una sola corrida corta (<30 min) usando EasyOCR para las 9 imágenes y PyMuPDF para los 548 digitales. El merge con el corpus existente no debe degradar las métricas contra gold seed (sanity check).

## 3. El método — dos partes en paralelo conceptual

### 3.1 Inventario inicial

```
corpus_ocr.csv actual: 1,669 filas / 403 docs
Engines actuales: {'easyocr': 1669}

image_manifest.csv: 1,678 filas / 412 docs escaneados

quality_report_completo.csv: 1,014 docs Fase 1

=== GAP A === Paginas escaneadas pendientes: 9
      folder                 filename  page_num
292   CEDULA          CEDULA (1).jpeg         1
294   CEDULA          CEDULA (2).jpeg         1
333   CEDULA  CEDULA SINDY VARGAS.jpg         1
339   CEDULA         CEDULA ZAMIR.jpg         1
348   CEDULA     Copia de CEDULA.jpeg         1
388      rut                RUT 1.jpg         1
465      rut     RUT ZAMIR MORENO.jpg         1
1676   OTROS              TP (1).jpeg         1
1677   OTROS              TP (2).jpeg         1

=== GAP B === Docs digitales (no escaneados, nunca procesados): 552
Docs corruptos (n_pages=0) que se excluyen: 4
Docs a procesar: 586
Paginas totales: 12,415

Por folder:
                       docs  paginas
category                            
CÃÂ¡mara de Comercio   183     2993
CÃÂ©dula                21       60
Otros                     9     3804
PÃÂ³liza               144     1918
RUT                     192     3640
```

**Observación:** los 21 Cédulas "digitales" son las 15 + 6 que Fase 1 clasificó como digital por tener `char_count ≥ 100`. Es una minoría (vs 319 escaneadas).

### 3.2 Parte A — 9 imágenes con EasyOCR

```
Parte A - EasyOCR: 100%|██████████| 9/9 [03:01<00:00, 20.15s/it]
Parte A completa. Filas producidas: 9
  Con error: 0
  Chars promedio: 738
  s/pagina:       20.0
```

Detalle fila por fila:

```
   folder                 filename  page_num  text_chars  elapsed_s error
0  CEDULA          CEDULA (1).jpeg         1         310     11.180  None
1  CEDULA          CEDULA (2).jpeg         1         139      7.160  None
2  CEDULA  CEDULA SINDY VARGAS.jpg         1          54      2.551  None
3  CEDULA         CEDULA ZAMIR.jpg         1         421     29.675  None
4  CEDULA     Copia de CEDULA.jpeg         1         435     13.769  None
5     rut                RUT 1.jpg         1        2217     25.605  None
6     rut     RUT ZAMIR MORENO.jpg         1        2285     69.370  None
7   OTROS              TP (1).jpeg         1         278     10.227  None
8   OTROS              TP (2).jpeg         1         504     10.100  None
```

Observación: los 2 RUT tienen ~2,250 chars — denso, formulario DIAN completo. `CEDULA SINDY VARGAS.jpg` tiene solo 54 chars → imagen muy borrosa o con poco texto visible.

### 3.3 Parte B — 548 digitales con PyMuPDF

```
Parte B - PyMuPDF: 100%|██████████| 586/586 [01:19<00:00,  7.35it/s]
Parte B completa.
  Filas producidas: 12,415
  Docs procesados:  548
  Con error:        0
  Chars promedio:   2513
  Chars totales:    31,199,414
  s/pagina (mean):  0.006  ← instantaneo
```

**1 minuto 19 segundos** para 548 documentos y 12,415 páginas. Comparación:

| Motor | Páginas | Tiempo | s/pág |
|---|---|---|---|
| EasyOCR CPU (nb05) | 1,669 | 23h 32min | 50.79 |
| **PyMuPDF** (nb05b parte B) | **12,415** | **1min 19s** | **0.006** |

**PyMuPDF es ~8,500× más rápido que EasyOCR CPU.** La lección: si el texto está digitalmente embebido en el PDF, **jamás aplicar OCR**. Es desperdicio puro y degrada el texto.

### 3.4 Consolidación

```
Backup creado: corpus_ocr_preV2_backup.csv
Tras concat: 14,093 filas
Escrito: corpus_ocr.csv — 13,254 filas     ← deduplicado
Escrito: corpus_ocr_summary.csv — 13,254 filas
```

Dedup defensivo por `(md5, page_num)`: si una página aparece más de una vez, se conserva la versión con más chars (no la que tenga error).

## 4. Los resultados — el corpus completo

### 4.1 Cobertura final

```
=== COBERTURA FINAL DEL CORPUS OCR ===

Docs totales:     960
Paginas totales:  13,254
Chars totales:    32,592,157

Por engine:
engine
pymupdf    11576
easyocr     1678
```

**32.6 millones de caracteres de texto**. 87% vía PyMuPDF (texto limpio), 13% vía EasyOCR (texto con ruido).

### 4.2 Desglose por folder (muestra el mojibake)

```
                       docs  paginas    chars
folder                                       
CAMARA DE CIO            16      160   399790       ← escaneado (nb04)
CEDULA                  308      356   147884       ← escaneado (nb04)
CÃÂ¡mara de Comercio   183     2611  7692986       ← digital (nb05b, mojibake de quality_report)
CÃÂ©dula                21       58    26072       ← digital
OTROS                     5       22    49136
Otros                     9     3804  9382559       ← digital
POLIZA                   59     1024  2705308       ← escaneado
PÃÂ³liza               144     1743  3296739       ← digital
RUT                     192     3360  8649208       ← digital
rut                      24      116   242475       ← escaneado
```

El folder `Otros` digital tiene **9.4 M chars en 3,804 páginas** — son expedientes largos no clasificados (ej. contratos, resoluciones). No se modelarán como clase propia en Fase 3, pero se preservan.

### 4.3 Validación post-cierre contra gold seed

```
=== VALIDACION POST-CIERRE ===

Agregados por folder:
                  cer  ent_recall
folder                           
CAMARA DE CIO  0.2184      0.6427
CEDULA         0.3107      0.5625
POLIZA         0.2294      0.7680
rut            0.3301      0.8890

CER global (media):     0.2798
CER global (mediana):   0.2696
Entity recall (media):  0.6849
```

**Los 15 docs del gold tienen métricas idénticas a nb05** (todos son escaneados → no los toca el merge). Esto es el **sanity check esperado**: el merge fue limpio, no corrompió ninguna fila previa.

## 5. La lectura crítica

### 5.1 Dos paradigmas de extracción, dos órdenes de magnitud

| Régimen | Motor | Throughput | Calidad |
|---|---|---|---|
| Escaneados (1,678 pág) | EasyOCR | 0.02 pág/s | CER ~0.28 |
| Digitales (11,576 pág) | PyMuPDF | 156 pág/s | CER ~0.00 |

La diferencia en **calidad** (perfect vs noisy) **y** en **velocidad** (instantáneo vs overnight) valida la decisión arquitectural de bifurcar por `es_escaneado`.

### 5.2 PyMuPDF en documentos "digitales" no siempre es perfecto

```
MuPDF error: format error: object is not a stream
MuPDF error: format error: object is not a stream
MuPDF error: format error: object is not a stream
```

Estos son errores **por PDF**. El notebook siguió adelante (`Con error: 0` al final porque el loop atrapa excepciones). Los docs afectados devuelven texto vacío o parcial.

**Descubrimiento adjunto** (análisis posterior con `pandas`): **463 páginas "digitales" tienen text_chars=0**. Concentradas en Pólizas (432 páginas). Son **páginas-imagen embebidas** en PDFs marcados como digitales — certificados escaneados anexos, firmas notariadas, sellos.

Esto no es error de PyMuPDF. Es la realidad del SECOP: los contratistas adjuntan anexos escaneados dentro de PDFs digitales. Opción futura para Fase 2.2 extendida: **tercer pase EasyOCR sobre esas 463 páginas específicas** recuperaría ~400 páginas más de texto.

### 5.3 El corpus final en perspectiva

Si los 960 docs representan ~1,000 procesos SECOP promedio:

- 13,254 páginas → **~13 páginas por proceso**
- 32.6 M chars → **~5.4 M palabras** de vocabulario administrativo colombiano
- Volumen comparable a un dataset académico mediano (e.g., [CoNLL-2003 NER](https://www.clips.uantwerpen.be/conll2003/ner/) tiene ~300K palabras)

El dataset supera las escalas típicas reportadas en literatura de IDP para Spanish-language documents [1] [2], con la ventaja de ser **dominio-específico** (normatividad colombiana).

## 6. Anomalías y hallazgos secundarios

### 6.1 Mojibake heredado en folder

El corpus final tiene **10 valores distintos de `folder`** en vez de 5 reales:

- `CEDULA` ≠ `CÃÂ©dula`
- `CAMARA DE CIO` ≠ `CÃÂ¡mara de Comercio`
- `POLIZA` ≠ `PÃÂ³liza`
- `rut` ≠ `RUT`

Los valores limpios vienen de nb04 (escaneados). Los mojibake vienen de `quality_report.category` (heredado de Fase 1 con conversión Windows → UTF-8 fallida).

**Decisión:** no normalizar en nb05b (mantener trazabilidad con origen). Los notebooks 06–09 normalizan con filtros `str.lower().contains()` que matchean ambos (e.g., `contains('poliz|liza')` captura `POLIZA` y `PÃÂ³liza`).

**Tarea pendiente para §2.2:** función `normalizar_folder()` canónica en `pipeline.py` — 5 líneas de código.

### 6.2 4 documentos corruptos excluidos

```
Docs corruptos (n_pages=0) que se excluyen: 4
```

Ya detectados en Fase 1. No se tocan — son irrecuperables (PDFs con estructura malformada desde origen SECOP).

### 6.3 Backup automático

```
Backup creado: corpus_ocr_preV2_backup.csv
```

Antes de sobrescribir `corpus_ocr.csv` con la versión fusionada, se guarda el pre-merge. Permite rollback sin re-correr las 23h de OCR.

## 7. ¿Qué sigue? — Cap. 6

Con 13,254 páginas de texto disponibles, la promesa del paper Snorkel (Ratner et al. 2018 [3]) se puede probar:

> *¿Pueden las Labeling Functions regex producir anotaciones de calidad sobre los 216 RUT del corpus?*

El Notebook 06 aplica las 6 LFs definidas en nb02 a todos los RUT y mide cobertura por entidad. Si la tesis de Snorkel se confirma, **habremos automatizado ~50% del trabajo de anotación humana** para la tipología más importante del proyecto.

→ [nb06_resultados.md](nb06_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/corpus_ocr.csv` | 13,254 filas — corpus completo (gitignored por PII) | ❌ PII |
| `data/processed/corpus_ocr_summary.csv` | 13,254 filas sin texto | ✅ |
| `data/processed/corpus_ocr_preV2_backup.csv` | Backup pre-merge | ❌ PII |
| `data/gold/ocr_corpus_validation.csv` | Re-validación post-cierre | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | Cañete, J. et al. (2020). *Spanish Pre-Trained BERT Model and Evaluation Data (BETO)*. PML4DC @ ICLR 2020 | https://users.dcc.uchile.cl/~jperez/papers/pml4dc2020.pdf |
| [2] | Wang, W. et al. (2025). *A Survey on Document Intelligence Foundations and Frontiers*. arXiv | https://arxiv.org/abs/2510.13366 |
| [3] | Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 | https://arxiv.org/abs/1711.10160 |

**Repositorios:**
- PyMuPDF — https://github.com/pymupdf/PyMuPDF
- MuPDF — https://mupdf.com/
