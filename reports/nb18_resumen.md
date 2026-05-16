# nb18 - NER-3 spaCy v3 + CNN (test set)

## Macro/Micro F1 por tipología

| Tipología | Macro F1 | Micro F1 | Micro P | Micro R | Support | Train s |
|---|---:|---:|---:|---:|---:|---:|
| **CC** | 0.887 | 0.879 | 0.851 | 0.909 | 44 | 71.3 |
| **CED** | 0.921 | 0.926 | 0.973 | 0.883 | 163 | 59.9 |
| **POL** | 0.337 | 0.360 | 0.390 | 0.333 | 48 | 124.3 |
| **RUT** | 0.696 | 0.715 | 0.643 | 0.806 | 67 | 164.6 |

## CC — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CC_FECHA_CONSTITUCION` | 0.667 | 0.909 | 0.769 | 10 | 5 | 1 | 11 |
| `CC_NIT` | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 | 10 |
| `CC_NUM_MATRICULA` | 0.909 | 0.909 | 0.909 | 10 | 1 | 1 | 11 |
| `CC_RAZON_SOCIAL` | 0.909 | 0.833 | 0.870 | 10 | 1 | 2 | 12 |
| **micro** | 0.851 | 0.909 | 0.879 | — | — | — | 44 |
| **macro F1** | — | — | 0.887 | — | — | — | — |

## CED — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CED_APELLIDO` | 0.969 | 0.939 | 0.954 | 31 | 1 | 2 | 33 |
| `CED_FECHA_EXPEDICION` | 0.971 | 0.971 | 0.971 | 33 | 1 | 1 | 34 |
| `CED_LUGAR_EXPEDICION` | 0.970 | 0.914 | 0.941 | 32 | 1 | 3 | 35 |
| `CED_NOMBRE` | 1.000 | 0.700 | 0.824 | 21 | 0 | 9 | 30 |
| `CED_NUMERO` | 0.964 | 0.871 | 0.915 | 27 | 1 | 4 | 31 |
| **micro** | 0.973 | 0.883 | 0.926 | — | — | — | 163 |
| **macro F1** | — | — | 0.921 | — | — | — | — |

## POL — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `POL_ENTIDAD_ASEGURADA` | 0.333 | 0.267 | 0.296 | 4 | 8 | 11 | 15 |
| `POL_NUM_POLIZA` | 0.667 | 0.222 | 0.333 | 2 | 1 | 7 | 9 |
| `POL_PRIMA` | 0.400 | 0.615 | 0.485 | 8 | 12 | 5 | 13 |
| `POL_TOMADOR` | 0.333 | 0.182 | 0.235 | 2 | 4 | 9 | 11 |
| **micro** | 0.390 | 0.333 | 0.360 | — | — | — | 48 |
| **macro F1** | — | — | 0.337 | — | — | — | — |

## RUT — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `RUT_ACTIVIDAD_ECO` | 0.312 | 0.357 | 0.333 | 5 | 11 | 9 | 14 |
| `RUT_DIRECCION_PPAL` | 1.000 | 1.000 | 1.000 | 20 | 0 | 0 | 20 |
| `RUT_NIT` | 0.357 | 0.714 | 0.476 | 10 | 18 | 4 | 14 |
| `RUT_RAZON_SOCIAL` | 0.950 | 1.000 | 0.974 | 19 | 1 | 0 | 19 |
| **micro** | 0.643 | 0.806 | 0.715 | — | — | — | 67 |
| **macro F1** | — | — | 0.696 | — | — | — | — |
