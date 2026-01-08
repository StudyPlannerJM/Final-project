# ==============================================================================
# SUMMARIZER MODULE - Text extraction and summarization functions
# ==============================================================================

import requests
import os


def extract_text_from_response(data):
    """
    Helper function to extract text from API response data.
    Handles different response formats (string, dict, list).
    
    Args:
        data: The data from API response (can be str, dict, or list)
        
    Returns:
        str: Extracted text as a string
    """
    if data is None:
        return ''
    
    if isinstance(data, str):
        return data
    
    if isinstance(data, dict):
        # Try common keys where text might be stored
        for key in ['text', 'content', 'extracted_text', 'result', 'value', 'output']:
            if key in data:
                return extract_text_from_response(data[key])
        # If no known key, join all string values
        text_parts = []
        for value in data.values():
            extracted = extract_text_from_response(value)
            if extracted:
                text_parts.append(extracted)
        return '\n'.join(text_parts)
    
    if isinstance(data, list):
        # Join list items
        text_parts = []
        for item in data:
            extracted = extract_text_from_response(item)
            if extracted:
                text_parts.append(extracted)
        return '\n'.join(text_parts)
    
    # For other types, convert to string
    return str(data)


# ApyHub API Configuration
APYHUB_API_KEY = "APY0xmuNMuMOM6C4fpyELD2neLTEJZHWBZ9X80HYRJTenbR6kpg3iXnbS7d15xYPPlviZ0d"
APYHUB_WORD_URL = "https://api.apyhub.com/extract/text/word-file"
APYHUB_PDF_URL = "https://api.apyhub.com/extract/text/pdf-file"
APYHUB_OCR_URL = "https://api.apyhub.com/ai/document/extract/read/file"


def extract_text_from_word(file_path):
    """
    Extract text from a Word document (.docx) using ApyHub API
    
    Args:
        file_path: Path to the Word document
        
    Returns:
        tuple: (success: bool, text_or_error: str)
    """
    try:
        headers = {
            'apy-token': APYHUB_API_KEY,
        }
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            }
            response = requests.post(APYHUB_WORD_URL, headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            # ApyHub returns the text in the 'data' field
            raw_data = result.get('data', '')
            text = extract_text_from_response(raw_data)
            if text and text.strip():
                return True, text.strip()
            else:
                return False, "No text could be extracted from the document."
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            return False, error_msg
            
    except Exception as e:
        return False, f"Error extracting text from Word file: {str(e)}"


def extract_text_from_pdf(file_path):
    """
    Extract text from a PDF document using ApyHub API
    
    Args:
        file_path: Path to the PDF document
        
    Returns:
        tuple: (success: bool, text_or_error: str)
    """
    try:
        headers = {
            'apy-token': APYHUB_API_KEY,
        }
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'application/pdf')
            }
            response = requests.post(APYHUB_PDF_URL, headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            raw_data = result.get('data', '')
            text = extract_text_from_response(raw_data)
            if text and text.strip():
                return True, text.strip()
            else:
                return False, "No text could be extracted from the PDF."
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            return False, error_msg
            
    except Exception as e:
        return False, f"Error extracting text from PDF: {str(e)}"


def extract_text_from_image_ocr(file_path):
    """
    Extract text from a scanned document/image using OCR via ApyHub API
    
    Args:
        file_path: Path to the image file (jpg, png, etc.)
        
    Returns:
        tuple: (success: bool, text_or_error: str)
    """
    try:
        headers = {
            'apy-token': APYHUB_API_KEY,
        }
        
        # Determine content type based on file extension
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.tiff': 'image/tiff',
            '.tif': 'image/tiff',
            '.pdf': 'application/pdf'
        }
        content_type = content_types.get(ext, 'application/octet-stream')
        
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, content_type),
            }
            response = requests.post(APYHUB_OCR_URL, headers=headers, files=files)
        
        if response.status_code == 200:
            result = response.json()
            raw_data = result.get('data', '')
            text = extract_text_from_response(raw_data)
            if text and text.strip():
                return True, text.strip()
            else:
                return False, "No text could be extracted using OCR."
        else:
            error_msg = f"API Error: {response.status_code} - {response.text}"
            return False, error_msg
            
    except Exception as e:
        return False, f"Error extracting text using OCR: {str(e)}"


def extract_text(file_path, file_type):
    """
    Main function to extract text from various file types
    
    Args:
        file_path: Path to the file
        file_type: Type of extraction ('word', 'pdf', 'ocr')
        
    Returns:
        tuple: (success: bool, text_or_error: str)
    """
    if file_type == 'word':
        return extract_text_from_word(file_path)
    elif file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'ocr':
        return extract_text_from_image_ocr(file_path)
    else:
        return False, "Unsupported file type"


def generate_summary(text, max_sentences=10):
    """
    Generate a summary from the extracted text using a simple extractive summarization approach.
    This creates bullet points from the key sentences.
    
    Args:
        text: The extracted text to summarize
        max_sentences: Maximum number of sentences in the summary
        
    Returns:
        str: The summarized text as bullet points
    """
    import re
    
    # Ensure text is a string (handle dict/list cases)
    if not isinstance(text, str):
        text = extract_text_from_response(text)
    
    if not text or len(text.strip()) == 0:
        return "No content to summarize."
    
    # Clean the text - remove extra whitespace and normalize
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'\n+', '\n', text)  # Normalize newlines
    
    # Split into sentences using multiple delimiters
    sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
    
    # Filter out very short sentences and clean them
    cleaned_sentences = []
    for s in sentences:
        s = s.strip()
        # Skip very short sentences or ones that look like headers/fragments
        if len(s) > 30 and not s.isupper() and s.count(' ') >= 3:
            cleaned_sentences.append(s)
    
    if not cleaned_sentences:
        # If no valid sentences found, return a cleaned version of original
        if len(text) > 500:
            return f"Document Content Preview:\n\n{text[:500]}..."
        return f"Document Content:\n\n{text}"
    
    # Simple extractive summarization: score sentences by various factors
    scored_sentences = []
    for i, sentence in enumerate(cleaned_sentences):
        # Score based on position (earlier sentences often more important)
        position_score = 1.0 / (i + 1)
        # Score based on length (medium-length sentences are often better)
        optimal_length = 100
        length_diff = abs(len(sentence) - optimal_length)
        length_score = max(0, 1.0 - (length_diff / 200))
        # Bonus for sentences with important keywords
        keyword_score = 0
        important_words = ['important', 'key', 'main', 'significant', 'essential', 
                          'conclusion', 'result', 'therefore', 'however', 'summary']
        for word in important_words:
            if word.lower() in sentence.lower():
                keyword_score += 0.1
        # Combined score
        score = position_score * 0.4 + length_score * 0.3 + min(keyword_score, 0.3)
        scored_sentences.append((score, i, sentence))
    
    # Sort by score and get top sentences
    scored_sentences.sort(reverse=True)
    top_sentences = scored_sentences[:max_sentences]
    
    # Sort back by original position to maintain logical flow
    top_sentences.sort(key=lambda x: x[1])
    
    # Format as bullet points for study notes
    summary_bullets = []
    for _, _, sentence in top_sentences:
        # Clean up the sentence
        sentence = sentence.strip()
        # Capitalize first letter if needed
        if sentence and sentence[0].islower():
            sentence = sentence[0].upper() + sentence[1:]
        # Add period if missing
        if sentence and not sentence[-1] in '.!?':
            sentence += '.'
        summary_bullets.append(f"• {sentence}")
    
    # Create formatted summary
    summary_header = "📝 Key Points Summary\n" + "=" * 40 + "\n\n"
    summary_content = "\n\n".join(summary_bullets)
    
    return summary_header + summary_content


def get_allowed_extensions():
    """Return the set of allowed file extensions"""
    return {'pdf', 'docx', 'doc', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif'}


def get_file_type(filename):
    """
    Determine the extraction method based on file extension
    
    Args:
        filename: Name of the file
        
    Returns:
        str: The file type ('word', 'pdf', 'ocr') or None if unsupported
    """
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if ext in ['docx', 'doc']:
        return 'word'
    elif ext == 'pdf':
        return 'pdf'
    elif ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif']:
        return 'ocr'
    else:
        return None
