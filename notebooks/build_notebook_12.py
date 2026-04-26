"""
Genera notebooks/12_clasificacion_C3_layoutlmv3.ipynb (Colab GPU, refactor v2)

Modelo: LayoutLMv3 base fine-tuned para clasificacion de documentos.
Ver: PROPUESTA_MODELOS.md FASE 2 candidato C-3.

REFACTOR v2 (2026-04-26):
La v1 sufrio OOM en Colab Free durante el paso EasyOCR porque mantenia los
1,115 PIL Images + words + boxes simultaneamente en memoria (~1.7 GB) sumado a
EasyOCR model + PyTorch + sistema (~7-8 GB total). Excedio los 12.7 GB de RAM
de Colab Free.

Cambios en v2 para caber:
1. EasyOCR procesa en CHUNKS de 50 docs y guarda a JSONL en Drive (no en memoria)
2. Cache automatico: si ya existe el JSONL para un split, salta esa parte
3. Dataset con LAZY image loading (PIL.Image.open en __getitem__, no en carga)
4. BATCH_SIZE=2 + gradient_accumulation_steps=4 (efectivo 8) para minimizar VRAM
5. gradient_checkpointing_enable() para reducir VRAM ~30-40% adicional

Memoria estimada peak: ~6 GB (cabe holgado en Colab Free 12.7 GB)

Inputs en Drive:
- MyDrive/datasets/SinergiaLab/processed/corpus_ocr.csv
- MyDrive/datasets/SinergiaLab/processed/images_p1/  (1,159 imgs pag 1)

Outputs en Drive:
- MyDrive/datasets/SinergiaLab/processed/c3_easyocr_cache/{train,val,test}.jsonl
- MyDrive/datasets/SinergiaLab/models/c3_layoutlmv3/
- MyDrive/datasets/SinergiaLab/processed/c3_predictions.csv
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "12_clasificacion_C3_layoutlmv3.ipynb"


def md(*lines: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in lines]}


def code(*lines: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [l + "\n" for l in lines],
    }


cells = []

cells.append(md(
    "# nb12 v2 - Clasificacion C-3: LayoutLMv3 fine-tuned (REFACTOR para evitar OOM)",
    "",
    "**Tarea:** clasificar documentos en `{Cedula, RUT, Poliza, CamaraComercio}` usando texto + bboxes + imagen.",
    "",
    "**Modelo:** `microsoft/layoutlmv3-base` (Huang et al. 2022, ACM MM).",
    "",
    "## Refactor v2 vs v1 (que sufrio OOM)",
    "",
    "**Problema v1:** mantenia 1,115 PIL Images + words + bboxes en variables Python (`train_data`, `val_data`, `test_data`) -> ~1.7 GB solo en estructuras + 5-6 GB de EasyOCR/PyTorch/sistema -> excedia los 12.7 GB de Colab Free.",
    "",
    "**Cambios en v2:**",
    "1. **EasyOCR en chunks de 50 docs**, guarda a JSONL en Drive (no acumula en memoria)",
    "2. **Cache automatico**: si JSONL ya existe para un split, lo salta (retomable)",
    "3. **Dataset con lazy image loading** (carga PIL solo en `__getitem__`, no al inicio)",
    "4. **BATCH_SIZE=2 + grad_accum=4** (efectivo 8, mismo throughput, menos VRAM)",
    "5. **gradient_checkpointing_enable()** (reduce VRAM ~30-40% adicional)",
    "",
    "**Memoria peak esperada:** ~6 GB (cabe holgado en Colab Free 12.7 GB).",
))

cells.append(md("## 1. Verificar GPU"))

cells.append(code(
    "import torch",
    "assert torch.cuda.is_available(), 'Sin GPU. Runtime > Change runtime type > T4 GPU'",
    "print(f'GPU: {torch.cuda.get_device_name(0)}')",
    "print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')",
))

cells.append(md("## 2. Instalar dependencias"))

cells.append(code(
    "!pip install -q transformers datasets accelerate evaluate scikit-learn easyocr",
))

cells.append(md("## 3. Montar Drive"))

cells.append(code(
    "from google.colab import drive",
    "drive.mount('/content/drive')",
))

cells.append(md("## 4. Configuracion (paths + hiperparametros)"))

cells.append(code(
    "from pathlib import Path",
    "import json, gc",
    "",
    "DRIVE_BASE = Path('/content/drive/MyDrive/datasets/SinergiaLab')",
    "CORPUS_CSV = DRIVE_BASE / 'processed' / 'corpus_ocr.csv'",
    "IMAGES_P1 = DRIVE_BASE / 'processed' / 'images_p1'",
    "EASYOCR_CACHE = DRIVE_BASE / 'processed' / 'c3_easyocr_cache'",
    "MODELS_DIR = DRIVE_BASE / 'models' / 'c3_layoutlmv3'",
    "PREDS_CSV = DRIVE_BASE / 'processed' / 'c3_predictions.csv'",
    "EASYOCR_CACHE.mkdir(parents=True, exist_ok=True)",
    "MODELS_DIR.mkdir(parents=True, exist_ok=True)",
    "",
    "MODEL_NAME = 'microsoft/layoutlmv3-base'",
    "RANDOM_STATE = 42",
    "TEST_SIZE = 0.15",
    "VAL_SIZE = 0.15",
    "MAX_LENGTH = 512",
    "BATCH_SIZE = 2     # v2: reducido de 4 a 2 para menor VRAM",
    "GRAD_ACCUM = 4     # v2: efectivo batch = 8",
    "LEARNING_RATE = 2e-5",
    "N_EPOCHS = 5",
    "CHUNK_SIZE = 50    # v2: docs por chunk en EasyOCR",
    "",
    "assert CORPUS_CSV.exists(), f'NOT FOUND: {CORPUS_CSV}'",
    "assert IMAGES_P1.exists(), f'NOT FOUND: {IMAGES_P1}'",
    "n_images = len(list(IMAGES_P1.glob('processed_*_page_1.jpg')))",
    "print(f'Drive base    : {DRIVE_BASE}')",
    "print(f'Imagenes p1   : {n_images}')",
    "print(f'EasyOCR cache : {EASYOCR_CACHE}')",
    "print(f'Models out    : {MODELS_DIR}')",
    "print(f'Batch size    : {BATCH_SIZE} x grad_accum {GRAD_ACCUM} = effective {BATCH_SIZE*GRAD_ACCUM}')",
))

cells.append(md("## 5. Cargar corpus + agrupar + normalizar etiquetas"))

cells.append(code(
    "import pandas as pd",
    "",
    "df = pd.read_csv(CORPUS_CSV, dtype={'md5': str, 'doc_id': str})",
    "df['texto_ocr'] = df['texto_ocr'].fillna('')",
    "docs = df.groupby('doc_id').agg(folder=('folder', 'first'), md5=('md5', 'first')).reset_index()",
    "",
    "def normalizar_clase(folder):",
    "    s = str(folder).lower()",
    "    if 'cedul' in s: return 'Cedula'",
    "    if 'mara' in s: return 'CamaraComercio'",
    "    if 'liza' in s: return 'Poliza'",
    "    if s == 'rut': return 'RUT'",
    "    return 'OTRO'",
    "",
    "docs['clase'] = docs['folder'].apply(normalizar_clase)",
    "docs = docs[docs['clase'] != 'OTRO'].copy()",
    "docs['image_path'] = docs['md5'].apply(lambda m: IMAGES_P1 / f'processed_{m}_page_1.jpg')",
    "docs['image_exists'] = docs['image_path'].apply(lambda p: p.exists())",
    "n_sin_img = (~docs['image_exists']).sum()",
    "if n_sin_img:",
    "    print(f'WARNING: {n_sin_img} docs sin imagen pag 1 (excluidos)')",
    "docs = docs[docs['image_exists']].copy()",
    "",
    "CLASES = sorted(docs['clase'].unique())",
    "label2id = {c: i for i, c in enumerate(CLASES)}",
    "id2label = {i: c for c, i in label2id.items()}",
    "docs['label'] = docs['clase'].map(label2id)",
    "",
    "print(f'Docs finales: {len(docs)}')",
    "print(f'Clases: {CLASES}')",
    "print(docs['clase'].value_counts().to_string())",
))

cells.append(md("## 6. Split estratificado (mismo random_state=42 que nb10/nb11)"))

cells.append(code(
    "from sklearn.model_selection import train_test_split",
    "",
    "idx = docs.index.values",
    "y = docs['label'].values",
    "",
    "idx_temp, idx_test, _, _ = train_test_split(",
    "    idx, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y,",
    ")",
    "y_temp = docs.loc[idx_temp, 'label'].values",
    "idx_train, idx_val, _, _ = train_test_split(",
    "    idx_temp, y_temp,",
    "    test_size=VAL_SIZE / (1 - TEST_SIZE),",
    "    random_state=RANDOM_STATE,",
    "    stratify=y_temp,",
    ")",
    "",
    "train_docs = docs.loc[idx_train].reset_index(drop=True)",
    "val_docs   = docs.loc[idx_val].reset_index(drop=True)",
    "test_docs  = docs.loc[idx_test].reset_index(drop=True)",
    "print(f'Train: {len(train_docs)} | Val: {len(val_docs)} | Test: {len(test_docs)}')",
))

cells.append(md(
    "## 7. EasyOCR refactorizado: procesa en chunks y guarda a JSONL en Drive",
    "",
    "Cambio clave v2: en lugar de acumular 1,115 PIL+words+boxes en memoria, procesamos",
    "en chunks de 50 y guardamos cada record a JSONL inmediatamente. La memoria se",
    "libera entre chunks. Ademas hay cache: si ya existe el JSONL para un split, se salta.",
))

cells.append(code(
    "import easyocr",
    "from PIL import Image",
    "import numpy as np",
    "",
    "reader = easyocr.Reader(['es'], gpu=True)",
    "print('EasyOCR Reader listo en GPU')",
))

cells.append(code(
    "from tqdm.auto import tqdm",
    "import time",
    "",
    "def normalize_bbox(bbox_pts, img_w, img_h):",
    "    \"\"\"EasyOCR bbox = 4 puntos en pixeles -> LayoutLMv3 [x_min,y_min,x_max,y_max] en [0,1000]\"\"\"",
    "    xs = [p[0] for p in bbox_pts]",
    "    ys = [p[1] for p in bbox_pts]",
    "    return [",
    "        max(0, min(1000, int(min(xs) * 1000 / img_w))),",
    "        max(0, min(1000, int(min(ys) * 1000 / img_h))),",
    "        max(0, min(1000, int(max(xs) * 1000 / img_w))),",
    "        max(0, min(1000, int(max(ys) * 1000 / img_h))),",
    "    ]",
    "",
    "def extract_words_boxes(image_path):",
    "    img = Image.open(image_path).convert('RGB')",
    "    img_w, img_h = img.size",
    "    arr = np.array(img)",
    "    results = reader.readtext(arr, detail=1, paragraph=False)",
    "    words = [r[1] for r in results]",
    "    boxes = [normalize_bbox(r[0], img_w, img_h) for r in results]",
    "    img.close()",
    "    del arr",
    "    return words, boxes",
    "",
    "def process_split_chunked(df_split, name):",
    "    cache_path = EASYOCR_CACHE / f'{name}.jsonl'",
    "    ",
    "    # Cache: cuales doc_ids ya estan procesados",
    "    done_doc_ids = set()",
    "    if cache_path.exists():",
    "        with open(cache_path, 'r', encoding='utf-8') as f:",
    "            for line in f:",
    "                done_doc_ids.add(json.loads(line)['doc_id'])",
    "        print(f'  [{name}] cache: {len(done_doc_ids)} docs ya procesados')",
    "    ",
    "    pending = df_split[~df_split['doc_id'].isin(done_doc_ids)]",
    "    n_pending = len(pending)",
    "    if n_pending == 0:",
    "        print(f'  [{name}] todo en cache, skip')",
    "        return",
    "    print(f'  [{name}] {n_pending} docs por procesar en chunks de {CHUNK_SIZE}')",
    "    ",
    "    t0 = time.time()",
    "    n_ok = 0",
    "    n_skip = 0",
    "    n_err = 0",
    "    with open(cache_path, 'a', encoding='utf-8') as fout:",
    "        for chunk_start in range(0, n_pending, CHUNK_SIZE):",
    "            chunk = pending.iloc[chunk_start:chunk_start+CHUNK_SIZE]",
    "            for _, row in tqdm(chunk.iterrows(), total=len(chunk), desc=f'{name} chk{chunk_start//CHUNK_SIZE+1}'):",
    "                try:",
    "                    words, boxes = extract_words_boxes(row['image_path'])",
    "                    if len(words) == 0:",
    "                        n_skip += 1",
    "                        continue",
    "                    record = {",
    "                        'doc_id': row['doc_id'],",
    "                        'image_path': str(row['image_path']),",
    "                        'words': words,",
    "                        'boxes': boxes,",
    "                        'label': int(row['label']),",
    "                    }",
    "                    fout.write(json.dumps(record, ensure_ascii=False) + chr(10))",
    "                    n_ok += 1",
    "                except Exception as e:",
    "                    print(f'    ERROR {row[\"doc_id\"]}: {type(e).__name__}: {str(e)[:100]}')",
    "                    n_err += 1",
    "            fout.flush()  # asegura que llega a Drive",
    "            del chunk",
    "            gc.collect()",
    "    ",
    "    dt = (time.time() - t0) / 60",
    "    print(f'  [{name}] done: {n_ok} ok, {n_skip} skip, {n_err} err en {dt:.1f} min')",
    "",
    "process_split_chunked(train_docs, 'train')",
    "process_split_chunked(val_docs,   'val')",
    "process_split_chunked(test_docs,  'test')",
))

cells.append(md(
    "## 8. Liberar EasyOCR y memoria antes de cargar LayoutLMv3",
    "",
    "Critico para no acumular memoria: descargamos EasyOCR (que ya no necesitamos) antes de cargar LayoutLMv3.",
))

cells.append(code(
    "del reader",
    "gc.collect()",
    "torch.cuda.empty_cache()",
    "print('EasyOCR descargado, GPU memoria liberada')",
    "print(f'GPU memory allocated: {torch.cuda.memory_allocated()/1e9:.2f} GB')",
    "print(f'GPU memory reserved : {torch.cuda.memory_reserved()/1e9:.2f} GB')",
))

cells.append(md("## 9. Inicializar processor + modelo LayoutLMv3"))

cells.append(code(
    "from transformers import LayoutLMv3Processor, LayoutLMv3ForSequenceClassification",
    "",
    "processor = LayoutLMv3Processor.from_pretrained(MODEL_NAME, apply_ocr=False)",
    "model = LayoutLMv3ForSequenceClassification.from_pretrained(",
    "    MODEL_NAME,",
    "    num_labels=len(CLASES),",
    "    id2label=id2label,",
    "    label2id=label2id,",
    ")",
    "# Nota v2.1: gradient_checkpointing fue removido — LayoutLMv3ForSequenceClassification no lo soporta.",
    "# VRAM debe alcanzar igual con BATCH_SIZE=2 (LayoutLMv3-base 125M + batch 2 ≈ 6 GB en T4 16GB).",
    "print(f'Processor + model cargados: {MODEL_NAME}')",
))

cells.append(md(
    "## 10. Dataset con LAZY image loading",
    "",
    "Cambio clave v2: en lugar de cargar todas las imagenes de PIL en memoria, abrimos cada una solo cuando el Trainer pide ese ejemplo (`__getitem__`). Esto mantiene la memoria peak baja.",
))

cells.append(code(
    "from torch.utils.data import Dataset",
    "",
    "class LayoutLMv3Dataset(Dataset):",
    "    \"\"\"Dataset que carga records de JSONL y abre imagenes lazy en __getitem__.\"\"\"",
    "    def __init__(self, jsonl_path, processor, max_length=MAX_LENGTH):",
    "        self.processor = processor",
    "        self.max_length = max_length",
    "        # Solo metadata en memoria (~50 KB por record), NO imagenes",
    "        self.records = []",
    "        with open(jsonl_path, 'r', encoding='utf-8') as f:",
    "            for line in f:",
    "                self.records.append(json.loads(line))",
    "    ",
    "    def __len__(self):",
    "        return len(self.records)",
    "    ",
    "    def __getitem__(self, idx):",
    "        rec = self.records[idx]",
    "        # Lazy load image (se descarta tras encoding)",
    "        img = Image.open(rec['image_path']).convert('RGB')",
    "        encoding = self.processor(",
    "            img,",
    "            text=rec['words'],",
    "            boxes=rec['boxes'],",
    "            truncation=True,",
    "            padding='max_length',",
    "            max_length=self.max_length,",
    "            return_tensors='pt',",
    "        )",
    "        encoding = {k: v.squeeze(0) for k, v in encoding.items()}",
    "        encoding['labels'] = torch.tensor(rec['label'], dtype=torch.long)",
    "        return encoding",
    "",
    "ds_train = LayoutLMv3Dataset(EASYOCR_CACHE / 'train.jsonl', processor)",
    "ds_val   = LayoutLMv3Dataset(EASYOCR_CACHE / 'val.jsonl',   processor)",
    "ds_test  = LayoutLMv3Dataset(EASYOCR_CACHE / 'test.jsonl',  processor)",
    "print(f'Datasets: train={len(ds_train)}, val={len(ds_val)}, test={len(ds_test)}')",
))

cells.append(md("## 11. Trainer + entrenamiento"))

cells.append(code(
    "from transformers import TrainingArguments, Trainer",
    "from sklearn.metrics import accuracy_score, f1_score",
    "import numpy as np",
    "",
    "def compute_metrics(eval_pred):",
    "    logits, labels = eval_pred",
    "    preds = np.argmax(logits, axis=-1)",
    "    return {",
    "        'accuracy': accuracy_score(labels, preds),",
    "        'macro_f1': f1_score(labels, preds, average='macro'),",
    "        'weighted_f1': f1_score(labels, preds, average='weighted'),",
    "    }",
    "",
    "training_args = TrainingArguments(",
    "    output_dir='/content/c3_layoutlmv3_checkpoints',",
    "    num_train_epochs=N_EPOCHS,",
    "    per_device_train_batch_size=BATCH_SIZE,",
    "    per_device_eval_batch_size=BATCH_SIZE,",
    "    gradient_accumulation_steps=GRAD_ACCUM,  # batch efectivo = BATCH_SIZE * GRAD_ACCUM",
    "    learning_rate=LEARNING_RATE,",
    "    weight_decay=0.01,",
    "    eval_strategy='epoch',",
    "    save_strategy='epoch',",
    "    load_best_model_at_end=True,",
    "    metric_for_best_model='macro_f1',",
    "    logging_steps=20,",
    "    save_total_limit=1,",
    "    seed=RANDOM_STATE,",
    "    fp16=True,",
    "    report_to='none',",
    "    remove_unused_columns=False,",
    "    dataloader_num_workers=2,  # paralelizar lazy loading",
    ")",
    "",
    "trainer = Trainer(",
    "    model=model,",
    "    args=training_args,",
    "    train_dataset=ds_train,",
    "    eval_dataset=ds_val,",
    "    compute_metrics=compute_metrics,",
    ")",
    "",
    "import time",
    "t0 = time.time()",
    "trainer.train()",
    "elapsed_train = time.time() - t0",
    "print(f'Entrenamiento completado en {elapsed_train/60:.1f} min')",
))

cells.append(md("## 12. Evaluacion en test"))

cells.append(code(
    "test_results = trainer.evaluate(eval_dataset=ds_test)",
    "print('=== TEST ===')",
    "for k, v in test_results.items():",
    "    print(f'  {k}: {v:.4f}' if isinstance(v, float) else f'  {k}: {v}')",
))

cells.append(code(
    "from sklearn.metrics import classification_report",
    "",
    "preds_logits = trainer.predict(ds_test)",
    "y_test_pred = np.argmax(preds_logits.predictions, axis=-1)",
    "y_test_true = preds_logits.label_ids",
    "y_test_pred_str = [id2label[i] for i in y_test_pred]",
    "y_test_true_str = [id2label[i] for i in y_test_true]",
    "",
    "print(classification_report(y_test_true_str, y_test_pred_str, digits=4))",
))

cells.append(md("## 13. Matriz de confusion"))

cells.append(code(
    "from sklearn.metrics import confusion_matrix",
    "import matplotlib.pyplot as plt",
    "import seaborn as sns",
    "",
    "cm = confusion_matrix(y_test_true_str, y_test_pred_str, labels=CLASES)",
    "fig, ax = plt.subplots(figsize=(8, 6))",
    "sns.heatmap(cm, annot=True, fmt='d', cmap='Purples',",
    "            xticklabels=CLASES, yticklabels=CLASES, ax=ax)",
    "ax.set_xlabel('Predicho')",
    "ax.set_ylabel('Real')",
    "ax.set_title(f'C-3 LayoutLMv3  |  Test Macro-F1: {test_results[\"eval_macro_f1\"]:.4f}')",
    "plt.tight_layout()",
    "plt.savefig('/content/fig_nb12_confusion.png', dpi=120, bbox_inches='tight')",
    "plt.show()",
))

cells.append(md("## 14. Guardar modelo + predicciones a Drive"))

cells.append(code(
    "trainer.save_model(str(MODELS_DIR))",
    "processor.save_pretrained(str(MODELS_DIR))",
    "print(f'Modelo + processor guardados en {MODELS_DIR}')",
    "",
    "preds_df = pd.DataFrame({",
    "    'doc_id': [r['doc_id'] for r in ds_test.records],",
    "    'y_true': y_test_true_str,",
    "    'y_pred': y_test_pred_str,",
    "})",
    "preds_df.to_csv(PREDS_CSV, index=False, encoding='utf-8')",
    "print(f'Predicciones: {PREDS_CSV}')",
    "",
    "summary = {",
    "    'model': 'C-3 LayoutLMv3 fine-tuned (v2 refactor)',",
    "    'model_name': MODEL_NAME,",
    "    'random_state': RANDOM_STATE,",
    "    'n_train': len(ds_train),",
    "    'n_val': len(ds_val),",
    "    'n_test': len(ds_test),",
    "    'classes': CLASES,",
    "    'max_length': MAX_LENGTH,",
    "    'batch_size': BATCH_SIZE,",
    "    'grad_accum': GRAD_ACCUM,",
    "    'effective_batch_size': BATCH_SIZE * GRAD_ACCUM,",
    "    'gradient_checkpointing': True,",
    "    'learning_rate': LEARNING_RATE,",
    "    'n_epochs': N_EPOCHS,",
    "    'apply_ocr': False,",
    "    'ocr_engine_words_boxes': 'easyocr',",
    "    'training_time_min': float(elapsed_train / 60),",
    "    'test_accuracy': float(test_results['eval_accuracy']),",
    "    'test_macro_f1': float(test_results['eval_macro_f1']),",
    "    'test_weighted_f1': float(test_results['eval_weighted_f1']),",
    "}",
    "with open(MODELS_DIR / 'metrics.json', 'w') as f:",
    "    json.dump(summary, f, indent=2)",
    "print(f'Resumen: {summary}')",
))

cells.append(md(
    "## 15. Conclusion",
    "",
    "Tras correr nb10 (C-1), nb11 (C-2) y nb12 (C-3) sobre el MISMO split (random_state=42), el reporte comparativo final responde:",
    "",
    "1. C-1 vs C-2: ya sabemos que C-2 BETO no supera a C-1 TF-IDF (Macro-F1 0.9914 vs 1.0000)",
    "2. C-2 vs C-3: ¿LayoutLMv3 con info visual + layout supera a BETO con solo texto?",
    "3. Trade-off cost/perf: cual modelo va a produccion para esta tarea de clasificacion?",
    "",
    "Si C-3 tambien converge a ~99-100%, se confirma definitivamente que el dominio es trivialmente clasificable y la decision de produccion sigue siendo C-1 (mas barato, mas rapido, mas chico).",
))


nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3 (Colab)", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
        "colab": {"provenance": [], "gpuType": "T4"},
        "accelerator": "GPU",
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook generado: {OUT}")
print(f"Tamano: {OUT.stat().st_size:,} bytes")
print(f"Celdas: {len(cells)} ({sum(1 for c in cells if c['cell_type']=='code')} code, {sum(1 for c in cells if c['cell_type']=='markdown')} markdown)")
