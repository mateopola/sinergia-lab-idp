# nb16 - NER-1 Regex baseline (test set)

## Macro/Micro F1 por tipología

| Tipología | Macro F1 | Micro F1 | Micro P | Micro R | Support |
|---|---:|---:|---:|---:|---:|
| **CC** | 0.744 | 0.747 | 0.903 | 0.636 | 44 |
| **CED** | 0.353 | 0.368 | 0.646 | 0.258 | 163 |
| **POL** | 0.113 | 0.133 | 0.333 | 0.083 | 48 |
| **RUT** | 0.512 | 0.543 | 0.521 | 0.567 | 67 |

## CC — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CC_FECHA_CONSTITUCION` | 1.000 | 0.727 | 0.842 | 8 | 0 | 3 | 11 |
| `CC_NIT` | 0.750 | 0.600 | 0.667 | 6 | 2 | 4 | 10 |
| `CC_NUM_MATRICULA` | 1.000 | 0.545 | 0.706 | 6 | 0 | 5 | 11 |
| `CC_RAZON_SOCIAL` | 0.889 | 0.667 | 0.762 | 8 | 1 | 4 | 12 |
| **micro** | 0.903 | 0.636 | 0.747 | — | — | — | 44 |
| **macro F1** | — | — | 0.744 | — | — | — | — |

## CED — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `CED_APELLIDO` | 0.154 | 0.061 | 0.087 | 2 | 11 | 31 | 33 |
| `CED_FECHA_EXPEDICION` | 1.000 | 0.265 | 0.419 | 9 | 0 | 25 | 34 |
| `CED_LUGAR_EXPEDICION` | 1.000 | 0.371 | 0.542 | 13 | 0 | 22 | 35 |
| `CED_NOMBRE` | 0.000 | 0.000 | 0.000 | 0 | 11 | 30 | 30 |
| `CED_NUMERO` | 0.947 | 0.581 | 0.720 | 18 | 1 | 13 | 31 |
| **micro** | 0.646 | 0.258 | 0.368 | — | — | — | 163 |
| **macro F1** | — | — | 0.353 | — | — | — | — |

## POL — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `POL_ENTIDAD_ASEGURADA` | 0.222 | 0.133 | 0.167 | 2 | 7 | 13 | 15 |
| `POL_NUM_POLIZA` | 0.000 | 0.000 | 0.000 | 0 | 0 | 9 | 9 |
| `POL_PRIMA` | 0.000 | 0.000 | 0.000 | 0 | 0 | 13 | 13 |
| `POL_TOMADOR` | 0.667 | 0.182 | 0.286 | 2 | 1 | 9 | 11 |
| **micro** | 0.333 | 0.083 | 0.133 | — | — | — | 48 |
| **macro F1** | — | — | 0.113 | — | — | — | — |

## RUT — detalle por etiqueta

| Etiqueta | P | R | F1 | TP | FP | FN | support |
|---|---:|---:|---:|---:|---:|---:|---:|
| `RUT_ACTIVIDAD_ECO` | 0.000 | 0.000 | 0.000 | 0 | 18 | 14 | 14 |
| `RUT_DIRECCION_PPAL` | 1.000 | 0.850 | 0.919 | 17 | 0 | 3 | 20 |
| `RUT_NIT` | 0.158 | 0.214 | 0.182 | 3 | 16 | 11 | 14 |
| `RUT_RAZON_SOCIAL` | 0.947 | 0.947 | 0.947 | 18 | 1 | 1 | 19 |
| **micro** | 0.521 | 0.567 | 0.543 | — | — | — | 67 |
| **macro F1** | — | — | 0.512 | — | — | — | — |
