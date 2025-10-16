import google.generativeai as genai
from deep_translator import GoogleTranslator
import os
from dotenv import load_dotenv
import time
import re

load_dotenv()

print("🌐 Translation Module loaded (Hybrid: Gemini + Deep-Translator)")

# Configure Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("❌ ERROR: GEMINI_API_KEY not found in .env file!")
    print("⚠️  Gemini translation will not be available")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    print("✅ Gemini API configured successfully")

# Extended Language mapping
LANGUAGE_MAP = {
    'en': 'English',
    'si': 'Sinhala',
    'ta': 'Tamil',
    'hi': 'Hindi',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'zh-CN': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean',
    'ar': 'Arabic',
    'ru': 'Russian',
    'pt': 'Portuguese',
    'it': 'Italian',
    'nl': 'Dutch',
    'tr': 'Turkish'
}


def clean_pdf_text(text):
    """
    Clean PDF text while PRESERVING document structure:
    - Keeps paragraph breaks
    - Preserves headings and titles (short lines, often capitalized)
    - Joins broken sentences within paragraphs
    - Maintains bullet points and lists
    
    Args:
        text (str): Raw PDF text with line breaks
    
    Returns:
        str: Cleaned text with preserved structure
    """
    if not text:
        return ""
    
    # Split into lines for intelligent processing
    lines = text.split('\n')
    processed_lines = []
    current_paragraph = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines but mark paragraph break
        if not line:
            if current_paragraph:
                # Join current paragraph and add it
                processed_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            # Add empty line to preserve paragraph breaks
            processed_lines.append('')
            continue
        
        # Detect if line is likely a HEADING/TITLE
        # Headings are usually: short, capitalized, no ending punctuation
        is_heading = (
            len(line) < 60 and  # Short line
            (line.isupper() or line[0].isupper()) and  # Starts with capital or all caps
            not line[-1] in '.!?,' and  # No ending punctuation
            not line.startswith('-') and  # Not a bullet point
            not line.startswith('•')
        )
        
        # Detect BULLET POINTS or LIST ITEMS
        is_bullet = (
            line.startswith('-') or 
            line.startswith('•') or 
            line.startswith('*') or
            re.match(r'^\d+\.', line) or  # Numbered list: "1. item"
            re.match(r'^[a-z]\)', line)   # Lettered list: "a) item"
        )
        
        # If it's a heading or bullet, add it as a separate line
        if is_heading or is_bullet:
            if current_paragraph:
                processed_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            processed_lines.append(line)
            continue
        
        # Fix hyphenated words split across lines: "exam-\nple" → "example"
        if line.endswith('-'):
            # Remove hyphen and continue to next line
            current_paragraph.append(line[:-1])
            continue
        
        # Check if line ends mid-sentence (no punctuation, lowercase start of next line)
        ends_mid_sentence = (
            not line[-1] in '.!?:;' and
            i + 1 < len(lines) and
            len(lines[i + 1].strip()) > 0 and
            lines[i + 1].strip()[0].islower()
        )
        
        # Add line to current paragraph
        current_paragraph.append(line)
        
        # If line ends with punctuation or next line starts with capital, end paragraph
        if not ends_mid_sentence and (line[-1] in '.!?:;' or i == len(lines) - 1):
            processed_lines.append(' '.join(current_paragraph))
            current_paragraph = []
    
    # Add any remaining paragraph
    if current_paragraph:
        processed_lines.append(' '.join(current_paragraph))
    
    # Join with newlines to preserve structure
    text = '\n'.join(processed_lines)
    
    # Clean up excessive blank lines (max 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    
    # Fix spacing around punctuation
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def chunk_text(text, max_chunk_size=4000):
    """
    Split text into chunks for translation while PRESERVING structure
    - Respects paragraph boundaries
    - Keeps headings with their paragraphs
    - Maintains formatting
    
    Args:
        text (str): Text to chunk
        max_chunk_size (int): Maximum size of each chunk
    
    Returns:
        list: List of text chunks with preserved structure
    """
    # IMPORTANT: Clean the text FIRST to preserve structure
    text = clean_pdf_text(text)
    
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by paragraphs (double newline or single newline for headings)
    paragraphs = re.split(r'\n\n+', text)
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If this paragraph alone is too big, split it by sentences
        if len(para) > max_chunk_size:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 2 > max_chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    if current_chunk:
                        current_chunk += " " + sentence
                    else:
                        current_chunk = sentence
        
        # If adding this paragraph exceeds limit, save current chunk
        elif len(current_chunk) + len(para) + 2 > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            # Add paragraph with double newline to preserve structure
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Add the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def translate_with_gemini(text, target_lang='en'):
    """
    Translate text using Gemini AI (HIGH QUALITY)
    Best for: Selected text, short passages
    
    Args:
        text (str): Text to translate
        target_lang (str): Target language code (e.g., 'si', 'ta', 'en')
    
    Returns:
        str: Translated text
    """
    # Clean text before translation
    text = clean_pdf_text(text)
    
    # Get the full language name
    target_language = LANGUAGE_MAP.get(target_lang, 'English')
    
    print(f"\n{'='*60}")
    print(f"🤖 GEMINI AI TRANSLATION:")
    print(f"   Target Lang Code: {target_lang}")
    print(f"   Target Language: {target_language}")
    print(f"   Text Length: {len(text)} characters")
    print(f"   Text Preview: {text[:100]}...")
    print(f"{'='*60}")
    
    # Create a clear, simple prompt
    prompt = f"""Translate this text to {target_language}.

Rules:
1. Only provide the translation, nothing else
2. Keep natural grammar in {target_language}
3. Preserve meaning and context
4. Don't add explanations or notes

Text: {text}

{target_language} translation:"""
    
    try:
        # Use Gemini Flash (fast and stable)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        
        translated = response.text.strip()
        
        # Clean up any extra formatting
        translated = translated.replace('**', '').strip()
        translated = translated.strip('"').strip("'")
        
        print(f"✅ Gemini Translation Result: {translated[:100]}...\n")
        
        return translated
        
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        print(f"   Returning original text\n")
        return text


def translate_with_deep_translator(text, target_lang='en'):
    """
    Translate text using Deep-Translator/Google Translate (FAST)
    Best for: Full PDFs, long documents
    
    Args:
        text (str): Text to translate
        target_lang (str): Target language code
    
    Returns:
        str: Translated text with preserved formatting
    """
    # Clean text before translation (preserves structure)
    text = clean_pdf_text(text)
    
    print(f"\n{'='*60}")
    print(f"⚡ DEEP-TRANSLATOR (FAST MODE):")
    print(f"   Target Language: {target_lang}")
    print(f"   Text Length: {len(text)} characters")
    print(f"{'='*60}")
    
    try:
        # Split long text into chunks (Google Translator has limits)
        max_chunk_size = 4500
        chunks = chunk_text(text, max_chunk_size)
        
        print(f"   Splitting into {len(chunks)} chunks...")
        
        translated_chunks = []
        translator = GoogleTranslator(source='auto', target=target_lang)
        
        for i, chunk in enumerate(chunks, 1):
            print(f"   Translating chunk {i}/{len(chunks)}...")
            try:
                translated = translator.translate(chunk)
                translated_chunks.append(translated)
            except Exception as e:
                print(f"   ⚠️ Chunk {i} failed: {e}, using original")
                translated_chunks.append(chunk)
        
        # Join with double newline to preserve paragraph breaks
        result = '\n\n'.join(translated_chunks)
        print(f"✅ Fast translation completed!\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Deep-Translator Error: {e}")
        print(f"   Returning original text\n")
        return text


def translate_text(text, target_lang='en', source_lang='auto', mode='gemini'):
    """
    Main translation function with hybrid mode support
    
    Args:
        text (str): Text to translate
        target_lang (str): Target language code
        source_lang (str): Source language (ignored, auto-detected)
        mode (str): 'gemini' for high quality or 'fast' for speed
    
    Returns:
        str: Translated text
    """
    if not text or not text.strip():
        return ""
    
    text = text.strip()
    
    # Validate language
    if target_lang not in LANGUAGE_MAP and target_lang != 'auto':
        print(f"⚠️ Unknown language code: {target_lang}, using English")
        target_lang = 'en'
    
    try:
        # MODE 1: GEMINI AI (High Quality)
        if mode == 'gemini':
            if not GEMINI_API_KEY:
                print("⚠️ Gemini not available, switching to fast mode...")
                return translate_with_deep_translator(text, target_lang)
            
            # For short text, use Gemini directly
            if len(text) <= 4000:
                return translate_with_gemini(text, target_lang)
            
            # For longer text in gemini mode, chunk it
            print(f"📦 Text too long for single Gemini call, chunking...")
            chunks = chunk_text(text, max_chunk_size=4000)
            print(f"   Split into {len(chunks)} chunks")
            
            translated_chunks = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"   Processing chunk {i}/{len(chunks)}...")
                translated_chunk = translate_with_gemini(chunk, target_lang)
                translated_chunks.append(translated_chunk)
                
                # Small delay between chunks to avoid rate limits
                if i < len(chunks):
                    time.sleep(1.5)
            
            # Join with double newline to preserve structure
            result = "\n\n".join(translated_chunks)
            print(f"✅ All chunks translated with Gemini!\n")
            
            return result
        
        # MODE 2: FAST (Deep-Translator)
        else:
            return translate_with_deep_translator(text, target_lang)
        
    except Exception as e:
        print(f"❌ Translation failed: {e}")
        return text


def get_supported_languages():
    """Get list of supported languages"""
    return list(LANGUAGE_MAP.keys())


def validate_language_code(lang_code):
    """Validate language code"""
    return lang_code if lang_code in LANGUAGE_MAP else 'en'


# Test function
def test_translation():
    """Test translation functionality with structure preservation"""
    print("\n" + "="*70)
    print("HYBRID TRANSLATION TEST - WITH STRUCTURE PRESERVATION")
    print("="*70)
    
    # Test 1: Document with headings and paragraphs
    print("\n🧪 TEST 1: Document with Structure - Gemini Mode")
    text1 = """INTRODUCTION TO AI

Artificial intelligence (AI) is the simulation of human intelligence
processes by machines, especially computer systems.

KEY CONCEPTS

Machine Learning: A subset of AI that enables systems to learn
and improve from experience.

Neural Networks: Computing systems inspired by biological
neural networks that constitute animal brains."""
    
    result1 = translate_text(text1, target_lang='si', mode='gemini')
    print(f"📝 Original:\n{text1}")
    print(f"\n✅ Sinhala:\n{result1}")
    
    # Test 2: Paragraph preservation
    print("\n🧪 TEST 2: Multiple Paragraphs - Fast Mode")
    text2 = """First paragraph about artificial intelligence.
This is part of the first paragraph.

Second paragraph about machine learning.
This continues the second paragraph.

Third paragraph with conclusions."""
    
    result2 = translate_text(text2, target_lang='ta', mode='fast')
    print(f"📝 Original:\n{text2}")
    print(f"\n✅ Tamil:\n{result2}")
    
    # Test 3: List and bullet points
    print("\n🧪 TEST 3: Lists and Structure → Spanish")
    text3 = """Benefits of AI:

- Increased efficiency
- Better decision making
- Cost reduction

These are the main advantages."""
    
    result3 = translate_text(text3, target_lang='es', mode='fast')
    print(f"📝 Original:\n{text3}")
    print(f"\n✅ Spanish:\n{result3}")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS COMPLETED")
    print("="*70 + "\n")


if __name__ == "__main__":
    test_translation()