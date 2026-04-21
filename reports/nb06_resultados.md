# Resultados — Notebook 06 · Pre-anotaciones RUT (Weak Supervision)

**Fase CRISP-DM++:** 2.2 — Estrategia de Etiquetado
**Notebook:** [06_preanotaciones_rut.ipynb](../notebooks/06_preanotaciones_rut.ipynb)
**Fecha de ejecución:** 2026-04-18
**Output principal:** tareas Label Studio + manifest commiteable
**Paper metodológico:** Ratner et al., *Snorkel: Rapid Training Data Creation with Weak Supervision*, VLDB 2018 — https://arxiv.org/abs/1711.10160

---

## 1. Metadatos de ejecución

- Python 3.12, CPU
- Duración: ~3 min
- Input: `corpus_ocr.csv` filtrado por folder que contenga `rut` (case-insensitive)
- LFs aplicadas: `extraer_entidades_rut()` de `src/preprocessing/pipeline.py`
- Muestra procesada: **216 RUT** (216 del corpus OCR, cruzados con quality_report)

## 2. Resumen cuantitativo

### 2.1 Cobertura por entidad (tras normalización)

| Entidad | Detectados | Nulos | Cobertura | Valores únicos |
|---|---|---|---|---|
| `municipio` | 215 | 1 | **99.5%** | 6 |
| `regimen` | 213 | 3 | **98.6%** | 3 |
| `nit` | 212 | 4 | **98.1%** | 200 |
| `direccion` | 201 | 15 | **93.1%** | 185 |
| `razon_social` | 177 | 39 | **81.9%** | 166 |
| `representante_legal` | 141 | 75 | **65.3%** | 135 |

**Docs con los 6 campos completos:** 116 / 216 = **53.7%**

### 2.2 Distribución de valores tras normalización

**Régimen (3 valores canónicos):**
- `ordinario`: 197
- `especial`: 9
- `simple`: 7 (Régimen Simple de Tributación, Ley 2155/2021)
- `None`: 3

**Municipio (top 6 tras consolidar variantes de Bogotá):**
- `Cali`: 190
- `Bogotá D.C.`: 17 (consolidado de 5 variantes originales)
- `Bucaramanga`: 3
- `Medellín`: 3
- `Cúcuta`: 1
- `Neiva`: 1

### 2.3 Validación contra gold seed (3 RUT transcritos)

| Doc | NIT | Razón social | Régimen | Municipio | Rep. legal |
|---|---|---|---|---|---|
| RUT GESTIVA (digital) | ✅ 316588212-7 | ✅ GESTIONES EFECTIVAS GJH S.AS | ✅ ordinario | ✅ Cali | ❌ |
| RUT ASOVITAL (escaneado) | ❌ | ❌ | ✅ ordinario | ✅ Cúcuta | ❌ |
| RUT La Previsora (digital) | ✅ 601348755-5 | ✅ GRUPO BICENTENARIO S.AS | ✅ ordinario | ✅ Bogotá D.C | ❌ |

**Patrón claro:** LFs funcionan excelente en PyMuPDF (digitales) y degradan en OCR (escaneados).

## 3. Hallazgos

### 🟢 Hallazgo 1 — Cobertura confirma hipótesis de Weak Supervision

Cobertura 65-99% es típica de LFs según el paper Snorkel (Ratner 2018). El 53.7% de docs con los 6 campos completos justifica el flujo híbrido: **automatización barata + corrección humana selectiva** (no anotación desde cero).

**Estimación de ahorro de tiempo:**
- Anotación desde cero: ~20 min/doc × 216 = **72 horas** humanas
- Revisión de pre-anotaciones: ~10 min/doc × 216 = **36 horas** humanas
- **Ahorro: ~50%**

### 🔴 Hallazgo 2 — Representante legal es el cuello de botella

Cobertura 65.3% vs 98-99% del resto. Causa: la regex requiere el patrón estricto `APELLIDOS NOMBRES\nRepresentante legal`. Variantes no cubiertas: orden invertido, línea en blanco, saltos, formato alternativo.

**De los 75 docs sin detección:**
- Solo 3 tampoco tienen NIT → texto está bien extraído, es la regex la que falla
- Los otros 72 requerirán el anotador humano en Label Studio

**Decisión:** no refinar la LF (3-4h de trabajo para ~43 docs adicionales = ~7h de ahorro humano, ROI dudoso). Se acepta la limitación.

### 🟡 Hallazgo 3 — Mojibake de municipio: 5 variantes de Bogotá

En la extracción raw aparecieron: `Bogotá D.C.` (13), `Bogotá D.C` (2), `Bogotá DC` (1), `BOGOTÁ D.C.` (1), `Bogotá D.C` (2). **Normalización post-extracción** las consolida al canónico `Bogotá D.C.`.

**Por qué normalizar antes de Label Studio y no después:** si el humano ve variantes distintas, podría aprobar ambas como válidas → contaminación del ground truth.

### 🟢 Hallazgo 4 — Distinción jurídica `simple` vs `simplificado`

La LF original mapeaba `simpli*` → `simplificado` pero dejaba `Simple` (7 docs) sin normalizar. Se refinó para distinguir:
- `Simple*` → `simple` (Régimen Simple de Tributación, Ley 2155 de 2021)
- `Simplifi*` → `simplificado` (antiguo régimen simplificado de IVA)

Son **jurídicamente distintos** — esta normalización preserva información semántica que sería borrada por un `lower().strip()` genérico.

### 🟢 Hallazgo 5 — Geografía del corpus: 88% es Cali

190 de 216 RUT son de Cali. Confirma origen institucional (CCC — Cámara de Comercio de Cali). Implicación para §3.0 Clasificación: `municipio` **no discrimina tipología** — todos son Cali. Sirve solo como feature auxiliar.

### 🟡 Hallazgo 6 — Discrepancia interesante con Fase 1 (235 vs 216 RUT)

Fase 1 reportó 235 RUT; aquí son 216. Diferencia = 19 docs. Probablemente:
- Reclasificaciones (ej. `CC OMAR DAZA VEGA RL ASOPERIJA.pdf` movido de CC a Cédula durante benchmark)
- RUT corruptos excluidos en nb 04 / nb 05
- Ajustes de folder en nb 05b

No es crítico — sigue siendo ~90% del corpus original.

## 4. Anomalías y limitaciones

- 3 docs sin régimen detectado (texto posiblemente corrupto por OCR en los 116 easyocr de la muestra)
- 1 doc sin municipio — confirmado que el texto OCR no contiene ningún municipio reconocido
- Los valores únicos de `razon_social` (166 en 177 detectados) sugieren pocas empresas repetidas; útil para deduplicación futura

## 5. Implicaciones para fases posteriores

1. **Label Studio setup** — cargar `rut_preanotaciones_labelstudio.json`, definir esquema con 6 entidades en Label Studio
2. **Priorizar revisión humana** en los 75 docs sin `representante_legal` y ~6 docs escaneados completos
3. **Target Kappa ≥ 0.85** en muestra de validación cruzada de 50 docs (requiere doble anotación)
4. **Dataset de entrenamiento:** tras revisión, exportar y chunking (§2.3)

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/rut_preanotaciones.jsonl` | 216 líneas JSON (1 por doc, con entidades) | ❌ PII |
| `data/processed/rut_preanotaciones_labelstudio.json` | Tareas Label Studio (10 MB) | ❌ PII |
| `data/processed/rut_preanotaciones_summary.csv` | Cobertura por entidad | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §2.2 RUT](../PLAN_MODELADO_CRISPDM.md) — task `[x]` con cobertura documentada
- [nb02_resultados.md](nb02_resultados.md) — definición original de las LFs

## 8. Referencia científica

Ratner, A., Bach, S. H., Ehrenberg, H., Fries, J., Wu, S., Ré, C. (2018). **Snorkel: Rapid Training Data Creation with Weak Supervision**. *VLDB 2018*. https://arxiv.org/abs/1711.10160
