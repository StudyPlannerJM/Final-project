"""
Tests for Document Processor utility functions
"""
from unittest.mock import Mock, patch, mock_open
from app.utils.document_processor import (
    extract_text_from_response,
    extract_text_from_word,
    extract_text_from_pdf,
    extract_text_from_image_ocr,
    extract_text,
    generate_summary,
    get_allowed_extensions,
    get_file_type
)


class TestExtractTextFromResponse:
    """Test extract_text_from_response function"""
    
    def test_extract_from_none(self):
        """Test extraction from None returns empty string"""
        result = extract_text_from_response(None)
        assert result == ''
    
    def test_extract_from_string(self):
        """Test extraction from string returns the string"""
        result = extract_text_from_response("Sample text")
        assert result == "Sample text"
    
    def test_extract_from_dict_with_text_key(self):
        """Test extraction from dict with 'text' key"""
        data = {'text': 'Content here'}
        result = extract_text_from_response(data)
        assert result == 'Content here'
    
    def test_extract_from_dict_with_content_key(self):
        """Test extraction from dict with 'content' key"""
        data = {'content': 'Document content'}
        result = extract_text_from_response(data)
        assert result == 'Document content'
    
    def test_extract_from_dict_with_extracted_text_key(self):
        """Test extraction from dict with 'extracted_text' key"""
        data = {'extracted_text': 'Extracted data'}
        result = extract_text_from_response(data)
        assert result == 'Extracted data'
    
    def test_extract_from_dict_with_result_key(self):
        """Test extraction from dict with 'result' key"""
        data = {'result': 'Result content'}
        result = extract_text_from_response(data)
        assert result == 'Result content'
    
    def test_extract_from_dict_with_multiple_values(self):
        """Test extraction from dict with multiple values"""
        data = {'title': 'Title', 'body': 'Body content', 'footer': 'Footer'}
        result = extract_text_from_response(data)
        assert 'Title' in result
        assert 'Body content' in result
        assert 'Footer' in result
    
    def test_extract_from_nested_dict(self):
        """Test extraction from nested dict"""
        data = {'data': {'text': 'Nested text'}}
        result = extract_text_from_response(data)
        assert result == 'Nested text'
    
    def test_extract_from_list_of_strings(self):
        """Test extraction from list of strings"""
        data = ['Line 1', 'Line 2', 'Line 3']
        result = extract_text_from_response(data)
        assert result == 'Line 1\nLine 2\nLine 3'
    
    def test_extract_from_list_of_dicts(self):
        """Test extraction from list of dicts"""
        data = [{'text': 'First'}, {'text': 'Second'}]
        result = extract_text_from_response(data)
        assert 'First' in result
        assert 'Second' in result
    
    def test_extract_from_other_types(self):
        """Test extraction from other types converts to string"""
        result = extract_text_from_response(12345)
        assert result == '12345'


class TestExtractTextFromWord:
    """Test extract_text_from_word function"""
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'docx content')
    def test_extract_word_success(self, mock_file, mock_post, app):
        """Test successful Word text extraction"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'Extracted Word text'}
            mock_post.return_value = mock_response
            
            success, text = extract_text_from_word('/path/to/file.docx')
            
            assert success is True
            assert text == 'Extracted Word text'
            assert mock_post.called
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'docx content')
    def test_extract_word_api_error(self, mock_file, mock_post, app):
        """Test Word extraction handles API errors"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = 'Bad request'
            mock_post.return_value = mock_response
            
            success, error = extract_text_from_word('/path/to/file.docx')
            
            assert success is False
            assert 'API Error: 400' in error
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'docx content')
    def test_extract_word_empty_response(self, mock_file, mock_post, app):
        """Test Word extraction with empty data"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': ''}
            mock_post.return_value = mock_response
            
            success, error = extract_text_from_word('/path/to/file.docx')
            
            assert success is False
            assert 'No text could be extracted' in error
    
    @patch('builtins.open', side_effect=FileNotFoundError('File not found'))
    def test_extract_word_file_not_found(self, mock_file, app):
        """Test Word extraction with missing file"""
        with app.app_context():
            success, error = extract_text_from_word('/nonexistent/file.docx')
            
            assert success is False
            assert 'Error extracting text from Word file' in error


class TestExtractTextFromPDF:
    """Test extract_text_from_pdf function"""
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'pdf content')
    def test_extract_pdf_success(self, mock_file, mock_post, app):
        """Test successful PDF text extraction"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'Extracted PDF text'}
            mock_post.return_value = mock_response
            
            success, text = extract_text_from_pdf('/path/to/file.pdf')
            
            assert success is True
            assert text == 'Extracted PDF text'
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'pdf content')
    def test_extract_pdf_api_error(self, mock_file, mock_post, app):
        """Test PDF extraction handles API errors"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Internal server error'
            mock_post.return_value = mock_response
            
            success, error = extract_text_from_pdf('/path/to/file.pdf')
            
            assert success is False
            assert 'API Error: 500' in error
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'pdf content')
    def test_extract_pdf_empty_response(self, mock_file, mock_post, app):
        """Test PDF extraction with empty data"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': '   '}
            mock_post.return_value = mock_response
            
            success, error = extract_text_from_pdf('/path/to/file.pdf')
            
            assert success is False
            assert 'No text could be extracted from the PDF' in error


class TestExtractTextFromImageOCR:
    """Test extract_text_from_image_ocr function"""
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image content')
    def test_extract_ocr_success_jpg(self, mock_file, mock_post, app):
        """Test successful OCR extraction from JPG"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'OCR extracted text'}
            mock_post.return_value = mock_response
            
            success, text = extract_text_from_image_ocr('/path/to/image.jpg')
            
            assert success is True
            assert text == 'OCR extracted text'
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image content')
    def test_extract_ocr_success_png(self, mock_file, mock_post, app):
        """Test successful OCR extraction from PNG"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'PNG text content'}
            mock_post.return_value = mock_response
            
            success, text = extract_text_from_image_ocr('/path/to/image.png')
            
            assert success is True
            assert text == 'PNG text content'
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image content')
    def test_extract_ocr_api_error(self, mock_file, mock_post, app):
        """Test OCR extraction handles API errors"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = 'Unauthorized'
            mock_post.return_value = mock_response
            
            success, error = extract_text_from_image_ocr('/path/to/image.jpg')
            
            assert success is False
            assert 'API Error: 401' in error
    
    @patch('app.utils.document_processor.requests.post')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image content')
    def test_extract_ocr_empty_response(self, mock_file, mock_post, app):
        """Test OCR extraction with empty data"""
        with app.app_context():
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': ''}
            mock_post.return_value = mock_response
            
            success, error = extract_text_from_image_ocr('/path/to/image.jpg')
            
            assert success is False
            assert 'No text could be extracted using OCR' in error


class TestExtractText:
    """Test extract_text dispatcher function"""
    
    @patch('app.utils.document_processor.extract_text_from_word')
    def test_extract_text_word(self, mock_word, app):
        """Test dispatching to Word extraction"""
        with app.app_context():
            mock_word.return_value = (True, 'Word text')
            
            success, text = extract_text('/path/to/file.docx', 'word')
            
            assert success is True
            assert text == 'Word text'
            mock_word.assert_called_once_with('/path/to/file.docx')
    
    @patch('app.utils.document_processor.extract_text_from_pdf')
    def test_extract_text_pdf(self, mock_pdf, app):
        """Test dispatching to PDF extraction"""
        with app.app_context():
            mock_pdf.return_value = (True, 'PDF text')
            
            success, text = extract_text('/path/to/file.pdf', 'pdf')
            
            assert success is True
            assert text == 'PDF text'
            mock_pdf.assert_called_once_with('/path/to/file.pdf')
    
    @patch('app.utils.document_processor.extract_text_from_image_ocr')
    def test_extract_text_ocr(self, mock_ocr, app):
        """Test dispatching to OCR extraction"""
        with app.app_context():
            mock_ocr.return_value = (True, 'OCR text')
            
            success, text = extract_text('/path/to/image.jpg', 'ocr')
            
            assert success is True
            assert text == 'OCR text'
            mock_ocr.assert_called_once_with('/path/to/image.jpg')
    
    def test_extract_text_unsupported_type(self):
        """Test extraction with unsupported file type"""
        success, error = extract_text('/path/to/file.xyz', 'unknown')
        
        assert success is False
        assert error == "Unsupported file type"


class TestGenerateSummary:
    """Test generate_summary function"""
    
    def test_summary_from_normal_text(self):
        """Test summary generation from normal text"""
        text = """This is the first sentence of a document that contains important information.
        The second sentence provides additional context about the topic we are discussing.
        Here is another sentence that explains key concepts in detail and provides valuable insights.
        The fourth sentence continues the narrative with more examples and explanations about the subject.
        Finally, this sentence concludes the main points of the discussion."""
        
        result = generate_summary(text, max_sentences=3)
        
        assert '📝 Key Points Summary' in result
        assert '=' in result
        assert '•' in result
    
    def test_summary_empty_text(self):
        """Test summary with empty text"""
        result = generate_summary('')
        assert result == "No content to summarize."
    
    def test_summary_from_dict(self):
        """Test summary generation from dict input"""
        data = {'text': 'This is a sentence with enough words to be included in summary. Another good sentence here.'}
        result = generate_summary(data)
        
        assert '📝 Key Points Summary' in result
    
    def test_summary_short_text(self):
        """Test summary with very short text"""
        text = "Short content here with just a few words"
        result = generate_summary(text)
        
        # Should return preview or original since sentences too short
        assert 'Document Content' in result or '📝 Key Points Summary' in result
    
    def test_summary_respects_max_sentences(self):
        """Test that summary respects max_sentences parameter"""
        text = """First important sentence that should be included in the summary here.
        Second important sentence with valuable information here.
        Third important sentence with more details here.
        Fourth important sentence continuing the discussion here.
        Fifth important sentence adding more context here.
        Sixth important sentence with additional information here.
        Seventh important sentence with further explanations here."""
        
        result = generate_summary(text, max_sentences=3)
        
        # Count bullet points
        bullet_count = result.count('•')
        assert bullet_count <= 3
    
    def test_summary_normalizes_whitespace(self):
        """Test that summary normalizes excessive whitespace"""
        text = """This is a sentence with    excessive    spaces and information.
        
        
        Another sentence with     weird      formatting but important content."""
        
        result = generate_summary(text)
        
        # Should still create a summary
        assert '📝 Key Points Summary' in result
    
    def test_summary_filters_short_sentences(self):
        """Test that very short sentences are filtered out"""
        text = """Hi. Hello. This is a proper sentence with enough content to be meaningful.
        Ok. Another good sentence that provides valuable information and context."""
        
        result = generate_summary(text, max_sentences=5)
        
        # 'Hi', 'Hello', 'Ok' should be filtered out
        assert 'Hi.' not in result
        assert 'Hello.' not in result
        assert 'Ok.' not in result
    
    def test_summary_adds_punctuation(self):
        """Test that summary adds period if missing"""
        text = "This is a long sentence without ending punctuation but has enough words"
        result = generate_summary(text)
        
        # If sentence is included, it should have punctuation added
        if '•' in result:
            assert '.' in result or '!' in result or '?' in result
    
    def test_summary_capitalizes_sentences(self):
        """Test that summary capitalizes first letter"""
        text = "this is a lowercase sentence with adequate length and content for inclusion"
        result = generate_summary(text)
        
        # Should capitalize the first letter
        if 'this is a lowercase' in result.lower():
            # Find the bullet point and check capitalization
            lines = result.split('\n')
            for line in lines:
                if 'this' in line.lower() and '•' in line:
                    # After the bullet, first letter should be uppercase
                    assert 'This' in line or 'this' not in line.split('•')[1][:10].lower()
    
    def test_summary_long_document_preview(self):
        """Test preview mode for documents with no valid sentences"""
        text = "A" * 600  # Long text without proper sentences
        result = generate_summary(text)
        
        # Should provide a preview
        assert 'Document Content' in result or '...' in result
    
    def test_summary_keywords_boost_score(self):
        """Test that sentences with keywords get higher scores"""
        text = """This is an unimportant sentence with random words in it here today.
        The main conclusion of this research is that important factors matter significantly.
        Just another regular sentence without any special keywords here."""
        
        result = generate_summary(text, max_sentences=1)
        
        # Sentence with keywords should be preferred
        assert 'conclusion' in result.lower() or 'important' in result.lower()


class TestGetAllowedExtensions:
    """Test get_allowed_extensions function"""
    
    def test_returns_set_of_extensions(self):
        """Test that function returns a set with expected extensions"""
        extensions = get_allowed_extensions()
        
        assert isinstance(extensions, set)
        assert 'pdf' in extensions
        assert 'docx' in extensions
        assert 'doc' in extensions
        assert 'jpg' in extensions
        assert 'jpeg' in extensions
        assert 'png' in extensions


class TestGetFileType:
    """Test get_file_type function"""
    
    def test_word_docx_file(self):
        """Test identification of .docx files"""
        result = get_file_type('document.docx')
        assert result == 'word'
    
    def test_word_doc_file(self):
        """Test identification of .doc files"""
        result = get_file_type('document.doc')
        assert result == 'word'
    
    def test_pdf_file(self):
        """Test identification of PDF files"""
        result = get_file_type('document.pdf')
        assert result == 'pdf'
    
    def test_jpg_file(self):
        """Test identification of JPG files"""
        result = get_file_type('image.jpg')
        assert result == 'ocr'
    
    def test_jpeg_file(self):
        """Test identification of JPEG files"""
        result = get_file_type('image.jpeg')
        assert result == 'ocr'
    
    def test_png_file(self):
        """Test identification of PNG files"""
        result = get_file_type('image.png')
        assert result == 'ocr'
    
    def test_gif_file(self):
        """Test identification of GIF files"""
        result = get_file_type('image.gif')
        assert result == 'ocr'
    
    def test_uppercase_extension(self):
        """Test that uppercase extensions work"""
        result = get_file_type('IMAGE.JPG')
        assert result == 'ocr'
    
    def test_unsupported_file(self):
        """Test unsupported file type returns None"""
        result = get_file_type('file.xyz')
        assert result is None
    
    def test_file_without_extension(self):
        """Test file without extension returns None"""
        result = get_file_type('noextension')
        assert result is None
