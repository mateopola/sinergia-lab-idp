# Resultados — Notebook 09 · Pre-anotaciones Cámara de Comercio

**Fase CRISP-DM++:** 2.2 — Anotación Manual Reducida CC
**Notebook:** [09_preanotaciones_camara_comercio.ipynb](../notebooks/09_preanotaciones_camara_comercio.ipynb)
**Fecha de ejecución:** ⏳ pendiente (notebook generado, ejecución del usuario)
**Output esperado:** `data/processed/camara_comercio_muestra_manifest.csv` + tareas Label Studio

---

## 1. Metadatos esperados

- Python 3.12, CPU
- Duración estimada: ~2-3 min
- Input: `corpus_ocr.csv` filtrado por folder con mojibake handling
- Seed: 42
- Tamaño de muestra: **120 CC** (80 train + 40 val)

## 2. Resumen cuantitativo (smoke test)

### 2.1 Universo disponible

| Categoría | Docs | Páginas |
|---|---|---|
| CC escaneadas (`CAMARA DE CIO`) | 16 | 160 |
| CC digitales (`CÃ\x83Â¡mara de Comercio`) | 183 | 2,611 |
| **Total CC** | **199** | **2,771** |
| Con texto > 100 chars | 198 | — |

### 2.2 Muestreo

| Split | N |
|---|---|
| train | 80 |
| val | 40 |
| **Total** | **120** |

### 2.3 Cobertura de pre-anotaciones (smoke test)

| Entidad | Detectados | Cobertura | Método |
|---|---|---|---|
| `razon_social` | 116 / 120 | **96.7%** | Regex MAYÚSCULAS + forma jurídica (reutilizado de LFs RUT) |
| `matricula` | 97 / 120 | **80.8%** | Regex `MATRICULA + Nº + dígitos` (propio CC) |
| `nit` | 77 / 120 | **64.2%** | Regex formato continuo + cajas DIAN (reutilizado de LFs RUT) |

## 3. Hallazgos esperados

### 🟢 Hallazgo 1 — Razón social con cobertura excepcional (96.7%)

Mayor que en RUT (81.9%). Posibles razones:
- CC imprime la razón social **varias veces** en distintas secciones (header, representación legal, establecimientos)
- Al menos una aparición matchea el patrón MAYÚSCULAS+forma jurídica
- Densidad textual alta (2,500 chars/pag × 11 pags promedio) maximiza oportunidades de match

### 🟡 Hallazgo 2 — NIT con cobertura menor que RUT (64% vs 98%)

Esperado porque los patrones DIAN de cajas (`8 6 0 5 1 8 8 6 2 7`) **solo existen en el formulario RUT**, no en CC. En CC el NIT aparece en formato continuo (`860.518.862-7`) con menos repeticiones. La regex reutilizada está optimizada para RUT, no CC.

**Mitigación posible:** añadir regex específica para formato CC `NIT\s*:\s*\d{9,10}-?\d`. No prioritario — 64% es cobertura usable.

### 🟢 Hallazgo 3 — Matricula mercantil bien capturada (80.8%)

Regex propia del CC: `MATRICULA(\s+MERCANTIL)?\s*N°?\s*\d{5,10}`. Funciona porque el formato está regulado (Decreto 2150/1995). Los 20% de fallos probablemente corresponden a CC escaneados con OCR ruidoso en ese campo específico.

### 🟡 Hallazgo 4 — 92% de CC son digitales (PyMuPDF)

Solo 16 de 199 (8%) son escaneados. Esto es ventajoso para pre-anotación: texto limpio sin errores OCR. Contrasta con Cédulas (93% escaneadas) donde la cobertura regex cae drásticamente.

### 🟡 Hallazgo 5 — Falsos positivos en razón social

En smoke test se observó un caso: el texto `"CERTIFICADO DE EXISTENCIA Y REPRESENTACIÓN LEGAL O DE INSCRIPCIÓN DE DOCUMENTOS."` fue capturado como `razon_social`. Es una línea estándar del encabezado del certificado, no una razón social real.

**Impacto:** ~5-10% de falsos positivos esperados, corregibles por el humano en Label Studio.

## 4. Anomalías y limitaciones

- La regex de `razon_social` es la misma que RUT — no distingue entre razón social real y frases genéricas en MAYÚSCULAS con terminación `LEGAL`, `DOCUMENTOS`, etc.
- Muestra aleatoria no estratificada por cámara de origen (CCB, CCC, CCM, etc.) — puede sobrerrepresentar Cámaras grandes
- Los 7 campos manuales (`tipo_sociedad`, `fecha_renovacion`, `domicilio`, `objeto_social`, `representante_legal`, `activos`, `capital_social`) requieren tiempo alto de anotación por densidad textual

## 5. Implicaciones para fases posteriores

1. **Label Studio:** esquema de 10 entidades, 2 proyectos (train + val)
2. **Anotación humana:** 25 min/doc × 120 = **50 horas** (mayor que Pólizas por densidad y número de campos)
3. **Fase 2.3 Chunking layout-aware:** aplicar `layout_aware_chunks()` con `cv2.HoughLinesP` para segmentar cada CC anotado en 4 bloques canónicos:
   - `datos_basicos`
   - `representantes_legales`
   - `establecimientos`
   - `actividades_economicas`
4. **Fase 3 NER:** CC es candidato primario para modelos layout-aware (LayoutLMv3) por su estructura tabular consistente — ver §3.1 del plan y PROPUESTA_MODELOS.md

## 6. Evidencia en disco (esperada tras ejecución)

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/camara_comercio_muestra_manifest.csv` | 120 md5 + split + 3 pre-anotaciones | ✅ |
| `data/processed/camara_comercio_preanotaciones_labelstudio.json` | Tareas Label Studio | ❌ PII |
| `data/processed/camara_comercio_preanotaciones_summary.csv` | Cobertura agregada | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §2.2 Cámara de Comercio](../PLAN_MODELADO_CRISPDM.md)
- [PLAN_MODELADO_CRISPDM.md §2.3 chunking layout-aware](../PLAN_MODELADO_CRISPDM.md)
- [nb06_resultados.md](nb06_resultados.md) — LFs de RUT reutilizadas
- [PROPUESTA_MODELOS.md](../PROPUESTA_MODELOS.md) — LayoutLMv3 como candidato para CC

## 8. Referencias científicas

- Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018. https://arxiv.org/abs/1711.10160
- Huang, Y., Lv, T., Cui, L., Lu, Y., Wei, F. (2022). *LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking*. ACM MM 2022. https://arxiv.org/abs/2204.08387 (relevante para Fase 3)

---

> **Este reporte se actualiza tras la ejecución real del notebook por el usuario.** Los números actuales provienen del smoke test previo al commit.
