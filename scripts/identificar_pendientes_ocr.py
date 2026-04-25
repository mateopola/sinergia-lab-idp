"""
identificar_pendientes_ocr.py

Genera data/processed/ocr_pendientes.csv listando los documentos que necesitan
OCR en la fase de re-unificacion a EasyOCR (PLAN_OCR_COLAB.md, 2026-04-21).

Dos categorias de pendientes:
  1. nuevo            -> PDF en data/raw/ cuyo md5 no esta en corpus_ocr.csv
  2. re_ocr_pymupdf   -> documento ya procesado pero con engine=pymupdf
                          (debe re-procesarse con EasyOCR para uniformidad)

Uso:
    python scripts/identificar_pendientes_ocr.py

Requisitos:
    pip install pandas pymupdf
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: pymupdf no instalado. pip install pymupdf")
    sys.exit(1)


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CORPUS_OCR = ROOT / "data" / "processed" / "corpus_ocr.csv"
QUALITY_REPORT = ROOT / "data" / "processed" / "quality_report_completo.csv"
OUTPUT = ROOT / "data" / "processed" / "ocr_pendientes.csv"


def md5_file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def get_n_pages(pdf_path: Path) -> int | None:
    try:
        doc = fitz.open(str(pdf_path))
        n = doc.page_count
        doc.close()
        return n
    except Exception:
        return None


def main():
    print(f"[1/4] Cargando corpus_ocr.csv ({CORPUS_OCR.stat().st_size // 1024} KB)...")
    corpus = pd.read_csv(
        CORPUS_OCR,
        usecols=["md5", "doc_id", "filename", "folder", "engine", "page_num"],
        dtype={"md5": str, "doc_id": str},
    )
    print(f"      paginas en corpus: {len(corpus):,}")
    print(f"      por engine:")
    for k, v in corpus["engine"].value_counts().items():
        print(f"        {k}: {v:,}")

    print(f"\n[2/4] Identificando documentos con engine=pymupdf (re_ocr)...")
    pymupdf_md5s = set(corpus.loc[corpus["engine"] == "pymupdf", "md5"].unique())
    print(f"      docs unicos a re-procesar: {len(pymupdf_md5s):,}")

    quality = pd.read_csv(
        QUALITY_REPORT,
        usecols=["md5", "filename", "category", "n_pages", "filepath"],
        dtype={"md5": str},
    )

    re_ocr_df = quality[quality["md5"].isin(pymupdf_md5s)].copy()
    re_ocr_df["motivo"] = "re_ocr_pymupdf"
    re_ocr_df = re_ocr_df.rename(columns={"category": "folder"})
    print(f"      docs re_ocr matcheados con quality_report: {len(re_ocr_df)}")

    print(f"\n[3/4] Escaneando data/raw/ para detectar PDFs nuevos...")
    md5s_existentes = set(corpus["md5"].unique())
    md5s_existentes |= set(quality["md5"].unique())  # union por seguridad

    nuevos = []
    for folder_dir in sorted(RAW_DIR.iterdir()):
        if not folder_dir.is_dir():
            continue
        # Skip folders con prefijo _ (cuarentena, archivados, etc.)
        if folder_dir.name.startswith("_"):
            print(f"      {folder_dir.name}: omitido (prefijo _)")
            continue
        # Skip clase Otros (no aporta al clasificador, decision 2026-04-21)
        if folder_dir.name.lower().startswith("otro"):
            print(f"      {folder_dir.name}: omitido (clase Otros descartada)")
            continue
        pdfs = sorted([p for p in folder_dir.iterdir() if p.suffix.lower() == ".pdf"])
        print(f"      {folder_dir.name}: {len(pdfs)} PDFs", end="")
        n_nuevos = 0
        for pdf in pdfs:
            md5 = md5_file(pdf)
            if md5 not in md5s_existentes:
                nuevos.append(
                    {
                        "md5": md5,
                        "filename": pdf.name,
                        "folder": folder_dir.name,
                        "filepath": str(pdf),
                        "n_pages": get_n_pages(pdf),
                        "motivo": "nuevo",
                    }
                )
                n_nuevos += 1
        print(f" -> nuevos: {n_nuevos}")
    nuevos_df = pd.DataFrame(nuevos)
    print(f"      total nuevos detectados: {len(nuevos_df)}")

    print(f"\n[4/4] Combinando, deduplicando y guardando...")
    cols = ["md5", "filename", "folder", "filepath", "n_pages", "motivo"]
    pendientes = pd.concat(
        [re_ocr_df[cols], nuevos_df[cols] if len(nuevos_df) else pd.DataFrame(columns=cols)],
        ignore_index=True,
    )
    # Excluir clase Otros del re_ocr (consistencia con scan de raw)
    n_otros = int(pendientes["folder"].astype(str).str.lower().str.startswith("otro").sum())
    if n_otros:
        pendientes = pendientes[~pendientes["folder"].astype(str).str.lower().str.startswith("otro")]
        print(f"      excluidos {n_otros} docs de clase Otros")
    # Deduplicar por md5 (quality_report puede tener duplicados)
    n_antes = len(pendientes)
    pendientes = pendientes.drop_duplicates(subset="md5", keep="first")
    n_dups = n_antes - len(pendientes)
    if n_dups:
        print(f"      removidos {n_dups} duplicados por md5")
    pendientes.to_csv(OUTPUT, index=False, encoding="utf-8")

    print(f"\n=== RESUMEN ===")
    print(f"Salida: {OUTPUT}")
    print(f"Total pendientes: {len(pendientes):,} documentos")
    print(f"\nPor motivo:")
    print(pendientes["motivo"].value_counts().to_string())
    print(f"\nPor folder:")
    for folder, n in pendientes.groupby("folder").size().items():
        # safe-print para Windows cp1252 (algunos folder names tienen mojibake)
        safe = str(folder).encode("ascii", "replace").decode("ascii")
        print(f"  {safe}: {n}")
    n_pags_estim = int(pendientes["n_pages"].fillna(0).sum())
    n_pags_lim10 = int(pendientes["n_pages"].fillna(0).clip(upper=10).sum())
    print(f"\nPaginas sin limite: {n_pags_estim:,}")
    print(f"Paginas con limite 10 (decision 2026-04-21): {n_pags_lim10:,}")
    if pendientes["n_pages"].isna().any():
        n_sin_pages = int(pendientes["n_pages"].isna().sum())
        print(f"  (advertencia: {n_sin_pages} docs sin n_pages -- quality_report no los tenia, se contara en Colab)")
    tiempo_estim_h = n_pags_lim10 * 6 / 3600  # 6 s/pag en T4 GPU, con limite 10
    print(f"\nTiempo estimado en Colab T4 GPU (limite 10 pags, ~6 s/pag): {tiempo_estim_h:.1f} h")


if __name__ == "__main__":
    main()
