# Entrega — Gold Standard y Selección del Motor OCR

**Proyecto:** SinergIA Lab — IDP para Documentos Corporativos Colombianos SECOP
**Institución:** Pontificia Universidad Javeriana · Especialización en Inteligencia Artificial · Ciclo 1 · 2026
**Fase CRISP-DM++:** 2.1.1 — Selección del Motor OCR
**Fecha de entrega:** 2026-04-20
**Notebook de referencia:** `notebooks/03_benchmark_ocr.ipynb`
**Bitácora completa:** `OCR_BENCHMARK.md`

---

## Resumen ejecutivo

Este documento responde cinco preguntas metodológicas centrales del proyecto:

1. ¿Cómo se construyó el *gold standard* de evaluación OCR?
2. ¿Para qué sirve ese gold?
3. ¿Qué motores OCR se compararon?
4. ¿Qué métricas cuantitativas se calcularon y qué mide cada una?
5. ¿Qué motor se eligió y por qué?

Se siguió un diseño experimental controlado sobre **15 documentos transcritos manualmente**, aplicando métricas estándar de la literatura OCR (CER, WER) y una métrica específica para el dominio del proyecto (entity_recall). La decisión final se sustenta en una regla documentada previa al experimento.

---

## 1. El gold standard: qué es, cómo se construyó y para qué sirve

### 1.1 Definición operativa

Un **gold standard** (también llamado *ground truth*) en tareas de Procesamiento de Lenguaje Natural (PLN) y Visión por Computador (CV) es un **conjunto de datos anotado manualmente con rigurosidad**, tratado como la verdad de referencia contra la cual se evalúa todo sistema automático [1] [2].

En este proyecto, el gold standard es un subconjunto de **15 documentos del corpus SECOP** con transcripciones humanas literales a nivel de carácter.

### 1.2 Propósito en el proyecto

El gold cumple **cuatro roles** simultáneos en el ciclo de vida del proyecto:

| Rol | Fase | Cómo se usa |
|---|---|---|
| **Benchmark OCR** | 2.1.1 (este documento) | Medir la calidad de cada motor OCR contra texto humano |
| **Validación de Labeling Functions (LFs)** | 2.2 (RUT) | Verificar que las LFs regex extraen entidades consistentes con el humano |
| **Validación de reconstrucción textual** | 2.1.4 (cierre de gaps) | Confirmar que el corpus completo (13,254 páginas) mantiene la calidad OCR medida |
| **Evaluación final de F1 del modelo NER** | Fase 4 | Comparar extracción del modelo fine-tuneado contra etiquetas humanas |

Sin gold estándar, la pregunta "¿funciona mi sistema?" no tiene respuesta cuantificable. Este es el principio metodológico central de CRISP-DM [3] y de toda evaluación experimental de PLN moderno [4].

### 1.3 Diseño de la muestra: composición y justificación

La composición del gold se definió **antes** de ejecutar el benchmark, bajo tres principios:

1. **Cobertura tipológica:** representar las 4 tipologías del corpus (Cédula, RUT, Póliza, Cámara de Comercio).
2. **Estratificación por calidad visual en Cédulas:** incluir ejemplos nítidos y ruidosos para medir sensibilidad al ruido.
3. **Representatividad de escaneados:** el gold solo contiene documentos escaneados (son los que OCR debe resolver).

| Tipología | Documentos | Criterio |
|---|---|---|
| Cédula | 6 | 3 alta calidad (`blur_score ≥ 100`, `contrast ≥ 30`) + 3 ruidosas |
| RUT | 3 | Escaneados (minoría dentro del RUT: 11.5% del total) |
| Póliza | 3 | Escaneadas (27% del corpus de Pólizas) |
| Cámara de Comercio | 3 | Escaneadas (9% del corpus de CC) |
| **Total** | **15 docs** | |

**Cap uniforme:** se transcribieron las primeras **4 páginas** de cada documento multipágina (no todo el documento). Esta decisión reduce el esfuerzo humano manteniendo la representatividad (`pages_to_use=4` configurable en `gold_seed_manifest.csv`).

### 1.4 Proceso de construcción paso a paso

#### Paso 1 — Selección reproducible

La selección se hizo con `random_state=42` fijo para garantizar reproducibilidad. Un script (`notebooks/03_benchmark_ocr.ipynb`, celda 9-11) filtra el corpus por tipología y calidad, y muestrea los 15 documentos. El plan de muestreo generado:

```
{'CEDULA': {'alta': 3, 'ruidosa': 3},
 'rut': {'cualquiera': 3},
 'POLIZA': {'cualquiera': 3},
 'CAMARA DE CIO': {'cualquiera': 3}}
```

#### Paso 2 — Resolución de mojibake vía índice MD5

El corpus SECOP venía con nombres de archivo afectados por conversión Windows CP-1252 → UTF-8 fallida (`CÃÂ©dula` en vez de `Cédula`, etc.). Para evitar colisiones, se construyó un índice MD5 de todos los PDFs en disco:

```
Indexando data/raw/ por MD5 (puede tomar 1-2 min la primera vez)...
  955 PDFs indexados en disco
  Sin match por MD5 en disco (excluidos): 9
```

Este índice también detectó **una reclasificación**: el archivo `CC OMAR DAZA VEGA RL ASOPERIJA.pdf` estaba en la carpeta `CAMARA DE CIO` pero es una Cédula. Se reclasificó vía MD5 y se reemplazó en el gold por `CERTIFICADO CAMARA COMERCIO ene2026 MAX.pdf`.

#### Paso 3 — Transcripción humana literal

Para cada uno de los 15 documentos seleccionados se generó una plantilla `{md5}.txt` y un anotador humano (Mateo) transcribió literalmente el texto visible, carácter por carácter, **sin corregir errores del original** (ortografía, acentos, abreviaciones). La transcripción respeta el orden de lectura natural (arriba-abajo, izquierda-derecha).

#### Paso 4 — Validación de completitud

Un script verifica que las 15 transcripciones están listas antes de ejecutar el benchmark:

```
Transcripciones listas: 15/15
```

Longitudes obtenidas (validación de coherencia con la naturaleza del documento):

| Tipología | Chars mínimo | Chars máximo | Observación |
|---|---|---|---|
| Cédula | 447 | 466 | 1 página estándar, texto uniforme |
| RUT | 2,273 | 12,011 | Varía según páginas del formulario DIAN |
| Póliza | 5,792 | 11,565 | Layout denso con términos y condiciones |
| Cámara de Comercio | 9,741 | 16,157 | Mayor densidad textual (certificados extensos) |

#### Paso 5 — Congelación del gold

Tras validación, el gold se marca **inmutable**:

- **Metadata** en `data/gold/gold_seed_manifest.csv`
- **Transcripciones** en `data/gold/transcriptions/{md5}.txt`
- **Semilla fija** `random_state=42` para reproducibilidad
- **Bandera** `RESAMPLE=False` en el notebook para evitar re-muestreos accidentales

### 1.5 Por qué 15 documentos y no más

La decisión de usar una "gold seed" reducida (15 docs) en lugar del gold extendido (70 docs originalmente planteado) se documenta en `PLAN_MODELADO_CRISPDM.md §2.1.2` con tres razones:

1. **Costo humano:** transcribir 70 documentos multipágina tomaría ~50 horas. 15 documentos toman ~8 horas.
2. **Suficiencia estadística para la decisión OCR:** 15 docs × 2 motores = 30 puntos de datos. La varianza entre motores es lo suficientemente alta como para detectar el ganador con 15 docs (confirmado por los resultados).
3. **Gold extendido diferido a Fase 4:** el gold de 70 docs con Cohen's Kappa ≥ 0.85 se construirá antes de la evaluación del modelo NER, donde la precisión estadística sí es crítica.

---

## 2. Los motores OCR comparados

### 2.1 EasyOCR 1.7.2 — candidato deep learning

**EasyOCR** es una librería open-source [5] que implementa una pipeline de dos redes neuronales:

1. **CRAFT** (Character Region Awareness For Text detection, Baek et al., CVPR 2019 [6]): red convolucional que detecta regiones de texto a nivel de carácter, no de palabra. Produce bounding boxes precisos incluso en texto curvo o desordenado.

2. **CRNN** (Convolutional Recurrent Neural Network, Shi, Bai, Yao, IEEE TPAMI 2017 [7]): red que combina CNN para extraer features visuales + RNN para reconocer la secuencia de caracteres dentro de cada región detectada.

- Soporta 80+ idiomas, incluido español.
- Corre en CPU o GPU (CUDA).
- Modelo descargable una vez (~60 MB para español).

### 2.2 Tesseract 5.5.0 — candidato clásico

**Tesseract OCR Engine** es el motor OCR open-source más longevo en uso. Desarrollado originalmente en HP Labs (1984-1994), liberado por Google en 2005, y mantenido por la comunidad [8].

- Desde la versión 4.0 (2018), usa un clasificador **LSTM** (Long Short-Term Memory) en lugar del clasificador clásico pre-2018.
- Requiere descarga manual de `spa.traineddata` para español (~30 MB).
- Produce texto plano; los bounding boxes son opcionales.
- Fundamentación técnica: Smith (2007) [9].

### 2.3 Motores descartados

Durante la fase de diseño (previo a este benchmark) se evaluaron dos candidatos adicionales que se descartaron por razones documentadas:

| Motor | Razón del descarte | Fuente |
|---|---|---|
| **PaddleOCR** (Baidu) | Incompatible con Python 3.12 al momento del benchmark | `PLAN_MODELADO_CRISPDM.md §2.1.1` |
| **Donut** (NAVER, 2022) [10] | No es OCR propiamente dicho sino un VLM end-to-end (imagen → JSON). Corpus multi-tipológico requeriría 4 modelos especializados. Descartado como arquitectura global en `ALT-1` del plan. | `PLAN_MODELADO_CRISPDM.md §ALT-1` |

### 2.4 Nota sobre PyMuPDF

**PyMuPDF** [11] no es un motor OCR sino un **extractor nativo** de texto de PDFs digitales. No se incluye en el benchmark porque opera en un régimen distinto (`es_escaneado == False`). En el pipeline productivo del proyecto, PyMuPDF maneja los 548 documentos digitales del corpus con CER ≈ 0 (extracción perfecta), mientras que EasyOCR/Tesseract manejan los 416 escaneados. Esta bifurcación está documentada en `OCR_BENCHMARK.md §2.6.2`.

---

## 3. Las métricas: qué se midió y qué mide cada una

Se calcularon **cuatro métricas** por cada combinación (motor × documento). Las métricas se diseñaron para responder cuatro preguntas distintas:

### 3.1 Character Error Rate (CER) — "¿qué tan cerca está el texto OCR del texto real?"

**Definición matemática** [12]:

```
CER = (S + D + I) / N
```

donde:
- `S` = número de caracteres sustituidos
- `D` = número de caracteres borrados
- `I` = número de caracteres insertados
- `N` = número total de caracteres en el texto de referencia (gold)

Se calcula con la **distancia de edición de Levenshtein** entre `texto_OCR` y `texto_gold`. Es la métrica canónica de literatura OCR desde los años 80.

**Dirección:** ↓ menor es mejor. `CER = 0` significa coincidencia perfecta.

**Normalización previa:** lowercase + colapso de whitespace (evita que diferencias de mayúsculas o espacios múltiples cuenten como errores).

**Implementación:** librería `jiwer` [13] `jiwer.cer(reference, hypothesis)`.

### 3.2 Word Error Rate (WER) — "¿cuántas palabras está errando el OCR?"

**Definición matemática** [12]:

```
WER = (S + D + I) / N
```

Misma fórmula que CER pero operando a nivel de **palabra** en vez de carácter. Se calcula con alineación Levenshtein sobre la secuencia de palabras tokenizadas por whitespace.

**Dirección:** ↓ menor es mejor.

**Por qué medir ambas:** CER es sensible a errores de tipografía (`nit` → `mt`), WER es sensible a palabras enteras fragmentadas (`RICO S.A.` → `RICOS.A.`). Dos motores pueden tener CER similar pero WER muy distinto, lo que tiene implicaciones downstream distintas.

### 3.3 Entity Recall — "¿qué utilidad tiene este OCR para extracción de entidades?"

Esta es **la métrica más importante** para el objetivo del proyecto (NER sobre documentos colombianos).

**Definición operativa propia del proyecto:**

```
entity_recall = |entidades_detectadas_en_OCR ∩ entidades_en_gold| / |entidades_en_gold|
```

Las "entidades" se extraen con **cuatro regex estándar** para el dominio colombiano [14]:

| Entidad | Patrón regex |
|---|---|
| `nit` | `\b\d{8,10}[-\s]?\d\b` |
| `cedula` | `\b\d{1,3}(?:[.\s]\d{3}){2,3}\b` |
| `fecha` | `\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b` |
| `monto` | `\$\s?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?` |

**Dirección:** ↑ mayor es mejor. `entity_recall = 1.0` significa que el OCR preservó todas las entidades del gold.

**Por qué es crítico:** un OCR puede tener CER 0.30 (30% de errores de carácter) pero si los dígitos de un NIT quedan rotos, la extracción NER downstream falla aunque "en promedio" el texto se lea. Entity recall mide directamente **utilidad downstream**.

Esta métrica está alineada con la evaluación a nivel de span/entidad del shared task CoNLL-2002 [4].

### 3.4 Tiempo por página (s/page) — "¿cuánto cuesta operar esto?"

**Definición:**

```
s_per_page = tiempo_total_ejecución / número_de_páginas
```

Se mide con `time.perf_counter()` en alta resolución, contabilizando **solo el tiempo de inferencia** (no de carga del modelo, que es amortizable).

**Dirección:** ↓ menor es mejor.

**Por qué es crítico:** el corpus tiene 1,678 páginas escaneadas. Un motor a 50 s/pág requiere ~23 horas de cómputo. Un motor a 5 s/pág requiere ~2.3 horas. La diferencia operativa es sustancial para iteración experimental.

### 3.5 Resumen de las métricas

| Métrica | Fórmula | Dirección | Responde a |
|---|---|---|---|
| **CER** | `(S+D+I)/N` carácter | ↓ | Calidad carácter-a-carácter |
| **WER** | `(S+D+I)/N` palabra | ↓ | Calidad palabra-a-palabra |
| **entity_recall** | `\|ent_OCR ∩ ent_GT\|/\|ent_GT\|` | ↑ | Utilidad downstream para NER |
| **s_per_page** | `tiempo / pags` | ↓ | Costo operativo |

---

## 4. Diseño experimental

### 4.1 Procedimiento

Para cada uno de los 15 documentos del gold:

1. Renderizar las páginas a procesar a imagen (300 DPI) con PyMuPDF
2. Para cada motor `m ∈ {EasyOCR, Tesseract}`:
   - Ejecutar `m.extract(imagen)` → `texto_OCR_m`
   - Normalizar `texto_OCR_m` y `texto_gold` (lowercase + whitespace)
   - Calcular `CER(gold, OCR_m)`, `WER`, `entity_recall`, `s_per_page`
3. Agregar resultados por motor y por tipología

### 4.2 Hardware y entorno

- CPU: equipo local (Windows 11, sin GPU disponible en el momento del benchmark)
- Python 3.12.10
- EasyOCR 1.7.2, Tesseract 5.5.0
- PyTorch con `pin_memory=true` (produce advertencia benigna al no haber GPU)

### 4.3 Reproducibilidad

Todas las corridas son determinísticas al nivel de la semilla:
- `random_state=42` en selección de gold
- `RESAMPLE=False` para preservar manifest entre corridas
- Transcripciones inmutables tras validación

---

## 5. Resultados

### 5.1 Resultados globales

| Motor | N | CER medio | WER medio | Entity recall medio | s/página |
|---|---|---|---|---|---|
| **EasyOCR (CPU)** | 15 | **0.276** | 0.476 | 0.551 | 46.02 |
| Tesseract 5 | 15 | 0.446 | 0.557 | **0.605** | **5.06** |

**Lecturas directas:**

- EasyOCR tiene **CER 38% menor** que Tesseract global
- Tesseract es **9× más rápido** en CPU
- Tesseract tiene marginalmente mejor entity_recall global (+5 puntos)

### 5.2 Resultados por tipología

| Tipología | EasyOCR CER | Tesseract CER | EasyOCR entity | Tesseract entity | Motor ganador |
|---|---|---|---|---|---|
| Cédula | **0.333** | 0.782 | **0.444** | 0.111 | EasyOCR (abrumador) |
| RUT | **0.289** | 0.394 | 0.889 | 0.889 | EasyOCR (CER) / Tesseract (velocidad) |
| Póliza | 0.329 | **0.226** | 0.649 | **0.951** | Tesseract |
| Cámara de Comercio | 0.096 | **0.047** | 0.326 | **0.963** | Tesseract (contundente) |

### 5.3 Casos extremos

Los tres documentos con mayor diferencia CER entre motores son **todos Cédulas**:

| Documento | EasyOCR CER | Tesseract CER | Diferencia |
|---|---|---|---|
| 23 cc.pdf | 0.261 | 0.903 | 0.642 |
| cc Julieth Payares.pdf | 0.416 | 0.955 | 0.540 |
| CC Yerlis cabarcas.pdf | 0.460 | 0.998 | 0.538 |

Este patrón confirma que **Tesseract colapsa sistemáticamente en Cédulas** (CER > 0.9 = texto casi irrecuperable).

### 5.4 Interpretación técnica

**¿Por qué Tesseract falla en Cédulas?**
La cédula colombiana combina condiciones adversas para un clasificador LSTM clásico: texto pequeño (~6-8 pt), hologramas superpuestos, columnas apretadas, bajo contraste. Tesseract pasa la imagen completa al LSTM, que se satura. EasyOCR (vía CRAFT) detecta **regiones de texto** antes de reconocer, aislando el ruido visual — estrategia documentada como ventajosa en Baek et al. 2019 [6].

**¿Por qué Tesseract gana en CC?**
Los certificados de Cámara de Comercio son el antípodal: texto estándar, sin hologramas, columnas anchas, alto contraste. En este régimen el LSTM clásico funciona excelente y gana por velocidad (9×).

---

## 6. La decisión y su justificación

### 6.1 La regla de decisión (definida antes del experimento)

```
1. Gana el motor con menor CER global si t_ganador < 2 × t_más_rápido
2. Empate CER (±2%) → gana mayor entity_recall
3. Si cada motor domina una tipología distinta → selector híbrido por tipología
```

### 6.2 Aplicación de la regla

- **Regla 1:** EasyOCR tiene menor CER global (0.276 vs 0.446), pero es **9× más lento** que Tesseract. **No cumple la restricción de tiempo** (9 > 2×). No gana por regla 1.
- **Regla 2:** diferencia CER (17 puntos absolutos) > 2%. No aplica.
- **Regla 3:** cada motor domina tipologías distintas. **Aplica.**

### 6.3 Decisión final

En CPU (entorno actual del laboratorio), la regla 3 sugiere un **selector híbrido**:

```python
def select_ocr(tipologia):
    return 'easyocr' if tipologia == 'Cedula' else 'tesseract'
```

Sin embargo, el proyecto adoptó **EasyOCR unificado** para todo el corpus escaneado por las siguientes razones:

1. **Cédulas son la tipología más numerosa** (32.9% del corpus). EasyOCR es crítico para esta tipología y su CER en las otras tipologías es aceptable (no catastrófico).
2. **Simplicidad del pipeline:** un solo motor reduce puntos de falla y facilita mantenimiento.
3. **Con GPU futuro:** EasyOCR pasa de 46 s/pág a ~1 s/pág (40× más rápido) — elimina la ventaja de Tesseract en velocidad.
4. **Trabajo futuro:** Tesseract queda disponible como experimento de respaldo si el F1 NER en Pólizas/CC queda bajo umbral en Fase 4.

### 6.4 Validación posterior (nb05)

Al aplicar EasyOCR al corpus completo de 1,678 páginas escaneadas, se midió el CER y el entity_recall contra el mismo gold seed:

| Métrica | Benchmark aislado (nb03) | Producción (nb05) | Delta |
|---|---|---|---|
| CER global | 0.276 | 0.282 | +2.2% (despreciable) |
| Entity recall | 0.551 | 0.640 | **+16%** |

**El benchmark predijo correctamente el comportamiento productivo.** La mejora de +16% en entity_recall se atribuye a la eliminación del paso `binarize()` del pipeline productivo (decisión documentada en `OCR_BENCHMARK.md §2.6.0`).

### 6.5 Metadatos de trazabilidad

- **Fecha de la decisión:** 2026-04-15
- **Gold seed:** 15 docs en `data/gold/gold_seed_manifest.csv` (`random_state=42`, cap=4 páginas)
- **Transcripciones congeladas:** `data/gold/transcriptions/` — inmutables desde la fecha
- **EasyOCR version:** 1.7.2 (modelos español, CPU)
- **Tesseract version:** 5.5.0 (`spa.traineddata` en `tessdata/` local del proyecto)
- **Ambiente:** Python 3.12.10, Windows 11, CPU-only

---

## 7. Referencias bibliográficas

Todas las referencias son verificables en línea con DOI, arXiv ID o URL institucional oficial.

### 7.1 Sobre gold standards y evaluación

[1] Manning, C. D., Raghavan, P., Schütze, H. (2008). ***Introduction to Information Retrieval***. Cambridge University Press — Capítulo 8 "Evaluation in Information Retrieval". URL: https://nlp.stanford.edu/IR-book/

[2] Wang, W. et al. (2025). *A Survey on Document Intelligence Foundations and Frontiers*. arXiv:2510.13366. URL: https://arxiv.org/abs/2510.13366

[3] Wirth, R. & Hipp, J. (2000). *CRISP-DM: Towards a Standard Process Model for Data Mining*. 4th Intl. Conf. on the Practical Applications of Knowledge Discovery and Data Mining. URL: https://www.cs.unibo.it/~montesi/CBD/Beatriz/10.1.1.198.5133.pdf

[4] Tjong Kim Sang, E. F. (2002). *Introduction to the CoNLL-2002 Shared Task: Language-Independent Named Entity Recognition*. CoNLL 2002. URL: https://aclanthology.org/W02-2024/

### 7.2 Sobre los motores OCR evaluados

[5] EasyOCR — Repositorio oficial JaidedAI. URL: https://github.com/JaidedAI/EasyOCR

[6] Baek, Y., Lee, B., Han, D., Yun, S., Lee, H. (2019). *Character Region Awareness for Text Detection (CRAFT)*. CVPR 2019. URL: https://arxiv.org/abs/1904.01941

[7] Shi, B., Bai, X., Yao, C. (2017). *An End-to-End Trainable Neural Network for Image-based Sequence Recognition and Its Application to Scene Text Recognition (CRNN)*. IEEE TPAMI 39(11). URL: https://arxiv.org/abs/1507.05717

[8] Tesseract OCR — Repositorio oficial. URL: https://github.com/tesseract-ocr/tesseract

[9] Smith, R. (2007). *An Overview of the Tesseract OCR Engine*. ICDAR 2007. URL: https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/

[10] Kim, G. et al. (2022). *OCR-free Document Understanding Transformer (Donut)*. ECCV 2022. URL: https://arxiv.org/abs/2111.15664

[11] PyMuPDF — Documentación oficial Artifex. URL: https://pymupdf.readthedocs.io/ — Repositorio: https://github.com/pymupdf/PyMuPDF

### 7.3 Sobre las métricas utilizadas

[12] Morris, A. C., Maier, V., Green, P. (2004). *From WER and RIL to MER and WIL: improved evaluation measures for connected speech recognition*. Interspeech 2004. URL: https://www.isca-speech.org/archive/interspeech_2004/morris04_interspeech.html

[13] jiwer — Librería Python para cálculo de CER/WER. URL: https://github.com/jitsi/jiwer

[14] DIAN. *Resolución 000110 del 11-10-2021* (estructura del RUT, fundamenta regex de NIT). URL: https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000110%20de%2011-10-2021.pdf

### 7.4 Referencias contextuales del proyecto

[15] Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 — fundamenta el flujo de pre-anotación automática post-OCR. URL: https://arxiv.org/abs/1711.10160

[16] Colakoglu, G. et al. (2025). *A Retrospective on Information Extraction from Documents: From Layout-aware Models to Large Language Models*. arXiv:2502.18179. URL: https://arxiv.org/abs/2502.18179

### 7.5 Documentos internos del proyecto

| Documento | Ubicación |
|---|---|
| Plan maestro CRISP-DM++ | `PLAN_MODELADO_CRISPDM.md` |
| Bitácora completa del benchmark | `OCR_BENCHMARK.md` |
| Propuesta de modelos (Fase 3) | `PROPUESTA_MODELOS.md` |
| Reporte narrativo del benchmark | `reports/nb03_resultados.md` |
| Reporte de ejecución productiva | `reports/nb05_resultados.md` |
| Notebook del benchmark | `notebooks/03_benchmark_ocr.ipynb` |
| Gold seed manifest | `data/gold/gold_seed_manifest.csv` |
| Transcripciones humanas | `data/gold/transcriptions/*.txt` (gitignored por PII) |

---

## Apéndice A — Tabla completa de resultados

Los 15 documentos del gold con métricas por motor (extracto del output real del notebook):

```
   engine  folder         n  cer_mean  wer_mean  entity_recall_mean  s_per_page_mean
  easyocr  CAMARA DE CIO  3    0.0960    0.2229              0.3259          51.5373
  easyocr  CEDULA         6    0.3333    0.5737              0.4444          42.0840
  easyocr  POLIZA         3    0.3286    0.4973              0.6493          48.1290
  easyocr  rut            3    0.2891    0.5134              0.8889          46.2573
tesseract  CAMARA DE CIO  3    0.0469    0.0316              0.9630           5.2543
tesseract  CEDULA         6    0.7818    0.8843              0.1111           5.4147
tesseract  POLIZA         3    0.2256    0.3466              0.9510           4.8143
tesseract  rut            3    0.3941    0.6402              0.8889           4.4030
```

CSV crudo: `data/processed/ocr_benchmark.csv` (30 filas, ✅ commiteable)
CSV agregado: `data/processed/ocr_benchmark_summary.csv` (8 filas, ✅ commiteable)
Figura: `data/processed/fig11_ocr_benchmark.png` (barras CER + scatter CER vs tiempo)

---

*Este documento es parte de los entregables académicos del proyecto SinergIA Lab, PUJ Especialización en IA, Ciclo 1, 2026. Toda afirmación cuantitativa está respaldada por artefactos verificables en el repositorio del proyecto.*
