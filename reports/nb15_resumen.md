# nb15 - Dataset BIO unificado para NER

random_state=42, split=(0.7, 0.15, 0.15)

## Conteo de docs por tipologia y split

| Tipologia | Train | Dev | Test | Total |
|---|---|---|---|---|
| CC | 56 | 12 | 12 | 80 |
| CED | 158 | 34 | 35 | 227 |
| POL | 79 | 17 | 17 | 113 |
| RUT | 93 | 20 | 20 | 133 |

## Conteo de entidades por tipologia (total = train+dev+test)

### CC

| Etiqueta | Count |
|---|---|
| `CC_RAZON_SOCIAL` | 79 |
| `CC_NIT` | 75 |
| `CC_NUM_MATRICULA` | 73 |
| `CC_FECHA_CONSTITUCION` | 70 |

### CED

| Etiqueta | Count |
|---|---|
| `CED_NUMERO` | 210 |
| `CED_APELLIDO` | 205 |
| `CED_FECHA_EXPEDICION` | 200 |
| `CED_LUGAR_EXPEDICION` | 199 |
| `CED_NOMBRE` | 198 |

### POL

| Etiqueta | Count |
|---|---|
| `POL_ENTIDAD_ASEGURADA` | 103 |
| `POL_PRIMA` | 97 |
| `POL_TOMADOR` | 96 |
| `POL_NUM_POLIZA` | 60 |

### RUT

| Etiqueta | Count |
|---|---|
| `RUT_DIRECCION_PPAL` | 133 |
| `RUT_RAZON_SOCIAL` | 126 |
| `RUT_ACTIVIDAD_ECO` | 100 |
| `RUT_NIT` | 95 |
