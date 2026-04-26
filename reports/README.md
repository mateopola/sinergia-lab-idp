# Reportes por Notebook — La historia del proyecto SinergIA Lab

Este directorio contiene el análisis detallado de los resultados reales de cada notebook ejecutado. No es una bitácora técnica — es una **narrativa cohesiva** donde cada reporte es un capítulo: establece contexto, formula una hipótesis, describe método, analiza resultados y apunta al capítulo siguiente.

## El arco narrativo

```
                        ┌──────────────────────────────────────┐
   [nb01] Diagnóstico   │ 1,014 documentos heterogéneos.       │
   del corpus           │ 93% de Cédulas son escaneadas.       │
                        │ Hay que trabajar tipología por       │
                        │ tipología, no con pipeline único.    │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb02] Pipeline      │ 12 funciones OpenCV + LFs para RUT   │
   de preprocesamiento  │ + chunking diferenciado. El dispatch │
   + LFs                │ por tipología es la tesis.           │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb03] Benchmark     │ 15 docs gold transcritos a mano.     │
   OCR                  │ EasyOCR domina Cédulas (CER 0.333),  │
                        │ Tesseract domina CC (CER 0.047).     │
                        │ Decisión: EasyOCR + GPU futuro.      │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb04] Preprocesar   │ 1,678 imágenes preprocesadas en      │
   imágenes escaneadas  │ 8:44 min. 0 errores. Hallazgo        │
                        │ contra-intuitivo: binarize() sabotea │
                        │ EasyOCR (5× más lento).              │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb05] OCR de los    │ 1,669 páginas OCR'd en 23h 32min.    │
   escaneados           │ CER global 0.282 (reproduce bench).  │
                        │ Descubrimos 2 gaps: 9 imgs + 552     │
                        │ digitales fuera del pipeline.        │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb05b] Cierre de    │ Parte A: 9 imgs en 3 min (EasyOCR).  │
   gaps                 │ Parte B: 12,415 páginas digitales en │
                        │ 1:19 min (PyMuPDF, 0.006 s/pág!).    │
                        │ Corpus completo: 13,254 páginas.     │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb06] LFs sobre     │ 216 RUT. Cobertura 65-99% confirma   │
   RUT                  │ hipótesis Snorkel. Cuello de botella │
                        │ documentado: representante_legal     │
                        │ (65%).                               │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb07] Cédulas       │ 60 docs estratificados por           │
                        │ blur_score. Hallazgo publicable:     │
                        │ ruidosas tienen MEJOR cobertura      │
                        │ regex (80%) que nítidas (47%).       │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb08] Pólizas       │ 120 docs (80+40). Layout variable    │
                        │ → solo 2 entidades pre-anotables.    │
                        │ 62% de las pólizas con aseguradora   │
                        │ detectada son Mundial de Seguros.    │
                        └──────────────────┬───────────────────┘
                                           │
                        ┌──────────────────▼───────────────────┐
   [nb09] Cámara de     │ 120 docs. El caso opuesto a Pólizas: │
   Comercio             │ regulación Decreto 2150/1995 impone  │
                        │ estructura → 96.7% cobertura razón   │
                        │ social. Candidato ideal para         │
                        │ LayoutLMv3 en Fase 3.                │
                        └──────────────────┬───────────────────┘
                                           │
                                     [Fase 3 →]
                              9 candidatos de modelado
                               (PROPUESTA_MODELOS.md)
```

## Índice de capítulos

| # | Título del capítulo | Reporte | Estado |
|---|---|---|---|
| 01 | El diagnóstico — quiénes son estos 1,014 documentos | [nb01_resultados.md](nb01_resultados.md) | ✅ |
| 02 | Las herramientas — pipeline adaptativo por tipología | [nb02_resultados.md](nb02_resultados.md) | ✅ |
| 03 | La decisión — ¿qué motor OCR para qué documento? | [nb03_resultados.md](nb03_resultados.md) | ✅ |
| 04 | La preparación — 1,678 imágenes, un giro contra-intuitivo | [nb04_resultados.md](nb04_resultados.md) | ✅ |
| 05 | La travesía — 23 horas extrayendo texto | [nb05_resultados.md](nb05_resultados.md) | ✅ |
| 05b | El cierre — cuando el texto digital hace al OCR ver pequeño | [nb05b_resultados.md](nb05b_resultados.md) | ✅ |
| 05c | La unificación — EasyOCR para todo el corpus (Colab GPU, 2 sesiones) | [colab_ocr_unificacion_resultados.md](colab_ocr_unificacion_resultados.md) | ✅ |
| 06 | El experimento Snorkel — ¿funcionan las reglas en RUT? | [nb06_resultados.md](nb06_resultados.md) | ✅ |
| 07 | La paradoja de la calidad — cédulas ruidosas ganan | [nb07_resultados.md](nb07_resultados.md) | ✅ |
| 08 | El caso difícil — Pólizas con layout variable | [nb08_resultados.md](nb08_resultados.md) | ✅ |
| 09 | El caso regulado — Cámara de Comercio y LayoutLMv3 | [nb09_resultados.md](nb09_resultados.md) | ✅ |
| 10 | El baseline trivial — TF-IDF + LR sobre 4 clases auto-identificadoras (F1=1.0) | [nb10_resultados.md](nb10_resultados.md) | ✅ |
| 11 | BETO fine-tuned — la ironía del modelo más sofisticado (F1=0.9914, 1 error) | [nb11_resultados.md](nb11_resultados.md) | ✅ |
| 12 | (pendiente) LayoutLMv3 multimodal — C-3 en Colab GPU | nb12_resultados.md | ⏳ |

## Ritual de actualización post-ejecución

Para que esta narrativa se mantenga viva, cada vez que se ejecute un notebook se aplica el ritual documentado en [../WORKFLOW.md](../WORKFLOW.md):

1. Analizar prints reales de cada celda
2. Actualizar el reporte correspondiente con números reales
3. Identificar hallazgos nuevos y documentar en el reporte
4. Definir los siguientes pasos
5. Commit

## Principios de citación

Toda cita en estos reportes es **verificable**. Usamos solo:

- **Papers con DOI o arXiv ID** (enlace funcional a arxiv.org, aclanthology.org, etc.)
- **Repositorios oficiales** (github.com/org_oficial/repo, huggingface.co/owner/model)
- **Normatividad colombiana** (dian.gov.co, funcionpublica.gov.co, secretariasenado.gov.co)
- **Textbooks** con DOI o página oficial (nlp.stanford.edu/IR-book, etc.)

No citamos blogs corporativos sin paper asociado, wikis anónimas, o enlaces sin fuente institucional.

## Documentos relacionados

- [../PLAN_MODELADO_CRISPDM.md](../PLAN_MODELADO_CRISPDM.md) — hoja de ruta con tasks marcados
- [../PROPUESTA_MODELOS.md](../PROPUESTA_MODELOS.md) — 9 candidatos de modelado para Fase 3
- [../OCR_BENCHMARK.md](../OCR_BENCHMARK.md) — bitácora detallada del benchmark OCR
- [../Resumen_Investigacion_SinergIA_Lab.md](../Resumen_Investigacion_SinergIA_Lab.md) — contexto académico
- [../WORKFLOW.md](../WORKFLOW.md) — ritual de actualización post-ejecución
