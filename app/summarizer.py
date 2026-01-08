# ==============================================================================
# SUMMARIZER MODULE - Text extraction and summarization functions
# ==============================================================================

import requests
import os

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
            text = result.get('data', '')
            if text:
                return True, text
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
            text = result.get('data', '')
            if text:
                return True, text
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
            text = result.get('data', '')
            if text:
                return True, text
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
    if not text or len(text.strip()) == 0:
        return "No content to summarize."
    
    # Clean the text
    text = text.strip()
    
    # Split into sentences (simple approach)
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    # Filter out very short sentences and clean them
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if not sentences:
        return text  # Return original if no valid sentences found
    
    # Simple extractive summarization: score sentences by length and position
    # and select the most important ones
    scored_sentences = []
    for i, sentence in enumerate(sentences):
        # Score based on position (earlier sentences often more important)
        position_score = 1.0 / (i + 1)
        # Score based on length (medium-length sentences are often better)
        length_score = min(len(sentence) / 100, 1.0)
        # Combined score
        score = position_score * 0.6 + length_score * 0.4
        scored_sentences.append((score, i, sentence))
    
    # Sort by score and get top sentences
    scored_sentences.sort(reverse=True)
    top_sentences = scored_sentences[:max_sentences]
    
    # Sort back by original position to maintain flow
    top_sentences.sort(key=lambda x: x[1])
    
    # Format as bullet points for study notes
    summary_bullets = []
    for _, _, sentence in top_sentences:
        # Clean up the sentence
        sentence = sentence.strip()
        if not sentence.endswith('.'):
            sentence += '.'
        summary_bullets.append(f"• {sentence}")
    
    return "\n\n".join(summary_bullets)


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
