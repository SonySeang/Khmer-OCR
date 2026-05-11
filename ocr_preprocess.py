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
        return cv2.bilateralFilter(gray, 5, 75, 75)  # d=5 not 9: 3x faster on large images
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

    # Skip upscaling if the image is already high-res (300 DPI PDF pages are ~2500x3500px).
    # Upscaling large images makes bilateral filter take 30-60s; 300 DPI is already optimal for Tesseract.
    h0, w0 = gray.shape[:2]
    if h0 * w0 > 2_000_000:
        upscale_factor = 1

    # Upscale
    if upscale_factor > 1:
        if verbose: print(f"   ↳ Upscaling {upscale_factor}x...")
        gray = cv2.resize(gray, None, fx=upscale_factor, fy=upscale_factor,
                         interpolation=cv2.INTER_CUBIC)

    # Apply preset-specific pipeline
    if preset == "clean":
        # sharpen → otsu → deskew: empirically best for clean digital PDFs.
        # Bilateral + adaptive over-processes crisp text and hurts thin Khmer strokes.
        if verbose: print("   ↳ Pipeline: sharpen → otsu → deskew")
        sharpened = sharpen(gray)
        binary = binarize(sharpened, method="otsu")
        binary = deskew(binary)

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
        # Use bilateral instead of NLM — NLM on large upscaled images hangs for minutes.
        if verbose: print("   ↳ Pipeline: heavy denoise → gamma → CLAHE → sharpen → otsu → deskew → cleanup")
        denoised = remove_noise(gray, method="bilateral")
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

    # ---- STEP 0: Form blank-field cleanup ----
    # Forms use dotted/dashed lines for fill-in blanks (e.g. "...............", "-..-..--..").
    # Tesseract reads these as literal dots and dashes. Replace with a clean placeholder.

    # Strip special chars that OCR picks up from form decorations
    text = re.sub(r'[‹›«»©®™°•·]', '', text)

    # 5+ consecutive dots → blank marker
    text = re.sub(r'\.{5,}', '________', text)
    # 5+ consecutive dashes → blank marker
    text = re.sub(r'-{5,}', '________', text)

    # Mixed dot/dash/space sequences (e.g. "- - -- - .", "-..-..-..-..") → blank marker
    # Check ratio on non-space chars so spaced-out dashes ("- - - -- -") are caught too.
    def _form_blank(m):
        s = m.group()
        non_space = s.replace(' ', '').replace('\t', '')
        if not non_space:
            return s
        dot_dash = non_space.count('.') + non_space.count('-')
        if dot_dash >= 4 and dot_dash / len(non_space) >= 0.85:
            return '________'
        return s
    text = re.sub(r'[-. ]{8,}', _form_blank, text)

    # Second pass: stray dot/dash runs directly adjacent to blank markers
    # NOTE: avoid (group){n,} patterns — they cause catastrophic backtracking on form-heavy pages
    text = re.sub(r'(?<![ក-អ\w])[-.\s]+(?=________)', '________ ', text)
    text = re.sub(r'(?<=________)[\s.-]+(?![ក-អ\w])', ' ________', text)
    # Markers separated only by dots/dashes (no Khmer between them)
    text = re.sub(r'________[-. ]+________', '________ ', text)
    # Now collapse any consecutive blank markers (including after above fixes)
    text = re.sub(r'(________\s*){2,}', '________ ', text)
    # Clean orphan dash/dots immediately after a blank marker (before Khmer or end of line)
    text = re.sub(r'(?<=________)\s*[-\.]{1,4}\s*(?=[ក-៿])', ' ', text)
    text = re.sub(r'________\s*[-\.]{1,4}\s*$', '________', text, flags=re.MULTILINE)

    # Remove short Latin noise tokens that appear between blank markers and Khmer text
    # e.g. "________ esse  i កើត" → "________ កើត"
    # e.g. "________ SS a________" → "________ ________"
    text = re.sub(
        r'(?<=________)\s+(?:[a-zA-Z]{1,8}\s*){1,4}(?=[ក-៿]|________)',
        ' ', text
    )

    # Drop lines that are nothing but blank markers + whitespace → keep as single marker
    lines_out = []
    for ln in text.split('\n'):
        if re.fullmatch(r'[\s________]+', ln.strip()) and '________' in ln:
            lines_out.append('________')
        else:
            lines_out.append(ln)
    text = '\n'.join(lines_out)

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
        
        # Remove very short lines (1-2 chars) including lone Khmer letters (header artifacts)
        if len(stripped) <= 2 and stripped not in ('', '•'):
            continue
            
        # Remove footer lines: email addresses, URLs, phone numbers
        if re.search(r'[\w\.\-]+@[\w\.\-]+\.\w{2,}', stripped):
            continue
        if re.search(r'\bwww\.\w+\.\w+', stripped, re.I):
            continue
        # Phone number lines: colon + digit clusters (e.g. ": ៨៥៥ ២) ២២០ ...")
        if re.search(r':\s*[\d៨៥៤៣២១០\(\)\s]{10,}', stripped) and stripped.count(':') >= 2:
            continue

        # Count Khmer characters vs Total characters
        khmer_chars = len(re.findall(r'[\u1780-\u17FF]', stripped))
        total_chars = len(stripped)
        
        # Remove lines that are mostly English garbage or symbols (common with graphs/noise)
        if total_chars > 0:
            khmer_ratio = khmer_chars / total_chars
            known_english = ['MSME', 'ChatGPT', 'Gemini', 'Claude', 'Copilot', 'JOTA',
                             'EdTech', 'AI', 'Al', 'IFC', 'NBC', 'CMA', 'STEM', 'KAPE',
                             'Centre', 'Excellence', 'Designer', 'Media', 'MFI', 'NGO',
                             'ASEAN', 'UNESCO', 'UNICEF', 'ADB', 'IMF', 'GDP']
            is_page_marker  = stripped.startswith('--- Page')
            is_known_eng    = any(eng in stripped for eng in known_english)
            is_form_blank   = '________' in stripped

            # If line has NO Khmer characters at all → drop unless it's a known marker
            if khmer_chars == 0:
                if not is_known_eng and not is_page_marker and not is_form_blank and not re.match(r'^[0-9\s\.\,\-\%]+$', stripped):
                    continue

            # If line is longer than 5 chars and has less than 15% Khmer → likely noise
            elif total_chars > 5 and khmer_ratio < 0.15:
                if not is_known_eng and not is_page_marker and not is_form_blank:
                    continue

            # Lines with a long ALL-CAPS run → stamp/logo garbage
            elif re.search(r'[A-Z]{6,}', stripped) and khmer_ratio < 0.35:
                if not is_known_eng and not is_page_marker:
                    continue

            # Lines with 2+ separate ALL-CAPS words (e.g. "CRBS SHAE ក កក") → graphic noise
            allcaps_words = re.findall(r'\b[A-Z]{3,}\b', stripped)
            if len(allcaps_words) >= 2 and khmer_ratio < 0.30:
                if not is_known_eng and not is_page_marker:
                    continue

            # Lines where Latin letters dominate (>70%) and Khmer is sparse (<20%)
            # → random noise row (e.g. "snstmnaimado sunt ynesinge ភ្នំពេញ")
            latin_chars = len(re.findall(r'[a-zA-Z]', stripped))
            if total_chars > 8 and latin_chars / total_chars > 0.70 and khmer_ratio < 0.20:
                if not is_known_eng and not is_page_marker:
                    continue
        
        cleaned_lines.append(line)
    
    result = '\n'.join(cleaned_lines)
    
    # ---- STEP 1.5: Remove specific English garbage strings from mixed lines ----
    # (Often caused by Tesseract misreading logos or sidebar OSD text)
    result = re.sub(r'ANEANitniimia\s*', '', result)
    result = re.sub(r'1 IN Sits inns', '', result)
    result = re.sub(r'1 ដូចនេះ', 'ដូចនេះ', result)

    # Remove long runs of ALL-CAPS garbage embedded inside valid lines
    # e.g. "ការណ៍ HSAISESMSMS AULHAIM ក្រសួង" → "ការណ៍ ក្រសួង"
    result = re.sub(r'\b[A-Z]{4,}(?:\s+[A-Z]{2,}){2,}\b', '', result)

    # Remove long lowercase Latin garbage runs inside valid Khmer lines
    # e.g. "snstmnaimado sunt ynesinge ភ្នំពេញ" → "ភ្នំពេញ"
    result = re.sub(r'\b[a-z]{4,}(?:\s+[a-z]{3,}){2,}\b', '', result)

    # Remove inline bracket noise with only Latin/digits inside
    result = re.sub(r'\[[A-Za-z0-9\s\.\-]{4,}\]', '', result)

    # Remove isolated English garbage tokens commonly seen in Khmer government PDFs
    # (logos, stamps, page decorations misread as text)
    for token in [r'SOHAP', r'\(HOWE\)', r'\bWw\b', r'\bchara\b',
                  r'\bSuny\b', r'\bBI\b', r'\bAS\b',
                  r'\bShahn\b', r'\bgrag\b', r'\bgiant\b', r'\bBrim\b',
                  r'\bberi\b', r'\beae\b', r'\bNeha\b']:
        result = re.sub(r'\s*' + token + r'\s*', ' ', result)

    # Remove isolated English words (4–9 chars) sandwiched between Khmer characters
    # e.g. "សីលធម៌ Shahn វិជ្ជាជីវៈ" → "សីលធម៌ វិជ្ជាជីវៈ"
    # Safe: only fires when Khmer is on both sides
    result = re.sub(
        r'(?<=[\u1780-\u17FF])\s+(?!(?:Designer|Media|Centre|Excellence|ChatGPT|Gemini|AI|EdTech|JOTA|STEM|KAPE|ASEAN|UNESCO|UNICEF))[A-Z][a-z]{3,8}\s+(?=[\u1780-\u17FF])',
        ' ', result
    )

    # Strip leading short Latin/digit noise before Khmer content on same line
    # e.g. "EM. ការ..." → "ការ...",  "7 a  ជាតិ" → "ជាតិ"
    result = re.sub(r'^[A-Za-z0-9]{1,4}[\.\s]*(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)
    # Catch patterns like "7 a  ជាតិ" — digit + whitespace + short latin + whitespace before Khmer
    result = re.sub(r'^\d{1,2}\s+[A-Za-z]{1,3}\s+(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)
    # Also handle bare digit(s) + whitespace before Khmer
    result = re.sub(r'^\d{1,2}\s+(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)
    # Strip single stray Khmer char + dot pattern at line start (e.g. "យ .  ព" → "ព")
    result = re.sub(r'^[\u1780-\u17FF]\s+\.\s+(?=[\u1780-\u17FF])', '', result, flags=re.MULTILINE)
    # Strip leading Khmer vowel that can't start a word (OCR split line artifact)
    result = re.sub(r'^[ាិីឹឺុូួើឿៀែៃោៅ]\s*', '', result, flags=re.MULTILINE)

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

        # Khmer numeral misread as Latin letter in numbered lists
        ('G-Copy', '៤-Copy'),
        ('C-Copy', '៥-Copy'),
        ('G-copy', '៤-Copy'),
        ('C-copy', '៥-Copy'),

        # Scholarship form corrections
        ('សូមេគារពជូន', 'សូមគោរពជូន'),          # Greeting phrase
        ('ពាក្យេស្លីសុំ', 'ពាក្យសុំ'),           # Form title
        ('ក្សត្រត្រ', 'ក្សត្រ'),                  # Extra ត្រ at end of royal title
        ('ម្រិតវំប្បធម៌', 'វប្បធម៌'),            # Education level
        ('ជ្នៅ', 'នៅ'),                           # Location preposition
        ('ឃំ-', 'ឃុំ-'),                          # Village (commune)
        ('ស្រកា"', 'ស្រុក/'),                     # District
        ('ខណ្ឌ', 'ខណ្ឌ'),                         # Already correct
        ('ខេត្ត"', 'ខេត្ត/'),                     # Province
        ('ក្រុង់', 'ក្រុង'),                      # City: stray ់

        # Official document header corrections (seen in government PDFs)
        ('ព្រះរាជាណាចក្រកម្មជា', 'ព្រះរាជាណាចក្រកម្ពុជា'),  # Cambodia: ម្ម → ម្ព
        ('ពាះរាជាណាបក្រ', 'ព្រះរាជាណាចក្រ'),  # Full header phrase fix
        ('ពាះរាជាណា', 'ព្រះរាជាណា'),           # Partial: ពាះ → ព្រះ
        ('ណាបក្រ', 'ណាចក្រ'),                  # ចក្រ misread as បក្រ
        ('ម្ព្ហ', 'ម្ពុ'),                      # in កម្ពុជា
        ('ប្រូក្សា', 'ប្រឹក្សា'),              # Council: ប្រូ → ប្រឹ
        ('ក្លិបសកម្ម', 'ក្លឹបសកម្ម'),          # Club: ក្លិ → ក្លឹ
        ('មជ្លមណ្ឌល', 'មជ្ឈមណ្ឌល'),           # Center: មជ្ល → មជ្ឈ
        ('ពង្រិក', 'ពង្រីក'),                  # Expand: missing ី vowel
        ('ការ័', 'ការ'),                       # Extra diacritic artifact

        # ---- Vowel missing / wrong diacritic (very common OCR errors) ----
        ('ព្រាះរាជ', 'ព្រះរាជ'),               # ព្រះ with extra ា vowel
        ('ព្រារាជ',  'ព្រះរាជ'),               # variant
        ('ផ្លវ',    'ផ្លូវ'),                   # road: missing ូ
        ('ចក្ខវ',   'ចក្ខុវ'),                  # vision: missing ុ (ចក្ខុវិស័យ)
        ('ចក្ខិ',   'ចក្ខុ'),                   # vowel variant
        ('ខ្ញំ',    'ខ្ញុំ'),                   # I/me: missing ុ
        ('យុវជំន',  'យុវជន'),                  # youth: extra ំ
        ('បច្ខុ',   'បច្ចុ'),                   # present: ខ → ច (បច្ចុប្បន្ន)
        ('ដណាក់',  'ដំណាក់'),                  # stage: missing ំ
        ('ឥរិយាបថ័','ឥរិយាបថ'),                # behavior: stray ័

        # ---- Wrong consonant / wrong character ----
        ('ពិបារណា', 'ពិចារណា'),               # consider: ប → ច
        ('សម្រួច',  'សម្រេច'),                # achieve/accomplish: ួ → េ
        ('បណ្តះ',   'បណ្តុះ'),                # cultivate: missing ុ
        ('ជំនាញ្ញ', 'ជំនាញ'),                 # skill: extra ្ញ

        # Education / government document specific
        ('ត្រសួង', 'ក្រសួង'),                  # ក្រ misread as ត្រ at line start
        ('ម៉ូដែល', 'ម៉ូដែល'),                  # Already correct, keep
        ('ឌីជីប៉ល', 'ឌីជីថល'),               # Digital: ប៉ → ថ
        ('ឌីជីវល', 'ឌីជីថល'),                # Digital variant
        ('សតវត្សរ៍', 'សតវត្សរ៍'),             # Already correct
        ('បំណេះ', 'បំណិន'),                    # Skill: េះ → ិន
        ('សហគ្រិន', 'សហគ្រិន'),               # Entrepreneurship (correct)
        ('ពិព័រណ', 'ពិព័រណ៍'),                # Exhibition: missing ៍
        ('ពិព័រណ៏', 'ពិព័រណ៍'),               # Exhibition: wrong diacritic
        ('ចរិយាធម', 'ចរិយាធម៌'),              # Morality: missing ៌
        ('សីលធម', 'សីលធម៌'),                  # Ethics: missing ៌
        ('ព្រះមហាក្ស', 'ព្រះមហាក្សត្រ'),       # King title truncated
        ('ជំនា\nន់', 'ជំនាន់'),               # Page-break artifact in keyword
        ('ជំនានំ', 'ជំនាន់'),                  # Wrong diacritic
        ('ម៉ូ\nដែល', 'ម៉ូដែល'),               # Page-break artifact
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
    
    # ---- STEP 4: Fix Khmer period and punctuation misreads ----
    # Latin "4" at line end after Khmer text = Khmer period ។
    # (Tesseract cannot distinguish ។ from 4 in many fonts)
    result = re.sub(r'(?<=[\u1780-\u17FF\s]) 4\s*$', '។', result, flags=re.MULTILINE)
    result = re.sub(r'(?<=[\u1780-\u17FF])4\s*$',    '។', result, flags=re.MULTILINE)

    # "!" at line end after Khmer = ។
    result = re.sub(r'(?<=[\u1780-\u17FF])\s*!\s*$', '។', result, flags=re.MULTILINE)

    # Remove trailing "  ." or " ." at end of any line (border/ruler artifact)
    # Khmer documents use ។ not "." so a trailing space+dot is always noise
    result = re.sub(r'\s+\.\s*$', '', result, flags=re.MULTILINE)

    # "4" mid-sentence sandwiched between Khmer = ។ (e.g. "...ជន 4 ការ...")
    result = re.sub(r'(?<=[\u1780-\u17FF]) 4 (?=[\u1780-\u17FF])', '។ ', result)

    # ---- STEP 4.5: Common numeral OCR confusions ----
    # ២១ (21) is misread as "wo" — seen in "សតវត្សរ៍ទី wo" (21st century)
    result = re.sub(r'(?<=ទី\s)wo\b', '២១', result)
    result = re.sub(r'\bwo\b(?=\s*[\u1780-\u17FF])', '២១', result)

    # "7" before Khmer digits = often misread Khmer numeral (remove stray 7)
    result = re.sub(r'\b7(?=[\u17E0-\u17E9])', '', result)

    # ---- STEP 5: Fix broken words (space in middle) ----
    result = re.sub(r'បា\s+ន', 'បាន', result)
    result = re.sub(r'រួ\s+ម', 'រួម', result)

    # Remove empty lines left by cleanup (keep max 2 consecutive)
    result = re.sub(r'\n{4,}', '\n\n\n', result)
    
    return result


def run_ocr(processed_pil_image):
    """Run Tesseract OCR on a preprocessed PIL image. Returns raw text."""
    import pytesseract, os
    try:
        homebrew_path = '/opt/homebrew/bin/tesseract'
        if os.path.exists(homebrew_path):
            pytesseract.pytesseract.tesseract_cmd = homebrew_path
        else:
            conda_prefix = os.environ.get('CONDA_PREFIX')
            if conda_prefix:
                pytesseract.pytesseract.tesseract_cmd = f"{conda_prefix}/bin/tesseract"
    except Exception:
        pass
    config = '--oem 1 --psm 4 -c preserve_interword_spaces=1 -c textord_min_linesize=1.5'
    return pytesseract.image_to_string(processed_pil_image, lang='khm+eng', config=config)


# ============================================================
# FULL PDF READER: Replaces your read_pdf_file function
# ============================================================
def read_pdf_improved(filename, dpi=300, preset="auto", apply_postprocess=True, verbose=True):
    """Run the full OCR pipeline on a PDF file. Returns extracted text."""
    from pdf2image import convert_from_path

    if verbose:
        print(f"📄 Loading: {filename}")

    images = convert_from_path(filename, dpi=dpi)

    if verbose:
        print(f"   Found {len(images)} pages")

    extracted_text = ""
    for i, img in enumerate(images):
        if verbose:
            print(f"\n📸 Processing Page {i+1}/{len(images)}...")
        processed = preprocess_for_ocr(img, preset=preset, verbose=verbose)
        text = run_ocr(processed)
        if apply_postprocess:
            text = postprocess_khmer(text)
        extracted_text += f"--- Page {i+1} ---\n{text}\n"

    if verbose:
        print(f"\n✅ Extraction complete!")
    return extracted_text


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
