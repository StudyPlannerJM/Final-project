# ==============================================================================
# AI STUDY PLAN GENERATOR
# Uses Google Gemini AI to generate personalized study plans
# ==============================================================================

import os
from google import genai
from google.genai.types import GenerateContentConfig
from flask import current_app


def configure_gemini_api():
    """Configure the Google Gemini API with the API key"""
    # Try to get from environment variable first, fallback to hardcoded key
    api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyCbDUdL0WUWP20lS4rZM4bqGBSmUqoj54o')
    client = genai.Client(api_key=api_key)
    return client


def generate_study_plan(subject, days_until_exam, hours_per_day, knowledge_level):
    """
    Generate a personalized study plan using Google Gemini AI
    
    Args:
        subject (str): The subject or topic to study
        days_until_exam (int): Number of days until the exam
        hours_per_day (float): Hours available per day for studying
        knowledge_level (str): Current knowledge level (beginner, intermediate, advanced)
    
    Returns:
        str: Generated study plan in formatted text
    """
    try:
        # Configure the API
        client = configure_gemini_api()
        
        # Calculate total study hours
        total_hours = days_until_exam * hours_per_day
        
        # Create the prompt for the AI
        prompt = f"""
You are an expert educational advisor. Create a detailed, personalized study plan based on the following information:

**Subject/Topic:** {subject}
**Days Until Exam:** {days_until_exam} days
**Available Study Time:** {hours_per_day} hours per day (Total: {total_hours} hours)
**Current Knowledge Level:** {knowledge_level}

Please generate a comprehensive study plan that includes:

1. **Overview & Goals**
   - Brief assessment of the learning journey
   - Key learning objectives to achieve
   - Expected outcomes

2. **Week-by-Week Breakdown**
   - Divide the {days_until_exam} days into clear study phases
   - For each phase, specify:
     * Topics to cover
     * Recommended study methods
     * Time allocation per topic
     * Milestones to achieve

3. **Daily Study Schedule Template**
   - Suggested daily routine structure
   - Balance between learning new material and revision
   - Break recommendations

4. **Study Techniques & Resources**
   - Recommended study methods based on {knowledge_level} level
   - Suggested resources (textbooks, online courses, practice problems)
   - Active learning strategies

5. **Practice & Assessment**
   - Self-assessment checkpoints
   - Practice problem recommendations
   - Mock test schedule (especially in final days)

6. **Tips for Success**
   - Subject-specific tips
   - Memory retention techniques
   - Exam preparation strategies

Please make the plan realistic, achievable, and tailored to the {knowledge_level} knowledge level. Use clear formatting with headers, bullet points, and numbered lists for easy reading.
"""
        
        # Generate the study plan using the new API
        # Using gemini-flash-latest which typically has better quota availability
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt
        )
        
        # Return the generated text
        return response.text
        
    except Exception as e:
        current_app.logger.error(f"Error generating study plan: {str(e)}")
        return f"Error generating study plan: {str(e)}"


def format_plan_for_display(plan_content):
    """
    Format the AI-generated plan for better HTML display
    
    Args:
        plan_content (str): Raw plan content from AI
    
    Returns:
        str: Formatted HTML content
    """
    # Replace markdown-style headers with HTML
    import re
    
    # Replace **text** with <strong>text</strong>
    plan_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', plan_content)
    
    # Replace *text* with <em>text</em>
    plan_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', plan_content)
    
    # Replace line breaks with <br> tags
    plan_content = plan_content.replace('\n', '<br>')
    
    return plan_content


def generate_flashcards_from_plan(subject, plan_content, num_cards=10):
    """
    Generate flashcards from a study plan using Google Gemini AI
    
    Args:
        subject (str): The subject or topic
        plan_content (str): The study plan content
        num_cards (int): Number of flashcards to generate (default: 10)
    
    Returns:
        list: List of dictionaries with 'question' and 'answer' keys
    """
    try:
        # Configure the API
        client = configure_gemini_api()
        
        # Create the prompt for the AI
        prompt = f"""
Based on the following study plan for {subject}, generate {num_cards} high-quality flashcards for effective learning.

STUDY PLAN:
{plan_content}

Generate exactly {num_cards} flashcards that cover the most important concepts, terms, and ideas from this study plan.

CRITICAL FORMATTING REQUIREMENTS:
1. Return ONLY a valid JSON array with no additional text, markdown, or code blocks
2. Each flashcard must be an object with "question" and "answer" fields
3. Properly escape all special characters in JSON (use \\" for quotes, \\n for newlines)
4. Avoid using backslashes in text unless absolutely necessary
5. Keep text simple and avoid special formatting characters

Example format:
[
  {{"question": "What is the definition of photosynthesis?", "answer": "Photosynthesis is the process by which plants convert light energy into chemical energy."}},
  {{"question": "Explain Newton's First Law", "answer": "An object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force."}}
]

Generate flashcards that:
- Cover key concepts and terminology
- Include both factual recall and conceptual understanding questions
- Are clear, concise, and focused on one concept per card
- Have complete, accurate answers
- Are suitable for active recall practice

Return ONLY the JSON array, no other text before or after.
"""
        
        # Generate the flashcards using the AI with JSON response format
        config = GenerateContentConfig(
            response_mime_type="application/json"
        )
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=config
        )
        
        # Parse the response
        import json
        import re
        
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        response_text = response_text.strip()
        
        # Clean up potential escape sequence issues
        # Replace problematic backslashes that aren't part of valid escape sequences
        # This handles cases where AI includes file paths or other backslash-containing text
        try:
            # Try parsing as-is first
            flashcards = json.loads(response_text)
        except json.JSONDecodeError as e:
            current_app.logger.warning(f"Initial JSON parse failed: {str(e)}. Attempting to clean response.")
            # If that fails, try to clean the text
            # Use raw string decoder to handle escape sequences properly
            try:
                # Decode with strict=False to be more lenient
                decoder = json.JSONDecoder(strict=False)
                flashcards = decoder.decode(response_text)
            except:
                # Last resort: manually escape backslashes and try again
                response_text_cleaned = response_text.replace('\\', '\\\\')
                # But preserve valid JSON escapes
                response_text_cleaned = response_text_cleaned.replace('\\\\n', '\\n')
                response_text_cleaned = response_text_cleaned.replace('\\\\t', '\\t')
                response_text_cleaned = response_text_cleaned.replace('\\\\r', '\\r')
                response_text_cleaned = response_text_cleaned.replace('\\\\"', '\\"')
                flashcards = json.loads(response_text_cleaned)
        
        # Validate the structure
        if not isinstance(flashcards, list):
            raise ValueError("Response is not a list")
        
        # Ensure all flashcards have required fields
        validated_cards = []
        for card in flashcards[:num_cards]:  # Limit to requested number
            if isinstance(card, dict) and 'question' in card and 'answer' in card:
                validated_cards.append({
                    'question': str(card['question']).strip(),
                    'answer': str(card['answer']).strip()
                })
        
        return validated_cards
        
    except Exception as e:
        current_app.logger.error(f"Error generating flashcards: {str(e)}")
        # Return empty list on error
        return []
