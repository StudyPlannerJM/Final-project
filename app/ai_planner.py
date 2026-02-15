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


def generate_study_plan(subject, time_value, time_unit, knowledge_level):
    """
    Generate a personalized study plan using Google Gemini AI
    
    Args:
        subject (str): The subject or topic to study
        time_value (int): Number of time units
        time_unit (str): Unit of time ('days', 'weeks', or 'months')
        knowledge_level (str): Current knowledge level (beginner, intermediate, advanced)
    
    Returns:
        str: Generated study plan in formatted text
    """
    try:
        # Configure the API
        client = configure_gemini_api()
        
        # Convert time to days for calculations
        if time_unit == 'days':
            total_days = time_value
            time_display = f"{time_value} {'day' if time_value == 1 else 'days'}"
        elif time_unit == 'weeks':
            total_days = time_value * 7
            time_display = f"{time_value} {'week' if time_value == 1 else 'weeks'}"
        elif time_unit == 'months':
            total_days = time_value * 30  # Approximate
            time_display = f"{time_value} {'month' if time_value == 1 else 'months'}"
        else:
            total_days = time_value
            time_display = f"{time_value} days"
        
        # Create the prompt for the AI
        prompt = f"""
You are an expert educational advisor. Create a concise, actionable study plan based on the following:

**Subject:** {subject}
**Available Time:** {time_display} ({total_days} days)
**Knowledge Level:** {knowledge_level}

Generate a CONCISE study plan with clear structure:

# 📋 Overview
- Learning goals (2-3 key objectives)
- Expected outcome

# 📅 Study Schedule
Divide the {time_display} into phases (e.g., Week 1, Week 2, or Phase 1-3):
- **Phase [X]:** Topics to cover, time allocation, key milestone

# 📖 Daily Routine
- Suggested daily study blocks
- Include breaks (e.g., 25-min Pomodoro sessions)

# 🎯 Study Methods
- 3-4 most effective techniques for {knowledge_level} level
- Recommended resources (be specific)

# ✅ Assessment Points
- When to self-test (e.g., end of each phase)
- Practice problem schedule
- Mock exam timing

# 💡 Success Tips
3-5 actionable tips for {subject} mastery

Keep it CONCISE and ACTIONABLE. Use markdown formatting: # for main headers, ## for subheaders, - for bullets, **bold** for emphasis.
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
    Format the AI-generated plan for better HTML display with proper markdown conversion
    
    Args:
        plan_content (str): Raw plan content from AI with markdown
    
    Returns:
        str: Formatted HTML content
    """
    import re
    
    # Split into lines for processing
    lines = plan_content.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines (we'll add spacing with CSS)
        if not stripped:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append('<div class="section-spacing"></div>')
            continue
        
        # Main headers (# Header with emoji)
        if stripped.startswith('# '):
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            header_text = stripped[2:].strip()
            formatted_lines.append(f'<h2 class="plan-section-header">{header_text}</h2>')
        
        # Subheaders (## Subheader)
        elif stripped.startswith('## '):
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            header_text = stripped[3:].strip()
            formatted_lines.append(f'<h3 class="plan-subsection-header">{header_text}</h3>')
        
        # Bullet points (- item or * item)
        elif stripped.startswith('- ') or stripped.startswith('* '):
            item_text = stripped[2:].strip()
            # Format **bold** and *italic*
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item_text)
            item_text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', item_text)
            
            if not in_list:
                formatted_lines.append('<ul class="plan-list">')
                in_list = True
            formatted_lines.append(f'<li>{item_text}</li>')
        
        # Regular paragraph text
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            
            # Format **bold** and *italic*
            text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
            text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
            formatted_lines.append(f'<p class="plan-paragraph">{text}</p>')
    
    # Close any open list
    if in_list:
        formatted_lines.append('</ul>')
    
    return '\n'.join(formatted_lines)
