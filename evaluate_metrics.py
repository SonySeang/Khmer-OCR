import cv2
import numpy as np
from PIL import Image

def test_crop():
    print("Testing crop function (run `evaluate_metrics.py` instead for metrics)")
    pass

if __name__ == "__main__":
    import argparse
    import sys
    try:
        import jiwer
    except ImportError:
        print("ERROR: Please install jiwer (pip install jiwer)")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Evaluate OCR Accuracy Metrics (CER/WER).")
    parser.add_argument("ground_truth", help="Path to ground truth text file")
    parser.add_argument("ocr_output", help="Path to OCR output text file")
    args = parser.parse_args()

    # Load files
    try:
        with open(args.ground_truth, 'r', encoding='utf-8') as f:
            gt_text = f.read().strip()
    except Exception as e:
        print(f"Error reading ground truth file: {e}")
        sys.exit(1)

    try:
        with open(args.ocr_output, 'r', encoding='utf-8') as f:
            ocr_text = f.read().strip()
    except Exception as e:
        print(f"Error reading OCR output file: {e}")
        sys.exit(1)

    # Normalize whitespace for clean comparison
    import re
    gt_clean = re.sub(r'\s+', ' ', gt_text)
    ocr_clean = re.sub(r'\s+', ' ', ocr_text)

    # Calculate metrics
    cer = jiwer.cer(gt_clean, ocr_clean)
    wer = jiwer.wer(gt_clean, ocr_clean)

    print("\n==================================")
    print(" 📊 OCR Accuracy Metrics Report")
    print("==================================")
    print(f"Ground Truth File : {args.ground_truth}")
    print(f"OCR Output File   : {args.ocr_output}")
    print("----------------------------------")
    print(f"📈 Character Error Rate (CER): {cer * 100:.2f}%")
    print(f"📈 Word Error Rate (WER)     : {wer * 100:.2f}%")
    print("==================================\n")
    print("* Lower percentages are better! *")
