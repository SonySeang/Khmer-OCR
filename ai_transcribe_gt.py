import glob
import os
import sys
import time
from PIL import Image

try:
    from google import genai
except ImportError:
    print("Please install google-genai : pip install google-genai")
    sys.exit(1)

# Load API key from .env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip("'\""))

api_key = os.environ.get('GOOGLE_API_KEY')
if not api_key:
    print("ERROR: GOOGLE_API_KEY not found in .env")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# Get all .tif images
tif_files = sorted(glob.glob('/Users/seangsony/Downloads/Ocr-PP/tesstrain/data/khm_custom-ground-truth/*.tif'))

print(f"🤖 Starting Gemini AI Transcription for {len(tif_files)} lines...")

# The prompt for Gemini Vision
PROMPT = """You are a perfect OCR transcriber for Khmer text.
I am providing you an image of a single line of Khmer text.
1. Transcribe the Khmer text perfectly.
2. If there are any stray English words or random symbols that clearly look like garbage, ignore them.
3. Return ONLY the exact Khmer text shown in the image, on a single line, with NO explanation, NO markdown quotes, and NO other words.
"""

success = 0
for i, tif_path in enumerate(tif_files):
    # Determine corresponding txt path
    txt_path = tif_path.replace('.tif', '.gt.txt')
    
    # Check if the image has any dark pixels (sometimes blank lines are generated)
    try:
        img = Image.open(tif_path)
    except Exception as e:
        print(f"Skipping {os.path.basename(tif_path)} (corrupt image)")
        continue
        
    extrema = img.convert("L").getextrema()
    if extrema[0] == extrema[1]:
        # Image is a solid color (likely blank white)
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('')
        print(f"[{i+1}/{len(tif_files)}] Blank line skipped -> {os.path.basename(tif_path)}")
        continue
    
    # Send image to Gemini API
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, PROMPT]
        )
        # Clean the output
        text = response.text.replace('\n', ' ').strip()
        
        # Save to gt.txt
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
            
        print(f"[{i+1}/{len(tif_files)}] AI Transcribed -> {text[:40]}...")
        success += 1
        
        # Small delay to avoid API rate limits
        time.sleep(2)
        
    except Exception as e:
        print(f"[{i+1}/{len(tif_files)}] ❌ API Error on {os.path.basename(tif_path)}: {e}")

print(f"\n✅ Successfully generated perfect ground truth for {success} images using Gemini AI!")
print("You are now ready to run 'gmake training' inside the tesstrain folder!")
