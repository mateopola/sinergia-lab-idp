"""
Genera notebooks/11_clasificacion_C2_beto.ipynb (para subir a Colab GPU)

Modelo: BETO fine-tuned (Canete et al. 2020).
Ver: PROPUESTA_MODELOS.md FASE 2 candidato C-2.

CRITICO: usa el MISMO random_state=42 y MISMA logica de split que nb10 para comparacion justa.

Inputs en Drive:
- MyDrive/datasets/SinergiaLab/processed/corpus_ocr.csv

Outputs en Drive:
- MyDrive/datasets/SinergiaLab/models/c2_beto/ (modelo fine-tuned)
- MyDrive/datasets/SinergiaLab/processed/c2_predictions.csv
- MyDrive/datasets/SinergiaLab/models/c2_beto/metrics.json

Run en Colab T4 GPU (~30 min).
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "11_clasificacion_C2_beto.ipynb"


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
    "# nb11 - Clasificacion C-2: BETO fine-tuned (Bert en Espanol)",
    "",
    "**Tarea:** clasificar documentos en `{Cedula, RUT, Poliza, CamaraComercio}`",
    "",
    "**Modelo:** `dccuchile/bert-base-spanish-wwm-cased` (BETO, Canete et al. 2020) fine-tuned con HuggingFace Trainer.",
    "Ver [PROPUESTA_MODELOS.md](https://github.com/) FASE 2 candidato C-2.",
    "",
    "**Decisiones (alineadas con C-1 TF-IDF y C-3 LayoutLMv3 para comparacion justa):**",
    "- Mismo split estratificado 70/15/15 con `random_state=42`",
    "- Texto = concat de texto_ocr de las primeras 10 paginas",
    "- Truncado a 512 tokens (limite BERT)",
    "- 4 clases (sin Otros)",
    "",
    "**Hardware:** Colab T4 GPU. Tiempo: ~30 min (carga modelo + 3 epochs).",
))

cells.append(md("## 1. Verificar GPU"))

cells.append(code(
    "import torch",
    "assert torch.cuda.is_available(), 'Sin GPU. Runtime > Change runtime type > T4 GPU'",
    "print(f'GPU: {torch.cuda.get_device_name(0)}')",
))

cells.append(md("## 2. Instalar dependencias"))

cells.append(code(
    "!pip install -q transformers datasets accelerate evaluate scikit-learn",
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
    "MODELS_DIR = DRIVE_BASE / 'models' / 'c2_beto'",
    "PREDS_CSV = DRIVE_BASE / 'processed' / 'c2_predictions.csv'",
    "MODELS_DIR.mkdir(parents=True, exist_ok=True)",
    "",
    "MODEL_NAME = 'dccuchile/bert-base-spanish-wwm-cased'",
    "RANDOM_STATE = 42",
    "TEST_SIZE = 0.15",
    "VAL_SIZE = 0.15",
    "MAX_LENGTH = 512",
    "BATCH_SIZE = 16",
    "LEARNING_RATE = 2e-5",
    "N_EPOCHS = 3",
    "",
    "assert CORPUS_CSV.exists(), f'NOT FOUND: {CORPUS_CSV}'",
    "print(f'Corpus: {CORPUS_CSV}')",
    "print(f'Models out: {MODELS_DIR}')",
))

cells.append(md("## 5. Cargar corpus + agrupar por documento"))

cells.append(code(
    "import pandas as pd",
    "",
    "df = pd.read_csv(CORPUS_CSV, dtype={'md5': str, 'doc_id': str})",
    "print(f'Filas: {len(df):,} | Docs unicos: {df[\"doc_id\"].nunique()}')",
    "print('Engines:', df['engine'].value_counts().to_dict())",
    "",
    "df['texto_ocr'] = df['texto_ocr'].fillna('')",
    "docs = df.groupby('doc_id').agg(",
    "    texto=('texto_ocr', lambda s: '\\n'.join(s)),",
    "    folder=('folder', 'first'),",
    ").reset_index()",
    "print(f'Documentos agrupados: {len(docs)}')",
))

cells.append(md("## 6. Normalizar etiquetas (mismo mapping que nb10)"))

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
    "docs = docs[docs['texto'].str.strip() != ''].copy()",
    "",
    "CLASES = sorted(docs['clase'].unique())",
    "label2id = {c: i for i, c in enumerate(CLASES)}",
    "id2label = {i: c for c, i in label2id.items()}",
    "docs['label'] = docs['clase'].map(label2id)",
    "",
    "print('Clases:', CLASES)",
    "print(docs['clase'].value_counts().to_string())",
))

cells.append(md("## 7. Split (mismo random_state que nb10)"))

cells.append(code(
    "from sklearn.model_selection import train_test_split",
    "",
    "X_temp, X_test, y_temp, y_test = train_test_split(",
    "    docs['texto'], docs['label'],",
    "    test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=docs['clase'],",
    ")",
    "X_train, X_val, y_train, y_val = train_test_split(",
    "    X_temp, y_temp,",
    "    test_size=VAL_SIZE / (1 - TEST_SIZE), random_state=RANDOM_STATE, stratify=y_temp,",
    ")",
    "",
    "print(f'Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}')",
))

cells.append(md("## 8. Tokenizar con BETO"))

cells.append(code(
    "from transformers import AutoTokenizer",
    "from datasets import Dataset",
    "",
    "tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)",
    "",
    "def tokenize_fn(batch):",
    "    return tokenizer(batch['text'], truncation=True, padding=False, max_length=MAX_LENGTH)",
    "",
    "def df_to_ds(X, y):",
    "    return Dataset.from_dict({'text': X.tolist(), 'label': y.tolist()})",
    "",
    "ds_train = df_to_ds(X_train, y_train).map(tokenize_fn, batched=True)",
    "ds_val   = df_to_ds(X_val, y_val).map(tokenize_fn, batched=True)",
    "ds_test  = df_to_ds(X_test, y_test).map(tokenize_fn, batched=True)",
    "",
    "ds_train.set_format('torch', columns=['input_ids', 'attention_mask', 'label'])",
    "ds_val.set_format('torch', columns=['input_ids', 'attention_mask', 'label'])",
    "ds_test.set_format('torch', columns=['input_ids', 'attention_mask', 'label'])",
    "",
    "print(f'Tokenized: train={len(ds_train)}, val={len(ds_val)}, test={len(ds_test)}')",
))

cells.append(md("## 9. Cargar modelo BETO"))

cells.append(code(
    "from transformers import AutoModelForSequenceClassification",
    "",
    "model = AutoModelForSequenceClassification.from_pretrained(",
    "    MODEL_NAME,",
    "    num_labels=len(CLASES),",
    "    id2label=id2label,",
    "    label2id=label2id,",
    ")",
    "print(f'Modelo cargado: {MODEL_NAME} | num_labels: {len(CLASES)}')",
))

cells.append(md("## 10. Setup Trainer + entrenamiento"))

cells.append(code(
    "from transformers import TrainingArguments, Trainer, DataCollatorWithPadding",
    "import numpy as np",
    "from sklearn.metrics import accuracy_score, f1_score",
    "",
    "data_collator = DataCollatorWithPadding(tokenizer=tokenizer)",
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
    "    output_dir='/content/c2_beto_checkpoints',",
    "    num_train_epochs=N_EPOCHS,",
    "    per_device_train_batch_size=BATCH_SIZE,",
    "    per_device_eval_batch_size=BATCH_SIZE,",
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
    ")",
    "",
    "trainer = Trainer(",
    "    model=model,",
    "    args=training_args,",
    "    train_dataset=ds_train,",
    "    eval_dataset=ds_val,",
    "    tokenizer=tokenizer,",
    "    data_collator=data_collator,",
    "    compute_metrics=compute_metrics,",
    ")",
    "",
    "import time",
    "t0 = time.time()",
    "trainer.train()",
    "elapsed_train = time.time() - t0",
    "print(f'Entrenamiento completado en {elapsed_train/60:.1f} min')",
))

cells.append(md("## 11. Evaluacion en test"))

cells.append(code(
    "test_results = trainer.evaluate(eval_dataset=ds_test)",
    "print('=== TEST ===')",
    "for k, v in test_results.items():",
    "    print(f'  {k}: {v:.4f}' if isinstance(v, float) else f'  {k}: {v}')",
))

cells.append(code(
    "from sklearn.metrics import classification_report, confusion_matrix",
    "",
    "preds_logits = trainer.predict(ds_test)",
    "y_test_pred = np.argmax(preds_logits.predictions, axis=-1)",
    "y_test_true = preds_logits.label_ids",
    "",
    "y_test_pred_str = [id2label[i] for i in y_test_pred]",
    "y_test_true_str = [id2label[i] for i in y_test_true]",
    "",
    "print(classification_report(y_test_true_str, y_test_pred_str, digits=4))",
))

cells.append(md("## 12. Matriz de confusion"))

cells.append(code(
    "import matplotlib.pyplot as plt",
    "import seaborn as sns",
    "",
    "cm = confusion_matrix(y_test_true_str, y_test_pred_str, labels=CLASES)",
    "fig, ax = plt.subplots(figsize=(8, 6))",
    "sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',",
    "            xticklabels=CLASES, yticklabels=CLASES, ax=ax)",
    "ax.set_xlabel('Predicho')",
    "ax.set_ylabel('Real')",
    "ax.set_title(f'C-2 BETO  |  Test Macro-F1: {test_results[\"eval_macro_f1\"]:.4f}')",
    "plt.tight_layout()",
    "plt.savefig('/content/fig_nb11_confusion.png', dpi=120, bbox_inches='tight')",
    "plt.show()",
))

cells.append(md("## 13. Guardar modelo + predicciones a Drive"))

cells.append(code(
    "import json",
    "",
    "trainer.save_model(str(MODELS_DIR))",
    "tokenizer.save_pretrained(str(MODELS_DIR))",
    "print(f'Modelo + tokenizer guardados en {MODELS_DIR}')",
    "",
    "preds_df = pd.DataFrame({",
    "    'doc_id': X_test.index.map(lambda i: docs.loc[i, 'doc_id']),",
    "    'y_true': y_test_true_str,",
    "    'y_pred': y_test_pred_str,",
    "})",
    "preds_df.to_csv(PREDS_CSV, index=False, encoding='utf-8')",
    "print(f'Predicciones: {PREDS_CSV}')",
    "",
    "summary = {",
    "    'model': 'C-2 BETO fine-tuned',",
    "    'model_name': MODEL_NAME,",
    "    'random_state': RANDOM_STATE,",
    "    'n_train': int(len(X_train)),",
    "    'n_val': int(len(X_val)),",
    "    'n_test': int(len(X_test)),",
    "    'classes': CLASES,",
    "    'max_length': MAX_LENGTH,",
    "    'batch_size': BATCH_SIZE,",
    "    'learning_rate': LEARNING_RATE,",
    "    'n_epochs': N_EPOCHS,",
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
    "## 14. Conclusion + comparacion contra C-1",
    "",
    "Para comparar con C-1 (TF-IDF), descarga este `metrics.json` y compara `test_macro_f1`.",
    "",
    "**Criterio del paper:** BETO debe superar a C-1 en al menos +5 puntos de macro-F1 para justificar su costo computacional.",
    "",
    "**Siguiente paso:** ejecutar `nb12_clasificacion_C3_layoutlmv3.ipynb` (LayoutLMv3 con imagen + texto + bboxes) para el experimento 3.",
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
