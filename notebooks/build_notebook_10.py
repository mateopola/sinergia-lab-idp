"""
Genera notebooks/10_clasificacion_C1_tfidf.ipynb

Modelo: TF-IDF + Regresion Logistica (baseline obligatorio del estudio comparativo).
Ver: PROPUESTA_MODELOS.md FASE 2 candidato C-1.

Inputs:
- data/processed/corpus_ocr.csv (necesita estar al 100% EasyOCR despues de Colab)

Outputs:
- models/c1_tfidf/{vectorizer.joblib, classifier.joblib}
- reports/nb10_resultados.md (template para el ritual de WORKFLOW.md)
- data/processed/c1_predictions.csv

Run en CPU local. Tiempo estimado: ~20 min total.
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "10_clasificacion_C1_tfidf.ipynb"


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
    "# nb10 - Clasificacion C-1: TF-IDF + Regresion Logistica",
    "",
    "**Tarea:** clasificar cada documento en una de 4 clases: `{Cedula, RUT, Poliza, CamaraComercio}`",
    "",
    "**Modelo:** TF-IDF (Sparck Jones 1972) + Logistic Regression — baseline obligatorio del estudio comparativo.",
    "Ver [PROPUESTA_MODELOS.md](../PROPUESTA_MODELOS.md) FASE 2 candidato C-1.",
    "",
    "**Decisiones (alineadas con C-2 BETO y C-3 LayoutLMv3 para comparacion justa):**",
    "- Mismo split estratificado 70/15/15 con `random_state=42`",
    "- Texto del documento = concat de texto_ocr de las primeras 10 paginas (limite del OCR unificado)",
    "- Excluida clase Otros (decision 2026-04-21)",
    "- Etiquetas canonicas: `{Cedula, RUT, Poliza, CamaraComercio}` (normalizadas desde folder con mojibake)",
    "",
    "**Hardware:** CPU local. Tiempo: ~20 min.",
))

cells.append(md("## 1. Imports y configuracion"))

cells.append(code(
    "import pandas as pd",
    "import numpy as np",
    "from pathlib import Path",
    "import matplotlib.pyplot as plt",
    "import seaborn as sns",
    "from sklearn.feature_extraction.text import TfidfVectorizer",
    "from sklearn.linear_model import LogisticRegression",
    "from sklearn.model_selection import train_test_split",
    "from sklearn.metrics import (",
    "    classification_report, confusion_matrix, f1_score, accuracy_score",
    ")",
    "import joblib",
    "import json",
    "",
    "ROOT = Path('..')",
    "CORPUS = ROOT / 'data' / 'processed' / 'corpus_ocr.csv'",
    "MODELS_DIR = ROOT / 'models' / 'c1_tfidf'",
    "REPORTS_DIR = ROOT / 'reports'",
    "MODELS_DIR.mkdir(parents=True, exist_ok=True)",
    "",
    "RANDOM_STATE = 42",
    "TEST_SIZE = 0.15",
    "VAL_SIZE = 0.15  # del 85% restante",
    "",
    "print(f'Corpus: {CORPUS}')",
    "print(f'Models out: {MODELS_DIR}')",
))

cells.append(md("## 2. Cargar corpus + agrupar por documento"))

cells.append(code(
    "df = pd.read_csv(CORPUS, dtype={'md5': str, 'doc_id': str})",
    "print(f'Filas en corpus: {len(df):,}')",
    "print(f'Docs unicos    : {df[\"doc_id\"].nunique()}')",
    "print()",
    "print('Por engine (debe ser 100% easyocr post-Fase 2.1.5):')",
    "print(df['engine'].value_counts().to_string())",
))

cells.append(code(
    "# Agrupar texto por documento (concat de las 10 paginas)",
    "df['texto_ocr'] = df['texto_ocr'].fillna('')",
    "docs = df.groupby('doc_id').agg(",
    "    texto=('texto_ocr', lambda s: '\\n'.join(s)),",
    "    folder=('folder', 'first'),",
    "    n_pages=('page_num', 'count'),",
    ").reset_index()",
    "print(f'Documentos despues de agrupar: {len(docs)}')",
    "print(f'Distribucion de paginas por doc:')",
    "print(docs['n_pages'].describe().to_string())",
))

cells.append(md("## 3. Normalizar etiquetas (mojibake -> canonicas)"))

cells.append(code(
    "def normalizar_clase(folder: str) -> str:",
    "    s = str(folder).lower()",
    "    if 'cedul' in s:",
    "        return 'Cedula'",
    "    if 'mara' in s:  # Camara de Comercio (con o sin mojibake)",
    "        return 'CamaraComercio'",
    "    if 'liza' in s:  # Poliza (con o sin mojibake)",
    "        return 'Poliza'",
    "    if s == 'rut':",
    "        return 'RUT'",
    "    return 'OTRO'  # no deberia aparecer (Otros eliminados)",
    "",
    "docs['clase'] = docs['folder'].apply(normalizar_clase)",
    "print('Distribucion de clases:')",
    "print(docs['clase'].value_counts().to_string())",
    "",
    "# Excluir cualquier OTRO residual (defensivo)",
    "n_antes = len(docs)",
    "docs = docs[docs['clase'] != 'OTRO'].copy()",
    "if len(docs) != n_antes:",
    "    print(f'WARNING: removidos {n_antes - len(docs)} docs sin clase canonica')",
    "",
    "# Eliminar docs con texto vacio (no se pueden clasificar)",
    "docs = docs[docs['texto'].str.strip() != ''].copy()",
    "print(f'Docs finales para entrenamiento: {len(docs)}')",
))

cells.append(md("## 4. Split estratificado 70/15/15 con `random_state=42`"))

cells.append(code(
    "# Primer split: 85% train+val, 15% test",
    "X_temp, X_test, y_temp, y_test = train_test_split(",
    "    docs['texto'], docs['clase'],",
    "    test_size=TEST_SIZE,",
    "    random_state=RANDOM_STATE,",
    "    stratify=docs['clase'],",
    ")",
    "",
    "# Segundo split: del 85% -> 70%/15% (es decir, val es 15/85 = ~17.6% de temp)",
    "X_train, X_val, y_train, y_val = train_test_split(",
    "    X_temp, y_temp,",
    "    test_size=VAL_SIZE / (1 - TEST_SIZE),",
    "    random_state=RANDOM_STATE,",
    "    stratify=y_temp,",
    ")",
    "",
    "print(f'Train: {len(X_train)} ({len(X_train)/len(docs):.0%})')",
    "print(f'Val  : {len(X_val)} ({len(X_val)/len(docs):.0%})')",
    "print(f'Test : {len(X_test)} ({len(X_test)/len(docs):.0%})')",
    "print()",
    "print('Distribucion train:')",
    "print(y_train.value_counts(normalize=True).to_string())",
    "print()",
    "print('Distribucion test:')",
    "print(y_test.value_counts(normalize=True).to_string())",
))

cells.append(md(
    "## 5. Vectorizar con TF-IDF",
    "",
    "Hiperparametros (justificacion en Manning, Raghavan, Schutze 2008 Cap. 6):",
    "- `ngram_range=(1, 2)`: unigramas + bigramas para capturar terminos como 'razon social', 'numero poliza'",
    "- `max_features=20000`: cota razonable para corpus de ~1k docs",
    "- `sublinear_tf=True`: damp tf con `1 + log(tf)` para reducir efecto de terminos repetidos",
    "- `min_df=2, max_df=0.95`: descartar terminos en 1 doc o en >95% de docs (ruido)",
    "- `strip_accents='unicode'`: normalizar acentos",
))

cells.append(code(
    "vectorizer = TfidfVectorizer(",
    "    ngram_range=(1, 2),",
    "    max_features=20000,",
    "    sublinear_tf=True,",
    "    min_df=2,",
    "    max_df=0.95,",
    "    strip_accents='unicode',",
    "    lowercase=True,",
    ")",
    "",
    "X_train_vec = vectorizer.fit_transform(X_train)",
    "X_val_vec = vectorizer.transform(X_val)",
    "X_test_vec = vectorizer.transform(X_test)",
    "",
    "print(f'Vocabulario: {len(vectorizer.vocabulary_):,} features')",
    "print(f'Matriz train: {X_train_vec.shape} ({X_train_vec.nnz / X_train_vec.shape[0]:.1f} no-cero por doc)')",
))

cells.append(md(
    "## 6. Entrenar Regresion Logistica",
    "",
    "Multinomial (softmax sobre 4 clases) con regularizacion L2.",
    "`class_weight='balanced'` para compensar desbalance (Cedulas dominan ~46%).",
))

cells.append(code(
    "clf = LogisticRegression(",
    "    multi_class='multinomial',",
    "    solver='lbfgs',",
    "    max_iter=1000,",
    "    class_weight='balanced',",
    "    random_state=RANDOM_STATE,",
    "    C=1.0,",
    ")",
    "",
    "import time",
    "t0 = time.time()",
    "clf.fit(X_train_vec, y_train)",
    "elapsed = time.time() - t0",
    "print(f'Entrenamiento completado en {elapsed:.1f} s')",
    "print(f'Clases: {list(clf.classes_)}')",
))

cells.append(md("## 7. Evaluacion en validacion"))

cells.append(code(
    "y_val_pred = clf.predict(X_val_vec)",
    "print('=== Validacion ===')",
    "print(f'Accuracy   : {accuracy_score(y_val, y_val_pred):.4f}')",
    "print(f'Macro-F1   : {f1_score(y_val, y_val_pred, average=\"macro\"):.4f}')",
    "print(f'Weighted-F1: {f1_score(y_val, y_val_pred, average=\"weighted\"):.4f}')",
    "print()",
    "print(classification_report(y_val, y_val_pred, digits=4))",
))

cells.append(md("## 8. Evaluacion en test (metrica primaria del paper)"))

cells.append(code(
    "y_test_pred = clf.predict(X_test_vec)",
    "y_test_proba = clf.predict_proba(X_test_vec)",
    "",
    "test_acc = accuracy_score(y_test, y_test_pred)",
    "test_macro_f1 = f1_score(y_test, y_test_pred, average='macro')",
    "test_weighted_f1 = f1_score(y_test, y_test_pred, average='weighted')",
    "",
    "print('=== TEST (metricas para el reporte) ===')",
    "print(f'Accuracy     : {test_acc:.4f}')",
    "print(f'Macro-F1     : {test_macro_f1:.4f}  <- metrica primaria de comparacion')",
    "print(f'Weighted-F1  : {test_weighted_f1:.4f}')",
    "print()",
    "print(classification_report(y_test, y_test_pred, digits=4))",
))

cells.append(md("## 9. Matriz de confusion"))

cells.append(code(
    "cm = confusion_matrix(y_test, y_test_pred, labels=clf.classes_)",
    "fig, ax = plt.subplots(figsize=(8, 6))",
    "sns.heatmap(",
    "    cm, annot=True, fmt='d', cmap='Blues',",
    "    xticklabels=clf.classes_, yticklabels=clf.classes_, ax=ax,",
    ")",
    "ax.set_xlabel('Predicho')",
    "ax.set_ylabel('Real')",
    "ax.set_title(f'C-1 TF-IDF+LR  |  Test Macro-F1: {test_macro_f1:.4f}')",
    "plt.tight_layout()",
    "fig_path = REPORTS_DIR / 'fig_nb10_confusion.png'",
    "fig_path.parent.mkdir(parents=True, exist_ok=True)",
    "plt.savefig(fig_path, dpi=120, bbox_inches='tight')",
    "plt.show()",
    "print(f'Figura guardada: {fig_path}')",
))

cells.append(md(
    "## 10. Interpretabilidad — top features por clase",
    "",
    "Una de las ventajas de TF-IDF + LR sobre BETO/LayoutLMv3 es interpretabilidad pura.",
    "Los pesos de cada feature (palabra/bigrama) revelan que terminos identifican cada clase.",
))

cells.append(code(
    "feature_names = vectorizer.get_feature_names_out()",
    "top_n = 15",
    "",
    "for idx, clase in enumerate(clf.classes_):",
    "    coefs = clf.coef_[idx]",
    "    top_pos = np.argsort(coefs)[-top_n:][::-1]",
    "    print(f'\\n=== {clase} - Top {top_n} features (coef positivo) ===')",
    "    for i in top_pos:",
    "        print(f'  {feature_names[i]:30s}  {coefs[i]:+.4f}')",
))

cells.append(md("## 11. Guardar modelo + predicciones"))

cells.append(code(
    "joblib.dump(vectorizer, MODELS_DIR / 'vectorizer.joblib')",
    "joblib.dump(clf, MODELS_DIR / 'classifier.joblib')",
    "print(f'Modelo guardado en {MODELS_DIR}')",
    "",
    "# Predicciones del test set para reporte comparativo",
    "predictions_df = pd.DataFrame({",
    "    'doc_id': X_test.index.map(lambda i: docs.loc[i, 'doc_id']),",
    "    'y_true': y_test.values,",
    "    'y_pred': y_test_pred,",
    "    'proba_correct': [y_test_proba[i, list(clf.classes_).index(y)] for i, y in enumerate(y_test)],",
    "})",
    "pred_path = ROOT / 'data' / 'processed' / 'c1_predictions.csv'",
    "predictions_df.to_csv(pred_path, index=False, encoding='utf-8')",
    "print(f'Predicciones guardadas en {pred_path}')",
    "",
    "# Resumen JSON para el reporte",
    "summary = {",
    "    'model': 'C-1 TF-IDF + Logistic Regression',",
    "    'random_state': RANDOM_STATE,",
    "    'n_train': int(len(X_train)),",
    "    'n_val': int(len(X_val)),",
    "    'n_test': int(len(X_test)),",
    "    'classes': list(clf.classes_),",
    "    'vocab_size': int(len(vectorizer.vocabulary_)),",
    "    'test_accuracy': float(test_acc),",
    "    'test_macro_f1': float(test_macro_f1),",
    "    'test_weighted_f1': float(test_weighted_f1),",
    "    'training_time_s': float(elapsed),",
    "}",
    "with open(MODELS_DIR / 'metrics.json', 'w') as f:",
    "    json.dump(summary, f, indent=2)",
    "print(f'Resumen: {summary}')",
))

cells.append(md(
    "## 12. Conclusion",
    "",
    "Este notebook produce el **baseline obligatorio C-1**. El criterio de exito es:",
    "- Macro-F1 reportado para comparacion con C-2 (BETO) y C-3 (LayoutLMv3) en `nb11`/`nb12`",
    "- BETO debe superar este baseline en al menos +5 puntos para justificar su costo computacional (segun el plan)",
    "",
    "**Siguiente paso:** ejecutar `nb11_clasificacion_C2_beto.ipynb` en Colab GPU usando el MISMO split (random_state=42) para comparacion justa.",
))


nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook generado: {OUT}")
print(f"Tamano: {OUT.stat().st_size:,} bytes")
print(f"Celdas: {len(cells)} ({sum(1 for c in cells if c['cell_type']=='code')} code, {sum(1 for c in cells if c['cell_type']=='markdown')} markdown)")
