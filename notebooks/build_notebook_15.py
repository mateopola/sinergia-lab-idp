"""
Genera notebooks/15_ner_dataset_construccion.ipynb

Construye el dataset BIO unificado para los 3 candidatos NER de Fase 3.1 (NER-1
Regex / NER-2 CRF / NER-3 spaCy+CNN). Ver FASE_3_1_NER.md.

Inputs:
- data/raw/ner_annotations/*.ndjson     (3 exports Labelbox)
- data/raw/ner_corpus/{data_row_id}.txt (textos subidos a Labelbox)

Outputs:
- data/processed/ner/{cc,ced,pol,rut}/{train,dev,test}.jsonl
- reports/nb15_resumen.md + reports/nb15_resumen.json

Hallazgos clave que el notebook codifica:
- Offset Labelbox es `end` inclusivo: token == txt[start:end+1].
- Tipologia se infiere por prefijo del label (CC_, CED_, POL_, RUT_); en el corpus
  actual 553/559 docs son homogeneos, 6 no tienen anotaciones, 0 mixtos.

Run en CPU local sin dependencias pesadas (solo stdlib + pandas + sklearn).
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "15_ner_dataset_construccion.ipynb"


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
    "# nb15 - Dataset BIO unificado para NER (Fase 3.1)",
    "",
    "**Objetivo:** parsear los 3 exports NDJSON de Labelbox, alinearlos con los .txt",
    "descargados, normalizar a formato BIO por tipologia y generar splits 70/15/15",
    "reproducibles que alimentan los 3 candidatos NER de Fase 3.1.",
    "",
    "Ver [FASE_3_1_NER.md](../FASE_3_1_NER.md).",
    "",
    "**Hallazgos validados antes de construir el notebook:**",
    "- Labelbox usa `end` **inclusivo** (`token == txt[start:end+1]`). Verificado al 100% sobre 2,119 anotaciones.",
    "- 553/559 docs son **homogeneos en tipologia** (los 6 restantes no tienen anotaciones).",
    "- Todos los .txt referenciados estan en `data/raw/ner_corpus/`.",
    "",
    "**Split:** 70/15/15 estratificado por tipologia, `random_state=42` (consistente con Fase 3.0).",
    "",
    "**Hardware:** CPU local. Sin dependencias pesadas (solo stdlib + pandas + sklearn).",
))

cells.append(md("## 1. Imports y configuracion"))

cells.append(code(
    "from __future__ import annotations",
    "import json",
    "import re",
    "import sys",
    "from collections import Counter, defaultdict",
    "from pathlib import Path",
    "",
    "import pandas as pd",
    "from sklearn.model_selection import train_test_split",
    "",
    "ROOT = Path('..')",
    "ANNOT_DIR = ROOT / 'data' / 'raw' / 'ner_annotations'",
    "TXT_DIR   = ROOT / 'data' / 'raw' / 'ner_corpus'",
    "OUT_DIR   = ROOT / 'data' / 'processed' / 'ner'",
    "REPORTS   = ROOT / 'reports'",
    "OUT_DIR.mkdir(parents=True, exist_ok=True)",
    "REPORTS.mkdir(parents=True, exist_ok=True)",
    "",
    "RANDOM_STATE = 42",
    "SPLIT = (0.70, 0.15, 0.15)  # train / dev / test",
    "",
    "NDJSON_FILES = [",
    "    'export_Sebas_20260513.ndjson',",
    "    'Export  project - NER_Documentos_CAMILO.ndjson',",
    "    'export_Mateo_20260512 (1).ndjson',",
    "]",
    "",
    "ANOTADOR = {",
    "    'export_Sebas_20260513.ndjson':              'sebas',",
    "    'Export  project - NER_Documentos_CAMILO.ndjson': 'camilo',",
    "    'export_Mateo_20260512 (1).ndjson':           'mateo',",
    "}",
    "",
    "# Prefijo del label -> codigo de tipologia",
    "PREFIX_TO_TIP = {'CC': 'cc', 'CED': 'ced', 'POL': 'pol', 'RUT': 'rut'}",
    "",
    "print('annot dir :', ANNOT_DIR.resolve())",
    "print('txt dir   :', TXT_DIR.resolve())",
    "print('out dir   :', OUT_DIR.resolve())",
))

cells.append(md(
    "## 2. Parsear NDJSON y alinear con los .txt",
    "",
    "Por cada doc:",
    "1. Leer texto plano desde `ner_corpus/{data_row_id}.txt`.",
    "2. Extraer todas las anotaciones (`TextEntity`) con `start`, `end`, `name`, `token`.",
    "3. Convertir offset Labelbox **inclusivo** -> slice Python **exclusivo**: `end_excl = end + 1`.",
    "4. Inferir tipologia desde el prefijo de los labels presentes.",
    "5. Validar que `token == txt[start:end_excl]` (si no, descartar span con warning).",
))

cells.append(code(
    "def parse_ndjson_files() -> list[dict]:",
    "    docs = []",
    "    for fname in NDJSON_FILES:",
    "        path = ANNOT_DIR / fname",
    "        with path.open(encoding='utf-8') as fh:",
    "            for line in fh:",
    "                if not line.strip():",
    "                    continue",
    "                obj = json.loads(line)",
    "                rid = obj['data_row']['id']",
    "                ext = obj['data_row'].get('external_id', '')",
    "                txt_path = TXT_DIR / f'{rid}.txt'",
    "                if not txt_path.exists():",
    "                    continue",
    "                txt = txt_path.read_text(encoding='utf-8')",
    "",
    "                spans = []",
    "                prefixes_in_doc = set()",
    "                for pid, pdata in obj.get('projects', {}).items():",
    "                    for lab in pdata.get('labels', []):",
    "                        for o in lab.get('annotations', {}).get('objects', []):",
    "                            if o.get('annotation_kind') != 'TextEntity':",
    "                                continue",
    "                            name = o.get('name', '?')",
    "                            pref = name.split('_', 1)[0]",
    "                            prefixes_in_doc.add(pref)",
    "                            loc = o.get('location', {})",
    "                            s, e, tok = loc.get('start'), loc.get('end'), loc.get('token', '')",
    "                            if s is None or e is None:",
    "                                continue",
    "                            end_excl = e + 1  # Labelbox inclusivo -> Python exclusivo",
    "                            actual = txt[s:end_excl]",
    "                            if actual != tok:",
    "                                # tolerancia: el campo 'token' puede tener normalizacion;",
    "                                # confiamos en el texto del .txt como fuente unica de verdad",
    "                                if actual.strip() == '':",
    "                                    continue",
    "                            spans.append({",
    "                                'start': s,",
    "                                'end':   end_excl,  # convencion Python (exclusivo)",
    "                                'label': name,",
    "                                'text':  actual,",
    "                            })",
    "",
    "                if len(prefixes_in_doc) == 1:",
    "                    tip = PREFIX_TO_TIP.get(next(iter(prefixes_in_doc)))",
    "                elif len(prefixes_in_doc) == 0:",
    "                    tip = None  # sin anotaciones",
    "                else:",
    "                    tip = '__mixta__'",
    "",
    "                docs.append({",
    "                    'doc_id':    rid,",
    "                    'external_id': ext,",
    "                    'anotador':  ANOTADOR.get(fname, '?'),",
    "                    'tipologia': tip,",
    "                    'n_chars':   len(txt),",
    "                    'n_spans':   len(spans),",
    "                    'text':      txt,",
    "                    'spans':     spans,",
    "                })",
    "    return docs",
    "",
    "docs = parse_ndjson_files()",
    "print(f'TOTAL docs cargados: {len(docs)}')",
    "by_tip = Counter(d['tipologia'] for d in docs)",
    "by_anot = Counter(d['anotador'] for d in docs)",
    "print(f'\\nPor tipologia: {dict(by_tip)}')",
    "print(f'Por anotador : {dict(by_anot)}')",
    "print(f'Total spans   : {sum(d[\"n_spans\"] for d in docs)}')",
))

cells.append(md(
    "## 3. Tokenizacion default + alineacion a BIO",
    "",
    "Tokenizamos con regex `\\w+|[^\\w\\s]` (palabras y signos sueltos). Esta tokenizacion",
    "es **canonica para el dataset JSONL** y la que consumen NER-1 (Regex) y NER-2 (CRF).",
    "El notebook 18 (NER-3 spaCy) puede retokenizar con el tokenizer de spaCy y rehacer la",
    "alineacion desde los spans char, que son la verdad ultima.",
    "",
    "**Algoritmo BIO:**",
    "- Para cada token en `(start_tok, end_tok)`, buscar la primera anotacion con `start <= start_tok < end`.",
    "- Si hay match y `start_tok == ann.start`: tag = `B-<label>`.",
    "- Si hay match pero `start_tok > ann.start`: tag = `I-<label>`.",
    "- Sin match: tag = `O`.",
    "- Si un token cae parcialmente dentro y fuera (boundary), se respeta el span de la anotacion.",
))

cells.append(code(
    "TOKEN_RE = re.compile(r'\\w+|[^\\w\\s]', flags=re.UNICODE)",
    "",
    "def tokenize_with_offsets(text: str) -> list[tuple[str, int, int]]:",
    "    return [(m.group(), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]",
    "",
    "def spans_to_bio(tokens: list[tuple[str,int,int]], spans: list[dict]) -> list[str]:",
    "    # Ordenar spans por start; resolver solapamientos por orden de aparicion",
    "    spans_sorted = sorted(spans, key=lambda s: (s['start'], -s['end']))",
    "    tags = ['O'] * len(tokens)",
    "    si = 0",
    "    for ti, (_, t_s, t_e) in enumerate(tokens):",
    "        # Avanzar puntero de spans descartando los que ya quedaron atras",
    "        while si < len(spans_sorted) and spans_sorted[si]['end'] <= t_s:",
    "            si += 1",
    "        if si >= len(spans_sorted):",
    "            break",
    "        sp = spans_sorted[si]",
    "        # token intersecta con el span?",
    "        if t_s < sp['end'] and t_e > sp['start']:",
    "            inside = (t_s > sp['start'])",
    "            tags[ti] = ('I-' if inside else 'B-') + sp['label']",
    "    return tags",
    "",
    "def build_record(doc: dict) -> dict:",
    "    toks = tokenize_with_offsets(doc['text'])",
    "    tags = spans_to_bio(toks, doc['spans'])",
    "    return {",
    "        'doc_id':    doc['doc_id'],",
    "        'external_id': doc['external_id'],",
    "        'anotador':  doc['anotador'],",
    "        'tipologia': doc['tipologia'],",
    "        'text':      doc['text'],",
    "        'tokens':    [t for t,_,_ in toks],",
    "        'offsets':   [[s,e] for _,s,e in toks],",
    "        'tags':      tags,",
    "        'spans':     doc['spans'],",
    "    }",
    "",
    "# smoke test sobre 1 doc con spans",
    "_sample = next(d for d in docs if d['n_spans'] > 0)",
    "_rec = build_record(_sample)",
    "print(f\"sample doc: {_rec['doc_id']}  tip={_rec['tipologia']}  tokens={len(_rec['tokens'])}  spans={len(_rec['spans'])}\")",
    "_tags_nonO = [(t,g) for t,g in zip(_rec['tokens'], _rec['tags']) if g != 'O']",
    "for tk, tg in _tags_nonO[:15]:",
    "    print(f'  {tg:30}  {tk}')",
))

cells.append(md(
    "## 4. Filtrar docs anotados y agrupar por tipologia",
    "",
    "Descartamos los 6 docs sin anotaciones (no aportan supervision) y los",
    "(posiblemente 0) docs con tipologia mixta. Los 553 restantes se agrupan por",
    "tipologia para los splits.",
))

cells.append(code(
    "TIP_VALIDAS = ('cc', 'ced', 'pol', 'rut')",
    "",
    "records = []",
    "descartados = Counter()",
    "for d in docs:",
    "    if d['tipologia'] not in TIP_VALIDAS:",
    "        descartados[d['tipologia']] += 1",
    "        continue",
    "    if d['n_spans'] == 0:",
    "        descartados['sin_spans'] += 1",
    "        continue",
    "    records.append(build_record(d))",
    "",
    "print(f'records utiles : {len(records)}')",
    "print(f'descartados    : {dict(descartados)}')",
    "",
    "by_tip = defaultdict(list)",
    "for r in records:",
    "    by_tip[r['tipologia']].append(r)",
    "for tip, recs in sorted(by_tip.items()):",
    "    print(f'  {tip}: {len(recs)} docs')",
))

cells.append(md(
    "## 5. Split estratificado 70/15/15 por tipologia",
    "",
    "Dentro de cada tipologia, split aleatorio reproducible con `random_state=42`.",
    "Como cada tipologia es su propio dataset (un modelo por tipologia, ver",
    "FASE_3_1_NER.md), no necesitamos estratificacion inter-tipologia.",
))

cells.append(code(
    "def split_70_15_15(items: list, seed: int = RANDOM_STATE) -> dict:",
    "    rest, test = train_test_split(items, test_size=0.15, random_state=seed, shuffle=True)",
    "    # dev = 0.15 del total => 0.1765 del 'rest' (que es 85% del total)",
    "    train, dev = train_test_split(rest, test_size=0.15/0.85, random_state=seed, shuffle=True)",
    "    return {'train': train, 'dev': dev, 'test': test}",
    "",
    "splits = {tip: split_70_15_15(recs) for tip, recs in by_tip.items()}",
    "for tip, sp in splits.items():",
    "    print(f'  {tip}: train={len(sp[\"train\"]):3d}  dev={len(sp[\"dev\"]):3d}  test={len(sp[\"test\"]):3d}')",
))

cells.append(md(
    "## 6. Exportar JSONL por tipologia y split",
    "",
    "Estructura final:",
    "```",
    "data/processed/ner/",
    "  cc/{train,dev,test}.jsonl",
    "  ced/{train,dev,test}.jsonl",
    "  pol/{train,dev,test}.jsonl",
    "  rut/{train,dev,test}.jsonl",
    "```",
    "Cada linea es un doc con `{doc_id, external_id, anotador, tipologia, text, tokens, offsets, tags, spans}`.",
))

cells.append(code(
    "def dump_jsonl(records: list[dict], path: Path) -> None:",
    "    path.parent.mkdir(parents=True, exist_ok=True)",
    "    with path.open('w', encoding='utf-8') as fh:",
    "        for r in records:",
    "            fh.write(json.dumps(r, ensure_ascii=False) + '\\n')",
    "",
    "for tip, sp in splits.items():",
    "    base = OUT_DIR / tip",
    "    for split_name, recs in sp.items():",
    "        out = base / f'{split_name}.jsonl'",
    "        dump_jsonl(recs, out)",
    "        print(f'  escrito {out.relative_to(ROOT)}  ({len(recs)} docs)')",
))

cells.append(md(
    "## 7. Reporte de calidad (distribucion de etiquetas por tipologia y split)",
))

cells.append(code(
    "def label_counts(records: list[dict]) -> Counter:",
    "    c = Counter()",
    "    for r in records:",
    "        for s in r['spans']:",
    "            c[s['label']] += 1",
    "    return c",
    "",
    "report = {",
    "    'random_state': RANDOM_STATE,",
    "    'split': SPLIT,",
    "    'by_tipologia': {},",
    "}",
    "",
    "for tip, sp in splits.items():",
    "    tip_block = {",
    "        'docs_total': sum(len(v) for v in sp.values()),",
    "        'docs_split': {k: len(v) for k,v in sp.items()},",
    "        'labels_total': dict(label_counts([r for v in sp.values() for r in v])),",
    "        'labels_por_split': {k: dict(label_counts(v)) for k,v in sp.items()},",
    "        'tokens_total': sum(len(r['tokens']) for v in sp.values() for r in v),",
    "    }",
    "    report['by_tipologia'][tip] = tip_block",
    "",
    "rep_path = REPORTS / 'nb15_resumen.json'",
    "rep_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')",
    "print(f'reporte JSON: {rep_path.relative_to(ROOT)}')",
    "",
    "rows = []",
    "for tip, blk in report['by_tipologia'].items():",
    "    for lbl, cnt in sorted(blk['labels_total'].items()):",
    "        rows.append({'tipologia': tip, 'label': lbl, 'count': cnt})",
    "df_summary = pd.DataFrame(rows).pivot_table(",
    "    index='label', columns='tipologia', values='count', fill_value=0",
    ").astype(int)",
    "df_summary",
))

cells.append(code(
    "# Verificacion final: ningun span quedo huerfano (text[span.start:span.end] == span.text)",
    "errors = 0",
    "for tip, sp in splits.items():",
    "    for split_name, recs in sp.items():",
    "        for r in recs:",
    "            for s in r['spans']:",
    "                if r['text'][s['start']:s['end']] != s['text']:",
    "                    errors += 1",
    "print(f'verificacion final - spans corruptos: {errors}')",
))

cells.append(md(
    "## 8. Resumen Markdown para el ritual de WORKFLOW",
))

cells.append(code(
    "lines = []",
    "lines.append('# nb15 - Dataset BIO unificado para NER\\n')",
    "lines.append(f'random_state={RANDOM_STATE}, split={SPLIT}\\n')",
    "lines.append('## Conteo de docs por tipologia y split\\n')",
    "lines.append('| Tipologia | Train | Dev | Test | Total |')",
    "lines.append('|---|---|---|---|---|')",
    "for tip, sp in splits.items():",
    "    t, d, te = len(sp['train']), len(sp['dev']), len(sp['test'])",
    "    lines.append(f'| {tip.upper()} | {t} | {d} | {te} | {t+d+te} |')",
    "lines.append('')",
    "lines.append('## Conteo de entidades por tipologia (total = train+dev+test)\\n')",
    "for tip, blk in report['by_tipologia'].items():",
    "    lines.append(f'### {tip.upper()}\\n')",
    "    lines.append('| Etiqueta | Count |')",
    "    lines.append('|---|---|')",
    "    for lbl, cnt in sorted(blk['labels_total'].items(), key=lambda x: -x[1]):",
    "        lines.append(f'| `{lbl}` | {cnt} |')",
    "    lines.append('')",
    "",
    "(REPORTS / 'nb15_resumen.md').write_text('\\n'.join(lines), encoding='utf-8')",
    "print('reporte MD: reports/nb15_resumen.md')",
))

cells.append(md(
    "---",
    "## Cierre",
    "",
    "El dataset BIO unificado queda listo en `data/processed/ner/{cc,ced,pol,rut}/`.",
    "Cada uno de los 3 candidatos NER (Regex / CRF / spaCy+CNN) consumira el mismo",
    "split para garantizar comparacion justa.",
    "",
    "**Siguiente paso:** [16_ner_NER1_regex_baseline.ipynb](16_ner_NER1_regex_baseline.ipynb)",
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
