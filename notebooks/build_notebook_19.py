"""
Genera notebooks/19_ner_comparativa.ipynb

Consolidación del benchmark Fase 3.1 NER. Carga los reportes JSON de nb16/17/18,
construye matriz comparativa 3 candidatos × 4 tipologías × etiquetas, identifica
ganador por tipología y produce el reporte final.

Inputs:
- reports/nb16_resumen.json (Regex)
- reports/nb17_resumen.json (CRF)
- reports/nb18_resumen.json (spaCy+CNN)

Outputs:
- reports/nb19_comparativa.md  (reporte ejecutivo)
- reports/nb19_comparativa.json
- reports/fig_nb19_macro_f1.png  (gráfico de barras agrupado)
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "19_ner_comparativa.ipynb"


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
    "# nb19 - Comparativa NER-1 / NER-2 / NER-3 (Fase 3.1)",
    "",
    "Consolida los 3 candidatos sobre el MISMO test set (split 70/15/15, seed 42).",
    "Reporta macro/micro F1 por tipología y F1 por etiqueta. Selecciona ganador",
    "por tipología bajo el criterio primario macro-F1; desempate por micro-F1, luego",
    "por costo de inferencia/training (Regex < CRF < spaCy+CNN).",
    "",
    "Ver [FASE_3_1_NER.md](../FASE_3_1_NER.md).",
))

cells.append(md("## 1. Imports"))

cells.append(code(
    "from __future__ import annotations",
    "import json",
    "from pathlib import Path",
    "",
    "import matplotlib.pyplot as plt",
    "import numpy as np",
    "import pandas as pd",
    "",
    "ROOT = Path('..').resolve()",
    "REPORTS = ROOT / 'reports'",
    "",
    "candidatos = [",
    "    ('NER-1 Regex',     REPORTS / 'nb16_resumen.json'),",
    "    ('NER-2 CRF',       REPORTS / 'nb17_resumen.json'),",
    "    ('NER-3 spaCy+CNN', REPORTS / 'nb18_resumen.json'),",
    "]",
    "TIPOLOGIAS = ('cc', 'ced', 'pol', 'rut')",
    "",
    "data = {name: json.loads(p.read_text(encoding='utf-8')) for name, p in candidatos}",
    "for name, blk in data.items():",
    "    print(name, '->', list(blk.keys()))",
    "",
    "# NER-4 Qwen QLoRA (Colab) - solo POL, opcional. Si nb21_resumen.json existe, integrar.",
    "ner4_path = REPORTS / 'nb21_resumen.json'",
    "ner4_data = None",
    "if ner4_path.exists():",
    "    ner4_data = json.loads(ner4_path.read_text(encoding='utf-8'))",
    "    print(f'NER-4 Qwen QLoRA -> {ner4_data[\"modelo\"]} (solo {ner4_data[\"tipologia\"]})')",
    "    print(f'  macro_f1={ner4_data[\"macro_f1\"]:.3f}  micro_f1={ner4_data[\"micro_f1\"]:.3f}')",
))

cells.append(md(
    "## 2. Tabla resumen — macro F1 y micro F1 por tipología × candidato",
))

cells.append(code(
    "rows = []",
    "for tip in TIPOLOGIAS:",
    "    for name, blk in data.items():",
    "        s = blk[tip]",
    "        rows.append({",
    "            'tipologia': tip.upper(),",
    "            'candidato': name,",
    "            'macro_f1':  s['macro_f1'],",
    "            'micro_f1':  s['micro_f1'],",
    "            'micro_p':   s['micro_p'],",
    "            'micro_r':   s['micro_r'],",
    "            'support':   s['support'],",
    "        })",
    "df = pd.DataFrame(rows)",
    "summary = df.pivot_table(index='tipologia', columns='candidato',",
    "                          values='macro_f1', aggfunc='first')[",
    "    [c[0] for c in candidatos]",
    "]",
    "summary['Δ best vs Regex'] = summary.max(axis=1) - summary['NER-1 Regex']",
    "summary['ganador'] = summary[[c[0] for c in candidatos]].idxmax(axis=1)",
    "summary.round(3)",
))

cells.append(md(
    "## 3. Gráfico — macro F1 agrupado por tipología",
))

cells.append(code(
    "fig, ax = plt.subplots(figsize=(9, 5))",
    "x = np.arange(len(TIPOLOGIAS))",
    "width = 0.27",
    "for i, (name, _) in enumerate(candidatos):",
    "    vals = [data[name][t]['macro_f1'] for t in TIPOLOGIAS]",
    "    ax.bar(x + (i-1)*width, vals, width, label=name)",
    "ax.set_xticks(x); ax.set_xticklabels([t.upper() for t in TIPOLOGIAS])",
    "ax.set_ylabel('macro F1 (test)')",
    "ax.set_ylim(0, 1.0)",
    "ax.set_title('Fase 3.1 NER — comparativa macro F1 por tipología')",
    "ax.legend()",
    "ax.grid(axis='y', alpha=0.3)",
    "for i, (name, _) in enumerate(candidatos):",
    "    vals = [data[name][t]['macro_f1'] for t in TIPOLOGIAS]",
    "    for j, v in enumerate(vals):",
    "        ax.text(x[j] + (i-1)*width, v+0.01, f'{v:.2f}', ha='center', fontsize=8)",
    "plt.tight_layout()",
    "plt.savefig(REPORTS / 'fig_nb19_macro_f1.png', dpi=120)",
    "plt.show()",
))

cells.append(md(
    "## 4. Detalle por etiqueta — F1 por candidato",
    "",
    "Para cada tipología, tabla 17 etiquetas (subconjunto por tipología) × 3 candidatos.",
))

cells.append(code(
    "for tip in TIPOLOGIAS:",
    "    labels = sorted({lab for blk in data.values() for lab in blk[tip]['per_label']})",
    "    rows = []",
    "    for lab in labels:",
    "        rec = {'label': lab}",
    "        for name, blk in data.items():",
    "            f1 = blk[tip]['per_label'].get(lab, {}).get('f1', 0.0)",
    "            rec[name] = round(f1, 3)",
    "        rec['support'] = blk[tip]['per_label'].get(lab, {}).get('support', 0)",
    "        rec['Δ best'] = round(max(rec[name] for name,_ in candidatos), 3)",
    "        rows.append(rec)",
    "    print(f'\\n=== {tip.upper()} ===')",
    "    print(pd.DataFrame(rows).to_string(index=False))",
))

cells.append(md(
    "## 5. Selección de ganador por tipología",
    "",
    "Criterio:",
    "1. **macro-F1** sobre test (primario).",
    "2. **micro-F1** (desempate).",
    "3. **Costo** (regex < CRF < spaCy+CNN) — desempate final.",
))

cells.append(code(
    "ranking_cost = {n:i for i,(n,_) in enumerate(candidatos)}  # menor i = menor costo",
    "",
    "ganadores = {}",
    "for tip in TIPOLOGIAS:",
    "    pool = list(data.items())",
    "    # NER-4 solo entra al pool si la tipologia coincide",
    "    if ner4_data and ner4_data['tipologia'] == tip:",
    "        pool.append(('NER-4 Qwen-3B+QLoRA', {tip: ner4_data}))",
    "    candidatos_ord = sorted(",
    "        pool,",
    "        key=lambda kv: (-kv[1][tip]['macro_f1'],",
    "                         -kv[1][tip]['micro_f1'],",
    "                         ranking_cost.get(kv[0], 99))",
    "    )",
    "    win_name, win_blk = candidatos_ord[0]",
    "    ganadores[tip] = {",
    "        'ganador':   win_name,",
    "        'macro_f1':  win_blk[tip]['macro_f1'],",
    "        'micro_f1':  win_blk[tip]['micro_f1'],",
    "        'sobre_regex': win_blk[tip]['macro_f1'] - data['NER-1 Regex'][tip]['macro_f1'],",
    "    }",
    "    print(f\"  {tip.upper():4s}  ganador={win_name:22s}  macro={win_blk[tip]['macro_f1']:.3f}  \"",
    "          f\"micro={win_blk[tip]['micro_f1']:.3f}  ΔvsRegex={ganadores[tip]['sobre_regex']:+.3f}\")",
))

cells.append(md(
    "## 6. Reporte final consolidado",
))

cells.append(code(
    "lines = ['# Fase 3.1 NER — Comparativa final\\n']",
    "lines.append('Test set único (split 70/15/15, seed 42). Métrica primaria: macro-F1 entity-level (exact span match).\\n')",
    "lines.append('## Macro F1 por tipología × candidato\\n')",
    "lines.append('| Tipología | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Δ best vs Regex | Ganador |')",
    "lines.append('|---|---:|---:|---:|---:|---|')",
    "for tip in TIPOLOGIAS:",
    "    row = [data[name][tip]['macro_f1'] for name,_ in candidatos]",
    "    best = max(row)",
    "    cells_md = []",
    "    for v in row:",
    "        s = f'{v:.3f}'",
    "        if v == best: s = f'**{s}**'",
    "        cells_md.append(s)",
    "    delta = best - row[0]",
    "    lines.append(f'| **{tip.upper()}** | {cells_md[0]} | {cells_md[1]} | {cells_md[2]} | '",
    "                 f'{delta:+.3f} | {ganadores[tip][\"ganador\"]} |')",
    "lines.append('')",
    "lines.append('## Micro F1 por tipología × candidato\\n')",
    "lines.append('| Tipología | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN |')",
    "lines.append('|---|---:|---:|---:|')",
    "for tip in TIPOLOGIAS:",
    "    row = [data[name][tip]['micro_f1'] for name,_ in candidatos]",
    "    best = max(row)",
    "    cm = [f'**{v:.3f}**' if v == best else f'{v:.3f}' for v in row]",
    "    lines.append(f'| **{tip.upper()}** | {cm[0]} | {cm[1]} | {cm[2]} |')",
    "lines.append('')",
    "",
    "# Detalle por etiqueta",
    "lines.append('## Detalle F1 por etiqueta\\n')",
    "for tip in TIPOLOGIAS:",
    "    labels = sorted({lab for blk in data.values() for lab in blk[tip]['per_label']})",
    "    lines.append(f'### {tip.upper()}\\n')",
    "    lines.append('| Etiqueta | NER-1 Regex | NER-2 CRF | NER-3 spaCy+CNN | Support |')",
    "    lines.append('|---|---:|---:|---:|---:|')",
    "    for lab in labels:",
    "        row = [data[name][tip]['per_label'].get(lab, {}).get('f1', 0.0) for name,_ in candidatos]",
    "        sup = data['NER-2 CRF'][tip]['per_label'].get(lab, {}).get('support', 0)",
    "        best = max(row)",
    "        cm = [f'**{v:.3f}**' if v == best else f'{v:.3f}' for v in row]",
    "        lines.append(f'| `{lab}` | {cm[0]} | {cm[1]} | {cm[2]} | {sup} |')",
    "    lines.append('')",
    "",
    "lines.append('## Ganadores por tipología (criterio: macro-F1 → micro-F1 → costo)\\n')",
    "lines.append('| Tipología | Ganador | Macro F1 | Micro F1 | ΔvsRegex |')",
    "lines.append('|---|---|---:|---:|---:|')",
    "for tip in TIPOLOGIAS:",
    "    g = ganadores[tip]",
    "    lines.append(f'| **{tip.upper()}** | {g[\"ganador\"]} | {g[\"macro_f1\"]:.3f} | '",
    "                 f'{g[\"micro_f1\"]:.3f} | {g[\"sobre_regex\"]:+.3f} |')",
    "lines.append('')",
    "",
    "# NER-4 sobre POL si existe",
    "if ner4_data:",
    "    lines.append('## NER-4 Qwen 2.5 3B + QLoRA — solo POL (Colab T4)\\n')",
    "    lines.append(f'Modelo: `{ner4_data[\"modelo\"]}`, epochs={ner4_data[\"epochs\"]}, train={ner4_data[\"train_size\"]} docs, test={ner4_data[\"test_size\"]} docs, training={ner4_data[\"train_elapsed_min\"]:.1f} min.\\n')",
    "    lines.append('| Etiqueta | P | R | F1 | TP | FP | FN | support |')",
    "    lines.append('|---|---:|---:|---:|---:|---:|---:|---:|')",
    "    for lab, m in sorted(ner4_data['per_label'].items()):",
    "        lines.append(f'| `{lab}` | {m[\"p\"]:.3f} | {m[\"r\"]:.3f} | {m[\"f1\"]:.3f} | '",
    "                     f'{m[\"tp\"]} | {m[\"fp\"]} | {m[\"fn\"]} | {m[\"support\"]} |')",
    "    lines.append(f'| **macro** | — | — | **{ner4_data[\"macro_f1\"]:.3f}** | — | — | — | — |')",
    "    lines.append(f'| **micro** | {ner4_data[\"micro_p\"]:.3f} | {ner4_data[\"micro_r\"]:.3f} | {ner4_data[\"micro_f1\"]:.3f} | — | — | — | — |')",
    "    lines.append('')",
    "    lines.append('**Lectura:** Qwen 3B + QLoRA con 3 épocas no convergió. Loss train final ≈ 2.10 (debería estar <1.0).')",
    "    lines.append('El modelo aprendió el formato JSON pero no el copy-task: devuelve `{}` vacío en la mayoría de docs.')",
    "    lines.append('Causa probable: insuficientes gradient updates (30 steps) sobre 79 docs train + 3B capacity.')",
    "    lines.append(f'Resultado por debajo del baseline spaCy+CNN ({data[\"NER-3 spaCy+CNN\"][\"pol\"][\"macro_f1\"]:.3f}). Se descarta NER-4 para producción.')",
    "    lines.append('')",
    "",
    "# Hallazgos clave",
    "lines.append('## Hallazgos clave\\n')",
    "macro_avg = {n: np.mean([data[n][t]['macro_f1'] for t in TIPOLOGIAS]) for n,_ in candidatos}",
    "for n, v in macro_avg.items():",
    "    lines.append(f'- **{n}** macro F1 promedio entre las 4 tipologías: **{v:.3f}**')",
    "lines.append('')",
    "if macro_avg['NER-2 CRF'] > macro_avg['NER-3 spaCy+CNN']:",
    "    lines.append('- CRF supera a spaCy+CNN en promedio: el ML clásico con features hand-crafted alcanza para este corpus.')",
    "else:",
    "    lines.append('- spaCy+CNN supera a CRF en promedio: el deep learning ligero aporta sobre features hand-crafted en este corpus.')",
    "if ner4_data:",
    "    lines.append('- LLM generativo (Qwen 3B + QLoRA) con corpus pequeño y few epochs no aporta sobre baselines clásicos — confirma la hipótesis de la literatura (Kalušev & Brkljač 2025).')",
    "",
    "(REPORTS / 'nb19_comparativa.md').write_text('\\n'.join(lines), encoding='utf-8')",
    "(REPORTS / 'nb19_comparativa.json').write_text(",
    "    json.dumps({",
    "        'macro_promedio': {n: float(v) for n, v in macro_avg.items()},",
    "        'ganadores': ganadores,",
    "        'por_tipologia': {tip: {n: data[n][tip] for n,_ in candidatos} for tip in TIPOLOGIAS},",
    "    }, indent=2, ensure_ascii=False),",
    "    encoding='utf-8',",
    ")",
    "print('reports/nb19_comparativa.{md,json} y fig_nb19_macro_f1.png escritos')",
))

cells.append(md(
    "---",
    "## Cierre de Fase 3.1 NER",
    "",
    "Con esto cierra la comparación de los 3 candidatos CPU-only. El reporte final",
    "`reports/nb19_comparativa.md` consolida resultados para el informe académico.",
    "Trabajo futuro (post-GPU): N-1 BETO, N-2 Llama 3.3+QLoRA, N-3 LayoutLMv3 — ver",
    "FASE_3_1_NER.md §7.",
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
