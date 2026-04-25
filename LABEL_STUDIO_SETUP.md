# Label Studio — Setup y guía de uso para Fase 2.2

Guía end-to-end para instalar Label Studio, crear los 4 proyectos de anotación (RUT, Cédulas, Pólizas, Cámara de Comercio), importar las pre-anotaciones generadas por nb06-nb09, y exportar el dataset final corregido.

**Tiempo total estimado de revisión humana:** ~20-25 h para los 516 docs.

---

## 1. Instalación (una sola vez)

```bash
pip install label-studio
```

Requiere Python 3.10-3.12 (ya lo tienes). No necesita Docker ni servicios externos — corre como proceso local.

Verificar instalación:

```bash
label-studio --version
```

## 2. Arrancar el servidor

```bash
label-studio start
```

Esto:
- Levanta un servidor local en **http://localhost:8080**
- Crea/usa una base SQLite en `~/.local/share/label-studio/` (Linux/Mac) o `%APPDATA%\label-studio\` (Windows)
- Abre el navegador automáticamente

**Primera vez:** te pide crear una cuenta (email + password). Es solo local — no se sube nada a la nube. Sugerencia: usa el mismo email tuyo y una pass simple, como es offline no importa la seguridad.

Para detener: `Ctrl+C` en la terminal. Los datos persisten en disco.

## 3. Crear los 4 proyectos

Para cada tipología repetir el flujo:

1. **Create Project** → nombre del proyecto
2. **Data Import** → subir el JSON correspondiente (desde `data/processed/`)
3. **Labeling Setup** → pegar el XML de configuración (abajo)
4. **Save**

Al importar, Label Studio detecta automáticamente las `predictions` del JSON y te las muestra pre-pintadas en cada tarea.

### 3.1 Proyecto RUT — 216 docs

- **Nombre:** `RUT — DIAN (216 docs)`
- **Archivo:** [data/processed/rut_preanotaciones_labelstudio.json](data/processed/rut_preanotaciones_labelstudio.json)
- **XML:**

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="nit" background="#FF6B6B"/>
    <Label value="razon_social" background="#4ECDC4"/>
    <Label value="regimen" background="#45B7D1"/>
    <Label value="direccion" background="#FFA500"/>
    <Label value="municipio" background="#95E1D3"/>
    <Label value="representante_legal" background="#C9A0FF"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

### 3.2 Proyecto Cédulas — 60 docs (bimodal: texto + imagen)

- **Nombre:** `Cédulas — Registraduría (60 docs)`
- **Archivo:** [data/processed/cedulas_preanotaciones_labelstudio.json](data/processed/cedulas_preanotaciones_labelstudio.json)
- **XML:**

```xml
<View>
  <Image name="image" value="$image_path"/>
  <Labels name="label" toName="text">
    <Label value="numero" background="#FF6B6B"/>
    <Label value="nombre_completo" background="#4ECDC4"/>
    <Label value="apellidos" background="#45B7D1"/>
    <Label value="fecha_nacimiento" background="#FFA500"/>
    <Label value="lugar_nacimiento" background="#95E1D3"/>
    <Label value="fecha_expedicion" background="#C9A0FF"/>
    <Label value="lugar_expedicion" background="#F38181"/>
    <Label value="sexo" background="#AA96DA"/>
    <Label value="rh" background="#FCBAD3"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

**Nota bimodal:** cada tarea tiene `image_path` + `text`. La imagen aparece arriba (solo de referencia visual) y marcas el span sobre el texto de abajo.

### 3.3 Proyecto Pólizas — 120 docs

- **Nombre:** `Pólizas — Seguros (80 train + 40 val)`
- **Archivo:** [data/processed/polizas_preanotaciones_labelstudio.json](data/processed/polizas_preanotaciones_labelstudio.json)
- **XML:**

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="numero_poliza" background="#FF6B6B"/>
    <Label value="aseguradora" background="#4ECDC4"/>
    <Label value="tomador" background="#45B7D1"/>
    <Label value="asegurado" background="#FFA500"/>
    <Label value="vigencia_desde" background="#95E1D3"/>
    <Label value="vigencia_hasta" background="#C9A0FF"/>
    <Label value="valor_asegurado" background="#F38181"/>
    <Label value="prima_neta" background="#AA96DA"/>
    <Label value="amparo_principal" background="#FCBAD3"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

### 3.4 Proyecto Cámara de Comercio — 120 docs

- **Nombre:** `Cámara Comercio — CC (80 train + 40 val)`
- **Archivo:** [data/processed/camara_comercio_preanotaciones_labelstudio.json](data/processed/camara_comercio_preanotaciones_labelstudio.json)
- **XML:**

```xml
<View>
  <Labels name="label" toName="text">
    <Label value="nit" background="#FF6B6B"/>
    <Label value="razon_social" background="#4ECDC4"/>
    <Label value="matricula" background="#45B7D1"/>
    <Label value="tipo_sociedad" background="#FFA500"/>
    <Label value="fecha_renovacion" background="#95E1D3"/>
    <Label value="domicilio" background="#C9A0FF"/>
    <Label value="objeto_social" background="#F38181"/>
    <Label value="representante_legal" background="#AA96DA"/>
    <Label value="activos" background="#FCBAD3"/>
    <Label value="capital_social" background="#B5EAD7"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>
```

## 4. Cómo anotar (flujo por tarea)

Al abrir una tarea ves:
- **Panel izquierdo:** los botones numerados de cada entidad (ej: `[1] nit`, `[2] razon_social`...).
- **Panel central:** el texto del documento con las pre-anotaciones ya pintadas con los colores del XML.
- **Panel derecho:** lista de todas las entidades marcadas con opción de editar/borrar.

### Atajos de teclado esenciales

| Tecla | Acción |
|---|---|
| `1`–`9` | Seleccionar la entidad N de la lista (en el orden del XML) |
| Arrastrar sobre texto | Crear anotación con la entidad seleccionada |
| Click sobre anotación → `Delete` / `Backspace` | Borrar anotación |
| Click sobre anotación → arrastrar bordes | Ajustar span |
| `Ctrl+Enter` | Submit (confirmar tarea y pasar a la siguiente) |
| `Ctrl+Z` | Deshacer |
| `→` / `←` | Siguiente/anterior tarea |

### Criterios de calidad

Revisar cada pre-anotación y decidir:

- ✅ **Correcta y completa** → dejar como está.
- ✂️ **Correcta pero span mal cortado** (incluye caracteres extra o le falta texto) → ajustar bordes.
- ❌ **Falso positivo** (la regex marcó algo que no es la entidad) → eliminar.
- ➕ **Falta algo que debería estar** → seleccionar el texto y asignar la entidad.

El detalle de QUÉ es cada entidad y casos borde está en [CRITERIOS_ANOTACION.md](CRITERIOS_ANOTACION.md).

## 5. Orden de revisión recomendado (ROI)

```
1. Cámara de Comercio  (120 docs, ~3h)  — 96.7% pre-anotado, casi solo confirmar
2. RUT                 (216 docs, ~8h)  — cobertura 65-99%, más entidades
3. Pólizas             (120 docs, ~6h)  — solo 2 entidades pre-anotadas, más trabajo manual
4. Cédulas             (60 docs, ~3h)   — bimodal, más lento por doc
```

Partir cada tipología en sesiones de ~2h para no perder concentración.

## 6. Exportar cuando termines

Por cada proyecto completado:

1. **Export** (botón arriba a la derecha)
2. Formato: **JSON-MIN** (o **JSON** completo si quieres preservar timestamps)
3. Descargar → guardar en `data/processed/label_studio_export/<tipologia>.json`

Esos JSONs son el input del **nb10 (chunking)** que convierte las anotaciones en `train.jsonl` / `val.jsonl` para fine-tuning.

## 7. Troubleshooting

| Problema | Solución |
|---|---|
| La imagen de Cédulas no carga | En Label Studio: Settings → Cloud Storage → Add local files → apuntar a `data/processed/images/` |
| Al importar el JSON no aparecen las pre-anotaciones | Verificar que el XML del proyecto tenga el nombre `name="label"` que matchea el `from_name` de las predicciones |
| El servidor se cae por uso de memoria | Reiniciar `label-studio start`; los datos están en disco, no se pierden |
| Quiero hacer export incremental (ej: solo 20 docs corregidos) | Filtrar por "Labeled: Yes" antes de exportar |

## 8. Referencias

- Documentación oficial: https://labelstud.io/guide/
- Labeling bimodal (para Cédulas): https://labelstud.io/guide/labeling#Bimodal-labeling
- NER Tagging config: https://labelstud.io/templates/named_entity
