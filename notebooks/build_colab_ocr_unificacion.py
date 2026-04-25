"""
Genera notebooks/colab_ocr_unificacion.ipynb listo para subir a Google Colab.

Plan: ver PLAN_OCR_COLAB.md
- Re-OCR de digitales (PyMuPDF -> EasyOCR) + ingesta de Cedulas nuevas
- Limite 10 paginas por doc
- Excluida clase Otros y 2 RUPs mal clasificados
- ~747 docs / ~3,821 pags / ~6.4 h en Colab T4
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path(__file__).parent / "colab_ocr_unificacion.ipynb"


def md(*lines: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [l + "\n" for l in lines],
    }


def code(*lines: str) -> dict:
    src = []
    for l in lines:
        if l.startswith("\n"):
            src.append(l[1:] + "\n")
        else:
            src.append(l + "\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": src,
    }


cells = []

# ============================================================
cells.append(md(
    "# OCR Unificado en Colab GPU - Re-procesamiento del corpus SinergIA Lab",
    "",
    "**Decision arquitectural:** EasyOCR para todo el corpus (escaneados Y digitales) por paridad train-inference.",
    "",
    "**Scope (decision 2026-04-21):**",
    "- 747 docs a procesar (537 re-OCR digitales + 210 cedulas nuevas)",
    "- Limite 10 paginas por documento",
    "- Excluida clase Otros + 2 RUPs mal clasificados",
    "- Tiempo estimado: ~6.4 h en Tesla T4",
    "",
    "**Pre-requisitos:** Drive con la carpeta `SinergIA-Lab/` que contiene:",
    "- `raw/CEDULA/`, `raw/POLIZA/`, `raw/CAMARA DE CIO/`, `raw/rut/`",
    "- `processed/corpus_ocr.csv` (estado actual)",
    "- `processed/ocr_pendientes.csv` (lista de docs a procesar)",
    "",
    "**Documentacion:** ver [PLAN_OCR_COLAB.md](https://github.com/) en el repo del proyecto.",
))

# ============================================================
cells.append(md("## 1. Verificar GPU y entorno"))

cells.append(code(
    "import torch",
    "assert torch.cuda.is_available(), 'Sin GPU CUDA. Ir a Runtime > Change runtime type > T4 GPU'",
    "print(f'GPU: {torch.cuda.get_device_name(0)}')",
    "print(f'VRAM total: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')",
))

# ============================================================
cells.append(md("## 2. Instalar dependencias"))

cells.append(code(
    "!pip install -q easyocr pymupdf pandas tqdm",
))

# ============================================================
cells.append(md("## 3. Montar Drive"))

cells.append(code(
    "from google.colab import drive",
    "drive.mount('/content/drive')",
))

# ============================================================
cells.append(md("## 4. Configuracion (paths y constantes)"))

cells.append(code(
    "from pathlib import Path",
    "",
    "# Ruta confirmada en Drive del usuario: MyDrive/datasets/SinergiaLab/",
    "DRIVE_BASE = Path('/content/drive/MyDrive/datasets/SinergiaLab')",
    "RAW_DIR = DRIVE_BASE / 'raw'",
    "PROCESSED = DRIVE_BASE / 'processed'",
    "",
    "CORPUS_CSV = PROCESSED / 'corpus_ocr.csv'",
    "PENDIENTES_CSV = PROCESSED / 'ocr_pendientes.csv'",
    "",
    "# Constantes (decision 2026-04-21)",
    "EASYOCR_VERSION = '1.7.2'",
    "LIMITE_PAGINAS = 10",
    "DPI_RENDER = 200",
    "CHECKPOINT_EVERY = 50  # docs entre checkpoints a Drive",
    "",
    "# Verify",
    "assert PENDIENTES_CSV.exists(), f'NOT FOUND: {PENDIENTES_CSV}. Subiste ocr_pendientes.csv?'",
    "assert RAW_DIR.exists(), f'NOT FOUND: {RAW_DIR}. Subiste raw/?'",
    "print(f'Drive base    : {DRIVE_BASE}')",
    "print(f'Raw           : {RAW_DIR}')",
    "print(f'Pendientes    : {PENDIENTES_CSV}')",
    "print(f'Corpus actual : {CORPUS_CSV} ({\"existe\" if CORPUS_CSV.exists() else \"sera nuevo\"})')",
    "print(f'Limite pags   : {LIMITE_PAGINAS}')",
))

# ============================================================
cells.append(md("## 5. Backup del corpus actual + pre-cleanup"))

cells.append(code(
    "import shutil",
    "from datetime import datetime, timezone",
    "import pandas as pd",
    "",
    "# 5a. Backup",
    "if CORPUS_CSV.exists():",
    "    ts = datetime.now().strftime('%Y%m%d_%H%M%S')",
    "    backup_path = PROCESSED / f'corpus_ocr.backup_{ts}.csv'",
    "    shutil.copy(CORPUS_CSV, backup_path)",
    "    print(f'Backup: {backup_path.name}')",
))

cells.append(code(
    "# 5b. Pre-cleanup: eliminar filas pymupdf de docs en pendientes (seran re-OCR)",
    "pend = pd.read_csv(PENDIENTES_CSV, dtype={'md5': str})",
    "print(f'Pendientes cargados: {len(pend)} docs')",
    "for k, v in pend['motivo'].value_counts().items():",
    "    print(f'  {k}: {v}')",
    "",
    "if CORPUS_CSV.exists():",
    "    df = pd.read_csv(CORPUS_CSV, dtype={'md5': str})",
    "    pend_md5s = set(pend['md5'])",
    "    mask_borrar = (df['engine'] == 'pymupdf') & (df['md5'].isin(pend_md5s))",
    "    n_borrar = int(mask_borrar.sum())",
    "    if n_borrar:",
    "        df = df[~mask_borrar].copy()",
    "        df.to_csv(CORPUS_CSV, index=False, encoding='utf-8')",
    "        print(f'Pre-cleanup: eliminadas {n_borrar:,} filas pymupdf de docs a re-OCR')",
    "    print(f'Corpus tras pre-cleanup: {len(df):,} filas, {df[\"md5\"].nunique()} docs unicos')",
))

# ============================================================
cells.append(md(
    "## 6. Construir cache de paginas ya procesadas con EasyOCR",
    "",
    "Permite que el notebook sea **retomable** si la sesion Colab se cae: solo procesa lo que falta.",
))

cells.append(code(
    "cached_pages = set()",
    "if CORPUS_CSV.exists():",
    "    df_cache = pd.read_csv(CORPUS_CSV, usecols=['md5', 'page_num', 'engine'], dtype={'md5': str})",
    "    df_cache = df_cache[df_cache['engine'] == 'easyocr']",
    "    cached_pages = set(zip(df_cache['md5'], df_cache['page_num']))",
    "print(f'Cache: {len(cached_pages):,} pares (md5, page_num) ya procesados con EasyOCR')",
))

# ============================================================
cells.append(md("## 7. Inicializar EasyOCR (~30 seg, descarga modelo la primera vez)"))

cells.append(code(
    "import easyocr",
    "reader = easyocr.Reader(['es'], gpu=True)",
    "print('EasyOCR Reader listo en GPU')",
))

# ============================================================
cells.append(md("## 8. Funciones de procesamiento"))

cells.append(code(
    "import fitz  # PyMuPDF",
    "import json",
    "import time",
    "import numpy as np",
    "from PIL import Image",
    "",
    "def render_page(pdf_path, page_idx, dpi=DPI_RENDER):",
    "    \"\"\"Renderiza una pagina PDF a array numpy RGB.\"\"\"",
    "    doc = fitz.open(pdf_path)",
    "    page = doc[page_idx]",
    "    mat = fitz.Matrix(dpi / 72, dpi / 72)",
    "    pix = page.get_pixmap(matrix=mat)",
    "    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)",
    "    doc.close()",
    "    return np.array(img)",
    "",
    "def process_page(pdf_path, page_idx, md5, doc_id, filename, folder):",
    "    \"\"\"OCR una pagina con EasyOCR, devuelve dict con esquema corpus_ocr.\"\"\"",
    "    t0 = time.time()",
    "    error = None",
    "    texto = ''",
    "    bboxes = []",
    "    n_dets = 0",
    "    try:",
    "        img = render_page(pdf_path, page_idx)",
    "        results = reader.readtext(img, detail=1, paragraph=False)",
    "        # results: lista de [bbox, text, conf]",
    "        bboxes = [",
    "            {",
    "                'box': [[int(p[0]), int(p[1])] for p in r[0]],",
    "                'text': r[1],",
    "                'conf': float(r[2]),",
    "            }",
    "            for r in results",
    "        ]",
    "        texto = '\\n'.join(r[1] for r in results)",
    "        n_dets = len(bboxes)",
    "    except Exception as e:",
    "        error = f'{type(e).__name__}: {e}'",
    "    return {",
    "        'md5': md5,",
    "        'doc_id': doc_id,",
    "        'filename': filename,",
    "        'folder': folder,",
    "        'page_num': page_idx + 1,",
    "        'engine': 'easyocr',",
    "        'engine_version': EASYOCR_VERSION,",
    "        'gpu_used': True,",
    "        'texto_ocr': texto,",
    "        'bboxes_json': json.dumps(bboxes, ensure_ascii=False) if bboxes else '',",
    "        'n_detections': n_dets,",
    "        'text_chars': len(texto),",
    "        'elapsed_s': round(time.time() - t0, 3),",
    "        'timestamp': datetime.now(timezone.utc).isoformat(),",
    "        'error': error,",
    "    }",
    "",
    "def flush_buffer(buffer):",
    "    \"\"\"Append buffer al CSV en Drive y vacia.\"\"\"",
    "    if not buffer:",
    "        return 0",
    "    df_new = pd.DataFrame(buffer)",
    "    if CORPUS_CSV.exists():",
    "        df_old = pd.read_csv(CORPUS_CSV, dtype={'md5': str})",
    "        df_all = pd.concat([df_old, df_new], ignore_index=True)",
    "    else:",
    "        df_all = df_new",
    "    df_all.to_csv(CORPUS_CSV, index=False, encoding='utf-8')",
    "    return len(df_all)",
))

# ============================================================
cells.append(md(
    "## 9. Loop principal de OCR",
    "",
    "Procesa los 747 docs de pendientes con limite 10 pags. Hace checkpoint a Drive cada 50 docs.",
    "",
    "**Si la sesion se cae:** vuelve a ejecutar este notebook desde el principio. El cache MD5 retoma donde quedo.",
))

cells.append(code(
    "from tqdm.auto import tqdm",
    "",
    "results_buffer = []",
    "docs_processed = 0",
    "docs_skipped_cache = 0",
    "docs_not_found = 0",
    "pages_processed = 0",
    "errors = 0",
    "t_start = time.time()",
    "",
    "for _, row in tqdm(pend.iterrows(), total=len(pend), desc='Docs'):",
    "    md5 = row['md5']",
    "    folder = row['folder']",
    "    filename = row['filename']",
    "    ",
    "    # Localizar PDF en Drive (folder name puede tener mojibake distinto)",
    "    pdf_drive = RAW_DIR / folder / filename",
    "    if not pdf_drive.exists():",
    "        # Buscar en cualquier subcarpeta de raw/",
    "        found = False",
    "        for d in RAW_DIR.iterdir():",
    "            if not d.is_dir() or d.name.startswith('_'):",
    "                continue",
    "            candidate = d / filename",
    "            if candidate.exists():",
    "                pdf_drive = candidate",
    "                found = True",
    "                break",
    "        if not found:",
    "            docs_not_found += 1",
    "            continue",
    "    ",
    "    # Contar paginas reales",
    "    try:",
    "        pdf_doc = fitz.open(str(pdf_drive))",
    "        n_total = pdf_doc.page_count",
    "        pdf_doc.close()",
    "    except Exception as e:",
    "        # Log error a nivel doc",
    "        results_buffer.append({",
    "            'md5': md5, 'doc_id': md5, 'filename': filename, 'folder': folder,",
    "            'page_num': 0, 'engine': 'easyocr', 'engine_version': EASYOCR_VERSION,",
    "            'gpu_used': True, 'texto_ocr': '', 'bboxes_json': '',",
    "            'n_detections': 0, 'text_chars': 0, 'elapsed_s': 0,",
    "            'timestamp': datetime.now(timezone.utc).isoformat(),",
    "            'error': f'OpenError: {e}',",
    "        })",
    "        errors += 1",
    "        continue",
    "    ",
    "    n_to_process = min(n_total, LIMITE_PAGINAS)",
    "    ",
    "    # Skip doc completo si todas las paginas estan en cache",
    "    todas_en_cache = all(",
    "        (md5, p + 1) in cached_pages for p in range(n_to_process)",
    "    )",
    "    if todas_en_cache:",
    "        docs_skipped_cache += 1",
    "        continue",
    "    ",
    "    # Procesar paginas faltantes",
    "    for page_idx in range(n_to_process):",
    "        page_num = page_idx + 1",
    "        if (md5, page_num) in cached_pages:",
    "            continue",
    "        result = process_page(str(pdf_drive), page_idx, md5, md5, filename, folder)",
    "        results_buffer.append(result)",
    "        cached_pages.add((md5, page_num))",
    "        pages_processed += 1",
    "        if result['error']:",
    "            errors += 1",
    "    ",
    "    docs_processed += 1",
    "    ",
    "    # Checkpoint",
    "    if docs_processed % CHECKPOINT_EVERY == 0:",
    "        n_total_corpus = flush_buffer(results_buffer)",
    "        elapsed = (time.time() - t_start) / 60",
    "        print(f'  [checkpoint] docs={docs_processed} pags={pages_processed} corpus={n_total_corpus:,} errs={errors} elapsed={elapsed:.1f} min')",
    "        results_buffer = []",
    "",
    "# Flush final",
    "n_final = flush_buffer(results_buffer)",
    "elapsed_total = (time.time() - t_start) / 60",
    "",
    "print(f'\\n=== DONE en {elapsed_total:.1f} min ===')",
    "print(f'  Docs procesados nuevos    : {docs_processed}')",
    "print(f'  Docs skip (ya en cache)   : {docs_skipped_cache}')",
    "print(f'  Docs no encontrados       : {docs_not_found}')",
    "print(f'  Paginas procesadas        : {pages_processed:,}')",
    "print(f'  Errores                   : {errors}')",
    "print(f'  Filas finales en corpus   : {n_final:,}')",
))

# ============================================================
cells.append(md("## 10. Verificacion final"))

cells.append(code(
    "final = pd.read_csv(CORPUS_CSV, dtype={'md5': str})",
    "print(f'Total filas    : {len(final):,}')",
    "print(f'Docs unicos    : {final[\"md5\"].nunique()}')",
    "print()",
    "print('Por engine:')",
    "print(final['engine'].value_counts().to_string())",
    "print()",
    "pct_bboxes = (final['bboxes_json'].fillna('').str.len() > 5).mean()",
    "print(f'% filas con bboxes : {pct_bboxes:.1%}')",
    "print(f'Filas con error    : {final[\"error\"].notna().sum()}')",
    "print()",
    "print('Por folder:')",
    "for f, n in final.groupby('folder')['md5'].nunique().items():",
    "    print(f'  {f}: {n} docs')",
))

# ============================================================
cells.append(md(
    "## 11. Siguientes pasos",
    "",
    "1. Descargar `corpus_ocr.csv` desde Drive a tu local en `data/processed/`.",
    "2. Verificar localmente con `python -c \"import pandas as pd; df=pd.read_csv('data/processed/corpus_ocr.csv'); print(df['engine'].value_counts())\"`",
    "3. Generar imagenes pag 1 para los 548 digitales (PyMuPDF render local, ~5 min) - input C-3 LayoutLMv3.",
    "4. Commit `feat(fase2.1.5): OCR unificado EasyOCR (Colab GPU, limite 10 pags)`",
    "5. Pasar a entrenar nb10 (C-1 TF-IDF), nb11 (C-2 BETO), nb12 (C-3 LayoutLMv3).",
    "",
    "Ver [PLAN_OCR_COLAB.md](../PLAN_OCR_COLAB.md) para checklist completo.",
))

# ============================================================
nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3 (Colab)",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10",
        },
        "colab": {
            "provenance": [],
            "machine_shape": "hm",
            "gpuType": "T4",
        },
        "accelerator": "GPU",
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"Notebook generado: {OUT}")
print(f"Tamano: {OUT.stat().st_size:,} bytes")
print(f"Celdas: {len(cells)} ({sum(1 for c in cells if c['cell_type']=='code')} code, {sum(1 for c in cells if c['cell_type']=='markdown')} markdown)")
