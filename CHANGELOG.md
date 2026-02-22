# Improving Khmer OCR Accuracy Using Image Preprocessing Techniques

## កម្មវិធី Tesseract OCR សម្រាប់អត្ថបទខ្មែរ

---

## 1. Introduction (សេចក្តីផ្តើម)

### 1.1 Project Goal
This project aims to extract Khmer text from PDF documents using **Tesseract OCR** (Optical Character Recognition) and improve the accuracy through **image preprocessing techniques** and **text post-processing**.

### 1.2 Problem Statement
Khmer script (អក្សរខ្មែរ) is one of the most complex writing systems with:
- **74 letters** in the alphabet
- **Stacked consonant clusters** (ជើង) placed below base characters
- **Vowels** that appear above, below, before, or after consonants
- **Thin dependent vowels and diacritics**

These make OCR significantly harder than Latin scripts. Common errors include:
- Misreading similar characters (e.g., `គួ` vs `តួ`)
- Dropping thin vowel marks (e.g., missing `ុ` in `ក្នុង`)
- Confusing punctuation (e.g., `9` instead of `•`)
- Breaking stacked consonant clusters
- Misreading logos and decorations as text

### 1.3 Tools & Libraries

| Library | Purpose |
|---|---|
| Python 3.12 | Programming language |
| Tesseract OCR 5.x | Text recognition engine |
| pytesseract | Python wrapper for Tesseract |
| OpenCV (cv2) | Image preprocessing |
| pdf2image | PDF → image conversion |
| Pillow (PIL) | Image manipulation |

---

## 2. Original Approach (វិធីសាស្ត្រដើម)

### 2.1 Original Pipeline (3 steps)

```
PDF (300 DPI) → Grayscale → Upscale 2x → Adaptive Threshold → Tesseract OCR
```

```python
def clean_image(pil_image):
    img = np.array(pil_image)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                    cv2.THRESH_BINARY, 31, 2)
    return Image.fromarray(binary)
```

### 2.2 Original Results (docx_1.pdf — 5 pages)

| Metric | Result |
|---|---|
| Average Confidence | **77.2%** |
| Suspicious Words (< 60% confidence) | **94** |

---

## 3. Improvement Phase 1: Smart Preprocessing Pipeline

### 3.1 What Changed

Added a **7-stage pipeline** with **auto-detection** that selects the right processing for each document:

```
PDF → Grayscale → Upscale → [Auto-Detect] → Denoise → CLAHE → Binarize → Deskew → Morphology → OCR
```

### 3.2 Auto-Detection System

The system analyzes each page and classifies it:

```python
def detect_image_quality(gray_img):
    noise_level = cv2.Laplacian(gray_img, cv2.CV_64F).var()
    contrast = np.std(gray_img)
    white_ratio = np.mean(gray_img > 200) * 100
```

| Document Type | Detection | Pipeline Applied |
|---|---|---|
| **Clean** (digital PDF) | Low noise, high white | Light: adaptive threshold + deskew |
| **Scan** (scanned paper) | Medium noise | Moderate: denoise + CLAHE + adaptive + deskew + cleanup |
| **Photo** (camera shot) | High noise | Heavy: NLM denoise + CLAHE + Otsu + deskew + cleanup |

### 3.3 New Preprocessing Stages Explained

#### Stage 3: Bilateral Filter (Noise Removal)
```python
denoised = cv2.bilateralFilter(gray, 9, 75, 75)
```
Removes noise while **preserving edges** — critical for thin Khmer character strokes.

#### Stage 4: CLAHE (Contrast Enhancement)
```python
clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
enhanced = clahe.apply(denoised)
```
Divides image into 8×8 tiles and enhances contrast independently. Fixes uneven lighting across the page.

#### Stage 5: Deskew Correction
```python
coords = np.column_stack(np.where(binary > 0))
angle = cv2.minAreaRect(coords)[-1]
```
Detects rotation angle and straightens the image. Even 1-2° rotation significantly degrades Khmer OCR.

#### Stage 6: Improved Binarization
Auto-selects between **Adaptive Threshold** (for clean documents) and **Otsu's Method** (for noisy photos) based on quality detection.

#### Stage 7: Morphological Operations
```python
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)  # Repair broken strokes
cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)   # Remove noise dots
```

### 3.4 Parameter Tuning (13 Configurations Tested)

| # | Configuration | Avg Confidence | Suspicious Words |
|---|---|---|---|
| 1 | Baseline (old) | 79.8% | 15 |
| 2 | Old + denoise | 78.0% | 18 |
| 3 | Old + CLAHE | 77.0% | 21 |
| 4 | Full + Otsu | 75.8% | 21 |
| **5** | **Full + Adaptive** | **80.1%** | **16** |

**Key finding:** Heavy preprocessing hurts clean digital PDFs. The auto-detection routes to lighter processing when appropriate.

### 3.5 Phase 1 Results (docx_1.pdf — 5 pages)

| Metric | Before | After Phase 1 | Change |
|---|---|---|---|
| **Average Confidence** | 77.2% | 78.1% | ✅ +0.9% |
| **Suspicious Words** | 94 | 87 | ✅ −7 (7.4% reduction) |

---

## 4. Improvement Phase 2: Khmer Post-Processing

### 4.1 What Changed

Added a `postprocess_khmer()` function with **4 steps** that clean up OCR output text:

### Step 1: Garbage Line Removal
Automatically removes:
- Standalone page numbers (`2`, `3`, `4` alone on a line)
- Short garbage lines (1-2 random non-Khmer characters)
- English-only garbage lines (no Khmer content, e.g., `CHWS SAH = A On GRO`)

```python
# Remove standalone page numbers
if re.match(r'^\d{1,2}$', stripped):
    continue

# Remove short garbage (not Khmer)
if len(stripped) <= 2 and not re.match(r'^[\u1780-\u17FF]', stripped):
    continue
```

### Step 2: Khmer Character Corrections
Fixes common Tesseract misreadings of Khmer characters:

| OCR Error | Correction | Error Type |
|---|---|---|
| `ក្នង` | `ក្នុង` | Missing vowel `ុ` |
| `កម្ពជា` | `កម្ពុជា` | Missing vowel `ុ` |
| `ដំណេរ` | `ដំណើរ` | Missing vowel `ើ` |
| `ស័ក្សា` | `សិក្សា` | Vowel confusion |
| `ឥំរិយាបថ` | `ឥរិយាបថ` | Extra `ំ` |
| `គួអង្គ` | `តួអង្គ` | Character confusion |
| `គ្រួបង្រៀន` | `គ្រូបង្រៀន` | Character confusion |
| `ឌីជីប៉ល` | `ឌីជីថល` | `ប៉` → `ថ` |
| `ទិសេដា` | `ទិសដៅ` | Misread |
| `ក្លូយៗ` | `កូនៗ` | Wrong word |
| `រំពុក` / `រំពូក` | `រំឭក` | Misread |

### Step 3: Symbol Cleanup
```python
result = re.sub(r'\|', '', result)           # Remove stray pipes
result = re.sub(r'^- =\s', '-  ', result)    # Fix "- =" → "-"
result = re.sub(r'\s/\s', ' ', result)       # Remove stray "/"
result = re.sub(r'^\]\s*$', '', result)       # Remove stray brackets
```

### Step 4: Broken Word Repair
```python
result = re.sub(r'បា\s+ន', 'បាន', result)    # "បា ន" → "បាន"
result = re.sub(r'រួ\s+ម', 'រួម', result)      # "រួ ម" → "រួម"
```

### 4.2 Phase 2 Results (test4.pdf — 4 pages)

**Errors fixed by post-processing:**
| Fix | Count |
|---|---|
| Garbage lines removed (`©`, `YN:`, `CHWS SAH...`) | 5 lines |
| Page numbers removed | 3 lines |
| Khmer character corrections | 10+ fixes |
| Stray symbols cleaned (`/`, `=`, `]`) | 5 fixes |
| Broken words repaired | 2 fixes |
| **Total fixes** | **~25 corrections** |

**Remaining errors (8):** These are garbage text mixed into valid Khmer lines (e.g., `Shavidiunus`, `givows-womo`). These require **AI-based correction** (Google Gemini) which is the next improvement phase.

---

## 5. Architecture (ស្ថាបត្យកម្ម)

```
┌─────────────┐
│  PDF File   │
│ (300 DPI)   │
└──────┬──────┘
       ▼
┌──────────────────────────────────────────┐
│     SMART PREPROCESSING PIPELINE         │
│                                          │
│  Grayscale → Upscale 2x → Auto-Detect   │
│                               │          │
│            ┌──────────────────┤          │
│         [clean]    [scan]   [photo]      │
│            │         │        │          │
│        Adaptive  Bilateral  NLM+         │
│        +Deskew   +CLAHE+    CLAHE+       │
│                  Adaptive+  Otsu+        │
│                  Deskew+    Deskew+       │
│                  Morph      Morph         │
└──────────────────┬───────────────────────┘
                   ▼
          ┌─────────────────┐
          │  Tesseract OCR  │
          │  khm+eng        │
          └────────┬────────┘
                   ▼
          ┌─────────────────┐
          │ Post-Processing │
          │ • Garbage removal│
          │ • Char fixes    │
          │ • Symbol cleanup│
          │ • Word repair   │
          └────────┬────────┘
                   ▼
          ┌─────────────────┐
          │  Clean Output   │
          └─────────────────┘
```

---

## 6. Summary of All Improvements

| Feature | Original | After Improvement |
|---|---|---|
| Preprocessing Steps | 3 (grayscale, upscale, threshold) | 7 (+ denoise, CLAHE, deskew, morphology) |
| Auto-Detection | ❌ None | ✅ Clean/Scan/Photo detection |
| Post-Processing | ❌ None | ✅ 4-step text correction |
| Confidence (docx_1.pdf) | 77.2% | 78.1% |
| Suspicious Words (docx_1.pdf) | 94 | 87 |
| Garbage Line Removal | ❌ | ✅ |
| Khmer Character Fixes | ❌ | ✅ (15+ patterns) |
| Broken Word Repair | ❌ | ✅ |

---

## 7. Limitations & Future Work

### Current Limitations
- Garbage text mixed into valid Khmer lines cannot be auto-removed
- Some Khmer character clusters too complex for Tesseract
- Post-processing patterns are manually defined

### Next Step: AI Correction (Phase 3)
Use **Google Gemini AI** to intelligently fix remaining errors by understanding context — this will handle the 8 remaining errors that post-processing cannot fix.

---

## 8. How to Use

```python
from ocr_preprocess import read_pdf_improved

# Extract text from any PDF
text = read_pdf_improved("Document/test4.pdf")
print(text)
```

---

## 9. File Structure

```
Ocr-PP/
├── Document/              # PDF files for testing
├── allmain.ipynb           # Original notebook (unchanged)
├── main.ipynb             # Original notebook (unchanged)
├── ocr_preprocess.py      # Smart preprocessing module
├── testing-out-put.ipynb  # Test notebook
└── CHANGELOG.md           # This document
```

---

*Project by: [Your Name]*  
*Date: February 2026*  
*Course: [Your Course Name]*
