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
