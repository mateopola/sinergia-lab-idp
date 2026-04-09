"""
SinergIA Lab — Enriquecimiento del quality_report_completo.csv
==============================================================
Este script NO re-procesa los documentos.
Lee el CSV existente (1,014 filas x 53 columnas) y agrega las columnas
derivadas que faltaban en el pipeline original:

  es_escaneado         : True si lexicon_count <= 5
  tokens_heuristica    : lexicon_count / 0.75
  tokens_bpe_ajustado  : tokens_heuristica * 1.25 (correccion BPE Llama 3)
  supera_limite_bpe    : tokens_bpe_ajustado > 1,800

Tambien genera dos figuras nuevas que complementan el EDA existente:
  fig03_tokens_bpe.png      : distribucion de tokens con limite BPE
  fig04_densidad_escaneados : escaneados vs digitales por tipologia

Ejecutar desde la raiz del proyecto:
    python notebooks/enriquecer_reporte.py
"""
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import json

# ── Rutas ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PROC    = PROJECT_ROOT / 'data' / 'processed'
CSV_IN       = DATA_PROC / 'quality_report_completo.csv'
CSV_OUT      = DATA_PROC / 'quality_report_completo.csv'  # sobreescribir con columnas nuevas

BPE_CORRECTION    = 1.25
HEURISTIC_RATIO   = 0.75
TOKENS_HARD_LIMIT = 1800
SCAN_THRESHOLD    = 5      # lexicon_count <= umbral -> documento escaneado

CAT_COLORS = ['#4C72B0', '#DD8452', '#55A868', '#C44E52', '#8c8c8c']

def build_palette(categories):
    """Construye palette dict desde los valores reales del DataFrame."""
    return {cat: CAT_COLORS[i % len(CAT_COLORS)] for i, cat in enumerate(sorted(categories))}

sns.set_theme(style='whitegrid', palette='muted', font_scale=1.1)
plt.rcParams.update({'figure.dpi': 120})


def enriquecer(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las 4 columnas derivadas de correccion BPE al DataFrame existente."""
    df = df.copy()

    df['es_escaneado']         = df['lexicon_count'] <= SCAN_THRESHOLD
    df['tokens_heuristica']    = (df['lexicon_count'] / HEURISTIC_RATIO).astype(int)
    df['tokens_bpe_ajustado']  = (df['tokens_heuristica'] * BPE_CORRECTION).astype(int)
    df['supera_limite_bpe']    = df['tokens_bpe_ajustado'] > TOKENS_HARD_LIMIT

    return df


def fig_tokens_bpe(df: pd.DataFrame):
    """
    Figura: distribucion de tokens con correccion BPE por tipologia.
    Reemplaza la estimacion cruda con la version corregida para Llama 3.
    Muestra cuantos documentos superan el limite duro de chunking (1,800 tok).
    """
    df_t = df.dropna(subset=['tokens_bpe_ajustado'])
    cat_order = (df_t.groupby('category')['tokens_bpe_ajustado']
                 .median().sort_values().index.tolist())

    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    fig.suptitle(
        f'Estimacion de Tokens con Correccion BPE Llama 3 (x{BPE_CORRECTION})\n'
        f'Limite duro de chunking: {TOKENS_HARD_LIMIT} tokens (margen 12% sobre 2,048)',
        fontsize=12, fontweight='bold'
    )

    # Panel izquierdo: violin con limites
    palette = build_palette(df_t['category'].unique())
    sns.violinplot(data=df_t, x='tokens_bpe_ajustado', y='category', hue='category',
                   order=cat_order, palette=palette, inner='box', legend=False, ax=axes[0])
    axes[0].axvline(TOKENS_HARD_LIMIT, color='red',    linestyle='--', lw=1.8,
                    label=f'Limite chunking ({TOKENS_HARD_LIMIT} tok)')
    axes[0].axvline(2048,              color='orange', linestyle=':',  lw=1.2,
                    label='Contexto maximo Llama 3 (2,048)')
    axes[0].axvline(512,               color='gray',   linestyle=':',  lw=1.0,
                    label='512 tok (sin chunking)')
    axes[0].set_xlabel('Tokens estimados (BPE x1.25)')
    axes[0].set_title('Distribucion por tipologia')
    axes[0].legend(fontsize=8)

    # Panel derecho: barras con docs que superan el limite
    supera = df_t.groupby('category')['supera_limite_bpe'].sum().reindex(cat_order)
    totales = df_t.groupby('category').size().reindex(cat_order)
    pct     = (supera / totales * 100).fillna(0)
    colors  = [palette.get(c, '#888') for c in cat_order]

    bars = axes[1].barh(cat_order, supera.values, color=colors, edgecolor='white')
    for bar, v, p, t in zip(bars, supera.values, pct.values, totales.values):
        axes[1].text(v + 0.3, bar.get_y() + bar.get_height() / 2,
                     f'{int(v)}/{int(t)} docs  ({p:.1f}%)',
                     va='center', fontsize=9)
    axes[1].set_xlabel('Documentos que superan el limite BPE')
    axes[1].set_title(f'Docs con tokens_bpe > {TOKENS_HARD_LIMIT} (requieren chunking)')
    axes[1].set_xlim(0, supera.max() * 1.6 if supera.max() > 0 else 10)

    plt.tight_layout()
    out = DATA_PROC / 'fig03_tokens_bpe.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


def fig_escaneados_vs_digitales(df: pd.DataFrame):
    """
    Figura: proporcion de documentos escaneados vs digitales por tipologia.
    Este grafico documenta el hallazgo critico del EDA:
    el 93% de las Cedulas son imagenes — lo que invalida la estrategia de regex LFs.
    """
    resumen = (df.groupby('category')['es_escaneado']
               .agg(escaneados='sum', total='count')
               .reset_index())
    resumen['digitales']       = resumen['total'] - resumen['escaneados']
    resumen['pct_escaneados']  = resumen['escaneados']  / resumen['total'] * 100
    resumen['pct_digitales']   = resumen['digitales'] / resumen['total'] * 100
    resumen = resumen.sort_values('pct_escaneados', ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    fig.suptitle(
        'Documentos Escaneados vs. Digitales por Tipologia\n'
        'Hallazgo critico: 93% Cedulas son imagenes — NO elegibles para regex LFs',
        fontsize=12, fontweight='bold'
    )

    # Panel izquierdo: barras apiladas
    cats   = resumen['category'].tolist()
    esc    = resumen['escaneados'].tolist()
    dig    = resumen['digitales'].tolist()
    x      = np.arange(len(cats))
    width  = 0.5

    bars_e = axes[0].bar(x, esc, width, label='Escaneados (requieren OCR)',
                         color='#e74c3c', alpha=0.85, edgecolor='white')
    bars_d = axes[0].bar(x, dig, width, bottom=esc, label='Digitales (PyMuPDF directo)',
                         color='#2ecc71', alpha=0.85, edgecolor='white')

    # Anotaciones de porcentaje
    for i, (e, d, t) in enumerate(zip(esc, dig, resumen['total'])):
        if e > 0:
            axes[0].text(i, e / 2, f'{e/t*100:.0f}%\nescaneados',
                         ha='center', va='center', fontsize=8, color='white', fontweight='bold')
        if d > 0:
            axes[0].text(i, e + d / 2, f'{d/t*100:.0f}%\ndigitales',
                         ha='center', va='center', fontsize=8, color='white', fontweight='bold')

    axes[0].set_xticks(x)
    axes[0].set_xticklabels(cats, rotation=15, ha='right')
    axes[0].set_ylabel('Documentos')
    axes[0].set_title('Distribucion absoluta')
    axes[0].legend(fontsize=9)

    # Panel derecho: tabla de impacto en estrategia de etiquetado
    impact = {
        'Cedula':             'OCR muestral (60 docs)\n+ anotacion manual Label Studio',
        'RUT':                'Regex LFs automaticas\n(texto digital disponible)',
        'Poliza':             'Anotacion manual\n(80 docs train)',
        'Camara de Comercio': 'Anotacion manual\n(80 docs train)',
    }
    tabla_data = []
    for _, row in resumen.iterrows():
        cat = row['category']
        tabla_data.append([
            cat,
            f"{int(row['escaneados'])} ({row['pct_escaneados']:.0f}%)",
            f"{int(row['digitales'])} ({row['pct_digitales']:.0f}%)",
            impact.get(cat, '—'),
        ])

    axes[1].axis('off')
    tabla = axes[1].table(
        cellText=tabla_data,
        colLabels=['Tipologia', 'Escaneados', 'Digitales', 'Estrategia de Etiquetado'],
        cellLoc='center', loc='center',
    )
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(8.5)
    tabla.scale(1, 2.2)
    for (row, col), cell in tabla.get_celld().items():
        if row == 0:
            cell.set_facecolor('#2c3e50')
            cell.set_text_props(color='white', fontweight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#ecf0f1')
    axes[1].set_title('Impacto en estrategia de etiquetado (Plan v1.3)', fontweight='bold')

    plt.tight_layout()
    out = DATA_PROC / 'fig04_escaneados_vs_digitales.png'
    plt.savefig(out, bbox_inches='tight', dpi=150)
    plt.close()
    print(f'  Guardada: {out}')


def actualizar_decisiones(df: pd.DataFrame):
    """Actualiza fase1_decisiones.json con los datos de correccion BPE."""
    dec_path = DATA_PROC / 'fase1_decisiones.json'
    with open(dec_path, 'r', encoding='utf-8') as f:
        decisions = json.load(f)

    chunking_bpe = {}
    for cat in df['category'].dropna().unique():
        sub = df[df['category'] == cat]
        med_bpe  = sub['tokens_bpe_ajustado'].median()
        n_sup    = int(sub['supera_limite_bpe'].sum())
        n_esc    = int(sub['es_escaneado'].sum())
        total    = len(sub)
        if med_bpe > 2048:
            strat = 'layout_aware_opencv'
        elif n_sup / total > 0.10:
            strat = 'sliding_window_30pct'
        else:
            strat = 'sin_chunking'
        chunking_bpe[cat] = {
            'mediana_tokens_bpe':  int(med_bpe),
            'docs_superan_limite': n_sup,
            'pct_superan':         round(n_sup / total * 100, 1),
            'docs_escaneados':     n_esc,
            'pct_escaneados':      round(n_esc / total * 100, 1),
            'estrategia':          strat,
        }

    decisions['bpe_correction']    = BPE_CORRECTION
    decisions['tokens_hard_limit']  = TOKENS_HARD_LIMIT
    decisions['chunking_bpe']       = chunking_bpe
    decisions['total_escaneados']   = int(df['es_escaneado'].sum())
    decisions['pct_escaneados']     = round(df['es_escaneado'].mean() * 100, 1)

    with open(dec_path, 'w', encoding='utf-8') as f:
        json.dump(decisions, f, ensure_ascii=False, indent=2)
    print(f'  fase1_decisiones.json actualizado: {dec_path}')


def main():
    print()
    print('=' * 60)
    print('  Enriquecimiento del EDA — SinergIA Lab')
    print('  Agrega columnas BPE + figuras faltantes al CSV existente')
    print('=' * 60)
    print()

    print(f'[1/4] Leyendo {CSV_IN.name}...')
    df = pd.read_csv(CSV_IN, encoding='latin-1')
    print(f'  Shape original: {df.shape}')

    print('[2/4] Calculando columnas derivadas...')
    df = enriquecer(df)
    nuevas = ['es_escaneado', 'tokens_heuristica', 'tokens_bpe_ajustado', 'supera_limite_bpe']
    print(f'  Columnas agregadas: {nuevas}')
    print(f'  Shape final: {df.shape}')
    print()

    # Resumen de hallazgos
    print('  RESUMEN DE HALLAZGOS:')
    for cat in ['C\u00e9dula', 'RUT', 'P\u00f3liza', 'C\u00e1mara de Comercio']:
        sub = df[df['category'] == cat]
        n_esc  = sub['es_escaneado'].sum()
        n_sup  = sub['supera_limite_bpe'].sum()
        med_bpe = sub['tokens_bpe_ajustado'].median()
        print(f'    {cat:<22} escaneados={n_esc}/{len(sub)} '
              f'| mediana_bpe={med_bpe:.0f} | superan_limite={n_sup}')
    print()

    print('[3/4] Generando figuras...')
    fig_tokens_bpe(df)
    fig_escaneados_vs_digitales(df)

    print('[4/4] Guardando artefactos...')
    df.to_csv(CSV_OUT, index=False, encoding='utf-8-sig')
    print(f'  CSV actualizado: {CSV_OUT} -> {df.shape}')
    actualizar_decisiones(df)

    print()
    print('=' * 60)
    print('  COMPLETADO')
    print('  CSV existente conservado + 4 columnas nuevas + 2 figuras')
    print('  Nada del EDA anterior fue eliminado.')
    print('=' * 60)


if __name__ == '__main__':
    main()
