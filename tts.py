import io
import asyncio
import edge_tts
from gtts import gTTS
import sys
import re

print("🎙️ TTS Module loaded (Edge TTS + gTTS fallback)")

# Voice mapping for Edge TTS
EDGE_VOICES = {
    'male': {
        'en': 'en-US-GuyNeural',
        'si': 'si-LK-SameeraNeural',
        'ta': 'ta-IN-ValluvarNeural',
        'hi': 'hi-IN-MadhurNeural',
        'es': 'es-ES-AlvaroNeural',
        'fr': 'fr-FR-HenriNeural',
        'de': 'de-DE-ConradNeural',
        'zh-CN': 'zh-CN-YunxiNeural',
        'ja': 'ja-JP-KeitaNeural',
        'ko': 'ko-KR-InJoonNeural',
        'ar': 'ar-SA-HamedNeural',
        'ru': 'ru-RU-DmitryNeural',
        'pt': 'pt-BR-AntonioNeural',
        'it': 'it-IT-DiegoNeural',
        'nl': 'nl-NL-MaartenNeural',
        'tr': 'tr-TR-AhmetNeural',
    },
    'female': {
        'en': 'en-US-JennyNeural',
        'si': 'si-LK-ThiliniNeural',
        'ta': 'ta-IN-PallaviNeural',
        'hi': 'hi-IN-SwaraNeural',
        'es': 'es-ES-ElviraNeural',
        'fr': 'fr-FR-DeniseNeural',
        'de': 'de-DE-KatjaNeural',
        'zh-CN': 'zh-CN-XiaoxiaoNeural',
        'ja': 'ja-JP-NanamiNeural',
        'ko': 'ko-KR-SunHiNeural',
        'ar': 'ar-SA-ZariyahNeural',
        'ru': 'ru-RU-SvetlanaNeural',
        'pt': 'pt-BR-FranciscaNeural',
        'it': 'it-IT-ElsaNeural',
        'nl': 'nl-NL-ColetteNeural',
        'tr': 'tr-TR-EmelNeural',
    }
}

# Supported languages for gTTS fallback
GTTS_LANGUAGES = {
    'en', 'si', 'ta', 'hi', 'es', 'fr', 'de', 'zh-CN', 
    'ja', 'ko', 'ar', 'ru', 'pt', 'it', 'nl', 'tr'
}


def clean_text_for_tts(text):
    """
    Clean and normalize text for natural TTS speech
    Fixes line breaks that cause awkward pauses
    
    Args:
        text (str): Raw text with potential line breaks
    
    Returns:
        str: Cleaned text optimized for TTS
    """
    if not text:
        return ""
    
    # Replace multiple spaces with single space
    text = re.sub(r' +', ' ', text)
    
    # Replace single line breaks (not paragraph breaks) with spaces
    # This fixes: "hi my\nname\nis kavinda" → "hi my name is kavinda"
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    
    # Preserve paragraph breaks (double line breaks) - convert to period + space
    text = re.sub(r'\n{2,}', '. ', text)
    
    # Remove line breaks that interrupt sentences
    text = re.sub(r'([a-z])\n([a-z])', r'\1 \2', text, flags=re.IGNORECASE)
    
    # Fix hyphenated words split across lines: "exam-\nple" → "example"
    text = re.sub(r'-\s*\n\s*', '', text)
    
    # Remove any remaining single line breaks
    text = text.replace('\n', ' ')
    
    # Clean up multiple spaces again
    text = re.sub(r' +', ' ', text)
    
    # Fix punctuation spacing
    text = re.sub(r'\s+([.,!?;:])', r'\1', text)
    text = re.sub(r'([.,!?;:])\s*([.,!?;:])', r'\1\2', text)
    
    # Ensure proper spacing after punctuation
    text = re.sub(r'([.,!?;:])([A-Za-z])', r'\1 \2', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Fix multiple periods
    text = re.sub(r'\.{2,}', '.', text)
    
    # Ensure sentences end with proper punctuation
    if text and not text[-1] in '.!?':
        text += '.'
    
    return text


async def generate_edge_tts_async(text, voice_name, rate="+0%", volume="+0%"):
    """
    Generate TTS using Edge TTS (async)
    
    Args:
        text (str): Text to convert to speech
        voice_name (str): Voice identifier
        rate (str): Speech rate adjustment (e.g., "+20%", "-10%")
        volume (str): Volume adjustment (e.g., "+0%", "-10%")
    
    Returns:
        io.BytesIO: Audio data
    """
    communicate = edge_tts.Communicate(text, voice_name, rate=rate, volume=volume)
    audio_data = io.BytesIO()
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.write(chunk["data"])
    
    audio_data.seek(0)
    return audio_data


def run_async_in_sync(coro):
    """
    Safely run async coroutine in sync context.
    Handles existing event loops properly.
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running (e.g., in Jupyter), use nest_asyncio
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(coro)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create new one
        if sys.version_info >= (3, 7):
            return asyncio.run(coro)
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()


def text_to_speech_generate(text, lang='en', slow=False):
    """
    Convert text to speech using gTTS (fallback)
    
    Args:
        text (str): Text to convert to speech
        lang (str): Language code (default: 'en')
        slow (bool): Slow speech rate (default: False)
    
    Returns:
        BytesIO: Audio file as MP3 bytes
    """
    try:
        # Clean text before TTS
        text = clean_text_for_tts(text)
        
        print(f"🎙️ Generating TTS with gTTS: {len(text)} chars, lang: {lang}")
        
        # Normalize language code for gTTS
        gtts_lang = lang.split('-')[0] if '-' in lang else lang
        if gtts_lang not in GTTS_LANGUAGES:
            print(f"⚠️ Language {gtts_lang} not supported by gTTS, using 'en'")
            gtts_lang = 'en'
        
        tts = gTTS(text=text, lang=gtts_lang, slow=slow)
        
        audio_file = io.BytesIO()
        tts.write_to_fp(audio_file)
        audio_file.seek(0)
        
        print(f"✅ Audio generated successfully ({audio_file.getbuffer().nbytes} bytes)")
        return audio_file
        
    except Exception as e:
        print(f"❌ TTS Error: {e}")
        raise Exception(f"Text-to-speech failed: {str(e)}")


def text_to_speech_with_voice(text, voice_type='male', speed=1.0, lang='en'):
    """
    Convert text to speech with voice selection using Edge TTS
    
    Args:
        text (str): Text to convert to speech
        voice_type (str): 'male' or 'female'
        speed (float): Speech speed multiplier (0.5 = 50% slower, 2.0 = 2x faster)
        lang (str): Language code
    
    Returns:
        io.BytesIO: Audio file in memory
    """
    try:
        # Clean text before TTS - FIXES LINE BREAK PAUSES
        text = clean_text_for_tts(text)
        
        print(f"🎤 Generating {voice_type} voice for lang: {lang}")
        print(f"   Original → Cleaned: {len(text)} chars")
        print(f"   Preview: {text[:80]}...")
        
        # Validate and sanitize inputs
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        text = text.strip()
        
        # Get the appropriate voice
        voice_map = EDGE_VOICES.get(voice_type.lower(), EDGE_VOICES['female'])
        voice_name = voice_map.get(lang, voice_map.get('en'))
        
        # Convert speed to rate percentage for Edge TTS
        # speed 1.0 = +0%, 1.5 = +50%, 0.5 = -50%
        rate_percent = int((speed - 1.0) * 100)
        rate = f"{rate_percent:+d}%"
        
        print(f"   Using voice: {voice_name}, rate: {rate}")
        
        # Run async function safely
        audio_file = run_async_in_sync(
            generate_edge_tts_async(text, voice_name, rate=rate)
        )
        
        print(f"✅ {voice_type.capitalize()} voice generated successfully ({audio_file.getbuffer().nbytes} bytes)")
        return audio_file
        
    except Exception as e:
        print(f"⚠️ Edge TTS error: {e}, falling back to gTTS...")
        # Fallback to gTTS
        slow = speed < 0.9
        return text_to_speech_generate(text, lang=lang, slow=slow)


def get_available_voices(lang='en'):
    """
    Get available voices for a specific language
    
    Args:
        lang (str): Language code
    
    Returns:
        dict: Available voices {'male': voice_name, 'female': voice_name}
    """
    return {
        'male': EDGE_VOICES['male'].get(lang, EDGE_VOICES['male']['en']),
        'female': EDGE_VOICES['female'].get(lang, EDGE_VOICES['female']['en'])
    }


def get_supported_languages():
    """
    Get list of all supported languages
    
    Returns:
        list: Language codes
    """
    return list(EDGE_VOICES['male'].keys())


# Quick test function
def test_tts():
    """Test TTS functionality with text cleaning"""
    print("\n🧪 Testing TTS module...")
    
    try:
        # Test text with line breaks
        test_text = """hi my
name 
is kavinda"""
        
        print(f"\n📝 Original text: {repr(test_text)}")
        cleaned = clean_text_for_tts(test_text)
        print(f"✨ Cleaned text: {cleaned}")
        
        # Test Edge TTS
        audio = text_to_speech_with_voice(test_text, voice_type='female', lang='en')
        print(f"✅ Edge TTS test passed: {audio.getbuffer().nbytes} bytes")
        
        # Test gTTS fallback
        audio2 = text_to_speech_generate("Fallback test", lang='en')
        print(f"✅ gTTS test passed: {audio2.getbuffer().nbytes} bytes")
        
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    test_tts()