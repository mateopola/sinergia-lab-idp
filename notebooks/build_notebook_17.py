"""
Genera notebooks/17_ner_NER2_crf.ipynb

Candidato NER-2: Conditional Random Fields (sklearn-crfsuite). ML clásico,
baseline obligatorio del benchmark NER pre-deep-learning.
Ver FASE_3_1_NER.md §3.2, fundamentado en Lafferty/McCallum/Pereira ICML 2001.

Inputs:
- data/processed/ner/<tip>/{train,dev,test}.jsonl

Outputs:
- models/ner2_crf/<tip>.crfsuite
- reports/nb17_resumen.md + reports/nb17_resumen.json
- data/processed/ner/<tip>/predictions_ner2_test.jsonl
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "17_ner_NER2_crf.ipynb"


def md(*lines):
    return {"cell_type": "markdown", "metadata": {}, "source": [l + "\n" for l in lines]}


def code(*lines):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [l + "\n" for l in lines],
    }


cells = []

cells.append(md(
    "# nb17 - NER-2 Conditional Random Fields",
    "",
    "**Candidato NER-2** de Fase 3.1. ML clásico con features hand-crafted sobre tokens (Lafferty/McCallum/Pereira ICML 2001).",
    "Ver [FASE_3_1_NER.md](../FASE_3_1_NER.md).",
    "",
    "Cada tipología se entrena por separado (4 modelos × tipología). Features:",
    "word, lowercase, is_upper/is_digit, prefix-2/3, suffix-2/3, length, has_punct,",
    "y contexto ±1 token. Optimizador L-BFGS, max_iter=100.",
))

cells.append(md("## 1. Imports y configuración"))

cells.append(code(
    "from __future__ import annotations",
    "import json, sys",
    "from pathlib import Path",
    "",
    "import joblib",
    "import sklearn_crfsuite",
    "",
    "ROOT = Path('..').resolve()",
    "if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))",
    "",
    "from src.ner_eval import load_split, score_predictions, PredSpan, bio_tags_to_spans, fmt_per_label_table",
    "",
    "REPORTS = ROOT / 'reports'",
    "DATA    = ROOT / 'data' / 'processed' / 'ner'",
    "MODELS  = ROOT / 'models' / 'ner2_crf'",
    "REPORTS.mkdir(parents=True, exist_ok=True)",
    "MODELS.mkdir(parents=True, exist_ok=True)",
    "TIPOLOGIAS = ('cc', 'ced', 'pol', 'rut')",
))

cells.append(md(
    "## 2. Featurización por token",
    "",
    "Features clásicas de la literatura NER (lower-case, prefix/suffix, case info,",
    "dígitos, contexto ±1). Sin POS — evitamos depender de `es_core_news_sm`.",
))

cells.append(code(
    "import string",
    "PUNCT = set(string.punctuation)",
    "",
    "def token_features(tokens, i):",
    "    tok = tokens[i]",
    "    feats = {",
    "        'bias': 1.0,",
    "        'tok':         tok,",
    "        'tok.lower':   tok.lower(),",
    "        'pre2':        tok[:2],",
    "        'pre3':        tok[:3],",
    "        'suf2':        tok[-2:],",
    "        'suf3':        tok[-3:],",
    "        'is_upper':    tok.isupper(),",
    "        'is_title':    tok.istitle(),",
    "        'is_digit':    tok.isdigit(),",
    "        'has_digit':   any(c.isdigit() for c in tok),",
    "        'has_punct':   any(c in PUNCT for c in tok),",
    "        'len':         len(tok),",
    "    }",
    "    if i > 0:",
    "        prev = tokens[i-1]",
    "        feats.update({'-1:tok.lower': prev.lower(),",
    "                       '-1:is_upper': prev.isupper(),",
    "                       '-1:is_digit': prev.isdigit()})",
    "    else:",
    "        feats['BOS'] = True",
    "    if i < len(tokens)-1:",
    "        nxt = tokens[i+1]",
    "        feats.update({'+1:tok.lower': nxt.lower(),",
    "                       '+1:is_upper': nxt.isupper(),",
    "                       '+1:is_digit': nxt.isdigit()})",
    "    else:",
    "        feats['EOS'] = True",
    "    return feats",
    "",
    "def doc_to_xy(rec):",
    "    toks = rec['tokens']",
    "    X = [token_features(toks, i) for i in range(len(toks))]",
    "    y = list(rec['tags'])",
    "    return X, y",
))

cells.append(md(
    "## 3. Entrenar 4 modelos CRF (uno por tipología)",
))

cells.append(code(
    "import time",
    "",
    "models = {}",
    "for tip in TIPOLOGIAS:",
    "    t0 = time.time()",
    "    train = load_split(tip, 'train')",
    "    Xy = [doc_to_xy(r) for r in train]",
    "    X_train = [x for x, _ in Xy]",
    "    y_train = [y for _, y in Xy]",
    "    crf = sklearn_crfsuite.CRF(",
    "        algorithm='lbfgs',",
    "        c1=0.1, c2=0.1,",
    "        max_iterations=100,",
    "        all_possible_transitions=True,",
    "    )",
    "    crf.fit(X_train, y_train)",
    "    elapsed = time.time() - t0",
    "    models[tip] = crf",
    "    joblib.dump(crf, MODELS / f'{tip}.joblib')",
    "    print(f'  {tip}: train={len(train)} docs, entrenado en {elapsed:.1f}s, '",
    "          f'transitions={len(crf.transition_features_)}')",
))

cells.append(md(
    "## 4. Evaluar sobre test por tipología",
))

cells.append(code(
    "results = {}",
    "for tip, crf in models.items():",
    "    test = load_split(tip, 'test')",
    "    X_test = [token_features(r['tokens'], i) for r in test for i in range(len(r['tokens']))]",
    "    # Predecir doc por doc para mapear a spans",
    "    preds_spans = {}",
    "    for r in test:",
    "        X = [token_features(r['tokens'], i) for i in range(len(r['tokens']))]",
    "        pred_tags = crf.predict_single(X)",
    "        offsets = [tuple(o) for o in r['offsets']]",
    "        pspans = bio_tags_to_spans(offsets, pred_tags)",
    "        preds_spans[r['doc_id']] = pspans",
    "    scored = score_predictions(test, preds_spans)",
    "    results[tip] = {'scores': scored, 'preds': preds_spans, 'records': test}",
    "    print(f\"  {tip.upper():4s}  macro F1={scored['macro_f1']:.3f}  micro F1={scored['micro_f1']:.3f}  support={scored['support']}\")",
))

cells.append(md(
    "## 5. Tablas detalladas",
))

cells.append(code(
    "for tip, blk in results.items():",
    "    print('='*70)",
    "    print(f'TIPOLOGIA {tip.upper()}')",
    "    print('='*70)",
    "    print(fmt_per_label_table(blk['scores'], header=f'NER-2 CRF - {tip} (test)'))",
    "    print()",
))

cells.append(md(
    "## 6. Persistir resultados",
))

cells.append(code(
    "summary = {}",
    "for tip, blk in results.items():",
    "    s = blk['scores']",
    "    summary[tip] = {",
    "        'macro_f1': s['macro_f1'], 'micro_f1': s['micro_f1'],",
    "        'micro_p':  s['micro_p'],  'micro_r':  s['micro_r'],",
    "        'support':  s['support'],  'per_label': s['per_label'],",
    "    }",
    "(REPORTS / 'nb17_resumen.json').write_text(",
    "    json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')",
    "",
    "lines = ['# nb17 - NER-2 CRF (test set)\\n']",
    "lines.append('## Macro/Micro F1 por tipología\\n')",
    "lines.append('| Tipología | Macro F1 | Micro F1 | Micro P | Micro R | Support |')",
    "lines.append('|---|---:|---:|---:|---:|---:|')",
    "for tip, s in summary.items():",
    "    lines.append(f'| **{tip.upper()}** | {s[\"macro_f1\"]:.3f} | {s[\"micro_f1\"]:.3f} | '",
    "                 f'{s[\"micro_p\"]:.3f} | {s[\"micro_r\"]:.3f} | {s[\"support\"]} |')",
    "lines.append('')",
    "for tip, blk in results.items():",
    "    lines.append(f'## {tip.upper()} — detalle por etiqueta\\n')",
    "    lines.append(fmt_per_label_table(blk['scores']))",
    "    lines.append('')",
    "(REPORTS / 'nb17_resumen.md').write_text('\\n'.join(lines), encoding='utf-8')",
    "print('reports/nb17_resumen.{json,md} escritos')",
    "",
    "for tip, blk in results.items():",
    "    out = DATA / tip / 'predictions_ner2_test.jsonl'",
    "    with out.open('w', encoding='utf-8') as fh:",
    "        for r in blk['records']:",
    "            ps = [{'start': p.start, 'end': p.end, 'label': p.label,",
    "                   'text': r['text'][p.start:p.end]}",
    "                  for p in blk['preds'].get(r['doc_id'], [])]",
    "            fh.write(json.dumps({'doc_id': r['doc_id'], 'preds': ps}, ensure_ascii=False) + '\\n')",
    "    print(f'  preds: {out.relative_to(ROOT)}')",
))

cells.append(md(
    "---",
    "**Siguiente:** [18_ner_NER3_spacy_cnn.ipynb](18_ner_NER3_spacy_cnn.ipynb)",
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

OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"escrito {OUT}")
