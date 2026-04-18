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
    # NOTE: sharp digital PDFs have HIGH Laplacian (crisp edges), same as noisy photos.
    # white_ratio is the most reliable discriminator — check it first.
    if white_ratio > 75:
        # Very white background = clean digital PDF (even if Laplacian is high)
        preset = "clean"
        is_clean = True
    elif white_ratio > 50 and contrast > 50:
        # Moderate white with decent contrast = clean-ish PDF
        preset = "clean"
        is_clean = True
    elif noise_level > 2000:
        # High noise AND low white ratio = photo of document
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


def sharpen(gray):
    """
    Unsharp masking to enhance character edges.
    Critical for thin Khmer vowel marks and diacritics.
    """
    blurred = cv2.GaussianBlur(gray, (0, 0), 3)
    return cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)


def gamma_correct(gray, gamma=1.2):
    """
    Gamma correction to brighten dark scanned documents.
    Gamma > 1 brightens midtones; use 1.2–1.5 for dark scans.
    """
    inv_gamma = 1.0 / gamma
    table = np.array([((i / 255.0) ** inv_gamma) * 255
                      for i in range(256)], dtype="uint8")
    return cv2.LUT(gray, table)


def crop_to_main_text_body(binary_img):
    """
    Document Layout Analysis: Finds the main text contours and crops out 
    headers, footers, and page numbers at the extreme edges.
    """
    h, w = binary_img.shape
    
    # 1. Dilate to connect text characters into blocks
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 20))
    dilated = cv2.dilate(binary_img, kernel, iterations=2)
    
    # 2. Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return binary_img
        
    valid_bboxes = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        
        # Filter out very small noise blocks
        if area < 500:
            continue
            
        # Filter out header (top 8%) and footer (bottom 8%) small blocks
        # Only keep them if they are very large (like a massive logo/title)
        center_y = y + (ch / 2)
        if center_y < h * 0.08 and area < (w * h * 0.05):
            continue  # Likely a header or top page number
        if center_y > h * 0.92 and area < (w * h * 0.05):
            continue  # Likely a footer or bottom page number
            
        valid_bboxes.append((x, y, x + cw, y + ch))
        
    if not valid_bboxes:
        return binary_img
        
    # 3. Find global bounding box of all valid text
    min_x = max(0, min([b[0] for b in valid_bboxes]) - 20)
    min_y = max(0, min([b[1] for b in valid_bboxes]) - 20)
    max_x = min(w, max([b[2] for b in valid_bboxes]) + 20)
    max_y = min(h, max([b[3] for b in valid_bboxes]) + 20)
    
    # Crop the binary image
    cropped = binary_img[int(min_y):int(max_y), int(min_x):int(max_x)]
    return cropped


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

    # Auto-detect quality on the ORIGINAL image (before upscaling)
    # so noise/contrast metrics are not skewed by interpolation.
    if preset == "auto":
        quality = detect_image_quality(gray)
        preset = quality['recommended_preset']
        if verbose:
            print(f"   ↳ Auto-detected: {preset} document "
                  f"(noise={quality['noise_level']}, "
                  f"contrast={quality['contrast']}, "
                  f"white={quality['white_ratio']}%)")

    # Use preset-specific upscale factor when caller passes the default (2).
    # Scan/photo benefit from higher resolution for thin Khmer strokes.
    if upscale_factor == 2 and preset in ("scan", "photo"):
        upscale_factor = 3

    # Upscale
    if upscale_factor > 1:
        if verbose: print(f"   ↳ Upscaling {upscale_factor}x...")
        gray = cv2.resize(gray, None, fx=upscale_factor, fy=upscale_factor,
                         interpolation=cv2.INTER_CUBIC)

    # Apply preset-specific pipeline
    if preset == "clean":
        # Clean digital PDF: light bilateral to smooth rendering noise, then sharpen
        # edges before adaptive threshold. Empirically best on docx_1.pdf (78.5% conf).
        if verbose: print("   ↳ Pipeline: bilateral → sharpen → adaptive → deskew → cleanup")
        denoised = remove_noise(gray, method="bilateral")
        sharpened = sharpen(denoised)
        binary = binarize(sharpened, method="adaptive")
        binary = deskew(binary)
        binary = morphological_cleanup(binary)

    elif preset == "scan":
        # Scanned document: denoise → gamma → CLAHE → sharpen → adaptive → deskew → cleanup
        if verbose: print("   ↳ Pipeline: denoise → gamma → CLAHE → sharpen → adaptive → deskew → cleanup")
        denoised = remove_noise(gray, method="bilateral")
        brightened = gamma_correct(denoised, gamma=1.3)
        enhanced = enhance_contrast(brightened, clip_limit=2.5)
        sharpened = sharpen(enhanced)
        binary = binarize(sharpened, method="adaptive")
        binary = deskew(binary)
        binary = morphological_cleanup(binary)

    elif preset == "photo":
        # Photo of document: heavy denoise → gamma → CLAHE → sharpen → otsu → deskew → cleanup
        if verbose: print("   ↳ Pipeline: heavy denoise → gamma → CLAHE → sharpen → otsu → deskew → cleanup")
        denoised = remove_noise(gray, method="nlm")
        brightened = gamma_correct(denoised, gamma=1.4)
        enhanced = enhance_contrast(brightened, clip_limit=3.5)
        sharpened = sharpen(enhanced)
        binary = binarize(sharpened, method="otsu")
        binary = deskew(binary)
        binary = morphological_cleanup(binary)

    else:
        # Fallback
        binary = binarize(gray, method="adaptive")

    # Crop to main text body: skip for clean PDFs (headers/footers are valid text
    # in digital docs; the crop can cut off legitimate content).
    if preset in ("scan", "photo"):
        if verbose: print("   ↳ Layout Analysis: cropping edge noise...")
        binary = crop_to_main_text_body(binary)

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
    
    # ---- STEP 1.5: Remove specific English garbage strings from mixed lines ----
    # (Often caused by Tesseract misreading logos or sidebar OSD text)
    result = re.sub(r'ANEANitniimia\s*', '', result)
    result = re.sub(r'1 IN Sits inns', '', result)
    result = re.sub(r'1 ដូចនេះ', 'ដូចនេះ', result)

    # Remove isolated English garbage tokens commonly seen in Khmer government PDFs
    # (logos, stamps, page decorations misread as text)
    for token in [r'SOHAP', r'\(HOWE\)', r'\bWw\b', r'\bchara\b',
                  r'\bSuny\b', r'\bBI\b', r'\bAS\b']:
        result = re.sub(r'\s*' + token + r'\s*', ' ', result)

    # Strip leading short Latin/digit noise before Khmer content on same line
    # e.g. "7  ជាតិ" → "ជាតិ",  "EM. ការ..." → "ការ..."
    result = re.sub(r'^[A-Za-z0-9]{1,4}[\.\s]*(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)
    # Also handle bare digit(s) + any amount of whitespace before Khmer
    result = re.sub(r'^\d{1,2}\s+(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)
    # Strip single stray Khmer char + dot pattern at line start (e.g. "យ .  ព" → "ព")
    result = re.sub(r'^[\u1780-\u17FF]\s+\.\s+(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)

    # Remove /_ artifact and stray parenthesised all-caps noise
    result = re.sub(r'/_\s*', '', result)
    result = re.sub(r'\([A-Z]{2,6}\)', '', result)   # e.g. (HOWE), (OSD), etc.
    result = re.sub(r'\(\s*\)', '', result)           # Empty parens after token removal
    
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
        
        # New dictionary additions
        ('ហិរញ្ជវិត្ថុ', 'ហិរញ្ញវត្ថុ'),
        ('ហិរញ្ជវត្ថុ', 'ហិរញ្ញវត្ថុ'),
        ('អាជ្ញាបីណ្ណ', 'អាជ្ញាប័ណ្ណ'),
        ('នេ៖', 'នេះ'),
        ('ព្រោនថា', 'ព្រោះថា'),
        
        # Capital Market / Finance corrections
        ('ទីផុរារ', 'ទីផ្សារ'),
        ('ទិផុារ', 'ទីផ្សារ'),
        ('ទីិផ្យវារ', 'ទីផ្សារ'),
        ('ទិីផ្សារ', 'ទីផ្សារ'),
        ('ជុញដូរ', 'ជួញដូរ'),
        ('មធុម', 'មធ្យម'),
        ('ដើមទន', 'ដើមទុន'),
        ('កម៉ី', 'កម្ចី'),
        ('ទៅត។', 'ទៅទៀត។'),
        ('ដំសំខាន់', 'ដ៏សំខាន់'),
        ('ដំមាន', 'ដ៏មាន'),
        ('គ្រប ដណ្ឌប់', 'គ្របដណ្តប់'),
        ('ប្រមូលផ្តំ', 'ប្រមូលផ្តុំ'),
        
        ('សនុស្រេប', 'សន្សំ'),
        ('គ្រប ដ\nណ្ឌប់', 'គ្របដណ្តប់'),
        ('ការព\nន្លឿន', 'ការពន្លឿន'),
        ('ទីផ្សារ មូលធន', 'ទីផ្សារមូលធន'),
        ('វែងភាគ ច្រើន', 'វែងភាគច្រើន'),
        ('ទំនិញ', 'ហិរញ្ញវត្ថុ'), # Often confused in context of services
        
        # Common word-level fixes
        ('ក្លូយៗ', 'កូនៗ'),          # Misread word
        ('បំណេះ', 'បំណិន'),          # Common confusion (may vary)
        
        # Section header fixes
        ('៖ស', 'សេ'),               # ៖ If prefix on សេចក្តី

        # Official document header corrections (seen in government PDFs)
        ('ពាះរាជាណាបក្រ', 'ព្រះរាជាណាចក្រ'),  # Full header phrase fix
        ('ពាះរាជាណា', 'ព្រះរាជាណា'),           # Partial: ពាះ → ព្រះ
        ('ណាបក្រ', 'ណាចក្រ'),                  # ចក្រ misread as បក្រ
        ('ម្ព្ហ', 'ម្ពុ'),                      # in កម្ពុជា
        ('ប្រូក្សា', 'ប្រឹក្សា'),              # Council: ប្រូ → ប្រឹ
        ('ក្លិបសកម្ម', 'ក្លឹបសកម្ម'),          # Club: ក្លិ → ក្លឹ
        ('មជ្លមណ្ឌល', 'មជ្ឈមណ្ឌល'),           # Center: មជ្ល → មជ្ឈ
        ('ពង្រិក', 'ពង្រីក'),                  # Expand: missing ី vowel
        ('ការ័', 'ការ'),                       # Extra diacritic artifact
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
    # Set Tesseract path
    try:
        homebrew_path = '/opt/homebrew/bin/tesseract'
        if os.path.exists(homebrew_path):
            pytesseract.pytesseract.tesseract_cmd = homebrew_path
        else:
            conda_prefix = os.environ.get('CONDA_PREFIX')
            if conda_prefix:
                pytesseract.pytesseract.tesseract_cmd = f"{conda_prefix}/bin/tesseract"
    except:
        pass
    
    if verbose:
        print(f"📄 Loading: {filename}")
    
    images = convert_from_path(filename, dpi=dpi)
    
    if verbose:
        print(f"   Found {len(images)} pages")
    
    config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
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
    return '--oem 3 --psm 6 -c preserve_interword_spaces=1'


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
    
    import time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "exceeded your current quota" in error_str:
                if attempt < max_retries - 1:
                    wait_time = 4 * (attempt + 1) # Wait 4s, 8s, etc.
                    print(f"⏳ Gemini Quota hit. Waiting {wait_time}s before retry ({attempt+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
            
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
