from deep_translator import GoogleTranslator

def translate_text(text, target_lang='en'):
    """
    Translate text to target language using Google Translator
    
    Args:
        text (str): Text to translate
        target_lang (str): Target language code (default: 'en')
    
    Returns:
        str: Translated text
    """
    try:
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated = translator.translate(text)
        return translated
    except Exception as e:
        raise Exception(f"Translation failed: {str(e)}")