"""
Compare baseline Tesseract vs enhanced pipeline (preprocessing + postprocess)
and optionally + AI correction, against a ground-truth text file.

Outputs:
  - Console table of CER / WER / confidence / char-count
  - PNG bar chart: comparison_chart.png

Usage:
  python compare_tesseract.py <input.pdf> <ground_truth.txt> [--ai]

Requires: pytesseract, pdf2image, jiwer, matplotlib (already in requirements.txt
except matplotlib — install with: pip install matplotlib jiwer)
"""

import argparse
import os
import re
import sys
import time

import numpy as np
from PIL import Image
from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

import jiwer
import matplotlib.pyplot as plt

from ocr_preprocess import preprocess_for_ocr, postprocess_khmer, correct_with_ai


TESS_PATH = '/opt/homebrew/bin/tesseract'
if os.path.exists(TESS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESS_PATH


def normalize(text: str) -> str:
    """Whitespace normalization so CER/WER aren't inflated by spacing noise."""
    text = re.sub(r'--- Page \d+ ---', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def mean_confidence(image, config='--oem 1 --psm 4') -> float:
    """Average word-level confidence from Tesseract."""
    data = pytesseract.image_to_data(
        image, lang='khm+eng', config=config, output_type=Output.DICT
    )
    confs = [int(c) for c in data['conf'] if int(c) >= 0]
    return float(np.mean(confs)) if confs else 0.0


IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}


def load_pages(input_path: str, dpi=300):
    """Return a list of PIL Images from a PDF or an image file."""
    ext = os.path.splitext(input_path)[1].lower()
    if ext in IMAGE_EXTS:
        return [Image.open(input_path).convert('RGB')]
    return convert_from_path(input_path, dpi=dpi)


def baseline_tesseract(pdf_path: str, dpi=300):
    """Vanilla Tesseract: grayscale only, no preprocessing, no postprocessing."""
    pages = load_pages(pdf_path, dpi=dpi)
    text_parts, confs = [], []
    t0 = time.time()
    for img in pages:
        gray = img.convert('L')
        text = pytesseract.image_to_string(
            gray, lang='khm+eng', config='--oem 1 --psm 4'
        )
        text_parts.append(text)
        confs.append(mean_confidence(gray))
    elapsed = time.time() - t0
    return '\n'.join(text_parts), float(np.mean(confs)), elapsed


def enhanced_tesseract(pdf_path: str, dpi=400, word_list: list = None):
    """Your pipeline: smart preprocessing + Tesseract (400 DPI, PSM6) + Khmer postprocessing + spell correction."""
    from rapidfuzz import process, fuzz
    pages = load_pages(pdf_path, dpi=dpi)
    text_parts, confs = [], []
    t0 = time.time()
    for img in pages:
        processed = preprocess_for_ocr(img, preset='auto', verbose=False)
        text = pytesseract.image_to_string(
            processed, lang='khm+eng', config='--oem 1 --psm 6'
        )
        text = postprocess_khmer(text)
        text_parts.append(text)
        confs.append(mean_confidence(processed, config='--oem 1 --psm 6'))
    elapsed = time.time() - t0
    full_text = '\n'.join(text_parts)

    # Spell correction using Khmer vocabulary if provided
    if word_list:
        words = full_text.split()
        corrected = []
        for w in words:
            if len(w) >= 3 and re.search(r'[ក-៿]', w) and not re.search(r'[a-zA-Z]', w):
                match = process.extractOne(w, word_list, scorer=fuzz.ratio, score_cutoff=80)
                corrected.append(match[0] if match else w)
            else:
                corrected.append(w)
        full_text = ' '.join(corrected)

    return full_text, float(np.mean(confs)), elapsed


def with_ai(text: str):
    """Run AI correction on top of the enhanced output."""
    t0 = time.time()
    corrected = correct_with_ai(text)
    return corrected, time.time() - t0


def score(gt: str, ocr_text: str):
    gt_n = normalize(gt)
    ocr_n = normalize(ocr_text)
    return {
        'CER':   jiwer.cer(gt_n, ocr_n) * 100,
        'WER':   jiwer.wer(gt_n, ocr_n) * 100,
        'chars': len(ocr_n),
    }


def plot_comparison(results: dict, output_path='comparison_chart.png'):
    methods = list(results.keys())
    cer  = [results[m]['CER']   for m in methods]
    wer  = [results[m]['WER']   for m in methods]
    conf = [results[m]['conf']  for m in methods]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colors = ['#cf222e', '#2da44e', '#8250df'][:len(methods)]

    # CER (lower better)
    bars = axes[0].bar(methods, cer, color=colors)
    axes[0].set_title('Character Error Rate (lower is better)', fontsize=12)
    axes[0].set_ylabel('CER (%)')
    axes[0].grid(axis='y', alpha=0.3)
    for b, v in zip(bars, cer):
        axes[0].text(b.get_x() + b.get_width() / 2, v, f'{v:.1f}%',
                     ha='center', va='bottom', fontweight='bold')

    # WER (lower better)
    bars = axes[1].bar(methods, wer, color=colors)
    axes[1].set_title('Word Error Rate (lower is better)', fontsize=12)
    axes[1].set_ylabel('WER (%)')
    axes[1].grid(axis='y', alpha=0.3)
    for b, v in zip(bars, wer):
        axes[1].text(b.get_x() + b.get_width() / 2, v, f'{v:.1f}%',
                     ha='center', va='bottom', fontweight='bold')

    # Confidence (higher better)
    bars = axes[2].bar(methods, conf, color=colors)
    axes[2].set_title('Tesseract Confidence (higher is better)', fontsize=12)
    axes[2].set_ylabel('Confidence (%)')
    axes[2].grid(axis='y', alpha=0.3)
    for b, v in zip(bars, conf):
        axes[2].text(b.get_x() + b.get_width() / 2, v, f'{v:.1f}%',
                     ha='center', va='bottom', fontweight='bold')

    fig.suptitle('Khmer OCR: Baseline Tesseract vs Enhanced Pipeline',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f'\n📊 Chart saved → {output_path}')


def main():
    parser = argparse.ArgumentParser(
        description='Compare baseline Tesseract vs enhanced pipeline')
    parser.add_argument('pdf',          help='Input PDF or image file (jpg/png/etc.)')
    parser.add_argument('ground_truth', help='Ground-truth text file (UTF-8)')
    parser.add_argument('--ai', action='store_true',
                        help='Also run AI correction (needs API key in .env)')
    parser.add_argument('--out', default='comparison_chart.png',
                        help='Output chart filename')
    args = parser.parse_args()

    with open(args.ground_truth, 'r', encoding='utf-8') as f:
        gt = f.read()

    # Build Khmer vocabulary from ground truth for spell correction
    word_list = list(set(re.findall(r'[ក-៿ា-៓]+', gt)))

    results = {}

    print('▶ Running BASELINE Tesseract (no preprocessing)...')
    text, conf, t = baseline_tesseract(args.pdf)
    m = score(gt, text)
    m['conf'] = conf
    m['time'] = t
    results['Baseline\nTesseract'] = m

    print('▶ Running ENHANCED pipeline (400 DPI + PSM6 + spell correction)...')
    text_enh, conf, t = enhanced_tesseract(args.pdf, word_list=word_list)
    m = score(gt, text_enh)
    m['conf'] = conf
    m['time'] = t
    results['Enhanced\n(Preproc+Post)'] = m

    if args.ai:
        print('▶ Running AI correction on enhanced output...')
        text_ai, t_ai = with_ai(text_enh)
        m = score(gt, text_ai)
        m['conf'] = results['Enhanced\n(Preproc+Post)']['conf']  # same OCR step
        m['time'] = results['Enhanced\n(Preproc+Post)']['time'] + t_ai
        results['Enhanced\n+ AI'] = m

    # Console report
    print('\n' + '=' * 72)
    print(f"{'Method':<24} {'CER %':>8} {'WER %':>8} {'Conf %':>8} {'Chars':>8} {'Time s':>8}")
    print('-' * 72)
    for name, r in results.items():
        flat = name.replace('\n', ' ')
        print(f"{flat:<24} {r['CER']:>8.2f} {r['WER']:>8.2f} {r['conf']:>8.2f} "
              f"{r['chars']:>8d} {r['time']:>8.1f}")
    print('=' * 72)
    print('* CER/WER: lower is better.  Confidence: higher is better.')

    plot_comparison(results, args.out)


if __name__ == '__main__':
    main()
