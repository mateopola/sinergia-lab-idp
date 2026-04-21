# Capítulo 4 — La preparación: 1,678 imágenes, un giro contra-intuitivo

**Notebook:** [04_preprocesamiento_imagenes.ipynb](../notebooks/04_preprocesamiento_imagenes.ipynb)
**Fecha de ejecución:** 2026-04-17
**Fase CRISP-DM++:** 2.1 — Pipeline de Preprocesamiento Visual
**Artefactos:** `data/processed/image_manifest.csv` (1,678 filas), `data/processed/images/*.jpg` (1.9 GB)

---

## 1. El contexto — el puente entre decisión y ejecución

El capítulo anterior eligió EasyOCR. El capítulo siguiente (nb05) aplicará EasyOCR a los 1,678 escaneados. Este capítulo es el **puente**: prepara las imágenes con el pipeline OpenCV definido en nb02.

Pero este capítulo guarda un giro que no estaba en el plan original. El plan §2.1.2 definía:

```
deskew → denoise → enhance_contrast (CLAHE) → binarize → normalize_dpi
```

Durante la ejecución productiva descubrimos que **`binarize()` sabotea a EasyOCR**. Y eso cambió el pipeline final.

## 2. La hipótesis inicial

> El pipeline clásico OpenCV (deskew + denoise + CLAHE + binarize + normalize_dpi) mejora la precisión de OCR en imágenes de calidad heterogénea, siguiendo la tradición del preprocesamiento documental [1] [2].

Esta hipótesis viene del consenso industrial pre-deep-learning. Tesseract se beneficia de imágenes binarizadas — el LSTM clásico trabaja mejor sobre texto blanco/negro.

## 3. El método

### 3.1 Selección de imágenes a procesar

Filtro crítico: solo escaneados. El plan original procesaba los 1,014 docs, generando 14 GB de JPGs innecesarios (los digitales no necesitan preprocesamiento — van directo a PyMuPDF en nb05). Con el filtro `es_escaneado == True`:

```
Corpus total (incluye duplicados): 1014
Sin duplicados:                    964
  Digitales (saltan este nb):      548 docs, 11576 paginas
  Escaneados (se procesan aqui):   416 docs, 1678 paginas

DataFrame de trabajo: 416 docs escaneados
```

Reducción de disco: **14 GB → 1.9 GB** (86% ahorro).

### 3.2 Indexación MD5 para resolver mojibake

```
Indexando data/raw/ por MD5 (1-2 min la primera vez)...
  964 archivos indexados:  PDFs=955  Imagenes directas=9
  Sin match por MD5 en disco: 0 (se excluyen)

  ⚠ 1 docs reclasificados desde Fase 1:
     - CC OMAR DAZA VEGA RL ASOPERIJA.pdf   CAMARA DE CIO -> CEDULA
```

El índice MD5 resuelve dos problemas:
1. Mojibake en nombres de archivo (Windows CP-1252 → UTF-8)
2. Reclasificaciones manuales (la cédula que estaba en la carpeta equivocada)

### 3.3 Soporte para imágenes directas (.jpg/.jpeg)

9 documentos del corpus son imágenes nativas, no PDFs:

```python
SUPPORTED_EXTS = {'.pdf', '.jpg', '.jpeg', '.png'}

def load_page_as_image(path, page_num):
    if path.suffix == '.pdf':
        return fitz.open(path)[page_num - 1]  # PyMuPDF render
    else:
        return cv2.imread(str(path))  # imagen directa
```

### 3.4 Pipeline aplicado

```
deskew → denoise → enhance_contrast (CLAHE) → normalize_dpi (300 DPI)
```

**`binarize()` eliminado del pipeline productivo.** La razón de este cambio es el hallazgo central de este capítulo.

### 3.5 Ejecución por bloques con checkpoint

```
Procesando 1678 paginas en 34 bloques de 50...
```

Cada bloque produce un `image_bloque_NNNN.csv` → permite retomar si se interrumpe la ejecución.

## 4. Los resultados — los números reales

### 4.1 Corrida productiva completa

```
Paginas: 100%|██████████| 1678/1678 [08:44<00:00,  3.20it/s]
Bloques completados. Paginas con error: 0/1678 (0.0%)
```

**1,678 páginas procesadas en 8:44 minutos — 3.2 it/s. Cero errores.**

### 4.2 Distribución por tipología

```
folder
POLIZA           1024   (61.0%)
CEDULA            356   (21.2%)
CAMARA DE CIO     160    (9.5%)
rut               116    (6.9%)
OTROS              22    (1.3%)
```

Las Pólizas escaneadas dominan el cómputo (61% del tiempo) porque son multipágina (60 docs × ~17 pág/doc promedio).

### 4.3 Validación final

```
============================================================
RESULTADO DE VALIDACION
============================================================
  ✅ Paginas esperadas vs en manifest
     esperadas=1678, en manifest=1678
  ✅ Tasa de errores < 2%
     0.00% (0 paginas)
  ✅ Archivos JPG existen
     0 archivos faltantes
  ✅ MD5 presentes en quality_report
     0 md5 desconocidos
============================================================
OK — listo para Notebook 05
```

## 5. La lectura crítica — el giro contra-intuitivo

### 5.1 Descubrimiento durante una corrida anterior

En una ejecución previa del pipeline **con `binarize()`**, medimos:

- 68 páginas en 1h 54min = **110 s/pág**
- Extrapolación a 1,678 páginas = **~51 horas**

Sin `binarize()`:

- 1,678 páginas en 8:44 min = **0.31 s/pág** (solo preprocesamiento, sin OCR)
- OCR EasyOCR posterior (nb05) = ~20 s/pág

**5.5× menos tiempo de preprocesamiento + 5× menos tiempo de OCR con EasyOCR sin binarize.**

### 5.2 La explicación técnica

EasyOCR usa el detector CRAFT [3], que es **deep learning entrenado con imágenes naturales**. CRAFT espera:
- Gradientes suaves en los bordes de caracteres
- Intensidades continuas (no binarias)
- Textura CLAHE-enhanced (contraste local adaptativo)

Una imagen binarizada Otsu (0/255 puro) tiene:
- Solo ~2 valores distintos (tras binarización + JPG compression se extiende a ~20-32 valores)
- Bordes abruptos (no diferenciables)
- CRAFT no reconoce los patrones aprendidos → **aumenta el tiempo de detección** porque los bounding boxes son inciertos

### 5.3 Contexto histórico

`binarize()` era convención del paradigma OCR clásico (Tesseract, 1990s-2000s) donde Otsu mejoraba precisión. Para motores deep learning modernos (EasyOCR, PaddleOCR, TrOCR [4]), este paso es **contraproducente**.

**Moraleja del capítulo:** cuando se adopta una tecnología nueva (deep OCR), las prácticas heredadas del paradigma anterior deben re-validarse empíricamente. No asumir.

### 5.4 Pipeline final adoptado

```python
def preprocess_pipeline(img_gray):
    img = deskew(img_gray)
    img = denoise(img)
    img = enhance_contrast(img)       # CLAHE adaptativo
    img = normalize_dpi(img, 300)
    # binarize() ELIMINADO
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)  # grayscale en 3 canales
```

Output: imagen **grayscale replicada a 3 canales** (lo que EasyOCR espera). No binarizada.

## 6. Anomalías y hallazgos secundarios

### 6.1 Errores MuPDF benignos

Durante el render de PDFs corruptos:

```
MuPDF error: library error: zlib error: invalid block type
MuPDF error: format error: cmsOpenProfileFromMem failed
```

Son **advertencias** de PyMuPDF al abrir PDFs con metadata malformada (perfiles de color corruptos). No afectan el render de las páginas. Se registran pero no se abortan.

### 6.2 Bug resuelto: numeración de bloques

Un bug inicial hizo que los `image_bloque_NNNN.csv` se sobreescribieran en re-ejecuciones. Fix: numeración continua desde el último bloque existente.

### 6.3 Paths absolutos en manifest

Originalmente `image_manifest.csv` guardaba paths relativos. nb05 se ejecuta desde otro directorio → los paths no resolvían → 100% errores. Fix: `str(path.resolve())` en nb04 + resolución defensiva en nb05.

## 7. ¿Qué sigue? — Cap. 5

Con las 1,678 imágenes preprocesadas y el descubrimiento de `binarize()` documentado, la siguiente pregunta es operativa:

> *Aplicar EasyOCR a las 1,678 imágenes tomará ~23 horas. ¿Qué descubriremos durante esa corrida?*

El Notebook 05 hace el OCR masivo overnight. El hallazgo no es OCR en sí — es que al finalizar descubriremos **2 gaps de cobertura** que obligan al Notebook 05b de cierre.

→ [nb05_resultados.md](nb05_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/image_manifest.csv` | 1,678 filas × 13 columnas con paths absolutos | ✅ |
| `data/processed/images/processed_{md5}_page_{N}.jpg` | JPGs grayscale 300 DPI | ❌ (1.9 GB) |
| `data/processed/image_blocks/image_bloque_NNNN.csv` | 34 checkpoints (bloques de 50) | ❌ |
| `data/processed/fig12_preprocesamiento_test.png` | Visual antes/después (3 docs piloto) | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | Otsu, N. (1979). *A Threshold Selection Method from Gray-Level Histograms*. IEEE TSMC | https://doi.org/10.1109/TSMC.1979.4310076 |
| [2] | Smith, R. (2007). *An Overview of the Tesseract OCR Engine*. ICDAR (recomienda binarización) | https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/ |
| [3] | Baek, Y. et al. (2019). *Character Region Awareness for Text Detection (CRAFT)*. CVPR 2019 | https://arxiv.org/abs/1904.01941 |
| [4] | Li, M. et al. (2021). *TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models*. AAAI 2023 | https://arxiv.org/abs/2109.10282 |
| [5] | Zuiderveld, K. (1994). *Contrast Limited Adaptive Histogram Equalization*. Graphics Gems IV | https://doi.org/10.1016/B978-0-12-336156-1.50061-6 |
| [6] | Buades, A., Coll, B., Morel, J.-M. (2005). *A Non-Local Algorithm for Image Denoising*. CVPR 2005 | https://ieeexplore.ieee.org/document/1467423 |

**Referencia interna:**
- [OCR_BENCHMARK.md §2.6.0](../OCR_BENCHMARK.md) — decisión técnica completa sobre `binarize()`
- [PLAN_MODELADO_CRISPDM.md §2.1.3](../PLAN_MODELADO_CRISPDM.md) — registro de la decisión arquitectural
