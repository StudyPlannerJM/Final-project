"""
Tests for AI Generator utility functions
"""
import pytest
from unittest.mock import Mock, patch
from app.utils.ai_generator import configure_gemini_api, generate_study_plan, format_plan_for_display


class TestConfigureGeminiAPI:
    """Test configure_gemini_api function"""
    
    def test_configure_with_valid_api_key(self, app):
        """Test API configuration with valid key"""
        with app.app_context():
            with patch('app.utils.ai_generator.genai') as mock_genai:
                mock_client = Mock()
                mock_genai.Client.return_value = mock_client
                
                result = configure_gemini_api()
                
                assert result == mock_client
                mock_genai.Client.assert_called_once()
    
    def test_configure_without_genai_library(self, app):
        """Test error when genai is not installed"""
        with app.app_context():
            with patch('app.utils.ai_generator.genai', None):
                with pytest.raises(ImportError, match="Google Generative AI library is not installed"):
                    configure_gemini_api()
    
    def test_configure_without_api_key(self, app):
        """Test error when API key is missing"""
        with app.app_context():
            app.config['GEMINI_API_KEY'] = None
            with patch('app.utils.ai_generator.genai') as _mock_genai:
                with pytest.raises(ValueError, match="GEMINI_API_KEY is not configured"):
                    configure_gemini_api()


class TestGenerateStudyPlan:
    """Test generate_study_plan function"""
    
    @patch('app.utils.ai_generator.configure_gemini_api')
    def test_generate_plan_with_days(self, mock_config, app):
        """Test plan generation with days as time unit"""
        with app.app_context():
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "# Generated Study Plan\n- Goal 1\n- Goal 2"
            mock_client.models.generate_content.return_value = mock_response
            mock_config.return_value = mock_client
            
            result = generate_study_plan('Python', 7, 'days', 'beginner')
            
            assert result is not None
            assert "Generated Study Plan" in result
            mock_client.models.generate_content.assert_called_once()
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            assert call_kwargs['model'] == 'gemini-flash-latest'
            assert 'Python' in call_kwargs['contents']
            assert '7 days' in call_kwargs['contents']
            assert 'beginner' in call_kwargs['contents']
    
    @patch('app.utils.ai_generator.configure_gemini_api')
    def test_generate_plan_with_weeks(self, mock_config, app):
        """Test plan generation with weeks as time unit"""
        with app.app_context():
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "# Study Plan\n- Week 1 tasks"
            mock_client.models.generate_content.return_value = mock_response
            mock_config.return_value = mock_client
            
            result = generate_study_plan('Mathematics', 2, 'weeks', 'intermediate')
            
            assert result is not None
            assert "Study Plan" in result
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            assert 'Mathematics' in call_kwargs['contents']
            assert '2 weeks' in call_kwargs['contents']
            assert 'intermediate' in call_kwargs['contents']
    
    @patch('app.utils.ai_generator.configure_gemini_api')
    def test_generate_plan_with_months(self, mock_config, app):
        """Test plan generation with months as time unit"""
        with app.app_context():
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "# Advanced Study Plan\n## Month 1"
            mock_client.models.generate_content.return_value = mock_response
            mock_config.return_value = mock_client
            
            result = generate_study_plan('Data Science', 3, 'months', 'advanced')
            
            assert result is not None
            assert "Advanced Study Plan" in result
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            assert 'Data Science' in call_kwargs['contents']
            assert '3 months' in call_kwargs['contents']
            assert 'advanced' in call_kwargs['contents']
    
    @patch('app.utils.ai_generator.configure_gemini_api')
    def test_generate_plan_singular_time_units(self, mock_config, app):
        """Test plan generation with singular time units (1 day, 1 week, 1 month)"""
        with app.app_context():
            mock_client = Mock()
            mock_response = Mock()
            mock_response.text = "Plan content"
            mock_client.models.generate_content.return_value = mock_response
            mock_config.return_value = mock_client
            
            # Test 1 day
            generate_study_plan('Quick Topic', 1, 'days', 'beginner')
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            assert '1 day' in call_kwargs['contents']
            
            # Test 1 week
            generate_study_plan('Weekly Topic', 1, 'weeks', 'beginner')
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            assert '1 week' in call_kwargs['contents']
            
            # Test 1 month
            generate_study_plan('Monthly Topic', 1, 'months', 'beginner')
            call_kwargs = mock_client.models.generate_content.call_args.kwargs
            assert '1 month' in call_kwargs['contents']
    
    @patch('app.utils.ai_generator.configure_gemini_api')
    def test_generate_plan_handles_api_errors(self, mock_config, app):
        """Test error handling when API call fails"""
        with app.app_context():
            mock_client = Mock()
            mock_client.models.generate_content.side_effect = Exception("API Error")
            mock_config.return_value = mock_client
            
            result = generate_study_plan('Subject', 5, 'days', 'beginner')
            
            assert result is not None
            assert "Error generating study plan" in result
            assert "API Error" in result
    
    @patch('app.utils.ai_generator.configure_gemini_api')
    def test_generate_plan_handles_config_errors(self, mock_config, app):
        """Test error handling when configuration fails"""
        with app.app_context():
            mock_config.side_effect = ValueError("Configuration failed")
            
            result = generate_study_plan('Subject', 5, 'days', 'beginner')
            
            assert result is not None
            assert "Error generating study plan" in result
            assert "Configuration failed" in result


class TestFormatPlanForDisplay:
    """Test format_plan_for_display function"""
    
    def test_format_main_headers(self):
        """Test formatting of main headers (# Header)"""
        content = "# Overview\nSome text\n# Study Schedule"
        result = format_plan_for_display(content)
        
        assert '<h2 class="plan-section-header">Overview</h2>' in result
        assert '<h2 class="plan-section-header">Study Schedule</h2>' in result
    
    def test_format_subheaders(self):
        """Test formatting of subheaders (## Subheader)"""
        content = "## Phase 1: Introduction\n## Phase 2: Practice"
        result = format_plan_for_display(content)
        
        assert '<h3 class="plan-subsection-header">Phase 1: Introduction</h3>' in result
        assert '<h3 class="plan-subsection-header">Phase 2: Practice</h3>' in result
    
    def test_format_bullet_lists_with_dash(self):
        """Test formatting of bullet lists with dash (-)"""
        content = "- Item one\n- Item two\n- Item three"
        result = format_plan_for_display(content)
        
        assert '<ul class="plan-list">' in result
        assert '<li>Item one</li>' in result
        assert '<li>Item two</li>' in result
        assert '<li>Item three</li>' in result
        assert '</ul>' in result
    
    def test_format_bullet_lists_with_asterisk(self):
        """Test formatting of bullet lists with asterisk (*)"""
        content = "* First item\n* Second item"
        result = format_plan_for_display(content)
        
        assert '<ul class="plan-list">' in result
        assert '<li>First item</li>' in result
        assert '<li>Second item</li>' in result
        assert '</ul>' in result
    
    def test_format_numbered_lists(self):
        """Test formatting of numbered lists"""
        content = "1. Step one\n2. Step two\n3. Step three"
        result = format_plan_for_display(content)
        
        assert '<ol class="plan-numbered-list">' in result
        assert '<li>Step one</li>' in result
        assert '<li>Step two</li>' in result
        assert '<li>Step three</li>' in result
        assert '</ol>' in result
    
    def test_format_bold_text(self):
        """Test formatting of bold text (**bold**)"""
        content = "This is **important** text"
        result = format_plan_for_display(content)
        
        assert '<strong>important</strong>' in result
    
    def test_format_italic_text(self):
        """Test formatting of italic text (*italic*)"""
        content = "This is *emphasized* text"
        result = format_plan_for_display(content)
        
        assert '<em>emphasized</em>' in result
    
    def test_format_mixed_markdown(self):
        """Test formatting with mixed markdown elements"""
        content = "# Main Title\n## Subsection\n- **Bold** item\n- *Italic* item\n1. First\n2. Second"
        result = format_plan_for_display(content)
        
        assert '<h2 class="plan-section-header">Main Title</h2>' in result
        assert '<h3 class="plan-subsection-header">Subsection</h3>' in result
        assert '<strong>Bold</strong>' in result
        assert '<em>Italic</em>' in result
        assert '<ol class="plan-numbered-list">' in result
    
    def test_format_regular_paragraphs(self):
        """Test formatting of regular paragraph text"""
        content = "This is a regular paragraph.\nAnother paragraph here."
        result = format_plan_for_display(content)
        
        assert '<p class="plan-paragraph">This is a regular paragraph.</p>' in result
        assert '<p class="plan-paragraph">Another paragraph here.</p>' in result
    
    def test_format_empty_lines_create_spacing(self):
        """Test that empty lines create section spacing"""
        content = "Line one\n\nLine two"
        result = format_plan_for_display(content)
        
        assert '<div class="section-spacing"></div>' in result
    
    def test_format_closes_open_lists(self):
        """Test that open lists are properly closed"""
        content = "- Item 1\n- Item 2"
        result = format_plan_for_display(content)
        
        # Should have opening and closing ul tags
        assert result.count('<ul class="plan-list">') == 1
        assert result.count('</ul>') == 1
    
    def test_format_xss_protection(self):
        """Test XSS protection in formatted content"""
        content = "<script>alert('xss')</script>"
        result = format_plan_for_display(content)
        
        # Script tags should be escaped
        assert '&lt;script&gt;' in result
        assert '<script>' not in result
    
    def test_format_xss_in_headers(self):
        """Test XSS protection in headers"""
        content = "# <img src=x onerror=alert(1)>"
        result = format_plan_for_display(content)
        
        assert '&lt;img' in result
        assert '<img' not in result
    
    def test_format_xss_in_lists(self):
        """Test XSS protection in list items"""
        content = "- <iframe src='evil.com'></iframe>"
        result = format_plan_for_display(content)
        
        assert '&lt;iframe' in result
        assert '<iframe' not in result
    
    def test_format_transition_between_list_types(self):
        """Test transitions between bullet and numbered lists"""
        content = "- Bullet 1\n- Bullet 2\n1. Number 1\n2. Number 2\n- Bullet 3"
        result = format_plan_for_display(content)
        
        # Should properly close bullet list and open numbered list
        assert '<ul class="plan-list">' in result
        assert '</ul>' in result
        assert '<ol class="plan-numbered-list">' in result
        assert '</ol>' in result
    
    def test_format_complex_markdown_structure(self):
        """Test complex markdown structure with all elements"""
        content = """# 📋 Overview
- Goal: Master **Python** programming
- Duration: *30 days*

## Phase 1: Basics
1. Learn syntax
2. Practice **variables**
3. Study *functions*

Some explanatory text here.

- Additional tip
- Another tip"""
        
        result = format_plan_for_display(content)
        
        # Verify all elements are present and properly formatted
        assert '<h2 class="plan-section-header">' in result
        assert '<h3 class="plan-subsection-header">' in result
        assert '<ul class="plan-list">' in result
        assert '<ol class="plan-numbered-list">' in result
        assert '<strong>Python</strong>' in result
        assert '<em>30 days</em>' in result
        assert '<li>Learn syntax</li>' in result
        assert 'explanatory text' in result
    
    def test_format_preserves_emoji(self):
        """Test that emoji characters are preserved"""
        content = "# 📋 Overview\n- 📚 Study materials\n- ✅ Complete tasks"
        result = format_plan_for_display(content)
        
        assert '📋' in result
        assert '📚' in result
        assert '✅' in result
    
    def test_format_handles_bold_and_italic_in_same_line(self):
        """Test handling of both bold and italic in same line"""
        content = "This has **bold** and *italic* formatting"
        result = format_plan_for_display(content)
        
        assert '<strong>bold</strong>' in result
        assert '<em>italic</em>' in result
    
    def test_format_returns_markup_safe_html(self):
        """Test that the function returns Markup-safe HTML"""
        content = "# Test\n- Item"
        result = format_plan_for_display(content)
        
        # The result should contain Markup objects (safe HTML)
        assert '<h2 class="plan-section-header">' in result
        # Check that it's a string (joined Markup objects)
        assert isinstance(result, str)
