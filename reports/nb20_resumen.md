# nb20 - Dataset QLoRA POL (prompt-completion)

Schema: ['POL_NUM_POLIZA', 'POL_ENTIDAD_ASEGURADA', 'POL_TOMADOR', 'POL_PRIMA']

## Tamaño por split

| Split | Docs | Avg chars |
|---|---:|---:|
| train | 79 | 2470 |
| dev | 17 | 2422 |
| test | 17 | 2286 |

## Null por etiqueta (cuántos docs no tienen la entidad anotada)

| Etiqueta | train | dev | test |
|---|---:|---:|---:|
| `POL_NUM_POLIZA` | 39 | 6 | 8 |
| `POL_ENTIDAD_ASEGURADA` | 9 | 1 | 2 |
| `POL_TOMADOR` | 14 | 1 | 6 |
| `POL_PRIMA` | 12 | 0 | 4 |

Listo para subir a Drive: `data/_to_upload/qlora_pol/` (3 archivos)
