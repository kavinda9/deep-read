from groq import Groq
import os
from dotenv import load_dotenv
import re

load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)

print(f"✅ Groq configured: {'Yes' if GROQ_API_KEY else 'No'}")


def markdown_to_html(text):
    """
    Convert markdown formatting to styled HTML
    
    Args:
        text (str): Text with markdown formatting
    
    Returns:
        str: HTML formatted text with colors
    """
    # Replace **text** with red bold (main topics)
    text = re.sub(
        r'\*\*(.+?)\*\*', 
        r'<strong style="color: #d32f2f; font-size: 1.1em;">\1</strong>', 
        text
    )
    
    # Replace *text* with purple italic (sub topics)
    text = re.sub(
        r'\*(.+?)\*', 
        r'<em style="color: #7b1fa2; font-weight: 600;">\1</em>', 
        text
    )
    
    # Replace ### Headings with red headings
    text = re.sub(
        r'^### (.+)$', 
        r'<h3 style="color: #d32f2f; margin-top: 20px; margin-bottom: 10px;">\1</h3>', 
        text, 
        flags=re.MULTILINE
    )
    
    # Replace ## Headings with larger red headings
    text = re.sub(
        r'^## (.+)$', 
        r'<h2 style="color: #c62828; margin-top: 25px; margin-bottom: 12px;">\1</h2>', 
        text, 
        flags=re.MULTILINE
    )
    
    # Replace # Headings with largest red headings
    text = re.sub(
        r'^# (.+)$', 
        r'<h1 style="color: #b71c1c; margin-top: 30px; margin-bottom: 15px;">\1</h1>', 
        text, 
        flags=re.MULTILINE
    )
    
    # Replace bullet points (- or *) with styled list items
    text = re.sub(
        r'^\s*[-*]\s+(.+)$', 
        r'<div style="margin-left: 20px; margin-bottom: 8px;">• \1</div>', 
        text, 
        flags=re.MULTILINE
    )
    
    # Replace numbered lists (1. 2. etc)
    text = re.sub(
        r'^\s*(\d+)\.\s+(.+)$', 
        r'<div style="margin-left: 20px; margin-bottom: 8px;"><strong style="color: #1976d2;">\1.</strong> \2</div>', 
        text, 
        flags=re.MULTILINE
    )
    
    # Replace newlines with <br> for proper spacing
    text = text.replace('\n\n', '<br><br>')
    text = text.replace('\n', '<br>')
    
    return text


def summarize_text(text, max_length=20000):
    """
    Summarize text using Groq's LLaMA model with enhanced formatting
    
    Args:
        text (str): Text to summarize
        max_length (int): Maximum text length to process (default: 20000)
    
    Returns:
        dict: Contains both 'summary' (plain) and 'summary_html' (formatted)
    """
    try:
        # Truncate text if too long
        text = text[:max_length]
        
        print(f"📝 Summarizing {len(text)} characters...")
        
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at summarizing documents. 
                    
Format your summaries with:
- **Main Topics** in bold (use **text**)
- *Sub-points* in italic (use *text*)
- Clear structure with headings (use # ## ###)
- Bullet points for lists (use - or *)

Provide clear, well-organized summaries that are easy to scan."""
                },
                {
                    "role": "user",
                    "content": f"Summarize this document with clear formatting:\n\n{text}"
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=2048,
        )
        
        summary = chat_completion.choices[0].message.content
        
        # Convert markdown to HTML with colors
        summary_html = markdown_to_html(summary)
        
        print("✅ Summary generated with formatting")
        
        return {
            'summary': summary,  # Original markdown
            'summary_html': summary_html  # Formatted HTML
        }
        
    except Exception as e:
        print(f"❌ Summarization error: {e}")
        raise Exception(f"Summarization failed: {str(e)}")


def summarize_text_simple(text, max_length=20000):
    """
    Simple wrapper that returns only formatted HTML (for backward compatibility)
    
    Args:
        text (str): Text to summarize
        max_length (int): Maximum text length to process
    
    Returns:
        str: HTML formatted summary
    """
    result = summarize_text(text, max_length)
    return result['summary_html']


# Test function
def test_formatting():
    """Test the markdown to HTML conversion"""
    test_text = """# Main Document Summary

## Key Points

**Important Topic 1**: This is a crucial point
*Sub-point*: Additional details here

**Important Topic 2**: Another main idea
- Bullet point 1
- Bullet point 2

### Section Details

1. First numbered point
2. Second numbered point

**Conclusion**: Final thoughts"""
    
    print("\n🧪 Testing formatting:")
    print("-" * 50)
    html_output = markdown_to_html(test_text)
    print(html_output)
    print("-" * 50)


if __name__ == "__main__":
    test_formatting()