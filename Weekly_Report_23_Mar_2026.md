# Project Practicum / Final Report

**Student Name:** Seang Sony  
**Date:** 23-Mar-2026  

# Weekly Report

### Summary of work completed:
1. **Layout Analysis and Document Cropping:** Engineered an OpenCV contour-detection system (`crop_to_main_text_body`) that intelligently strips headers, footers, and noisy page edges out of the image *before* Tesseract OCR is applied.
2. **Formal Accuracy Metrics (CER/WER):** Built a standalone mathematical evaluation script (`evaluate_metrics.py`) using the `jiwer` library. The pipeline can now natively calculate Character Error Rates and Word Error Rates against ground truth texts.
3. **Regex Dictionary Expansion:** Updated the automated post-processing scripts in `ocr_preprocess.py` to automatically catch and correct Tesseract's consistent Khmer misspellings based on rigorous PDF testing.

### Plans for Next Week:
1. Implement the Google Gemini AI API as a final text-correction pass to intelligently fix complex grammatical issues that pattern-based Python dictionaries cannot catch.
2. Polish the Flask User Interface to allow users to easily download the perfectly edited text files.

### Challenges & Issues:
1. Some heavily decorated PDFs with background watermarks still confuse the layout cropping system, requiring dynamic adjustments to the OpenCV bounding boxes.
2. Distinguishing between real Khmer text and random page artifacts (like signatures) remains mathematically complex without AI assistance.

### In Progress:
1. Running stress tests on the improved pre-processing pipeline using 20+ page documents to measure speed and reliability.
2. Preparing the comprehensive architecture diagrams for the final end-of-semester practicum presentation.
