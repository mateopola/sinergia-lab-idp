"""
Genera notebooks/20_ner_qlora_dataset.ipynb

Convierte el dataset BIO de POL (nb15) a formato prompt-completion (`messages`)
para fine-tuning supervisado de un LLM generativo (Qwen 2.5 7B / Llama 3.1 8B)
con QLoRA en Colab.

Input:
- data/processed/ner/pol/{train,dev,test}.jsonl

Output:
- data/processed/ner/pol/qlora_{train,dev,test}.jsonl
- data/_to_upload/qlora_pol/  (carpeta lista para subir a Drive con todo lo necesario)
- reports/nb20_resumen.md

Por qué empezamos con POL: es el cuello de botella del benchmark CPU
(spaCy+CNN sólo alcanzó macro F1=0.337). Si Qwen QLoRA gana ahí, justifica
escalar a las otras 3 tipologías.
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "20_ner_qlora_dataset.ipynb"


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
    "# nb20 - Dataset prompt-completion para NER QLoRA (POL)",
    "",
    "Convierte el dataset BIO de Pólizas (nb15) a formato `messages` para",
    "fine-tuning supervisado (SFT) de Qwen 2.5 7B / Llama 3.1 8B con QLoRA",
    "en Colab Free T4. Output listo para subir a Drive y consumir desde nb21.",
    "",
    "**Esquema de salida** que debe producir el modelo:",
    "```json",
    "{",
    "  \"POL_NUM_POLIZA\":        \"<string|null>\",",
    "  \"POL_ENTIDAD_ASEGURADA\": \"<string|null>\",",
    "  \"POL_TOMADOR\":           \"<string|null>\",",
    "  \"POL_PRIMA\":             \"<string|null>\"",
    "}",
    "```",
    "",
    "Si un campo no está en el documento, va `null` (entrenamos al modelo a no alucinar).",
    "Si un campo aparece varias veces, tomamos la primera ocurrencia anotada.",
))

cells.append(md("## 1. Imports y configuración"))

cells.append(code(
    "from __future__ import annotations",
    "import json, shutil, sys",
    "from pathlib import Path",
    "",
    "ROOT = Path('..').resolve()",
    "DATA_IN  = ROOT / 'data' / 'processed' / 'ner' / 'pol'",
    "DATA_OUT = ROOT / 'data' / 'processed' / 'ner' / 'pol'  # mismo dir, nombres con prefijo qlora_",
    "UPLOAD   = ROOT / 'data' / '_to_upload' / 'qlora_pol'",
    "REPORTS  = ROOT / 'reports'",
    "UPLOAD.mkdir(parents=True, exist_ok=True)",
    "",
    "SCHEMA_LABELS = ['POL_NUM_POLIZA', 'POL_ENTIDAD_ASEGURADA', 'POL_TOMADOR', 'POL_PRIMA']",
    "",
    "SYSTEM_PROMPT = (",
    "    'Eres un extractor de entidades de pólizas de seguros colombianas. '",
    "    'Recibes el texto OCR de una póliza y devuelves un JSON con los 4 campos del esquema. '",
    "    'Si un campo no aparece en el documento, su valor debe ser null. '",
    "    'Devuelve SOLO el JSON, sin texto adicional, sin comentarios, sin bloques de código.'",
    ")",
    "",
    "USER_TEMPLATE = (",
    "    'Texto del documento:\\n```\\n{texto}\\n```\\n\\n'",
    "    'Extrae los siguientes campos (usa null si no encuentras el campo):\\n'",
    "    '- POL_NUM_POLIZA: número/código de la póliza\\n'",
    "    '- POL_ENTIDAD_ASEGURADA: nombre del asegurado o beneficiario\\n'",
    "    '- POL_TOMADOR: nombre del tomador (quien contrata el seguro)\\n'",
    "    '- POL_PRIMA: valor de la prima\\n\\n'",
    "    'Responde solo con el JSON.'",
    ")",
))

cells.append(md(
    "## 2. Convertir cada record a `messages`",
    "",
    "Cada record del JSONL BIO tiene `spans = [{start, end, label, text}, ...]`.",
    "Construimos el dict `{etiqueta: primera_aparicion_text | None}`, lo serializamos",
    "como JSON con claves en orden estable, y armamos `messages` con system/user/assistant.",
))

cells.append(code(
    "def record_to_messages(rec):",
    "    by_label = {lab: None for lab in SCHEMA_LABELS}",
    "    # ordenar spans por start para preservar 'primera aparición'",
    "    for s in sorted(rec['spans'], key=lambda x: x['start']):",
    "        if s['label'] in by_label and by_label[s['label']] is None:",
    "            by_label[s['label']] = s['text']",
    "    assistant_payload = json.dumps(by_label, ensure_ascii=False)",
    "    return {",
    "        'doc_id': rec['doc_id'],",
    "        'messages': [",
    "            {'role': 'system', 'content': SYSTEM_PROMPT},",
    "            {'role': 'user', 'content': USER_TEMPLATE.format(texto=rec['text'])},",
    "            {'role': 'assistant', 'content': assistant_payload},",
    "        ],",
    "        # Guardamos también spans gold originales para evaluación posterior",
    "        'gold_spans': rec['spans'],",
    "        'text': rec['text'],",
    "    }",
))

cells.append(md(
    "## 3. Procesar train/dev/test y persistir",
))

cells.append(code(
    "splits = ('train', 'dev', 'test')",
    "stats = {}",
    "for sp in splits:",
    "    in_p  = DATA_IN  / f'{sp}.jsonl'",
    "    out_p = DATA_OUT / f'qlora_{sp}.jsonl'",
    "    records = [json.loads(l) for l in in_p.read_text(encoding='utf-8').splitlines() if l.strip()]",
    "    out_records = [record_to_messages(r) for r in records]",
    "    with out_p.open('w', encoding='utf-8') as fh:",
    "        for r in out_records:",
    "            fh.write(json.dumps(r, ensure_ascii=False) + '\\n')",
    "    shutil.copy2(out_p, UPLOAD / out_p.name)",
    "    # Stats de campos null vs llenos",
    "    null_counts = {lab: 0 for lab in SCHEMA_LABELS}",
    "    for r in out_records:",
    "        gold = json.loads(r['messages'][2]['content'])",
    "        for lab, v in gold.items():",
    "            if v is None: null_counts[lab] += 1",
    "    stats[sp] = {",
    "        'n_docs': len(out_records),",
    "        'avg_chars': round(sum(len(r['text']) for r in out_records) / len(out_records)),",
    "        'null_per_label': null_counts,",
    "    }",
    "    print(f'  {sp}: {len(out_records)} docs -> {out_p.relative_to(ROOT)} (copiado a {UPLOAD.relative_to(ROOT)})')",
    "",
    "print()",
    "print('STATS:')",
    "for sp, blk in stats.items():",
    "    print(f'  {sp}: {blk[\"n_docs\"]} docs, avg_chars={blk[\"avg_chars\"]}, null por label: {blk[\"null_per_label\"]}')",
))

cells.append(md(
    "## 4. Verificación — mostrar 1 ejemplo del train completo",
))

cells.append(code(
    "with (DATA_OUT / 'qlora_train.jsonl').open(encoding='utf-8') as fh:",
    "    sample = json.loads(fh.readline())",
    "print('doc_id:', sample['doc_id'])",
    "print('text (primeros 200 chars):', sample['text'][:200], '...')",
    "print()",
    "for m in sample['messages']:",
    "    print(f\"[{m['role'].upper()}]\")",
    "    print(m['content'][:500])",
    "    print()",
))

cells.append(md(
    "## 5. Reporte resumen",
))

cells.append(code(
    "lines = ['# nb20 - Dataset QLoRA POL (prompt-completion)\\n']",
    "lines.append(f'Schema: {SCHEMA_LABELS}\\n')",
    "lines.append('## Tamaño por split\\n')",
    "lines.append('| Split | Docs | Avg chars |')",
    "lines.append('|---|---:|---:|')",
    "for sp, blk in stats.items():",
    "    lines.append(f'| {sp} | {blk[\"n_docs\"]} | {blk[\"avg_chars\"]} |')",
    "lines.append('')",
    "lines.append('## Null por etiqueta (cuántos docs no tienen la entidad anotada)\\n')",
    "lines.append('| Etiqueta | ' + ' | '.join(splits) + ' |')",
    "lines.append('|---|' + '---:|' * len(splits))",
    "for lab in SCHEMA_LABELS:",
    "    row = f'| `{lab}` |'",
    "    for sp in splits:",
    "        row += f' {stats[sp][\"null_per_label\"][lab]} |'",
    "    lines.append(row)",
    "lines.append('')",
    "lines.append(f'Listo para subir a Drive: `data/_to_upload/qlora_pol/` ({len(list(UPLOAD.glob(\"*.jsonl\")))} archivos)\\n')",
    "(REPORTS / 'nb20_resumen.md').write_text('\\n'.join(lines), encoding='utf-8')",
    "print('reports/nb20_resumen.md escrito')",
))

cells.append(md(
    "---",
    "## Siguiente paso",
    "",
    "Subir `data/_to_upload/qlora_pol/` a Drive (carpeta `MyDrive/datasets/SinergiaLab/qlora_pol/`)",
    "y abrir [21_ner_qwen_qlora_colab.ipynb](21_ner_qwen_qlora_colab.ipynb) en Colab Free.",
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
