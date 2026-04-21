# Resultados — Notebook 01 · Análisis Descriptivo del Corpus SECOP

**Fase CRISP-DM++:** 1 — Comprensión de Datos
**Notebook:** [01_analisis_descriptivo_secop.ipynb](../notebooks/01_analisis_descriptivo_secop.ipynb)
**Fecha de ejecución:** 2026-04-08
**Output principal:** `data/processed/quality_report_completo.csv` (gitignored — PII)

---

## 1. Metadatos de ejecución

- Python 3.12, entorno local CPU
- Duración: ~45 min
- Input: `data/raw/` (1,014 PDFs + 9 imágenes .jpg/.jpeg)
- Output: `quality_report_completo.csv`, `fig01..fig10.png`, `near_duplicates.json`, `vocabulario_dominio.json`, `portadas_detectadas.json`

## 2. Resumen cuantitativo

### 2.1 Inventario por tipología

| Tipología | Documentos | % del corpus |
|---|---|---|
| Cédula | 334 | 32.9% |
| RUT | 235 | 23.2% |
| Póliza | 219 | 21.6% |
| Cámara de Comercio | 212 | 20.9% |
| Otros | 14 | 1.4% |
| **Total** | **1,014** | **100%** |

### 2.2 Distribución escaneados vs digitales

| Categoría | Escaneados | Digitales | % escaneados |
|---|---|---|---|
| Cédula | 312 / 334 | 22 / 334 | 93% |
| RUT | 35 / 235 | 200 / 235 | 15% |
| Póliza | 59 / 219 | 160 / 219 | 27% |
| Cámara de Comercio | 16 / 212 | 196 / 212 | 8% |
| **Corpus** | **~422 / 1,014** | **~592 / 1,014** | **42%** |

### 2.3 Textometría (tokens BPE estimados, factor x1.25)

| Tipología | Mediana BPE | Docs > 1,800 tokens |
|---|---|---|
| Cédula | ~0 (escaneado) | 0 |
| RUT | 1,861 | 151 (64%) |
| Póliza | ~806 | 31 (14%) |
| Cámara de Comercio | ~1,772 | 96 (45%) |

### 2.4 Calidad visual

- `blur_score` mediano del corpus: ~1,469
- Cédulas: 324 APTO / 8 REQUIERE_PREPROCESAMIENTO / 2 DESCARTADO

## 3. Hallazgos

### 🔴 Hallazgo 1 — Cédulas son mayoritariamente escaneadas (93%)

Implica que las Labeling Functions regex **no son aplicables** a esta tipología (decisión documentada en PLAN_MODELADO_CRISPDM.md §2.2 ALERTA v1.3). Requiere flujo alternativo con anotación manual sobre salida OCR.

### 🟢 Hallazgo 2 — RUT es densamente tabular

Una página típica de RUT tiene **97 bloques de texto** y **26.2% densidad de área de texto**. Esta estructura tabular con micro-casillas DIAN supera la capacidad de extracción de modelos basados en texto plano — justifica evaluar candidatos layout-aware en Fase 3.

### 🟡 Hallazgo 3 — RUT supera el límite de chunking

64% de los RUT (151/235) superan 1,800 tokens BPE. Corrige la asunción del plan v1.1-v1.3 ("RUT sin chunking") → **RUT requiere ventana deslizante**, igual que Pólizas (§2.3 del plan).

### 🟢 Hallazgo 4 — Vocabulario CIIU contamina embeddings de RUT

El formulario DIAN imprime la lista completa de clasificaciones CIIU (~300 entradas) en cada RUT. Requiere filtrado específico (`filtrar_ciiu_rut()` en pipeline.py) para generar embeddings/TF-IDF limpios sin perder valores de campos.

### 🟡 Hallazgo 5 — Portadas detectables solo en Pólizas y CC

- RUT: 0/20 portadas (plantilla DIAN siempre inicia con datos)
- Póliza: 5/20 (25%) — portadas corporativas de aseguradoras
- Cámara de Comercio: 2/20 (10%)
- Cédula: desactivado (3 falsos positivos — ver nb02)

## 4. Anomalías y limitaciones

- 2 Cédulas clasificadas `DESCARTADO` (tamaño 0 o corruptas desde origen)
- 4 PDFs con `n_pages=0` (corruptos — se excluyen de Fase 2)
- Mojibake en nombres de archivo por conversión Windows → resuelto via índice MD5
- Categoría `Otros` (14 docs) heterogénea: TP, Formatos, Anexos — no se modelan como clase propia

## 5. Implicaciones para fases posteriores

1. **Fase 2.1 OCR:** dos motores en paralelo según `es_escaneado` (EasyOCR / PyMuPDF) por la mezcla 42/58
2. **Fase 2.2 Anotaciones:** flujo diferenciado — LFs en RUT (texto limpio), regex laxa en Cédulas (OCR), anotación manual Pólizas/CC
3. **Fase 2.3 Chunking:** 3 estrategias según longitud medida (sin chunking / sliding window / layout-aware)
4. **Fase 3 Modelado:** incluir candidato layout-aware (LayoutLMv3) por densidad tabular de RUT/CC

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/quality_report_completo.csv` | 1,014 filas × 15 columnas con metadata por doc | ❌ PII |
| `data/processed/fig01..fig10.png` | Figuras EDA | ✅ |
| `data/processed/near_duplicates.json` | Detección MinHash de duplicados | ✅ |
| `data/processed/vocabulario_dominio.json` | Vocabulario dominio por tipología | ✅ |
| `data/processed/fase1_decisiones.json` | Decisiones tomadas en Fase 1 | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §1](../PLAN_MODELADO_CRISPDM.md) — Fase 1 checklist marcada ✅
- Hallazgos 1 y 2 citados en §2.2 y §2.3 respectivamente
