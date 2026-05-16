# Fase 3.1 NER — Comparativa final

Test set único (split 70/15/15, seed 42). Métrica primaria: macro-F1 entity-level (exact span match).

## Macro F1 por tipología × candidato

| Tipología | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Δ best vs Regex | Ganador |
|---|---:|---:|---:|---:|---|
| **CC** | 0.744 | **0.915** | 0.887 | +0.171 | NER-2 CRF |
| **CED** | 0.353 | 0.880 | **0.921** | +0.567 | NER-3 spaCy+CNN |
| **POL** | 0.113 | 0.267 | **0.337** | +0.224 | NER-3 spaCy+CNN |
| **RUT** | 0.512 | 0.629 | **0.696** | +0.184 | NER-3 spaCy+CNN |

## Micro F1 por tipología × candidato

| Tipología | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN |
|---|---:|---:|---:|
| **CC** | 0.747 | **0.916** | 0.879 |
| **CED** | 0.368 | 0.890 | **0.926** |
| **POL** | 0.133 | 0.282 | **0.360** |
| **RUT** | 0.543 | **0.720** | 0.715 |

## Detalle F1 por etiqueta

### CC

| Etiqueta | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Support |
|---|---:|---:|---:|---:|
| `CC_FECHA_CONSTITUCION` | 0.842 | **0.909** | 0.769 | 11 |
| `CC_NIT` | 0.667 | **1.000** | **1.000** | 10 |
| `CC_NUM_MATRICULA` | 0.706 | **0.952** | 0.909 | 11 |
| `CC_RAZON_SOCIAL` | 0.762 | 0.800 | **0.870** | 12 |

### CED

| Etiqueta | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Support |
|---|---:|---:|---:|---:|
| `CED_APELLIDO` | 0.087 | 0.903 | **0.954** | 33 |
| `CED_FECHA_EXPEDICION` | 0.419 | 0.955 | **0.971** | 34 |
| `CED_LUGAR_EXPEDICION` | 0.542 | 0.925 | **0.941** | 35 |
| `CED_NOMBRE` | 0.000 | 0.667 | **0.824** | 30 |
| `CED_NUMERO` | 0.720 | **0.951** | 0.915 | 31 |

### POL

| Etiqueta | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Support |
|---|---:|---:|---:|---:|
| `POL_ENTIDAD_ASEGURADA` | 0.167 | **0.364** | 0.296 | 15 |
| `POL_NUM_POLIZA` | 0.000 | 0.182 | **0.333** | 9 |
| `POL_PRIMA` | 0.000 | 0.286 | **0.485** | 13 |
| `POL_TOMADOR` | **0.286** | 0.235 | 0.235 | 11 |

### RUT

| Etiqueta | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Support |
|---|---:|---:|---:|---:|
| `RUT_ACTIVIDAD_ECO` | 0.000 | **0.357** | 0.333 | 14 |
| `RUT_DIRECCION_PPAL` | 0.919 | 0.950 | **1.000** | 20 |
| `RUT_NIT` | 0.182 | 0.211 | **0.476** | 14 |
| `RUT_RAZON_SOCIAL` | 0.947 | **1.000** | 0.974 | 19 |

## Ganadores por tipología (criterio: macro-F1 → micro-F1 → costo)

| Tipología | Ganador | Macro F1 | Micro F1 | ΔvsRegex |
|---|---|---:|---:|---:|
| **CC** | NER-2 CRF | 0.915 | 0.916 | +0.171 |
| **CED** | NER-3 spaCy+CNN | 0.921 | 0.926 | +0.567 |
| **POL** | NER-3 spaCy+CNN | 0.337 | 0.360 | +0.224 |
| **RUT** | NER-3 spaCy+CNN | 0.696 | 0.715 | +0.184 |

## NER-4 Qwen 2.5 3B + QLoRA — solo POL (Colab T4)

Modelo: `unsloth/Qwen2.5-3B-Instruct-bnb-4bit`, epochs=3, train=79 docs, test=17 docs, training=6.2 min.

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `POL_ENTIDAD_ASEGURADA` | 1.000 | 0.067 | 0.125 | 1 | 0 | 14 | 15 |
| `POL_NUM_POLIZA` | 0.000 | 0.000 | 0.000 | 0 | 0 | 9 | 9 |
| `POL_PRIMA` | 0.000 | 0.000 | 0.000 | 0 | 1 | 13 | 13 |
| `POL_TOMADOR` | 0.333 | 0.091 | 0.143 | 1 | 2 | 10 | 11 |
| **macro** | — | — | **0.067** | — | — | — | — |
| **micro** | 0.400 | 0.042 | 0.075 | — | — | — | — |

**Lectura:** Qwen 3B + QLoRA con 3 épocas no convergió. Loss train final ≈ 2.10 (debería estar <1.0).
El modelo aprendió el formato JSON pero no el copy-task: devuelve `{}` vacío en la mayoría de docs.
Causa probable: insuficientes gradient updates (30 steps) sobre 79 docs train + 3B capacity.
Resultado por debajo del baseline spaCy+CNN (0.337). Se descarta NER-4 para producción.

## Hallazgos clave

- **NER-1 Regex** macro F1 promedio entre las 4 tipologías: **0.431**
- **NER-2 CRF** macro F1 promedio entre las 4 tipologías: **0.673**
- **NER-3 spaCy+CNN** macro F1 promedio entre las 4 tipologías: **0.710**

- spaCy+CNN supera a CRF en promedio: el deep learning ligero aporta sobre features hand-crafted en este corpus.
- LLM generativo (Qwen 3B + QLoRA) con corpus pequeño y few epochs no aporta sobre baselines clásicos — confirma la hipótesis de la literatura (Kalušev & Brkljač 2025).