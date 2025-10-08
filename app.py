from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import PyPDF2
import os
import uuid
from dotenv import load_dotenv

# Import helper modules
from translate import translate_text
from summarize import summarize_text
from tts import text_to_speech_with_voice

load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

# Text-to-Speech (UPDATED with voice selection)
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

# Translation
@app.route('/translate', methods=['POST'])
def translate():
    try:
        data = request.json
        text = data.get('text', '')
        target_lang = data.get('target_lang', 'en')
        
        translated = translate_text(text, target_lang)
        return jsonify({'translated_text': translated})
    except Exception as e:
        print(f"Translation error: {e}")
        return jsonify({'error': str(e)}), 500

# Extract PDF Text
@app.route('/extract-text', methods=['POST'])
def extract_text():
    try:
        data = request.json
        session_id = data.get('session_id')
        
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        
        if not os.path.exists(pdf_path):
            return jsonify({'error': 'PDF not found'}), 404
        
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        return jsonify({'text': text})
    except Exception as e:
        print(f"Extract text error: {e}")
        return jsonify({'error': str(e)}), 500

# Summarization
@app.route('/summarize', methods=['POST'])
def summarize():
    """Summarize PDF text using Groq AI with HTML formatting"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        print(f"📝 Summarizing {len(text)} characters...")
        
        # Get summary with HTML formatting
        result = summarize_text(text, max_length=20000)
        
        # Return the HTML formatted version
        return jsonify({
            'summary': result['summary_html'],  # ✅ Send formatted HTML
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
        
        return jsonify({'success': True, 'session_id': session_id})
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Get PDF
@app.route('/get-pdf/<session_id>')
def get_pdf(session_id):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        return send_file(filepath, mimetype='application/pdf')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

# Viewer
@app.route('/viewer/<session_id>')
def viewer(session_id):
    return render_template('viewer.html', session_id=session_id)

# Cleanup
@app.route('/cleanup/<session_id>', methods=['POST'])
def cleanup(session_id):
    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}.pdf")
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'success': True})
    except Exception as e:
        print(f"Cleanup error: {e}")
        return jsonify({'success': False}), 500

if __name__ == '__main__':
    app.run(debug=True)
