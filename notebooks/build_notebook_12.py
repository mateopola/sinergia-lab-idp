"""
Genera notebooks/12_clasificacion_C3_layoutlmv3.ipynb (para subir a Colab GPU)

Modelo: LayoutLMv3 base fine-tuned para clasificacion de documentos.
Ver: PROPUESTA_MODELOS.md FASE 2 candidato C-3.

Inputs por documento:
- Imagen pag 1 (data/processed/images/processed_<md5>_page_1.jpg)
- Words + bboxes obtenidos via EasyOCR sobre la misma imagen (paridad train-inference)

CRITICO: usa el MISMO random_state=42 y MISMA logica de split que nb10 y nb11.

Inputs en Drive:
- MyDrive/datasets/SinergiaLab/processed/corpus_ocr.csv
- MyDrive/datasets/SinergiaLab/processed/images_p1/  (carpeta con imagenes pag 1)

Outputs en Drive:
- MyDrive/datasets/SinergiaLab/models/c3_layoutlmv3/
- MyDrive/datasets/SinergiaLab/processed/c3_predictions.csv
- MyDrive/datasets/SinergiaLab/models/c3_layoutlmv3/metrics.json

Run en Colab T4 GPU (~60-90 min: 5-10 min EasyOCR sobre 1,159 imgs + ~50 min training).
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
    "# nb12 - Clasificacion C-3: LayoutLMv3 fine-tuned (multimodal: texto + layout + imagen)",
    "",
    "**Tarea:** clasificar documentos en `{Cedula, RUT, Poliza, CamaraComercio}`",
    "",
    "**Modelo:** `microsoft/layoutlmv3-base` (Huang et al. 2022, ACM MM) fine-tuned con HuggingFace Trainer.",
    "Ver [PROPUESTA_MODELOS.md](https://github.com/) FASE 2 candidato C-3.",
    "",
    "**Por que LayoutLMv3:** estado del arte en Document AI (FUNSD F1 90.8, CORD F1 98.48). Aprovecha la estructura visual del documento (formularios, tablas) que C-1 (TF-IDF) y C-2 (BETO) ignoran completamente.",
    "",
    "**Decisiones (alineadas con C-1 y C-2 para comparacion justa):**",
    "- Mismo split estratificado 70/15/15 con `random_state=42`",
    "- Imagen = pag 1 renderizada (150 DPI guardada localmente, processor la reescala a 224x224)",
    "- Words + bboxes = re-extraidos via EasyOCR sobre la misma imagen (paridad train-inference)",
    "- 4 clases (sin Otros)",
    "",
    "**Hardware:** Colab T4 GPU. Tiempo: ~60-90 min (10 min EasyOCR + 50-80 min training).",
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
    "",
    "DRIVE_BASE = Path('/content/drive/MyDrive/datasets/SinergiaLab')",
    "CORPUS_CSV = DRIVE_BASE / 'processed' / 'corpus_ocr.csv'",
    "IMAGES_P1 = DRIVE_BASE / 'processed' / 'images_p1'  # carpeta con processed_<md5>_page_1.jpg",
    "MODELS_DIR = DRIVE_BASE / 'models' / 'c3_layoutlmv3'",
    "PREDS_CSV = DRIVE_BASE / 'processed' / 'c3_predictions.csv'",
    "MODELS_DIR.mkdir(parents=True, exist_ok=True)",
    "",
    "MODEL_NAME = 'microsoft/layoutlmv3-base'",
    "RANDOM_STATE = 42",
    "TEST_SIZE = 0.15",
    "VAL_SIZE = 0.15",
    "MAX_LENGTH = 512",
    "BATCH_SIZE = 4   # LayoutLMv3 + imagen consume mas VRAM que solo texto",
    "LEARNING_RATE = 2e-5",
    "N_EPOCHS = 5     # mas epochs que BETO porque hay mas parametros que ajustar",
    "",
    "assert CORPUS_CSV.exists(), f'NOT FOUND: {CORPUS_CSV}'",
    "assert IMAGES_P1.exists(), f'NOT FOUND: {IMAGES_P1} (subiste data/processed/images_p1/?)'",
    "n_images = len(list(IMAGES_P1.glob('processed_*_page_1.jpg')))",
    "print(f'Corpus: {CORPUS_CSV}')",
    "print(f'Imagenes p1 disponibles: {n_images}')",
    "print(f'Models out: {MODELS_DIR}')",
))

cells.append(md("## 5. Cargar corpus + agrupar (igual que nb10/nb11)"))

cells.append(code(
    "import pandas as pd",
    "",
    "df = pd.read_csv(CORPUS_CSV, dtype={'md5': str, 'doc_id': str})",
    "df['texto_ocr'] = df['texto_ocr'].fillna('')",
    "docs = df.groupby('doc_id').agg(",
    "    folder=('folder', 'first'),",
    "    md5=('md5', 'first'),",
    ").reset_index()",
    "print(f'Documentos en corpus: {len(docs)}')",
))

cells.append(md("## 6. Normalizar etiquetas + filtrar docs sin imagen"))

cells.append(code(
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
    "",
    "# Filtrar docs cuya imagen pag 1 existe",
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

cells.append(md("## 7. Split estratificado (mismo random_state=42 que nb10/nb11)"))

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
    "## 8. Re-extraer words + bboxes con EasyOCR sobre la imagen pag 1",
    "",
    "Garantiza paridad train-inference (mismo motor OCR que producira el corpus en produccion).",
    "Ademas las bboxes quedan en las dimensiones exactas de la imagen guardada (no necesita scaling DPI).",
    "",
    "Bboxes se devuelven en pixel coords; LayoutLMv3 espera [0, 1000]. La conversion se hace al construir el dataset.",
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
    "    \"\"\"EasyOCR bbox = 4 puntos [[x1,y1], [x2,y1], [x2,y2], [x1,y2]] en pixeles.",
    "    LayoutLMv3 espera [x_min, y_min, x_max, y_max] en [0, 1000].\"\"\"",
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
    "    return img, words, boxes",
    "",
    "# Pre-procesar todas las imagenes (cachear para no re-procesar en cada epoch)",
    "def process_split(df_split, name):",
    "    out = []",
    "    t0 = time.time()",
    "    for _, row in tqdm(df_split.iterrows(), total=len(df_split), desc=name):",
    "        try:",
    "            img, words, boxes = extract_words_boxes(row['image_path'])",
    "            if len(words) == 0:",
    "                # Documento sin texto detectable (pagina en blanco) - skip",
    "                continue",
    "            out.append({",
    "                'doc_id': row['doc_id'],",
    "                'image': img,",
    "                'words': words,",
    "                'boxes': boxes,",
    "                'label': int(row['label']),",
    "            })",
    "        except Exception as e:",
    "            print(f'  ERROR {row[\"doc_id\"]}: {e}')",
    "    print(f'  {name}: {len(out)}/{len(df_split)} docs procesados en {(time.time()-t0)/60:.1f} min')",
    "    return out",
    "",
    "train_data = process_split(train_docs, 'train')",
    "val_data   = process_split(val_docs, 'val')",
    "test_data  = process_split(test_docs, 'test')",
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
    "print(f'Processor + model cargados: {MODEL_NAME}')",
))

cells.append(md("## 10. Construir HF Dataset con encoding LayoutLMv3"))

cells.append(code(
    "from torch.utils.data import Dataset",
    "",
    "class LayoutLMv3Dataset(Dataset):",
    "    def __init__(self, data, processor, max_length=MAX_LENGTH):",
    "        self.data = data",
    "        self.processor = processor",
    "        self.max_length = max_length",
    "    def __len__(self):",
    "        return len(self.data)",
    "    def __getitem__(self, idx):",
    "        item = self.data[idx]",
    "        encoding = self.processor(",
    "            item['image'],",
    "            text=item['words'],",
    "            boxes=item['boxes'],",
    "            truncation=True,",
    "            padding='max_length',",
    "            max_length=self.max_length,",
    "            return_tensors='pt',",
    "        )",
    "        encoding = {k: v.squeeze(0) for k, v in encoding.items()}",
    "        encoding['labels'] = torch.tensor(item['label'], dtype=torch.long)",
    "        return encoding",
    "",
    "ds_train = LayoutLMv3Dataset(train_data, processor)",
    "ds_val   = LayoutLMv3Dataset(val_data, processor)",
    "ds_test  = LayoutLMv3Dataset(test_data, processor)",
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
    "    gradient_accumulation_steps=2,  # batch efectivo = 8",
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
    "    remove_unused_columns=False,  # importante para LayoutLMv3",
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
    "import json",
    "",
    "trainer.save_model(str(MODELS_DIR))",
    "processor.save_pretrained(str(MODELS_DIR))",
    "print(f'Modelo + processor guardados en {MODELS_DIR}')",
    "",
    "preds_df = pd.DataFrame({",
    "    'doc_id': [d['doc_id'] for d in test_data],",
    "    'y_true': y_test_true_str,",
    "    'y_pred': y_test_pred_str,",
    "})",
    "preds_df.to_csv(PREDS_CSV, index=False, encoding='utf-8')",
    "print(f'Predicciones: {PREDS_CSV}')",
    "",
    "summary = {",
    "    'model': 'C-3 LayoutLMv3 fine-tuned',",
    "    'model_name': MODEL_NAME,",
    "    'random_state': RANDOM_STATE,",
    "    'n_train': len(train_data),",
    "    'n_val': len(val_data),",
    "    'n_test': len(test_data),",
    "    'classes': CLASES,",
    "    'max_length': MAX_LENGTH,",
    "    'batch_size': BATCH_SIZE,",
    "    'gradient_accumulation_steps': 2,",
    "    'effective_batch_size': BATCH_SIZE * 2,",
    "    'learning_rate': LEARNING_RATE,",
    "    'n_epochs': N_EPOCHS,",
    "    'apply_ocr': False,",
    "    'ocr_engine_words_boxes': 'easyocr',  # paridad train-inference",
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
    "## 15. Conclusion + comparacion 3-vias",
    "",
    "Tras correr nb10 (C-1), nb11 (C-2) y nb12 (C-3) sobre el MISMO split (random_state=42), el reporte comparativo final responde:",
    "",
    "1. **C-1 vs C-2:** ¿BETO supera al baseline TF-IDF en >= +5 puntos macro-F1? (criterio del paper)",
    "2. **C-2 vs C-3:** ¿LayoutLMv3 supera a BETO usando layout/imagen? (esperado segun literatura: si)",
    "3. **Trade-off cost/perf:** que tanto cuesta entrenar e inferir cada uno?",
    "",
    "Metricas a llevar al reporte (de cada `metrics.json`):",
    "",
    "| Modelo | Test Macro-F1 | Tiempo train | VRAM | Tamano modelo |",
    "|---|---|---|---|---|",
    "| C-1 TF-IDF + LR  | (de nb10)     | ~20s         | -    | <10 MB |",
    "| C-2 BETO         | (de nb11)     | ~30 min      | ~6 GB | 440 MB |",
    "| C-3 LayoutLMv3   | (de nb12)     | ~50-80 min   | ~10 GB | 500 MB |",
    "",
    "Veredicto al final del estudio comparativo: cual modelo va a produccion segun coste/beneficio.",
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
