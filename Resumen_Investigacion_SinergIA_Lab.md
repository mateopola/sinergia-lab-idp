# Informe Completo de Investigación
# Procesamiento Inteligente de Documentos Corporativos y Gubernamentales
# Proyecto SinergIA Lab — Pontificia Universidad Javeriana
### Especialización en Inteligencia Artificial | Ciclo 1 | Marzo 2026

---

## ÍNDICE

1. [Contextualización Estratégica y Alcance del Proyecto](#1-contextualización-estratégica-y-alcance-del-proyecto)
2. [Revisión de Antecedentes Científicos y Técnicos (Sección 2.3)](#2-revisión-de-antecedentes-científicos-y-técnicos)
3. [Revisión de Productos y Soluciones en el Mercado (Sección 2.4)](#3-revisión-de-productos-y-soluciones-en-el-mercado)
4. [Análisis Comparativo de Referentes (Sección 2.5)](#4-análisis-comparativo-de-referentes)
5. [Características Iniciales del Producto (Sección 2.6)](#5-características-iniciales-del-producto)
6. [Requerimientos Funcionales (Sección 2.7)](#6-requerimientos-funcionales-preliminares)
7. [Requerimientos No Funcionales (Sección 2.8)](#7-requerimientos-no-funcionales-preliminares)
8. [Aprendizajes y Moralejas (Sección 2.9)](#8-aprendizajes-recomendaciones-y-moralejas)
9. [Referencias Bibliográficas](#9-referencias-bibliográficas)
10. [URLs de Referencia Web](#10-urls-de-referencia-web-consultadas)

---

## 1. Contextualización Estratégica y Alcance del Proyecto

### 1.1 Problema Central y Premisa Estratégica

El presente informe de investigación aborda la estructuración conceptual, técnica y comercial del proyecto **SinergIA Lab**, una iniciativa de consultoría tecnológica enmarcada en el dominio de la Inteligencia Artificial aplicada. Este proyecto emerge como una respuesta directa a una de las fricciones operativas más persistentes y costosas en el entorno corporativo y gubernamental contemporáneo: la **alta dependencia de archivos físicos y repositorios de documentos digitales no estructurados**.

Bajo la premisa estratégica de transitar **"del papel a la inteligencia"**, SinergIA Lab se propone transformar la documentación estática en activos de información dinámicos, estructurados y de alto valor analítico.

La dependencia de formatos documentales no estructurados —imágenes escaneadas o PDFs sin capas de metadatos— genera:

- **Asimetrías severas** en el acceso a la información institucional
- **Mayor vulnerabilidad** ante pérdida, deterioro documental y fraude
- **Ralentización drástica** de flujos de trabajo orientados a auditoría, supervisión normativa y toma de decisiones estratégicas

### 1.2 Marco Metodológico

El diseño de la solución SinergIA Lab se estructura rigurosamente bajo tres marcos integrados:

- **CRISP-DM++** (Cross-Industry Standard Process for Data Mining): metodología de ciencia de datos adaptada con rigor empresarial
- **Scrum**: principios de desarrollo ágil por sprints para iteración rápida del MVP
- **Design Thinking**: herramientas de conceptualización centradas en el usuario, con énfasis en **mapas de empatía** para caracterizar a los actores involucrados (stakeholders)

Esta alineación metodológica garantiza que la solución tecnológica no sea un mero ejercicio académico, sino que responda de manera precisa a necesidades reales y cuantificables del mercado.

### 1.3 Tres Objetivos de Negocio Fundamentales

**Objetivo 1 — Eficiencia Operativa:**
Mejora radical de los tiempos de recuperación y consulta de información documental crítica. Reducción de la fricción y el costo laboral asociado a las búsquedas manuales en archivos físicos o repositorios digitales desorganizados.

**Objetivo 2 — Mitigación del Riesgo Operativo:**
Al digitalizar, clasificar y organizar inteligentemente los datos, se disminuye la exposición a errores humanos y se garantiza la preservación de la **memoria institucional**. Los documentos dejan de ser vulnerables a pérdida física, deterioro o fraude.

**Objetivo 3 — Cumplimiento Normativo (Compliance):**
Fortalecimiento de la capacidad de respuesta institucional frente a requerimientos de auditoría y supervisión. Se garantiza un acceso trazable, rápido y confiable a los registros documentales probatorios, alineado con la normatividad colombiana vigente.

**Impacto adicional — Sostenibilidad:**
Más allá de la rentabilidad, la propuesta de valor de SinergIA Lab incorpora beneficios sociales, ambientales y económicos mediante la **desmaterialización progresiva** de los procesos y la **reducción tangible de la huella de carbono** asociada al uso indiscriminado del papel.

### 1.4 Alcance Técnico del MVP — Dos Metas Analíticas Secuenciales

**Meta 1 — Clasificación automática de documentos:**
Despliegue de un modelo computacional capaz de ingerir archivos heterogéneos en formatos no estructurados (específicamente JPG y PDF) y categorizarlos de forma autónoma en **tipologías documentales predefinidas**. El sistema debe asignar el documento correcto a la categoría correcta sin intervención humana en el caso nominal.

**Meta 2 — Extracción de información estructurada (NER):**
Implementación de arquitecturas de **Reconocimiento de Entidades Nombradas (NER)** acopladas a modelos de visión por computadora para identificar, extraer y estructurar campos clave dentro de la documentación. El resultado final es la transformación del texto plano en **pares de clave-valor consultables**, listos para inyección en sistemas CRM o ERP.

### 1.5 Dataset: 1,000 Documentos Reales del SECOP

Para garantizar la viabilidad empírica de los modelos de IA y evitar el sobreajuste a entornos sintéticos, el equipo consolidó un corpus de datos primario compuesto por **1,000 documentos reales**. Estos fueron extraídos manualmente del **Sistema Electrónico de Contratación Pública de Colombia (SECOP)**, decisión metodológica crítica que introduce la varianza estocástica, el ruido visual, las marcas de agua, los sellos superpuestos y la heterogeneidad estructural que los modelos inevitablemente enfrentarán en entornos de producción.

#### Categoría 1: Cédula de Ciudadanía — 334 documentos

La cédula de ciudadanía presenta retos sustanciales de visión por computadora:
- **Variaciones severas de iluminación** en las fotografías aportadas por los usuarios (algunas tomadas con celular bajo luz artificial deficiente)
- **Hologramas de seguridad** que interfieren con la legibilidad del texto subyacente al reflejar luz de manera impredecible
- **Fondos texturizados** con patrones que compiten visualmente con el contenido textual
- **Desgaste físico** del documento original (dobleces, rasgaduras, tinta borrada)

Las entidades objetivo a extraer son: nombres completos, número de cédula, fecha de expedición, lugar de expedición.

#### Categoría 2: RUT — Registro Único Tributario (DIAN) — 235 documentos

Formato estandarizado por la **Dirección de Impuestos y Aduanas Nacionales (DIAN)** de Colombia. Su complejidad analítica es excepcional:
- **Extrema densidad tipográfica**: decenas de micro-casillas en un formato A4 que deben ser leídas en el orden correcto
- **Casillas críticas**: especialmente las casillas **46, 47, 48 y 50**, que contienen los **códigos CIIU** (Clasificación Industrial Internacional Uniforme) que determinan el perfil de riesgo y tributario de una organización
- **Intolerancia al error**: un solo dígito mal clasificado altera completamente la naturaleza jurídica de la empresa analizada. Un código CIIU incorrecto puede implicar una categoría tributaria diferente, régimen de IVA diferente, o un sector económico distinto

Las entidades objetivo: NIT, razón social, representante legal, dirección, actividad económica (CIIU), tipo de contribuyente.

#### Categoría 3: Pólizas de Seguros — 219 documentos

Piezas documentales densas en terminología legal con características particulares:
- **Arquitecturas semiestructuradas variables** según la entidad aseguradora emisora (Sura, Bolívar, Liberty, HDI, etc. tienen formatos distintos)
- El objetivo del NLP **no es solo extraer cifras**, sino **comprender el contexto** en que se dictaminan: beneficiarios, fechas de vigencia, cláusulas de exclusión, amparos, deducibles
- Alta ambigüedad léxica: términos como "valor asegurado", "suma asegurada", "capital asegurado" pueden referir a la misma entidad en documentos diferentes

Las entidades objetivo: asegurado, beneficiario, valor asegurado, fecha inicio vigencia, fecha fin vigencia, número de póliza, tipo de amparo.

#### Categoría 4: Certificados de Cámara de Comercio — 212 documentos / 2,505 páginas

La categoría más compleja del dataset:
- **2,505 páginas en total** para solo 212 documentos
- **Promedio de más de 11 páginas por archivo**, con algunos documentos superando las 20 páginas
- Son documentos **narrativos multipágina** que fusionan en un solo bloque textual: balances financieros, datos de representación legal, embargos judiciales, composición accionaria, historial de reformas estatutarias
- Exigen arquitecturas LLM con **ventanas de contexto excepcionalmente extensas** o estrategias sofisticadas de **fragmentación semántica (chunking)** para no desbordar la memoria de inferencia
- Las Cámaras de Comercio de distintas ciudades (Bogotá, Cali, Aburrá Sur, Cauca) emiten formatos narrativos con estructuras propias

Las entidades objetivo: razón social, NIT, representante legal, objeto social, capital social, fecha de constitución, domicilio, vigencia de la empresa.

#### Tabla Resumen del Dataset

| Categoría | Docs | Páginas aprox. | Reto principal |
|---|---|---|---|
| Cédula de Ciudadanía | 334 | ~334 | Ruido visual, hologramas, iluminación |
| RUT (DIAN) | 235 | ~235 | Densidad tipográfica, casillas CIIU críticas |
| Pólizas de Seguros | 219 | ~650+ | Terminología legal, variabilidad por aseguradora |
| Cámara de Comercio | 212 | 2,505 | Volumen multipágina, narrativa compleja, chunking |
| **TOTAL** | **1,000** | **~3,724** | |

#### Entidades Objetivo Globales del Sistema NER

El sistema debe extraer de forma transversal las siguientes entidades:
- **Nombres completos y razones sociales** — personas naturales y jurídicas
- **Números de identificación** — NIT corporativo y Cédula personal
- **Fechas exactas** — expedición, constitución, vigencia, expiración
- **Cifras económicas** — críticas en pólizas de seguros (valor asegurado, capital, deducibles)

#### Necesidad de Curaduría del Dataset

Como corolario del análisis exploratorio, el equipo diagnosticó la necesidad ineludible de someter el dataset a una rigurosa fase de **curaduría y control de calidad** para mitigar:
- Sesgo algorítmico por documentos duplicados
- Ruido estadístico por páginas ilegibles o con calidad de escaneo inferior al umbral mínimo
- Inconsistencias en la etiquetación manual inicial

---

## 2. Revisión de Antecedentes Científicos y Técnicos

### 2.1 La Metamorfosis del Campo IDP (2024–2026)

El campo del **Procesamiento Inteligente de Documentos (Intelligent Document Processing — IDP)** ha experimentado una metamorfosis acelerada y disruptiva entre 2024 y 2026. La literatura científica evidencia una **transición definitiva** desde los flujos de trabajo fundamentados exclusivamente en el Reconocimiento Óptico de Caracteres (OCR) tradicional y la aplicación de expresiones regulares, hacia **arquitecturas de Transformadores Multimodales y Modelos de Lenguaje de Gran Escala (LLMs) finamente ajustados**. Esta evolución ha redefinido los límites de la precisión, la resiliencia ante formatos desconocidos y la extracción de datos en entornos empresariales.

### 2.2 La Falla Estructural del Paradigma OCR+NLP Secuencial

Históricamente, los sistemas de extracción de información requerían procesos estrictamente secuenciales:
1. Un motor OCR extraía el texto bruto de la imagen
2. Este texto plano alimentaba un modelo NLP que intentaba discernir el significado

**Este paradigma adolecía de una falencia estructural crítica**: la **pérdida irrecuperable del contexto topológico y visual**. En documentos corporativos como una factura, un formulario RUT o un certificado de la Cámara de Comercio, la **posición espacial de un elemento en la página (su layout) es tan semánticamente relevante como el texto mismo**.

Por ejemplo: una cifra numérica adquiere el significado de "Total a Pagar" o "Capital Suscrito" únicamente por su **proximidad visual** a la etiqueta correspondiente. Un modelo que extrae texto de izquierda a derecha y de arriba a abajo **destruye completamente** esa información posicional.

La investigación científica reciente documenta la supremacía absoluta de los **Modelos Multimodales de Lenguaje (MLLMs) y los Modelos Visión-Lenguaje (VLMs)**, diseñados para procesar simultáneamente:
- El corpus textual
- La topología bidimensional del documento
- Las características visuales ricas: logotipos, tipografías en negrita, tablas complejas, firmas, sellos

### 2.3 Modelos del Estado del Arte

#### LayoutLMv3 — El Estándar Fundacional

La familia de modelos **LayoutLM**, particularmente su tercera iteración **LayoutLMv3**, se consolidó como estándar fundacional en la industria. Su arquitectura introduce una **proyección unificada** de parches de imagen y representaciones de texto, utilizando **embeddings posicionales en 2D**. Esta triple capa de percepción permite a LayoutLMv3 correlacionar espacialmente las entidades, superando ampliamente las limitaciones de lectura lineal del OCR.

**Limitación crítica documentada**: su desempeño sigue estando inherentemente **subordinado a la calidad del motor OCR de primera fase**. Si el OCR falla en la transcripción de un número de cédula borroso, el modelo LayoutLM heredará ese error — fenómeno conocido en ciencia de datos como **"garbage in, garbage out"**. Esta dependencia representa una vulnerabilidad sistémica cuando los documentos del SECOP presentan baja calidad de escaneo.

#### Donut — Arquitectura OCR-Free

Para mitigar las vulnerabilidades de la dependencia de OCR externo, la academia propuso arquitecturas **"OCR-free"** como el modelo **Donut (Document Understanding Transformer)**. Este enfoque revolucionario:

- **Ingiere la imagen cruda** del documento a través de un Transformador de Visión (Vision Transformer)
- **Genera directamente** una estructura de datos codificada (típicamente JSON) mediante un mecanismo codificador-decodificador
- **Omite completamente** la fase de reconocimiento carácter por carácter y el uso de cajas delimitadoras (bounding boxes)
- **Aprende a mapear** representaciones visuales globales directamente a secuencias de texto estructurado

El resultado es una **notable robustez ante documentos ruidosos o escaneos de baja calidad**, precisamente el escenario predominante en el dataset del SECOP.

#### Doc-Researcher — Huawei Technologies (Octubre 2025, arXiv:2510.21603v1)

Sistema unificado presentado por investigadores de **Huawei Technologies** que resuelve la severa fragmentación metodológica en la comprensión de documentos multimodales extensos:

- Realiza **análisis estructural profundo** que preserva la semántica visual de tablas, gráficos y ecuaciones (no solo extrae texto)
- Permite **investigaciones iterativas de múltiples saltos lógicos (multi-hop reasoning)** sobre corpus documentales técnicos y financieros — es decir, puede responder preguntas que requieren cruzar información de múltiples secciones del documento
- Arquitectura híbrida que permite seleccionar dinámicamente la **granularidad de recuperación de información**
- Opera como un **ecosistema de agentes colaborativos**, lo cual es excepcionalmente valioso para la auditoría de contratos largos

**Relevancia para SinergIA Lab**: valida teóricamente la viabilidad de procesar los densos documentos de Cámara de Comercio que fusionan balances financieros, representación legal y embargos judiciales.

#### Arctic-Extract — Snowflake AI Research (Noviembre 2025, arXiv:2511.16470v1)

Uno de los hallazgos científicos más críticos para la viabilidad del proyecto. Desarrollado por la división de IA de **Snowflake**:

- Peso total: apenas **6.6 GiB** — sin requerir OCR previo
- Procesa imagen y texto de forma **fusionada nativa**, eludiendo completamente la tubería OCR tradicional
- Capacidad de procesar hasta **125 páginas A4** en GPUs de recursos moderados como una **NVIDIA A10 de 24 GB de VRAM**
- Supera en **35%** a otros LLMs comerciales en la tarea de **extracción tabular** (crítica para el RUT con sus micro-casillas y las Cámaras de Comercio con sus balances financieros)

**Relevancia directa para SinergIA Lab**: valida empíricamente que es posible procesar documentos densos de Cámara de Comercio (que promedian más de 11 páginas) de manera **eficiente en costos** y **sin sacrificar precisión**, en hardware de nivel comercial accesible.

#### QLoRA — Fine-Tuning Eficiente de SLMs (Paradigma 2025-2026)

En paralelo al desarrollo de modelos multimodales, la vertiente más crítica para la privacidad de datos es el **ajuste fino (Fine-Tuning) de Modelos de Lenguaje de código abierto**. Los modelos comerciales cerrados (GPT-4o, Gemini 1.5 Pro) exhiben capacidades excepcionales en zero-shot learning, pero su implementación en sectores gubernamentales y financieros presenta **barreras infranqueables**:
- Soberanía de los datos
- Privacidad de la Información Personal Identificable (PII)
- Costos recurrentes de inferencia a escala inasumibles mediante APIs en la nube

La técnica dominante en 2025-2026 para resolver esto es **QLoRA (Quantized Low-Rank Adaptation)**:

1. **Congela** los pesos preentrenados del modelo en representación matemática de **baja precisión (4 bits)**
2. **Inyecta pequeñas matrices de bajo rango** que son las únicas que se entrenan para la tarea específica
3. El resultado es un modelo especializado que ocupa una fracción del hardware de un modelo full-precision

**Resultados documentados en la literatura**: modelos de la familia **Llama 3** (versiones de 8B o inferiores) ajustados mediante QLoRA en hardware de nivel consumidor logran tasas de precisión **superiores al 85%-90% (F1-score)** en tareas hiperespecíficas de extracción de entidades — extrayendo datos de formularios médicos, sentencias judiciales y documentos gubernamentales confidenciales, rivalizando con la precisión de modelos 100 veces más grandes.

**Ecosistema de herramientas open-source**:
- **Ollama**: para servir modelos localmente con interfaz unificada
- **Unsloth**: optimizador de fine-tuning que reduce el tiempo de entrenamiento hasta 5x
- **LlamaFactory**: framework unificado para fine-tuning eficiente de 100+ LLMs y VLMs (ACL 2024)

**Garantía de privacidad**: los documentos sensibles **nunca abandonan el servidor** de la empresa durante inferencia ni durante entrenamiento.

#### RAG Multimodal + Semantic Chunking — Para Documentos de Gran Longitud

Para los documentos de Cámara de Comercio (2,505 páginas en 212 documentos), forzar a un LLM a ingerir 50 páginas simultáneamente frecuentemente induce **degradación de la atención y alucinaciones** en el medio del texto — el modelo "se distrae" y comienza a inventar entidades que no existen.

La solución documentada en la literatura:
1. **Segmentación preservando topología**: dividir el documento respetando los límites lógicos de secciones (no cortar a mitad de un párrafo legal)
2. **Vectorización** de los fragmentos en un espacio semántico
3. **Recuperación selectiva**: solo inyectar en el contexto del modelo los segmentos pertinentes a la consulta
4. **Instrucción estructurada**: forzar al modelo mediante prompt engineering a emitir respuesta estrictamente en esquema JSON

### 2.4 Tabla de Síntesis de Literatura Científica

| Referencia | Tecnología | Hallazgo Clave | Relevancia para SinergIA Lab |
|---|---|---|---|
| Dong, K. et al., Huawei (Oct 2025), arXiv:2510.21603 | Doc-Researcher: parsing multimodal + deep research multi-agente | Multi-hop reasoning sobre corpus densos; preserva semántica visual tablas y gráficos | Valida arquitectura para documentos Cámara de Comercio multipágina con balances y embargos |
| Chiliński, M. et al., Snowflake (Nov 2025), arXiv:2511.16470 | Arctic-Extract: VLM de 6.6 GiB, sin OCR, extracción tabular SoTA | +35% sobre competidores en extracción tabular; procesa 125 págs A4 en GPU 24 GB | Valida viabilidad de modelos VLM ligeros para despliegue local en RUT y pólizas |
| Wang, W. et al., SAP Singapore (Oct 2025), arXiv:2510.13366 | Survey: evolución Document AI hacia LLMs decodificadores y RAG | Transición definitiva de OCR+regex hacia MLLMs contextuales | Fundamenta la elección arquitectónica del proyecto hacia LLMs para Key Information Extraction |
| Colakoglu, G. et al., NEC Labs Europe / ZHAW (Feb 2025), arXiv:2502.18179 | Benchmark LayoutLMv3 vs LLMs generales en documentos ricos en layout | LLMs generales compiten con LayoutLM cuando el layout es preservado correctamente | Informa las decisiones de diseño sobre cuándo usar embeddings espaciales vs. texto puro |
| Kalušev, V. & Brkljač, B., Serbia (Feb 2025), arXiv:2502.10582 | Fine-tuning LLMs para NER en documentos legales | Fine-tuning mejora dramáticamente precisión en NER especializado vs zero-shot | Justifica el fine-tuning específico para pólizas de seguros y certificados de Cámara de Comercio |
| Wiz Research Team (Jun 2025) | Fine-tuning Llama 3.2 1B para detección de secretos/PII en código | SLMs tiny con QLoRA alcanzan rendimiento usable en tareas de privacidad | Valida que modelos muy pequeños (1B) son viables para detección de PII — aplica a Cédulas |
| Buscaldi, D. et al., Sorbonne (2025), CEUR | NER científico con Fine-Tuning y Few-Shot Learning | Few-shot learning + fine-tuning son complementarios en dominios especializados | Justifica parámetros de entrenamiento para terminología específica de pólizas de seguros |
| Pingili, R., Itech US Inc. (Jun 2025) | IDP en gobierno: impacto en tiempos de gestión pública | **IDP reduce tiempos de gestión pública en 70%** | Legitima el caso de negocio para el sector público colombiano (SECOP, contratación pública) |
| **(Nuevo)** IDP Accelerator (2026), arXiv:2602.23481 | Pipeline agéntico: extracción → validación compliance automatizada | Arquitectura end-to-end con agentes para extracción + validación normativa | Modelo de referencia para la capa de compliance con Ley 1581 y SIC Circular 002/2024 |
| **(Nuevo)** LLaMA NER hallucinations (2025), arXiv:2506.08827 | Impacto del fine-tuning de LLaMA sobre alucinaciones en NER legal | Fine-tuning específico reduce significativamente alucinaciones en extracción de entidades legales | Crítico para pólizas: justifica el fine-tuning como mecanismo anti-alucinación en textos legales |

---

## 3. Revisión de Productos y Soluciones en el Mercado

### 3.1 Contexto de Mercado Global

La transición del IDP desde concepto de vanguardia hacia necesidad corporativa esencial se refleja en la dinámica del mercado global:

- Mercado IDP con **CAGR del 24%-35%** sostenido hacia 2025-2026
- Proyecciones de valoración: **$21B-$54B** hacia el horizonte 2034-2035 (Global Market Insights)
- **78%** de las empresas corporativas ya han operacionalizado soluciones IA para IDP (AIIM Market Momentum Index 2025)
- **66%** de los nuevos proyectos IDP en 2025 tienen como objetivo **sustituir plataformas OCR legadas u obsoletas** — evidencia de apetito insaciable por innovación y precisión

**Evolución de los casos de uso**: han migrado del *back-office* tradicional (procesamiento de facturas, archivo contable) hacia operaciones de **front-office** con impacto directo al cliente:
- Validación de protocolos **KYC** (Conozca a su Cliente) en banca
- Procesamiento de contratos legales en tiempo real
- Expedientes gubernamentales de contratación pública
- Onboarding de empleados con validación automática de documentos

### 3.2 Contexto Latinoamericano y Colombiano

En Colombia, la adopción de IDP se cataliza por un entorno regulatorio que ha digitalizado agresivamente la facturación y la tributación (factura electrónica DIAN, SEII, RADIAN), **pero que aún exige que las empresas concilien cientos de miles de documentos PDF dispares**. Las áreas operativas más impactadas diariamente son:
- **Banca**: validación de identidad (KYC), cédulas en onboarding, RUT para apertura cuentas empresariales
- **Recursos Humanos**: RUT y cédulas en procesos de vinculación y nómina
- **Jurídica**: Cámaras de Comercio de múltiples regiones (Bogotá, Cali, Aburrá Sur, Cauca) para debida diligencia y contratos
- **Seguros**: pólizas de cumplimiento obligatorias en contratación pública (SECOP)

### 3.3 Segmentación del Ecosistema Competitivo

#### Estrato 1: Proveedores de Infraestructura Cloud (Hyperscalers)

**Actores**: Amazon Web Services (AWS Textract + Amazon Bedrock/Nova), Microsoft Azure (AI Document Intelligence), Google Cloud Platform (Document AI)

Estos productos operan como **APIs orientadas a equipos de desarrollo**. Sus características:
- Escalabilidad computacional virtualmente **infinita**
- Vastos catálogos de modelos preentrenados que identifican facturas, IDs y recibos con asombrosa agilidad
- Posibilidad de **interrogar el documento directamente en lenguaje natural** (ej. "¿Cuál es el NIT de esta empresa?")
- Modelos específicos como Amazon Nova Lite permiten procesar PDFs directamente a JSON con few-shot learning

**Limitaciones frente a SinergIA Lab**:
- Proveen los bloques de construcción técnicos, pero **exigen que la organización cliente invierta fuertemente en ingeniería** para orquestar la lógica de negocio, crear interfaces de validación e integrar con sus sistemas
- Al operar en clústeres de nube pública compartidos, la **transmisión transfronteriza** de datos de alto riesgo (huellas y rostros en Cédulas, datos financieros del RUT, PII en general) desencadena severos escrutinios bajo la **Ley 1581 de 2012** y la **Circular 002 de 2024 de la SIC**
- **No están "tropicalizados"** para el ecosistema colombiano: un modelo preentrenado en documentos norteamericanos y europeos no comprende las particularidades del RUT de la DIAN ni los formatos narrativos de las Cámaras de Comercio

#### Estrato 2: Plataformas Especializadas Corporativas y Nativas de RPA (Enterprise IDP)

**Actores**: ABBYY Vantage, UiPath Document Understanding/IXP, Hyperscience, Tungsten Automation (antes Kofax), OpenText

Estas corporaciones lideran los **Cuadrantes Mágicos de Gartner** y las evaluaciones del **IDC MarketScape**. Características detalladas:

**ABBYY Vantage:**
- Destacado por su **"Skill Designer" modular**: permite crear habilidades de extracción específicas para tipos de documentos sin programación
- OCR histórico capaz de descifrar documentos de **archivo profundamente degradados**, abarcando más de **150 idiomas**
- Integración nativa con flujos RPA y plataformas de gestión documental enterprise

**UiPath Document Understanding / IXP:**
- Integra la lectura de documentos dentro de flujos de **Automatización Robótica de Procesos (RPA)** de forma nativa
- Módulo **"Action Center"**: cuando el modelo de IA duda (confianza baja), permite a operadores humanos **intervenir y corregir**, creando un bucle de retroalimentación perfecto (Active Learning continuo)
- El resultado de cada corrección humana retroalimenta automáticamente el modelo para mejorar en iteraciones futuras

**Hyperscience:**
- Posicionado específicamente en la cima para casos de uso **gubernamentales y de seguros de alto riesgo**
- Prioriza la **gobernanza algorítmica** y la colaboración humano-máquina
- Auditoría estricta de cada decisión del modelo

**Limitaciones frente a SinergIA Lab**:
- La complejidad de su arquitectura exige despliegues que suelen tardar entre **8 y 14 semanas**
- Los costos de **licenciamiento anual son extremadamente prohibitivos** para el segmento PyME en mercados emergentes como Colombia — el TCO (Costo Total de Propiedad) descalifica automáticamente a la gran mayoría del tejido empresarial colombiano medio
- Cuando se enfrentan a **formatos hiperlocales no contemplados** en sus librerías globales (el RUT con sus resoluciones DIAN, las Cámaras de Comercio regionales), requieren costosos servicios profesionales de configuración adicional

#### Estrato 3: Soluciones de Nicho, Fintech y Actores Locales

**Actores**: Extend, Rossum, Klippa DocHorizon, Doc.AI Colombia

Herramientas ágiles de reciente generación:
- Interfaces **no-code** con tiempos de despliegue medidos en **días** en lugar de meses
- Tasas de precisión **superiores al 95%** en flujos financieros estrechos (Cuentas por Pagar, facturas DIAN)
- **Doc.AI Colombia**: especializado en automatización de facturas y declaraciones de la DIAN; conocimiento profundo del ecosistema tributario colombiano

**Limitaciones frente a SinergIA Lab**:
- Al intentar forzar estas herramientas verticales a procesar **expedientes legales multipágina, laberínticos y narrativos** como los de la Cámara de Comercio, carecen de la flexibilidad arquitectónica necesaria
- No tienen capacidad para integrar **RAG multimodal** ni para manejar ventanas de contexto extensas
- Su enfoque restringido los hace ineficaces para el procesamiento semántico profundo de textos legales densos

### 3.4 Tabla Comparativa Completa

| Tipo de Solución | Actores Principales | Funcionalidades Destacadas | Fortalezas | Limitaciones vs. SinergIA Lab |
|---|---|---|---|---|
| **Infraestructura Cloud (API)** | AWS Textract+Bedrock, Azure AI Document Intelligence, Google Cloud Document AI | APIs REST, modelos preentrenados, consulta en lenguaje natural, few-shot learning, escalabilidad infinita | Pago por uso, integración ecosistema cloud, velocidad de despliegue | Requiere ingeniería costosa para orquestar. Datos confidenciales salen al exterior (Ley 1581). No tropicalizados para Colombia |
| **Enterprise IDP/RPA** | ABBYY Vantage (150+ idiomas, Skill Designer), UiPath IXP (Action Center HITL), Hyperscience (gobierno/seguros), Tungsten/Kofax, OpenText | Flujos visuales extremo a extremo, HITL integrado, orquestación RPA, auditoría estricta, Active Learning | Precisión extrema en entornos bancarios y legales; IDC MarketScape leaders; ecosistema integral | **8-14 semanas de despliegue**. Licenciamiento prohibitivo para PyMEs colombianas. Configuración costosa para formatos locales |
| **Nicho/Fintech/Local** | Extend, Rossum, Klippa DocHorizon, Doc.AI Colombia (DIAN) | No-code, despliegue en días, >95% en flujos financieros, adaptación tributaria local Colombia | ROI rápido, conocimiento tributario local | Falla en expedientes legales narrativos multipágina. Sin RAG multimodal. Sin capacidad para Cámara de Comercio |

---

## 4. Análisis Comparativo de Referentes

### 4.1 Coincidencias entre Literatura Científica y Mercado

Existe un **consenso irrefutable** entre la academia y la industria:

**Consenso 1 — Obsolescencia del OCR puro**: El estándar moderno, avalado por investigaciones sobre LayoutLMv3 y productos como UiPath IXP, dicta que el procesamiento documental debe ser **inherentemente "inteligente" e impulsado por el contexto**. Un sistema competitivo no solo transfiere texto, sino que infiere lógicamente que una cadena numérica de 9 dígitos bajo la palabra "NIT" es una entidad corporativa clave, incluso si el documento fue escaneado boca abajo.

**Consenso 2 — Human-in-the-Loop como estándar, no excepción**: Tanto la investigación algorítmica como el diseño de producto de los mejores competidores (UiPath Action Center, Hyperscience) coinciden en que la **validación asistida por humanos no es una señal de fracaso de la IA**, sino un **componente mandatorio** para el aseguramiento de la calidad y el aprendizaje activo en entornos de misión crítica.

### 4.2 Vacíos Estructurales que SinergIA Lab Puede Cubrir

#### Vacío 1: Tropicalización y Especialización Colombiana

Las grandes plataformas globales adolecen de un **sesgo norteamericano y europeo** en su preentrenamiento. Identifican perfectamente un formulario **W-2 del IRS de EE.UU.** pero los formatos colombianos les resultan ajenos:

- El **RUT de la DIAN** contiene micro-casillas que cambian según resoluciones locales específicas (ej. Resolución 000110 de octubre 2021)
- Las **Cámaras de Comercio** de Bogotá o Cali emiten documentos narrativos que fusionan balances financieros, datos de representación legal y embargos judiciales en un solo bloque textual multipágina — un formato que no existe en los datasets de preentrenamiento de las plataformas globales
- El ajuste fino local permite a SinergIA Lab comprender esta idiosincrasia documental con una precisión que las plataformas genéricas no pueden igualar

#### Vacío 2: Soberanía de Datos, Compliance y Privacidad

Al procesar cédulas de ciudadanía y documentos de nómina, las organizaciones colombianas están sujetas a:
- **Ley Estatutaria 1581 de 2012** — Protección de Datos Personales (Hábeas Data)
- **Circular Externa 002 de 2024 de la Superintendencia de Industria y Comercio (SIC)** — Directrices específicas sobre uso de IA con datos personales
- **CONPES 4144** — Política Nacional de Inteligencia Artificial

**Transmitir copias de cédulas a servidores de OpenAI o nubes públicas externas representa un riesgo de cumplimiento normativo significativo** para las organizaciones colombianas. SinergIA Lab puede proponer arquitecturas donde los **SLMs (como Llama 3 8B)** se despliegan localmente (on-premise) o en instancias de nube privada controladas por el cliente, garantizando que la **PII nunca abandone el perímetro seguro de la organización**.

#### Vacío 3: Barreras de Costo y Flexibilidad

El **TCO (Costo Total de Propiedad)** de soluciones como ABBYY Vantage o Hyperscience descalifica automáticamente a la gran mayoría del tejido empresarial colombiano medio — especialmente PyMEs, cooperativas, entidades públicas de nivel municipal y empresas medianas del sector asegurador.

El uso de tecnologías open-source comprobadas en la literatura (**QLoRA** para fine-tuning + **Ollama** para inferencia), empaquetadas en un servicio **modular API-first**, permite ofrecer un **modelo de precios disruptivo, ágil y escalable** que lleva capacidades de nivel enterprise al segmento de mercado desatendido.

### 4.3 Oportunidad para el MVP: El Orquestador Híbrido y Vertical

La oportunidad estratégica consiste en construir un **orquestador híbrido y vertical**. En lugar de competir construyendo un nuevo LLM desde cero, SinergIA Lab ensamblará componentes del estado del arte:

- **Motor de preprocesamiento de visión** eficiente y robusto
- **LLM open-source finamente ajustado** (fine-tuned) para reconocer las entidades específicas del RUT, Cédula, Pólizas y Cámara de Comercio colombianos
- **Interfaz de validación humana** sencilla pero poderosa

El resultado es un **IDP para el mercado latinoamericano** que combina:
- **Agilidad de startup** (despliegue en días, precios accesibles)
- **Precisión semántica de gigante tecnológico** (modelos del estado del arte)
- **Rigor de privacidad de sistema de defensa** (todo on-premise, sin datos al exterior)

---

## 5. Características Iniciales del Producto

El MVP de SinergIA Lab se conceptualiza como una solución de software **modular y orientada a servicios (API-first)**, complementada con una aplicación web administrativa para intervención humana. Sus cinco componentes cardinales:

### Componente 1: Motor de Ingesta Inteligente y Preprocesamiento

**Función**: Recibe los documentos y los prepara para el procesamiento de IA.

**Capacidades técnicas**:
- **Omnicanal**: acepta archivos de imágenes (JPG, JPEG, PNG) y documentos PDF, tanto individuales como en lote (batch)
- **Deskewing (enderezamiento)**: corrección automática de documentos escaneados con inclinación (ej. cédula fotografiada a 15° de ángulo)
- **Binarización de contraste**: normaliza la iluminación y aumenta el contraste para hacer el texto legible independientemente de las condiciones del escaneo original
- **Eliminación de ruido de fondo**: filtra artefactos de compresión JPEG, manchas, fondos texturizados

**Por qué es crítico**: La sofisticación de la IA en capas posteriores es irrelevante si la imagen de entrada tiene baja calidad. Este módulo determina el techo de precisión de todo el sistema.

### Componente 2: Módulo Clasificador Neuronal Autodirigido

**Función**: Determina qué tipo de documento acaba de ingresar al sistema.

**Mecanismo**:
- Un **modelo de visión/lenguaje ligero** (optimizado para velocidad sobre exhaustividad) analiza el documento entrante
- Asigna una **etiqueta categórica** con porcentaje de confianza: `Cedula_Ciudadania`, `RUT_DIAN`, `Camara_Comercio`, `Poliza_Seguro`
- El resultado del clasificador **enruta el documento** al modelo de extracción NER especializado para esa categoría — porque el modelo fine-tuned para cédulas tiene un vocabulario y esquema JSON diferente al de pólizas

**Por qué es crítico**: Sin clasificación correcta, un documento podría ser procesado por el modelo equivocado, generando extracciones sin sentido.

### Componente 3: Orquestador de Fragmentación (Chunking) Sensible al Diseño

**Función**: Divide documentos largos de manera inteligente para no desbordar el LLM.

**Mecanismo**:
- Identifica los **límites lógicos de las secciones** en documentos multipágina (ej. en un certificado de Cámara de Comercio, detecta dónde termina la sección de "composición accionaria" y comienza "representación legal")
- Divide el texto **preservando la coherencia semántica** — nunca corta a mitad de una cláusula legal o de una tabla de cifras
- Ensambla posteriormente los resultados de extracción de cada fragmento en un JSON unificado **sin pérdida de contexto**

**Por qué es crítico**: Los documentos de Cámara de Comercio promedian más de 11 páginas. Sin chunking inteligente, el LLM sufriría "degradación de atención" y comenzaría a alucinar entidades inexistentes.

### Componente 4: Módulo Central de Extracción Semántica (NER)

**Función**: El núcleo analítico del sistema — extrae las entidades de negocio.

**Mecanismo**:
- Impulsado por un **LLM local con ajuste fino** específico por categoría documental
- Extrae quirúrgicamente: nombres completos, razones sociales, números de identificación (Cédula/NIT), fechas de expedición/vigencia, montos monetarios
- Basa la extracción en **entendimiento contextual**, no solo en coincidencia de patrones (entiende que "capital suscrito" y "valor asegurado" son entidades diferentes aunque ambas sean cifras numéricas)
- Empaqueta todos los resultados en un **esquema JSON estrictamente formateado** con claves predefinidas

**Salida ejemplo para RUT**:
```json
{
  "razon_social": "EMPRESA EJEMPLO S.A.S.",
  "nit": "900123456-7",
  "actividad_economica_principal": "6201",
  "tipo_contribuyente": "Responsable del IVA",
  "fecha_expedicion": "2024-03-15",
  "confidence": 0.94
}
```

### Componente 5: Interfaz de Resolución y Consenso (Human-in-the-Loop)

**Función**: Involucra al operador humano cuando la IA no está segura.

**Mecanismo**:
- Si el modelo extrae cualquier entidad obligatoria con **confianza < 80%** (umbral configurable), el flujo automático se **detiene completamente**
- La imagen del documento se presenta en pantalla al operador con los **campos dudosos resaltados visualmente** (ej. el NIT subrayado en amarillo con el valor propuesto)
- El operador **corrige o confirma** el valor propuesto
- Cada corrección se almacena automáticamente en un **repositorio de datos de reentrenamiento** — cada interacción humana hace al modelo más inteligente en iteraciones futuras

**Valor comercial dual**:
1. **Inmediato**: garantía de calidad en el 100% de los documentos procesados
2. **Estratégico a largo plazo**: el modelo mejora continuamente con datos reales del cliente, creando un **foso defensivo** que los competidores no pueden replicar sin acceso a esos datos

---

## 6. Requerimientos Funcionales Preliminares

Los requerimientos funcionales definen los **comportamientos medibles y las transacciones de información** que el sistema SinergIA Lab debe ejecutar satisfactoriamente.

| ID | Nombre | Descripción Detallada | Criterio de Aceptación |
|---|---|---|---|
| **RF-01** | Carga y Recepción de Documentos | El sistema expone una **API REST** y un portal web con capacidad de carga asíncrona, tanto individual como en lotes (batch). La API acepta formatos: `.pdf`, `.jpg`, `.jpeg`, `.png`. Debe gestionar colas de procesamiento para lotes masivos sin timeout del cliente. | Confirmación de recepción en < 500ms. Cola de procesamiento visible. Soporte mínimo de 100 documentos por lote. |
| **RF-02** | Clasificación Documental Automática | Asignación de etiqueta categórica a cada documento: `Cedula_Ciudadania`, `RUT_DIAN`, `Camara_Comercio`, `Poliza_Seguro`. El resultado incluye el porcentaje de confianza de la clasificación. Enrutamiento automático al extractor NER correspondiente. | **Precisión (accuracy) > 85%** en conjunto de prueba del piloto con 200 documentos balanceados |
| **RF-03** | Análisis y Fragmentación de Documentos Densos | Para documentos `Camara_Comercio` con más de 3 páginas: segmentación espacial por bloques semánticos coherentes con ensamblaje posterior sin pérdida de contexto entre fragmentos. El sistema debe detectar secciones: constitución, representación, composición accionaria, capital. | Ninguna entidad objetivo debe perderse por fragmentación incorrecta. Tasa de pérdida por chunking: 0% en conjunto de prueba. |
| **RF-04** | Extracción de Entidades Nombradas (NER) | Extracción de: Nombres completos / Razón Social, Números de Identificación (Cédula / NIT con dígito verificador), Fechas Relevantes (expedición, constitución, vigencia, expiración), Cifras Monetarias (valor asegurado, capital suscrito, deducibles). Resultados en pares clave-valor con metadato de confianza. | F1-score > 85% por categoría documental en conjunto de prueba |
| **RF-05** | Cálculo y Enrutamiento por Puntuación de Confianza | Cada entidad extraída incluye un porcentaje de confianza individual (0%-100%). Si **cualquier entidad obligatoria** tiene confianza < **80%** (umbral configurable por cliente), el documento completo se enruta automáticamente a validación humana en la interfaz HITL. | Cero documentos con entidades de baja confianza marcadas como "finalizados" sin revisión humana |
| **RF-06** | Generación y Exportación de Estructuras JSON | Al finalizar la extracción (automática o con validación humana), el sistema empaqueta todos los datos en un **JSON estándar predefinido** por categoría, listo para integración inmediata mediante webhook o polling con CRM, ERP o sistemas de gestión documental del cliente. | JSON válido según esquema definido en 100% de los casos. Tiempo de generación < 1 segundo post-extracción. |

---

## 7. Requerimientos No Funcionales Preliminares

Los requerimientos no funcionales rigen los **atributos de calidad, el desempeño, la seguridad de la infraestructura y las restricciones legales** bajo las cuales el sistema opera en territorio colombiano.

| ID | Nombre | Descripción Detallada | Restricción Técnica |
|---|---|---|---|
| **RNF-01** | Cumplimiento Normativo y Privacidad de Datos | Adherencia estricta a **Ley Estatutaria 1581 de 2012** (Hábeas Data Colombia), **Circular Externa 002 de 2024 de la SIC** (uso de IA con datos personales), y **CONPES 4144** (Política Nacional de IA). Todos los datos biométricos (fotografías en cédulas) y PII deben ser procesados localmente. | Cifrado **AES-256 en reposo** para datos biométricos y PII. Política de **cero retención de datos** post-procesamiento en la nube. Logs de auditoría no modificables. Opción de despliegue on-premise obligatoria. |
| **RNF-02** | Latencia y Tiempos de Respuesta | Dos regímenes de procesamiento según complejidad del documento: sincrónico para documentos simples, asíncrono con notificación para documentos complejos. | Cédulas y RUT (1 página): respuesta sincrónica en **≤ 5 segundos**. Pólizas y Cámara de Comercio (multipágina): procesamiento en segundo plano con notificación vía **webhooks en < 45 segundos**. |
| **RNF-03** | Eficiencia Computacional y Hardware | Los modelos deben funcionar en hardware comercial accesible para empresas medianas colombianas, sin requerir infraestructura de datacenter masivo. | SLMs cuantizados a **4 bits (PEFT/QLoRA)** operando en **una sola GPU comercial de 24 GB VRAM** (NVIDIA A10, RTX 3090 o RTX 4090). Prohibido requerir múltiples GPUs A100 para operación nominal. |
| **RNF-04** | Alta Disponibilidad y Resiliencia | El sistema debe tolerar fallos parciales sin afectar la operación completa. Un fallo en el módulo OCR/preprocesamiento no debe tumbar el módulo LLM. | Arquitectura de **microservicios / contenedores Kubernetes** para aislamiento de fallos. **Uptime del 99.9%** en producción (< 8.76 horas de caída por año). Recuperación automática de pods fallidos. |
| **RNF-05** | Trazabilidad y Auditoría de Sistemas IA | Capacidad de responder ante auditorías regulatorias y corporativas: ¿quién procesó qué documento, cuándo, con qué nivel de confianza del algoritmo, y qué modificaciones hizo el operador humano? | **Log de auditoría inmutable** que registra: marca de tiempo, identificador de usuario / API Key, porcentaje de confianza del algoritmo, rastro completo de modificaciones del operador humano, versión del modelo usado. Alineado con principios de **IA explicable (XAI)** y ética corporativa. |

---

## 8. Aprendizajes, Recomendaciones y Moralejas

La síntesis holística de la investigación científica, el análisis del mercado IDP y la validación de las necesidades del ecosistema colombiano decanta en cuatro directrices estratégicas críticas para asegurar que SinergIA Lab trascienda de un prototipo académico a un producto comercialmente escalable.

### Moraleja 1: "Garbage In, Garbage Out" — El Preprocesamiento lo es Todo

La sofisticación de la capa de inteligencia artificial es **absolutamente irrelevante si la capa de percepción es defectuosa**. Modelos de lenguaje masivos y computacionalmente costosos fracasarán irremediablemente al intentar extraer un NIT de un RUT si la imagen subyacente está borrosa, rotada 90°, o presenta ruido de compresión JPEG severo.

Esta lección está validada empíricamente por múltiples investigaciones en visión por computadora, incluyendo los propios benchmarks de Arctic-Extract y la crítica bien documentada a LayoutLMv3 (cuyo desempeño cae abruptamente cuando el OCR de primera fase comete errores).

**Implicación práctica**: el esfuerzo ingenieril invertido en el **módulo de preprocesamiento de imagen** y en la **limpieza exhaustiva del dataset SECOP** (eliminación de duplicados, páginas ilegibles, inconsistencias de etiquetado) será **tan determinante para el éxito del modelo final como la afinación de los hiperparámetros de la red neuronal**. No es glamoroso, pero es el fundamento.

### Moraleja 2: Abrazar la Eficiencia de los SLMs — No Necesitas GPT-4

La hiper-tendencia observada en la investigación aplicada entre 2025 y 2026 demuestra fehacientemente que **no es necesario, ni financieramente prudente, desplegar modelos mastodónticos de cientos de billones de parámetros**, ni depender de costosas APIs en la nube para ejecutar tareas de extracción estructurada.

SinergIA Lab debe capitalizar el uso de modelos base altamente eficientes (Arctic-Extract 6.6 GiB o la familia Llama 3 8B) sometidos a un **riguroso proceso de Fine-Tuning con QLoRA**. Esta ruta tecnológica:
- Garantiza un rendimiento especializado **equivalente a los modelos cerrados gigantes** en las tareas específicas del proyecto
- **Blinda a la empresa y a sus clientes** frente a los severos riesgos legales de transferencia de datos confidenciales
- Protege la **soberanía digital** en América Latina
- Elimina la dependencia de terceros externos para la inferencia en producción

### Moraleja 3: Evitar la "Falacia de la Automatización Absoluta"

Intentar alcanzar un **100% de automatización sin intervención humana** (Straight-Through Processing absoluto) en la primera iteración del producto conduce frecuentemente al **fracaso sistémico y a la desilusión del cliente corporativo**.

La incorporación de flujos de revisión humana (HITL) debe presentarse comercialmente **no como un defecto o debilidad de la IA**, sino como un **mecanismo avanzado de gobernanza algorítmica**. Esta es la misma filosofía que impulsa a UiPath a vender su Action Center como feature premium, no como workaround.

En sectores críticos como el **bancario, legal y asegurador**, la supervisión humana de las excepciones (casos con confianza baja) es una **exigencia operativa regulatoria**, no una debilidad técnica. Además, esta interacción humana proporciona un **flujo continuo de datos de entrenamiento** retroalimentados que enriquecerán el modelo a lo largo del tiempo, creando un **foso defensivo comercial** que los competidores no pueden replicar sin acceso a esos datos propios del cliente.

### Moraleja 4: El Valor Real está en la Orquestación, no en la Lectura

El valor definitivo de SinergIA Lab **no residirá únicamente en la proeza técnica de "leer y entender" un documento complejo** emitido por la Cámara de Comercio. Cualquier competidor con suficiente inversión podría replicar esa capacidad.

Su **valor monetizable y diferencial** provendrá de la **orquestación**: la capacidad de:
1. Traducir párrafos jurídicos densos en **JSONs predecibles y estructurados**
2. **Inyectar esa información** de manera limpia, segura y asíncrona dentro del software contable, el CRM o el ERP del cliente
3. Hacerlo cumpliendo con la normativa colombiana de privacidad
4. Hacerlo sin que un solo byte de información sensible abandone el perímetro seguro del cliente

El cliente no compra un "lector de documentos". Compra la **eliminación de la fricción entre el papel y su sistema de gestión**.

---

## 9. Referencias Bibliográficas

### Documentación Base del Proyecto
- **Grupo-1 - Ciclo-1-V1.docx**: Contexto SinergIA Lab, metodología CRISP-DM++, análisis exploratorio del dataset SECOP. Pontificia Universidad Javeriana, Especialización en Inteligencia Artificial. 28 de marzo de 2026.
- **DIAN Colombia**: Documentación sobre el formato RUT y regulaciones de Cámaras de Comercio (IN-CAC-0237; Resolución 000110 de 11-10-2021)

### Normatividad Colombiana
- **Ley Estatutaria 1581 de 2012** — Protección de Datos Personales (Hábeas Data)
- **Circular Externa No. 002 de 2024** — Superintendencia de Industria y Comercio (SIC) — Directrices sobre uso de IA con datos personales
- **CONPES 4144** — Política Nacional de Inteligencia Artificial de Colombia

### Artículos Científicos y Literatura Académica (2024-2026)

| Autores | Año | Título | Publicación | arXiv/DOI |
|---|---|---|---|---|
| Dong, K., Huang, S., Ye, F. et al. (Huawei Technologies) | Oct 2025 | Doc-Researcher: A Unified System for Multimodal Document Parsing and Deep Research | Huawei Technologies Co., Ltd. | arXiv:2510.21603v1 |
| Chiliński, M., Ołtusek, J., Jaśkowski, W. (Snowflake AI Research) | Nov 2025 | Arctic-Extract Technical Report | Snowflake AI Research | arXiv:2511.16470v1 |
| Wang, W., Hu, H., Zhang, Z. et al. (SAP Singapore) | Oct 2025 | Document Intelligence in the Era of Large Language Models: A Survey | SAP Singapore | arXiv:2510.13366v1 |
| Colakoglu, G., Solmaz, G., Fürst, J. (NEC Labs Europe / ZHAW) | Feb 2025 | Information Extraction Design Space for Layout-Rich Documents using LLMs | NEC Laboratories Europe | arXiv:2502.18179v4 |
| Kalušev, V. & Brkljač, B. (Serbia) | Feb 2025 | Fine-Tuning LLMs for Named Entity Recognition in Legal Documents | Institute for AI Research, Serbia | arXiv:2502.10582v1 |
| Pingili, R. (Itech US Inc.) | Jun 2025 | AI-driven intelligent document processing in government and public administration | World Journal of Advanced Engineering Technology and Sciences | ResearchGate |
| Buscaldi, D., Dessi, D., Osborne, F. et al. (Sorbonne) | 2025 | Evaluating LLMs for NER in Scientific Domain with Fine-Tuning and Few-Shot Learning | CEUR Workshop Proceedings | ceur-ws.org/Vol-3979 |
| Iqbal, K. et al. | 2024/2025 | Applications of Intelligent Document Processing (IDP) | Journal of Applied Management and Multidisciplinary Studies | JAMM |
| Wiz Research Team | Jun 2025 | Small Language Model for Secrets Detection in Code | Wiz Blog | wiz.io/blog |
| **(Adicional)** IDP Accelerator Team | 2026 | IDP Accelerator: Agentic Document Intelligence from Extraction to Compliance Validation | arXiv | arXiv:2602.23481 |
| **(Adicional)** Autores NER Legal | 2025 | The impact of LLaMA fine tuning on hallucinations for named entity extraction in legal documents | arXiv | arXiv:2506.08827v1 |

### Informes de Mercado e Industria
- **AIIM & Deep Analysis (2025)**: *Market Momentum Index: Intelligent Document Processing (IDP) Survey 2025.* 78% adopción IA en IDP; 66% reemplazando sistemas legados.
- **IDC MarketScape (2025-2026)**: *Worldwide Intelligent Document Processing Software Vendor Assessment.* Ref: US53014125.
- **Global Market Insights (2024-2034)**: *IDP Market Analysis.* Proyecciones $21B-$54B, CAGR 24%-35%.
- **Gartner Peer Insights 2026**: *Best Intelligent Document Processing Solutions Reviews.*

### Productos Comerciales Analizados
- **Cloud APIs**: AWS (Textract + Bedrock + Amazon Nova Lite), Microsoft Azure AI Document Intelligence, Google Cloud Document AI
- **Enterprise IDP/RPA**: ABBYY Vantage, UiPath Document Understanding/IXP, Hyperscience, Tungsten Automation (Kofax), OpenText
- **Nicho y Local**: Extend, Rossum, Klippa DocHorizon, Doc.AI Colombia
- **Herramientas Open-Source de Fine-Tuning**: Ollama, Unsloth, LlamaFactory (ACL 2024, GitHub: hiyouga/LlamaFactory)

---

## 10. URLs de Referencia Web Consultadas

### Modelos, Arquitecturas e Investigación
| Recurso | URL |
|---|---|
| LayoutLMv3 — KungFu.AI | https://www.kungfu.ai/blog-post/engineering-explained-layoutlmv3-and-the-future-of-document-ai |
| LayoutLMv3 — ThirdEye Data | https://thirdeyedata.ai/technologies/ocr-and-layoutlmv3 |
| Donut vs TrOCR vs TrOCR+LayoutLM | https://discuss.huggingface.co/t/which-model-should-i-choose-trocr-trocr-layoutlm-or-donut/145295 |
| Doc-Researcher — arXiv | https://arxiv.org/html/2510.21603v1 |
| Doc-Researcher — AlphaXiv | https://www.alphaxiv.org/overview/2510.21603v1 |
| Doc-Researcher — ResearchGate | https://www.researchgate.net/publication/396924643 |
| Arctic-Extract — arXiv | https://arxiv.org/html/2511.16470v1 |
| Arctic-Extract — Snowflake Blog (1) | https://www.snowflake.com/en/engineering-blog/arctic-extract-document-understanding/ |
| Arctic-Extract — Snowflake Blog (2) | https://www.snowflake.com/en/engineering-blog/arctic-extract-vision-language-document-ai/ |
| Document Intelligence Survey (SAP) — arXiv | https://arxiv.org/pdf/2510.13366 |
| Document Intelligence Survey — arXiv HTML | https://arxiv.org/html/2510.13366v1 |
| Information Extraction Design Space — arXiv v1 | https://arxiv.org/html/2502.18179v1 |
| Information Extraction Design Space — arXiv v4 | https://arxiv.org/html/2502.18179v4 |
| NER Legal Documents Serbia — arXiv | https://arxiv.org/html/2502.10582v1 |
| LLaMA fine-tuning + hallucinations NER — arXiv | https://arxiv.org/html/2506.08827v1 |
| IDP Accelerator (agéntico) — arXiv | https://arxiv.org/pdf/2602.23481 |
| OCR → IDP transición — Medium | https://medium.com/@mehrdadmohamadali7/transitioning-from-traditional-ocr-to-intelligent-document-processing-why-legacy-models-fail-in-2a1022a67b53 |
| LLMs vs OCRs 2026 — Vellum | https://www.vellum.ai/blog/document-data-extraction-llms-vs-ocrs |
| NER enterprise deep learning 2026 | https://muralimarimekala.com/2026/02/09/named-entity-recognition-deep-learning-nlp-enterprise/ |
| Comparing Top 6 OCR Models 2025 — MarkTechPost | https://www.marktechpost.com/2025/11/02/comparing-the-top-6-ocr-optical-character-recognition-models-systems-in-2025/ |

### Fine-Tuning, SLMs y Herramientas Open-Source
| Recurso | URL |
|---|---|
| Wiz — Small Language Model Secrets Detection | https://www.wiz.io/blog/small-language-model-for-secrets-detection-in-code |
| Unsloth — Fine-tune Llama-3 + Ollama | https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/tutorial-how-to-finetune-llama-3-and-use-in-ollama |
| LlamaFactory — GitHub | https://github.com/hiyouga/LlamaFactory |
| Fine-tune Llama 3.2 + Ollama + LoRA — Medium | https://medium.com/towardsdev/complete-guide-fine-tuning-llama-3-2-locally-with-ollama-and-lora-be7eb05314ff |
| Fine-tune VLMs multipage→JSON (AWS SageMaker) | https://aws.amazon.com/blogs/machine-learning/fine-tune-vlms-for-multipage-document-to-json-with-sagemaker-ai-and-swift/ |
| Amazon Nova fine-tuning structured outputs | https://aws.amazon.com/blogs/machine-learning/optimizing-document-ai-and-structured-outputs-by-fine-tuning-amazon-nova-models-and-on-demand-inference/ |
| Top 5 local LLM tools 2025 | https://devtoollab.com/blog/top-5-local-llm-tools-models-2025 |
| Fine-tuning LLaMA-3 practical guide | https://medium.com/@heyamit10/fine-tuning-llama-3-a-practical-guide-0989df65dbfc |
| LLaMA-3 fine-tuning para oncología (privacidad) | https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2024.1493716/full |
| Harnessing Open-Source LLMs for Tender NER — ACL | https://aclanthology.org/2025.ranlp-1.1.pdf |
| Exploring LLMs for Scientific IE — arXiv | https://arxiv.org/html/2512.10004v2 |
| Evaluating LLMs NER Scientific Domain — CEUR | https://ceur-ws.org/Vol-3979/paper1.pdf |

### Chunking, RAG y Procesamiento de Documentos
| Recurso | URL |
|---|---|
| Segmenting Documents with LLMs (Roots Automation) | https://www.roots.ai/blog/segmenting-documents-with-llms-and-multimodal-document-ai-part-2 |
| Best practices ingesting mixed documents (LocalLLaMA Reddit) | https://www.reddit.com/r/LocalLLaMA/comments/1r3cy0s/best_practices_for_ingesting_lots_of_mixed/ |
| Best LLM models for document processing 2025 | https://algodocs.com/best-llm-models-for-document-processing-in-2025/ |
| LLMs document automation capabilities (Parseur) | https://parseur.com/blog/llms-document-automation-capabilities-limitations |

### Mercado IDP
| Recurso | URL |
|---|---|
| AIIM IDP Survey 2025 | https://info.aiim.org/market-momentum-index-idp-survey-2025 |
| DocuWare — AIIM IDP Market Insights | https://start.docuware.com/resource/aiim-idp-market-insights |
| DocuWare — IDP 2025 Market Summary | https://start.docuware.com/blog/document-management/intelligent-document-processing-market-research |
| Global Market Insights IDP proyecciones | https://www.gminsights.com/industry-analysis/intelligent-document-processing-market |
| IDC MarketScape IDP 2025-2026 | https://my.idc.com/getdoc.jsp?containerId=US53014125 |
| Gartner Peer Insights IDP 2026 | https://www.gartner.com/reviews/market/intelligent-document-processing-solutions |
| IDP trends 2026 (Graip.AI) | https://graip.ai/blog/intelligent-document-processing-trends-2026 |
| IDP gobierno (Pingili) — ResearchGate | https://www.researchgate.net/publication/392660796_AI-driven_intelligent_document_processing_in_government_and_public_administration |
| IDP Digital Transformation Foundation | https://www.blueirisiq.com/blog/idp-as-the-foundation-of-digital-transformation |
| Top 10 IDP Platforms 2025 | https://www.reveillesoftware.com/datacap/top-10-intelligent-document-processing-idp-platforms-of-2025/ |
| Best IDP Software 2026 — Floowed | https://www.floowed.com/insights/best-intelligent-document-processing-software |
| Guide to IDP 2026 — Reddit LanguageTechnology | https://www.reddit.com/r/LanguageTechnology/comments/1r1vlc3/guide_to_intelligent_document_processing_idp_in/ |
| IDP en transformación de negocios — eBiz Latam | https://ebizlatam.com/como-el-procesamiento-inteligente-de-documentos-esta-transformando-los-negocios/ |
| IDP Procesamiento Inteligente 2026 — Medium Docupipe | https://medium.com/@docupipeai/what-is-intelligent-document-processing-the-complete-guide-for-2026-529b6cd35e69 |

### Competidores Específicos
| Recurso | URL |
|---|---|
| UiPath IDP 2025.10 release | https://www.uipath.com/blog/product-and-updates/intelligent-document-processing-2025-10-release |
| Hyperscience — LLM-first document workflows | https://www.hyperscience.ai/blog/llm-first-document-workflows-whats-real-vs-hype/ |
| OpenText IDP — IDC MarketScape | https://www.opentext.com/es/resources/intelligent-document-processing |
| Doc.AI Colombia | https://documentsolutions.co/ |
| Invoice Recognition comparison (Yeeflow) | https://blog.yeeflow.com/post/whos-the-king-of-invoice-recognition-a-full-comparison-of-5-leading-cloud-based-ai-platforms |
| Top 10 IDP Financial Services 2026 — Forage AI | https://forage.ai/blog/top-10-document-processing-solutions-for-financial-services-in-2026/ |
| Best IDP Software 2026 — VAO | https://www.vao.world/blogs/The-Best-Intelligent-Document-Processing-Software-of-2026 |
| Best Legal OCR Software 2025 — LlamaIndex | https://www.llamaindex.ai/insights/best-legal-ocr-software |
| IDP Solutions Reviews — Scry AI | https://scryai.com/blog/best-intelligent-document-processing-solutions/ |
| IDP Roboyo | https://roboyo.global/es/tecnologias/procesamiento-inteligente-de-documentos/ |
| Iron Mountain IDP | https://www.ironmountain.com/services/intelligent-document-processing-and-workflow-automation |

### Normatividad Colombiana
| Recurso | URL |
|---|---|
| RUT DIAN — Instructivo IN-CAC-0237 | https://www.dian.gov.co/atencionciudadano/LMDP/Cercania-al-Ciudadano/Asistencia-al-Usuario/Instructivos/IN-CAC-0237.pdf |
| RUT DIAN — Resolución 000110/2021 | https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000110%20de%2011-10-2021.pdf |
| Cámara de Comercio de Cali | https://www.ccc.org.co/ |
| Cámara de Comercio de Bogotá — RUE | https://linea.ccb.org.co/ccbconsultasrue/consultas/rue/consulta_empresa.aspx |
| Cámara de Comercio Aburrá Sur — Registro Mercantil | https://ccas.org.co/registros/registro-mercantil/ |
| Regulación IA en Colombia — CMS Expert Guide | https://cms.law/en/int/expert-guides/ai-regulation-scanner/colombia |
| Colombia AI bills overview — DataGuidance | https://www.dataguidance.com/opinion/colombia-overview-colombias-ai-bills |
| AI Watch Colombia — White & Case LLP | https://www.whitecase.com/insight-our-thinking/ai-watch-global-regulatory-tracker-colombia |
| GDPR compliance (referencia comparada) | https://gdpr.eu/compliance/ |

---

*Documento fuente: "Investigación de Procesamiento Inteligente de Documentos.docx" — Proyecto SinergIA Lab, Pontificia Universidad Javeriana, Especialización en Inteligencia Artificial, Ciclo 1, Marzo 2026.*

*Generado el: 3 de abril de 2026*
