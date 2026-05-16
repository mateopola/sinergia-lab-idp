"""
Genera notebooks/18_ner_NER3_spacy_cnn.ipynb

Candidato NER-3: spaCy v3 + CNN tok2vec (no transformer). Deep learning ligero,
entrenable en CPU. Ver FASE_3_1_NER.md §3.2 (Honnibal & Montani, Zenodo DOI).

Inputs:
- data/processed/ner/<tip>/{train,dev,test}.jsonl

Outputs:
- models/ner3_spacy/<tip>/  (modelo spaCy serializado)
- reports/nb18_resumen.md + reports/nb18_resumen.json
- data/processed/ner/<tip>/predictions_ner3_test.jsonl
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "18_ner_NER3_spacy_cnn.ipynb"


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
    "# nb18 - NER-3 spaCy v3 + CNN tok2vec",
    "",
    "**Candidato NER-3** de Fase 3.1. Deep learning ligero — sin transformer.",
    "Pipeline NER nativo de spaCy v3 con embeddings + CNN convolucional.",
    "Ver [FASE_3_1_NER.md](../FASE_3_1_NER.md).",
    "",
    "Se entrena un modelo independiente por tipología sobre el dataset BIO de nb15.",
    "Sin pre-entreno: `spacy.blank('es')` da solo el tokenizer; el componente NER",
    "se entrena desde cero. Eso mantiene la comparación contra NER-1 y NER-2 honesta.",
))

cells.append(md("## 1. Imports y configuración"))

cells.append(code(
    "from __future__ import annotations",
    "import json, random, sys, time",
    "from pathlib import Path",
    "",
    "import spacy",
    "from spacy.training import Example",
    "from spacy.util import minibatch, compounding",
    "",
    "ROOT = Path('..').resolve()",
    "if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))",
    "",
    "from src.ner_eval import load_split, score_predictions, PredSpan, fmt_per_label_table",
    "",
    "REPORTS = ROOT / 'reports'",
    "DATA    = ROOT / 'data' / 'processed' / 'ner'",
    "MODELS  = ROOT / 'models' / 'ner3_spacy'",
    "REPORTS.mkdir(parents=True, exist_ok=True)",
    "MODELS.mkdir(parents=True, exist_ok=True)",
    "TIPOLOGIAS = ('cc', 'ced', 'pol', 'rut')",
    "SEED = 42",
    "N_EPOCHS = 30",
    "",
    "random.seed(SEED)",
    "print('spaCy:', spacy.__version__)",
))

cells.append(md(
    "## 2. JSONL → spaCy Examples",
    "",
    "Convertimos cada record al formato `(text, {'entities': [(start, end, label), ...]})`.",
    "Los spans del JSONL ya están en convención Python (end exclusivo).",
    "Como la tokenización spaCy puede no alinear perfectamente con nuestra tokenización",
    "regex de nb15, usamos `Doc.char_span(alignment_mode='contract')` para spans que",
    "no cuadran exacto con boundaries de token spaCy.",
))

cells.append(code(
    "def _filter_overlap(triples):",
    "    \"\"\"Acepta (start, end, label) en orden, descarta cualquier span que solape",
    "    con uno ya aceptado. Prioriza por (start asc, length desc) para conservar el span mayor.\"\"\"",
    "    triples = sorted(triples, key=lambda t: (t[0], -(t[1]-t[0])))",
    "    kept, used = [], []",
    "    for s, e, lab in triples:",
    "        if any(not (e <= us or s >= ue) for us, ue in used):",
    "            continue",
    "        kept.append((s, e, lab))",
    "        used.append((s, e))",
    "    return kept",
    "",
    "def records_to_examples(nlp, records):",
    "    examples = []",
    "    skipped_align = 0",
    "    dropped_overlap = 0",
    "    for r in records:",
    "        doc = nlp.make_doc(r['text'])",
    "        raw = []",
    "        for s in r['spans']:",
    "            span = doc.char_span(s['start'], s['end'], label=s['label'], alignment_mode='contract')",
    "            if span is None:",
    "                skipped_align += 1",
    "                continue",
    "            raw.append((span.start_char, span.end_char, span.label_))",
    "        filtered = _filter_overlap(raw)",
    "        dropped_overlap += len(raw) - len(filtered)",
    "        ex = Example.from_dict(doc, {'entities': filtered})",
    "        examples.append(ex)",
    "    return examples, skipped_align, dropped_overlap",
))

cells.append(md(
    "## 3. Entrenamiento por tipología",
    "",
    "Pipeline mínimo: `ner` (CNN tok2vec por defecto). Dropout 0.3, batches dinámicos",
    "`compounding(4, 16, 1.001)`. 30 épocas; suficiente para corpus pequeño en CPU.",
))

cells.append(code(
    "models = {}",
    "training_logs = {}",
    "",
    "for tip in TIPOLOGIAS:",
    "    print(f'\\n=== {tip.upper()} ===')",
    "    t0 = time.time()",
    "    train_recs = load_split(tip, 'train')",
    "    dev_recs   = load_split(tip, 'dev')",
    "",
    "    nlp = spacy.blank('es')",
    "    ner = nlp.add_pipe('ner', last=True)",
    "    for r in train_recs:",
    "        for s in r['spans']:",
    "            ner.add_label(s['label'])",
    "",
    "    train_examples, sk_tr, ov_tr = records_to_examples(nlp, train_recs)",
    "    print(f'  train: {len(train_examples)} examples, {sk_tr} no-alinean, {ov_tr} solapados descartados')",
    "    dev_examples, sk_dev, ov_dev = records_to_examples(nlp, dev_recs)",
    "",
    "    optimizer = nlp.initialize(lambda: train_examples)",
    "    log = []",
    "    for epoch in range(N_EPOCHS):",
    "        random.shuffle(train_examples)",
    "        losses = {}",
    "        for batch in minibatch(train_examples, size=compounding(4.0, 16.0, 1.001)):",
    "            nlp.update(batch, drop=0.3, losses=losses, sgd=optimizer)",
    "        if epoch % 5 == 0 or epoch == N_EPOCHS-1:",
    "            log.append({'epoch': epoch, 'ner_loss': float(losses.get('ner', 0.0))})",
    "            print(f'  epoch {epoch:3d}: ner_loss={losses.get(\"ner\", 0):.2f}')",
    "    elapsed = time.time() - t0",
    "    print(f'  entrenado en {elapsed:.1f}s')",
    "",
    "    out_dir = MODELS / tip",
    "    nlp.to_disk(out_dir)",
    "    models[tip] = nlp",
    "    training_logs[tip] = {'elapsed_s': elapsed, 'log': log}",
))

cells.append(md(
    "## 4. Evaluar sobre test",
))

cells.append(code(
    "results = {}",
    "for tip, nlp in models.items():",
    "    test = load_split(tip, 'test')",
    "    preds_spans = {}",
    "    for r in test:",
    "        doc = nlp(r['text'])",
    "        ps = [PredSpan(ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]",
    "        preds_spans[r['doc_id']] = ps",
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
    "    print(fmt_per_label_table(blk['scores'], header=f'NER-3 spaCy+CNN - {tip} (test)'))",
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
    "        'train_elapsed_s': training_logs[tip]['elapsed_s'],",
    "    }",
    "(REPORTS / 'nb18_resumen.json').write_text(",
    "    json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')",
    "",
    "lines = ['# nb18 - NER-3 spaCy v3 + CNN (test set)\\n']",
    "lines.append('## Macro/Micro F1 por tipología\\n')",
    "lines.append('| Tipología | Macro F1 | Micro F1 | Micro P | Micro R | Support | Train s |')",
    "lines.append('|---|---:|---:|---:|---:|---:|---:|')",
    "for tip, s in summary.items():",
    "    lines.append(f'| **{tip.upper()}** | {s[\"macro_f1\"]:.3f} | {s[\"micro_f1\"]:.3f} | '",
    "                 f'{s[\"micro_p\"]:.3f} | {s[\"micro_r\"]:.3f} | {s[\"support\"]} | '",
    "                 f'{s[\"train_elapsed_s\"]:.1f} |')",
    "lines.append('')",
    "for tip, blk in results.items():",
    "    lines.append(f'## {tip.upper()} — detalle por etiqueta\\n')",
    "    lines.append(fmt_per_label_table(blk['scores']))",
    "    lines.append('')",
    "(REPORTS / 'nb18_resumen.md').write_text('\\n'.join(lines), encoding='utf-8')",
    "print('reports/nb18_resumen.{json,md} escritos')",
    "",
    "for tip, blk in results.items():",
    "    out = DATA / tip / 'predictions_ner3_test.jsonl'",
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
    "**Siguiente:** [19_ner_comparativa.ipynb](19_ner_comparativa.ipynb)",
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
