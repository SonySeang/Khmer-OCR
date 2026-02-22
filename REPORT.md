# 📄 Khmer OCR Project Report
## Extracting Khmer Text from PDF Using Tesseract OCR with Image Preprocessing

---

## 🎯 Objective

Build a system to accurately extract Khmer (ខ្មែរ) text from PDF documents using Tesseract OCR, and improve accuracy through image preprocessing and text post-processing techniques.

---

## ❓ Why Is Khmer OCR Difficult?

| Challenge | Example |
|---|---|
| Stacked consonants (ជើង) | ក្រ = ក + ្រ (stacked below) |
| Vowels in 4 positions | Above: កី, Below: កុ, Before: កេ, After: កា |
| Thin diacritics | ំ ះ ៈ are very small marks |
| Similar-looking characters | គ vs ត, រ vs វ |
| Complex clusters | សេចក្តី = 5 components combined |

**Result:** Tesseract makes many mistakes that don't occur with English text.

---

## 🔄 What We Built: 3-Phase Improvement

### Phase 0: Original (Before)

**Pipeline:** `PDF → Grayscale → 2x Upscale → Adaptive Threshold → OCR`

Only 3 preprocessing steps. No error correction.

**Result on docx_1.pdf (5 pages):**
- Average confidence: **77.2%**
- Suspicious words: **94**

---

### Phase 1: Smart Image Preprocessing

**What we added:**

| # | Stage | Technique | Purpose |
|---|---|---|---|
| 1 | Grayscale | `cv2.cvtColor` | Simplify image to 1 channel |
| 2 | Upscale | `cv2.resize` (2x) | Make text bigger for OCR |
| 3 | **Denoise** | `cv2.bilateralFilter` | Remove noise, keep edges sharp |
| 4 | **Contrast** | CLAHE | Fix uneven lighting |
| 5 | **Binarize** | Adaptive or Otsu (auto) | Convert to black & white |
| 6 | **Deskew** | `cv2.minAreaRect` | Fix page rotation |
| 7 | **Morphology** | Close + Open | Repair broken strokes |

**Key innovation — Auto-Detection:**
```python
def detect_image_quality(gray_img):
    noise = cv2.Laplacian(gray_img, cv2.CV_64F).var()
    contrast = np.std(gray_img)
    white = np.mean(gray_img > 200) * 100
```

| If detected as... | Pipeline applied |
|---|---|
| Clean (digital PDF) | Light: threshold + deskew only |
| Scan (scanned paper) | Moderate: denoise + CLAHE + threshold + deskew + morph |
| Photo (camera shot) | Heavy: strong denoise + CLAHE + Otsu + deskew + morph |

**Result on docx_1.pdf (5 pages):**
- Average confidence: **77.2% → 78.1%** ✅ (+0.9%)
- Suspicious words: **94 → 87** ✅ (−7)

---

### Phase 2: Khmer Text Post-Processing

**What we added — 4 automatic cleanup steps after OCR:**

**Step 1 — Remove Garbage Lines:**
```python
# Page numbers: "2", "3", "4" alone on a line → removed
# Short garbage: random 1-2 characters → removed  
# English garbage: "CHWS SAH = A On GRO" → removed
```

**Step 2 — Fix Khmer Character Errors:**

| ❌ OCR Output | ✅ Corrected | Error |
|---|---|---|
| `ក្នង` | `ក្នុង` | Missing `ុ` |
| `កម្ពជា` | `កម្ពុជា` | Missing `ុ` |
| `ដំណេរ` | `ដំណើរ` | Missing `ើ` |
| `គួអង្គ` | `តួអង្គ` | `គួ` → `តួ` |
| `គ្រួបង្រៀន` | `គ្រូបង្រៀន` | `គ្រួ` → `គ្រូ` |
| `ឌីជីប៉ល` | `ឌីជីថល` | `ប៉` → `ថ` |
| `ទិសេដា` | `ទិសដៅ` | Misread |
| `ស័ក្សា` | `សិក្សា` | Vowel confusion |

**Step 3 — Clean Symbols:**
```python
"|" → removed          # Stray pipes
"- =" → "-"            # Stray equals
" / " → " "            # Stray slashes
"]" → removed          # Stray brackets
```

**Step 4 — Fix Broken Words:**
```python
"ដែលបា ន" → "ដែលបាន"   # Space in middle of word
```

**Result on test4.pdf (4 pages):** ~25 errors fixed automatically

---

## 📊 Final Results Summary

| Metric | Before | After | Improvement |
|---|---|---|---|
| Preprocessing stages | 3 | 7 | +4 new stages |
| Auto-detection | ❌ | ✅ | Clean/Scan/Photo |
| Post-processing | ❌ | ✅ | 4-step text cleanup |
| Avg confidence (docx_1.pdf) | 77.2% | 78.1% | **+0.9%** |
| Suspicious words (docx_1.pdf) | 94 | 87 | **−7.4%** |
| Post-processing fixes (docx_1.pdf) | 0 | 173 | **173 lines fixed** |
| Garbage lines auto-removed | 0 | ~8 | ✅ |
| Khmer character corrections | 0 | 15+ patterns | ✅ |

---

## 📐 System Architecture

```
         ┌──────────┐
         │ PDF File │
         └────┬─────┘
              │ 300 DPI
              ▼
    ┌───────────────────┐
    │   pdf2image        │
    │   (page → image)   │
    └────────┬──────────┘
             ▼
    ┌───────────────────────────┐
    │  SMART PREPROCESSING      │
    │                           │
    │  Grayscale → Upscale 2x   │
    │         │                 │
    │    Auto-Detect Quality    │
    │    ┌────┼────┐            │
    │  clean scan photo         │
    │    │    │    │            │
    │  light moderate heavy     │
    └────────┬──────────────────┘
             ▼
    ┌───────────────────┐
    │   Tesseract OCR   │
    │   lang: khm+eng   │
    │   oem 3, psm 6    │
    └────────┬──────────┘
             ▼
    ┌───────────────────┐
    │  POST-PROCESSING  │
    │  1. Garbage removal│
    │  2. Char fixes    │
    │  3. Symbol cleanup│
    │  4. Word repair   │
    └────────┬──────────┘
             ▼
    ┌───────────────────┐
    │   Clean Text ✅   │
    └───────────────────┘
```

---

## ⚠️ Current Limitations

| Limitation | Cause | Solution |
|---|---|---|
| Logo/header text garbage | Decorations misread as text | AI correction (Phase 3) |
| Complex Khmer clusters | Tesseract model limitation | Custom training data |
| English mixed into Khmer lines | Cannot remove without breaking line | AI correction (Phase 3) |

---

## 🚀 Next Step: Phase 3 — AI Correction

Use **Google Gemini AI** to intelligently fix remaining errors that pattern-based post-processing cannot handle. The AI understands Khmer language context and can fix garbage like `Shavidiunus` → correct Khmer word.

---

## 💻 Usage

```python
from ocr_preprocess import read_pdf_improved

text = read_pdf_improved("Document/test4.pdf")
print(text)
```

---

*Project by: [Your Name]*  
*Date: February 2026*  
*Course: [Your Course Name]*
