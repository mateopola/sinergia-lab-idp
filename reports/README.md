# Reportes de Resultados por Notebook

Este directorio contiene el resumen de resultados empíricos y su análisis por cada notebook ejecutado. Es la **fuente de verdad citable** para el informe final del proyecto.

## Estructura

Cada reporte sigue el esquema:
1. **Metadatos de ejecución** — fecha, entorno, hiperparámetros
2. **Resumen cuantitativo** — métricas principales
3. **Hallazgos** — hechos empíricos destacables
4. **Anomalías y limitaciones** — lo que no funcionó o requiere atención
5. **Implicaciones para fases posteriores**
6. **Evidencia en disco** — rutas a los artefactos generados

## Índice

| # | Notebook | Fase | Reporte | Estado |
|---|---|---|---|---|
| 01 | `01_analisis_descriptivo_secop.ipynb` | 1 EDA | [nb01_resultados.md](nb01_resultados.md) | ✅ |
| 02 | `02_preprocesamiento_pipeline.ipynb` | 2.0 | [nb02_resultados.md](nb02_resultados.md) | ✅ |
| 03 | `03_benchmark_ocr.ipynb` | 2.1.1 | [nb03_resultados.md](nb03_resultados.md) — también en [OCR_BENCHMARK.md](../OCR_BENCHMARK.md) | ✅ |
| 04 | `04_preprocesamiento_imagenes.ipynb` | 2.1 | [nb04_resultados.md](nb04_resultados.md) | ✅ |
| 05 | `05_ocr_corpus.ipynb` | 2.1 | [nb05_resultados.md](nb05_resultados.md) | ✅ |
| 05b | `05b_cierre_gaps_ocr.ipynb` | 2.1.4 | [nb05b_resultados.md](nb05b_resultados.md) | ✅ |
| 06 | `06_preanotaciones_rut.ipynb` | 2.2 | [nb06_resultados.md](nb06_resultados.md) | ✅ |
| 07 | `07_preanotaciones_cedulas.ipynb` | 2.2 | [nb07_resultados.md](nb07_resultados.md) | ✅ |
| 08 | `08_preanotaciones_polizas.ipynb` | 2.2 | [nb08_resultados.md](nb08_resultados.md) | ⏳ pendiente ejecución |
| 09 | `09_preanotaciones_camara_comercio.ipynb` | 2.2 | [nb09_resultados.md](nb09_resultados.md) | ⏳ pendiente ejecución |

## Convenciones

- Los reportes con métricas de CER/F1/precisión van con 3 decimales.
- Fechas en formato ISO `YYYY-MM-DD`.
- Rutas de archivos relativas a la raíz del repositorio.
- Citas científicas con DOI o URL arXiv cuando aplica.

## Documentos relacionados

- [PLAN_MODELADO_CRISPDM.md](../PLAN_MODELADO_CRISPDM.md) — hoja de ruta con checkboxes de avance
- [PROPUESTA_MODELOS.md](../PROPUESTA_MODELOS.md) — fundamentación científica de los 9 candidatos
- [OCR_BENCHMARK.md](../OCR_BENCHMARK.md) — bitácora del benchmark OCR
