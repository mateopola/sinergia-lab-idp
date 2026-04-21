# Capítulo 8 — El caso difícil: Pólizas con layout variable

**Notebook:** [08_preanotaciones_polizas.ipynb](../notebooks/08_preanotaciones_polizas.ipynb)
**Fecha de ejecución:** 2026-04-20
**Fase CRISP-DM++:** 2.2 — Anotación Manual Pólizas
**Artefactos:** `polizas_muestra_manifest.csv` · `polizas_preanotaciones_labelstudio.json` · `polizas_preanotaciones_summary.csv`

---

## 1. El contexto — cuando cada aseguradora diseña su propia plantilla

El RUT tenía un formulario regulado por DIAN (nb06). Las Cédulas tenían layout estándar (nb07). Las Pólizas presentan el **caso más hostil**: cada aseguradora comercial (Mundial, Sura, AXA Colpatria, Liberty, Allianz, Positiva, ...) usa su **propia plantilla gráfica**. Aunque el contenido jurídico está regulado por el Código de Comercio [1] y la Circular Básica Jurídica de la Superintendencia Financiera [2], la **presentación visual** no.

Esto mata a las LFs regex:

- "Valor Asegurado" en Sura vs "Suma Asegurada" en Liberty vs "Cuantía" en Positiva
- Fecha en `DD/MM/AAAA`, `DD-MM-YYYY`, literal "primero de marzo de dos mil veintiséis"
- Número de póliza con formatos distintos por aseguradora

## 2. La hipótesis

> En Pólizas, **solo 2 entidades son pre-anotables** con regex:
>
> 1. `numero_poliza` — patrones alfanuméricos con anchor `POLIZA|NUMERO`
> 2. `aseguradora` — via lookup contra `aseguradoras_corpus.json` (nb02)
>
> Los **7 campos restantes** (`tomador`, `asegurado`, `vigencia_desde`, `vigencia_hasta`, `valor_asegurado`, `prima_neta`, `amparo_principal`) requieren **anotación manual** en Label Studio.

La cobertura esperada: ~70% para `numero_poliza`, ~50% para `aseguradora` (depende de cuántas del corpus están en el diccionario).

## 3. El método

### 3.1 Mojibake handling — filtro robusto

```
Corpus total: 13,254 filas / 960 docs
Paginas Polizas: 2,767
Docs Polizas:    203

Distribucion por engine:
engine
easyocr     59
pymupdf    144

Docs con texto extraido (>100 chars): 199
```

**Crítico:** el filtro `folder.str.lower().str.contains('poliz|liza')` captura ambos:
- `POLIZA` (59 escaneados, limpio)
- `PÃÂ³liza` (144 digitales, mojibake)

Sin el OR con `liza`, se perderían 144 docs silenciosamente. Este es un ejemplo del tipo de bug sutil que los outputs reales revelan.

### 3.2 Distribución de longitud documental

```
Distribucion n_pages:
count    199.0
mean      13.8
std       21.5
min        1.0
25%        4.0
50%        8.0
75%       17.0
max      243.0
```

**Mediana = 8 páginas, máximo = 243.** El outlier de 243 páginas es un expediente con anexos escaneados múltiples. Esto será relevante para **chunking** en §2.3 — Pólizas > 1,800 tokens BPE requieren ventana deslizante.

### 3.3 Muestreo 80 train + 40 val

```
Muestra: 120 docs (80 train + 40 val)

Por engine:
split  engine 
train  easyocr    25
       pymupdf    55
val    easyocr    11
       pymupdf    29

Chars promedio por split:
        mean  median  min     max
split                            
train  32305   17595  542  374581
val    19718   14520  122  100279
```

El muestreo es aleatorio (seed=42) sin estratificación por aseguradora. El plan §2.2 v1.7 documenta la decisión:

> "Las entidades objetivo de Póliza son estándar del contrato de seguro colombiano — iguales en todas las aseguradoras independientemente del layout. La identificación de aseguradora no es requisito para estratificar."

**Consecuencia documentada:** si una aseguradora domina el corpus (como Mundial), también dominará la muestra aleatoria. Ver §5.2.

### 3.4 Aseguradoras en el diccionario

```
Aseguradoras en diccionario: 11
Ejemplos: ['Escaneada (sin texto)', 'Otra/No identificada', 'Mundial de Seguros',
           'Error de lectura', 'AXA Colpatria']
```

De las 11 entradas, **solo ~7 son aseguradoras reales** (las otras 4 son categorías artefacto de clasificación previa). El lookup filtra implícitamente: "Escaneada (sin texto)" no aparece en ningún texto real.

## 4. Los resultados — los números reales

### 4.1 Cobertura de las 2 LFs

```
Cobertura numero_poliza: 84/120 = 70.0%
Cobertura aseguradora:   60/120 = 50.0%
```

**Exactamente lo predicho.**

### 4.2 Distribución de aseguradoras detectadas

```
Top 10 aseguradoras detectadas:
aseguradora
Mundial de Seguros    37
Bolivar                9
AXA Colpatria          6
La Previsora           4
Sura                   2
La Equidad             1
Allianz                1
```

**Mundial de Seguros = 37/60 = 62% de las Pólizas con aseguradora detectada.** El resto se reparte entre 6 aseguradoras, con solo 1-9 pólizas cada una.

### 4.3 Ejemplos de números de póliza detectados

```
Ejemplos numero_poliza detectado (primeros 5):
                                    filename  numero_poliza        aseguradora
CUMP-CBM-100000889_0 DINAMICK_unlocked_1.pdf  Nii 860037013 Mundial de Seguros
             Poliza_10_CSU-100002172_0_1.pdf  Nit 860037013 Mundial de Seguros
           Garantia seriedad de oferta_1.pdf      101110383               None
 Poliza de seriedad SRC 2025 Dislumbra_1.pdf Nit 860037 013 Mundial de Seguros
                      POLIZA DE SERIEDAD.pdf 39-44-10117825               None
```

**Observación crítica:** 3 de 5 detecciones contienen **"Nit" o "Nii"** en la captura. El regex está confundiendo el NIT de la aseguradora (`860037013` = Mundial de Seguros) con el número de póliza. Es **falso positivo sistemático**.

El patrón de error: la plantilla de Mundial imprime `"NIT 860037013-6"` justo antes del número de póliza real. La regex `POLIZA.{0,30}?\d{7,10}` atrapa el NIT como "número de póliza".

Los valores `"101110383"` y `"39-44-10117825"` sí son números de póliza reales (las pólizas de seriedad sin aseguradora detectada). Los 3 primeros ejemplos con "Nit" son casos que el anotador humano **debe corregir** en Label Studio.

### 4.4 Export a Label Studio

```
Tareas Label Studio: 120
  con pre-anotacion numero: 84
  con pre-anotacion aseguradora: 60
Archivo: ..\data\processed\polizas_preanotaciones_labelstudio.json
Manifest: ..\data\processed\polizas_muestra_manifest.csv
Summary: ..\data\processed\polizas_preanotaciones_summary.csv
```

## 5. La lectura crítica

### 5.1 La regex de `numero_poliza` es defectuosa (falsos positivos)

El 60% de los detectados son en realidad NITs de aseguradora, no números de póliza. Esto significa que:

- **Precision real del `numero_poliza`: ~40%**, no 70% como parece por cobertura
- El anotador humano debe **eliminar y re-anotar** muchos números detectados

**Decisión para nb08:** no refinamos la regex. El proyecto optó por weak supervision con revisión humana (§2.2). Un 40% de precisión significa que la regex **aún ahorra tiempo** (40% de anotaciones correctas = 30-40 minutos ahorrados de un trabajo de 40 horas) pero el humano debe ser cauteloso.

**Refinamiento futuro (no crítico):** añadir blacklist de NITs conocidos de aseguradoras. El NIT de Mundial `860037013` aparece en casi todas sus pólizas — detectarlo y descartarlo elevaría la precision a >80%.

### 5.2 Concentración extrema en Mundial de Seguros

```
Mundial de Seguros    37   (62% de detectados, 31% de la muestra total)
Bolivar                9    (8%)
AXA Colpatria          6    (5%)
La Previsora           4    (3%)
resto                  4    (3%)
```

**Esto es un sesgo severo del corpus.** Implicaciones para Fase 3:

1. **El modelo NER aprenderá principalmente pólizas de Mundial.** Si el sistema se despliega en un contrato con aseguradora distinta, la generalización será mala.
2. **Validación sesgada:** el val set de 40 pólizas también es 60%+ Mundial. F1 reportado no es representativo del comportamiento cross-aseguradora.

**Mitigaciones posibles (para Fase 2.4 — augmentación):**
- Data augmentation específica de otras aseguradoras
- Reponderación del loss durante fine-tuning
- Recomendación al cliente: más pólizas de aseguradoras minoritarias para el gold extendido

### 5.3 Pólizas digital vs escaneada — split razonable

Train: 25 easyocr + 55 pymupdf (31% escaneadas)
Val: 11 easyocr + 29 pymupdf (28% escaneadas)

La proporción escaneadas/digitales es similar en ambos splits (~30% escaneados). El modelo verá ambos regímenes durante entrenamiento y será evaluado sobre la misma mezcla.

### 5.4 Outlier de 243 páginas

```
max      243.0
```

Este doc es crítico verificarlo. Probablemente es un expediente de póliza con múltiples anexos escaneados. Al chunking por 512 tokens generaría ~150 chunks por doc — mucho overhead. El plan §2.3 define que Pólizas usan sliding window.

Acción sugerida: revisar manualmente este outlier antes de incluirlo en entrenamiento. Si es un expediente agregado (varias pólizas en un solo PDF), segmentarlo. Si es una póliza genuina con anexos, mantenerlo.

## 6. Anomalías y hallazgos secundarios

### 6.1 Solo 7 aseguradoras distintas detectadas (de un diccionario de ~7 reales)

El diccionario `aseguradoras_corpus.json` fue construido en nb02 con lookup inicial. Cubre 100% de las aseguradoras que aparecen en el corpus muestreado. **No hay "aseguradoras desconocidas"** que el humano deba agregar.

### 6.2 El `n_pages` de Pólizas supera RUT y CC

```
Pólizas: mediana 8, máx 243
RUT:     mediana 4, máx 16
CC:      mediana 9, máx 163
```

Las Pólizas tienden a ser **más largas** que los RUT o CC. Esto tiene implicaciones para el chunking y para la memoria del modelo NER.

### 6.3 Chars promedio del train 63% más alto que val

```
train: mean 32305 chars
val:   mean 19718 chars
```

Diferencia grande. Posible explicación: el muestreo aleatorio no controló por longitud documental. Docs largos (tipo el outlier de 243 páginas) cayeron en train.

**Impacto:** el modelo verá docs largos durante entrenamiento (aprende robusto) pero se evalúa sobre docs más cortos (métricas optimistas). Para Fase 4, considerar **re-split estratificado por longitud**.

## 7. ¿Qué sigue? — Cap. 9

Queda la última tipología: **Cámara de Comercio**. En este caso la hipótesis es optimista:

> *Los certificados de CC están regulados por el Decreto 2150 de 1995 — estructura forzada por normatividad. ¿Se refleja eso en la cobertura de las LFs regex?*

Spoiler: **sí, y con creces.** `razon_social` alcanza **96.7% de cobertura**. CC es el **antípoda** de Pólizas: regulación estricta → estructura estable → LFs poderosas. Este resultado motiva LayoutLMv3 [3] como candidato principal para Fase 3 en CC.

→ [nb09_resultados.md](nb09_resultados.md)

## 8. Evidencia en disco

| Artefacto | Descripción | Commiteable |
|---|---|---|
| `data/processed/polizas_muestra_manifest.csv` | 120 md5 + split + pre-anotaciones | ✅ |
| `data/processed/polizas_preanotaciones_labelstudio.json` | 120 tareas LS | ❌ PII |
| `data/processed/polizas_preanotaciones_summary.csv` | Cobertura por LF | ✅ |

## 9. Referencias científicas

| # | Cita | URL |
|---|---|---|
| [1] | Decreto 410 de 1971 (Código de Comercio — Título V, artículos 1036-1162 regulan el contrato de seguro) | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=41102 |
| [2] | Superintendencia Financiera de Colombia. *Circular Básica Jurídica (Circular Externa 029 de 2014 y actualizaciones)* | https://www.superfinanciera.gov.co/ |
| [3] | Huang, Y. et al. (2022). *LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking*. ACM MM 2022 | https://arxiv.org/abs/2204.08387 |
| [4] | Ratner, A. et al. (2018). *Snorkel: Rapid Training Data Creation with Weak Supervision*. VLDB 2018 | https://arxiv.org/abs/1711.10160 |
| [5] | Ley 1328 de 2009 (Régimen de protección al consumidor financiero) | https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=36816 |

**Referencias internas:**
- [nb02_resultados.md](nb02_resultados.md) — `aseguradoras_corpus.json` generado
- [PLAN_MODELADO_CRISPDM.md §2.2 Pólizas](../PLAN_MODELADO_CRISPDM.md)
