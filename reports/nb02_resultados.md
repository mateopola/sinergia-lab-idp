# Capítulo 2 — Las herramientas: pipeline adaptativo por tipología

**Notebook:** [02_preprocesamiento_pipeline.ipynb](../notebooks/02_preprocesamiento_pipeline.ipynb)
**Fecha de ejecución:** 2026-04-08
**Fase CRISP-DM++:** 2.0 · 2.2 · 2.3 (herramientas)
**Artefacto principal:** `src/preprocessing/pipeline.py` (12 funciones productivas)
**Artefactos derivados:** `aseguradoras_corpus.json`, `vocabulario_dominio.json`, `portadas_detectadas.json`

---

## 1. El contexto — la promesa del dispatcher

El capítulo anterior (nb01) mostró que **cada tipología vive en un mundo distinto**: Cédulas escaneadas, RUT digital formulario, CC digital denso, Pólizas mezcla. Construir 4 notebooks separados (uno por tipología) duplicaría código y complicaría el mantenimiento. La alternativa: **un módulo único con funciones componibles y un dispatcher que decide qué aplicar según el tipo**.

Este es el Notebook 02 — **no un entregable de análisis, sino una caja de herramientas** que habilitará los notebooks 04–09.

## 2. La hipótesis

> Toda la variabilidad tipológica identificada en nb01 puede expresarse como **configuración** sobre un conjunto pequeño (≤12) de funciones reutilizables, siempre que el dispatcher tenga la información correcta (tipología, `es_escaneado`, calidad visual) para decidir la ruta de ejecución.

Esta hipótesis viene de la tradición del software de calidad documental, donde la **composición** supera la **duplicación** (ver principios de la librería OpenCV [1] y el survey de Document AI Wang et al. 2025 [2]).

## 3. El método — 12 funciones, 4 grupos

### 3.1 Preprocesamiento visual (nb04 depende de esto)

| Función | Propósito | Base teórica |
|---|---|---|
| `deskew()` | Corregir rotación con `cv2.minAreaRect` | Shi & Tomasi (1994) — detección de esquinas |
| `denoise()` | Gaussiano + Non-Local Means | Buades, Coll & Morel (2005) [3] |
| `enhance_contrast()` | CLAHE adaptativo | Zuiderveld (1994) [4] |
| `normalize_dpi()` | Re-muestreo a 300 DPI estándar | Estándar ISO 19005-1 (PDF/A) |
| `binarize()` | Otsu (para Tesseract — ver nb04) | Otsu (1979) [5] |

### 3.2 Detección (nb02 y posteriores)

| Función | Propósito |
|---|---|
| `detectar_portada()` | Heurística `lexicon < 50 AND blocks < 5` para páginas sin contenido |

### 3.3 Labeling Functions — pre-anotaciones regex para RUT (nb06 depende de esto)

| Función | Propósito |
|---|---|
| `extraer_entidades_rut(texto)` | 6 entidades: `nit`, `razon_social`, `regimen`, `direccion`, `municipio`, `representante_legal` |

Cada regex está basada en patrones regulatorios colombianos:
- `nit`: formato DIAN (Resolución 000110/2021 [6]) — `NNNNNNNNNN-N` o cajas de dígito individual
- `razon_social`: línea en MAYÚSCULAS con forma jurídica (`LTDA|SAS|S.A|E.U|EIRL` — Código de Comercio [7])
- `direccion`: nomenclatura Colombia (`CL|CR|AV|TV|KR` + número)
- `municipio`: lista de 17 ciudades principales
- `representante_legal`: patrón `APELLIDOS NOMBRES\nRepresentante legal`

### 3.4 Filtrado — eliminar ruido antes de embeddings

| Función | Propósito |
|---|---|
| `filtrar_ciiu_rut(texto)` | Elimina vocabulario CIIU (~300 términos de actividades económicas impresos por DIAN pero ajenos al doc individual) |

**Decisión crítica:** este filtro se usa **solo para embeddings/TF-IDF**. Para extracción NER se usa el texto completo, porque los valores de los campos pueden aparecer **después** del bloque CIIU en el orden no intuitivo de PyMuPDF.

### 3.5 Chunking — estrategia por tipología (nb10 futuro)

| Función | Estrategia | Tipologías |
|---|---|---|
| `sliding_window_chunks()` | 512 tokens / 30% overlap | RUT, Póliza |
| `layout_aware_chunks()` | `cv2.HoughLinesP` para segmentar 4 bloques | Cámara de Comercio |
| `chunk_document()` | Dispatcher: decide según `doc_type` | Todas |

## 4. Los resultados — validación sobre piloto

### 4.1 LFs RUT sobre 5 documentos piloto

El notebook validó las 6 LFs sobre un subset de 5 RUT bien formados:

| Entidad | Precisión piloto |
|---|---|
| `nit` | 5/5 (100%) |
| `razon_social` | 5/5 (100%) |
| `regimen` | 5/5 (100%) |
| `direccion` | 5/5 (100%) |
| `municipio` | 5/5 (100%) — todos Cali en muestra |
| `representante_legal` | 5/5 (100%) |

**Esta validación piloto es aspiracional** — nb06 muestra que a escala completa (216 RUT), `representante_legal` cae a 65.3%. El piloto solo prueba que **el código funciona** en casos benignos.

### 4.2 Artefactos derivados

El notebook genera tres JSONs reutilizables:

- **`aseguradoras_corpus.json`**: 11 aseguradoras identificadas en el corpus de Pólizas (nb08 lo usa como diccionario de lookup):

```json
["Escaneada (sin texto)", "Otra/No identificada",
 "Mundial de Seguros", "Error de lectura", "AXA Colpatria",
 "Sura", "Bolivar", "La Previsora", "La Equidad",
 "Allianz", ...]
```

- **`vocabulario_dominio.json`**: términos frecuentes por tipología (input para heurísticas de clasificación)
- **`portadas_detectadas.json`**: páginas detectadas como portadas por tipología (relevante solo para Pólizas 25% y CC 10%)

### 4.3 Dispatch validado

El dispatcher `chunk_document()` se valida con:

```python
chunk_document(doc_type='Cédula', ...)    → sin_chunking
chunk_document(doc_type='RUT', ...)       → sliding_window_30pct   (si >1,800 tokens)
chunk_document(doc_type='Póliza', ...)    → sliding_window_30pct
chunk_document(doc_type='Cámara', ...)    → layout_aware
```

## 5. La lectura crítica

### 5.1 Lo que el piloto NO responde

El piloto confirma que el código no tiene bugs obvios, pero **no prueba cobertura real**. La promesa de las LFs del paper Snorkel (Ratner et al. 2018 [8]) es que funcionan a escala; esa prueba se hace en nb06.

### 5.2 Hallazgo estructural — el orden no intuitivo de PyMuPDF en RUT

Durante la implementación descubrimos que PyMuPDF extrae el RUT en un **orden no natural**:

1. Primero, todos los **labels** del formulario (~1,500 chars): `"Número de Identificación Tributaria"`, `"Razón Social"`, `"Actividad Económica"`, etc.
2. Después, los **valores reales**: `"860518862"`, `"ACME SAS"`, `"4720"`, etc.

Esto tiene dos consecuencias:
- **No se puede truncar el texto** por un header como `"Actividad económica"` (estaría borrando los valores)
- Las LFs deben operar sobre **texto completo**, con patrones basados en el valor (no en la posición)

Por eso `filtrar_ciiu_rut()` usa **eliminación de tokens** (no truncado), y es exclusiva para embeddings — nunca para NER.

### 5.3 La forma jurídica como discriminador

El patrón más robusto para `razon_social` son **líneas en MAYÚSCULAS con sufijo jurídico colombiano** (`LTDA|SAS|S.A|E.U|EIRL`). El Decreto 410/1971 (Código de Comercio) [7] regula estas denominaciones — son un universo cerrado y bien tipado. Razones menos específicas (capitalización, longitud) generarían falsos positivos.

### 5.4 Detección de portada: desactivada para Cédulas

Probamos la heurística sobre 20 docs por tipología:

| Tipología | Portadas detectadas | Decisión |
|---|---|---|
| RUT | 0/20 (0%) | N/A — plantilla DIAN siempre inicia con datos |
| Póliza | 5/20 (25%) | Activar (portadas corporativas reales) |
| CC | 2/20 (10%) | Activar (portadas de algunas cámaras) |
| Cédula | 3/20 (pero falsos positivos) | **Desactivar** |

El detector disparaba sobre Cédulas porque la página 1 es una imagen sin texto, condición que cumplen "portadas verdaderas" pero también "cédulas normales". Con 93% del corpus Cédula escaneado, el detector dispara en casi todo. Excepción real detectada: `4. DOCUMENTO DE IDENTIDAD RL.pdf` (6 págs, portada textual de expediente) — caso aislado.

## 6. Anomalías y hallazgos secundarios

- **Vocabulario CC en Cédulas:** el análisis de vocabulario detectó que algunos docs en carpeta `CEDULA/` contienen vocabulario típico de Cámara de Comercio. Origen: documentos mal clasificados en el SECOP (ej. `Ponderable 3.1 Copia CC Socios - Autentica.pdf`). No es ruido de portadas sino un hallazgo del corpus — que se manejará en nb03 con una reclasificación explícita.

- **El Decreto 2150/1995** [9] (que regula la información mínima en certificados de Cámara de Comercio) impone **4 secciones canónicas**: datos básicos, representación legal, establecimientos, actividades económicas. Este hallazgo regulatorio motiva la estrategia `layout_aware_chunks()` con `HoughLinesP` para detectar los separadores.

- **`binarize()` se preservó** en el módulo aunque sabemos (spoiler de nb04) que **no se usa en el pipeline productivo** con EasyOCR. Se deja disponible para compatibilidad con Tesseract y pruebas futuras.

## 7. ¿Qué sigue? — Cap. 3

Con las herramientas listas, la pregunta que abre nb03 es:

> *De los 3 motores candidatos (EasyOCR, Tesseract, PyMuPDF), ¿cuál usar para los 416 docs escaneados?*

Esta decisión no puede tomarse por intuición — requiere un benchmark controlado sobre un **gold seed** (conjunto inmutable de transcripciones humanas). El Notebook 03 construye ese gold y mide CER + WER + entity_recall + tiempo para cada motor.

→ [nb03_resultados.md](nb03_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `src/preprocessing/pipeline.py` | 12 funciones productivas | ✅ |
| `data/processed/aseguradoras_corpus.json` | 11 aseguradoras del corpus | ✅ |
| `data/processed/vocabulario_dominio.json` | Términos frecuentes por tipología | ✅ |
| `data/processed/portadas_detectadas.json` | Outputs del detector | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | OpenCV documentation (librería productiva) | https://docs.opencv.org/ |
| [2] | Wang, W. et al. (2025). *A Survey on Document Intelligence Foundations and Frontiers*. arXiv | https://arxiv.org/abs/2510.13366 |
| [3] | Buades, A., Coll, B., Morel, J.-M. (2005). *A Non-Local Algorithm for Image Denoising*. CVPR 2005 | https://ieeexplore.ieee.org/document/1467423 |
| [4] | Zuiderveld, K. (1994). *Contrast Limited Adaptive Histogram Equalization*. Graphics Gems IV (Academic Press) | https://doi.org/10.1016/B978-0-12-336156-1.50061-6 |
| [5] | Otsu, N. (1979). *A Threshold Selection Method from Gray-Level Histograms*. IEEE TSMC | https://doi.org/10.1109/TSMC.1979.4310076 |
| [6] | DIAN. *Resolución 000110 del 11-10-2021* (estructura del RUT) | https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000110%20de%2011-10-2021.pdf |
| [7] | Decreto 410 de 1971 (Código de Comercio de Colombia) | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=41102 |
| [8] | Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 | https://arxiv.org/abs/1711.10160 |
| [9] | Decreto 2150 de 1995 (suprime trámites, regula Cámaras de Comercio) | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=1208 |
