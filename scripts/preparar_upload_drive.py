"""
preparar_upload_drive.py

Copia a data/_to_upload/ SOLO los archivos necesarios para Colab:
- Los 747 PDFs listados en ocr_pendientes.csv (preservando estructura raw/<folder>/)
- corpus_ocr.csv (estado actual del corpus)
- ocr_pendientes.csv (lista de pendientes)

Esto reduce el upload de ~1.1 GB (raw entero) a ~650 MB (solo lo necesario).

Uso:
    python scripts/preparar_upload_drive.py

Despues:
    1. Abrir Drive web (drive.google.com)
    2. Crear carpeta MyDrive/SinergIA-Lab/
    3. Drag-and-drop el contenido de data/_to_upload/ a esa carpeta
"""
from __future__ import annotations
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
STAGING = ROOT / "data" / "_to_upload"

PENDIENTES = PROCESSED / "ocr_pendientes.csv"
CORPUS = PROCESSED / "corpus_ocr.csv"


def main():
    if not PENDIENTES.exists():
        print(f"ERROR: no existe {PENDIENTES}")
        print("Ejecuta primero: python scripts/identificar_pendientes_ocr.py")
        sys.exit(1)

    pend = pd.read_csv(PENDIENTES)
    print(f"Pendientes a copiar: {len(pend)} docs")

    # Limpiar staging si existe
    if STAGING.exists():
        print(f"Limpiando {STAGING.name}/ existente...")
        shutil.rmtree(STAGING)
    STAGING.mkdir()

    # Crear estructura raw/
    raw_staging = STAGING / "raw"
    raw_staging.mkdir()

    # Indexar PDFs por filename (busqueda eficiente)
    print("Indexando PDFs en data/raw/...")
    pdf_index = {}
    for folder in RAW.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        for pdf in folder.glob("*.pdf"):
            pdf_index.setdefault(pdf.name, []).append((folder.name, pdf))

    # Copiar PDFs preservando carpeta
    copiados = 0
    no_encontrados = []
    duplicados_de_nombre = []
    total_size = 0
    for _, row in pend.iterrows():
        fname = row["filename"]
        if fname not in pdf_index:
            no_encontrados.append(fname)
            continue
        # Si hay multiples con mismo nombre, copiar el de la carpeta esperada
        candidates = pdf_index[fname]
        if len(candidates) > 1:
            duplicados_de_nombre.append((fname, [c[0] for c in candidates]))
        # Tomar el primero que matchee folder, sino el primero
        target_folder = row["folder"]
        chosen = next((c for c in candidates if c[0] == target_folder), candidates[0])
        src = chosen[1]
        dst_folder = raw_staging / chosen[0]
        dst_folder.mkdir(exist_ok=True)
        dst = dst_folder / fname
        shutil.copy2(src, dst)
        total_size += dst.stat().st_size
        copiados += 1

    # Copiar CSVs a processed/
    proc_staging = STAGING / "processed"
    proc_staging.mkdir()
    if CORPUS.exists():
        shutil.copy2(CORPUS, proc_staging / "corpus_ocr.csv")
        total_size += (proc_staging / "corpus_ocr.csv").stat().st_size
    shutil.copy2(PENDIENTES, proc_staging / "ocr_pendientes.csv")
    total_size += (proc_staging / "ocr_pendientes.csv").stat().st_size

    # Resumen
    print()
    print("=== RESUMEN ===")
    print(f"PDFs copiados                : {copiados}")
    print(f"PDFs no encontrados          : {len(no_encontrados)}")
    print(f"Duplicados de nombre         : {len(duplicados_de_nombre)}")
    print(f"Tamano total a subir         : {total_size/1e6:.0f} MB ({total_size/1e9:.2f} GB)")
    print()
    print(f"Listo para subir desde       : {STAGING}")
    print()
    print("Estructura:")
    for folder in sorted(raw_staging.iterdir()):
        n = len(list(folder.glob("*.pdf")))
        size = sum(p.stat().st_size for p in folder.glob("*.pdf")) / 1e6
        # Safe print
        safe = folder.name.encode("ascii", "replace").decode("ascii")
        print(f"  raw/{safe}: {n} PDFs ({size:.0f} MB)")

    if no_encontrados:
        print()
        print(f"PDFs no encontrados ({len(no_encontrados)} primeros 5):")
        for fn in no_encontrados[:5]:
            print(f"  - {fn.encode('ascii','replace').decode('ascii')}")


if __name__ == "__main__":
    main()
