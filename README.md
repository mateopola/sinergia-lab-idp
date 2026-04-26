# SinergIA Lab — IDP para Documentos Corporativos Colombianos

**Proyecto:** Procesamiento Inteligente de Documentos (IDP) orientado a extracción automática de entidades en documentos oficiales colombianos del corpus SECOP.
**Institución:** Pontificia Universidad Javeriana · Especialización en Inteligencia Artificial · Ciclo 1 · Marzo 2026.
**Metodología:** CRISP-DM++ + Scrum + Design Thinking.

---

## Estado del proyecto

**Última actualización:** 2026-04-21

> **Nuevo enfoque (2026-04-21):** Esta fase del proyecto se concentra en **Modelado y Evaluación de Clasificación** (3 candidatos C-1/C-2/C-3). Las anotaciones NER quedan parqueadas hasta cerrar clasificación. Adicionalmente: el corpus se está re-unificando bajo EasyOCR (eliminando el selector híbrido con PyMuPDF) por paridad train-inference. Ver [PLAN_OCR_COLAB.md](PLAN_OCR_COLAB.md) y [memoria del proyecto](C:/Users/mateo/.claude/projects/c--Users-mateo-Desktop-Archivos-SinergiaLabProyecto/memory/MEMORY.md).

| Fase | Estado | Notas |
|---|---|---|
| **Fase 1 — Comprensión de datos** | ✅ Completa | EDA sobre 1,014 docs SECOP. Corpus caracterizado (334 cédulas / 235 RUT / 219 pólizas / 212 CC / 14 otros). Output: `quality_report_completo.csv`. |
| **Fase 2 §2.1 — Preprocesamiento + OCR** | ✅ v1 (híbrido) · ✅ v2 unificado | v1: 13,254 págs (1,678 EasyOCR + 11,576 PyMuPDF). **v2 (✅ 2026-04-26):** corpus re-unificado bajo EasyOCR único — 5,351 filas / **1,134 docs únicos** / 100% engine=easyocr / 99.87% bboxes / 0 errores. Scope final: 4 clases `{Cedula, RUT, Poliza, CamaraComercio}`. Ver [PLAN_OCR_COLAB.md](PLAN_OCR_COLAB.md) + [reports/colab_ocr_unificacion_resultados.md](reports/colab_ocr_unificacion_resultados.md). |
| **Fase 2 §2.2 — Anotaciones NER** | ⏸️ Parqueado | Pre-anotaciones generadas (516 docs en 4 JSONs Label Studio). Revisión humana diferida hasta cerrar Fase 3 Clasificación. Ver [LABEL_STUDIO_SETUP.md](LABEL_STUDIO_SETUP.md) y [CRITERIOS_ANOTACION.md](CRITERIOS_ANOTACION.md) para cuando se retome. |
| **Fase 2 §2.3 — Chunking** | ⏳ Pendiente | Diferido hasta retomar NER. |
| **Fase 2 §2.4 — Augmentación** | ⏳ Pendiente | Diferido hasta antes del fine-tuning. |
| **Fase 3 §3.0 — Clasificación** | 🟡 En curso (foco actual) | **C-1 TF-IDF ✅ ejecutado (2026-04-26):** Test Macro-F1=1.0000, 5-fold CV Macro-F1=0.996±0.004 — el dominio resulta trivialmente clasificable (4 clases con titulos auto-identificadores en pag 1), no comparable a RVL-CDIP. Esperando ejecutar C-2 BETO (Colab) y C-3 LayoutLMv3 (Colab) sobre mismo split. Ver [reports/nb10_resultados.md](reports/nb10_resultados.md). |
| **Fase 3 §3.1 — NER (modelado)** | ⏳ Pendiente | Pendiente de revisión Label Studio (Fase 2.2). |
| **Fase 4 — Evaluación** | ⏳ Pendiente | Experimentos comparativos por fase. |

---

## Estructura del repositorio

```
SinergiaLabProyecto/
├── README.md                            ← este archivo
├── PLAN_MODELADO_CRISPDM.md            ← plan maestro (roadmap completo CRISP-DM++)
├── OCR_BENCHMARK.md                    ← bitácora del benchmark OCR + decisión
├── Resumen_Investigacion_SinergIA_Lab.md ← informe académico de investigación
│
├── data/
│   ├── raw/                            ← 1,014 PDFs originales (gitignore — PII)
│   ├── processed/
│   │   ├── quality_report_completo.csv ← EDA Fase 1 (gitignore — PII)
│   │   ├── image_manifest.csv          ← manifest de imágenes procesadas (nb 04)
│   │   ├── corpus_ocr.csv              ← texto del corpus (gitignore — PII, output de nb 05)
│   │   ├── corpus_ocr_summary.csv      ← métricas sin texto (commiteable)
│   │   ├── ocr_benchmark.csv           ← resultados benchmark (nb 03)
│   │   ├── images/                     ← JPGs procesados (gitignore, 1.9 GB)
│   │   └── fig*.png                    ← figuras de análisis
│   └── gold/
│       ├── gold_seed_manifest.csv      ← 15 docs de gold seed para benchmark
│       ├── transcriptions/             ← transcripciones humanas (gitignore — PII)
│       └── ocr_output/                 ← salidas OCR del benchmark (gitignore)
│
├── notebooks/
│   ├── 01_analisis_descriptivo_secop.ipynb    ← EDA Fase 1
│   ├── 02_preprocesamiento_pipeline.ipynb     ← define funciones OpenCV + LFs
│   ├── 03_benchmark_ocr.ipynb                 ← benchmark OCR (EasyOCR vs Tesseract)
│   ├── 04_preprocesamiento_imagenes.ipynb     ← aplica pipeline a corpus escaneado
│   ├── 05_ocr_corpus.ipynb                    ← OCR escaneados → corpus_ocr.csv
│   ├── 05b_cierre_gaps_ocr.ipynb              ← añade 9 imgs + ~590 digitales (PyMuPDF)
│   ├── 06_preanotaciones_rut.ipynb            ← weak supervision: LFs regex sobre 216 RUT → Label Studio
│   ├── 07_preanotaciones_cedulas.ipynb        ← muestra estratificada 60 Cédulas + regex numero → Label Studio bimodal
│   ├── 08_preanotaciones_polizas.ipynb        ← muestra aleatoria 120 Pólizas (80+40) + regex numero + lookup aseguradora
│   ├── 09_preanotaciones_camara_comercio.ipynb ← muestra aleatoria 120 CC (80+40) + regex nit/matricula/razon_social
│   ├── build_notebook_XX.py                   ← builders de cada notebook
│   └── run_fase1.py                           ← script ejecutado en Fase 1
│
├── src/
│   └── preprocessing/
│       ├── pipeline.py                 ← funciones reutilizables (OpenCV + LFs + chunking)
│       └── __init__.py
│
└── .gitignore                          ← excluye PII y archivos grandes regenerables
```

---

## Cómo correr el pipeline

Todos los notebooks son auto-contenidos y siguen el orden numérico. Ejecutar en este orden:

### 1. Entorno

```bash
pip install easyocr pymupdf opencv-python pandas tqdm jiwer pytesseract matplotlib seaborn
```

Python 3.12 recomendado. Algunos notebooks opcionales requieren Tesseract 5 (solo para el benchmark del nb 03).

### 2. Notebooks en orden

```bash
jupyter notebook
# o usa VSCode con la extensión de Jupyter
```

| Orden | Notebook | Qué produce | Duración |
|---|---|---|---|
| 1 | `01_analisis_descriptivo_secop.ipynb` | `quality_report_completo.csv`, figuras EDA | ~45 min |
| 2 | `02_preprocesamiento_pipeline.ipynb` | Funciones en `pipeline.py`, `aseguradoras_corpus.json` | ~15 min |
| 3 | `03_benchmark_ocr.ipynb` | `ocr_benchmark.csv` + decisión en `OCR_BENCHMARK.md` | ~3h (manual + 20 min cómputo) |
| 4 | `04_preprocesamiento_imagenes.ipynb` | `image_manifest.csv` + JPGs procesados | ~10 min |
| 5 | `05_ocr_corpus.ipynb` | `corpus_ocr.csv` + `corpus_ocr_summary.csv` (solo escaneados) | ~12h overnight CPU |
| 5b | `05b_cierre_gaps_ocr.ipynb` | Corpus OCR **completo** (añade 9 imágenes + ~590 digitales PyMuPDF) | ~20-25 min |
| 6 | `06_preanotaciones_rut.ipynb` | Pre-anotaciones RUT vía Weak Supervision (Snorkel/LFs) + tareas Label Studio | ~3 min |
| 7 | `07_preanotaciones_cedulas.ipynb` | Muestreo estratificado 60 Cédulas + regex `numero` + tareas Label Studio bimodal (texto + imagen) | ~2 min |
| 8 | `08_preanotaciones_polizas.ipynb` | Muestra aleatoria 120 Pólizas (80 train + 40 val) + regex `numero_poliza` + lookup `aseguradora` | ~3 min |
| 9 | `09_preanotaciones_camara_comercio.ipynb` | Muestra aleatoria 120 CC (80+40) + regex `nit`/`matricula`/`razon_social` | ~3 min |

**Caché por MD5:** los notebooks 04 y 05 son retomables. Si se interrumpen, al re-ejecutarlos continúan desde donde quedaron (detectan outputs en disco y saltan lo ya hecho).

### 3. Validaciones

Cada notebook incluye celdas de validación al final. Checks típicos:
- Conteo de filas/páginas matches corpus
- 0 errores (o <2%)
- Archivos esperados presentes en disco
- Validación contra gold seed (15 docs con transcripciones humanas)

---

## Decisiones arquitecturales clave

| Decisión | Ubicación | Resumen |
|---|---|---|
| **EasyOCR como motor OCR** | `OCR_BENCHMARK.md` §2 | Ganador del benchmark contra Tesseract. Con GPU: unificado. En CPU: selector híbrido (EasyOCR para Cédula; Tesseract para RUT/Póliza/CC). Este repo corre CPU con EasyOCR unificado. |
| **NO binarizar antes de EasyOCR** | `OCR_BENCHMARK.md` §2.6.0 + `PLAN_MODELADO_CRISPDM.md` §2.1.3 | Binarize (Otsu) ralentiza EasyOCR 5× (de ~20 s/pág a ~110 s/pág). EasyOCR es deep learning y prefiere grayscale con CLAHE, no binario puro. El pipeline final omite `binarize()`. |
| **Preprocesamiento visual solo para escaneados** | `notebooks/04_preprocesamiento_imagenes.ipynb` | Los 548 PDFs digitales van directo a PyMuPDF, no pasan por OpenCV. Ahorra 12 GB de disco. |
| **Chunking diferenciado por tipología** | `PLAN_MODELADO_CRISPDM.md` §2.3 | Cédula: sin chunking. RUT/Póliza: sliding window 512 tokens / 30% overlap. CC: layout-aware con HoughLinesP. |
| **Gold seed 15 docs ahora / gold extendido 70 docs en Fase 4** | `PLAN_MODELADO_CRISPDM.md` §2.1.2 | El seed de 15 cubre benchmark OCR y validación de LFs. El extendido a 70 solo si F1 requiere más rigor estadístico. |
| **Donut descartado como arquitectura global** | `PLAN_MODELADO_CRISPDM.md` §ALT-1 | Revisitable solo para Cédulas si F1 Fase 4 insuficiente. |
| **LayoutLMv3 como experimento 6 opcional** | `PLAN_MODELADO_CRISPDM.md` §ALT-2 | Considerar si F1 de RUT/CC queda bajo umbral. |

---

## Documentación principal

| Documento | Propósito |
|---|---|
| [PLAN_MODELADO_CRISPDM.md](PLAN_MODELADO_CRISPDM.md) | **Plan maestro.** Hoja de ruta Fase 1-4 con checkboxes de avance. |
| [OCR_BENCHMARK.md](OCR_BENCHMARK.md) | Bitácora del benchmark OCR (Parte 1: procedimiento / Parte 2: hallazgos + decisión). |
| [Resumen_Investigacion_SinergIA_Lab.md](Resumen_Investigacion_SinergIA_Lab.md) | Informe académico: contexto, literatura, competidores, requerimientos. |

---

## Equipo y contacto

Proyecto colaborativo del equipo SinergIA Lab, PUJ Especialización IA 2026.

Para ejecutar las partes pesadas del pipeline (corridas OCR overnight, fine-tuning), cada notebook es auto-contenido e incluye en su portada las dependencias, tiempos estimados y modo de ejecución retomable.
