import cv2
import numpy as np
from PIL import Image
import os
import pytesseract
from pdf2image import convert_from_path

def generate_ground_truth_from_pdf(pdf_path, output_dir="tesstrain/data/khm_custom-ground-truth", dpi=300):
    """
    Slices a PDF into single line images (.tif) for Tesseract fine-tuning.
    Also creates a "best guess" text file (.gt.txt) using your current OCR.
    """
    os.makedirs(output_dir, exist_ok=True)
    images = convert_from_path(pdf_path, dpi=dpi)
    
    line_idx = 0
    print(f"Extracting lines from {pdf_path} into {output_dir}...")
    
    for page_num, img in enumerate(images):
        # Convert to OpenCV format
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        
        # Binarize
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Dilate horizontally to merge characters into words/lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (100, 5))
        dilated = cv2.dilate(binary, kernel, iterations=1)
        
        # Find contours (which should now be lines)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Sort contours top-to-bottom
        boundingBoxes = [cv2.boundingRect(c) for c in contours]
        if not boundingBoxes:
            continue
            
        (contours, boundingBoxes) = zip(*sorted(zip(contours, boundingBoxes),
                                                key=lambda b:b[1][1]))
        
        for (x, y, w, h) in boundingBoxes:
            # Skip very small noise
            if w < 50 or h < 15:
                continue
                
            # Add padding
            pad = 10
            min_y = max(0, y - pad)
            max_y = min(cv_img.shape[0], y + h + pad)
            min_x = max(0, x - pad)
            max_x = min(cv_img.shape[1], x + w + pad)
            
            line_crop = cv_img[min_y:max_y, min_x:max_x]
            
            # Save TIF image
            base_name = f"khm_{page_num+1}_{line_idx:04d}"
            tif_path = os.path.join(output_dir, f"{base_name}.tif")
            txt_path = os.path.join(output_dir, f"{base_name}.gt.txt")
            
            cv2.imwrite(tif_path, line_crop)
            
            # Use current OCR as a baseline transcription to save time
            config = '--oem 3 --psm 7' # PSM 7 = single text line
            baseline_text = pytesseract.image_to_string(line_crop, lang='khm', config=config).strip()
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(baseline_text)
                
            line_idx += 1
            
    print(f"✅ Generated {line_idx} training line pairs in {output_dir}!")
    print("\nNext Steps:")
    print("1. Open the .gt.txt files and MANUALLY FIX the transcriptions.")
    print("2. Once they are 100% correct, run 'gmake training' again.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generate_ground_truth.py Document/your_file.pdf")
    else:
        generate_ground_truth_from_pdf(sys.argv[1])
