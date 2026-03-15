"""
OCR Preprocessing Module for Khmer Text Extraction
====================================================
Smart preprocessing pipeline that auto-detects document quality
and applies the optimal processing for each image.

Usage:
    from ocr_preprocess import preprocess_for_ocr, read_pdf_improved
    
    # For a single image:
    clean_img = preprocess_for_ocr(pil_image)
    
    # For a full PDF:
    text = read_pdf_improved("Document/docx_1.pdf")
"""

import cv2
import numpy as np
from PIL import Image
import re


# ============================================================
# DOCUMENT QUALITY AUTO-DETECTION
# ============================================================
def detect_image_quality(gray_img):
    """
    Analyze image to determine if it's a clean digital PDF
    or a noisy scan/photo. Returns a quality score and recommendation.
    
    Returns:
        dict with keys:
            - noise_level: float (0=clean, higher=noisier)
            - contrast: float (standard deviation of pixel values)
            - is_clean: bool (True = clean digital PDF)
            - recommended_preset: str ('clean', 'scan', 'photo')
    """
    # Measure noise using Laplacian variance
    laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
    noise_level = laplacian.var()
    
    # Measure contrast (standard deviation of pixel values)
    contrast = np.std(gray_img)
    
    # Measure how much of the image is "white" background
    white_ratio = np.mean(gray_img > 200) * 100
    
    # Decision logic
    if white_ratio > 60 and contrast > 60:
        # Lots of white background, good contrast = clean digital PDF
        preset = "clean"
        is_clean = True
    elif noise_level > 2000:
        # Very noisy = photo of document
        preset = "photo"
        is_clean = False
    else:
        # Medium quality = scanned document
        preset = "scan"
        is_clean = False
    
    return {
        'noise_level': round(noise_level, 1),
        'contrast': round(contrast, 1),
        'white_ratio': round(white_ratio, 1),
        'is_clean': is_clean,
        'recommended_preset': preset
    }


# ============================================================
# INDIVIDUAL PROCESSING STAGES
# ============================================================
def to_grayscale(img_array):
    """Convert image to grayscale if it's color."""
    if len(img_array.shape) == 3:
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    return img_array


def remove_noise(gray, method="bilateral"):
    """
    Remove noise while preserving edges.
    - 'bilateral': Fast, good edge preservation
    - 'nlm': Slower but best quality (Non-Local Means)
    - 'gaussian': Simple blur
    """
    if method == "bilateral":
        return cv2.bilateralFilter(gray, 9, 75, 75)
    elif method == "nlm":
        return cv2.fastNlMeansDenoising(gray, h=10)
    elif method == "gaussian":
        return cv2.GaussianBlur(gray, (3, 3), 0)
    return gray


def enhance_contrast(gray, clip_limit=2.0):
    """Apply CLAHE for uneven lighting correction."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def deskew(binary_img):
    """Detect and correct text rotation angle."""
    coords = np.column_stack(np.where(binary_img > 0))
    if len(coords) < 100:
        return binary_img
    
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    if abs(angle) > 10 or abs(angle) < 0.1:
        return binary_img
    
    h, w = binary_img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(binary_img, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def binarize(gray, method="adaptive"):
    """
    Convert to black & white.
    - 'otsu': Auto threshold (better for clean docs)
    - 'adaptive': Better for uneven lighting
    """
    if method == "otsu":
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    elif method == "adaptive":
        return cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 31, 2
        )
    return gray


def morphological_cleanup(binary):
    """Repair broken Khmer character strokes and remove noise dots."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
    return cleaned


# ============================================================
# SMART PIPELINE: Auto-selects best processing for each image
# ============================================================
def preprocess_for_ocr(pil_image, preset="auto", upscale_factor=2, verbose=False):
    """
    Smart preprocessing pipeline. Auto-detects document quality
    and applies the right combination of techniques.
    
    Presets:
        - 'auto': Detect quality and choose best pipeline
        - 'clean': Minimal processing for clean digital PDFs
        - 'scan': Moderate processing for scanned documents
        - 'photo': Heavy processing for photos of documents
    
    Returns:
        PIL Image: Preprocessed image ready for Tesseract
    """
    img = np.array(pil_image)
    gray = to_grayscale(img)
    
    # Upscale
    if upscale_factor > 1:
        if verbose: print(f"   ↳ Upscaling {upscale_factor}x...")
        gray = cv2.resize(gray, None, fx=upscale_factor, fy=upscale_factor,
                         interpolation=cv2.INTER_CUBIC)
    
    # Auto-detect quality if preset is "auto"
    if preset == "auto":
        quality = detect_image_quality(gray)
        preset = quality['recommended_preset']
        if verbose:
            print(f"   ↳ Auto-detected: {preset} document "
                  f"(noise={quality['noise_level']}, "
                  f"contrast={quality['contrast']}, "
                  f"white={quality['white_ratio']}%)")
    
    # Apply preset-specific pipeline
    if preset == "clean":
        # Clean digital PDF: minimal processing to avoid introducing artifacts
        if verbose: print("   ↳ Pipeline: adaptive threshold (light touch)")
        binary = binarize(gray, method="adaptive")
        binary = deskew(binary)
    
    elif preset == "scan":
        # Scanned document: moderate denoising + CLAHE + adaptive
        if verbose: print("   ↳ Pipeline: denoise → CLAHE → adaptive → deskew → cleanup")
        denoised = remove_noise(gray, method="bilateral")
        enhanced = enhance_contrast(denoised, clip_limit=2.0)
        binary = binarize(enhanced, method="adaptive")
        binary = deskew(binary)
        binary = morphological_cleanup(binary)
    
    elif preset == "photo":
        # Photo of document: heavy denoising + CLAHE + morphology
        if verbose: print("   ↳ Pipeline: heavy denoise → CLAHE → otsu → deskew → cleanup")
        denoised = remove_noise(gray, method="nlm")
        enhanced = enhance_contrast(denoised, clip_limit=3.0)
        binary = binarize(enhanced, method="otsu")
        binary = deskew(binary)
        binary = morphological_cleanup(binary)
    
    else:
        # Fallback
        binary = binarize(gray, method="adaptive")
    
    return Image.fromarray(binary)


# ============================================================
# KHMER POST-PROCESSING: Fix common OCR errors in text
# ============================================================
def postprocess_khmer(text):
    """
    Fix common Tesseract OCR errors specific to Khmer text.
    General-purpose corrections that work for any Khmer PDF document.
    """
    
    # ---- STEP 1: Line-level cleanup (remove garbage lines) ----
    cleaned_lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        
        # Remove empty lines
        if not stripped:
            continue
            
        # Remove standalone page numbers (single digit on its own line)
        if re.match(r'^\d{1,2}$', stripped):
            continue
        
        # Remove very short garbage lines (1-2 random characters, not Khmer numbers)
        if len(stripped) <= 2 and not re.match(r'^[\u1780-\u17FF]', stripped) and stripped not in ('', '•'):
            continue
            
        # Count Khmer characters vs Total characters
        khmer_chars = len(re.findall(r'[\u1780-\u17FF]', stripped))
        total_chars = len(stripped)
        
        # Remove lines that are mostly English garbage or symbols (common with graphs/noise)
        if total_chars > 0:
            khmer_ratio = khmer_chars / total_chars
            
            # If line is longer than 5 chars and has less than 15% Khmer chars, it's likely noise
            if total_chars > 5 and khmer_ratio < 0.15:
                # Keep lines with known useful content (page markers, known English names)
                known_english = ['MSME', 'ChatGPT', 'Gemini', 'Claude', 'Copilot', 'JOTA', 'EdTech', 'AI', 'Al', 'IFC', 'NBC', 'CMA']
                if not any(eng in stripped for eng in known_english) and not stripped.startswith('--- Page'):
                    continue
            
            # If line has NO Khmer characters at all
            elif khmer_chars == 0:
                known_english = ['MSME', 'ChatGPT', 'Gemini', 'Claude', 'Copilot', 'JOTA', 'EdTech', 'AI', 'Al', 'IFC', 'NBC', 'CMA']
                if not any(eng in stripped for eng in known_english) and not stripped.startswith('--- Page') and not re.match(r'^[0-9\s\.\,\-\%]+$', stripped):
                    continue
        
        cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    # ---- STEP 2: Khmer character corrections ----
    corrections = [
        # Bullet points: '9' is often misread instead of '•'
        (r'^9\s', '• '),
        (r'\n9\s', '\n• '),
        
        # Common missing vowels
        ('ក្នង', 'ក្នុង'),           # Missing ុ
        ('ព្រមទាង', 'ព្រមទាំង'),     # Missing ំ
        ('ដំណេរ', 'ដំណើរ'),         # Missing ើ
        ('ស័ក្សា', 'សិក្សា'),         # Vowel confusion
        ('កម្ពជា', 'កម្ពុជា'),        # Missing ុ
        ('ឥំរិយាបថ', 'ឥរិយាបថ'),    # Extra ំ
        
        # Common character confusions
        ('គួអង្គ', 'តួអង្គ'),         # គួ → តួ
        ('គ្រួបង្រៀន', 'គ្រូបង្រៀន'),   # គ្រួ → គ្រូ
        ('រំពុក', 'រំឭក'),            # Misread
        ('រំពូក', 'រំឭក'),            # Misread variant
        ('ឌីជីប៉ល', 'ឌីជីថល'),       # ប៉ → ថ
        ('ទិសេដា', 'ទិសដៅ'),         # Misread
        
        # Common word-level fixes
        ('ក្លូយៗ', 'កូនៗ'),          # Misread word
        ('បំណេះ', 'បំណិន'),          # Common confusion (may vary)
        
        # Section header fixes
        ('៖ស', 'សេ'),               # ៖ If prefix on សេចក្តី
    ]
    
    for pattern, replacement in corrections:
        if pattern.startswith('^') or pattern.startswith('\\n'):
            result = re.sub(pattern, replacement, result, flags=re.MULTILINE)
        else:
            result = result.replace(pattern, replacement)
    
    # ---- STEP 3: Symbol cleanup ----
    result = re.sub(r'\|', '', result)           # Stray pipe characters
    result = re.sub(r'^- =\s', '-  ', result, flags=re.MULTILINE)  # "- =" → "-"
    result = re.sub(r'\s/\s', ' ', result)       # Stray " / " separators
    result = re.sub(r'\s{3,}', '  ', result)     # Compress excessive whitespace
    result = re.sub(r'^\]\s*$', '', result, flags=re.MULTILINE)  # Stray brackets
    
    # ---- STEP 4: Fix broken words (space in middle) ----
    result = re.sub(r'បា\s+ន', 'បាន', result)    # ដែលបា ន → ដែលបាន
    result = re.sub(r'រួ\s+ម', 'រួម', result)      # រួ ម → រួម
    
    # Remove empty lines left by cleanup (keep max 2 consecutive)
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    
    return result


# ============================================================
# FULL PDF READER: Replaces your read_pdf_file function
# ============================================================
def read_pdf_improved(filename, dpi=300, preset="auto", apply_postprocess=True, verbose=True):
    """
    Improved PDF text extraction with smart preprocessing.
    
    Drop-in replacement for read_pdf_file() in your notebook.
    
    Args:
        filename: Path to PDF file
        dpi: Resolution for PDF→image conversion (300 recommended)
        preset: 'auto', 'clean', 'scan', or 'photo'
        apply_postprocess: Whether to run Khmer text corrections
        verbose: Print progress
    
    Returns:
        str: Extracted text from all pages
    """
    import pytesseract
    from pdf2image import convert_from_path
    import os
    
    # Set Tesseract path
    try:
        conda_prefix = os.environ.get('CONDA_PREFIX')
        pytesseract.pytesseract.tesseract_cmd = f"{conda_prefix}/bin/tesseract"
    except:
        pass
    
    if verbose:
        print(f"📄 Loading: {filename}")
    
    images = convert_from_path(filename, dpi=dpi)
    
    if verbose:
        print(f"   Found {len(images)} pages")
    
    config = '--oem 3 --psm 3 -c preserve_interword_spaces=1'
    extracted_text = ""
    
    for i, img in enumerate(images):
        if verbose:
            print(f"\n📸 Processing Page {i+1}/{len(images)}...")
        
        # Smart preprocessing
        processed = preprocess_for_ocr(img, preset=preset, verbose=verbose)
        
        # OCR
        text = pytesseract.image_to_string(processed, lang='khm+eng', config=config)
        
        # Post-processing corrections
        if apply_postprocess:
            text = postprocess_khmer(text)
        
        extracted_text += f"--- Page {i+1} ---\n{text}\n"
    
    if verbose:
        print(f"\n✅ Extraction complete!")
    
    return extracted_text


# ============================================================
# LEGACY: Old preprocessing (kept for comparison)
# ============================================================
def preprocess_old(pil_image):
    """Original preprocessing: upscale + adaptive threshold."""
    img = np.array(pil_image)
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 31, 2)
    return Image.fromarray(binary)


def get_best_tesseract_config():
    """Returns recommended Tesseract config for Khmer documents."""
    return '--oem 3 --psm 3 -c preserve_interword_spaces=1'


# ============================================================
# PHASE 3: AI TEXT CORRECTION (Google Gemini)
# ============================================================
def correct_with_ai(text, api_key=None, model="gemini-2.0-flash"):
    """
    Use Google Gemini AI to fix OCR errors in Khmer text.
    
    The AI understands Khmer language context and can fix errors
    that pattern-based post-processing cannot handle.
    
    Args:
        text: OCR text to correct
        api_key: Google API key (or set GOOGLE_API_KEY env variable)
        model: Gemini model to use
    
    Returns:
        str: Corrected text
    """
    import os
    from google import genai
    
    # Load API key from .env file (no extra dependency needed)
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))
    
    key = api_key or os.environ.get('GOOGLE_API_KEY')
    if not key:
        print("❌ No API key! Set GOOGLE_API_KEY environment variable or pass api_key parameter.")
        print("   Example: export GOOGLE_API_KEY='your-key-here'")
        return text
    
    # Create client
    client = genai.Client(api_key=key)
    
    prompt = f"""You are a Khmer OCR error correction expert. 
The following text was extracted from a PDF using Tesseract OCR. 
It contains errors specific to Khmer script OCR.

RULES:
1. Fix ONLY clear OCR errors — do NOT rewrite or paraphrase
2. Remove garbage text (random English words mixed into Khmer lines like "Shavidiunus", "givows-womo", "iy", "Sd.")
3. Fix broken Khmer characters and missing vowels
4. Keep the original structure, line breaks, and formatting
5. Keep page separators like "--- Page X ---"
6. Keep legitimate English words (ChatGPT, Gemini, AI, JOTA-JOTI, EdTech, etc.)
7. Return ONLY the corrected text, no explanations

TEXT TO CORRECT:
{text}"""
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"⚠️ AI correction failed: {e}")
        print("   Returning text with only post-processing corrections.")
        return text


def read_pdf_with_ai(filename, api_key=None, dpi=300, preset="auto", verbose=True):
    """
    Full pipeline: PDF → Preprocessing → OCR → Post-Processing → AI Correction.
    
    This is the best quality extraction, combining all 3 phases.
    
    Args:
        filename: Path to PDF file
        api_key: Google API key (or set GOOGLE_API_KEY env variable)
        dpi: Resolution (300 recommended)
        preset: 'auto', 'clean', 'scan', or 'photo'
        verbose: Print progress
    
    Returns:
        str: AI-corrected extracted text
    """
    # Phase 1 + 2: Preprocessing + OCR + Post-processing
    if verbose:
        print("📋 Phase 1-2: Preprocessing + OCR + Post-processing")
    text = read_pdf_improved(filename, dpi=dpi, preset=preset, 
                              apply_postprocess=True, verbose=verbose)
    
    # Phase 3: AI Correction
    if verbose:
        print("\n🤖 Phase 3: AI Correction (Google Gemini)...")
    
    corrected = correct_with_ai(text, api_key=api_key)
    
    if verbose:
        print("✅ AI correction complete!")
    
    return corrected
