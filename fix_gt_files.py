import glob
import os
import sys

# Import your own custom dictionary rules
sys.path.append('/Users/seangsony/Downloads/Ocr-PP')
from ocr_preprocess import postprocess_khmer

# Find all the Ground Truth text files we just generated
files = glob.glob('/Users/seangsony/Downloads/Ocr-PP/tesstrain/data/khm_custom-ground-truth/*.gt.txt')
fixed = 0

print(f"Checking {len(files)} lines for spelling errors...")

for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        original_text = file.read()
    
    # 1. Apply your custom dictionary rules!
    cleaned_text = postprocess_khmer(original_text)
    
    # 2. Ground truth MUST be a single line, so force remove any newlines
    cleaned_text = cleaned_text.replace('\n', ' ').strip()
    
    # Save the file if we fixed anything
    if cleaned_text != original_text:
        with open(f, 'w', encoding='utf-8') as file:
            file.write(cleaned_text)
        fixed += 1

print(f"✅ Automatically corrected {fixed} files using your custom OCR Python dictionary!")
print("   (You still need to manually check them to be absolutely sure they match the images).")
