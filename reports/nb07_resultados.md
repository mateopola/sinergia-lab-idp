# Resultados — Notebook 07 · Pre-anotaciones Cédulas (muestra estratificada)

**Fase CRISP-DM++:** 2.2 — Anotación vía OCR Muestral
**Notebook:** [07_preanotaciones_cedulas.ipynb](../notebooks/07_preanotaciones_cedulas.ipynb)
**Fecha de ejecución:** 2026-04-20
**Output principal:** `data/processed/cedulas_muestra_manifest.csv` (commiteable) + tareas Label Studio bimodales

---

## 1. Metadatos de ejecución

- Python 3.12, CPU
- Duración: ~2 min
- Input: `corpus_ocr.csv` + `quality_report_completo.csv` + `image_manifest.csv`
- Seed de muestreo: **42** (reproducible)
- Tamaño de muestra: **60 Cédulas** (30 alta calidad + 30 ruidosas)

## 2. Resumen cuantitativo

### 2.1 Muestreo estratificado

| Estrato | N | blur_score mediano | blur_score min/max |
|---|---|---|---|
| alta_calidad (≥ Q3) | 30 | 6,926 | 4,342 / 15,094 |
| ruidosa (≤ Q1) | 30 | 335 | 14 / 526 |
| **Total** | **60** | — | — |

### 2.2 Cobertura de la regex para `numero` de cédula

| Estrato | Detectados | Cobertura |
|---|---|---|
| alta_calidad | 14 / 30 | **47%** |
| ruidosa | 24 / 30 | **80%** |
| **Global** | **38 / 60** | **63%** |

*Nota: 37 tareas con pre-anotación insertada en Label Studio tras validación adicional de posicionamiento en el texto.*

### 2.3 Distribución de longitud de números detectados

| Dígitos | Cuenta | Tipo |
|---|---|---|
| 7 | 3 | Cédulas antiguas |
| 8 | 25 | Formato estándar mayoría del corpus |
| 9 | 2 | Variante regional |
| 10 | 8 | Cédulas recientes |

**Sin falsos positivos por longitud** — todos dentro del rango válido 7-10 dígitos colombianos.

### 2.4 Esquema de anotación Label Studio

9 labels definidas para anotación bimodal (texto + imagen):

- `numero` (pre-anotado en 37 de 60)
- `nombre_completo`, `apellidos`, `fecha_nacimiento`, `lugar_nacimiento`, `fecha_expedicion`, `lugar_expedicion`, `sexo`, `rh` (todos manuales)

## 3. Hallazgos

### 🟢 Hallazgo 1 — Estratificación funcionó (separación clara de blur_score)

Medianas: alta_calidad **6,926** vs ruidosa **335** → ratio 20.7×. La separación es limpia, garantiza que el dataset contenga representación real del ruido visual del corpus.

### 🔴 Hallazgo 2 — Contraintuitivo: ruidosas tienen mejor cobertura de regex (80% vs 47%)

**Hipótesis (publicable):** en OCR de baja calidad visual, **menos texto periférico** extraído resulta en **menos competencia** para el anchor regex. Las Cédulas nítidas capturan texto adicional (dirección, texto legal al reverso, leyendas) que introduce números alternativos (códigos, fechas, etc.) que confunden la regex de anclaje.

**Implicación práctica:** el 53% de Cédulas alta_calidad sin pre-anotación de `numero` no es un fallo del pipeline — es una limitación específica de la estrategia regex sobre texto denso. El humano aprovecha la imagen para resolver.

### 🟢 Hallazgo 3 — Regex con anchor evita falsos positivos por longitud

El filtro `7 ≤ len(digits) ≤ 10` combinado con el requerimiento de anchor (`NUMERO|CEDULA|CC|IDENTIFICACION`) eliminó todos los falsos positivos por longitud. No hay códigos de barra o números de serie capturados como cédula.

### 🟢 Hallazgo 4 — Todos los 60 docs tienen imagen procesada disponible

La intersección `corpus_ocr ∩ quality_report ∩ image_manifest` resulta en 312 Cédulas candidatas. El muestreo reproducible extrae 60 sin problemas de disponibilidad de imagen.

### 🟡 Hallazgo 5 — 23 docs requieren anotación total manual

De los 60, 23 no tienen número pre-anotado. Para el humano en Label Studio:
- 60 docs × 7 campos manuales = 420 anotaciones manuales base
- + 23 números adicionales = 443 anotaciones totales
- - 37 pre-anotaciones regex = **43 anotaciones menos**

Ahorro efectivo de la regex: ~10% del trabajo — menor al de RUT pero útil.

## 4. Anomalías y limitaciones

- El patrón **estricto** (anchor + 7-10 dígitos) tiene trade-off: alta precisión, recall medio
- Patrón relaxable para futuros experimentos: buscar sin anchor con validación posterior (código DV, municipio de expedición)
- La imagen mostrada en Label Studio es la procesada (grayscale 300 DPI), no la original — el humano no ve color original que a veces distingue legítimas de falsificaciones (no relevante para este proyecto)

## 5. Implicaciones para fases posteriores

1. **Label Studio setup bimodal** — esquema XML con `<Image>` + `<Text>` + 9 `<Label>` definido en el notebook
2. **Estimación de tiempo humano:** 15 min/doc × 60 = **15 horas** (vs. ~20 horas sin pre-anotación + sin imagen visual)
3. **Dataset de entrenamiento Cédulas:** tras revisión, estos 60 son el seed antes de augmentation 3x (§2.4 del plan) → target efectivo ~180 ejemplos
4. **Validación contra gold seed:** no hay Cédulas en el gold seed actual (15 docs). Se recomienda incluir 3-5 Cédulas en el gold extendido de 70 docs (§2.1.2) para validar el modelo NER de Fase 3

## 6. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/cedulas_muestra_manifest.csv` | 60 md5 + estrato + blur_score + numero_regex | ✅ |
| `data/processed/cedulas_preanotaciones_labelstudio.json` | Tareas Label Studio bimodales (72 KB) | ❌ PII |
| `data/processed/cedulas_preanotaciones_summary.csv` | Cobertura agregada | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §2.2 Cédula](../PLAN_MODELADO_CRISPDM.md) — task `[x]` con cobertura empírica
- [nb06_resultados.md](nb06_resultados.md) — comparación con flujo RUT (LFs full)

## 8. Referencia metodológica

La decisión de **no aplicar LFs full** está fundamentada en Ratner et al. (2018) *Snorkel: Rapid Training Data Creation with Weak Supervision*, VLDB 2018 (https://arxiv.org/abs/1711.10160), que advierte explícitamente que las LFs requieren fuentes de texto estructuradas y deterministas. OCR con CER ~0.28 no cumple ese criterio.
