# Resultados — Notebook 08 · Pre-anotaciones Pólizas (muestreo aleatorio)

**Fase CRISP-DM++:** 2.2 — Anotación Manual Pólizas
**Notebook:** [08_preanotaciones_polizas.ipynb](../notebooks/08_preanotaciones_polizas.ipynb)
**Fecha de ejecución:** ⏳ pendiente (notebook generado, ejecución del usuario)
**Output esperado:** `data/processed/polizas_muestra_manifest.csv` + tareas Label Studio

---

## 1. Metadatos esperados

- Python 3.12, CPU
- Duración estimada: ~2-3 min
- Input: `corpus_ocr.csv` filtrado por folder que contenga `poliz` o `liza` (mojibake-aware)
- Seed: 42 (reproducible)
- Tamaño de muestra: **120 Pólizas** (80 train + 40 val)

## 2. Resumen cuantitativo (resultados de smoke test)

### 2.1 Universo disponible

| Categoría | Docs | Páginas |
|---|---|---|
| Pólizas escaneadas (folder=`POLIZA`) | 59 | 1,024 |
| Pólizas digitales (folder=`PÃ\x83Â³liza`) | 144 | 1,743 |
| **Total Pólizas** | **203** | **2,767** |
| Con texto > 100 chars | 199 | — |

### 2.2 Muestreo

| Split | N |
|---|---|
| train | 80 |
| val | 40 |
| **Total** | **120** |

### 2.3 Cobertura de pre-anotaciones (smoke test)

| Entidad | Detectados | Cobertura | Método |
|---|---|---|---|
| `numero_poliza` | 84 / 120 | **70%** | Regex con anchor `POLIZA/NUMERO` + formato `XXX-NN-NNN` |
| `aseguradora` | 60 / 120 | **50%** | Lookup case-insensitive contra `aseguradoras_corpus.json` |

### 2.4 Top aseguradoras detectadas

| Aseguradora | Docs |
|---|---|
| Mundial de Seguros | 37 |
| Bolívar | 9 |
| AXA Colpatria | 6 |
| La Previsora | 4 |
| Sura | 2 |
| La Equidad | 1 |
| Allianz | 1 |

## 3. Hallazgos esperados

### 🟢 Hallazgo 1 — Mojibake handling crítico

Los filtros iniciales con `contains('oliz')` solo matcheaban los 59 escaneados (59/203 = 29% del universo). Tras agregar OR con `liza` (sub-string del mojibake `PÃ\x83Â³liza`), la cobertura sube a 203/203 (100%). Sin este fix, el 71% de las Pólizas (las digitales) se habrían perdido silenciosamente.

### 🟡 Hallazgo 2 — Concentración en Mundial de Seguros (62%)

De los 60 docs con aseguradora detectada, 37 son Mundial de Seguros. Esto puede reflejar:
- Sesgo real del corpus SECOP (una aseguradora dominante en contrataciones públicas)
- Sesgo del lookup (nombres más cortos matchean más fácilmente)

**Implicación para Fase 3:** el modelo NER puede sobreajustar a Mundial de Seguros. Considerar augmentation específica o reponderación si la validación muestra sesgo.

### 🟢 Hallazgo 3 — 70% cobertura `numero_poliza` razonable

Esperado por la variabilidad de formato entre aseguradoras:
- Mundial: `001-35-2024001234`
- Sura: `35-01-2024-98765`
- AXA: `POL-CT-2024-445566`
- Algunas con alfanuméricos (`BS24-15-12345`)

La regex con anchor tolera estos formatos pero no es exhaustiva. 30% de fallos será manejado por anotador humano.

### 🟡 Hallazgo 4 — 50% cobertura aseguradora

Menor que esperado. Posibles causas:
- `aseguradoras_corpus.json` tiene 11 entradas (limitado)
- Algunas Pólizas mencionan la aseguradora solo en el header visual (logo), no en el texto
- Aseguradoras menos frecuentes no están en el diccionario

**Mitigación:** el anotador agrega aseguradoras nuevas al diccionario durante la revisión — proceso iterativo.

## 4. Anomalías y limitaciones

- Muestra aleatoria no estratificada por aseguradora (decisión del plan v1.7) — puede resultar en sub-representación de aseguradoras minoritarias
- El diccionario `aseguradoras_corpus.json` incluye entradas artefacto (`Escaneada (sin texto)`, `Otra/No identificada`, `Error de lectura`) que no son aseguradoras reales — se filtran implícitamente porque no matchean el texto

## 5. Implicaciones para fases posteriores

1. **Label Studio:** crear 2 proyectos (train + val) con el esquema de 9 entidades
2. **Anotación manual de 7 campos restantes:** `tomador`, `asegurado`, `vigencia_desde`, `vigencia_hasta`, `valor_asegurado`, `prima_neta`, `amparo_principal`
3. **Tiempo humano estimado:** 20 min/doc × 120 = **40 horas**
4. **Fase 2.3 Chunking:** aplicar `sliding_window_chunks()` (Pólizas supera 1,800 tokens BPE en 14% de casos)

## 6. Evidencia en disco (esperada tras ejecución)

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/polizas_muestra_manifest.csv` | 120 md5 + split + pre-anotaciones | ✅ |
| `data/processed/polizas_preanotaciones_labelstudio.json` | Tareas Label Studio (~pendiente PII review) | ❌ PII |
| `data/processed/polizas_preanotaciones_summary.csv` | Cobertura agregada | ✅ |

## 7. Referencias internas

- [PLAN_MODELADO_CRISPDM.md §2.2 Pólizas](../PLAN_MODELADO_CRISPDM.md)
- [nb02_resultados.md](nb02_resultados.md) — `aseguradoras_corpus.json` generado

## 8. Referencia científica

- Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018. https://arxiv.org/abs/1711.10160 — justifica flujo manual vs LFs cuando layout es variable

---

> **Este reporte se actualiza tras la ejecución real del notebook por el usuario.** Los números actuales provienen del smoke test previo al commit.
