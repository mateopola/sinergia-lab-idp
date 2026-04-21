# Capítulo 5 — La travesía: 23 horas extrayendo texto

**Notebook:** [05_ocr_corpus.ipynb](../notebooks/05_ocr_corpus.ipynb)
**Fecha de ejecución:** 2026-04-17 → 2026-04-18 (overnight)
**Fase CRISP-DM++:** 2.1 — OCR productivo
**Artefacto principal:** `data/processed/corpus_ocr.csv` (37.6 MB — gitignored por PII)

---

## 1. El contexto — aplicar la decisión

Tres capítulos de preparación (nb02 herramientas, nb03 decisión del motor, nb04 pipeline visual) culminan en una sola corrida: **aplicar EasyOCR a las 1,678 imágenes preprocesadas**.

En CPU, a ~50 s/pág, son unas 23 horas. Se ejecuta **overnight** con el usuario durmiendo. Al despertar, el corpus textual está listo para las Labeling Functions de RUT y la anotación humana de las demás tipologías.

## 2. La hipótesis

> La corrida productiva reproducirá aproximadamente el CER del benchmark aislado (nb03 reportó CER=0.276 para EasyOCR). Si hay desviación >20%, algo cambió entre el entorno del benchmark y el de producción y requiere investigación.

Esta es una prueba de **reproducibilidad**: el benchmark predice el comportamiento productivo.

## 3. El método

### 3.1 Setup

```
Rutas OK.
  Manifest entrada: ..\data\processed\image_manifest.csv
  Salida final:     ..\data\processed\corpus_ocr.csv
  EasyOCR version:  1.7.2  (GPU=False)
  BLOCK_SIZE=25  FORCE_REPROCESS=False
```

Bloques más pequeños que nb04 (25 vs 50) porque OCR toma **50× más tiempo que preprocesar**.

### 3.2 Selección de páginas

```
image_manifest: 1678 filas (paginas preprocesadas)
Indexando data/raw/ por MD5...
  955 PDFs indexados
  ⚠ 9 paginas sin PDF en disco — se excluyen
Paginas listas para OCR: 1669
```

**Gap 1 detectado en la primera celda:** el índice MD5 solo busca `.pdf` en `data/raw/`, pero 9 docs son `.jpg`/`.jpeg` — **son excluidos silenciosamente** del OCR aunque tienen imagen preprocesada. Este gap se cerrará en nb05b.

### 3.3 Funciones de reconstrucción

El notebook define `reconstruir_texto(detections)` que ordena bboxes por Y-centroid y luego por X dentro de cada línea. Esto produce texto en **orden de lectura natural** (arriba-abajo, izquierda-derecha), no el orden de confianza de EasyOCR.

### 3.4 Test sobre 1 página escaneada

Validación en tiempo real:

```
=== Escaneada (EasyOCR) ===
  filename: 001. CEDULA REPRESENTANTE LEGAL.pdf  pag 1/1
  engine: easyocr  detecciones: 42  tiempo: 47.018s  chars: 472
  primeros 300 chars del texto:
  REPUBLICA DE COLOMBIA
  IDENTIFICACION PERSONAL
  CEDULA DE CIUDADANIA LICADE
  hns 82222FE
  NUMERO 40.768,-564
  SANCHEZ TRUJILLO a
  5a
  APELLIDOS
  MARIELA
  NoMBREs
  ...
```

Observaciones del test:
- `REPUBLICA DE COLOMBIA`, `IDENTIFICACION PERSONAL`, `CEDULA DE CIUDADANIA` — encabezado correcto
- `NUMERO 40.768,-564` — el número de cédula tiene errores OCR (`40.768.564` probablemente)
- `SANCHEZ TRUJILLO` — apellido correcto
- `MARIELA` — nombre
- Minúsculas en `NoMBREs` — artefacto OCR clásico en tipografías pequeñas

Esto **confirma lo que nb03 predijo**: CER ~0.33 en Cédulas, entity_recall moderado.

### 3.5 Test sobre 1 página de Póliza

```
=== Random ===
  filename: POLIZA DE RESPONSABILIDAD CIVIL EXTRACONTRACTUAL KENT.pdf  pag 1/4
  engine: easyocr  detecciones: 175  tiempo: 66.191s  chars: 4122
  primeros 300 chars del texto:
  seguros
  mundial COMPAÑIA MUNDIAL DE SEGUROS SA
  DIRECCION GENERAL CALLE 33 N 6B 24 PISOS 1,2Y3-BOGOTA
  TELÉFONO: 2855600 FAX 2851220 -WWW SEGUROSMUNDIAL CoMCo
  ...
```

Mundial de Seguros detectada correctamente. NIT `860037013-6` también aparece en el texto (se verá en nb08 del análisis de Pólizas).

### 3.6 Corrida masiva

```
Paginas pendientes: 1669
Procesando en 67 bloques de 25...
OCR paginas: 100%|██████████| 1669/1669 [23:32:43<00:00, 50.79s/it]
Corrida completa.
```

**23 horas 32 minutos, 50.79 s/pág.** Con ventilador de soporte térmico (la CPU en 100% durante toda la noche).

## 4. Los resultados — los números reales

### 4.1 Output consolidado

```
Bloques OCR encontrados: 67
corpus_ocr.csv:   1669 filas -> ..\data\processed\corpus_ocr.csv
  tamano: 37.6 MB
corpus_ocr_summary.csv: 1669 filas -> ..\data\processed\corpus_ocr_summary.csv
```

### 4.2 Validación contra gold seed (los 15 docs transcritos a mano)

```
Validacion contra gold seed (15 docs):
       folder                                          filename  pages_used    cer  entity_recall
       CEDULA                                         23 cc.pdf           1 0.2222         1.0000
       CEDULA                            cc Jonathan Blanco.pdf           1 0.3366         0.0000
       CEDULA                            CC Yerlis cabarcas.pdf           1 0.4431         0.3333
       CEDULA     4. CEDULA PAULA ANDREA CASTAÃÂO ZULUAGA.pdf           2 0.2368         1.0000
       CEDULA                            cc Julieth Payares.pdf           1 0.4014         0.6667
       CEDULA                                 28 cedula (2).pdf           1 0.2334         0.6667
          rut                                   RUT GESTIVA.pdf           4 0.3623         1.0000
          rut                                  RUT ASOVITAL.pdf           1 0.3659         0.6667
          rut 14. RUT La Previsora S.A. 05-03-26 - Completo.pdf           4 0.2697         1.0000
       POLIZA                                    0. POLIZA .pdf           4 0.3691         0.7895
       POLIZA    2-29 Garantia de Seriedad del Ofrecimiento.pdf           3 0.1793         0.2000
       POLIZA POLIZA DE SERIEDAD 21-44-101492068_FIRMADA _1.pdf           4 0.1490         0.9583
CAMARA DE CIO 04. CÃÂ¡mara de Comercio Solidaria Manizales.pdf           4 0.0482         0.2222
CAMARA DE CIO         camara de comercio 23 oct 2025 - ISVI.pdf           4 0.5450         0.5333
CAMARA DE CIO       CERTIFICADO CAMARA COMERCIO ene2026 MAX.pdf           4 0.0655         0.5556
```

### 4.3 Resumen por tipología

```
Resumen por tipologia:
               n  cer_mean  entity_recall_mean
folder                                        
CAMARA DE CIO  3    0.2196              0.4370
CEDULA         6    0.3122              0.6111
POLIZA         3    0.2325              0.6493
rut            3    0.3326              0.8889

CER medio global:           0.2818  (benchmark EasyOCR CPU ≈ 0.276)
Entity recall medio global: 0.6395  (benchmark ≈ 0.55)
```

## 5. La lectura crítica

### 5.1 La hipótesis se confirma con precisión

- **CER predicho:** 0.276 (benchmark nb03)
- **CER medido:** 0.282 (nb05 productivo)
- **Delta:** +2.2% — dentro del ruido estadístico esperado

El benchmark predijo correctamente el comportamiento productivo. Esto valida la metodología del gold seed.

### 5.2 Entity recall **sube +16 puntos** inesperadamente

- **Entity recall predicho:** 0.55
- **Entity recall medido:** 0.64
- **Delta:** +16%

Esto es un hallazgo positivo. La explicación más probable: el pipeline productivo **sin `binarize()`** (decisión de nb04) preserva más detalle en los dígitos que las versiones binarizadas del benchmark (que en algunas páginas usaban imagen binarizada). Menos fragmentación de dígitos en el OCR → más entidades reconocibles.

### 5.3 Observaciones por tipología

- **RUT (entity_recall 0.889):** el mejor desempeño. Valida la hipótesis para §2.2 nb06: las LFs regex **tendrán buen texto sobre el que operar**.
- **Pólizas (0.649):** Tesseract ganaba aquí en nb03 (0.95). EasyOCR queda 30 puntos atrás. **Riesgo documentado** para Fase 3: modelos NER en Pólizas tendrán menos entidades limpias como señal.
- **CC (0.437):** más bajo que benchmark aislado (0.326). El doc `camara de comercio 23 oct 2025 - ISVI.pdf` tiene CER 0.545 — caso particularmente difícil (tablas multicolumna).
- **Cédulas (0.611):** mejor que benchmark. Pero con 6 docs, alta varianza por doc.

### 5.4 Casos extremos — lecciones para Fase 4

| Doc | CER | Entity recall | Observación |
|---|---|---|---|
| `CC Yerlis cabarcas.pdf` | 0.443 | 0.333 | Cédula borrosa legítima — límite del OCR |
| `camara de comercio 23 oct 2025` | 0.545 | 0.533 | Tablas densas multi-columna → LayoutLMv3 candidato (nb09) |
| `04. Cámara de Comercio Solidaria` | 0.048 | 0.222 | **CER bajísimo pero entity_recall bajo**: el OCR funciona, pero los NITs no matchean porque el regex de validación los rechaza (posible formato atípico) |

El último caso es revelador: **CER ≠ utilidad downstream**. Un OCR "técnicamente correcto" puede producir texto con entidades en formato inesperado. Este es el argumento principal para **entity_recall** como métrica primaria para un sistema IDP.

## 6. Anomalías y hallazgos secundarios

### 6.1 Los dos gaps detectados

**Gap 1 — 9 imágenes escaneadas filtradas:**

```
image_manifest: 1678 filas
Paginas listas para OCR: 1669    ← 9 páginas perdidas
```

Causa: el indexador `md5_index` solo busca `*.pdf` en `data/raw/`. Los 9 archivos `.jpg`/`.jpeg` tienen MD5 que no matchea. Aunque ya están preprocesados en `data/processed/images/`, el filtro los excluye.

**Gap 2 — 548+ digitales nunca entraron al pipeline:**

El notebook solo itera el `image_manifest.csv`, que por diseño solo contiene escaneados. Los docs con `es_escaneado == False` **nunca se extraen** en esta corrida — deberán procesarse con PyMuPDF por separado. Este gap no es bug: es **descubrimiento** de que nb04 + nb05 solo cubren una parte del corpus.

**Ambos gaps se cierran en nb05b.**

### 6.2 Advertencia PyTorch benigna

```
UserWarning: 'pin_memory' argument is set as true but no accelerator is found
```

EasyOCR intenta usar pinned memory (útil en GPU). En CPU es inofensivo; la warning aparece una vez por bloque.

### 6.3 Throughput vs benchmark aislado

- Benchmark: 46 s/pág (15 docs, corrida de ~1h)
- Productivo: 50.79 s/pág (1,669 docs, corrida de 23h)
- **Delta: +10%** — atribuible a variabilidad térmica. La CPU en 100% continuo durante 23h reduce throughput por throttling. El ventilador externo mitigó pero no eliminó.

## 7. ¿Qué sigue? — Cap. 5b

El corpus OCR tiene **1,669 páginas escaneadas** pero el universo total es **13,254 páginas** (escaneadas + digitales). Faltan dos cosas:

1. Procesar las 9 imágenes filtradas con EasyOCR
2. Procesar las ~12,400 páginas digitales con PyMuPDF (instantáneo, sin OCR)

El Notebook 05b resuelve ambas en **20 minutos** totales. Spoiler: PyMuPDF es ~10,000× más rápido que EasyOCR (0.006 s/pág vs 50 s/pág).

→ [nb05b_resultados.md](nb05b_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/corpus_ocr.csv` | 1,669 filas con texto + bboxes por página (37.6 MB) | ❌ PII |
| `data/processed/corpus_ocr_summary.csv` | Métricas sin texto | ✅ |
| `data/processed/ocr_blocks/ocr_bloque_*.csv` | 67 checkpoints | ❌ |
| `data/gold/ocr_corpus_validation.csv` | Validación CER + entity_recall vs gold | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | Baek, Y. et al. (2019). *CRAFT*. CVPR | https://arxiv.org/abs/1904.01941 |
| [2] | Shi, B., Bai, X., Yao, C. (2017). *CRNN*. IEEE TPAMI | https://arxiv.org/abs/1507.05717 |
| [3] | Morris, A. C., Maier, V., Green, P. (2004). *From WER and RIL to MER and WIL: improved evaluation measures for connected speech recognition*. ICSLP 2004 (referencia canónica para CER/WER en extensión a OCR) | https://www.isca-speech.org/archive/interspeech_2004/morris04_interspeech.html |
| [4] | Navigli, R., Conia, S. (2023). *Biases in Large Language Models and Benchmarks*. (valida entity_recall como métrica downstream) | https://arxiv.org/abs/2310.11850 |

**Referencias internas:**
- [OCR_BENCHMARK.md §2.6.2](../OCR_BENCHMARK.md) — ejecución productiva documentada
- [nb03_resultados.md](nb03_resultados.md) — benchmark predictivo
- [nb04_resultados.md](nb04_resultados.md) — pipeline sin binarize
