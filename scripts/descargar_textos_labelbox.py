"""
Descarga los textos desde las URLs firmadas de Labelbox antes que expiren
y los guarda localmente en data/raw/ner_corpus/.

Los 3 NDJSON exports comparten algunos doc_ids (mismo data_row.id) entre
anotadores; deduplicamos por id para evitar descargas redundantes.
"""
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "raw" / "ner_corpus"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NDJSON_DIR = ROOT / "data" / "raw" / "ner_annotations"

NDJSON_FILES = [
    "Export  project - NER_Documentos_CAMILO.ndjson",
    "export_Mateo_20260512 (1).ndjson",
    "export_Sebas_20260513.ndjson",
]


def collect_jobs():
    """Devuelve lista de (data_row_id, external_id, url) sin duplicados."""
    seen = {}
    for nm in NDJSON_FILES:
        p = NDJSON_DIR / nm
        if not p.exists():
            print(f"  WARN: no existe {nm}")
            continue
        with p.open(encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                drow = d.get("data_row", {})
                rid = drow.get("id")
                if not rid or rid in seen:
                    continue
                seen[rid] = {
                    "id": rid,
                    "external_id": drow.get("external_id", ""),
                    "url": drow.get("row_data", ""),
                }
    return list(seen.values())


def download_one(job):
    """Descarga un texto y lo guarda como <id>.txt; retorna (id, status, size)."""
    out = OUT_DIR / f"{job['id']}.txt"
    if out.exists() and out.stat().st_size > 100:
        return (job["id"], "cached", out.stat().st_size)
    try:
        req = urllib.request.Request(job["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        out.write_bytes(data)
        return (job["id"], "ok", len(data))
    except Exception as e:
        return (job["id"], f"ERR: {e}", 0)


def main():
    jobs = collect_jobs()
    print(f"Total documentos únicos a descargar: {len(jobs)}")
    print(f"Carpeta destino: {OUT_DIR}")

    ok = err = cached = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        futures = {ex.submit(download_one, j): j for j in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            rid, status, size = fut.result()
            if status == "ok":
                ok += 1
            elif status == "cached":
                cached += 1
            else:
                err += 1
                print(f"  [{i:3d}] {rid}: {status}")
            if i % 50 == 0:
                print(f"  Progreso: {i}/{len(jobs)}  (ok={ok}, cache={cached}, err={err})")

    print(f"\nResumen:")
    print(f"  OK descargados : {ok}")
    print(f"  Ya en caché    : {cached}")
    print(f"  Errores        : {err}")
    print(f"  Total en disco : {len(list(OUT_DIR.glob('*.txt')))}")


if __name__ == "__main__":
    main()
