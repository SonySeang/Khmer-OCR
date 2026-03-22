import pytesseract
from PIL import Image
import os

# Select an image that was in the training set
test_image = "tesstrain/data/khm_custom-ground-truth/khm_0009_08.tif"
test_text = "tesstrain/data/khm_custom-ground-truth/khm_0009_08.gt.txt"

print(f"🖼️  Testing OCR Models on Image: {os.path.basename(test_image)}\n")

if not os.path.exists(test_image):
    print("Error: Could not find the testing image.")
else:
    img = Image.open(test_image)
    
    # 1. Official Ground Truth (what the text ACTUALLY is)
    with open(test_text, 'r', encoding='utf-8') as f:
        truth = f.read().strip()
    print("✅ PERFECT HUMAN TEXT (Ground Truth):")
    print(f"   {truth}\n")

    # 2. Base Model (Before Training)
    base_config = '--oem 3 --psm 13 -c preserve_interword_spaces=1'
    base_text = pytesseract.image_to_string(img, lang='khm', config=base_config).strip()
    print("❌ BASE MODEL (Before Training):")
    print(f"   {base_text}\n")

    # 3. Custom Model (After Training)
    custom_dir = os.path.abspath("tesstrain/usr/share/tessdata")
    custom_config = f'--tessdata-dir "{custom_dir}" --oem 3 --psm 13 -c preserve_interword_spaces=1'
    try:
        custom_text = pytesseract.image_to_string(img, lang='khm_custom', config=custom_config).strip()
        print("🚀 NEW CUSTOM MODEL (After Training):")
        print(f"   {custom_text}\n")
    except Exception as e:
        print(f"Error loading custom model: {e}")
        
    print("-" * 50)
    print("Did the custom model fix any OCR spelling errors that the base model made?")
