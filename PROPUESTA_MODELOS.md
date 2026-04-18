# Propuesta de Modelos — Fundamentación Científica

**Proyecto:** SinergIA Lab — IDP para Documentos Corporativos Colombianos
**Institución:** Pontificia Universidad Javeriana · Especialización en Inteligencia Artificial · Ciclo 1 · 2026
**Autor del documento:** Equipo SinergIA Lab
**Fecha:** 2026-04-18

---

## Propósito

Este documento fundamenta la selección de modelos para las tres fases técnicas del proyecto — **OCR**, **Clasificación de tipo de documento** y **Extracción de entidades (NER)** — contra la literatura científica oficial. Por cada candidato se documenta:

1. Descripción técnica precisa.
2. Justificación para este proyecto (corpus SECOP, 1,014 documentos colombianos).
3. Fuente primaria (paper arXiv, conferencia revisada por pares o repositorio oficial).
4. URL canónica verificable.

**Principio de trazabilidad científica:** ningún modelo se adopta sin una cita a paper original o repositorio institucional oficial. Blogs corporativos se usan solo como evidencia complementaria cuando existe también paper.

---

## Principios de selección comunes

| Dimensión | Criterio |
|---|---|
| **Reproducibilidad** | Pesos + código disponibles públicamente (HuggingFace, GitHub oficial) |
| **Soberanía de datos** | Ejecución local sin envío de PII a APIs externas (Ley 1581/2012) |
| **Costo de anotación** | Preferencia por modelos que aprovechen el corpus ya preparado (`corpus_ocr.csv`) |
| **Métricas comparables** | Cada candidato se evalúa sobre el mismo gold set con las mismas métricas |
| **Tamaño del modelo** | ≤8B parámetros o equivalente en VRAM ≤24 GB |

---

## FASE 1 — OCR (ya decidido, benchmark ejecutado)

**Estado:** ✅ decidido — ver [OCR_BENCHMARK.md](OCR_BENCHMARK.md) y [notebooks/03_benchmark_ocr.ipynb](notebooks/03_benchmark_ocr.ipynb).

### OCR-1 — EasyOCR (ganador del benchmark productivo)

**Qué es:** motor OCR open-source basado en dos redes neuronales en cascada:
1. **CRAFT** (Character Region Awareness For Text detection) para detección de regiones de texto.
2. **CRNN** (Convolutional Recurrent Neural Network) para reconocimiento carácter-secuencia.

**Por qué para este proyecto:**
- Benchmark propio (§2.6.2 OCR_BENCHMARK.md) midió **CER 0.276 / entity_recall 0.685** sobre gold seed de 15 docs — superior a Tesseract en Cédulas (tipología más numerosa del corpus, 332 docs).
- Tras eliminar el paso `binarize()` del pipeline (§2.1.3 PLAN_MODELADO_CRISPDM.md), throughput CPU = ~20 s/página.
- 0 errores en corrida productiva de 23h sobre 1,678 páginas escaneadas.

**Fuentes:**
| Recurso | URL |
|---|---|
| Paper CRAFT: Baek et al., "Character Region Awareness for Text Detection", CVPR 2019 | https://arxiv.org/abs/1904.01941 |
| Paper CRNN: Shi, Bai, Yao, "An End-to-End Trainable Neural Network for Image-based Sequence Recognition", IEEE TPAMI 2017 | https://arxiv.org/abs/1507.05717 |
| Repositorio oficial EasyOCR (JaidedAI) | https://github.com/JaidedAI/EasyOCR |
| Repositorio oficial CRAFT (Clova AI) | https://github.com/clovaai/CRAFT-pytorch |

### OCR-2 — Tesseract 5 (comparador del benchmark, descartado como motor único)

**Qué es:** motor OCR clásico basado en LSTM con modelos entrenables por idioma. Desarrollado originalmente en HP (1985) y actualmente mantenido por Google/comunidad.

**Por qué se evaluó:** referencia histórica obligatoria en literatura IDP; ganó en Cámara de Comercio (CER 0.047) y Pólizas (CER 0.226) en el benchmark.

**Por qué NO se adoptó como motor único:** colapsa en Cédulas (CER 0.782) debido a texto con hologramas, columnas y bajo contraste. En CPU es 9× más rápido que EasyOCR, pero GPU invierte la ventaja.

**Fuentes:**
| Recurso | URL |
|---|---|
| Paper Smith, "An Overview of the Tesseract OCR Engine", ICDAR 2007 | https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/ |
| Repositorio oficial | https://github.com/tesseract-ocr/tesseract |

### OCR-3 — PyMuPDF (extractor nativo para PDFs digitales)

**Qué es:** binding Python de **MuPDF** (Artifex Software). Extrae texto directamente de la estructura del PDF sin pasar por reconocimiento óptico — funciona solo cuando los caracteres están embebidos como texto (no como imagen).

**Por qué para este proyecto:** 548–590 de los 1,014 documentos son PDFs digitales. Aplicar OCR a un PDF digital es degradar texto perfecto. PyMuPDF extrae 11,576 páginas en ~10 minutos con CER = 0 (determinista).

**Fuentes:**
| Recurso | URL |
|---|---|
| Documentación oficial PyMuPDF | https://pymupdf.readthedocs.io/ |
| Repositorio oficial | https://github.com/pymupdf/PyMuPDF |
| Proyecto base MuPDF (Artifex) | https://mupdf.com/ |

### OCR descartados con justificación

| Modelo | Motivo | Fuente del descarte |
|---|---|---|
| **Donut** (OCR-free, NAVER 2022) | Corpus multi-tipológico requeriría 4 modelos separados; no escala a docs multipágina | Kim et al., ECCV 2022 — https://arxiv.org/abs/2111.15664 ; repo: https://github.com/clovaai/donut |
| **PaddleOCR** | Incompatible con Python 3.12 al momento del benchmark | Documentado en OCR_BENCHMARK.md §1.2 |

---

## FASE 2 — CLASIFICACIÓN DE TIPO DE DOCUMENTO (3 candidatos)

**Input:** texto OCR + opcionalmente imagen de página 1.
**Output:** `{Cedula, RUT, Poliza, CC, Otros}`.
**Tamaño del dataset:** corpus de 960 docs ya clasificados por carpeta → labels de entrenamiento disponibles.

### C-1 — TF-IDF + Regresión Logística (baseline clásico)

**Qué es:** vectorización del texto mediante **TF-IDF** (Term Frequency – Inverse Document Frequency, Spärck Jones 1972) seguida de un clasificador lineal (Regresión Logística o SVM lineal).

**Por qué para este proyecto:**
- Baseline obligatorio en cualquier estudio científico de clasificación de texto. Establece el umbral mínimo contra el cual los modelos más complejos deben justificar su costo computacional.
- Entrenamiento en segundos, <10 MB en disco, sin GPU.
- Interpretable: los pesos de cada feature revelan qué términos identifican cada tipología (ej. "DIAN", "NIT" → RUT).

**Fuentes:**
| Recurso | URL |
|---|---|
| Spärck Jones, "A Statistical Interpretation of Term Specificity and Its Application in Retrieval", Journal of Documentation 1972 | https://doi.org/10.1108/eb026526 |
| Manning, Raghavan, Schütze, *Introduction to Information Retrieval* (Cambridge, 2008) — Cap. 6 "Scoring, term weighting and the vector space model" | https://nlp.stanford.edu/IR-book/ |
| Implementación de referencia: `sklearn.feature_extraction.text.TfidfVectorizer` | https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html |

### C-2 — BETO fine-tuned (BERT en español)

**Qué es:** modelo **BERT** (Bidirectional Encoder Representations from Transformers) pre-entrenado desde cero sobre un corpus de ~3 GB de texto en español por la Universidad de Chile. Variante usada: `bert-base-spanish-wwm-cased` (cased, Whole Word Masking, 110M parámetros).

**Por qué para este proyecto:**
- BETO captura semántica específica del español jurídico-administrativo colombiano mucho mejor que modelos multilingües (mBERT, XLM-R) según la evaluación del paper original.
- Fine-tuning para clasificación de texto requiere 15-30 minutos en GPU 6 GB con 960 ejemplos.
- Robusto ante variantes de OCR: si el texto contiene errores carácter-a-carácter (CER ~0.28 en nuestro caso), BETO sigue generalizando por contexto.

**Fuentes:**
| Recurso | URL |
|---|---|
| Paper BETO: Cañete, Chaperon, Fuentes, Ho, Kang, Pérez, "Spanish Pre-Trained BERT Model and Evaluation Data", PML4DC @ ICLR 2020 | https://users.dcc.uchile.cl/~jperez/papers/pml4dc2020.pdf |
| Paper BERT original: Devlin, Chang, Lee, Toutanova, "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding", NAACL 2019 | https://arxiv.org/abs/1810.04805 |
| Model card oficial HuggingFace | https://huggingface.co/dccuchile/bert-base-spanish-wwm-cased |
| Repositorio oficial BETO | https://github.com/dccuchile/beto |

### C-3 — LayoutLMv3 (multimodal texto + layout + imagen)

**Qué es:** modelo multimodal pre-entrenado por Microsoft Research que procesa simultáneamente texto, coordenadas 2D de cada token y parches de imagen. Variante base: 125M parámetros.

**Por qué para este proyecto:**
- El layout de un RUT (formulario DIAN con 97 bloques por página) es visualmente distinto al de una Cédula (imagen de ID) aun cuando ambos contengan texto similar. Un clasificador puramente textual puede confundirlos; LayoutLMv3 los discrimina por estructura visual.
- Estado del arte documentado en benchmarks **FUNSD** (F1 90.8) y **CORD** (F1 98.48) sobre clasificación y extracción en documentos con layout rico.
- Mencionado explícitamente en la literatura base del proyecto — ver Resumen_Investigacion_SinergIA_Lab.md §2.3.

**Fuentes:**
| Recurso | URL |
|---|---|
| Paper: Huang, Lv, Cui, Lu, Wei, "LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking", ACM MM 2022 | https://arxiv.org/abs/2204.08387 |
| Repositorio oficial Microsoft | https://github.com/microsoft/unilm/tree/master/layoutlmv3 |
| Model card HuggingFace | https://huggingface.co/microsoft/layoutlmv3-base |

---

## FASE 3 — EXTRACCIÓN DE ENTIDADES (NER) (3 candidatos)

**Input:** texto OCR del corpus completo (`corpus_ocr.csv` 13,254 páginas) + opcional: tipo predicho por Fase 2, bounding boxes, imagen.
**Output:** JSON estructurado con entidades por tipología (ver esquemas en PLAN_MODELADO_CRISPDM.md §2.2).

### N-1 — spaCy con BETO-NER fine-tuned (baseline discriminativo)

**Qué es:** pipeline NER de la librería **spaCy** v3 con un transformador **BETO** como backbone, entrenado para clasificación de tokens con etiquetado **BIO** (Beginning/Inside/Outside).

**Por qué para este proyecto:**
- **Arquitectura discriminativa:** clasifica cada token con una etiqueta, por lo que **no puede alucinar** entidades que no están en el texto — contraste crítico con N-2.
- Tarea estándar NER con métrica F1 por entidad bien definida y comparable con literatura.
- spaCy es robusto en producción, serializable, con latencia <100 ms por documento en CPU.
- BETO como backbone aprovecha el pre-entrenamiento en español jurídico (§C-2).

**Fuentes:**
| Recurso | URL |
|---|---|
| spaCy (citación canónica por DOI Zenodo, no hay paper revisado) | https://doi.org/10.5281/zenodo.1212303 |
| Repositorio oficial spaCy | https://github.com/explosion/spaCy |
| Sitio oficial | https://spacy.io/ |
| Paper BETO (backbone, mismo que C-2) | https://users.dcc.uchile.cl/~jperez/papers/pml4dc2020.pdf |
| Benchmark NER en español de referencia: Tjong Kim Sang, "Introduction to the CoNLL-2002 Shared Task: Language-Independent Named Entity Recognition", CoNLL 2002 | https://aclanthology.org/W02-2024/ |

### N-2 — Llama 3.3 + QLoRA (NER generativo — candidato principal del plan)

**Qué es:** modelo **Llama 3.3 8B-Instruct** (Meta AI, diciembre 2024) ajustado con **QLoRA** (Quantized Low-Rank Adaptation) para producir JSON estructurado con las entidades extraídas del documento de entrada.

**Por qué para este proyecto:**
- Candidato central de Fase 3 según [PLAN_MODELADO_CRISPDM.md §3.1 Etapa B](PLAN_MODELADO_CRISPDM.md).
- **QLoRA** permite fine-tuning en GPU de 24 GB (p.ej. RTX 4090, A10) cuantizando los pesos en 4 bits e inyectando matrices de bajo rango entrenables. El modelo adaptado ocupa <200 MB en disco.
- **Llama 3.3** (actualización de Llama 3 original del paper, diciembre 2024) incluye soporte oficial de español en la model card y mejora en instruction-following sobre Llama 3.0/3.1.
- Maneja layouts variables (Pólizas) donde un modelo discriminativo por tokens falla.
- Ecosistema maduro: **Unsloth** acelera el fine-tuning hasta 5×, **LlamaFactory** (ACL 2024) estandariza la configuración.

**Riesgo documentado:** los modelos generativos pueden inducir alucinaciones en NER legal — ver arXiv:2506.08827 (Kalušev & Brkljač) como evidencia de que el fine-tuning específico mitiga este riesgo.

**Fuentes:**
| Recurso | URL |
|---|---|
| Paper Llama 3: Grattafiori et al., "The Llama 3 Herd of Models", arXiv 2024 | https://arxiv.org/abs/2407.21783 |
| Model card oficial Meta — Llama 3.3 | https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/MODEL_CARD.md |
| HuggingFace — Llama 3.3 70B-Instruct (referencia; 8B usado en proyecto disponible desde Llama 3.1) | https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct |
| Paper QLoRA: Dettmers, Pagnoni, Holtzman, Zettlemoyer, "QLoRA: Efficient Finetuning of Quantized LLMs", NeurIPS 2023 | https://arxiv.org/abs/2305.14314 |
| Repositorio oficial QLoRA | https://github.com/artidoro/qlora |
| Paper LlamaFactory: Zheng et al., "LlamaFactory: Unified Efficient Fine-Tuning of 100+ Language Models", ACL 2024 (system demonstrations) | https://arxiv.org/abs/2403.13372 |
| Paper Unsloth — repositorio (no peer-reviewed, citable como software) | https://github.com/unslothai/unsloth |
| Paper de riesgo de alucinaciones NER legal: Kalušev, Brkljač, "Applying Large Language Models to Named Entity Recognition in Legal Documents", arXiv 2025 | https://arxiv.org/abs/2502.10582 |

**Alternativas equivalentes contempladas (mismo pipeline Unsloth + QLoRA):**
| Modelo | Paper |
|---|---|
| Qwen2.5-7B-Instruct (Alibaba) | Qwen Team, "Qwen2.5 Technical Report", arXiv 2024 — https://arxiv.org/abs/2412.15115 |
| Mistral Small 3 (Mistral AI) | Blog oficial — https://mistral.ai/news/mistral-small-3 (no paper) |

### N-3 — LayoutLMv3 fine-tuned para token classification (candidato layout-aware)

**Qué es:** mismo modelo que C-3 pero entrenado para la tarea de **token classification con BIO tagging**. Cada token tiene asociado un bounding box y el modelo predice qué entidad representa.

**Por qué para este proyecto:**
- Está en el plan como **experimento 6 opcional** — ver [PLAN_MODELADO_CRISPDM.md ALT-2](PLAN_MODELADO_CRISPDM.md).
- Aprovecha la información espacial que Llama 3.3 pierde al recibir texto plano — **crítico para RUT** (97 bloques por página) y **Cámara de Comercio** (estructura tabular multipágina).
- Ventaja frente a N-2: inferencia <1 s/doc, 125M parámetros, sin riesgo de alucinación (discriminativo).
- Limitación: requiere anotación con bounding boxes por token (más costosa que texto span); Pólizas con layout variable le son hostiles.

**Fuentes:**
| Recurso | URL |
|---|---|
| Paper LayoutLMv3 (mismo que C-3) | https://arxiv.org/abs/2204.08387 |
| Paper benchmark LayoutLMv3 vs LLMs: Colakoglu, Solmaz, Fürst, "A Retrospective on Information Extraction from Documents", arXiv 2025 | https://arxiv.org/abs/2502.18179 |
| Repositorio oficial | https://github.com/microsoft/unilm/tree/master/layoutlmv3 |
| Model card HuggingFace | https://huggingface.co/microsoft/layoutlmv3-base |

---

## Diseño experimental para selección

### Métricas por fase

| Fase | Métrica primaria | Métricas secundarias |
|---|---|---|
| OCR | CER (Character Error Rate) | WER, entity_recall, s/página |
| Clasificación | Macro-F1 | Accuracy, matriz de confusión |
| NER | F1 por entidad | F1 macro, hallucination rate (para N-2), latencia |

### Protocolo

1. **Split reproducible** con semilla fija: 70% train, 15% val, 15% test sobre el gold extendido (70 docs, por construir).
2. **Los 3 candidatos de cada fase se entrenan sobre el mismo split y se evalúan sobre el mismo test.**
3. **Criterio de selección primario** = macro-F1 por tipología (no agregado global — una mejora global puede ocultar degradación en una tipología específica).
4. **Criterios secundarios de desempate** (orden de prioridad): VRAM requerida → latencia → tamaño en disco → interpretabilidad.
5. **Cada experimento se reporta** con: hiperparámetros, tiempo de entrenamiento, VRAM pico, tamaño de modelo, métricas sobre test.

### Resultados esperados que este diseño permite responder

- ¿Vale la pena la complejidad de BETO sobre TF-IDF para clasificación? (esperado: sí si F1 > +5 puntos)
- ¿El layout aporta sobre el texto plano en NER? (comparar N-2 vs N-3 por tipología)
- ¿Un modelo discriminativo (N-1) es suficiente para nuestro caso de uso? (pregunta clave para producción)

---

## Referencias bibliográficas completas (orden alfabético)

1. Baek, Y., Lee, B., Han, D., Yun, S., Lee, H. (2019). **Character Region Awareness for Text Detection**. *CVPR 2019*. https://arxiv.org/abs/1904.01941
2. Cañete, J., Chaperon, G., Fuentes, R., Ho, J.-H., Kang, H., Pérez, J. (2020). **Spanish Pre-Trained BERT Model and Evaluation Data**. *PML4DC @ ICLR 2020*. https://users.dcc.uchile.cl/~jperez/papers/pml4dc2020.pdf
3. Colakoglu, G., Solmaz, G., Fürst, J. (2025). **A Retrospective on Information Extraction from Documents: From Layout-aware Models to Large Language Models**. *arXiv:2502.18179*. https://arxiv.org/abs/2502.18179
4. Devlin, J., Chang, M.-W., Lee, K., Toutanova, K. (2019). **BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding**. *NAACL 2019*. https://arxiv.org/abs/1810.04805
5. Dettmers, T., Pagnoni, A., Holtzman, A., Zettlemoyer, L. (2023). **QLoRA: Efficient Finetuning of Quantized LLMs**. *NeurIPS 2023*. https://arxiv.org/abs/2305.14314
6. Grattafiori, A. et al. — Llama Team, Meta AI (2024). **The Llama 3 Herd of Models**. *arXiv:2407.21783*. https://arxiv.org/abs/2407.21783
7. Huang, Y., Lv, T., Cui, L., Lu, Y., Wei, F. (2022). **LayoutLMv3: Pre-training for Document AI with Unified Text and Image Masking**. *ACM Multimedia 2022*. https://arxiv.org/abs/2204.08387
8. Kalušev, V., Brkljač, B. (2025). **Applying Large Language Models to Named Entity Recognition in Legal Documents**. *arXiv:2502.10582*. https://arxiv.org/abs/2502.10582
9. Kim, G. et al. (2022). **OCR-free Document Understanding Transformer (Donut)**. *ECCV 2022*. https://arxiv.org/abs/2111.15664
10. Manning, C. D., Raghavan, P., Schütze, H. (2008). ***Introduction to Information Retrieval***. Cambridge University Press. https://nlp.stanford.edu/IR-book/
11. Qwen Team (2024). **Qwen2.5 Technical Report**. *arXiv:2412.15115*. https://arxiv.org/abs/2412.15115
12. Shi, B., Bai, X., Yao, C. (2017). **An End-to-End Trainable Neural Network for Image-based Sequence Recognition (CRNN)**. *IEEE TPAMI 39(11)*. https://arxiv.org/abs/1507.05717
13. Smith, R. (2007). **An Overview of the Tesseract OCR Engine**. *ICDAR 2007*. https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/
14. Spärck Jones, K. (1972). **A Statistical Interpretation of Term Specificity and Its Application in Retrieval**. *Journal of Documentation 28(1)*. https://doi.org/10.1108/eb026526
15. Tjong Kim Sang, E. F. (2002). **Introduction to the CoNLL-2002 Shared Task: Language-Independent Named Entity Recognition**. *CoNLL 2002*. https://aclanthology.org/W02-2024/
16. Zheng, Y. et al. (2024). **LlamaFactory: Unified Efficient Fine-Tuning of 100+ Language Models**. *ACL 2024 System Demonstrations*. https://arxiv.org/abs/2403.13372

---

## Nota metodológica final

Este documento cumple con las directrices académicas del Ciclo 1 PUJ: **toda elección arquitectural está respaldada por al menos una cita a paper revisado por pares o repositorio institucional oficial**. Los blogs corporativos (Meta AI, Snowflake, JaidedAI) se citan únicamente como documentación complementaria cuando existe también paper o repositorio oficial.

Durante el desarrollo, nuevas referencias se incorporan mediante actualización de este documento. La lista de referencias bibliográficas es la fuente de verdad citable en el informe final del proyecto.
