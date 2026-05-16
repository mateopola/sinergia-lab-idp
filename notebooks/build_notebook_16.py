"""
Genera notebooks/16_ner_NER1_regex_baseline.ipynb

Candidato NER-1: Regex + Labeling Functions. Baseline trivial obligatorio del
benchmark de Fase 3.1 (ver FASE_3_1_NER.md §3.2).

Inputs:
- data/processed/ner/<tip>/{train,dev,test}.jsonl (de nb15)

Outputs:
- reports/nb16_resumen.md + reports/nb16_resumen.json
- data/processed/ner/<tip>/predictions_ner1_test.jsonl
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "16_ner_NER1_regex_baseline.ipynb"


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
    "# nb16 - NER-1 Regex + LFs (baseline)",
    "",
    "**Candidato NER-1** de Fase 3.1 (ver [FASE_3_1_NER.md](../FASE_3_1_NER.md)).",
    "",
    "Reglas regex con anchors (ej. `Nit`, `Razón Social`, `MATRICULA`) por cada una de las 17 etiquetas.",
    "No requiere entrenamiento: se aplica directo sobre el texto del documento y se reporta F1",
    "entity-level (exact span match) sobre `data/processed/ner/<tip>/test.jsonl`.",
    "",
    "Es la línea base: si los modelos NER-2 y NER-3 no superan estas reglas, no justifican",
    "su complejidad sobre el dominio.",
))

cells.append(md("## 1. Imports"))

cells.append(code(
    "from __future__ import annotations",
    "import json, re, sys",
    "from pathlib import Path",
    "",
    "ROOT = Path('..').resolve()",
    "if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))",
    "",
    "from src.ner_eval import load_split, score_predictions, PredSpan, fmt_per_label_table",
    "",
    "REPORTS = ROOT / 'reports'",
    "DATA    = ROOT / 'data' / 'processed' / 'ner'",
    "REPORTS.mkdir(parents=True, exist_ok=True)",
))

cells.append(md(
    "## 2. Reglas regex por tipología",
    "",
    "Cada LF recibe el texto completo del documento y devuelve una lista de",
    "`PredSpan(start, end, label)`. Las regex usan anchors locales (palabras clave",
    "del formulario) para limitar falsos positivos y aprovechan los patrones",
    "estructurales de los documentos colombianos oficiales.",
))

cells.append(code(
    "# ---------------------------- helpers -----------------------------------",
    "",
    "def _all_matches(pattern: re.Pattern, text: str, label: str, group: int = 1):",
    "    \"\"\"Devuelve PredSpans de todos los matches del grupo `group`.\"\"\"",
    "    out = []",
    "    for m in pattern.finditer(text):",
    "        s, e = m.span(group)",
    "        if e > s:",
    "            out.append(PredSpan(s, e, label))",
    "    return out",
    "",
    "def _first_match(pattern: re.Pattern, text: str, label: str, group: int = 1):",
    "    m = pattern.search(text)",
    "    if not m: return []",
    "    s, e = m.span(group)",
    "    return [PredSpan(s, e, label)] if e > s else []",
    "",
    "def _dedupe(spans):",
    "    seen, out = set(), []",
    "    for s in spans:",
    "        k = (s.start, s.end, s.label)",
    "        if k in seen: continue",
    "        seen.add(k); out.append(s)",
    "    return out",
))

cells.append(code(
    "# ============================ CC ========================================",
    "# Anchors observados en train: 'Razón Social:', 'Nombre', 'Nit', 'MATRICULA',",
    "# 'Matrícula No', 'Fec(h|k)a de matr', 'Fecha de constituci'",
    "",
    "# Boundaries por linea (\\n) para no cruzar al siguiente campo del formulario.",
    "_RX_CC_NIT      = re.compile(r'(?:N\\s*[ií]\\s*t|NIT)[\\s:]*([0-9]{6,12}-?\\s*[0-9]?)', re.I)",
    "_RX_CC_MATRI    = re.compile(r'(?:Matr[íi]cula\\s*No?\\.?|MATRICULA\\s*\\n?N[ºo°]?|^\\s*No)[\\s:]*([0-9]{2}-?[0-9]{4,8}-?[0-9]{0,2})', re.I | re.M)",
    "_RX_CC_RAZON    = re.compile(r'(?:Raz[óo]n\\s+Social|Nombre)[\\s:]*\\n?[ \\t]*([A-ZÁÉÍÓÚÑ][^\\n]{4,80}?)\\s*(?:\\n|,|$)')",
    "_RX_CC_FECHA    = re.compile(r'(?:Fec[hk]a\\s+de\\s+matr[íi:]?cula|Fecha\\s+de\\s+constituci[oó]n)[\\s:]*([0-9]{1,2}\\s+de\\s+[a-zA-Záéíóú:]{3,12}\\s+de\\s+[12][0-9]{3})', re.I)",
    "",
    "def lfs_cc(text):",
    "    return _dedupe(",
    "        _first_match(_RX_CC_NIT,   text, 'CC_NIT') +",
    "        _first_match(_RX_CC_MATRI, text, 'CC_NUM_MATRICULA') +",
    "        _first_match(_RX_CC_RAZON, text, 'CC_RAZON_SOCIAL') +",
    "        _first_match(_RX_CC_FECHA, text, 'CC_FECHA_CONSTITUCION')",
    "    )",
))

cells.append(code(
    "# ============================ CED ========================================",
    "# Anchors: 'NUMERO', 'NUME3O' (OCR noise), 'APELLIDOS', 'NOMBRES'",
    "# Layout cédula: <NUMERO> <APELLIDO> <NOMBRES> <FECHA_NAC> <LUGAR_NAC> ... <FECHA_EXP> <LUGAR_EXP>",
    "",
    "_RX_CED_NUMERO  = re.compile(r'(?:NUMERO|N[UÚ]ME[3R]O|NUMEPO|C[ÉE]DULA\\s+DE\\s+CIUDADAN[ÍI]A)[\\s\\n]*([0-9]{1,3}(?:[\\.,][0-9]{3}){1,3})')",
    "_RX_CED_FECHA_EXP = re.compile(r'([0-9]{1,2}[- ][A-Z]{3}[- ][12][0-9]{3})\\s+[A-ZÁÉÍÓÚÑ]{3,}\\s*\\n+\\s*FECHA\\s+Y\\s+LUGAR\\s+DE\\s+EXPEDICI[ÓO]N', re.I)",
    "_RX_CED_LUGAR_EXP = re.compile(r'[0-9]{1,2}[- ][A-Z]{3}[- ][12][0-9]{3}\\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\\s]{2,40}?)\\s*\\n+\\s*FECHA\\s+Y\\s+LUGAR\\s+DE\\s+EXPEDICI[ÓO]N', re.I)",
    "_RX_CED_APELLIDO  = re.compile(r'(?:NUMERO|N[UÚ]ME[3R]O)[^\\n]*\\n([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\\s]{2,40})\\n', re.M)",
    "_RX_CED_NOMBRE    = re.compile(r'(?:NUMERO|N[UÚ]ME[3R]O)[^\\n]*\\n[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\\s]{2,40}\\n([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\\s]{2,40})\\n', re.M)",
    "",
    "def lfs_ced(text):",
    "    return _dedupe(",
    "        _first_match(_RX_CED_NUMERO,   text, 'CED_NUMERO') +",
    "        _first_match(_RX_CED_FECHA_EXP, text, 'CED_FECHA_EXPEDICION') +",
    "        _first_match(_RX_CED_LUGAR_EXP, text, 'CED_LUGAR_EXPEDICION') +",
    "        _first_match(_RX_CED_APELLIDO, text, 'CED_APELLIDO') +",
    "        _first_match(_RX_CED_NOMBRE,   text, 'CED_NOMBRE')",
    "    )",
))

cells.append(code(
    "# ============================ POL ========================================",
    "# Anchors: 'TOMADOR', 'ASEGURADO', 'BENEFICIARIO', 'PRIMA', '$'",
    "",
    "# Captura limitada a una linea hasta el siguiente keyword (NIT/DIRECCION/CALLE/etc.) o newline.",
    "_RX_POL_TOMADOR     = re.compile(r'(?:TOMADOR|NOMBRE\\s+DEL\\s+TOMADOR)[\\s:]*\\n?[ \\t]*([A-ZÁÉÍÓÚÑ][^\\n]{2,60}?)(?=\\s+(?:NIT|DIRECCI|TEL|IDENTIFICACI|$)|\\n)', re.I)",
    "_RX_POL_ENTIDAD     = re.compile(r'(?:ASEGURADO|BENEFICIAR[I1IK]O)\\b[\\s:\\-]*\\n?[ \\t]*([A-ZÁÉÍÓÚÑ][^\\n]{2,60}?)(?=\\s+(?:NIT|DIRECCI|IDENTIFICACI|TEL|$)|\\n)', re.I)",
    "_RX_POL_PRIMA       = re.compile(r'(?:PRIMA[A-Z\\s]{0,40}PESOS|PRIMA\\s+NETA|VALOR\\s+PRIMA|PRIMA\\s+TOTAL)[\\s\\$\\*:]*([0-9][0-9\\.,\\s]{2,20}[0-9]{1,2})', re.I)",
    "_RX_POL_NUM         = re.compile(r'(?:N[°º]?\\s*(?:DE\\s+)?P[ÓO]LIZA|P[ÓO]LIZA\\s*N[°º]?|NRO\\.?\\s*P[ÓO]LIZA|N[Uu]mero\\s+de\\s+P[óo]liza|GARANTIA\\s+No\\.?)[\\s:]*([A-Z0-9\\-]{4,20})', re.I)",
    "",
    "def lfs_pol(text):",
    "    return _dedupe(",
    "        _first_match(_RX_POL_TOMADOR, text, 'POL_TOMADOR') +",
    "        _first_match(_RX_POL_ENTIDAD, text, 'POL_ENTIDAD_ASEGURADA') +",
    "        _first_match(_RX_POL_PRIMA,   text, 'POL_PRIMA') +",
    "        _first_match(_RX_POL_NUM,     text, 'POL_NUM_POLIZA')",
    "    )",
))

cells.append(code(
    "# ============================ RUT ========================================",
    "# Anchors: 'Razón social', 'Dirección principal', 'Identificación', 'Número de Identificación'",
    "# El NIT en RUT viene en formato DIAN: dígitos con espacios entre cada cifra.",
    "",
    "# Captures one-line only: terminan en newline para no atrapar la siguiente etiqueta del formulario.",
    "_RX_RUT_NIT_GS1   = re.compile(r'\\(8020\\)\\s*([0-9]{12,18})')",
    "_RX_RUT_NIT_PLANO = re.compile(r'(?:NIT|Identificaci[óo]n)[\\s:]*([0-9]{6,15})', re.I)",
    "_RX_RUT_RAZON     = re.compile(r'(?:Raz[óo]n\\s+social|35\\.?\\s*Raz[óo]n)[\\s:]*\\n[ \\t]*([A-ZÁÉÍÓÚÑ][^\\n]{3,80})')",
    "_RX_RUT_DIRECCION = re.compile(r'(?:Direcci[óo]n\\s+principal|41\\.?\\s*Direcci[óo]n)[\\s:]*\\n[ \\t]*((?:CL|CR|AV|TV|KR|AC|DG|CARRERA|CALLE|AVENIDA)[^\\n]{2,60})', re.I)",
    "_RX_RUT_ACTECO    = re.compile(r'(?:C[óo]digo\\s+establecimientos|Actividad\\s+econ[óo]mica|46\\.?\\s*Actividad)[\\s:]*\\n?[ \\t]*((?:[0-9]\\s*){2,8})', re.I)",
    "",
    "def lfs_rut(text):",
    "    spans = []",
    "    # RUT NIT: probar GS1 (codigo de barras DIAN), luego anchor plano",
    "    spans += _first_match(_RX_RUT_NIT_GS1, text, 'RUT_NIT')",
    "    if not spans: spans += _first_match(_RX_RUT_NIT_PLANO, text, 'RUT_NIT')",
    "    spans += _first_match(_RX_RUT_RAZON, text, 'RUT_RAZON_SOCIAL')",
    "    spans += _first_match(_RX_RUT_DIRECCION, text, 'RUT_DIRECCION_PPAL')",
    "    spans += _first_match(_RX_RUT_ACTECO, text, 'RUT_ACTIVIDAD_ECO')",
    "    return _dedupe(spans)",
))

cells.append(md(
    "## 3. Evaluación sobre test por tipología",
))

cells.append(code(
    "LFS = {'cc': lfs_cc, 'ced': lfs_ced, 'pol': lfs_pol, 'rut': lfs_rut}",
    "",
    "results = {}",
    "for tip, lf in LFS.items():",
    "    test_recs = load_split(tip, 'test')",
    "    preds = {r['doc_id']: lf(r['text']) for r in test_recs}",
    "    scored = score_predictions(test_recs, preds)",
    "    results[tip] = {'scores': scored, 'preds': preds, 'records': test_recs}",
    "    print(f\"  {tip.upper():4s}  macro F1={scored['macro_f1']:.3f}  micro F1={scored['micro_f1']:.3f}  support={scored['support']}\")",
))

cells.append(md(
    "## 4. Tablas detalladas por tipología",
))

cells.append(code(
    "for tip, blk in results.items():",
    "    print('='*70)",
    "    print(f'TIPOLOGIA {tip.upper()}')",
    "    print('='*70)",
    "    print(fmt_per_label_table(blk['scores'], header=f'NER-1 Regex - {tip} (test)'))",
    "    print()",
))

cells.append(md(
    "## 5. Persistir resultados",
))

cells.append(code(
    "summary = {}",
    "for tip, blk in results.items():",
    "    scores = blk['scores']",
    "    summary[tip] = {",
    "        'macro_f1': scores['macro_f1'],",
    "        'micro_f1': scores['micro_f1'],",
    "        'micro_p':  scores['micro_p'],",
    "        'micro_r':  scores['micro_r'],",
    "        'support':  scores['support'],",
    "        'per_label': scores['per_label'],",
    "    }",
    "(REPORTS / 'nb16_resumen.json').write_text(",
    "    json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')",
    "",
    "lines = ['# nb16 - NER-1 Regex baseline (test set)\\n']",
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
    "(REPORTS / 'nb16_resumen.md').write_text('\\n'.join(lines), encoding='utf-8')",
    "print('reports/nb16_resumen.{json,md} escritos')",
    "",
    "# Guardar predicciones para uso en nb19",
    "for tip, blk in results.items():",
    "    out = DATA / tip / 'predictions_ner1_test.jsonl'",
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
    "## Lectura del baseline",
    "",
    "El Regex baseline establece el piso: cualquier modelo con costo computacional debe",
    "superar estas reglas para justificarse en el reporte final (nb19). Las regex",
    "fallan especialmente cuando el OCR es ruidoso (Cédulas escaneadas, Pólizas",
    "con layouts variables entre aseguradoras) o cuando una entidad no tiene anchor",
    "léxico consistente (p.ej. `POL_NUM_POLIZA`).",
    "",
    "**Siguiente:** [17_ner_NER2_crf.ipynb](17_ner_NER2_crf.ipynb)",
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
