"""
Utilidades compartidas para Fase 3.1 NER (notebooks 16-19).

- I/O de los JSONL generados por nb15 (`data/processed/ner/<tip>/{train,dev,test}.jsonl`).
- Métrica entity-level F1 (exact match span-level, sin dependencia de seqeval).
- Conversión entre tags BIO y spans char-level.

Las predicciones que consume `score_predictions` son siempre listas de
`PredSpan(start, end, label)` con `end` exclusivo (convención Python).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed" / "ner"


@dataclass(frozen=True)
class PredSpan:
    start: int
    end: int  # exclusive
    label: str


def load_split(tipologia: str, split: str) -> list[dict]:
    """Carga un split (train/dev/test) de una tipología desde el JSONL."""
    p = DATA_DIR / tipologia / f"{split}.jsonl"
    out: list[dict] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def gold_spans(record: dict) -> list[PredSpan]:
    """Extrae los spans gold de un record del JSONL."""
    return [PredSpan(int(s["start"]), int(s["end"]), s["label"]) for s in record["spans"]]


def bio_tags_to_spans(
    tokens_offsets: list[tuple[int, int]],
    tags: list[str],
) -> list[PredSpan]:
    """Convierte una secuencia BIO sobre tokens a spans char-level.

    `tokens_offsets`: lista de (start, end) por token (end exclusivo).
    `tags`: lista de BIO tags (`O`, `B-X`, `I-X`).
    """
    spans: list[PredSpan] = []
    cur_label = None
    cur_start = -1
    cur_end = -1
    for (t_s, t_e), tag in zip(tokens_offsets, tags):
        if tag == "O":
            if cur_label is not None:
                spans.append(PredSpan(cur_start, cur_end, cur_label))
                cur_label = None
            continue
        kind, _, lab = tag.partition("-")
        if kind == "B" or (kind == "I" and cur_label != lab):
            if cur_label is not None:
                spans.append(PredSpan(cur_start, cur_end, cur_label))
            cur_label = lab
            cur_start = t_s
            cur_end = t_e
        elif kind == "I" and cur_label == lab:
            cur_end = t_e
    if cur_label is not None:
        spans.append(PredSpan(cur_start, cur_end, cur_label))
    return spans


def _key(s: PredSpan) -> tuple[int, int, str]:
    return (s.start, s.end, s.label)


def prf_per_label(
    gold: list[PredSpan],
    pred: list[PredSpan],
) -> dict[str, dict[str, float]]:
    """Precision/recall/F1 por etiqueta (exact span match).

    Devuelve `{label: {p, r, f1, tp, fp, fn, support}}`.
    """
    labels = {s.label for s in gold} | {s.label for s in pred}
    g_keys = Counter(_key(s) for s in gold)
    p_keys = Counter(_key(s) for s in pred)
    by_lab: dict[str, dict[str, float]] = {}
    for lab in sorted(labels):
        g_lab = {k: c for k, c in g_keys.items() if k[2] == lab}
        p_lab = {k: c for k, c in p_keys.items() if k[2] == lab}
        tp = sum(min(g_lab.get(k, 0), p_lab.get(k, 0)) for k in (set(g_lab) | set(p_lab)))
        fp = sum(p_lab.values()) - tp
        fn = sum(g_lab.values()) - tp
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        by_lab[lab] = {
            "p": precision,
            "r": recall,
            "f1": f1,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "support": sum(g_lab.values()),
        }
    return by_lab


def score_predictions(
    records: list[dict],
    predictions: dict[str, list[PredSpan]],
) -> dict:
    """Evalúa un conjunto de predicciones sobre un split.

    `predictions[doc_id]` = lista de PredSpan para ese documento.
    Devuelve dict con `per_label`, `macro_f1`, `micro_f1`, `support`.
    """
    gold_all: list[PredSpan] = []
    pred_all: list[PredSpan] = []
    per_doc_gold = []
    per_doc_pred = []
    for rec in records:
        rid = rec["doc_id"]
        # tag spans por doc_id para evitar colisiones de offsets entre docs
        for g in gold_spans(rec):
            gold_all.append(PredSpan(g.start, g.end, f"{rid}|{g.label}"))
        for p in predictions.get(rid, []):
            pred_all.append(PredSpan(p.start, p.end, f"{rid}|{p.label}"))
        per_doc_gold.append(gold_spans(rec))
        per_doc_pred.append(predictions.get(rid, []))

    # per-label sin la prefix de doc_id
    plain_gold = [PredSpan(s.start, s.end, s.label.split("|", 1)[1]) for s in gold_all]
    plain_pred = [PredSpan(s.start, s.end, s.label.split("|", 1)[1]) for s in pred_all]

    # Métrica entity-level: necesitamos contar TP solo cuando span coincide DENTRO del mismo doc.
    # Por eso usamos la versión con doc_id-prefix:
    by_lab = prf_per_label(gold_all, pred_all)
    # Re-mapear labels limpios
    clean: dict[str, dict[str, float]] = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "support": 0})
    for compound_lab, m in by_lab.items():
        clean_lab = compound_lab.split("|", 1)[1]
        for k in ("tp", "fp", "fn", "support"):
            clean[clean_lab][k] += m[k]
    out_per_label = {}
    for lab, m in sorted(clean.items()):
        tp, fp, fn = m["tp"], m["fp"], m["fn"]
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        out_per_label[lab] = {
            "p": p, "r": r, "f1": f1,
            "tp": tp, "fp": fp, "fn": fn,
            "support": m["support"],
        }

    macro_f1 = (
        sum(v["f1"] for v in out_per_label.values()) / len(out_per_label)
        if out_per_label else 0.0
    )
    total_tp = sum(v["tp"] for v in out_per_label.values())
    total_fp = sum(v["fp"] for v in out_per_label.values())
    total_fn = sum(v["fn"] for v in out_per_label.values())
    micro_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) else 0.0
    micro_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) else 0.0
    micro_f1 = 2 * micro_p * micro_r / (micro_p + micro_r) if (micro_p + micro_r) else 0.0

    return {
        "per_label": out_per_label,
        "macro_f1": macro_f1,
        "micro_f1": micro_f1,
        "micro_p": micro_p,
        "micro_r": micro_r,
        "support": sum(v["support"] for v in out_per_label.values()),
    }


def fmt_per_label_table(scores: dict, header: str = "") -> str:
    """Devuelve una tabla markdown con P/R/F1 por etiqueta."""
    lines = []
    if header:
        lines.append(f"**{header}**\n")
    lines.append("| Etiqueta | P | R | F1 | TP | FP | FN | support |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    for lab, m in sorted(scores["per_label"].items()):
        lines.append(
            f"| `{lab}` | {m['p']:.3f} | {m['r']:.3f} | {m['f1']:.3f} | "
            f"{m['tp']} | {m['fp']} | {m['fn']} | {m['support']} |"
        )
    lines.append(
        f"| **micro** | {scores['micro_p']:.3f} | {scores['micro_r']:.3f} | "
        f"{scores['micro_f1']:.3f} | — | — | — | {scores['support']} |"
    )
    lines.append(f"| **macro F1** | — | — | {scores['macro_f1']:.3f} | — | — | — | — |")
    return "\n".join(lines)
