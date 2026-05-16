"""
Genera notebooks/21_ner_qwen_qlora_colab.ipynb

Notebook para Colab Free GPU (T4). Fine-tunea Qwen 2.5 7B Instruct con QLoRA
(Unsloth) sobre el dataset de Pólizas generado por nb20. Evalúa sobre test
con la MISMA métrica entity-level que nb16/17/18.

NO ejecutable en CPU local. Subir a Colab manualmente.

Prereqs en Colab:
1. Drive montado (carpeta MyDrive/datasets/SinergiaLab/qlora_pol/ con qlora_{train,dev,test}.jsonl)
2. Runtime GPU T4

Outputs (en Drive):
- MyDrive/datasets/SinergiaLab/qlora_pol/model/  (LoRA adapter, ~50-200 MB)
- MyDrive/datasets/SinergiaLab/qlora_pol/predictions_test.jsonl
- MyDrive/datasets/SinergiaLab/qlora_pol/nb21_resumen.json
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "21_ner_qwen_qlora_colab.ipynb"


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
    "# nb21 - NER-4 Qwen 2.5 7B + QLoRA (Colab)",
    "",
    "**Candidato extendido NER-4** (post-GPU) de Fase 3.1. Fine-tuning generativo",
    "del LLM **Qwen 2.5 7B Instruct** con QLoRA (Unsloth) sobre Pólizas — la",
    "tipología más débil en el benchmark CPU (spaCy+CNN solo alcanzó 0.337).",
    "",
    "Ver [FASE_3_1_NER.md §7](../FASE_3_1_NER.md) y [PROPUESTA_MODELOS.md §FASE 3 N-2](../PROPUESTA_MODELOS.md).",
    "",
    "**¿Por qué Qwen y no Llama 3.1?**",
    "Qwen 2.5 (Alibaba, dic 2024) es libre, sin gating de HuggingFace, con mejor soporte",
    "de español documentado en su technical report (arXiv:2412.15115). Mismo pipeline",
    "Unsloth+QLoRA, intercambiable con Llama 3.1 si se quiere comparar.",
    "",
    "**Hardware:** Colab Free GPU (T4, 16 GB VRAM). Cuenta `mateopolanco2@gmail.com`",
    "con el setup de Drive ya documentado.",
))

cells.append(md(
    "## 0. Prerequisitos en Colab",
    "",
    "Antes de correr este notebook:",
    "",
    "1. **Subir a Drive** la carpeta local `data/_to_upload/qlora_pol/` (3 archivos JSONL) a:",
    "   `MyDrive/datasets/SinergiaLab/qlora_pol/`",
    "2. **Cambiar runtime**: Runtime > Change runtime type > T4 GPU",
    "3. **Verificar GPU**: la celda 2 debe imprimir `Tesla T4`",
    "",
    "Si Colab corta la sesión por cuota antes de terminar, los pesos QLoRA se",
    "guardan cada 25 steps en Drive — al retomar, se levantan desde el último",
    "checkpoint.",
))

cells.append(md("## 1. Instalar Unsloth (incluye transformers, peft, trl, bitsandbytes)"))

cells.append(code(
    "# Instalación recomendada por Unsloth para Colab T4 (2026)",
    "%%capture",
    "!pip install --upgrade --no-cache-dir 'unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git'",
    "!pip install --no-deps 'xformers<0.0.27' 'trl<0.9.0' peft accelerate bitsandbytes",
))

cells.append(code(
    "# Permitir al allocator expandir segmentos => reduce fragmentación (recomendado en T4 con LoRA)",
    "import os",
    "os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'",
    "",
    "import torch",
    "print('CUDA disponible :', torch.cuda.is_available())",
    "print('GPU             :', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')",
    "print('VRAM total      :', f'{torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB' if torch.cuda.is_available() else '-')",
))

cells.append(md("## 2. Montar Drive y cargar dataset"))

cells.append(code(
    "from google.colab import drive",
    "drive.mount('/content/drive')",
    "",
    "import json",
    "from pathlib import Path",
    "",
    "DRIVE  = Path('/content/drive/MyDrive/datasets/SinergiaLab/qlora_pol')",
    "MODELS = DRIVE / 'model'",
    "MODELS.mkdir(parents=True, exist_ok=True)",
    "",
    "def load_jsonl(p):",
    "    return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]",
    "",
    "train_recs = load_jsonl(DRIVE / 'qlora_train.jsonl')",
    "dev_recs   = load_jsonl(DRIVE / 'qlora_dev.jsonl')",
    "test_recs  = load_jsonl(DRIVE / 'qlora_test.jsonl')",
    "print(f'train: {len(train_recs)}   dev: {len(dev_recs)}   test: {len(test_recs)}')",
))

cells.append(md(
    "## 3. Cargar Qwen 2.5 7B Instruct en 4-bit con Unsloth",
    "",
    "Unsloth precarga el modelo con bitsandbytes 4-bit y prepara el LoRA wrap.",
    "El download del modelo pre-cuantizado tarda ~3-5 min (4.5 GB).",
))

cells.append(code(
    "from unsloth import FastLanguageModel",
    "",
    "MAX_SEQ_LEN = 1024   # 2048 hace OOM en T4; 1024 cubre 95%+ de POL (avg 700-900 tokens)",
    "# Empíricamente Qwen 7B + LoRA + checkpointing satura T4 16GB (~14.5/15 GB antes del 1er step).",
    "# 3B en 4-bit ocupa ~2 GB pesos vs ~5 GB del 7B; deja ~12 GB libres para activations.",
    "MODEL_NAME  = 'unsloth/Qwen2.5-3B-Instruct-bnb-4bit'",
    "",
    "model, tokenizer = FastLanguageModel.from_pretrained(",
    "    model_name      = MODEL_NAME,",
    "    max_seq_length  = MAX_SEQ_LEN,",
    "    dtype           = None,         # auto: bfloat16 en T4 si soporta, float16 si no",
    "    load_in_4bit    = True,",
    ")",
))

cells.append(md(
    "## 4. Aplicar adaptadores LoRA",
    "",
    "Config estándar para tareas de extracción: r=16, alpha=16, módulos atención + MLP.",
    "Solo se entrenan ~50M parámetros vs 7B base; resto congelado.",
))

cells.append(code(
    "model = FastLanguageModel.get_peft_model(",
    "    model,",
    "    r              = 16,",
    "    target_modules = ['q_proj', 'k_proj', 'v_proj', 'o_proj',",
    "                       'gate_proj', 'up_proj', 'down_proj'],",
    "    lora_alpha     = 16,",
    "    lora_dropout   = 0.05,",
    "    bias           = 'none',",
    "    use_gradient_checkpointing = 'unsloth',  # ahorra VRAM",
    "    random_state   = 42,",
    "    use_rslora     = False,",
    "    loftq_config   = None,",
    ")",
))

cells.append(md(
    "## 5. Aplicar chat template de Qwen al dataset",
    "",
    "Qwen 2.5 usa el formato `<|im_start|>role\\ncontent<|im_end|>`. Unsloth incluye",
    "helper `get_chat_template` que aplica este template a la columna `messages`.",
))

cells.append(code(
    "from datasets import Dataset",
    "from unsloth.chat_templates import get_chat_template",
    "",
    "tokenizer = get_chat_template(tokenizer, chat_template='qwen-2.5')",
    "",
    "def formatting_func(batch):",
    "    return {'text': [",
    "        tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=False)",
    "        for msgs in batch['messages']",
    "    ]}",
    "",
    "ds_train = Dataset.from_list([{'messages': r['messages']} for r in train_recs]).map(",
    "    formatting_func, batched=True)",
    "ds_dev   = Dataset.from_list([{'messages': r['messages']} for r in dev_recs]).map(",
    "    formatting_func, batched=True)",
    "",
    "# Sanity: mostrar el primer ejemplo formateado",
    "print(ds_train[0]['text'][:1200])",
))

cells.append(md(
    "## 6. Configurar SFTTrainer",
    "",
    "Hiperparámetros conservadores para 79 docs train (corpus pequeño): 3 épocas",
    "efectivas con batch 2 + grad_accum 4 = batch efectivo 8.",
))

cells.append(code(
    "from trl import SFTTrainer",
    "from transformers import TrainingArguments",
    "",
    "training_args = TrainingArguments(",
    "    output_dir                  = str(MODELS),",
    "    num_train_epochs            = 3,",
    "    per_device_train_batch_size = 1,   # bajado de 2 para evitar OOM en T4",
    "    gradient_accumulation_steps = 8,   # subido de 4 para mantener batch efectivo = 8",
    "    warmup_steps                = 5,",
    "    learning_rate               = 2e-4,",
    "    lr_scheduler_type           = 'cosine',",
    "    optim                       = 'adamw_8bit',",
    "    weight_decay                = 0.01,",
    "    logging_steps               = 5,",
    "    save_steps                  = 25,",
    "    save_total_limit            = 2,",
    "    fp16                        = not torch.cuda.is_bf16_supported(),",
    "    bf16                        = torch.cuda.is_bf16_supported(),",
    "    seed                        = 42,",
    "    report_to                   = 'none',",
    ")",
    "",
    "trainer = SFTTrainer(",
    "    model           = model,",
    "    tokenizer       = tokenizer,",
    "    train_dataset   = ds_train,",
    "    dataset_text_field = 'text',",
    "    max_seq_length  = MAX_SEQ_LEN,",
    "    packing         = False,",
    "    args            = training_args,",
    ")",
))

cells.append(md(
    "## 7. Entrenar",
    "",
    "Tiempo estimado en T4: ~30-50 min para 3 épocas. Si la sesión se corta,",
    "los checkpoints están en Drive — relanzar con `resume_from_checkpoint`.",
))

cells.append(code(
    "import time",
    "t0 = time.time()",
    "stats = trainer.train()",
    "elapsed = time.time() - t0",
    "print(f'Entrenamiento completado en {elapsed/60:.1f} min')",
    "print(stats)",
    "",
    "# Guardar adapter final en Drive",
    "model.save_pretrained(str(MODELS / 'final'))",
    "tokenizer.save_pretrained(str(MODELS / 'final'))",
    "print('Adapter guardado en', MODELS / 'final')",
))

cells.append(md(
    "## 8. Inferencia sobre test",
    "",
    "Generamos con greedy decoding (`do_sample=False`) — para NER queremos consistencia,",
    "no creatividad. Parseamos el JSON de la respuesta y normalizamos.",
))

cells.append(code(
    "import re",
    "from unsloth import FastLanguageModel",
    "FastLanguageModel.for_inference(model)  # 2x speedup",
    "",
    "def parse_json_response(text):",
    "    \"\"\"Extrae el primer JSON válido de la respuesta del modelo.\"\"\"",
    "    # Quitar markdown fence si aparece",
    "    text = re.sub(r'^```(?:json)?\\s*', '', text.strip())",
    "    text = re.sub(r'\\s*```\\s*$', '', text)",
    "    # Buscar el primer bloque {...}",
    "    m = re.search(r'\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}', text)",
    "    if not m: return {}",
    "    try:",
    "        return json.loads(m.group(0))",
    "    except Exception:",
    "        return {}",
    "",
    "predictions = []",
    "for i, rec in enumerate(test_recs):",
    "    # Sólo system + user en el prompt; el modelo completa con assistant",
    "    prompt_msgs = rec['messages'][:2]",
    "    prompt = tokenizer.apply_chat_template(prompt_msgs, tokenize=False, add_generation_prompt=True)",
    "    inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=MAX_SEQ_LEN-256).to('cuda')",
    "    out = model.generate(**inputs, max_new_tokens=256, do_sample=False, temperature=0.0,",
    "                          pad_token_id=tokenizer.eos_token_id)",
    "    gen = tokenizer.decode(out[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)",
    "    pred = parse_json_response(gen)",
    "    predictions.append({'doc_id': rec['doc_id'], 'raw': gen, 'pred': pred,",
    "                          'gold_spans': rec['gold_spans'], 'text': rec['text']})",
    "    if i < 3:",
    "        print(f'--- doc {rec[\"doc_id\"][:12]} ---')",
    "        print('gold (assistant):', rec['messages'][2]['content'])",
    "        print('pred:           ', pred)",
    "        print()",
))

cells.append(md(
    "## 9. Métrica entity-level (mismo F1 que nb16/17/18)",
    "",
    "Para comparar contra los otros candidatos: cada valor predicho se mapea a un",
    "span char en el texto vía substring search (`text.find(value)`). Si no se encuentra,",
    "la predicción no cuenta (modelo alucinó). Si se encuentra, comparamos contra gold spans.",
))

cells.append(code(
    "from collections import Counter, defaultdict",
    "",
    "def predicted_spans_from_json(pred_json, text):",
    "    spans = []",
    "    for lab, value in (pred_json or {}).items():",
    "        if not value or value in ('null', 'None'): continue",
    "        idx = text.find(value)",
    "        if idx < 0: continue  # alucinación: no aparece en el texto",
    "        spans.append((idx, idx + len(value), lab))",
    "    return spans",
    "",
    "# Evaluación entity-level (exact span match, dentro del mismo doc)",
    "per_label_counts = defaultdict(lambda: {'tp':0, 'fp':0, 'fn':0, 'support':0})",
    "for p in predictions:",
    "    gold = {(s['start'], s['end'], s['label']) for s in p['gold_spans']}",
    "    pred = set(predicted_spans_from_json(p['pred'], p['text']))",
    "    all_labels = {x[2] for x in gold} | {x[2] for x in pred}",
    "    for lab in all_labels:",
    "        g_lab = {x for x in gold if x[2] == lab}",
    "        p_lab = {x for x in pred if x[2] == lab}",
    "        per_label_counts[lab]['tp'] += len(g_lab & p_lab)",
    "        per_label_counts[lab]['fp'] += len(p_lab - g_lab)",
    "        per_label_counts[lab]['fn'] += len(g_lab - p_lab)",
    "        per_label_counts[lab]['support'] += len(g_lab)",
    "",
    "results = {}",
    "for lab, c in per_label_counts.items():",
    "    p = c['tp']/(c['tp']+c['fp']) if (c['tp']+c['fp']) else 0.0",
    "    r = c['tp']/(c['tp']+c['fn']) if (c['tp']+c['fn']) else 0.0",
    "    f1 = 2*p*r/(p+r) if (p+r) else 0.0",
    "    results[lab] = {'p':p, 'r':r, 'f1':f1, **c}",
    "",
    "macro_f1 = sum(v['f1'] for v in results.values()) / max(1, len(results))",
    "ttp = sum(c['tp'] for c in per_label_counts.values())",
    "tfp = sum(c['fp'] for c in per_label_counts.values())",
    "tfn = sum(c['fn'] for c in per_label_counts.values())",
    "micro_p = ttp/(ttp+tfp) if (ttp+tfp) else 0.0",
    "micro_r = ttp/(ttp+tfn) if (ttp+tfn) else 0.0",
    "micro_f1 = 2*micro_p*micro_r/(micro_p+micro_r) if (micro_p+micro_r) else 0.0",
    "",
    "print(f'\\n=== POL — NER-4 Qwen 2.5 7B + QLoRA ===')",
    "print(f'macro F1: {macro_f1:.3f}   micro F1: {micro_f1:.3f}   support: {sum(c[\"support\"] for c in per_label_counts.values())}')",
    "print()",
    "print(f'{\"Etiqueta\":<25} {\"P\":>6} {\"R\":>6} {\"F1\":>6} {\"TP\":>4} {\"FP\":>4} {\"FN\":>4} sup')",
    "for lab in sorted(results):",
    "    m = results[lab]",
    "    print(f'{lab:<25} {m[\"p\"]:>6.3f} {m[\"r\"]:>6.3f} {m[\"f1\"]:>6.3f} {m[\"tp\"]:>4} {m[\"fp\"]:>4} {m[\"fn\"]:>4} {m[\"support\"]:>4}')",
))

cells.append(md(
    "## 10. Persistir resultados en Drive",
))

cells.append(code(
    "summary = {",
    "    'modelo':     MODEL_NAME,",
    "    'tipologia':  'pol',",
    "    'epochs':     training_args.num_train_epochs,",
    "    'train_size': len(train_recs),",
    "    'test_size':  len(test_recs),",
    "    'macro_f1':   macro_f1,",
    "    'micro_f1':   micro_f1,",
    "    'micro_p':    micro_p,",
    "    'micro_r':    micro_r,",
    "    'per_label':  results,",
    "    'train_elapsed_min': elapsed / 60,",
    "}",
    "(DRIVE / 'nb21_resumen.json').write_text(",
    "    json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')",
    "",
    "# Predicciones por doc (para integrar en nb19 comparativa)",
    "with (DRIVE / 'predictions_test.jsonl').open('w', encoding='utf-8') as fh:",
    "    for p in predictions:",
    "        out_preds = [",
    "            {'start': s[0], 'end': s[1], 'label': s[2], 'text': p['text'][s[0]:s[1]]}",
    "            for s in predicted_spans_from_json(p['pred'], p['text'])",
    "        ]",
    "        fh.write(json.dumps({'doc_id': p['doc_id'], 'preds': out_preds,",
    "                              'raw_json': p['pred']}, ensure_ascii=False) + '\\n')",
    "",
    "print('Outputs en Drive:')",
    "print(f'  - {DRIVE / \"nb21_resumen.json\"}')",
    "print(f'  - {DRIVE / \"predictions_test.jsonl\"}')",
    "print(f'  - {MODELS / \"final\"}/ (adapter LoRA, ~50-200 MB)')",
))

cells.append(md(
    "---",
    "## Comparativa rápida vs CPU benchmark",
    "",
    "Resultados POL del benchmark CPU (test set, macro F1):",
    "- NER-1 Regex      → 0.113",
    "- NER-2 CRF        → 0.267",
    "- NER-3 spaCy+CNN  → 0.337  ← actual mejor",
    "",
    "Si `macro_f1` de este notebook supera 0.337, justifica entrenar las otras 3",
    "tipologías (CC, CED, RUT) con el mismo pipeline y actualizar nb19 comparativa.",
))


nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
        "accelerator": "GPU",
        "colab": {"gpuType": "T4", "provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"escrito {OUT}")
