"""
preparar_upload_imagenes_p1.py

Copia a data/_to_upload_images_p1/ todas las imagenes pag 1 (processed_<md5>_page_1.jpg)
para subir a Drive en la ruta esperada por nb12 (C-3 LayoutLMv3):

    MyDrive/datasets/SinergiaLab/processed/images_p1/

Uso:
    python scripts/preparar_upload_imagenes_p1.py

Despues:
    1. Abrir Drive web
    2. Crear carpeta MyDrive/datasets/SinergiaLab/processed/images_p1/
    3. Drag-and-drop el contenido de data/_to_upload_images_p1/ a esa carpeta
"""
from __future__ import annotations
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "images"
DST = ROOT / "data" / "_to_upload_images_p1"


def main():
    if not SRC.exists():
        print(f"ERROR: no existe {SRC}")
        return

    if DST.exists():
        print(f"Limpiando {DST.name}/ existente...")
        shutil.rmtree(DST)
    DST.mkdir()

    # Solo pag 1
    pag1_imgs = sorted(SRC.glob("processed_*_page_1.jpg"))
    print(f"Imagenes pag 1 encontradas: {len(pag1_imgs)}")

    total_size = 0
    for img in pag1_imgs:
        dst = DST / img.name
        shutil.copy2(img, dst)
        total_size += dst.stat().st_size

    print()
    print("=== RESUMEN ===")
    print(f"Imagenes copiadas    : {len(pag1_imgs)}")
    print(f"Tamano total         : {total_size/1e6:.0f} MB ({total_size/1e9:.2f} GB)")
    print(f"Listo para subir desde: {DST}")
    print()
    print("Pasos en Drive:")
    print("  1. Ir a MyDrive/datasets/SinergiaLab/processed/")
    print("  2. Crear subcarpeta images_p1/")
    print("  3. Drag-and-drop el contenido de data/_to_upload_images_p1/ alli")


if __name__ == "__main__":
    main()
