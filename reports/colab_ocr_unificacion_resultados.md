# Capítulo 5c — La unificación: EasyOCR para todo el corpus

**Notebook:** [colab_ocr_unificacion.ipynb](../notebooks/colab_ocr_unificacion.ipynb)
**Builder:** [build_colab_ocr_unificacion.py](../notebooks/build_colab_ocr_unificacion.py)
**Fecha de ejecución:** 2026-04-25 (sesión 1) + 2026-04-26 (sesión 2 con segunda cuenta Google)
**Fase CRISP-DM++:** 2.1.5 — Re-unificación OCR
**Plan operativo:** [PLAN_OCR_COLAB.md](../PLAN_OCR_COLAB.md) · [PLAN_MODELADO_CRISPDM.md §2.1.5](../PLAN_MODELADO_CRISPDM.md)

---

## 1. El contexto — el dilema de la paridad train-inference

Los notebooks anteriores (nb05 + nb05b) consolidaron el corpus con **dos motores distintos**:
- **EasyOCR** sobre 1,678 páginas de los 412 documentos escaneados (CER ~0.28)
- **PyMuPDF** sobre 11,576 páginas de los 548 documentos digitales (CER ~0.0)

Ese diseño híbrido se justificó en `OCR_BENCHMARK.md §2.6`: PyMuPDF es exacto y ~8,300× más rápido para documentos digitales que ya tienen texto embebido. Era la decisión técnicamente óptima por calidad y costo.

**Pero introduce un problema metodológico no trivial:** los modelos de Clasificación y NER aprenden sobre datos heterogéneos en distribución de errores. En producción, si llegan documentos sin clasificar previamente y se les aplica un solo motor (EasyOCR como salvavidas universal), el modelo verá texto con CER ~0.28 mientras el 87% del entrenamiento fue texto perfecto. Esto se conoce como **distribution shift train-inference** y degrada la generalización.

## 2. La hipótesis y la decisión

> **Decisión arquitectural (2026-04-21):** unificar todo el corpus bajo EasyOCR (escaneados + digitales) aceptando voluntariamente la degradación de calidad de los digitales (CER 0.0 → ~0.28) a cambio de uniformidad estadística del dataset.

Esta decisión tiene **tres consecuencias colaterales positivas** para Fase 3:

1. **Resuelve el gap de bboxes** para C-3 LayoutLMv3: los `bboxes_json` quedan poblados al 100% (antes solo el 12.7%).
2. **Permite la elección racional del modelo en producción**: el sistema en producción puede aplicar EasyOCR a TODOS los inputs sin necesidad de un selector previo de tipo de archivo.
3. **Simplifica el pipeline** de inferencia: un solo motor, un solo path crítico, una sola fuente de errores OCR.

**Costo aceptado:** ~7 horas de cómputo en GPU + degradación intencional de la calidad de 11,576 páginas que estaban perfectas.

## 3. El método — Colab Free GPU + cache MD5

### 3.1 Por qué Colab y no local

El equipo del usuario (AMD Ryzen 5 4500U, 8 GB RAM, GPU AMD integrada sin CUDA) tomaría ~9-12 días continuos para esta corrida. Colab Free (Tesla T4 16 GB CUDA) la hace en ~6 h. La cuenta del usuario para Colab/Drive es `mateopolanco2@gmail.com`.

### 3.2 Decisiones operativas pre-corrida (2026-04-21)

Tres ajustes de scope antes de ejecutar:

1. **Excluir clase Otros** (9 docs heterogéneos sin patrón) → clases finales del clasificador: 4
2. **Límite de 10 páginas por documento** → ahorra 60% del cómputo (justificación: 79% del corpus es ≤10 págs naturalmente; BETO/LayoutLMv3 truncan a 512 tokens; TF-IDF tiene suficiente con 10 págs)
3. **Eliminar 2 RUPs mal clasificados como RUT** (`10. REGISTRO UNICO DE PROPONENTES.pdf` 1,331 págs y `Registro Unico de Propnentes (RUP).pdf` 606 págs) → movidos a `data/raw/_quarantine_misclassified/`

Volumen final a procesar: **747 docs únicos / ~3,821 páginas** (pendientes), preservando los 1,678 págs ya en EasyOCR de nb05.

### 3.3 Arquitectura del notebook — diseño retomable

El notebook implementa **cache MD5 por página** idéntico a nb05/05b:

1. Lee `corpus_ocr.csv` actual de Drive
2. Construye `cached_pages = set((md5, page_num))` filtrando solo `engine='easyocr'`
3. En cada iteración del loop, antes de OCR'ar una página, verifica si ya está en cache → si sí, skip
4. Checkpoint cada 50 documentos: append del buffer al CSV en Drive

Esto permite que **si la sesión Colab se cae, basta re-ejecutar `Run All` para retomar desde el último checkpoint sin perder trabajo.**

## 4. Los resultados — partido en dos sesiones por cuota Colab

### 4.1 Sesión 1 (2026-04-25) — interrumpida por límite GPU

```
Pre-cleanup: eliminadas 11,576 filas pymupdf de docs a re-OCR
Cache inicial: 1,678 pares (los escaneados de nb05)

Progreso al colapso: 67% (500/747 docs) en 5h 8min
Última checkpoint exitosa: docs=450 / corpus=4,584 filas

Pace observada: ~25-37 s/doc (estable)
0 errores fatales | ~24 MuPDF warnings de PDFs corruptos (no detuvieron el proceso)
```

Colab Free agotó la cuota de GPU para esta cuenta tras ~5h continuas. La sesión se desconectó.

### 4.2 Sesión 2 (2026-04-26) — retomada con segunda cuenta

**Solución innovadora del usuario:** dado que las cuotas de Colab Free son **por cuenta**, abrir la sesión con una segunda Gmail. Setup:

1. Desde `mateopolanco2@gmail.com`: compartir carpeta `SinergiaLab/` con la segunda Gmail (rol Editor)
2. Desde la segunda cuenta: `Drive web → Compartido conmigo → SinergiaLab → Organizar → Agregar acceso directo a Drive` → ubicar en `MyDrive/datasets/`
3. Abrir Colab con la segunda cuenta, subir el mismo notebook, Run All

El cache MD5 vio inmediatamente las 4,584 filas de la sesión 1 y solo procesó los 297 docs faltantes.

```
Cache inicial: 4,584 pares (md5, page_num) ← rescate completo de sesión 1
Pre-cleanup esta sesión: 0 filas a borrar (ya limpio)

Output final:
  === DONE en 81.2 min ===
    Docs procesados nuevos    : 277
    Docs skip (ya en cache)   : 450  ← rescatados de sesión 1
    Docs no encontrados       : 20   ← mojibake en filenames
    Páginas procesadas        : 767
    Errores                   : 0
    Filas finales en corpus   : 5,351
```

### 4.3 Estado final del corpus consolidado

```
corpus_ocr.csv (137 MB)
─────────────────────────────────
Filas totales : 5,351
Docs únicos   : 1,134
Engine        : 100% easyocr  ← objetivo de uniformidad cumplido
% bboxes      : 99.87%        ← gap C-3 LayoutLMv3 resuelto
Errores       : 0

Distribución por clase canónica:
  Cédula         537 (47.4%)
  RUT            212 (18.7%)
  Póliza         198 (17.5%)
  CamaraComercio 187 (16.5%)

Distribución páginas/doc:
  1 página      519 docs (mayoría cédulas)
  2-5 págs      233 docs
  6-9 págs      171 docs
  10 págs       172 docs (al límite)
  >10 págs       39 docs (escaneados de nb05 preservados sin límite)
```

## 5. Lectura crítica

### 5.1 La unificación se logró sin pérdida de información previa

Los 1,678 págs de los 412 escaneados procesados en nb05 (semana pasada) se preservaron intactos vía cache MD5. Cero re-procesamiento, cero modificación. **El trabajo previo no se perdió.**

### 5.2 La degradación intencional es real pero justificada

El corpus pasó de 13,254 filas a 5,351 filas. Este "shrink" se compone de:

- 9 docs Otros excluidos (~3,826 filas)
- 2 RUPs mal clasificados eliminados (1,937 filas)
- Truncamiento a 10 págs/doc en digitales largos (~2,140 filas)

→ Ninguna de estas reducciones es pérdida — son decisiones deliberadas de scope que mejoran la calidad del dataset de entrenamiento.

### 5.3 La estrategia "segunda cuenta" como hallazgo operativo

La interrupción por cuota Colab Free podría haber paralizado el proyecto 12-24 horas. La idea del usuario de **usar una segunda cuenta + compartir Drive** convirtió un bloqueo en una continuación de 5 minutos de setup. Esta táctica queda documentada en `memory/colab_drive_setup.md` como referencia para futuras corridas pesadas.

### 5.4 La distribución de clases es desbalanceada (47% Cédula)

Cédula domina con 537 docs (47.4%). Esto puede sesgar los clasificadores naive. Para mitigar:

- nb10 (C-1 TF-IDF) usa `class_weight='balanced'` en LogisticRegression
- nb11 (C-2 BETO) y nb12 (C-3 LayoutLMv3) usan stratified split + métrica macro-F1 (no weighted) para evaluación
- En cualquier caso, la distribución se mantiene proporcional en train/val/test gracias a stratify

## 6. Anomalías

### 6.1 Folder names con mojibake (heredado de quality_report)

```
folder              docs únicos
CAMARA DE CIO       16
Cámara de Comercio 171
CEDULA              518
Cédula               19
POLIZA               59
Póliza              139
RUT                 188
rut                  24
```

8 valores en `folder` para 4 clases reales. **Manejado en nb10/nb11/nb12** vía función `normalizar_clase()` que mapea por sub-string lowercase. Cero impacto sobre el clasificador.

### 6.2 24 MuPDF warnings de PDFs corruptos

```
MuPDF error: format error: object is not a stream    (×23)
MuPDF error: format error: No common ancestor...      (×1)
```

Vienen de los PDFs problemáticos identificados en el script local `generar_imagenes_pag1_faltantes.py` (`13. GARANTIA DE SERIEDAD_1.pdf`, `_Camara de comercio Centro Oriente 14 enero.pdf`, etc.). PyMuPDF imprime stderr pero **no levanta excepción** → el OCR continúa sobre la imagen parcial. Esto se ve reflejado en las **7 páginas con texto vacío** y **26 páginas con texto<50 chars** del corpus final.

**Decisión:** dejar pasar. Son <0.5% del corpus, no afectan el entrenamiento, y eliminarlos manualmente requeriría inspección humana caso por caso.

### 6.3 20 docs no encontrados durante el OCR

Filenames con mojibake (caracteres `Ã±`, `????`, etc.) que el script de upload no pudo matchear contra los PDFs del Drive. Ya se documentó en `scripts/preparar_upload_drive.py` (logueados al final de la corrida).

**Implicación:** el corpus final tiene 1,134 docs en lugar de los 1,154 esperados (1,134 + 20). Aceptable.

### 6.4 39 docs con >10 páginas en el corpus final

Estos son los **escaneados originales de nb05** (engine=easyocr desde la semana pasada). El límite de 10 págs solo aplicaba al re-procesamiento de los 747 pendientes; los docs en cache se preservaron tal cual. **No es bug.** El doc más largo tiene 243 págs (un escaneado de Cámara de Comercio).

Para nb10 (TF-IDF) este desbalance es irrelevante porque la vectorización normaliza por longitud. Para nb11 (BETO) y nb12 (LayoutLMv3) ambos truncan a 512 tokens.

## 7. Qué sigue

Esta fase **desbloquea Fase 3 (Modelado de Clasificación):**

1. **nb10 — C-1 TF-IDF + LogReg** (CPU local, ~3 segundos training) → ✅ ejecutado, ver [reports/nb10_resultados.md](nb10_resultados.md)
2. **nb11 — C-2 BETO fine-tuned** (Colab T4, ~30 min) → pendiente
3. **nb12 — C-3 LayoutLMv3** (Colab T4, ~60-90 min) → pendiente
4. **Reporte comparativo 3-vías** (macro-F1, latencia, costo, interpretabilidad) → pendiente

**Una vez cerrada Fase 3 Clasificación**, se retoma Fase 2.2 (Anotaciones NER en Label Studio — actualmente parqueada) seguido de Fase 3.1 NER.

## 8. Referencias

- [PLAN_OCR_COLAB.md](../PLAN_OCR_COLAB.md) — checklist operativo del re-OCR
- [PLAN_MODELADO_CRISPDM.md §2.1.5](../PLAN_MODELADO_CRISPDM.md) — decisión arquitectural integrada al plan maestro
- [memory/ocr_unification_decision.md](https://github.com) — memoria persistente del proyecto con la decisión y su porqué
- [memory/colab_drive_setup.md](https://github.com) — paths y cuenta de Drive del proyecto
- [_nb_outputs/colab_ocr_unificacion.txt](../_nb_outputs/colab_ocr_unificacion.txt) — outputs literales de las dos sesiones
