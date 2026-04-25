"""
generar_imagenes_pag1_faltantes.py

Renderiza la pagina 1 de cada PDF a JPG en data/processed/images/
para todos los docs que aun no tengan imagen pag 1 (principalmente los digitales).

Necesario como insumo para C-3 LayoutLMv3 (necesita imagen + texto + bboxes por doc).
LayoutLMv3 normaliza internamente -- no aplicamos CLAHE/deskew, solo render.

Convencion: data/processed/images/processed_<md5>_page_1.jpg

Uso:
    python scripts/generar_imagenes_pag1_faltantes.py
"""
from __future__ import annotations
import hashlib
import sys
import time
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: pip install pymupdf")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
IMAGES = ROOT / "data" / "processed" / "images"
DPI = 150  # suficiente para LayoutLMv3 (que reescala a 224x224)


def md5_file(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def render_page1(pdf_path: Path, out_path: Path, dpi: int = DPI) -> bool:
    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count < 1:
            doc.close()
            return False
        page = doc[0]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        pix.save(str(out_path), jpg_quality=85)
        doc.close()
        return True
    except Exception as e:
        print(f"  ERROR {pdf_path.name}: {e}")
        return False


def main():
    IMAGES.mkdir(parents=True, exist_ok=True)
    print(f"Output: {IMAGES}")
    print(f"DPI render: {DPI}")
    print()

    t0 = time.time()
    n_total = 0
    n_existentes = 0
    n_generados = 0
    n_errores = 0

    for folder in sorted(RAW.iterdir()):
        if not folder.is_dir():
            continue
        if folder.name.startswith("_"):
            print(f"Skip: {folder.name} (prefijo _)")
            continue
        if folder.name.lower().startswith("otro"):
            print(f"Skip: {folder.name} (clase Otros descartada)")
            continue

        pdfs = sorted([p for p in folder.iterdir() if p.suffix.lower() == ".pdf"])
        print(f"[{folder.name}] {len(pdfs)} PDFs")
        for pdf in pdfs:
            n_total += 1
            md5 = md5_file(pdf)
            out = IMAGES / f"processed_{md5}_page_1.jpg"
            if out.exists():
                n_existentes += 1
                continue
            if render_page1(pdf, out):
                n_generados += 1
            else:
                n_errores += 1

    dt = time.time() - t0
    print()
    print("=== RESUMEN ===")
    print(f"PDFs revisados      : {n_total}")
    print(f"Imagenes ya existian : {n_existentes}")
    print(f"Imagenes generadas  : {n_generados}")
    print(f"Errores             : {n_errores}")
    print(f"Tiempo              : {dt:.1f} s ({dt/60:.1f} min)")
    print(f"Imagenes en disco   : {len(list(IMAGES.glob('processed_*_page_1.jpg')))}")


if __name__ == "__main__":
    main()
