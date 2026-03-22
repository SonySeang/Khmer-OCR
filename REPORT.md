# 📄 Khmer OCR Project Report
## Extracting Khmer Text from PDF Using Tesseract OCR

---

## 🎯 Objective
Build an advanced machine learning system to accurately extract Khmer (ខ្មែរ) text from PDF documents using Tesseract OCR, and radically improve accuracy through image layout preprocessing, algorithmic parameter fine-tuning, and post-processing dictionaries.

---

## ❓ Why Is Khmer OCR Difficult?

| Challenge | Example |
|---|---|
| Stacked consonants (ជើង) | ក្រ = ក + ្រ (stacked below) |
| Vowels in 4 positions | Above: កី, Below: កុ, Before: កេ, After: កា |
| Thin diacritics | ំ ះ ៈ are very small marks |
| Similar-looking characters | គ vs ត, រ vs វ |
| Complex clusters | សេចក្តី = 5 components combined |

**Result:** Generic baseline OCR models hallucinate characters or fail to map visual boundaries accurately.

---

## 🔄 What We Built: 4-Phase Architecture

### Phase 1: Smart Image Preprocessing
Before OCR reads a document, the image quality must be mathematically maximized for Tesseract.

| # | Stage | Technique | Purpose |
|---|---|---|---|
| 1 | Grayscale | `cv2.cvtColor` | Simplify image to 1 channel |
| 2 | Upscale | `cv2.resize` (2x) | Make text bigger for OCR |
| 3 | **Denoise** | `cv2.bilateralFilter` | Remove noise, keep edges sharp |
| 4 | **Contrast** | CLAHE | Fix uneven lighting |
| 5 | **Binarize** | Adaptive or Otsu (auto) | Convert to black & white |

### Phase 2: Algorithmic Fine-Tuning & Automated Dictionaries
We fine-tuned the application pipeline by building automatic cleanup steps to mathematically trap and fix recurring OCR hallucinations.

| ❌ OCR Output | ✅ Corrected | Error Type |
|---|---|---|
| `ក្នង` | `ក្នុង` | Missing `ុ` |
| `កម្ពជា` | `កម្ពុជា` | Missing `ុ` |
| `ដំណេរ` | `ដំណើរ` | Missing `ើ` |
| `គួអង្គ` | `តួអង្គ` | `គួ` → `តួ` |
| `គ្រួបង្រៀន` | `គ្រូបង្រៀន` | `គ្រួ` → `គ្រូ` |

---

### Phase 3: Advanced Layout Analysis & Cropping
By analyzing real-world PDF extraction, we determined that signature stamps, background logos, and page footers were causing Tesseract to hallucinate "Garbage Character Blocks."

**Solution:**
A custom OpenCV Python script (`crop_to_main_text_body`) that binarizes the image, detects structural contours, and strategically draws mathematical bounding boxes strictly around text-only paragraphs. This safely strips away unreadable visual noise at the edges of documents *before* OCR processing begins.

---

### Phase 4: Scientific Accuracy Measurement
To prove that our pipeline fine-tuning was successful, we transitioned from basic "confidence scores" to legitimate scientific language evaluation metrics.

**Implementation (`evaluate_metrics.py`):**
- Integrated `jiwer`, the industry standard package for NLP evaluation.
- Evaluated **CER (Character Error Rate)**: Measures exactly how many individual letters were missed, added, or substituted.
- Evaluated **WER (Word Error Rate)**: Measures how many full words were incorrectly captured.
*This allows the system's fine-tuned parameters to be mathematically scored against a human-typed "Ground Truth."*

---

## 🚀 Next Steps
We will integrate a large language model (like the Gemini API) as a final post-processing step. While algorithmic dictionaries fix common spelling errors, an AI can contextually read the entire Khmer sentence and fix complex grammatical issues that Tesseract misses.

---

## 💻 System Usage

```bash
# Start the primary Flask User Interface:
python app.py

# Evaluate OCR metrics mathematically:
python evaluate_metrics.py test.gt.txt output.txt
```
