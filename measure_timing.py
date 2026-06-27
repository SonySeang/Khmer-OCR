"""
Measure per-phase processing time for Table 5.5.

Usage:
    python measure_timing.py clean_doc.pdf scan_doc.pdf photo_doc.pdf

If you only have one PDF, pass it for all three types:
    python measure_timing.py doc.pdf doc.pdf doc.pdf

Output:
    Console table  →  copy values into Table 5.5
    timing_results.json  →  raw numbers
"""

import sys
import time
import json
import os
import numpy as np
import cv2

# ── Setup ────────────────────────────────────────────────────────────
os.environ.setdefault('TESSDATA_PREFIX', '/opt/homebrew/share/tessdata')
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

from pdf2image import convert_from_path
from ocr_preprocess import preprocess_for_ocr, postprocess_khmer

TESS_CONFIG = '--oem 1 --psm 4 -c preserve_interword_spaces=1 -c textord_min_linesize=1.5'
LANG        = 'khm+eng'


def _convert_pdf(pdf_path):
    """Convert PDF to PIL images at 300 DPI."""
    return convert_from_path(pdf_path, dpi=300)


def _to_gray(pil_img):
    arr = np.array(pil_img)
    if len(arr.shape) == 3:
        return cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    return arr


def measure_one_pdf(pdf_path, preset, label, runs=3):
    """
    Run the pipeline `runs` times and return average times (seconds).
    Returns dict: preprocessing_s, tesseract_s, postprocess_s, total_s
    """
    print(f"\n  [{label}] converting PDF …", end=' ', flush=True)
    images = _convert_pdf(pdf_path)
    n_pages = len(images)
    print(f"{n_pages} pages")

    all_pre, all_tess, all_post = [], [], []

    for run in range(1, runs + 1):
        print(f"    run {run}/{runs} … ", end='', flush=True)
        t_pre = t_tess = t_post = 0.0

        for img in images:
            # ── Phase 1: Preprocessing ──────────────────────────────
            t0 = time.perf_counter()
            processed = preprocess_for_ocr(img, preset=preset)
            t_pre += time.perf_counter() - t0

            # ── Phase 2: Tesseract OCR ──────────────────────────────
            t0 = time.perf_counter()
            from pytesseract import Output as TessOut
            data = pytesseract.image_to_data(
                processed, lang=LANG, config=TESS_CONFIG,
                output_type=TessOut.DICT, timeout=60
            )
            # reconstruct raw text (same logic as app.py)
            lines = {}
            for i, word in enumerate(data['text']):
                w = str(word).strip()
                if not w:
                    continue
                key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                lines.setdefault(key, []).append(w)
            raw_text = '\n'.join(' '.join(ws) for ws in lines.values())
            t_tess += time.perf_counter() - t0

            # ── Phase 3: Post-processing ────────────────────────────
            t0 = time.perf_counter()
            _ = postprocess_khmer(raw_text)
            t_post += time.perf_counter() - t0

        all_pre.append(t_pre)
        all_tess.append(t_tess)
        all_post.append(t_post)
        print(f"pre={t_pre:.2f}s  tess={t_tess:.2f}s  post={t_post:.2f}s")

    avg_pre  = round(sum(all_pre)  / runs, 1)
    avg_tess = round(sum(all_tess) / runs, 1)
    avg_post = round(sum(all_post) / runs, 1)
    avg_total = round(avg_pre + avg_tess + avg_post, 1)

    return {
        'label':          label,
        'pages':          n_pages,
        'runs':           runs,
        'preprocessing_s':  avg_pre,
        'tesseract_s':      avg_tess,
        'postprocess_s':    avg_post,
        'total_s':          avg_total,
    }


def print_table(results):
    header = f"{'Document Type':<28} {'Preprocessing (s)':>18} {'Tesseract OCR (s)':>18} {'Post-Processing (s)':>20} {'Total (s)':>10}"
    sep    = '-' * len(header)
    print(f"\n{sep}")
    print("Table 5.5  Average Processing Time")
    print(sep)
    print(header)
    print(sep)
    for r in results:
        print(f"{r['label']:<28} {r['preprocessing_s']:>18.1f} {r['tesseract_s']:>18.1f} {r['postprocess_s']:>20.1f} {r['total_s']:>10.1f}")
    print(sep)
    print(f"  (averaged over {results[0]['runs']} runs, {results[0]['pages']} pages per doc)")
    print()


def main():
    docs = {
        'Clean digital PDF':    (sys.argv[1] if len(sys.argv) > 1 else None, 'clean'),
        'Scanned document':     (sys.argv[2] if len(sys.argv) > 2 else None, 'scan'),
        'Photographic document':(sys.argv[3] if len(sys.argv) > 3 else None, 'photo'),
    }

    # ── Validate inputs ──────────────────────────────────────────────
    if not any(p for p, _ in docs.values()):
        print(__doc__)
        sys.exit(1)

    # Fill missing with the first valid path
    first_valid = next((p for p, _ in docs.values() if p), None)
    docs = {
        label: (path or first_valid, preset)
        for label, (path, preset) in docs.items()
    }

    # ── Run measurements ─────────────────────────────────────────────
    print("\nMeasuring processing times …")
    results = []
    for label, (pdf_path, preset) in docs.items():
        if not os.path.exists(pdf_path):
            print(f"  WARNING: {pdf_path} not found — skipping {label}")
            continue
        r = measure_one_pdf(pdf_path, preset, label, runs=3)
        results.append(r)

    if not results:
        print("No results — check that your PDF paths are correct.")
        sys.exit(1)

    # ── Output ───────────────────────────────────────────────────────
    print_table(results)

    out_path = os.path.join(os.path.dirname(__file__), 'timing_results.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Raw numbers saved → timing_results.json")


if __name__ == '__main__':
    main()
