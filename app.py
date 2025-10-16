from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from werkzeug.utils import secure_filename
import PyPDF2
import os
import uuid
from dotenv import load_dotenv

# Import helper modules
from python.translate import translate_text  # ✅ Now supports hybrid mode
from python.tts import text_to_speech_with_voice
from python.summarize import summarize_text

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Serve images
@app.route('/images/<filename>')
def images(filename):
    """Serve files from the 'images' folder in project root"""
    return send_from_directory('images', filename)

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

# Text-to-Speech
@app.route('/text-to-speech', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        text = data.get('text', '')[:5000]
        lang = data.get('lang', 'en')
        voice_type = data.get('voice_type', 'female')
        
        print(f"🎤 TTS Request - Lang: {lang}, Voice: {voice_type}, Text length: {len(text)}")
        
        audio_file = text_to_speech_with_voice(text, voice_type=voice_type, speed=1.0, lang=lang)
        return send_file(audio_file, mimetype='audio/mpeg')
    except Exception as e:
        print(f"❌ TTS error: {e}")
        return jsonify({'error': str(e)}), 500

# HYBRID TRANSLATION using translate.py module
@app.route('/translate', methods=['POST'])
def translate():
    """
    Hybrid translation endpoint:
    - mode='gemini': High-quality AI translation (for selected text)
    - mode='fast': Quick Google Translate (for full PDF)
    """
    try:
        data = request.json
        text = data.get('text', '')
        
        # Get target language (try multiple parameter names)
        target_lang = data.get('target_lang') or data.get('language') or data.get('lang') or 'en'
        
        # Get translation mode
        mode = data.get('mode', 'gemini')  # Default to gemini for backward compatibility
        
        print(f"\n{'='*60}")
        print(f"🔄 TRANSLATION REQUEST:")
        print(f"   Mode: {mode.upper()}")
        print(f"   Target Language: {target_lang}")
        print(f"   Text Length: {len(text)} characters")
        print(f"   Text Preview: {text[:100]}...")
        print(f"{'='*60}\n")
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Call translate_text from translate.py with mode parameter
        translated_text = translate_text(
            text=text,
            target_lang=target_lang,
            mode=mode  # 🔥 This tells translate.py which engine to use
        )
        
        print(f"✅ Translation completed!")
        print(f"   Result length: {len(translated_text)} characters")
        print(f"   Preview: {translated_text[:100]}...\n")
        
        return jsonify({'translated_text': translated_text})
        
    except Exception as e:
        error_msg = f"Translation error: {str(e)}"
        print(f"❌ {error_msg}\n")
        return jsonify({'error': error_msg}), 500

# Extract PDF Text
@app.route('/extract-text', methods=['POST'])
def extract_text():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF not found'}), 404
        
        print(f"📄 Extracting text from: {session_id}")
        
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                text += page_text + "\n"
                print(f"   Page {page_num}: {len(page_text)} characters")
        
        print(f"✅ Extracted {len(text)} total characters\n")
        
        return jsonify({'text': text})
    except Exception as e:
        print(f"❌ Extract text error: {e}")
        return jsonify({'error': str(e)}), 500

# Summarization
@app.route('/summarize', methods=['POST'])
def summarize():
    """Summarize PDF text using AI with HTML formatting"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"📝 Summarizing {len(text)} characters...")
        
        # Get summary with HTML formatting
        result = summarize_text(text, max_length=20000)
        
        print(f"✅ Summary generated!\n")
        
        # Return the HTML formatted version
        return jsonify({
            'summary': result['summary_html'],  # Send formatted HTML
            'raw_summary': result['summary']     # Original markdown (backup)
        })
        
    except Exception as e:
        print(f"❌ Summarization error: {e}")
        return jsonify({'error': str(e)}), 500

# Upload PDF
@app.route('/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files allowed'}), 400
        
        session_id = str(uuid.uuid4())
        filename = f"{session_id}.pdf"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        print(f"✅ PDF uploaded: {session_id} ({file.filename})\n")
        
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Get PDF
@app.route('/get-pdf/<session_id>')
def get_pdf(session_id):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        if not os.path.exists(filepath):
            return jsonify({'error': 'PDF not found'}), 404
        return send_file(filepath, mimetype='application/pdf')
    except Exception as e:
        print(f"❌ Get PDF error: {e}")
        return jsonify({'error': str(e)}), 404

# Viewer
@app.route('/viewer/<session_id>')
def viewer(session_id):
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
    if not os.path.exists(pdf_path):
        return "Session expired or invalid", 404
    return render_template('viewer.html', session_id=session_id)

# Cleanup
@app.route('/cleanup/<session_id>', methods=['POST'])
def cleanup(session_id):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🗑️ Cleaned up: {session_id}\n")
        return jsonify({'success': True})
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return jsonify({'success': False}), 500
    
@app.route('/extract-text-pages', methods=['POST'])
def extract_text_pages():
    """
    Extract PDF text page by page for better TTS processing
    Returns an array of page texts instead of one large text
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF not found'}), 404
        
        print(f"📄 Extracting text page by page from: {session_id}")
        
        pages = []
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                
                # Clean the text (remove excessive whitespace, fix line breaks)
                page_text = ' '.join(page_text.split())
                
                if page_text.strip():  # Only add non-empty pages
                    pages.append({
                        'page_number': page_num,
                        'text': page_text.strip(),
                        'char_count': len(page_text)
                    })
                    print(f"   Page {page_num}/{total_pages}: {len(page_text)} characters")
                else:
                    print(f"   Page {page_num}/{total_pages}: Empty (skipped)")
        
        print(f"✅ Extracted {len(pages)} pages with text\n")
        
        return jsonify({
            'pages': pages,
            'total_pages': len(pages)
        })
        
    except Exception as e:
        print(f"❌ Extract pages error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DEEP READ PDF - AI-Powered PDF Reader")
    print("="*60)
    print(f"📂 Upload folder: {app.config['UPLOAD_FOLDER']}")
    print(f"🌐 Translation: Hybrid mode (Gemini + Deep-Translator)")
    print(f"🎤 Text-to-Speech: Enabled")
    print(f"📝 AI Summarization: Enabled")
    print("="*60 + "\n")
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

