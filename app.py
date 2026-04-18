import os
import json
import time
import uuid
from flask import (
    Flask, render_template, request, jsonify,
    send_file, Response, stream_with_context
)
from werkzeug.utils import secure_filename

# Import the existing OCR pipeline
from ocr_preprocess import (
    preprocess_for_ocr, postprocess_khmer,
    detect_image_quality, correct_with_ai
)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024  # 20MB max
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory store for processing results
results_store = {}

ALLOWED_EXTENSIONS = {'pdf'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Accept PDF upload and save it."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    # Generate unique ID for this upload
    file_id = str(uuid.uuid4())[:8]
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
    file.save(save_path)

    return jsonify({
        'file_id': file_id,
        'filename': filename,
        'size': os.path.getsize(save_path),
        'path': save_path
    })


@app.route('/process', methods=['POST'])
def process_file():
    """Process an uploaded PDF through the OCR pipeline. Returns SSE stream."""
    data = request.json
    file_id = data.get('file_id')
    preset = data.get('preset', 'auto')
    dpi = int(data.get('dpi', 300))
    use_ai = data.get('use_ai', False)

    # Find the uploaded file
    upload_dir = app.config['UPLOAD_FOLDER']
    matching = [f for f in os.listdir(upload_dir) if f.startswith(file_id)]
    if not matching:
        return jsonify({'error': 'File not found'}), 404

    filepath = os.path.join(upload_dir, matching[0])

    def generate():
        """SSE generator for real-time progress."""
        import pytesseract
        from pdf2image import convert_from_path

        # Set Tesseract path (try Homebrew first, then Conda, then system default)
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

        # Step 1: Convert PDF to images
        yield _sse({'step': 'converting', 'message': '📄 Converting PDF to images...'})

        try:
            images = convert_from_path(filepath, dpi=dpi)
        except Exception as e:
            yield _sse({'step': 'error', 'message': f'❌ Failed to convert PDF: {str(e)}'})
            return

        total_pages = len(images)
        yield _sse({
            'step': 'converted',
            'message': f'📄 Found {total_pages} page(s)',
            'total_pages': total_pages
        })

        config = '--oem 3 --psm 6 -c preserve_interword_spaces=1'
        pages_data = []

        # Step 2: Process each page
        for i, img in enumerate(images):
            page_num = i + 1

            # 2a: Quality detection
            import numpy as np
            import cv2
            gray = np.array(img)
            if len(gray.shape) == 3:
                gray = cv2.cvtColor(gray, cv2.COLOR_RGB2GRAY)
            quality = detect_image_quality(gray)

            yield _sse({
                'step': 'preprocessing',
                'message': f'🔧 Page {page_num}/{total_pages}: Preprocessing ({quality["recommended_preset"]} detected)...',
                'page': page_num,
                'quality': quality
            })

            # 2b: Preprocess
            processed = preprocess_for_ocr(img, preset=preset)

            # 2c: OCR
            yield _sse({
                'step': 'ocr',
                'message': f'🔍 Page {page_num}/{total_pages}: Running Tesseract OCR...',
                'page': page_num
            })

            # Save debug image to see what Tesseract is seeing
            debug_path = os.path.join(app.config['UPLOAD_FOLDER'], f"debug_page_{page_num}.png")
            try:
                processed.save(debug_path)
                print(f"🐛 Saved debug image: {debug_path}")
            except Exception as e:
                print(f"⚠️ Failed to save debug image: {e}")

            # [CUSTOM MODEL TOGGLE] 
            # To switch to your newly trained model (once you train it on 5,000+ lines), 
            # uncomment these next two lines and comment out the default raw_text line below!
            
            # custom_config = r'--tessdata-dir "tesstrain/usr/share/tessdata" --oem 3 --psm 1 -c preserve_interword_spaces=1'
            # raw_text = pytesseract.image_to_string(processed, lang='khm_custom+eng', config=custom_config)
            
            raw_text = pytesseract.image_to_string(processed, lang='khm+eng', config=config)

            # 2d: Post-processing
            yield _sse({
                'step': 'postprocess',
                'message': f'✨ Page {page_num}/{total_pages}: Applying Khmer corrections...',
                'page': page_num
            })

            corrected_text = postprocess_khmer(raw_text)

            # Count corrections
            raw_lines = len(raw_text.strip().split('\n'))
            corrected_lines = len(corrected_text.strip().split('\n'))
            lines_removed = raw_lines - corrected_lines

            pages_data.append({
                'page': page_num,
                'text': corrected_text,
                'raw_text': raw_text,
                'quality': quality,
                'lines_removed': max(0, lines_removed),
                'char_count': len(corrected_text)
            })

            yield _sse({
                'step': 'page_done',
                'message': f'✅ Page {page_num}/{total_pages} complete',
                'page': page_num,
                'progress': round((page_num / total_pages) * 100)
            })

        # Step 3: AI correction (optional)
        full_text = '\n'.join([p['text'] for p in pages_data])

        if use_ai:
            yield _sse({
                'step': 'ai_correction',
                'message': '🤖 Applying AI correction (Google Gemini)...'
            })
            try:
                ai_text = correct_with_ai(full_text)
                full_text = ai_text
                yield _sse({
                    'step': 'ai_done',
                    'message': '🤖 AI correction complete!'
                })
            except Exception as e:
                yield _sse({
                    'step': 'ai_error',
                    'message': f'⚠️ AI correction failed: {str(e)}. Using post-processed text.'
                })

        # Store results
        result = {
            'file_id': file_id,
            'filename': matching[0].split('_', 1)[1] if '_' in matching[0] else matching[0],
            'total_pages': total_pages,
            'pages': pages_data,
            'full_text': full_text,
            'preset': preset,
            'dpi': dpi,
            'ai_corrected': use_ai
        }
        results_store[file_id] = result

        yield _sse({
            'step': 'complete',
            'message': f'🎉 All {total_pages} page(s) processed!',
            'result': {
                'file_id': file_id,
                'filename': result['filename'],
                'total_pages': total_pages,
                'full_text': full_text,
                'pages': [{
                    'page': p['page'],
                    'text': p['text'],
                    'quality': p['quality'],
                    'lines_removed': p['lines_removed'],
                    'char_count': p['char_count']
                } for p in pages_data]
            }
        })

        # --- PRIVACY AUTO-DELETE: Remove the PDF file after processing ---
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"🧹 Auto-deleted processed file: {filepath}")
        except Exception as e:
            print(f"⚠️ Failed to auto-delete {filepath}: {e}")

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/download/<file_id>')
def download_result(file_id):
    """Download extracted text as a .txt file and auto-delete it afterwards."""
    from flask import after_this_request
    
    if file_id not in results_store:
        return jsonify({'error': 'No results found for this file'}), 404

    result = results_store[file_id]
    # Write to temp file
    txt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_output.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(result['full_text'])

    download_name = result['filename'].rsplit('.', 1)[0] + '_ocr_output.txt'
    
    @after_this_request
    def remove_file(response):
        try:
            if os.path.exists(txt_path):
                os.remove(txt_path)
                print(f"🧹 Auto-deleted download file: {txt_path}")
        except Exception as e:
            print(f"⚠️ Failed to auto-delete {txt_path}: {e}")
        return response

    return send_file(txt_path, as_attachment=True, download_name=download_name)


@app.route('/documents')
def list_documents():
    """List available PDF documents in the Document/ folder."""
    doc_dir = os.path.join(os.path.dirname(__file__), 'Document')
    if not os.path.exists(doc_dir):
        return jsonify([])

    docs = []
    for f in sorted(os.listdir(doc_dir)):
        if f.lower().endswith('.pdf'):
            path = os.path.join(doc_dir, f)
            docs.append({
                'name': f,
                'size': os.path.getsize(path),
                'path': path
            })
    return jsonify(docs)


@app.route('/process-local', methods=['POST'])
def process_local_file():
    """Process a PDF from the Document/ folder (for quick testing)."""
    data = request.json
    filename = data.get('filename')
    doc_path = os.path.join(os.path.dirname(__file__), 'Document', filename)

    if not os.path.exists(doc_path):
        return jsonify({'error': 'Document not found'}), 404

    # Copy to uploads with an ID
    file_id = str(uuid.uuid4())[:8]
    import shutil
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{file_id}_{filename}")
    shutil.copy2(doc_path, save_path)

    return jsonify({
        'file_id': file_id,
        'filename': filename,
        'size': os.path.getsize(save_path)
    })


def _sse(data):
    """Format data as Server-Sent Event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 50)
    print("  📱 Khmer OCR Web UI")
    print("  🌐 Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000, threaded=True)
