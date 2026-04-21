# Capítulo 1 — El diagnóstico: quiénes son estos 1,014 documentos

**Notebook:** [01_analisis_descriptivo_secop.ipynb](../notebooks/01_analisis_descriptivo_secop.ipynb)
**Fecha de ejecución:** 2026-04-08
**Fase CRISP-DM++:** 1 — Comprensión de los Datos
**Artefactos:** `data/processed/quality_report_completo.csv` · 10 figuras (`fig01..fig10.png`) · `fase1_decisiones.json`

---

## 1. El contexto — ¿por qué empezar por aquí?

Antes de construir pipeline alguno, había que responder una pregunta básica: **¿qué tipo de corpus tenemos?** Un sistema IDP (Intelligent Document Processing) que trate 1,014 documentos del SECOP como objetos homogéneos está condenado a fallar. La metodología CRISP-DM (Wirth & Hipp, 2000 [1]) es explícita: la fase de comprensión de datos define cuál será el sistema.

La pregunta práctica del proyecto:

> *¿Hay variabilidad estructural, de calidad visual o de longitud textual que exija estrategias diferenciadas por tipología?*

Si la respuesta es "sí, mucha", entonces el diseño del sistema debe ser **adaptativo**, no monolítico.

## 2. La hipótesis

Planteamos la hipótesis siguiente, informada por el survey de Document AI de Wang et al. (2025) [2]:

> Los cuatro tipos documentales del corpus (Cédula, RUT, Póliza, Cámara de Comercio) tienen distribuciones estadísticamente distintas en (a) proporción escaneada vs digital, (b) densidad textual, (c) longitud y (d) calidad visual. Por tanto, un pipeline único es inadecuado.

## 3. El método

Sobre los 1,014 PDFs + 9 imágenes directas (.jpg/.jpeg) del corpus SECOP:

1. **Inventario por categoría** con deduplicación MinHash
2. **Extracción de metadata:** tamaño, MD5, número de páginas (via PyMuPDF)
3. **Calidad visual:** `blur_score` (varianza del Laplaciano), `contrast`, `brightness` sobre página 1
4. **Densidad textual:** `char_count` via PyMuPDF (sin OCR). Si `char_count < 100` → escaneado heurístico
5. **Complejidad:** índices Flesch y Szigriszt-Pazos [3] para legibilidad en español
6. **Estimación de tokens BPE** con factor de corrección empírico x1.25 (validado contra Llama 3 tokenizer)
7. **Detección de portadas:** heurística `lexicon < 50 AND blocks < 5`

## 4. Los resultados — los números del corpus

### 4.1 Inventario confirmado (prints reales del reporte)

```
Total docs: 1014
Por categoria:
  Cédula                334    (32.9%)
  RUT                   235    (23.2%)
  Póliza                219    (21.6%)
  Cámara de Comercio    212    (20.9%)
  Otros                  14     (1.4%)

Por extensión:
  .pdf     1005
  .jpeg       5
  .jpg        4
```

### 4.2 Calidad visual — 98.4% aptos

```
quality_label:
  APTO                         998   (98.4%)
  REQUIERE_PREPROCESAMIENTO      9    (0.9%)
  ERROR                          4    (0.4%)
  DESCARTADO                     3    (0.3%)
```

**Hallazgo:** la mayoría del corpus es legible en términos visuales — el cuello de botella no es calidad de captura, es **formato** (digital vs escaneado).

### 4.3 Distribución escaneado vs digital (heurística `char_count < 100`)

```
                        digital  escaneado
Cédula                     15        319    (93.4% escaneada)
RUT                       208         27    (11.5% escaneada)
Póliza                    139         80    (36.5% escaneada)
Cámara de Comercio        192         20     (9.4% escaneada)
Otros                       9          5
```

**Este es el hallazgo estructural más importante del corpus.**

### 4.4 Complejidad textual por tipología (índice Flesch mediana)

| Tipología | Flesch | Palabras/doc (mediana) | Tokens BPE x1.25 | Estrategia chunking |
|---|---|---|---|---|
| Cédula | 58.0 | 0 (escaneada) | 0 | `sin_chunking` |
| RUT | **84.5** | 1,117 | **1,861** | `sliding_window_30pct` |
| Póliza | 61.0 | 484 | 806 | `sliding_window_30pct` |
| Cámara de Comercio | 51.2 | 1,063 | 1,772 | `sliding_window_30pct` |
| Otros | 49.3 | 278 | 370 | `sin_chunking` |

Valores Flesch: mayor = más fácil de leer. RUT tiene el valor más alto porque el formulario DIAN es léxicamente simple (palabras cortas). CC tiene el valor más bajo porque contiene lenguaje jurídico con muchas palabras largas.

### 4.5 Distribuciones físicas

```
n_pages stats:
  mean    14.0
  std    109.4    ← alta varianza: algunos docs son excepcionalmente largos
  min      0.0    ← 4 corruptos
  25%      1.0    ← mitad del corpus tiene ≤4 páginas
  50%      4.0
  75%      9.0
  max   3119.0    ← outlier extremo

blur_score stats:
  mean   5,764
  std    3,826
  min       13.8   ← documentos muy borrosos
  50%    5,253
  max   18,449

char_count stats:
  mean    3,078
  min         0    ← escaneados, sin texto digital
  50%     2,000
  max    13,745
```

## 5. La lectura crítica

### 5.1 Las 4 tipologías viven en mundos distintos

- **Cédulas** son 93% imágenes → el sistema **depende de OCR** para ellas. Sin OCR funcional en Cédulas, 32.9% del corpus es inútil para NER.
- **RUT** son 88% digital → texto nativo disponible. Se puede atacar con Labeling Functions regex (weak supervision a la Ratner 2018 [4]).
- **Pólizas** son 63% digital → mezclado, pero manejable sin OCR masivo.
- **CC** son 91% digital → caso ideal. Documentos largos con texto estructurado.

### 5.2 Implicación inmediata

La decisión arquitectural nace aquí: **no hay pipeline único**. Hay 4 flujos que se cruzan en los puntos donde coinciden:

```
Cédula   ──► OCR (EasyOCR) ──► NER sobre texto ruidoso
RUT      ──► PyMuPDF ──► LFs regex ──► NER sobre texto limpio
Póliza   ──► OCR + PyMuPDF mix ──► NER manual por layout variable
CC       ──► PyMuPDF ──► NER layout-aware (§Propuesta Modelos N-3)
```

### 5.3 El límite del chunking de Llama 3

RUT y CC superan los 1,800 tokens BPE en mediana (1,861 y 1,772 respectivamente). Llama 3 tiene contexto 2,048 en la config del proyecto — el límite de 1,800 tokens deja margen del 12% para prompt + output. **Chunking obligatorio** para estas dos tipologías.

## 6. Anomalías y hallazgos secundarios

- **3,119 páginas en un solo documento** (max n_pages) → outlier extremo que requiere verificación manual. Probablemente un expediente agregado, no un certificado individual.
- **4 docs con `n_pages=0`** (corruptos) y **3 `DESCARTADO`** → se excluyen de Fase 2. 1,007 docs efectivos.
- **Mojibake detectado en nombres:** `CÃÂ©dula`, `CÃÂ¡mara de Comercio` en `category`. Artefacto de Windows → CSV UTF-8. Se resuelve con índice MD5 para evitar colisiones.
- **Vocabulario CIIU** contamina embeddings de RUT. El formulario DIAN imprime la lista completa de clasificaciones (Resolución DIAN 000110/2021 [5]) → ~300 términos ajenos al contenido real del RUT. Requiere filtrado específico.

## 7. ¿Qué sigue? — Cap. 2

Con el diagnóstico en mano, la pregunta que abre el siguiente capítulo es:

> *¿Cómo se implementan 4 flujos distintos sin que el código se vuelva inmanejable?*

El Notebook 02 responde con **12 funciones reutilizables** agrupadas en un módulo `pipeline.py` y un dispatcher `chunk_document()` que decide la estrategia según la tipología. Se validan las funciones sobre un piloto de 5 docs por tipo y se define la estructura de las Labeling Functions regex para RUT.

→ [nb02_resultados.md](nb02_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/quality_report_completo.csv` | 1,014 filas × 15 columnas con metadata por doc | ❌ PII |
| `data/processed/fase1_decisiones.json` | Decisiones de la fase (chunking, BPE correction, etc.) | ✅ |
| `data/processed/fig01..fig10.png` | Figuras EDA (inventario, calidad, textometría) | ✅ |
| `data/processed/near_duplicates.json` | Detección MinHash de duplicados | ✅ |
| `data/processed/vocabulario_dominio.json` | Vocabulario por tipología | ✅ |
| `data/processed/portadas_detectadas.json` | Outputs del detector de portadas | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | Wirth, R. & Hipp, J. (2000). *CRISP-DM: Towards a Standard Process Model for Data Mining*. 4th Intl. Conf. on the Practical Applications of Knowledge Discovery and Data Mining | https://www.cs.unibo.it/~montesi/CBD/Beatriz/10.1.1.198.5133.pdf |
| [2] | Wang, W. et al. (2025). *A Survey on Document Intelligence Foundations and Frontiers*. arXiv | https://arxiv.org/abs/2510.13366 |
| [3] | Szigriszt-Pazos, F. (1993). *Sistemas predictivos de legibilidad del mensaje escrito: fórmula de perspicuidad*. Universidad Complutense (tesis doctoral) | https://eprints.ucm.es/id/eprint/1849/ |
| [4] | Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 | https://arxiv.org/abs/1711.10160 |
| [5] | DIAN. *Resolución 000110 del 11-10-2021* (estructura del RUT) | https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000110%20de%2011-10-2021.pdf |
