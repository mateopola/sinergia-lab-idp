# nb17 - NER-2 CRF (test set)

## Macro/Micro F1 por tipología

| Tipología | Macro F1 | Micro F1 | Micro P | Micro R | Support |
|---|---:|---:|---:|---:|---:|
| **CC** | 0.915 | 0.916 | 0.974 | 0.864 | 44 |
| **CED** | 0.880 | 0.890 | 0.945 | 0.840 | 163 |
| **POL** | 0.267 | 0.282 | 0.435 | 0.208 | 48 |
| **RUT** | 0.629 | 0.720 | 0.776 | 0.672 | 67 |

## CC — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CC_FECHA_CONSTITUCION` | 0.909 | 0.909 | 0.909 | 10 | 1 | 1 | 11 |
| `CC_NIT` | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 | 10 |
| `CC_NUM_MATRICULA` | 1.000 | 0.909 | 0.952 | 10 | 0 | 1 | 11 |
| `CC_RAZON_SOCIAL` | 1.000 | 0.667 | 0.800 | 8 | 0 | 4 | 12 |
| **micro** | 0.974 | 0.864 | 0.916 | — | — | — | 44 |
| **macro F1** | — | — | 0.915 | — | — | — | — |

## CED — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CED_APELLIDO` | 0.966 | 0.848 | 0.903 | 28 | 1 | 5 | 33 |
| `CED_FECHA_EXPEDICION` | 0.970 | 0.941 | 0.955 | 32 | 1 | 2 | 34 |
| `CED_LUGAR_EXPEDICION` | 0.969 | 0.886 | 0.925 | 31 | 1 | 4 | 35 |
| `CED_NOMBRE` | 0.810 | 0.567 | 0.667 | 17 | 4 | 13 | 30 |
| `CED_NUMERO` | 0.967 | 0.935 | 0.951 | 29 | 1 | 2 | 31 |
| **micro** | 0.945 | 0.840 | 0.890 | — | — | — | 163 |
| **macro F1** | — | — | 0.880 | — | — | — | — |

## POL — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `POL_ENTIDAD_ASEGURADA` | 0.571 | 0.267 | 0.364 | 4 | 3 | 11 | 15 |
| `POL_NUM_POLIZA` | 0.500 | 0.111 | 0.182 | 1 | 1 | 8 | 9 |
| `POL_PRIMA` | 0.375 | 0.231 | 0.286 | 3 | 5 | 10 | 13 |
| `POL_TOMADOR` | 0.333 | 0.182 | 0.235 | 2 | 4 | 9 | 11 |
| **micro** | 0.435 | 0.208 | 0.282 | — | — | — | 48 |
| **macro F1** | — | — | 0.267 | — | — | — | — |

## RUT — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `RUT_ACTIVIDAD_ECO` | 0.357 | 0.357 | 0.357 | 5 | 9 | 9 | 14 |
| `RUT_DIRECCION_PPAL` | 0.950 | 0.950 | 0.950 | 19 | 1 | 1 | 20 |
| `RUT_NIT` | 0.400 | 0.143 | 0.211 | 2 | 3 | 12 | 14 |
| `RUT_RAZON_SOCIAL` | 1.000 | 1.000 | 1.000 | 19 | 0 | 0 | 19 |
| **micro** | 0.776 | 0.672 | 0.720 | — | — | — | 67 |
| **macro F1** | — | — | 0.629 | — | — | — | — |
