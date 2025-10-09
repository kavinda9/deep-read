from deep_translator import GoogleTranslator
import time

print("🌐 Translation Module loaded (deep_translator)")

# Language mapping for better compatibility
LANGUAGE_MAP = {
    'en': 'en',
    'si': 'si',
    'ta': 'ta',
    'hi': 'hi',
    'es': 'es',
    'fr': 'fr',
    'de': 'de',
    'zh-CN': 'zh-CN',
    'zh': 'zh-CN',
    'ja': 'ja',
    'ko': 'ko',
    'ar': 'ar',
    'ru': 'ru',
    'pt': 'pt',
    'it': 'it',
    'nl': 'nl',
    'tr': 'tr'
}


def chunk_text(text, max_chunk_size=4500):
    """
    Split text into chunks for translation
    Respects sentence boundaries to maintain context
    
    Args:
        text (str): Text to chunk
        max_chunk_size (int): Maximum characters per chunk (Google Translate limit ~5000)
    
    Returns:
        list: List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Split by sentences (periods, question marks, exclamation marks, newlines)
    # Replace multiple delimiters with period for consistent splitting
    normalized_text = text.replace('!', '.').replace('?', '.').replace('\n\n', '. ')
    sentences = normalized_text.split('.')
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # If adding this sentence exceeds limit, save current chunk
        if len(current_chunk) + len(sentence) + 2 > max_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
            else:
                # Single sentence is too long, split by words
                words = sentence.split()
                for word in words:
                    if len(current_chunk) + len(word) + 1 > max_chunk_size:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = word + " "
                    else:
                        current_chunk += word + " "
        else:
            current_chunk += sentence + ". "
    
    # Add remaining chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def translate_chunk(chunk, target_lang='en', retry_count=3):
    """
    Translate a single chunk with retry logic
    
    Args:
        chunk (str): Text chunk to translate
        target_lang (str): Target language code
        retry_count (int): Number of retries on failure
    
    Returns:
        str: Translated chunk
    """
    # Normalize language code
    target_lang = LANGUAGE_MAP.get(target_lang, target_lang)
    
    for attempt in range(retry_count):
        try:
            translator = GoogleTranslator(source='auto', target=target_lang)
            translated = translator.translate(chunk)
            
            # Validate translation
            if translated and len(translated) > 0:
                return translated
            else:
                raise Exception("Empty translation received")
                
        except Exception as e:
            print(f"   ⚠️ Attempt {attempt + 1}/{retry_count} failed: {e}")
            
            if attempt < retry_count - 1:
                # Wait before retry (exponential backoff)
                wait_time = (attempt + 1) * 1.0
                print(f"   Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                # All retries failed, return original chunk
                print(f"   ❌ All retries failed, keeping original text")
                return chunk
    
    return chunk


def translate_text(text, target_lang='en', source_lang='auto'):
    """
    Robust translation with chunking and retry logic
    
    Strategy:
    1. Check text length
    2. If short (<4500 chars) → translate directly with retries
    3. If long → split into chunks, translate each, combine
    4. Handle failures gracefully (keep original if translation fails)
    
    Args:
        text (str): Text to translate
        target_lang (str): Target language code
        source_lang (str): Source language (auto-detect by default)
    
    Returns:
        str: Translated text
    """
    if not text or not text.strip():
        return ""
    
    text = text.strip()
    
    try:
        print(f"📝 Translation Request:")
        print(f"   Input: {len(text)} chars")
        print(f"   Target: {target_lang}")
        
        # For short text, translate directly
        if len(text) <= 4500:
            print(f"   Mode: Direct translation")
            result = translate_chunk(text, target_lang)
            print(f"✅ Translation complete: {len(result)} chars")
            return result
        
        # For long text, use chunking
        print(f"   Mode: Chunked translation (text too long)")
        chunks = chunk_text(text, max_chunk_size=4500)
        print(f"   Split into {len(chunks)} chunks")
        
        translated_chunks = []
        successful_chunks = 0
        failed_chunks = 0
        
        for i, chunk in enumerate(chunks, 1):
            print(f"   Chunk {i}/{len(chunks)}: {len(chunk)} chars")
            
            translated_chunk = translate_chunk(chunk, target_lang)
            translated_chunks.append(translated_chunk)
            
            # Check if translation was successful (not same as original)
            if translated_chunk != chunk:
                successful_chunks += 1
            else:
                failed_chunks += 1
            
            # Small delay between chunks to avoid rate limiting
            if i < len(chunks):
                time.sleep(0.8)
        
        # Combine chunks with proper spacing
        result = " ".join(translated_chunks)
        
        print(f"✅ Translation complete:")
        print(f"   Output: {len(result)} chars")
        print(f"   Success: {successful_chunks}/{len(chunks)} chunks")
        
        if failed_chunks > 0:
            print(f"   ⚠️ Warning: {failed_chunks} chunks kept in original language")
        
        return result
        
    except Exception as e:
        error_msg = f"Translation failed: {str(e)}"
        print(f"❌ {error_msg}")
        raise Exception(error_msg)


def get_supported_languages():
    """
    Get list of supported languages
    
    Returns:
        list: Language codes
    """
    return list(LANGUAGE_MAP.keys())


def validate_language_code(lang_code):
    """
    Validate and normalize language code
    
    Args:
        lang_code (str): Language code to validate
    
    Returns:
        str: Normalized language code or 'en' if invalid
    """
    normalized = LANGUAGE_MAP.get(lang_code, None)
    if normalized:
        return normalized
    
    print(f"⚠️ Unsupported language: {lang_code}, defaulting to English")
    return 'en'


# Test function
def test_translation():
    """Test translation with different scenarios"""
    print("\n" + "="*60)
    print("TRANSLATION MODULE TEST")
    print("="*60)
    
    # Test 1: Short text (English → Sinhala)
    print("\n📝 Test 1: Short text")
    text1 = "Hello, how are you today? This is a test."
    try:
        result1 = translate_text(text1, target_lang='si')
        print(f"✅ Original: {text1}")
        print(f"✅ Translated: {result1}")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
    
    # Test 2: Medium text (English → Tamil)
    print("\n📝 Test 2: Medium text")
    text2 = """Artificial intelligence is intelligence demonstrated by machines, 
    in contrast to the natural intelligence displayed by humans and animals. 
    Leading AI textbooks define the field as the study of intelligent agents."""
    try:
        result2 = translate_text(text2, target_lang='ta')
        print(f"✅ Original length: {len(text2)} chars")
        print(f"✅ Translated length: {len(result2)} chars")
        print(f"✅ Preview: {result2[:150]}...")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
    
    # Test 3: Long text (chunking test)
    print("\n📝 Test 3: Long text (chunking)")
    text3 = ("Machine learning is a subset of artificial intelligence. " * 100)[:6000]
    try:
        result3 = translate_text(text3, target_lang='hi')
        print(f"✅ Original length: {len(text3)} chars")
        print(f"✅ Translated length: {len(result3)} chars")
        print(f"✅ Chunks were processed successfully")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
    
    # Test 4: Language validation
    print("\n📝 Test 4: Language code validation")
    test_codes = ['en', 'si', 'zh', 'invalid']
    for code in test_codes:
        validated = validate_language_code(code)
        print(f"   {code} → {validated}")
    
    print("\n" + "="*60)
    print("✅ All tests completed!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_translation()